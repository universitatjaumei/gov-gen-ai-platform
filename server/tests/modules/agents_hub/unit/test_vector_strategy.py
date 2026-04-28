"""Tests de VectorRetrievalStrategy -- TDD."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.app.modules.agents_hub.services.retriever import SearchResult


def _make_chunk(doc_id: uuid.UUID | None, score: float, content: str = "fragmento") -> SearchResult:
    return SearchResult(
        id=uuid.uuid4(),
        content=content,
        source_url="https://ejemplo.com/norma.pdf",
        language="es",
        score=score,
        metadata={"document_id": str(doc_id)} if doc_id else {},
    )


def _make_document(doc_id: uuid.UUID, title: str = "Norma X") -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.title = title
    doc.canonical_url = f"https://ejemplo.com/{title.replace(' ', '_')}.pdf"
    return doc


@pytest.mark.asyncio
class TestVectorRetrievalStrategy:

    async def test_returns_empty_context_when_no_chunks(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )
        session = AsyncMock()
        embedding_svc = AsyncMock()
        embedding_svc.embed.return_value = [0.0] * 1024

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=[])
            strategy = VectorRetrievalStrategy(session, embedding_svc)
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert ctx.sources == []
        assert ctx.mode == "vector"
        assert ctx.total_tokens == 0

    async def test_groups_multiple_chunks_into_one_source_per_document(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )
        doc_id = uuid.uuid4()
        chunks = [
            _make_chunk(doc_id, 0.9, "fragmento A"),
            _make_chunk(doc_id, 0.7, "fragmento B"),
        ]
        session = AsyncMock()
        # make session.execute return the document
        doc = _make_document(doc_id, "Norma Municipal")
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [doc]
        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=exec_result)

        embedding_svc = AsyncMock()
        embedding_svc.embed.return_value = [0.0] * 1024

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(session, embedding_svc)
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        # Two chunks → one Source (same document)
        assert len(ctx.sources) == 1
        assert ctx.sources[0].document_id == doc_id

    async def test_uses_document_title_and_canonical_url_when_available(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )
        doc_id = uuid.uuid4()
        chunks = [_make_chunk(doc_id, 0.85, "extracto")]

        doc = _make_document(doc_id, "Ordenanza de Convivencia")
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [doc]
        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_mock
        session = AsyncMock()
        session.execute = AsyncMock(return_value=exec_result)

        embedding_svc = AsyncMock()
        embedding_svc.embed.return_value = [0.0] * 1024

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(session, embedding_svc)
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        src = ctx.sources[0]
        assert src.title == "Ordenanza de Convivencia"
        assert src.url == doc.canonical_url

    async def test_falls_back_to_filename_when_no_document_record(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )
        # chunk with no document_id in metadata → fallback
        chunk = SearchResult(
            id=uuid.uuid4(),
            content="contenido",
            source_url="https://servidor.com/reglamento.pdf",
            language="es",
            score=0.75,
            metadata={},
        )
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_mock
        session = AsyncMock()
        session.execute = AsyncMock(return_value=exec_result)

        embedding_svc = AsyncMock()
        embedding_svc.embed.return_value = [0.0] * 1024

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=[chunk])
            strategy = VectorRetrievalStrategy(session, embedding_svc)
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        src = ctx.sources[0]
        assert src.title == "reglamento.pdf"
        assert src.url == "https://servidor.com/reglamento.pdf"

    async def test_get_agent_tools_returns_empty_list(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )
        strategy = VectorRetrievalStrategy(AsyncMock(), AsyncMock())
        assert strategy.get_agent_tools() == []

    async def test_total_tokens_is_approximated_from_excerpt_length(self):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )
        doc_id = uuid.uuid4()
        excerpt = "A" * 400  # 400 chars / 4 = 100 tokens
        chunks = [_make_chunk(doc_id, 0.9, excerpt)]

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_mock
        session = AsyncMock()
        session.execute = AsyncMock(return_value=exec_result)

        embedding_svc = AsyncMock()
        embedding_svc.embed.return_value = [0.0] * 1024

        with patch(
            "server.app.modules.agents_hub.services.retrieval.vector_strategy.HybridRetriever"
        ) as MockRetriever:
            MockRetriever.return_value.hybrid_search = AsyncMock(return_value=chunks)
            strategy = VectorRetrievalStrategy(session, embedding_svc)
            ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert ctx.total_tokens == 100
