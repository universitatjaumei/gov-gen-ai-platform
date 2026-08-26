"""HIB.J — el pool de candidatos y la nota que lee el quality gate.

Apagar el reranker en HIB.A apagó también dos cosas que nadie pidió, y el paso 0 de este
prompt las midió sobre la tanda del 2026-08-26 (25 consultas del lote `ujirag-2024`):

1. **El pool se encogió de 30 fragmentos a 3.** En `vector_strategy.py` el número de
   candidatos era `pool_size(top_k) if reranker else top_k`. Como justo después se agrupa
   por documento y se conserva el mejor fragmento de cada uno, pedir 3 fragmentos hacía que
   `top_k = 3` no significara tres documentos: **19 de las 25 consultas recibieron menos
   documentos que `top_k`**, y 6 recibieron uno solo (reparto medido: 1 doc ×6, 2 docs ×13,
   3 docs ×6).

2. **La nota dejó de variar: valía EXACTAMENTE 0,7 en las 25.** Y 0,7 es `vector_weight`.
   El motivo no es un valor escrito a mano: el ganador de la fusión es siempre el fragmento
   de rango 1 de la rama vectorial, que aporta `vector_weight · 1/(k+1)`, y al normalizar
   por `RRF_MAX_SCORE = 1/(k+1)` queda `vector_weight`. El techo teórico —rango 1 en las dos
   ramas— exige que el MISMO fragmento salga en ambas, y con troceado fino eso práctimente
   no ocurre. `test_normalizes_rrf_score_to_0_1_scale_without_reranker` probaba la fórmula
   con ese techo teórico y pasaba; lo que no probaba es que la señal varíe.

   Una puerta que lee una constante no es una puerta: con umbral ≤ 0,7 pasa todo y con
   umbral > 0,7 no pasa nada. Es el mismo defecto que HIB.E arregla en el agéntico
   (`score = 1.0` fijo) por otra vía.

**Decisión de este prompt.** La ORDENACIÓN sigue siendo RRF: es lo que fusiona léxico y
vector, y la ablación de HIB.A mostró que ese camino funciona. Lo que cambia es la NOTA que
llega al quality gate, que pasa a ser la **similitud coseno** del mejor fragmento del
documento —una magnitud de relevancia, que varía— en vez de la fusión normalizada. Con
reranker sigue siendo la del reranker.

Esto no cambia la intención original, la cumple: el contrato escrito en `retriever.py` ya
decía que quien consume este score «para decidir ¿es una buena respuesta?» necesita la escala
[0,1] con la que se diseñó `quality_threshold`. La normalización intentaba dárselo y
producía una constante. Y de paso desaparece la asimetría que HIB.A tuvo que declarar como
trampa: con y sin reranker el umbral pasa a significar lo mismo.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.app.modules.agents_hub.services.retriever import SearchResult


def _chunk(
    doc_id: uuid.UUID | None,
    score: float,
    relevance: float | None,
    content: str = "fragmento",
) -> SearchResult:
    """Fragmento con la nota de fusión (`score`) y la similitud coseno (`relevance`)."""
    return SearchResult(
        id=uuid.uuid4(),
        content=content,
        source_url="https://ejemplo.com/norma.pdf",
        language="es",
        score=score,
        metadata={"document_id": str(doc_id)} if doc_id else {},
        relevance=relevance,
    )


def _session_sin_documentos() -> AsyncMock:
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars_mock
    session = AsyncMock()
    session.execute = AsyncMock(return_value=exec_result)
    return session


def _embedding() -> AsyncMock:
    svc = AsyncMock()
    svc.embed.return_value = [0.0] * 1024
    return svc


@pytest.mark.asyncio
class TestElPoolNoDependeDelReranker:

    async def test_should_keep_the_candidate_pool_when_the_reranker_is_off(self):
        from server.app.modules.agents_hub.services.reranker import pool_size
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            busqueda = AsyncMock(return_value=[])
            MockRetriever.return_value.hybrid_search = busqueda
            strategy = VectorRetrievalStrategy(
                _session_sin_documentos(), _embedding(), top_k=3
            )
            await strategy.get_context("consulta", uuid.uuid4())

        assert busqueda.await_args.kwargs["top_k"] == pool_size(3)

    async def test_should_use_the_explicit_candidate_k_when_configured(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            busqueda = AsyncMock(return_value=[])
            MockRetriever.return_value.hybrid_search = busqueda
            strategy = VectorRetrievalStrategy(
                _session_sin_documentos(), _embedding(), top_k=3, candidate_k=12
            )
            await strategy.get_context("consulta", uuid.uuid4())

        assert busqueda.await_args.kwargs["top_k"] == 12

    async def test_should_count_top_k_in_distinct_documents_not_chunks(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        docs = [uuid.uuid4() for _ in range(4)]
        chunks = []
        for i, d in enumerate(docs):
            chunks.append(_chunk(d, 0.9 - i * 0.1, 0.80 - i * 0.05, f"A{i}"))
            chunks.append(_chunk(d, 0.5 - i * 0.1, 0.70 - i * 0.05, f"B{i}"))

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(
                _session_sin_documentos(), _embedding(), top_k=3
            )
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert len(ctx.sources) == 3

    async def test_should_keep_the_rrf_order_of_documents(self):
        """El orden lo sigue decidiendo la fusión, no la relevancia coseno."""
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        primero, segundo = uuid.uuid4(), uuid.uuid4()
        chunks = [
            _chunk(primero, 0.9, 0.40, "gana la fusion"),
            _chunk(segundo, 0.2, 0.95, "gana el coseno"),
        ]

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(
                _session_sin_documentos(), _embedding(), top_k=2
            )
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert [s.excerpt for s in ctx.sources] == ["gana la fusion", "gana el coseno"]


@pytest.mark.asyncio
class TestLaNotaEsUnaMagnitudDeRelevancia:

    async def test_should_report_the_cosine_relevance_as_the_score_without_reranker(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )
        from server.app.modules.agents_hub.services.retriever import RRF_K

        fusion = 0.7 * (1.0 / (RRF_K + 1))  # el valor que producía la constante 0,7
        chunks = [_chunk(uuid.uuid4(), fusion, 0.83)]

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(_session_sin_documentos(), _embedding())
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert ctx.sources[0].score == pytest.approx(0.83)

    async def test_should_not_report_a_constant_for_different_matches(self):
        """El defecto medido, escrito como test: dos coincidencias distintas, misma nota."""
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )
        from server.app.modules.agents_hub.services.retriever import RRF_K

        fusion = 0.7 * (1.0 / (RRF_K + 1))
        notas = []
        for relevancia in (0.35, 0.91):
            chunks = [_chunk(uuid.uuid4(), fusion, relevancia)]
            with patch(
                "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
            ) as MockRetriever:
                MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
                strategy = VectorRetrievalStrategy(
                    _session_sin_documentos(), _embedding()
                )
                ctx = await strategy.get_context("consulta", uuid.uuid4())
            notas.append(ctx.sources[0].score)

        assert notas[0] != notas[1]

    async def test_should_still_report_the_reranker_score_when_the_reranker_is_on(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        chunks = [_chunk(uuid.uuid4(), 0.01, 0.20)]
        reranker = AsyncMock()
        reranker.rerank = AsyncMock(
            return_value=[type("R", (), {"index": 0, "score": 0.77})()]
        )

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(
                _session_sin_documentos(), _embedding(), reranker=reranker
            )
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert ctx.sources[0].score == pytest.approx(0.77)

    async def test_should_score_zero_when_no_chunk_has_a_cosine_relevance(self):
        """Fragmento sólo de la rama léxica: sin coseno no se afirma relevancia.

        Cero, y que decida la puerta; heredar una constante que la deja pasar es el
        defecto que este prompt viene a quitar.
        """
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        chunks = [_chunk(uuid.uuid4(), 0.005, None, "solo lexico")]

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(_session_sin_documentos(), _embedding())
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert ctx.sources[0].score == pytest.approx(0.0)

    async def test_should_take_the_best_relevance_among_the_chunks_of_a_document(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        doc_id = uuid.uuid4()
        chunks = [
            _chunk(doc_id, 0.9, 0.42, "gana la fusion"),
            _chunk(doc_id, 0.4, 0.88, "gana el coseno"),
        ]

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(_session_sin_documentos(), _embedding())
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        # La nota del documento es su mejor relevancia...
        assert ctx.sources[0].score == pytest.approx(0.88)
        # ...pero el fragmento citado —y del que sale el ancla— sigue siendo el que ganó la
        # fusión: mover eso cambiaría anclas y no es lo que este prompt decide.
        assert ctx.sources[0].excerpt == "gana la fusion"


@pytest.mark.asyncio
class TestLaFusionConservaLaSimilitudCoseno:
    """`hybrid_search` sobrescribía el coseno con la nota de fusión y lo perdía."""

    async def test_should_preserve_the_cosine_relevance_through_the_fusion(self):
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        chunk_id = uuid.uuid4()
        vectorial = SearchResult(
            id=chunk_id,
            content="fragmento",
            source_url="https://ejemplo.com/n.pdf",
            language="es",
            score=0.81,  # similitud coseno, tal como la devuelve `vector_search`
            metadata={},
        )

        retriever = HybridRetriever(AsyncMock())
        with patch.object(
            retriever, "vector_search", AsyncMock(return_value=[vectorial])
        ), patch.object(retriever, "keyword_search", AsyncMock(return_value=[])):
            resultados = await retriever.hybrid_search(
                query="consulta",
                query_embedding=[0.0] * 1024,
                chatbot_id=uuid.uuid4(),
                top_k=5,
            )

        assert len(resultados) == 1
        # La nota pasa a escala RRF, como siempre...
        assert resultados[0].score == pytest.approx(0.7 * (1.0 / 61))
        # ...y el coseno sobrevive para que la puerta tenga algo que leer.
        assert resultados[0].relevance == pytest.approx(0.81)

    async def test_should_leave_relevance_none_for_a_keyword_only_chunk(self):
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        lexico = SearchResult(
            id=uuid.uuid4(),
            content="fragmento",
            source_url="https://ejemplo.com/n.pdf",
            language="es",
            score=0.5,  # ts_rank_cd: señal de ranking, no de similitud
            metadata={},
        )

        retriever = HybridRetriever(AsyncMock())
        with patch.object(
            retriever, "vector_search", AsyncMock(return_value=[])
        ), patch.object(retriever, "keyword_search", AsyncMock(return_value=[lexico])):
            resultados = await retriever.hybrid_search(
                query="consulta",
                query_embedding=[0.0] * 1024,
                chatbot_id=uuid.uuid4(),
                top_k=5,
            )

        assert resultados[0].relevance is None
