"""Tests para el endpoint /api/v1/hub/clients."""
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

DEV_CLIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")

_ADMIN = UserInfo(user_id="admin-1", email="admin@test.com", role="admin")


def _make_client(name: str = "UJI", is_active: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=DEV_CLIENT_ID,
        name=name,
        partner_id="partner-1",
        theme_config={},
        is_active=is_active,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _session_for_list(rows_with_count: list):
    """Session mock para el endpoint list (devuelve tuplas (client, count))."""
    session = MagicMock()
    result = MagicMock()
    result.all.return_value = rows_with_count
    session.execute = AsyncMock(return_value=result)
    session.get = AsyncMock(return_value=rows_with_count[0][0] if rows_with_count else None)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _session_for_crud(client_obj=None):
    """Session mock para create/patch/delete."""
    session = MagicMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    session.get = AsyncMock(return_value=client_obj)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
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


class TestListClients:
    def test_returns_list_of_clients(self, client):
        c = _make_client()
        session = _session_for_list([(c, 3)])
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.get("/api/v1/hub/clients")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["name"] == "UJI"
            assert data[0]["chatbot_count"] == 3
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_returns_empty_list(self, client):
        session = _session_for_list([])
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.get("/api/v1/hub/clients")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_requires_auth(self, client):
        app.dependency_overrides.pop(get_current_user, None)
        try:
            resp = client.get("/api/v1/hub/clients")
            assert resp.status_code == 401
        finally:
            app.dependency_overrides[get_current_user] = lambda: _ADMIN


class TestCreateClient:
    def test_creates_client_returns_201(self, client):
        created = _make_client("Nueva Institución")
        session = _session_for_crud()

        async def _refresh(obj):
            obj.id = DEV_CLIENT_ID
            obj.created_at = created.created_at
            obj.updated_at = created.updated_at

        session.refresh = _refresh
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.post(
                "/api/v1/hub/clients",
                json={"name": "Nueva Institución", "partner_id": "partner-1"},
            )
            assert resp.status_code == 201
            assert resp.json()["name"] == "Nueva Institución"
            assert resp.json()["partner_id"] == "partner-1"
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_requires_name_and_partner_id(self, client):
        session = _session_for_crud()
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.post("/api/v1/hub/clients", json={"name": "Solo nombre"})
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_async_session, None)


class TestUpdateClient:
    def test_updates_name_returns_200(self, client):
        c = _make_client("Original")

        async def _refresh(obj):
            pass

        session = _session_for_crud(c)
        session.refresh = _refresh
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.patch(
                f"/api/v1/hub/clients/{DEV_CLIENT_ID}",
                json={"name": "Actualizado"},
            )
            assert resp.status_code == 200
            assert resp.json()["name"] == "Actualizado"
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_returns_404_for_unknown_id(self, client):
        session = _session_for_crud(None)
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.patch(
                f"/api/v1/hub/clients/{uuid.uuid4()}",
                json={"name": "x"},
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_async_session, None)


class TestDeleteClient:
    def test_deletes_client_returns_204(self, client):
        c = _make_client()
        session = _session_for_crud(c)
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.delete(f"/api/v1/hub/clients/{DEV_CLIENT_ID}")
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_async_session, None)

    def test_returns_404_for_unknown_id(self, client):
        session = _session_for_crud(None)
        app.dependency_overrides[get_async_session] = _override_session(session)
        try:
            resp = client.delete(f"/api/v1/hub/clients/{uuid.uuid4()}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_async_session, None)
