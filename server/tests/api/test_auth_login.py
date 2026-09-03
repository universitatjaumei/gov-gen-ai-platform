"""Tests TDD — El login de Admin exige contraseña (Prompt SEC.1, hallazgo A1).

**El agujero**: `/auth/admin/login` emitía un JWT comprobando solo que el email existiera y la
cuenta estuviera activa. `AdminAccount` ni siquiera tenía campo de hash, así que no era un
descuido de una rama: no había nada contra lo que comparar. Cualquiera que conociera un email
de administrador entraba con la contraseña que quisiera.

Dos invariantes menos obvios que la verificación en sí:

- **Una cuenta sin hash no entra.** El backfill de la migración deja NULL, y NULL tiene que
  significar «login local deshabilitado, usa SSO o pide a un superadmin que te la fije», no
  «pasa sin comprobar». Es el mismo bug de nuevo si se resuelve mal.
- **El error no distingue entre cuenta inexistente y contraseña incorrecta.** Si lo hiciera,
  el formulario de login se convierte en un oráculo para enumerar administradores.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from server.app.core.security import hash_password
from server.app.database.models import AdminAccount, SuperAdminAccount
from server.app.main import app
from server.app.api.deps import get_session

PASSWORD = "C0ntrasenya-de-prova!"


def _admin(*, con_password: bool = True, activo: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        partner_id="partner_dev",
        name="Admin Desarrollo",
        email="admin@uji.es",
        hashed_password=hash_password(PASSWORD) if con_password else None,
        credits_balance=0,
        is_active=activo,
    )


def _sesion(*, admin=None, superadmin=None):
    """Sesión falsa que devuelve la cuenta según lo que se consulte."""
    session = MagicMock()

    resultado = MagicMock()
    # El login de superadmin lee con `.first()`; el de Admin, con `.one_or_none()` desde USR.5
    # —`adminaccount.email` es único, así que dos filas son un error y no algo que desempatar—.
    # **Los dos tienen que estar puestos**: un doble que sólo ofrece uno devuelve un `MagicMock`
    # por el otro, y entonces `verify_password` compara contra un mock y el test falla con un
    # 401 que parece de la lógica y es del andamio.
    cuenta = admin if admin is not None else superadmin
    resultado.first = MagicMock(return_value=cuenta)
    resultado.one_or_none = MagicMock(return_value=cuenta)
    resultado.scalar_one_or_none = MagicMock(return_value=superadmin)
    resultado.scalars.return_value.all.return_value = []

    async def _exec(stmt, *args, **kwargs):
        return resultado

    session.exec = AsyncMock(side_effect=_exec)
    session.execute = AsyncMock(side_effect=_exec)
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _override(session):
    async def _dep():
        yield session
    return _dep


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _login(client, session, password: str | None):
    cuerpo: dict = {"email": "admin@uji.es"}
    if password is not None:
        cuerpo["password"] = password
    app.dependency_overrides[get_session] = _override(session)
    try:
        return client.post("/api/v1/auth/admin/login", json=cuerpo)
    finally:
        app.dependency_overrides.pop(get_session, None)


class TestLoginDeAdmin:

    def test_should_reject_admin_login_without_password_field(self, client):
        """Regresión del bug A1: sin contraseña no se emite token."""
        resp = _login(client, _sesion(admin=_admin()), None)

        assert resp.status_code in (401, 422), resp.text
        assert "access_token" not in resp.text

    def test_should_reject_admin_login_with_wrong_password(self, client):
        resp = _login(client, _sesion(admin=_admin()), "la-que-no-es")

        assert resp.status_code == 401
        assert "access_token" not in resp.text

    def test_should_accept_admin_login_with_correct_password(self, client):
        resp = _login(client, _sesion(admin=_admin()), PASSWORD)

        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"]

    def test_should_reject_admin_with_null_hashed_password(self, client):
        """NULL significa «login local deshabilitado», nunca «pasa sin comprobar»."""
        resp = _login(client, _sesion(admin=_admin(con_password=False)), PASSWORD)

        assert resp.status_code == 401
        assert "access_token" not in resp.text

    def test_should_reject_inactive_admin(self, client):
        resp = _login(client, _sesion(admin=_admin(activo=False)), PASSWORD)

        assert resp.status_code == 401

    def test_should_return_identical_error_for_unknown_and_wrong_password(self, client):
        """El login no puede servir para enumerar administradores."""
        desconocida = _login(client, _sesion(admin=None), PASSWORD)
        equivocada = _login(client, _sesion(admin=_admin()), "la-que-no-es")

        assert desconocida.status_code == equivocada.status_code == 401
        assert desconocida.json() == equivocada.json()


class TestModeloDeCuenta:

    def test_should_declare_a_password_hash_column(self):
        """Sin columna no hay nada que verificar: es la raíz del hallazgo A1."""
        assert "hashed_password" in AdminAccount.model_fields

    def test_should_allow_null_hash_for_sso_only_accounts(self):
        """Las cuentas que ya existían no tienen hash y no se les puede inventar uno."""
        campo = AdminAccount.model_fields["hashed_password"]
        assert campo.default is None or campo.is_required() is False

    def test_should_hash_and_never_store_the_plain_password(self):
        cuenta = AdminAccount(
            partner_id="p1",
            name="X",
            email="x@uji.es",
            hashed_password=hash_password(PASSWORD),
        )
        assert PASSWORD not in (cuenta.hashed_password or "")
        assert cuenta.hashed_password.startswith("$2b$")


class TestFijarContrasena:
    """Un superadmin puede fijar la contraseña de un admin; nadie más."""

    def test_should_let_superadmin_set_an_admin_password(self, client):
        from server.app.api.deps import get_current_user
        from server.app.core.auth.models import UserInfo

        cuenta = _admin(con_password=False)
        session = _sesion(admin=cuenta)
        session.get = AsyncMock(return_value=cuenta)
        app.dependency_overrides[get_current_user] = lambda: UserInfo(
            user_id="1", email="root@uji.es", role="superadmin"
        )
        app.dependency_overrides[get_session] = _override(session)
        try:
            resp = client.patch(
                "/api/v1/auth/admins/partner_dev/password",
                json={"password": "Una-Nova-Contrasenya!1"},
            )
            assert resp.status_code == 204, resp.text
            assert cuenta.hashed_password is not None
            assert cuenta.hashed_password.startswith("$2b$")
        finally:
            app.dependency_overrides.clear()

    def test_should_forbid_an_admin_from_setting_passwords(self, client):
        from server.app.api.deps import get_current_user
        from server.app.core.auth.models import UserInfo

        session = _sesion(admin=_admin())
        app.dependency_overrides[get_current_user] = lambda: UserInfo(
            user_id="2", email="admin@uji.es", role="admin"
        )
        app.dependency_overrides[get_session] = _override(session)
        try:
            resp = client.patch(
                "/api/v1/auth/admins/partner_dev/password",
                json={"password": "Una-Nova-Contrasenya!1"},
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()


class TestSuperadminSigueIgual:

    def test_should_not_break_superadmin_login(self, client):
        cuenta = SimpleNamespace(
            admin_id=1,
            name="Root",
            email="root@uji.es",
            hashed_password=hash_password(PASSWORD),
            is_active=True,
        )
        app.dependency_overrides[get_session] = _override(
            _sesion(superadmin=cuenta)
        )
        try:
            resp = client.post(
                "/api/v1/auth/superadmin/login",
                json={"email": "root@uji.es", "password": PASSWORD},
            )
            assert resp.status_code == 200, resp.text
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_should_keep_superadmin_model_untouched(self):
        assert "hashed_password" in SuperAdminAccount.model_fields
        assert uuid.UUID  # el import de uuid se usa aquí solo para el lint
