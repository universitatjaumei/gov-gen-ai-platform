"""VectorRetrievalStrategy -- envuelve HybridRetriever y agrupa por documento."""

import logging
import uuid
from collections import defaultdict
from dataclasses import replace
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.reranker import pool_size
from server.app.modules.agents_hub.services.retrieval.citations import with_anchor
from server.app.modules.agents_hub.services.retrieval.metadata_filter import MetadataFilter
from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext, Source
from server.app.modules.agents_hub.services.retrieval.vigencia import marca_de_vigencia
from server.app.modules.agents_hub.services.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class VectorRetrievalStrategy:
    mode = "RAG"

    def __init__(
        self,
        session: AsyncSession,
        embedding_service,
        top_k: int = 8,
        metadata_filter: MetadataFilter | None = None,
        min_score: float = 0.0,
        reranker: Any = None,
    ):
        self._session = session
        self._embedding = embedding_service
        self._retriever = HybridRetriever(session)
        self._top_k = top_k
        self._filter = metadata_filter if metadata_filter is not None else MetadataFilter()
        self._min_score = min_score
        # RAG.6a: None = sin reranking. Lo inyecta el pipeline solo si cfg.reranker_enabled,
        # así que la estrategia no tiene que conocer el flag.
        self._reranker = reranker

    async def get_context(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
    ) -> RetrievalContext:
        query_embedding = await self._embedding.embed(query)
        # RAG.6a: con reranker se pide un pool ampliado. Pedirle `top_k` candidatos a un
        # reranker es pedirle que reordene lo que ya está elegido: no puede mejorar nada.
        candidatos = pool_size(self._top_k) if self._reranker else self._top_k
        results = await self._retriever.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            chatbot_id=chatbot_id,
            top_k=candidatos,
            language=language,
            # El filtro incluye la exclusión de páginas superseded (9Q.6) y el nivel de
            # acceso del actor (VIS.1); el defecto es cerrado.
            metadata_filter=self._filter,
            min_score=self._min_score,
        )
        if not results:
            return RetrievalContext(sources=[], mode=self.mode, total_tokens=0)

        if self._reranker is not None:
            results = await self._aplicar_reranker(query, results)

        # Group chunks by document_id (from metadata or None for legacy chunks)
        by_doc: dict[uuid.UUID | None, list] = defaultdict(list)
        for r in results:
            raw_id = r.metadata.get("document_id")
            doc_id = uuid.UUID(raw_id) if raw_id else None
            by_doc[doc_id].append(r)

        # Bulk-load documents
        doc_ids = [d for d in by_doc.keys() if d is not None]
        docs_map: dict[uuid.UUID, HubDocument] = {}
        if doc_ids:
            stmt = select(HubDocument).where(HubDocument.id.in_(doc_ids))
            res = await self._session.execute(stmt)
            docs_map = {d.id: d for d in res.scalars().all()}

        sources: list[Source] = []
        total_tokens = 0
        for doc_id, chunks in by_doc.items():
            best = max(chunks, key=lambda c: c.score)
            doc = docs_map.get(doc_id) if doc_id else None
            title = doc.title if doc else best.source_url.rsplit("/", 1)[-1]
            base_url = doc.canonical_url if doc else best.source_url
            # La cita apunta al artículo del que sale la evidencia, no al documento
            # entero: el ancla viene del chunk mejor puntuado (ING.0.4).
            url = with_anchor(base_url, best.metadata)
            excerpt = best.content
            sources.append(Source(
                document_id=doc.id if doc else uuid.uuid4(),
                title=title,
                url=url,
                excerpt=excerpt,
                score=best.score,
                metadata={
                    "chunks_matched": len(chunks),
                    "ancora": best.metadata.get("ancora"),
                    "ruta": best.metadata.get("ruta"),
                    # VIS.3: sin documento no hay dato de vigencia que consultar (chunk
                    # temporal o legado), y en ese caso no se advierte de lo que no se sabe.
                    **(marca_de_vigencia(doc) if doc else {}),
                },
            ))
            total_tokens += len(excerpt) // 4

        sources.sort(key=lambda s: s.score, reverse=True)
        return RetrievalContext(sources=sources, mode=self.mode, total_tokens=total_tokens)

    async def _aplicar_reranker(self, query: str, results: list) -> list:
        """Reordena el pool y **sustituye** el score de fusión por el del reranker.

        La sustitución no es un detalle: el packer de RAG.5 corta por score y el quality
        gate del CoreGraph promedia. Si conviviesen la escala del RRF (~1/60) y la del
        reranker ([0,1]), esos dos controles decidirían sobre números incomparables.

        La duración se registra porque es el dato con el que se decide si el reranker sale a
        cuenta: añade una llamada de red por consulta y nadie ha medido todavía cuánto pesa.
        """
        inicio = perf_counter()
        clasificados = await self._reranker.rerank(
            query, [r.content for r in results], self._top_k
        )
        transcurrido_ms = (perf_counter() - inicio) * 1000

        reordenados = []
        for clasificado in clasificados:
            original = results[clasificado.index]
            reordenados.append(replace(original, score=clasificado.score))

        logger.info(
            "rerank: %d candidatos -> %d resultados en %.0f ms",
            len(results),
            len(reordenados),
            transcurrido_ms,
        )
        return reordenados

    def get_agent_tools(self) -> list:
        return []
