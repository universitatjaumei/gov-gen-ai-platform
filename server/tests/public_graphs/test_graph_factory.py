"""Tests de GraphFactory — 9B.13 (RED/GREEN).

Verifican que:
- GraphFactory resuelve la config efectiva y crea CoreGraph con el perfil correcto.
- Si el chatbot sobreescribe perfil y retrieval_mode, se usan esos valores.
- Si el chatbot no existe, se aplican los defaults de organización.
- Si no hay organización, se aplican los defaults de plataforma.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)
from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import CoreGraph
from server.app.modules.agents_hub.agent.public_graphs.core.graph_factory import GraphFactory
from server.app.modules.agents_hub.agent.public_graphs.registry import GraphProfileRegistry
from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import RetrievalOutput
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_CFG = (
    "server.app.modules.agents_hub.agent.public_graphs.core.graph_factory"
    ".get_effective_public_graph_config"
)


def _mock_language():
    lang = MagicMock()
    lang.detect = MagicMock(return_value="es")
    lang.filter_items = MagicMock(side_effect=lambda _lengua, items: items)
    lang.should_warn_translation = MagicMock(return_value=False)
    return lang


def _test_registry() -> GraphProfileRegistry:
    """Registry de prueba con factories mock para cada perfil conocido."""
    registry = GraphProfileRegistry()

    def make_mock_graph(cfg, deps, llm=None):
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve = AsyncMock(return_value=RetrievalOutput(buckets=[]))
        mock_merge = MagicMock()
        mock_merge.merge = MagicMock(return_value=[])
        mock_template = MagicMock()
        mock_template.build_prompt_context = MagicMock(return_value="ctx")
        return CoreGraph(
            retrieval_strategy=mock_retrieval,
            merge_strategy=mock_merge,
            template_strategy=mock_template,
            language_policy=_mock_language(),
            cfg=cfg,
            deps=deps,
            llm=llm,
        )

    # PLG.1: los nombres son cadenas, no miembros de un enum. Se listan aquí a propósito en vez
    # de leerlos del registro global: este test monta SU registro y no debe depender de qué haya
    # descubierto el cargador en el entorno, que puede incluir paquetes instalados.
    for profile in ("PUBLIC_KB_RICH", "PUBLIC_PORTAL_AGGREGATOR", "PUBLIC_PORTAL_ROUTER"):
        registry.register_profile(profile, make_mock_graph)

    return registry


def _make_cfg(profile: str, retrieval_mode: str) -> PublicGraphConfig:
    return PublicGraphConfig(
        profile=profile,
        retrieval_mode=retrieval_mode,
        language_mode="prefer",
        quality_threshold=0.6,
        min_retrieval_results=2,
        min_retrieval_score=0.25,
        reranker_enabled=False,
        answer_template="generic",
    )


CHATBOT_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGraphFactory:

    async def test_graph_factory_uses_chatbot_override_profile_and_retrieval_mode(self):
        """El chatbot sobreescribe perfil y retrieval_mode; la factory los respeta."""
        chatbot_cfg = _make_cfg("PUBLIC_PORTAL_AGGREGATOR", "MD_LONG_CONTEXT")
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(_PATCH_CFG, AsyncMock(return_value=chatbot_cfg)):
            factory = GraphFactory(registry=_test_registry())
            graph = await factory.build(CHATBOT_ID, deps)

        assert isinstance(graph, CoreGraph)
        assert graph.cfg.profile == "PUBLIC_PORTAL_AGGREGATOR"
        assert graph.cfg.retrieval_mode == "MD_LONG_CONTEXT"
        assert graph.compile() is not None

    async def test_graph_factory_uses_org_defaults_when_chatbot_missing(self):
        """Sin overrides del chatbot, la factory aplica los defaults de organización."""
        org_cfg = _make_cfg("PUBLIC_KB_RICH", "MD_LONG_CONTEXT")
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(_PATCH_CFG, AsyncMock(return_value=org_cfg)):
            factory = GraphFactory(registry=_test_registry())
            graph = await factory.build(CHATBOT_ID, deps)

        assert isinstance(graph, CoreGraph)
        assert graph.cfg.profile == "PUBLIC_KB_RICH"
        assert graph.cfg.retrieval_mode == "MD_LONG_CONTEXT"

    async def test_graph_factory_uses_platform_defaults_when_org_missing(self):
        """Sin org ni overrides, la factory aplica los defaults de plataforma."""
        platform_cfg = _make_cfg("PUBLIC_KB_RICH", "RAG")
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(_PATCH_CFG, AsyncMock(return_value=platform_cfg)):
            factory = GraphFactory(registry=_test_registry())
            graph = await factory.build(CHATBOT_ID, deps)

        assert isinstance(graph, CoreGraph)
        assert graph.cfg.profile == "PUBLIC_KB_RICH"
        assert graph.cfg.retrieval_mode == "RAG"
