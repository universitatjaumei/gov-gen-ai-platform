"""Tests TDD (RED) para el endpoint de chat con streaming SSE.

Rutas reales (monorepo):
  src/api/routers/chat.py → server/app/api/v1/hub_chat.py
  tests/e2e/test_chat_endpoint.py → server/tests/modules/agents_hub/unit/test_chat_endpoint.py
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# JWT env para tests
_JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}


def _make_token(role: str = "user", user_id: str = "user-1") -> str:
    import os
    os.environ.update(_JWT_ENV)
    from server.app.core.auth import UserInfo, create_token
    return create_token(UserInfo(user_id=user_id, email="user@test.com", role=role))


def _build_test_app(chatbot_mock) -> FastAPI:
    """Crea una app FastAPI aislada con la sesión mockeada."""
    from fastapi import FastAPI
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


class TestChatEndpointAuthentication:

    def test_chat_requires_authentication(self) -> None:
        """Sin token → 401."""
        from server.app.api.v1.hub_chat import router as chat_router
        app = FastAPI()
        app.include_router(chat_router, prefix="/api/v1")

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/api/v1/hub/chat/{uuid.uuid4()}",
                json={"message": "Hola"},
            )
        assert response.status_code == 401

    @patch.dict("os.environ", _JWT_ENV)
    def test_chat_rejects_empty_message(self) -> None:
        """Mensaje vacío → 422."""
        chatbot = MagicMock()
        chatbot.id = uuid.uuid4()
        app = _build_test_app(chatbot)

        token = _make_token()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/api/v1/hub/chat/{chatbot.id}",
                json={"message": ""},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422


class TestChatEndpointChatbot:

    @patch.dict("os.environ", _JWT_ENV)
    def test_chat_chatbot_not_found_returns_404(self) -> None:
        """Chatbot inexistente → 404."""
        app = _build_test_app(chatbot_mock=None)

        token = _make_token()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/api/v1/hub/chat/{uuid.uuid4()}",
                json={"message": "Hola"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 404


class TestChatEndpointStreaming:

    @patch.dict("os.environ", _JWT_ENV)
    def test_chat_returns_sse_stream(self) -> None:
        """Petición válida → 200 con Content-Type text/event-stream."""
        

        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()
        app = _build_test_app(chatbot)

        async def _mock_astream(state):
            yield {"generate_response": {"messages": [AIMessage(content="Hola! ¿En qué puedo ayudarte?")]}}

        mock_compiled = MagicMock()
        mock_compiled.astream = _mock_astream

        mock_graph = MagicMock()
        mock_graph.compile = MagicMock(return_value=mock_compiled)

        token = _make_token()
        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=mock_graph),
            patch("server.app.api.v1.hub_chat.GoogleEmbeddingService"),
        ):
            with TestClient(app) as client:
                with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "¿Puedes ayudarme?"},
                    headers={"Authorization": f"Bearer {token}"},
                ) as response:
                    assert response.status_code == 200
                    assert "text/event-stream" in response.headers.get("content-type", "")
                    lines = [l for l in response.iter_lines() if l.startswith("data:")]
                    assert len(lines) >= 1

    @patch.dict("os.environ", _JWT_ENV)
    def test_chat_stream_contains_content_and_run_id(self) -> None:
        """El stream incluye 'content' y 'run_id' en cada chunk de respuesta."""
        

        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()
        app = _build_test_app(chatbot)

        async def _mock_astream(state):
            yield {"generate_response": {"messages": [AIMessage(content="Respuesta de prueba")]}}

        mock_compiled = MagicMock()
        mock_compiled.astream = _mock_astream
        mock_graph = MagicMock()
        mock_graph.compile = MagicMock(return_value=mock_compiled)

        token = _make_token()
        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=mock_graph),
            patch("server.app.api.v1.hub_chat.GoogleEmbeddingService"),
        ):
            with TestClient(app) as client:
                with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "Test"},
                    headers={"Authorization": f"Bearer {token}"},
                ) as response:
                    data_lines = [l for l in response.iter_lines() if l.startswith("data:")]

        assert len(data_lines) >= 1
        payload = json.loads(data_lines[0].removeprefix("data:").strip())
        assert "content" in payload
        assert "run_id" in payload
        assert payload["content"] == "Respuesta de prueba"

    @patch.dict("os.environ", _JWT_ENV)
    def test_chat_stream_ends_with_done_event(self) -> None:
        """El stream termina con un evento {done: true, run_id: ...}."""
        

        chatbot = MagicMock(spec=HubChatbot)
        chatbot.id = uuid.uuid4()
        app = _build_test_app(chatbot)

        async def _mock_astream(state):
            yield {"generate_response": {"messages": [AIMessage(content="Ok")]}}

        mock_compiled = MagicMock()
        mock_compiled.astream = _mock_astream
        mock_graph = MagicMock()
        mock_graph.compile = MagicMock(return_value=mock_compiled)

        token = _make_token()
        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=mock_graph),
            patch("server.app.api.v1.hub_chat.GoogleEmbeddingService"),
        ):
            with TestClient(app) as client:
                with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "Test"},
                    headers={"Authorization": f"Bearer {token}"},
                ) as response:
                    data_lines = [l for l in response.iter_lines() if l.startswith("data:")]

        last = json.loads(data_lines[-1].removeprefix("data:").strip())
        assert last.get("done") is True
        assert "run_id" in last
