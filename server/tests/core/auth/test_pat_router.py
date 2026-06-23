"""Tests del router de PAT (AUTH.3): /auth/pats create/list/revoke.

Async + httpx.AsyncClient para compartir event loop con el fixture ``db``. El owner se
autentica con un JWT real (create_token); el router resuelve la identidad vía
get_current_user y delega en PatService con la sesión inyectada.
"""

import uuid

import httpx
import pytest
from fastapi import FastAPI


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _app(db):
    from server.app.api.deps import get_session
    from server.app.routers.pat_router import router
    from sqlmodel.ext.asyncio.session import AsyncSession

    async def _override_session():
        async with AsyncSession(db.engine) as s:
            yield s

    app = FastAPI()
    app.dependency_overrides[get_session] = _override_session
    app.include_router(router, prefix="/api/v1")
    return app


def _client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


def _headers(role: str, email: str):
    from server.app.core.auth import create_token
    from server.app.core.auth.models import UserInfo

    token = create_token(UserInfo(user_id=f"{role}-{_uid()}", email=email, role=role))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_pat_returns_token_once(db):
    email = f"admin-{_uid()}@uji.es"
    db.track(email)
    async with _client(_app(db)) as client:
        resp = await client.post(
            "/api/v1/auth/pats",
            json={"name": "mcp", "scopes": ["redaccion:templates:read"]},
            headers=_headers("admin", email),
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["token"].startswith("pat_")
    assert body["token_prefix"] in body["token"]
    assert body["scopes"] == ["redaccion:templates:read"]


@pytest.mark.asyncio
async def test_create_pat_forbidden_for_user_role(db):
    email = f"user-{_uid()}@uji.es"
    db.track(email)
    async with _client(_app(db)) as client:
        resp = await client.post(
            "/api/v1/auth/pats",
            json={"name": "mcp", "scopes": ["chatbots:read"]},
            headers=_headers("user", email),
        )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PAT_FORBIDDEN"


@pytest.mark.asyncio
async def test_create_pat_unknown_scope_422(db):
    email = f"admin-{_uid()}@uji.es"
    db.track(email)
    async with _client(_app(db)) as client:
        resp = await client.post(
            "/api/v1/auth/pats",
            json={"name": "mcp", "scopes": ["bogus:scope"]},
            headers=_headers("admin", email),
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "UNKNOWN_SCOPE"


@pytest.mark.asyncio
async def test_list_pats_never_exposes_secret(db):
    email = f"admin-{_uid()}@uji.es"
    db.track(email)
    headers = _headers("admin", email)
    async with _client(_app(db)) as client:
        await client.post(
            "/api/v1/auth/pats",
            json={"name": "mcp", "scopes": ["chatbots:read"]},
            headers=headers,
        )
        resp = await client.get("/api/v1/auth/pats", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    for item in items:
        assert "token" not in item
        assert "token_hash" not in item
        assert item["token_prefix"]


@pytest.mark.asyncio
async def test_revoke_pat(db):
    email = f"admin-{_uid()}@uji.es"
    db.track(email)
    headers = _headers("admin", email)
    async with _client(_app(db)) as client:
        created = await client.post(
            "/api/v1/auth/pats",
            json={"name": "mcp", "scopes": ["chatbots:read"]},
            headers=headers,
        )
        pat_id = created.json()["id"]
        resp = await client.delete(f"/api/v1/auth/pats/{pat_id}", headers=headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_revoke_other_owner_404(db):
    email_a = f"admin-{_uid()}@uji.es"
    email_b = f"admin-{_uid()}@uji.es"
    db.track(email_a)
    db.track(email_b)
    async with _client(_app(db)) as client:
        created = await client.post(
            "/api/v1/auth/pats",
            json={"name": "mcp", "scopes": ["chatbots:read"]},
            headers=_headers("admin", email_a),
        )
        pat_id = created.json()["id"]
        resp = await client.delete(
            f"/api/v1/auth/pats/{pat_id}", headers=_headers("admin", email_b)
        )
    assert resp.status_code == 404
