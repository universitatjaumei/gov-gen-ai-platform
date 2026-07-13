"""Tests MCP.2 (backend) — endpoints de autoría de plantillas.

Cubren los 3 endpoints nuevos de hub_redaccion_router que alimentan las tools MCP:
GET /template-schema, GET /template-versions/{id} y POST /templates/{id}/versions
(publicación append-only con dry_run). Sesión mockeada (AsyncMock), sin BD real.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.profiles.generic_report import GenericReportProfile
from server.app.routers.redaccion.hub_redaccion_router import router as hub_redaccion_router

_OWNER_ID = uuid.uuid4()


def _valid_spec_json() -> dict:
    """Spec válida garantizada (perfil GENERIC_REPORT)."""
    return GenericReportProfile().default_spec().model_dump(mode="json")


def _build_app(session_mock: AsyncMock, *, role: str = "admin") -> FastAPI:
    async def _override_session():
        yield session_mock

    async def _override_user():
        return UserInfo(user_id=str(_OWNER_ID), email="t@example.com", role=role)

    app = FastAPI()
    app.include_router(hub_redaccion_router, prefix="/api/v1")
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_user
    return app


def _exec_result(rows: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


# ---------------------------------------------------------------------------
# GET /template-schema
# ---------------------------------------------------------------------------

def test_template_schema_returns_json_schema():
    app = _build_app(AsyncMock(), role="user")
    with TestClient(app) as client:
        resp = client.get("/api/v1/hub/redaccion/template-schema")

    assert resp.status_code == 200, resp.text
    schema = resp.json()
    assert "properties" in schema
    # Campos clave de ReportTemplateSpec presentes en el contrato.
    for field in ("sections", "blocks", "input_contract", "ui_contract"):
        assert field in schema["properties"]
    assert "$defs" in schema


# ---------------------------------------------------------------------------
# GET /template-versions/{id}
# ---------------------------------------------------------------------------

def test_get_template_version_returns_spec():
    version_id = uuid.uuid4()
    template_id = uuid.uuid4()
    spec = _valid_spec_json()

    version_mock = MagicMock()
    version_mock.id = version_id
    version_mock.template_id = template_id
    version_mock.version = 3
    version_mock.spec_json = spec

    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=version_mock)

    app = _build_app(session_mock, role="user")
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/hub/redaccion/template-versions/{version_id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == 3
    assert body["template_id"] == str(template_id)
    assert body["spec"] == spec


def test_get_template_version_404():
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=None)

    app = _build_app(session_mock, role="user")
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/hub/redaccion/template-versions/{uuid.uuid4()}")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /templates/{id}/versions  (publish append-only + dry_run)
# ---------------------------------------------------------------------------

def test_publish_dry_run_validates_without_persisting():
    template_id = uuid.uuid4()
    existing = MagicMock()
    existing.version = 1

    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=MagicMock())  # template existe
    session_mock.execute = AsyncMock(return_value=_exec_result([existing]))
    session_mock.add = MagicMock()
    session_mock.commit = AsyncMock()

    app = _build_app(session_mock, role="admin")
    with TestClient(app) as client:
        resp = client.post(
            f"/api/v1/hub/redaccion/templates/{template_id}/versions",
            params={"dry_run": "true"},
            json={"spec_json": _valid_spec_json()},
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["published"] is False
    assert body["version"] == 2  # siguiente a la v1 existente
    assert body["version_id"] is None
    session_mock.add.assert_not_called()
    session_mock.commit.assert_not_called()


def test_publish_appends_new_version():
    template_id = uuid.uuid4()
    existing = MagicMock()
    existing.version = 1

    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=MagicMock())
    session_mock.execute = AsyncMock(return_value=_exec_result([existing]))
    session_mock.add = MagicMock()
    session_mock.flush = AsyncMock()
    session_mock.commit = AsyncMock()

    app = _build_app(session_mock, role="admin")
    with TestClient(app) as client:
        resp = client.post(
            f"/api/v1/hub/redaccion/templates/{template_id}/versions",
            json={"spec_json": _valid_spec_json()},
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["published"] is True
    assert body["version"] == 2
    assert body["version_id"] is not None
    session_mock.add.assert_called_once()
    session_mock.commit.assert_called_once()


def test_publish_first_version_when_no_existing():
    template_id = uuid.uuid4()
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=MagicMock())
    session_mock.execute = AsyncMock(return_value=_exec_result([]))
    session_mock.add = MagicMock()
    session_mock.flush = AsyncMock()
    session_mock.commit = AsyncMock()

    app = _build_app(session_mock, role="admin")
    with TestClient(app) as client:
        resp = client.post(
            f"/api/v1/hub/redaccion/templates/{template_id}/versions",
            json={"spec_json": _valid_spec_json()},
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["version"] == 1


def test_publish_invalid_spec_returns_422():
    template_id = uuid.uuid4()
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=MagicMock())  # template existe

    app = _build_app(session_mock, role="admin")
    with TestClient(app) as client:
        resp = client.post(
            f"/api/v1/hub/redaccion/templates/{template_id}/versions",
            json={"spec_json": {"sections": "not-a-list"}},
        )

    assert resp.status_code == 422, resp.text


def test_publish_template_not_found_404():
    session_mock = AsyncMock()
    session_mock.get = AsyncMock(return_value=None)  # template no existe

    app = _build_app(session_mock, role="admin")
    with TestClient(app) as client:
        resp = client.post(
            f"/api/v1/hub/redaccion/templates/{uuid.uuid4()}/versions",
            json={"spec_json": _valid_spec_json()},
        )

    assert resp.status_code == 404
