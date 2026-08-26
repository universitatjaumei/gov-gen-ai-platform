"""Prompt 2.7 — Retriever híbrido (vector + keyword, Reciprocal Rank Fusion).

VIS.1: las tres búsquedas aceptan un MetadataFilter y lo aplican **en SQL**, con OUTER
JOIN a `hub_documents` y el filtro en el WHERE, antes del ORDER BY / LIMIT. Sustituye al
filtrado en memoria posterior al top_k de 9Q.6, que hacía que los documentos excluidos
consumieran plazas del resultado en vez de ser reemplazados.

Sin filtro explícito se aplica `MetadataFilter()`: público, canónico, sin superseded y
sin documentos con `us_assistents='no'`. El defecto es el cerrado.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import (
    HubDocument,
    HubDocumentChunk,
)
from server.app.modules.agents_hub.services.retrieval.metadata_filter import MetadataFilter


# Exportada porque `vector_strategy.py` necesita normalizar este score a la escala [0,1]
# que el quality gate del CoreGraph espera (ver RRF_MAX_SCORE ahí): duplicar el número a
# mano dejaría la normalización rota en silencio si este k cambiara alguna vez.
RRF_K = 60


def _fts_config(language: str | None) -> str:
    """Configuración de full-text search para un idioma.

    Solo el castellano tiene stemmer en PostgreSQL core; el catalán no, así que va con
    `simple` y se busca por forma exacta de la palabra. Cuando no se filtra por idioma
    también manda `simple`: la consulta es una sola y no puede tener dos configuraciones a
    la vez, y stemmizar en español un corpus mixto produce falsos positivos silenciosos.
    """
    return "spanish" if language == "es" else "simple"


@dataclass
class SearchResult:
    id: uuid.UUID
    content: str
    source_url: str
    language: str
    score: float
    metadata: dict = field(default_factory=dict)
    # RAG.8: sección completa a la que pertenece el fragmento, con la estrategia
    # 'parent_child'. Se busca con el hijo y se responde con el padre.
    parent_content: str | None = None
    # HIB.J: la **similitud coseno** del fragmento, que `hybrid_search` conserva en vez de
    # perderla al sobrescribir `score` con la nota de fusión.
    #
    # Existen las dos porque miden cosas distintas y cada control necesita la suya:
    # `score` es posición relativa (ordena), `relevance` es magnitud de parecido (juzga).
    # El quality gate necesitaba la segunda y estaba leyendo la primera normalizada, que es
    # **constante e igual a `vector_weight`** —medido: 0,7 en las 25 consultas del lote—,
    # porque el ganador de la fusión es siempre el rango 1 de la rama vectorial y el techo
    # teórico exige que el mismo fragmento salga también en la léxica, que con troceado
    # fino no pasa.
    #
    # `None` cuando el fragmento sólo lo trajo la rama léxica: `ts_rank_cd` no es una
    # similitud y afirmar que lo es sería inventarse el dato.
    relevance: float | None = None


class HybridRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _with_metadata_filter(query, metadata_filter: MetadataFilter | None):
        """OUTER JOIN al documento + condición del filtro en el WHERE."""
        mf = metadata_filter if metadata_filter is not None else MetadataFilter()
        return query.outerjoin(
            HubDocument, HubDocumentChunk.document_id == HubDocument.id
        ).where(mf.chunk_condition())

    async def vector_search(
        self,
        query_embedding: list[float],
        chatbot_id: uuid.UUID,
        top_k: int = 5,
        language: str | None = None,
        owner_id: uuid.UUID | None = None,
        metadata_filter: MetadataFilter | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Búsqueda vectorial con umbral de similitud opcional (RAG.5).

        `min_score` se aplica sobre la **similitud coseno** y en el WHERE, antes del
        ORDER BY / LIMIT: filtrar después dejaría que los candidatos por debajo del umbral
        ocuparan plazas del top_k, que es el mismo error que VIS.1 corrigió con el filtro
        de metadatos.

        DET.1: el desempate va **en Python y después del LIMIT**, no en el ORDER BY. pgvector
        solo sirve el índice HNSW para `ORDER BY <distancia>` a secas; añadirle una segunda
        clave lo inutiliza y devuelve cada consulta a recorrer todos los chunks del chatbot,
        deshaciendo RAG.3. Medido: `ORDER BY embedding <=> $1, id` cae a `Seq Scan + Sort`.

        Residuo que se acepta a cambio de conservar el índice: si un empate cae justo en el
        borde del LIMIT, **qué filas vuelven** sigue dependiendo del plan; lo que ya no depende
        es en qué orden salen las que vuelven. Con BGE-M3 el caso es teórico —empates exactos
        entre floats de 1024 dimensiones no ocurren—; aparece con embeddings deterministas
        como el del corpus de fixture.
        """
        similarity = 1 - HubDocumentChunk.embedding.cosine_distance(query_embedding)
        query = (
            select(HubDocumentChunk, similarity.label("score"))
            .where(HubDocumentChunk.chatbot_id == chatbot_id)
            .where(HubDocumentChunk.embedding.isnot(None))
            .where(
                (~HubDocumentChunk.is_temporary)
                | (HubDocumentChunk.owner_id == owner_id)
            )
        )
        if min_score > 0.0:
            query = query.where(similarity >= min_score)
        if language:
            query = query.where(HubDocumentChunk.language == language)
        query = self._with_metadata_filter(query, metadata_filter)
        query = query.order_by(similarity.desc()).limit(top_k)

        result = await self.session.execute(query)
        filas = sorted(
            result.all(),
            key=lambda row: (-float(row.score), row.HubDocumentChunk.content_hash),
        )
        return [
            SearchResult(
                id=row.HubDocumentChunk.id,
                content=row.HubDocumentChunk.content,
                source_url=row.HubDocumentChunk.source_url,
                language=row.HubDocumentChunk.language,
                score=float(row.score),
                metadata=row.HubDocumentChunk.chunk_metadata or {},
                parent_content=row.HubDocumentChunk.parent_content,
            )
            for row in filas
        ]

    async def keyword_search(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        top_k: int = 5,
        language: str | None = None,
        owner_id: uuid.UUID | None = None,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[SearchResult]:
        """Full-text search de PostgreSQL sobre la columna generada `tsv` (RAG.4).

        `websearch_to_tsquery` y no `plainto_tsquery`: acepta la sintaxis que el usuario ya
        conoce de un buscador (comillas para frase exacta, `or`, `-`) y no revienta con
        entradas raras, que es lo que se recibe de un chat.

        El score es `ts_rank_cd` **normalizado dividiendo por el maximo del lote**, para que
        quede en [0,1] como el de la rama vectorial. Es normalizacion relativa a la consulta,
        no absoluta: el mejor resultado de cada busqueda vale 1.0. A la fusion RRF le da
        igual —solo mira el orden— pero quien lea el score sabra que compara dentro del lote.
        """
        config = _fts_config(language)
        tsquery = func.websearch_to_tsquery(config, query)
        rank = func.ts_rank_cd(HubDocumentChunk.tsv, tsquery)

        filters = [
            HubDocumentChunk.chatbot_id == chatbot_id,
            (~HubDocumentChunk.is_temporary)
            | (HubDocumentChunk.owner_id == owner_id),
            HubDocumentChunk.tsv.op("@@")(tsquery),
        ]
        if language:
            filters.append(HubDocumentChunk.language == language)

        stmt = self._with_metadata_filter(
            select(HubDocumentChunk, rank.label("rank")).where(*filters), metadata_filter
        )
        # DET.1: desempate en SQL, que aquí es gratis. El GIN sirve el WHERE y no el ORDER BY,
        # así que este Sort ya se pagaba; y `ts_rank_cd` devuelve valores muy cuantizados, o sea
        # que los empates son frecuentes y lo seguirán siendo con el corpus real. `content_hash`
        # y no `id`: el id es un uuid4 y rebarajaría los empates en cada reingesta.
        stmt = stmt.order_by(rank.desc(), HubDocumentChunk.content_hash).limit(top_k)

        filas = (await self.session.execute(stmt)).all()
        if not filas:
            return []
        maximo = max(float(fila.rank) for fila in filas) or 1.0
        return [
            SearchResult(
                id=fila.HubDocumentChunk.id,
                content=fila.HubDocumentChunk.content,
                source_url=fila.HubDocumentChunk.source_url,
                language=fila.HubDocumentChunk.language,
                score=float(fila.rank) / maximo,
                metadata=fila.HubDocumentChunk.chunk_metadata or {},
                parent_content=fila.HubDocumentChunk.parent_content,
            )
            for fila in filas
        ]

    async def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        chatbot_id: uuid.UUID,
        top_k: int = 5,
        language: str | None = None,
        vector_weight: float = 0.7,
        owner_id: uuid.UUID | None = None,
        metadata_filter: MetadataFilter | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Fusión RRF de las dos ramas (k=60, `vector_weight`), sin cambios desde 2.7.

        `min_score` viaja **solo a la rama vectorial** (RAG.5). La señal de la rama léxica es
        de ranking, no de similitud: un `ts_rank_cd` de 0,3 no significa lo mismo que un
        coseno de 0,3, y filtrar ambas con el mismo número sería comparar magnitudes
        distintas. El quality gate del CoreGraph es otro control y no se solapa con este:
        aquel decide por-respuesta sobre la media de evidencias, este por-chunk.

        El score que devuelve esta función está en escala RRF (máximo teórico 1/(k+1),
        aquí ~0,0164): a propósito, es el contrato que ya fija
        `test_should_keep_rrf_fusion_contract_unchanged`. Quien consuma este score para
        decidir "¿es una buena respuesta?" —el quality gate, vía `EvidenceItem.score`—
        necesita la escala [0,1] con la que se diseñó `quality_threshold` (los tests de
        `core_graph` ya mockean scores en ese rango), y esa conversión se hace en
        `vector_strategy.py` (`RRF_MAX_SCORE`), no aquí.
        """
        vector_results = await self.vector_search(
            query_embedding, chatbot_id, top_k * 2, language, owner_id,
            metadata_filter=metadata_filter, min_score=min_score,
        )
        keyword_results = await self.keyword_search(
            query, chatbot_id, top_k * 2, language, owner_id,
            metadata_filter=metadata_filter,
        )

        k = 60
        scores: dict[uuid.UUID, tuple[SearchResult, float]] = {}
        # HIB.J: la similitud coseno de la rama vectorial se guarda ANTES de que la fusión
        # sobrescriba `score`. Sólo la tienen los fragmentos que salieron por vector: la nota
        # de la rama léxica es `ts_rank_cd`, que ordena pero no mide parecido.
        relevancias: dict[uuid.UUID, float] = {}
        for rank, r in enumerate(vector_results):
            scores[r.id] = (r, vector_weight * (1 / (k + rank + 1)))
            relevancias[r.id] = r.score
        for rank, r in enumerate(keyword_results):
            rrf = (1 - vector_weight) * (1 / (k + rank + 1))
            if r.id in scores:
                scores[r.id] = (r, scores[r.id][1] + rrf)
            else:
                scores[r.id] = (r, rrf)

        sorted_results = sorted(scores.values(), key=lambda x: x[1], reverse=True)
        return [
            SearchResult(
                id=r.id,
                content=r.content,
                source_url=r.source_url,
                language=r.language,
                score=s,
                metadata=r.metadata,
                parent_content=r.parent_content,
                relevance=relevancias.get(r.id),
            )
            for r, s in sorted_results[:top_k]
        ]
