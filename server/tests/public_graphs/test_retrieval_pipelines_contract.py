"""Tests de contrato por pipeline — 9B.5 (RED → GREEN).

Verifican que cada pipeline devuelve un RetrievalResult con la estructura
correcta, independientemente de cómo obtenga la evidencia internamente.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)
from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)


CHATBOT_ID = str(uuid.uuid4())

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


def _make_source(doc_id: uuid.UUID | None = None, language: str = "es"):
    from server.app.modules.agents_hub.services.retrieval.types import Source
    return Source(
        document_id=doc_id or uuid.uuid4(),
        title="Norma de prueba",
        url="https://ejemplo.com/norma.pdf",
        excerpt="Contenido de la norma.",
        score=0.85,
        metadata={"language": language},
    )


def _make_retrieval_context(sources=None, mode="RAG"):
    from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext
    return RetrievalContext(sources=sources or [], mode=mode, total_tokens=100)


def _make_doc(language: str = "es") -> MagicMock:
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.title = "Documento de prueba"
    doc.canonical_url = "https://ejemplo.com/doc.md"
    doc.markdown_content = "# Título\n\nContenido del documento."
    doc.language = language
    return doc


def _make_session_for_docs(docs: list) -> AsyncMock:
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = docs
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars_mock
    session = AsyncMock()
    session.execute = AsyncMock(return_value=exec_result)
    return session


@pytest.mark.asyncio
class TestRagPipelineContract:

    async def test_rag_pipeline_conforms_to_contract(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline import (
            RagVectorPipeline,
        )
        source = _make_source()
        ctx = _make_retrieval_context(sources=[source])
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline.VectorRetrievalStrategy"
        ) as MockStrategy:
            MockStrategy.return_value.get_context = AsyncMock(return_value=ctx)
            result = await RagVectorPipeline().run("consulta", CHATBOT_ID, _CFG, deps)

        assert isinstance(result, RetrievalResult)
        assert isinstance(result.items, list)
        assert isinstance(result.debug, dict)
        assert result.debug.get("pipeline_mode") == "RAG"

    async def test_rag_pipeline_maps_sources_to_evidence_items(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline import (
            RagVectorPipeline,
        )
        doc_id = uuid.uuid4()
        source = _make_source(doc_id=doc_id, language="es")
        ctx = _make_retrieval_context(sources=[source])
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline.VectorRetrievalStrategy"
        ) as MockStrategy:
            MockStrategy.return_value.get_context = AsyncMock(return_value=ctx)
            result = await RagVectorPipeline().run("consulta", CHATBOT_ID, _CFG, deps)

        assert len(result.items) == 1
        item = result.items[0]
        assert isinstance(item, EvidenceItem)
        assert item.source_id == str(doc_id)
        assert item.content == "Contenido de la norma."
        assert item.title == "Norma de prueba"
        assert item.score == pytest.approx(0.85)

    async def test_rag_pipeline_sets_context_source_language(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline import (
            RagVectorPipeline,
        )
        sources = [_make_source(language="ca"), _make_source(language="ca")]
        ctx = _make_retrieval_context(sources=sources)
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline.VectorRetrievalStrategy"
        ) as MockStrategy:
            MockStrategy.return_value.get_context = AsyncMock(return_value=ctx)
            result = await RagVectorPipeline().run("consulta", CHATBOT_ID, _CFG, deps)

        assert result.context_source_language == "ca"

    async def test_rag_pipeline_returns_empty_result_when_no_chunks(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline import (
            RagVectorPipeline,
        )
        ctx = _make_retrieval_context(sources=[])
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline.VectorRetrievalStrategy"
        ) as MockStrategy:
            MockStrategy.return_value.get_context = AsyncMock(return_value=ctx)
            result = await RagVectorPipeline().run("consulta", CHATBOT_ID, _CFG, deps)

        assert result.items == []
        assert result.context_source_language is None


@pytest.mark.asyncio
class TestMdLongContextPipelineContract:

    async def test_md_long_context_pipeline_conforms_to_contract(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.md_long_context_pipeline import (
            MdLongContextPipeline,
        )
        source = _make_source()
        ctx = _make_retrieval_context(sources=[source], mode="MD_LONG_CONTEXT")
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.md_long_context_pipeline.LongContextRetrievalStrategy"
        ) as MockStrategy:
            MockStrategy.return_value.get_context = AsyncMock(return_value=ctx)
            cfg = PublicGraphConfig(**{**_CFG.__dict__, "retrieval_mode": "MD_LONG_CONTEXT"})
            result = await MdLongContextPipeline().run("consulta", CHATBOT_ID, cfg, deps)

        assert isinstance(result, RetrievalResult)
        assert isinstance(result.items, list)
        assert result.debug.get("pipeline_mode") == "MD_LONG_CONTEXT"
        assert "docs" in result.debug

    async def test_md_long_context_pipeline_maps_sources_to_evidence_items(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.md_long_context_pipeline import (
            MdLongContextPipeline,
        )
        doc_id = uuid.uuid4()
        source = _make_source(doc_id=doc_id, language="es")
        ctx = _make_retrieval_context(sources=[source], mode="MD_LONG_CONTEXT")
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.strategies.md_long_context_pipeline.LongContextRetrievalStrategy"
        ) as MockStrategy:
            MockStrategy.return_value.get_context = AsyncMock(return_value=ctx)
            result = await MdLongContextPipeline().run("consulta", CHATBOT_ID, _CFG, deps)

        assert len(result.items) == 1
        assert result.items[0].source_id == str(doc_id)


@pytest.mark.asyncio
class TestMdAgentSelectorPipelineContract:

    async def test_md_agent_selector_pipeline_conforms_to_contract(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.md_agent_selector_pipeline import (
            MdAgentSelectorPipeline,
        )
        docs = [_make_doc("es"), _make_doc("ca")]
        session = _make_session_for_docs(docs)
        deps = GraphDeps(session=session, embedder=AsyncMock())
        cfg = PublicGraphConfig(**{**_CFG.__dict__, "retrieval_mode": "MD_AGENT_SELECTOR"})

        result = await MdAgentSelectorPipeline().run("consulta", CHATBOT_ID, cfg, deps)

        assert isinstance(result, RetrievalResult)
        assert isinstance(result.items, list)
        assert result.debug.get("pipeline_mode") == "MD_AGENT_SELECTOR"
        assert result.debug.get("selection") == "stub_all"

    async def test_md_agent_selector_returns_all_docs_as_items(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.md_agent_selector_pipeline import (
            MdAgentSelectorPipeline,
        )
        docs = [_make_doc("es"), _make_doc("es")]
        session = _make_session_for_docs(docs)
        deps = GraphDeps(session=session, embedder=AsyncMock())

        result = await MdAgentSelectorPipeline().run("consulta", CHATBOT_ID, _CFG, deps)

        assert len(result.items) == 2
        for item in result.items:
            assert isinstance(item, EvidenceItem)
            assert item.score == pytest.approx(1.0)

    async def test_md_agent_selector_sets_dominant_language(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.md_agent_selector_pipeline import (
            MdAgentSelectorPipeline,
        )
        docs = [_make_doc("ca"), _make_doc("ca"), _make_doc("es")]
        session = _make_session_for_docs(docs)
        deps = GraphDeps(session=session, embedder=AsyncMock())

        result = await MdAgentSelectorPipeline().run("consulta", CHATBOT_ID, _CFG, deps)

        assert result.context_source_language == "ca"

    async def test_md_agent_selector_empty_corpus(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.md_agent_selector_pipeline import (
            MdAgentSelectorPipeline,
        )
        session = _make_session_for_docs([])
        deps = GraphDeps(session=session, embedder=AsyncMock())

        result = await MdAgentSelectorPipeline().run("consulta", CHATBOT_ID, _CFG, deps)

        assert result.items == []
        assert result.context_source_language is None
        assert result.debug["docs_available"] == 0
