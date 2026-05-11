"""Tests del perfil PUBLIC_KB_RICH — 9B.8 (RED/GREEN).

Verifican que SingleSourceRetrievalStrategy + PassthroughMergeStrategy +
GenericAnswerTemplateStrategy + DefaultLanguagePolicy producen una respuesta
completa (sin fallback) en cada uno de los tres modos de retrieval.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)
from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import CoreGraph
from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
    DefaultLanguagePolicy,
    GenericAnswerTemplateStrategy,
    PassthroughMergeStrategy,
    SingleSourceRetrievalStrategy,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)

CHATBOT_ID = str(uuid.uuid4())

_ITEM = EvidenceItem(
    source_id="doc-test",
    content="Contenido de prueba para el test del perfil PUBLIC_KB_RICH.",
    title="Documento de prueba",
    score=0.9,
)


def _make_cfg(mode: str) -> PublicGraphConfig:
    return PublicGraphConfig(
        profile="PUBLIC_KB_RICH",
        retrieval_mode=mode,
        language_mode="prefer",
        quality_threshold=0.6,
        min_retrieval_results=2,
        min_retrieval_score=0.25,
        reranker_enabled=False,
        answer_template="generic",
    )


def _make_mock_pipeline(mode: str) -> MagicMock:
    """Pipeline mock que devuelve 2 items con score 0.9."""
    result = RetrievalResult(
        items=[_ITEM, _ITEM],
        debug={"pipeline_mode": mode},
    )
    pipeline = MagicMock()
    pipeline.run = AsyncMock(return_value=result)
    return pipeline


@pytest.mark.asyncio
class TestPublicKbRich:

    async def test_public_kb_rich_runs_in_rag_mode(self):
        """El perfil PUBLIC_KB_RICH genera respuesta en modo RAG."""
        cfg = _make_cfg("RAG")
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.protocols.get_pipeline",
            return_value=_make_mock_pipeline("RAG"),
        ):
            graph = CoreGraph(
                retrieval_strategy=SingleSourceRetrievalStrategy(),
                merge_strategy=PassthroughMergeStrategy(),
                template_strategy=GenericAnswerTemplateStrategy(),
                language_policy=DefaultLanguagePolicy(),
                cfg=cfg,
                deps=deps,
            )
            result = await graph.run(
                "¿Cuáles son los requisitos de acceso a la universidad?",
                CHATBOT_ID,
            )

        assert result["fallback_used"] is False
        assert result["answer"] is not None
        assert len(result["answer"]) > 0
        assert result["merged_items"] == [_ITEM, _ITEM]

    async def test_public_kb_rich_runs_in_md_long_context_mode(self):
        """El perfil PUBLIC_KB_RICH genera respuesta en modo MD_LONG_CONTEXT."""
        cfg = _make_cfg("MD_LONG_CONTEXT")
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.protocols.get_pipeline",
            return_value=_make_mock_pipeline("MD_LONG_CONTEXT"),
        ):
            graph = CoreGraph(
                retrieval_strategy=SingleSourceRetrievalStrategy(),
                merge_strategy=PassthroughMergeStrategy(),
                template_strategy=GenericAnswerTemplateStrategy(),
                language_policy=DefaultLanguagePolicy(),
                cfg=cfg,
                deps=deps,
            )
            result = await graph.run(
                "¿Cuáles son los requisitos de acceso a la universidad?",
                CHATBOT_ID,
            )

        assert result["fallback_used"] is False
        assert result["answer"] is not None
        assert "Documento de prueba" in result["answer"]

    async def test_public_kb_rich_runs_in_md_agent_selector_mode(self):
        """El perfil PUBLIC_KB_RICH genera respuesta en modo MD_AGENT_SELECTOR."""
        cfg = _make_cfg("MD_AGENT_SELECTOR")
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.protocols.get_pipeline",
            return_value=_make_mock_pipeline("MD_AGENT_SELECTOR"),
        ):
            graph = CoreGraph(
                retrieval_strategy=SingleSourceRetrievalStrategy(),
                merge_strategy=PassthroughMergeStrategy(),
                template_strategy=GenericAnswerTemplateStrategy(),
                language_policy=DefaultLanguagePolicy(),
                cfg=cfg,
                deps=deps,
            )
            result = await graph.run(
                "¿Cuáles son los requisitos de acceso a la universidad?",
                CHATBOT_ID,
            )

        assert result["fallback_used"] is False
        assert result["answer"] is not None
        assert len(result["answer"]) > 0
