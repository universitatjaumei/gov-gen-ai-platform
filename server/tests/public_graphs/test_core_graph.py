"""Tests del CoreGraph — 9B.7 (RED/GREEN).

Verifican que:
- El CoreGraph compila sin error con cualquier conjunto de estrategias mock.
- Se toma el camino fallback cuando la calidad de retrieval es baja.
- El grafo produce una respuesta con cada retrieval_mode usando estrategias mock.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)
from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import CoreGraph
from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import RetrievalOutput
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)

_CFG = PublicGraphConfig(
    profile="PUBLIC_KB_RICH",
    retrieval_mode="RAG",
    language_mode="prefer",
    quality_threshold=0.6,
    min_retrieval_results=2,
    min_retrieval_score=0.25,
    reranker_enabled=False,
    answer_template="generic",
)


def _mock_strategies(merge_return=None, answer="respuesta"):
    mock_retrieval = MagicMock()
    mock_retrieval.retrieve = AsyncMock(
        return_value=RetrievalOutput(buckets=[])
    )
    mock_merge = MagicMock()
    mock_merge.merge = MagicMock(return_value=merge_return if merge_return is not None else [])
    mock_template = MagicMock()
    mock_template.build_prompt_context = MagicMock(return_value=answer)
    mock_language = MagicMock()
    mock_language.detect = MagicMock(return_value="es")
    mock_language.filter_items = MagicMock(side_effect=lambda lang, items: items)
    mock_language.should_warn_translation = MagicMock(return_value=False)
    return mock_retrieval, mock_merge, mock_template, mock_language


@pytest.mark.asyncio
class TestCoreGraph:

    async def test_core_graph_compiles_with_mock_strategies(self):
        """CoreGraph debe compilar sin errores con cualquier conjunto de estrategias mock."""
        retrieval, merge, template, language = _mock_strategies()
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        graph = CoreGraph(
            retrieval_strategy=retrieval,
            merge_strategy=merge,
            template_strategy=template,
            language_policy=language,
            cfg=_CFG,
            deps=deps,
        )
        compiled = graph.compile()
        assert compiled is not None

    async def test_core_graph_branches_to_fallback_when_quality_low(self):
        """Cuando merge devuelve 0 items, quality_score=0 < threshold → fallback."""
        retrieval, merge, template, language = _mock_strategies(merge_return=[])
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        graph = CoreGraph(
            retrieval_strategy=retrieval,
            merge_strategy=merge,
            template_strategy=template,
            language_policy=language,
            cfg=_CFG,
            deps=deps,
        )
        result = await graph.run("¿qué es esto?", str(uuid.uuid4()))

        assert result["fallback_used"] is True
        assert result["answer"] is None

    async def test_core_graph_runs_with_each_retrieval_mode_using_generic_profile(self):
        """Con 2 items de score 0.9, el grafo produce una respuesta en cada retrieval_mode."""
        for mode in ("RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR"):
            item = EvidenceItem(source_id="doc1", content="contenido de prueba", score=0.9)
            items = [item, item]

            mock_result = RetrievalResult(items=items, debug={"pipeline_mode": mode})
            mock_output = RetrievalOutput(buckets=[mock_result])

            mock_retrieval = MagicMock()
            mock_retrieval.retrieve = AsyncMock(return_value=mock_output)
            mock_merge = MagicMock()
            mock_merge.merge = MagicMock(return_value=items)
            mock_template = MagicMock()
            mock_template.build_prompt_context = MagicMock(return_value=f"contexto_{mode}")
            mock_language = MagicMock()
            mock_language.detect = MagicMock(return_value="es")
            mock_language.filter_items = MagicMock(side_effect=lambda lang, items: items)
            mock_language.should_warn_translation = MagicMock(return_value=False)

            cfg = PublicGraphConfig(
                profile="PUBLIC_KB_RICH",
                retrieval_mode=mode,
                language_mode="prefer",
                quality_threshold=0.6,
                min_retrieval_results=2,
                min_retrieval_score=0.25,
                reranker_enabled=False,
                answer_template="generic",
            )
            deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

            graph = CoreGraph(
                retrieval_strategy=mock_retrieval,
                merge_strategy=mock_merge,
                template_strategy=mock_template,
                language_policy=mock_language,
                cfg=cfg,
                deps=deps,
            )
            result = await graph.run("¿qué es X?", str(uuid.uuid4()))

            assert result["fallback_used"] is False, f"Fallback no esperado en modo {mode}"
            assert result["answer"] == f"contexto_{mode}", f"Respuesta incorrecta en modo {mode}"
