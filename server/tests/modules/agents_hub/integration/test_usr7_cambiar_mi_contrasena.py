"""USR.7 — cambiar la propia contraseña, que no existía en ningún rol.

Lo decía el docstring de `set_admin_password`: «cambiar la contraseña propia exige conocer la
anterior, y ese flujo no es este prompt». La consecuencia se vio el 2026-09-01: las seis cuentas
del piloto se crearon con **la misma** contraseña y ninguno de sus dueños podía cambiarla, así
que cualquiera de los seis podía entrar como otro y la atribución de las valoraciones valía lo
que valiera ese secreto compartido.

Cuatro cosas que este endpoint tiene que hacer bien, y que son los tests de abajo:

1. **Exigir la actual siempre**, también a un superadministrador. Es lo que impide que una
   sesión robada se quede la cuenta: con el token basta para actuar, pero no para cambiar la
   llave.
2. **Una sola ruta para las tres clases de identidad** con login local. Tres endpoints serían
   tres sitios donde olvidarse de una de las cuatro cosas.
3. **Limitar los intentos**, porque si no es un oráculo para adivinar la contraseña actual a
   ritmo de red — y esta vez con el token ya en la mano.
4. **La vieja deja de servir y la nueva sirve.** Se comprueba entrando, no leyendo el hash.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import server.app.main  # noqa: F401

from server.app.api.deps import get_current_user, get_session
from server.app.core.security import hash_password
from server.app.modules.agents_hub.database.config_models import HubUser
from server.app.routers.auth_router import router

VIEJA = "La-contrasena-vieja-2026"
NUEVA = "La-contrasena-nueva-2026"


@pytest.fixture(autouse=True)
def _sin_cupo_gastado():
    from server.app.core.rate_limit import limitador

    limitador.reiniciar()
    yield
    limitador.reiniciar()


@pytest.fixture(autouse=True)
async def _tablas_de_cuenta(db_session):
    from sqlmodel import SQLModel

    import server.app.database.models  # noqa: F401

    conexion = await db_session.connection()
    await conexion.run_sync(SQLModel.metadata.create_all)
    await db_session.commit()


async def _sesion_como_en_produccion(db_session):
    from sqlmodel.ext.asyncio.session import AsyncSession as SesionSQLModel

    return SesionSQLModel(bind=await db_session.connection())


def _cliente(session, principal=None) -> AsyncClient:
    async def _sesion():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_session] = _sesion
    if principal is not None:
        app.dependency_overrides[get_current_user] = lambda: principal
    app.include_router(router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Las tres clases de identidad, cada una sembrada como es ──────────────────────────────


async def _persona(db_session, role: str = "user") -> HubUser:
    fila = HubUser(
        id=uuid.uuid4(),
        email=f"persona-{uuid.uuid4().hex[:8]}@uji.es",
        role=role,
        organizacion_id=None,
        is_active=True,
        origen="manual",
        hashed_password=hash_password(VIEJA),
    )
    db_session.add(fila)
    await db_session.flush()
    return fila


async def _superadmin_de_arranque(db_session):
    from server.app.database.models import SuperAdminAccount

    fila = SuperAdminAccount(
        email=f"root-{uuid.uuid4().hex[:8]}@uji.es",
        name="Arranque",
        hashed_password=hash_password(VIEJA),
        is_active=True,
    )
    db_session.add(fila)
    await db_session.flush()
    return fila


async def _admin_de_partner(db_session):
    from server.app.database.models import AdminAccount

    fila = AdminAccount(
        partner_id=f"p-{uuid.uuid4().hex[:10]}",
        name="Administración de partner",
        email=f"admin-{uuid.uuid4().hex[:8]}@uji.es",
        hashed_password=hash_password(VIEJA),
    )
    db_session.add(fila)
    await db_session.flush()
    return fila


def _principal_de(user_id: str, email: str, role: str):
    from server.app.core.auth.models import UserInfo

    return UserInfo(user_id=user_id, email=email, role=role)


async def _cambia(db_session, principal, actual=VIEJA, nueva=NUEVA):
    async with _cliente(await _sesion_como_en_produccion(db_session), principal) as c:
        return await c.post(
            "/api/v1/auth/me/password",
            json={"password_actual": actual, "password_nueva": nueva},
        )


async def _entra_como_persona(db_session, email: str, password: str):
    async with _cliente(await _sesion_como_en_produccion(db_session)) as c:
        return await c.post(
            "/api/v1/auth/user/login", json={"email": email, "password": password}
        )


class TestLaPersona:

    async def test_should_change_it_knowing_the_current_one(self, db_session):
        persona = await _persona(db_session)
        principal = _principal_de(str(persona.id), persona.email, "user")

        r = await _cambia(db_session, principal)

        assert r.status_code == 204, r.text

    async def test_should_make_the_old_one_stop_working_and_the_new_one_work(self, db_session):
        """Se comprueba entrando, no leyendo el hash."""
        persona = await _persona(db_session)
        principal = _principal_de(str(persona.id), persona.email, "user")

        await _cambia(db_session, principal)

        vieja = await _entra_como_persona(db_session, persona.email, VIEJA)
        nueva = await _entra_como_persona(db_session, persona.email, NUEVA)
        assert vieja.status_code == 401, "la contraseña vieja sigue sirviendo"
        assert nueva.status_code == 200, nueva.text

    async def test_should_refuse_a_wrong_current_password(self, db_session):
        persona = await _persona(db_session)
        principal = _principal_de(str(persona.id), persona.email, "user")

        r = await _cambia(db_session, principal, actual="la-que-no-es")

        assert r.status_code == 401, r.text

    async def test_should_refuse_a_new_password_shorter_than_the_contract(self, db_session):
        persona = await _persona(db_session)
        principal = _principal_de(str(persona.id), persona.email, "user")

        r = await _cambia(db_session, principal, nueva="corta")

        assert r.status_code == 422, r.text

    async def test_should_refuse_when_there_is_no_local_login(self, db_session):
        """`hashed_password` NULL sigue siendo «login local deshabilitado», también aquí."""
        persona = await _persona(db_session)
        persona.hashed_password = None
        await db_session.flush()
        principal = _principal_de(str(persona.id), persona.email, "user")

        r = await _cambia(db_session, principal)

        assert r.status_code == 401, r.text


class TestElSuperadministrador:
    """Sin excepción por ser quien es: es lo que impide que una sesión robada se quede la cuenta."""

    async def test_should_also_be_asked_for_the_current_one(self, db_session):
        cuenta = await _superadmin_de_arranque(db_session)
        principal = _principal_de(str(cuenta.admin_id), cuenta.email, "superadmin")

        malo = await _cambia(db_session, principal, actual="la-que-no-es")
        bueno = await _cambia(db_session, principal)

        assert malo.status_code == 401, malo.text
        assert bueno.status_code == 204, bueno.text

    async def test_should_change_the_stored_hash(self, db_session):
        from server.app.core.security import verify_password

        cuenta = await _superadmin_de_arranque(db_session)
        principal = _principal_de(str(cuenta.admin_id), cuenta.email, "superadmin")

        await _cambia(db_session, principal)

        await db_session.refresh(cuenta)
        assert verify_password(NUEVA, cuenta.hashed_password)
        assert not verify_password(VIEJA, cuenta.hashed_password)


class TestElAdministradorDePartner:
    """La tercera clase, la que sigue existiendo mientras (b) no se complete (USR.6)."""

    async def test_should_change_its_own_password(self, db_session):
        from server.app.core.security import verify_password

        cuenta = await _admin_de_partner(db_session)
        principal = _principal_de(cuenta.partner_id, cuenta.email, "admin")

        r = await _cambia(db_session, principal)

        assert r.status_code == 204, r.text
        await db_session.refresh(cuenta)
        assert verify_password(NUEVA, cuenta.hashed_password)


class TestNoEsUnOraculo:

    async def test_should_rate_limit_this_route_too(self, db_session, monkeypatch):
        """Con el token en la mano, sin límite esto es adivinar la actual a ritmo de red."""
        import server.app.routers.auth_router as modulo

        llamadas: list[int] = []
        monkeypatch.setattr(modulo, "limitar_login", lambda request: llamadas.append(1))

        persona = await _persona(db_session)
        principal = _principal_de(str(persona.id), persona.email, "user")
        await _cambia(db_session, principal)

        assert llamadas, "`limitar_login` no se llama en el cambio de contraseña propia"

    async def test_should_answer_the_same_401_for_wrong_and_for_no_hash(self, db_session):
        """Distinguirlos diría si la cuenta tiene login local, que no es asunto de quien prueba."""
        con_hash = await _persona(db_session)
        sin_hash = await _persona(db_session)
        sin_hash.hashed_password = None
        await db_session.flush()

        mala = await _cambia(
            db_session,
            _principal_de(str(con_hash.id), con_hash.email, "user"),
            actual="la-que-no-es",
        )
        sin = await _cambia(
            db_session, _principal_de(str(sin_hash.id), sin_hash.email, "user")
        )

        assert mala.status_code == sin.status_code == 401
        assert mala.json() == sin.json(), f"{mala.json()} != {sin.json()}"

    async def test_should_never_return_anything_of_the_hash(self, db_session):
        persona = await _persona(db_session)
        principal = _principal_de(str(persona.id), persona.email, "user")

        r = await _cambia(db_session, principal)

        assert r.status_code == 204
        assert not r.content, f"el 204 trae cuerpo: {r.content!r}"
