"""Tests de AgenticRetrievalStrategy y sus tools -- TDD."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_doc_record(**kwargs) -> MagicMock:
    doc = MagicMock()
    doc.id = kwargs.get("id", uuid.uuid4())
    doc.title = kwargs.get("title", "Norma X")
    doc.canonical_url = kwargs.get("url", "https://ejemplo.com/norma.pdf")
    doc.markdown_content = kwargs.get("content", "Contenido completo")
    doc.language = kwargs.get("language", "es")
    doc.section_path = kwargs.get("section_path", None)
    doc.token_count = kwargs.get("token_count", 500)
    return doc


def _make_session_with_docs(docs: list) -> AsyncMock:
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = docs
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars_mock
    session = AsyncMock()
    session.execute = AsyncMock(return_value=exec_result)
    return session


@pytest.mark.asyncio
class TestAgenticStrategyCore:

    async def test_get_context_returns_empty_for_agentic(self):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        session = _make_session_with_docs([])
        strategy = AgenticRetrievalStrategy(session)
        ctx = await strategy.get_context("consulta", uuid.uuid4())

        assert ctx.sources == []
        assert ctx.mode == "agentic"
        assert ctx.total_tokens == 0

    async def test_get_agent_tools_returns_list_and_read_tools(self):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        strategy = AgenticRetrievalStrategy(AsyncMock())
        tools = strategy.get_agent_tools()
        tool_names = [t.__name__ for t in tools]
        assert "list_documents" in tool_names
        assert "read_document" in tool_names

    async def test_list_index_returns_all_documents_of_chatbot(self):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        doc = _make_doc_record(title="Ordenanza", token_count=1000)
        session = _make_session_with_docs([doc])
        strategy = AgenticRetrievalStrategy(session)
        items = await strategy.list_index(uuid.uuid4(), None)

        assert len(items) == 1
        assert items[0]["title"] == "Ordenanza"
        assert items[0]["token_count"] == 1000

    async def test_list_index_filters_by_language(self):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        doc = _make_doc_record(language="ca")
        session = _make_session_with_docs([doc])
        strategy = AgenticRetrievalStrategy(session)
        items = await strategy.list_index(uuid.uuid4(), "ca")

        assert items[0]["language"] == "ca"

    async def test_read_returns_full_markdown_with_metadata(self):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        doc_id = uuid.uuid4()
        doc = _make_doc_record(id=doc_id, title="Reglamento", content="# Texto", url="https://ej.com/reg.pdf")
        session = AsyncMock()
        session.get = AsyncMock(return_value=doc)
        strategy = AgenticRetrievalStrategy(session)
        result = await strategy.read(doc_id)

        assert result is not None
        assert result["title"] == "Reglamento"
        assert result["markdown_content"] == "# Texto"

    async def test_read_returns_none_for_unknown_id(self):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        strategy = AgenticRetrievalStrategy(session)
        result = await strategy.read(uuid.uuid4())

        assert result is None


@pytest.mark.asyncio
class TestListDocumentsTool:

    async def test_list_documents_tool_formats_index_with_token_estimates(self):
        from server.app.modules.agents_hub.agent.tools.list_documents import list_documents

        class FakeIndex:
            async def list_index(self, chatbot_id, language):
                return [
                    {"id": str(uuid.uuid4()), "title": "Norma A", "url": "https://ej.com/a.pdf",
                     "language": "es", "section_path": None, "token_count": 200},
                ]

        result = await list_documents(str(uuid.uuid4()), FakeIndex())
        assert "Norma A" in result
        assert "read_document" in result

    async def test_list_documents_tool_empty_returns_no_documents_message(self):
        from server.app.modules.agents_hub.agent.tools.list_documents import list_documents

        class EmptyIndex:
            async def list_index(self, chatbot_id, language):
                return []

        result = await list_documents(str(uuid.uuid4()), EmptyIndex())
        assert "No hay documentos" in result


@pytest.mark.asyncio
class TestReadDocumentTool:

    async def test_read_document_tool_returns_markdown_content(self):
        from server.app.modules.agents_hub.agent.tools.read_document import read_document

        class FakeReader:
            async def read(self, document_id):
                return {"title": "Reglamento", "url": "https://ej.com/reg.pdf",
                        "markdown_content": "## Articulo 1"}

        result = await read_document(str(uuid.uuid4()), FakeReader())
        assert "Reglamento" in result
        assert "Articulo 1" in result

    async def test_read_document_tool_returns_not_found_message_for_unknown_id(self):
        from server.app.modules.agents_hub.agent.tools.read_document import read_document

        class NotFoundReader:
            async def read(self, document_id):
                return None

        doc_id = str(uuid.uuid4())
        result = await read_document(doc_id, NotFoundReader())
        assert "no encontrado" in result.lower()
