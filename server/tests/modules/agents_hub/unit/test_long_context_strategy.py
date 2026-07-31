"""Tests de LongContextRetrievalStrategy -- TDD."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_doc(token_count: int, language: str = "es") -> MagicMock:
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.title = f"Norma-{uuid.uuid4().hex[:4]}"
    doc.canonical_url = "https://ejemplo.com/norma.pdf"
    doc.markdown_content = "Contenido de norma " * 50
    doc.language = language
    doc.token_count = token_count
    doc.created_at = None
    return doc


def _make_session(docs: list) -> AsyncMock:
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = docs
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars_mock
    session = AsyncMock()
    session.execute = AsyncMock(return_value=exec_result)
    return session


@pytest.mark.asyncio
class TestLongContextRetrievalStrategy:

    async def test_returns_all_documents_as_sources_when_under_limit(self):
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )
        docs = [_make_doc(1000), _make_doc(2000)]
        session = _make_session(docs)
        strategy = LongContextRetrievalStrategy(session, token_limit=10_000)
        ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert len(ctx.sources) == 2
        assert ctx.mode == "MD_LONG_CONTEXT"
        assert ctx.total_tokens == 3000

    async def test_truncates_when_corpus_exceeds_limit(self):
        """VIS.2 cambió el contrato: se recorta y se dice, no se lanza.

        La versión anterior lanzaba ValueError, y en producción eso es una caída: el
        usuario recibe un error en vez de una respuesta parcial y marcada como parcial.
        """
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )
        docs = [_make_doc(60_000), _make_doc(60_000)]
        session = _make_session(docs)
        strategy = LongContextRetrievalStrategy(session, token_limit=100_000)

        ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert len(ctx.sources) == 1
        assert ctx.total_tokens == 60_000
        assert ctx.truncated is True
        assert ctx.discarded_documents == 1

    async def test_filters_by_language_when_specified(self):
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )
        # Only "ca" docs returned by session mock
        docs = [_make_doc(500, language="ca")]
        session = _make_session(docs)
        strategy = LongContextRetrievalStrategy(session, token_limit=10_000)
        ctx = await strategy.get_context("consulta", uuid.uuid4(), language="ca")

        assert len(ctx.sources) == 1
        assert ctx.sources[0].metadata["language"] == "ca"

    async def test_marks_sources_as_cacheable(self):
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )
        docs = [_make_doc(1000)]
        session = _make_session(docs)
        strategy = LongContextRetrievalStrategy(session, token_limit=10_000)
        ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert ctx.sources[0].metadata["cacheable"] is True

    async def test_returns_empty_when_chatbot_has_no_documents(self):
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )
        session = _make_session([])
        strategy = LongContextRetrievalStrategy(session, token_limit=10_000)
        ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert ctx.sources == []
        assert ctx.total_tokens == 0

    async def test_get_agent_tools_returns_empty_list(self):
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )
        strategy = LongContextRetrievalStrategy(AsyncMock())
        assert strategy.get_agent_tools() == []
