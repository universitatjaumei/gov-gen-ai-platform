"""Tests del perfil PUBLIC_PORTAL_ROUTER — 9B.9 (RED/GREEN).

Verifica que PortalRouterRetrievalStrategy:
- Carga la config efectiva del chatbot hijo seleccionado.
- Usa el retrieval_mode del hijo (no el del padre).
- Devuelve el RetrievalOutput producido por el pipeline del hijo.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)
from server.app.modules.agents_hub.agent.public_graphs.profiles.public_portal_router import (
    PortalRouterRetrievalStrategy,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)

_PARENT_CFG = PublicGraphConfig(
    profile="PUBLIC_PORTAL_ROUTER",
    retrieval_mode="RAG",
    language_mode="prefer",
    quality_threshold=0.6,
    min_retrieval_results=2,
    min_retrieval_score=0.25,
    reranker_enabled=False,
    answer_template="generic",
)


@pytest.mark.asyncio
class TestPortalRouterRetrievalStrategy:

    async def test_portal_router_selects_child_chatbot_and_uses_child_retrieval_mode(self):
        """El router carga la config del hijo y usa su retrieval_mode, no el del padre."""
        child_id = uuid.uuid4()

        # El hijo está configurado con MD_LONG_CONTEXT; el padre usa RAG
        child_cfg = PublicGraphConfig(
            profile="PUBLIC_KB_RICH",
            retrieval_mode="MD_LONG_CONTEXT",
            language_mode="prefer",
            quality_threshold=0.6,
            min_retrieval_results=2,
            min_retrieval_score=0.25,
            reranker_enabled=False,
            answer_template="generic",
            chatbot_id=child_id,
        )

        item = EvidenceItem(
            source_id="hijo-doc",
            content="Contenido del chatbot hijo.",
            score=0.85,
        )
        mock_result = RetrievalResult(
            items=[item],
            debug={"pipeline_mode": "MD_LONG_CONTEXT"},
        )
        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value=mock_result)

        mock_get_cfg = AsyncMock(return_value=child_cfg)
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.profiles.public_portal_router.get_effective_public_graph_config",
            mock_get_cfg,
        ), patch(
            "server.app.modules.agents_hub.agent.public_graphs.profiles.public_portal_router.get_pipeline",
            return_value=mock_pipeline,
        ) as mock_get_pipeline:
            strategy = PortalRouterRetrievalStrategy(child_chatbot_ids=[child_id])
            output = await strategy.retrieve(
                "¿Cuáles son los procedimientos disponibles?",
                str(uuid.uuid4()),
                _PARENT_CFG,
                deps,
            )

        # Verifica que se cargó la config del hijo con su ID
        mock_get_cfg.assert_called_once_with(child_id, deps.session)
        # Verifica que se usó el retrieval_mode del hijo (MD_LONG_CONTEXT), no el del padre (RAG)
        mock_get_pipeline.assert_called_once_with("MD_LONG_CONTEXT")
        mock_pipeline.run.assert_called_once_with(
            "¿Cuáles son los procedimientos disponibles?",
            str(child_id),
            child_cfg,
            deps,
        )
        assert len(output.buckets) == 1
        assert output.buckets[0].debug["pipeline_mode"] == "MD_LONG_CONTEXT"

    async def test_portal_router_returns_empty_when_no_children(self):
        """Sin hijos disponibles, el router devuelve RetrievalOutput vacío."""
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())
        strategy = PortalRouterRetrievalStrategy(child_chatbot_ids=[])
        output = await strategy.retrieve("consulta", str(uuid.uuid4()), _PARENT_CFG, deps)

        assert output.buckets == []
