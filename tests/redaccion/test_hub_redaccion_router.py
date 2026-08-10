"""hub_redaccion_router: SuperAdmin/Admin no revientan con 500 (hallazgo #2 de MAN.2).

`GET /hub/redaccion/templates` y 5 sitios mas usaban uuid.UUID(user.user_id) directo.
SuperAdminAccount.admin_id es int y AdminAccount.partner_id es texto libre: ninguno de
los dos es UUID, asi que cualquier sesion de SuperAdmin/Admin lo reventaba con 500.
El fix reutiliza el _actor.user_to_uuid ya existente (uuid5 determinista) que
llm_drafts_router.py y scripts_router.py ya aplicaban para el mismo problema.

Tests RED -> GREEN. TestClient + dependency overrides; sin BD real.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.main import app
from server.app.routers.redaccion import hub_redaccion_router as router_module

# user_id no-UUID: SuperAdminAccount.admin_id es int, AdminAccount.partner_id es texto libre
_SUPERADMIN_NON_UUID = UserInfo(user_id="42", email="root@test.com", role="superadmin")
_ADMIN_NON_UUID = UserInfo(user_id="org-uji", email="admin@test.com", role="admin")


def _mock_session():
    session = MagicMock()

    def _add(obj):
        # Simula los default= de las columnas (uuid.uuid4 / _now): en un flush real
        # contra un engine los asigna SQLAlchemy; aqui el flush esta mockeado y no
        # hace nada, y TemplateOut/WorkspaceCreatedOut exigen id/created_at no nulos.
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)

    session.add = MagicMock(side_effect=_add)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


def _session_dep(session):
    async def _gen():
        yield session
    return _gen


def _empty_scalars_result():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    return result


@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


class TestListTemplatesNonUuidUserId:
    def test_superadmin_with_non_uuid_user_id_gets_200_not_500(self, client):
        session = _mock_session()
        session.execute = AsyncMock(return_value=_empty_scalars_result())
        app.dependency_overrides[get_current_user] = lambda: _SUPERADMIN_NON_UUID
        app.dependency_overrides[get_session] = _session_dep(session)

        resp = client.get("/api/v1/hub/redaccion/templates")

        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateTemplateNonUuidUserId:
    def test_admin_with_non_uuid_user_id_gets_201_not_500(self, client):
        session = _mock_session()
        app.dependency_overrides[get_current_user] = lambda: _ADMIN_NON_UUID
        app.dependency_overrides[get_session] = _session_dep(session)

        resp = client.post(
            "/api/v1/hub/redaccion/templates",
            json={"name": "Informe MAN.2"},
        )

        assert resp.status_code == 201
        assert resp.json()["name"] == "Informe MAN.2"


class TestCreateWorkspaceNonUuidUserId:
    def test_superadmin_with_non_uuid_user_id_gets_201_not_500(self, client):
        session = _mock_session()
        session.get = AsyncMock(return_value=MagicMock())  # version existente
        app.dependency_overrides[get_current_user] = lambda: _SUPERADMIN_NON_UUID
        app.dependency_overrides[get_session] = _session_dep(session)

        resp = client.post(
            "/api/v1/hub/redaccion/workspaces",
            json={"template_version_id": str(uuid.uuid4())},
        )

        assert resp.status_code == 201
        assert "workspace_id" in resp.json()


class TestMigrateWorkspaceNonUuidUserId:
    def test_admin_with_non_uuid_user_id_does_not_500(self, client, monkeypatch):
        fake_new_workspace = MagicMock(id=uuid.uuid4())
        mock_service = MagicMock()
        mock_service.migrate_workspace = AsyncMock(return_value=fake_new_workspace)
        monkeypatch.setattr(
            router_module, "TemplateMigrationService", MagicMock(return_value=mock_service)
        )

        session = _mock_session()
        app.dependency_overrides[get_current_user] = lambda: _ADMIN_NON_UUID
        app.dependency_overrides[get_session] = _session_dep(session)

        workspace_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/hub/redaccion/workspaces/{workspace_id}/migrate",
            json={"target_version_id": str(uuid.uuid4())},
        )

        assert resp.status_code == 201
        assert resp.json()["new_workspace_id"] == str(fake_new_workspace.id)

        # El actor pasado al servicio es una UUID real: uuid.UUID("org-uji") habria
        # lanzado ValueError antes de llegar aqui.
        called_actor = mock_service.migrate_workspace.call_args.args[2]
        assert isinstance(called_actor, uuid.UUID)


class TestPublishTemplateVersionNonUuidUserId:
    def test_superadmin_with_non_uuid_user_id_gets_201_not_500(self, client, monkeypatch):
        session = _mock_session()
        fake_template = MagicMock()
        session.get = AsyncMock(return_value=fake_template)
        session.execute = AsyncMock(return_value=_empty_scalars_result())
        monkeypatch.setattr(
            router_module.ReportTemplateSpec,
            "model_validate",
            staticmethod(lambda spec_json: None),
        )

        app.dependency_overrides[get_current_user] = lambda: _SUPERADMIN_NON_UUID
        app.dependency_overrides[get_session] = _session_dep(session)

        template_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/hub/redaccion/templates/{template_id}/versions",
            json={"spec_json": {}},
        )

        assert resp.status_code == 201
        assert resp.json()["published"] is True
