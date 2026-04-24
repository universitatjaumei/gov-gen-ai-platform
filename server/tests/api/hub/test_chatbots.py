"""Tests para el endpoint /api/v1/hub/chatbots."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from server.app.core.auth.models import UserInfo
from server.app.main import app
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.api.deps import get_current_user

DEV_LLM_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEV_CLIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
DEV_CHATBOT_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")

_ADMIN = UserInfo(user_id="admin-1", email="admin@test.com", role="admin")


def _make_chatbot(name: str = "Demo", is_active: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=DEV_CHATBOT_ID,
        name=name,
        client_id=DEV_CLIENT_ID,
        llm_config_id=DEV_LLM_ID,
        system_prompt="Eres un asistente.",
        sources=[],
        theme_config={},
        is_active=is_active,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _session_with(rows: list):
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    session.get = AsyncMock(return_value=rows[0] if rows else None)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _override_session(session):
    async def _dep():
        yield session
    return _dep


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: _ADMIN
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


class TestListChatbots:
    def test_returns_list_of_chatbots(self, client):
        chatbot = _make_chatbot()
        app.dependency_overrides[get_async_session] = _override_session(_session_with([chatbot]))
        try:
            resp = client.get("/api/v1/hub/chatbots")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["name"] == "Demo"
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_returns_empty_list(self, client):
        app.dependency_overrides[get_async_session] = _override_session(_session_with([]))
        try:
            resp = client.get("/api/v1/hub/chatbots")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_requires_auth(self, client):
        app.dependency_overrides.pop(get_current_user, None)
        try:
            resp = client.get("/api/v1/hub/chatbots")
            assert resp.status_code == 401
        finally:
            app.dependency_overrides[get_current_user] = lambda: _ADMIN


class TestCreateChatbot:
    def test_creates_chatbot_returns_201(self, client):
        created = _make_chatbot("Nuevo Bot")
        session = _session_with([])

        async def _refresh(obj):
            obj.id = DEV_CHATBOT_ID
            obj.created_at = created.created_at
            obj.updated_at = created.updated_at

        session.refresh = _refresh
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.post(
                "/api/v1/hub/chatbots",
                json={
                    "name": "Nuevo Bot",
                    "client_id": str(DEV_CLIENT_ID),
                    "llm_config_id": str(DEV_LLM_ID),
                    "system_prompt": "Eres útil.",
                },
            )
            assert resp.status_code == 201
            assert resp.json()["name"] == "Nuevo Bot"
        finally:
            app.dependency_overrides.pop(get_async_session, None)


class TestUpdateChatbot:
    def test_updates_name_returns_200(self, client):
        chatbot = _make_chatbot("Original")

        async def _refresh(obj):
            pass

        session = _session_with([chatbot])
        session.refresh = _refresh
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.patch(
                f"/api/v1/hub/chatbots/{DEV_CHATBOT_ID}",
                json={"name": "Actualizado"},
            )
            assert resp.status_code == 200
            assert resp.json()["name"] == "Actualizado"
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_returns_404_for_unknown_id(self, client):
        session = _session_with([])
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.patch(
                f"/api/v1/hub/chatbots/{uuid.uuid4()}",
                json={"name": "x"},
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_async_session, None)


class TestDeleteChatbot:
    def test_deletes_chatbot_returns_204(self, client):
        chatbot = _make_chatbot()
        session = _session_with([chatbot])
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.delete(f"/api/v1/hub/chatbots/{DEV_CHATBOT_ID}")
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_returns_404_for_unknown_id(self, client):
        session = _session_with([])
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.delete(f"/api/v1/hub/chatbots/{uuid.uuid4()}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_async_session, None)
