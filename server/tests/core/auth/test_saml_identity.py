"""Tests de provisioning JIT + mapeo de rol + emisión de JWT desde SAML (AUTH.2).

Las pruebas de ``resolve_session`` y el ACS completo usan el PostgreSQL de desarrollo
(fixture ``db`` de ``conftest.py``, que limpia las filas creadas).
"""

import uuid

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


def _uid() -> str:
    return uuid.uuid4().hex[:12]


# --------------------------------------------------------------------------- #
# resolve_role (puro, sin BD)                                                   #
# --------------------------------------------------------------------------- #
def test_resolve_role_explicit_attribute(saml_ctx):
    from server.app.core.auth.saml.role_mapping import resolve_role

    assert resolve_role({"role": ["admin"]}) == "admin"


def test_resolve_role_from_group_map(saml_ctx, monkeypatch):
    from server.app.core.auth.saml.role_mapping import resolve_role

    monkeypatch.setenv("SAML_GROUP_ROLE_MAP", '{"pas-informatica": "admin"}')
    assert resolve_role({"groups": ["pas-informatica"]}) == "admin"


def test_resolve_role_default_when_nothing(saml_ctx):
    from server.app.core.auth.saml.role_mapping import resolve_role

    assert resolve_role({}) == "user"  # SAML_DEFAULT_ROLE


def test_resolve_role_precedence_superadmin_over_admin(saml_ctx, monkeypatch):
    from server.app.core.auth.saml.role_mapping import resolve_role

    monkeypatch.setenv(
        "SAML_GROUP_ROLE_MAP",
        '{"grupo-super": "superadmin", "grupo-admin": "admin"}',
    )
    role = resolve_role({"groups": ["grupo-admin", "grupo-super"]})
    assert role == "superadmin"


# --------------------------------------------------------------------------- #
# resolve_session (BD)                                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_resolve_session_known_superadmin(saml_ctx, db):
    from server.app.core.auth.saml.identity_service import SamlIdentityService
    from server.app.database.models import SuperAdminAccount
    from server.app.modules.agents_hub.database.config_models import HubSsoUser
    from sqlalchemy import select

    email = f"superadmin-{_uid()}@uji.es"
    db.track(email)
    db.session.add(
        SuperAdminAccount(name="SuperAdmin Test", email=email, hashed_password="x", is_active=True)
    )
    await db.session.commit()

    info = await SamlIdentityService(db.session).resolve_session(
        nameid=email, attributes={"mail": [email]}
    )
    assert info.role == "superadmin"
    assert info.email == email
    # No se crea HubSsoUser para una cuenta superadmin existente.
    sso = (
        await db.session.execute(select(HubSsoUser).where(HubSsoUser.email == email))
    ).scalars().first()
    assert sso is None


@pytest.mark.asyncio
async def test_resolve_session_known_admin(saml_ctx, db):
    from server.app.core.auth.saml.identity_service import SamlIdentityService
    from server.app.database.models import AdminAccount

    email = f"admin-{_uid()}@uji.es"
    db.track(email)
    db.session.add(
        AdminAccount(partner_id=f"p-{_uid()}", name="Admin Test", email=email)
    )
    await db.session.commit()

    info = await SamlIdentityService(db.session).resolve_session(
        nameid=email, attributes={"mail": [email]}
    )
    assert info.role == "admin"
    assert info.email == email


@pytest.mark.asyncio
async def test_resolve_session_jit_provision_with_group_role(saml_ctx, db, monkeypatch):
    from server.app.core.auth.saml.identity_service import SamlIdentityService
    from server.app.modules.agents_hub.database.config_models import HubSsoUser
    from sqlalchemy import select

    monkeypatch.setenv("SAML_GROUP_ROLE_MAP", '{"pas-info": "admin"}')
    email = f"jit-{_uid()}@uji.es"
    db.track(email)

    info = await SamlIdentityService(db.session).resolve_session(
        nameid=email,
        attributes={
            "mail": [email],
            "displayName": ["JIT User"],
            "groups": ["pas-info"],
        },
    )
    assert info.role == "admin"
    sso = (
        await db.session.execute(select(HubSsoUser).where(HubSsoUser.email == email))
    ).scalars().first()
    assert sso is not None
    assert sso.role == "admin"
    assert sso.display_name == "JIT User"


@pytest.mark.asyncio
async def test_resolve_session_jit_default_role(saml_ctx, db):
    from server.app.core.auth.saml.identity_service import SamlIdentityService

    email = f"jit-{_uid()}@uji.es"
    db.track(email)
    info = await SamlIdentityService(db.session).resolve_session(
        nameid=email, attributes={"mail": [email]}
    )
    assert info.role == "user"


@pytest.mark.asyncio
async def test_resolve_session_second_login_no_duplicate(saml_ctx, db):
    from server.app.core.auth.saml.identity_service import SamlIdentityService
    from server.app.modules.agents_hub.database.config_models import HubSsoUser
    from sqlalchemy import func, select

    email = f"jit-{_uid()}@uji.es"
    db.track(email)
    service = SamlIdentityService(db.session)
    await service.resolve_session(nameid=email, attributes={"mail": [email]})
    await service.resolve_session(nameid=email, attributes={"mail": [email]})

    count = (
        await db.session.execute(
            select(func.count()).select_from(HubSsoUser).where(HubSsoUser.email == email)
        )
    ).scalar_one()
    assert count == 1
    sso = (
        await db.session.execute(select(HubSsoUser).where(HubSsoUser.email == email))
    ).scalars().first()
    assert sso.last_login_at is not None


@pytest.mark.asyncio
async def test_resolve_session_missing_email_raises(saml_ctx, db):
    from server.app.core.auth.saml.identity_service import (
        SamlIdentityService,
        SamlMissingEmailError,
    )

    with pytest.raises(SamlMissingEmailError):
        await SamlIdentityService(db.session).resolve_session(
            nameid="no-email", attributes={"displayName": ["No Email"]}
        )


# --------------------------------------------------------------------------- #
# ACS completo: aserción firmada → JWT → redirect                               #
# --------------------------------------------------------------------------- #
def test_acs_issues_jwt_and_redirects(saml_ctx, db):
    import os

    from sqlalchemy.ext.asyncio import create_async_engine

    from server.app.api.deps import get_session
    from server.app.core.auth import decode_token
    from server.app.routers.saml_auth_router import router
    from sqlmodel.ext.asyncio.session import AsyncSession

    email = f"ada-{_uid()}@uji.es"
    db.track(email)  # el fixture db limpia esta fila en el teardown

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai",
    )

    async def _override_session():
        # Engine creado dentro del request → vive en el loop del TestClient.
        eng = create_async_engine(database_url)
        try:
            async with AsyncSession(eng) as s:
                yield s
        finally:
            await eng.dispose()

    app = FastAPI()
    app.dependency_overrides[get_session] = _override_session
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app, base_url=saml_ctx.base_url)

    saml_response = saml_ctx.make_response(
        email=email, attributes={"mail": [email], "displayName": ["Ada Lovelace"]}
    )
    resp = client.post(
        "/api/v1/auth/saml/acs",
        data={"SAMLResponse": saml_response},
        follow_redirects=False,
    )
    assert resp.status_code == 302, resp.text
    location = resp.headers["location"]
    assert location.startswith(saml_ctx.return_url + "#token=")

    token = location.split("#token=", 1)[1]
    info = decode_token(token)
    assert info.email == email
    assert info.role == "user"
