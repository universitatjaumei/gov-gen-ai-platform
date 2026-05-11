"""Tests de protocolos de estrategia — 9B.6 (RED/GREEN).

Verifican que:
- PipelineRetrievalStrategy invoca get_pipeline con cfg.retrieval_mode y devuelve
  un RetrievalOutput con el resultado como único bucket.
- RetrievalOutput puede contener múltiples buckets (para futuras fusiones).
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
    PipelineRetrievalStrategy,
    RetrievalOutput,
)
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

CHATBOT_ID = str(uuid.uuid4())


@pytest.mark.asyncio
class TestPipelineRetrievalStrategy:

    async def test_retrieval_strategy_uses_pipeline_factory(self):
        """PipelineRetrievalStrategy debe invocar get_pipeline(cfg.retrieval_mode)."""
        mock_result = RetrievalResult(items=[], debug={"pipeline_mode": "RAG"})
        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(return_value=mock_result)
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.protocols.get_pipeline",
            return_value=mock_pipeline,
        ) as mock_get_pipeline:
            output = await PipelineRetrievalStrategy().retrieve("consulta", CHATBOT_ID, _CFG, deps)

        mock_get_pipeline.assert_called_once_with("RAG")
        mock_pipeline.run.assert_called_once_with("consulta", CHATBOT_ID, _CFG, deps)
        assert isinstance(output, RetrievalOutput)
        assert len(output.buckets) == 1
        assert output.buckets[0] is mock_result

    async def test_retrieval_strategy_respects_retrieval_mode(self):
        """PipelineRetrievalStrategy debe pasar el mode correcto aunque no sea RAG."""
        mock_result = RetrievalResult(items=[], debug={"pipeline_mode": "MD_LONG_CONTEXT"})
        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(return_value=mock_result)
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())
        cfg_md = PublicGraphConfig(**{**_CFG.__dict__, "retrieval_mode": "MD_LONG_CONTEXT"})

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.protocols.get_pipeline",
            return_value=mock_pipeline,
        ) as mock_get_pipeline:
            output = await PipelineRetrievalStrategy().retrieve("consulta", CHATBOT_ID, cfg_md, deps)

        mock_get_pipeline.assert_called_once_with("MD_LONG_CONTEXT")
        assert output.buckets[0] is mock_result


class TestRetrievalOutput:

    def test_retrieval_output_can_hold_multiple_buckets(self):
        """RetrievalOutput debe poder contener varios RetrievalResult (buckets)."""
        item = EvidenceItem(source_id="doc1", content="texto de prueba")
        bucket_a = RetrievalResult(items=[item], debug={"pipeline_mode": "RAG"})
        bucket_b = RetrievalResult(items=[], debug={"pipeline_mode": "MD_LONG_CONTEXT"})

        output = RetrievalOutput(buckets=[bucket_a, bucket_b])

        assert len(output.buckets) == 2
        assert output.buckets[0].debug["pipeline_mode"] == "RAG"
        assert output.buckets[1].debug["pipeline_mode"] == "MD_LONG_CONTEXT"

    def test_retrieval_output_defaults_to_empty_buckets(self):
        output = RetrievalOutput()
        assert output.buckets == []

    def test_retrieval_output_single_bucket(self):
        result = RetrievalResult(items=[], debug={"pipeline_mode": "RAG"})
        output = RetrievalOutput(buckets=[result])
        assert len(output.buckets) == 1
        assert output.buckets[0] is result
