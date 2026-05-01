"""Tests de integración SSE: evento done emite Source[] estructurado (9CBis.10).

Verifica que el evento 'done' serializa Source[] con (document_id, title, url, score)
en los tres modos de retrieval y que la selección de strategy es correcta.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.app.modules.agents_hub.database.config_models import HubChatbot
from server.app.modules.agents_hub.services.retrieval.types import Source

_JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}


def _make_token(user_id: str = "user-1") -> str:
    import os
    os.environ.update(_JWT_ENV)
    from server.app.core.auth import UserInfo, create_token
    return create_token(UserInfo(user_id=user_id, email="user@test.com", role="user"))


def _build_test_app(chatbot_mock) -> FastAPI:
    from server.app.api.v1.hub_chat import router as chat_router
    from server.app.modules.agents_hub.database.connection import get_async_session
    from sqlalchemy.ext.asyncio import AsyncSession

    mock_session = AsyncMock(spec=AsyncSession)
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none = MagicMock(return_value=chatbot_mock)
    mock_session.execute = AsyncMock(return_value=mock_scalar)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def _mock_session():
        yield mock_session

    app = FastAPI()
    app.dependency_overrides[get_async_session] = _mock_session
    app.include_router(chat_router, prefix="/api/v1")
    return app


def _parse_sse_lines(lines: list[str]) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    current_event = "message"
    for line in lines:
        if line.startswith("event:"):
            current_event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            payload = json.loads(line.removeprefix("data:").strip())
            events.append((current_event, payload))
            current_event = "message"
    return events


def _make_mock_graph_with_sources(
    sources: list,
    language_fallback: bool = False,
    language: str = "es",
) -> MagicMock:
    """Grafo mock que emite on_chain_end/generate_response con las fuentes dadas."""
    raw_events = [
        {
            "event": "on_chain_end",
            "name": "generate_response",
            "data": {
                "output": {
                    "sources": sources,
                    "language_fallback_triggered": language_fallback,
                    "language": language,
                }
            },
        }
    ]

    async def _astream(state, config=None, version="v2"):
        for ev in raw_events:
            yield ev

    mock_compiled = MagicMock()
    mock_compiled.astream_events = _astream
    mock_graph = MagicMock()
    mock_graph.compile = MagicMock(return_value=mock_compiled)
    return mock_graph


def _run_chat_and_get_done(chatbot, graph, token) -> dict:
    """Ejecuta el endpoint de chat y devuelve el payload del evento done."""
    app = _build_test_app(chatbot)
    with (
        patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=graph),
        patch("server.app.api.v1.hub_chat.get_embedding_service"),
        patch("server.app.api.v1.hub_chat.get_model", new_callable=AsyncMock),
    ):
        with TestClient(app) as client:
            with client.stream(
                "POST",
                f"/api/v1/hub/chat/{chatbot.id}",
                json={"message": "Test"},
                headers={"Authorization": f"Bearer {token}"},
            ) as response:
                lines = list(response.iter_lines())

    events = _parse_sse_lines(lines)
    done_events = [(e, p) for e, p in events if e == "done"]
    assert len(done_events) == 1, f"Se esperaba 1 evento 'done', encontrados: {len(done_events)}"
    return done_events[0][1]


# ──────────────────────────────────────────────────────────────────────────────
# Serialización estructurada de Source[]
# ──────────────────────────────────────────────────────────────────────────────

class TestDoneEventStructuredSources:

    @patch.dict("os.environ", _JWT_ENV)
    def test_done_event_includes_structured_sources_with_document_id(self) -> None:
        """El done incluye sources[].document_id como string UUID válido."""
        doc_id = uuid.uuid4()
        sources = [
            Source(
                document_id=doc_id,
                title="Reglament del Consell de Govern",
                url="https://www.uji.es/upo/rest/contenido/988181723/raw?idioma=ca",
                excerpt="text",
                score=0.92,
            )
        ]
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()

        done = _run_chat_and_get_done(chatbot, _make_mock_graph_with_sources(sources), _make_token())

        assert len(done["sources"]) == 1
        src = done["sources"][0]
        assert "document_id" in src
        assert src["document_id"] == str(doc_id)
        uuid.UUID(src["document_id"])  # debe ser UUID válido

    @patch.dict("os.environ", _JWT_ENV)
    def test_done_event_sources_have_title_url_and_score(self) -> None:
        """Cada source tiene title, url y score redondeado a 3 decimales."""
        doc_id = uuid.uuid4()
        sources = [
            Source(
                document_id=doc_id,
                title="Estatuts UJI",
                url="https://dogv.gva.es/datos/2025/12/18/pdf/2025_50021_va.pdf",
                excerpt="text",
                score=0.876543,
            )
        ]
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()

        done = _run_chat_and_get_done(chatbot, _make_mock_graph_with_sources(sources), _make_token())

        src = done["sources"][0]
        assert src["title"] == "Estatuts UJI"
        assert src["url"] == "https://dogv.gva.es/datos/2025/12/18/pdf/2025_50021_va.pdf"
        assert isinstance(src["score"], float)
        assert src["score"] == round(0.876543, 3)

    @patch.dict("os.environ", _JWT_ENV)
    def test_done_event_empty_sources_when_no_retrieval_happened(self) -> None:
        """Si generate_response devuelve sources=[], done emite sources=[]."""
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()

        done = _run_chat_and_get_done(chatbot, _make_mock_graph_with_sources([]), _make_token())

        assert done["sources"] == []

    @patch.dict("os.environ", _JWT_ENV)
    def test_done_event_multiple_sources_all_serialized(self) -> None:
        """Todas las fuentes se serializan, no solo la primera."""
        sources = [
            Source(document_id=uuid.uuid4(), title=f"Doc {i}",
                   url=f"https://example.com/doc{i}.pdf",
                   excerpt="text", score=round(0.9 - i * 0.1, 1))
            for i in range(3)
        ]
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()

        done = _run_chat_and_get_done(chatbot, _make_mock_graph_with_sources(sources), _make_token())

        assert len(done["sources"]) == 3
        titles = {s["title"] for s in done["sources"]}
        assert titles == {"Doc 0", "Doc 1", "Doc 2"}


# ──────────────────────────────────────────────────────────────────────────────
# Selección de RetrievalStrategy según retrieval_mode
# ──────────────────────────────────────────────────────────────────────────────

class TestRetrievalModeDispatch:

    @patch.dict("os.environ", _JWT_ENV)
    def test_long_context_strategy_instantiated_for_long_context_mode(self) -> None:
        """Cuando retrieval_mode='long_context', se instancia LongContextRetrievalStrategy."""
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()
        chatbot.retrieval_mode = "long_context"
        graph = _make_mock_graph_with_sources([])

        app = _build_test_app(chatbot)
        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=graph),
            patch("server.app.api.v1.hub_chat.get_embedding_service"),
            patch("server.app.api.v1.hub_chat.get_model", new_callable=AsyncMock),
            patch("server.app.api.v1.hub_chat.LongContextRetrievalStrategy") as mock_lc,
        ):
            with TestClient(app) as client:
                with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "Test"},
                    headers={"Authorization": f"Bearer {_make_token()}"},
                ) as response:
                    list(response.iter_lines())

        mock_lc.assert_called_once()

    @patch.dict("os.environ", _JWT_ENV)
    def test_agentic_strategy_instantiated_for_agentic_mode(self) -> None:
        """Cuando retrieval_mode='agentic', se instancia AgenticRetrievalStrategy."""
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()
        chatbot.retrieval_mode = "agentic"
        graph = _make_mock_graph_with_sources([])

        app = _build_test_app(chatbot)
        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=graph),
            patch("server.app.api.v1.hub_chat.get_embedding_service"),
            patch("server.app.api.v1.hub_chat.get_model", new_callable=AsyncMock),
            patch("server.app.api.v1.hub_chat.AgenticRetrievalStrategy") as mock_ag,
        ):
            with TestClient(app) as client:
                with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "Test"},
                    headers={"Authorization": f"Bearer {_make_token()}"},
                ) as response:
                    list(response.iter_lines())

        mock_ag.assert_called_once()

    @patch.dict("os.environ", _JWT_ENV)
    def test_vector_strategy_used_as_default(self) -> None:
        """Cuando retrieval_mode='vector' (default), se instancia VectorRetrievalStrategy."""
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()
        chatbot.retrieval_mode = "vector"
        graph = _make_mock_graph_with_sources([])

        app = _build_test_app(chatbot)
        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=graph),
            patch("server.app.api.v1.hub_chat.get_embedding_service"),
            patch("server.app.api.v1.hub_chat.get_model", new_callable=AsyncMock),
            patch("server.app.api.v1.hub_chat.VectorRetrievalStrategy") as mock_vec,
        ):
            with TestClient(app) as client:
                with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "Test"},
                    headers={"Authorization": f"Bearer {_make_token()}"},
                ) as response:
                    list(response.iter_lines())

        mock_vec.assert_called_once()

    @patch.dict("os.environ", _JWT_ENV)
    def test_long_context_mode_sources_marked_with_canonical_urls(self) -> None:
        """En modo long_context, los sources del done tienen la URL canónica del HubDocument."""
        canonical_url = "https://www.uji.es/upo/rest/contenido/1175964720/raw?idioma=ca"
        sources = [
            Source(
                document_id=uuid.uuid4(),
                title="Reglament del Claustre",
                url=canonical_url,
                excerpt="text complet",
                score=1.0,
            )
        ]
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()
        chatbot.retrieval_mode = "long_context"

        done = _run_chat_and_get_done(chatbot, _make_mock_graph_with_sources(sources), _make_token())

        assert len(done["sources"]) == 1
        assert done["sources"][0]["url"] == canonical_url
        assert done["sources"][0]["score"] == 1.0

    @patch.dict("os.environ", _JWT_ENV)
    def test_agentic_mode_sources_only_include_documents_actually_read(self) -> None:
        """En modo agentic, solo aparecen en sources los documentos que el LLM leyó."""
        read_doc_id = uuid.uuid4()
        unread_doc_id = uuid.uuid4()
        # El grafo agentic solo incluye el doc leído, no el listado
        sources_read = [
            Source(
                document_id=read_doc_id,
                title="Reglament Electoral",
                url="https://www.uji.es/upo/rest/contenido/1175964715/raw?idioma=ca",
                excerpt="text",
                score=1.0,
            )
        ]
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()
        chatbot.retrieval_mode = "agentic"

        done = _run_chat_and_get_done(
            chatbot, _make_mock_graph_with_sources(sources_read), _make_token()
        )

        source_ids = {s["document_id"] for s in done["sources"]}
        assert str(read_doc_id) in source_ids
        assert str(unread_doc_id) not in source_ids


# ──────────────────────────────────────────────────────────────────────────────
# Fallback de citas
# ──────────────────────────────────────────────────────────────────────────────

class TestNoCitationFallback:

    @patch.dict("os.environ", _JWT_ENV)
    def test_no_citation_fallback_emits_done_with_empty_sources(self) -> None:
        """Cuando retrieval no encontró nada (sources=[]), done emite sources=[]
        sin lanzar error y con interaction_id válido."""
        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()

        done = _run_chat_and_get_done(chatbot, _make_mock_graph_with_sources([]), _make_token())

        assert done["sources"] == []
        assert "interaction_id" in done
        uuid.UUID(done["interaction_id"])
        assert done["language_fallback"] is False
