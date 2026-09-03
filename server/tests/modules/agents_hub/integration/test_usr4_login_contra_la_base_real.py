"""USR.4 — el login de la persona, contra la base de datos de verdad.

**Por qué existe este fichero, que es la lección del prompt.** Los tests de USR.2
(`tests/api/test_usr2_login_de_persona.py`) doblan la sesión con un `MagicMock`, y con eso
comprueban muy bien las tres defensas —el orden del límite, el hash señuelo, el 401 idéntico—
pero **no pueden ver cómo se comporta el ORM**: el doble devuelve lo que se le dice y acepta
cualquier consulta. Verificando en navegador, el login de la persona devolvió **500**.

Es el mismo patrón que ya está anotado dos veces en este proyecto: un doble sin la forma del
objeto real esconde el fallo del objeto real. La diferencia aquí es que no es un cliente externo
sino **la sesión de base de datos**, que es la dependencia más doblada de todas.

Así que este fichero no repite las defensas: hace el recorrido **con la sesión real y una fila
real**, que es lo único que responde a «¿esto funciona?».
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import server.app.main  # noqa: F401

from server.app.api.deps import get_session
from server.app.core.security import hash_password
from server.app.modules.agents_hub.database.config_models import HubOrganizacion, HubUser
from server.app.routers.auth_router import router

PASSWORD = "Probador-de-integracion-2026"


@pytest.fixture(autouse=True)
def _sin_cupo_gastado():
    """El límite del login son 10 por minuto y por IP, y este fichero entra varias veces."""
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
    """Una sesión **de SQLModel** sobre la misma conexión que la fixture.

    Importa y costó un rojo falso: `deps.get_session` yield una
    `sqlmodel.ext.asyncio.session.AsyncSession`, que tiene `.exec()`, mientras la fixture del
    hub da una `AsyncSession` de SQLAlchemy, que no. Doblar la dependencia con la de la fixture
    hacía fallar el endpoint con `AttributeError: 'AsyncSession' object has no attribute 'exec'`
    — un fallo del andamio, no del código, y que además tapaba el 500 de verdad.

    Compartiendo la conexión, las filas que crea el test se ven desde el endpoint sin
    commitear, y la clase es la de producción.
    """
    from sqlmodel.ext.asyncio.session import AsyncSession as SesionSQLModel

    return SesionSQLModel(bind=await db_session.connection())


def _cliente(session) -> AsyncClient:
    async def _sesion():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_session] = _sesion
    app.include_router(router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _persona(
    session,
    *,
    con_password: bool = True,
    activa: bool = True,
    con_organizacion: bool = True,
) -> HubUser:
    org = None
    if con_organizacion:
        org = HubOrganizacion(name="UJI", partner_id=f"p-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.flush()
    fila = HubUser(
        id=uuid.uuid4(),
        email=f"probador-{uuid.uuid4().hex[:8]}@uji.es",
        role="user",
        organizacion_id=org.id if org else None,
        is_active=activa,
        origen="manual",
        hashed_password=hash_password(PASSWORD) if con_password else None,
    )
    session.add(fila)
    await session.flush()
    return fila


class TestElRecorridoDeVerdad:

    async def test_should_let_a_real_person_in(self, db_session):
        """El caso que devolvía 500 en el navegador."""
        persona = await _persona(db_session)

        async with _cliente(await _sesion_como_en_produccion(db_session)) as c:
            r = await c.post(
                "/api/v1/auth/user/login",
                json={"email": persona.email, "password": PASSWORD},
            )

        assert r.status_code == 200, r.text
        assert r.json()["access_token"]

    async def test_should_carry_the_real_role_and_organization(self, db_session):
        persona = await _persona(db_session)

        async with _cliente(await _sesion_como_en_produccion(db_session)) as c:
            r = await c.post(
                "/api/v1/auth/user/login",
                json={"email": persona.email, "password": PASSWORD},
            )

        from server.app.core.auth import decode_token

        sesion = decode_token(r.json()["access_token"])
        assert sesion.role == "user"
        assert sesion.organizacion_ids == (str(persona.organizacion_id),)
        assert not sesion.saml_groups

    async def test_should_record_the_login_in_the_row(self, db_session):
        """`last_login_at` es lo que la pantalla de personas usa para decidir si se borra."""
        persona = await _persona(db_session)
        assert persona.last_login_at is None

        async with _cliente(await _sesion_como_en_produccion(db_session)) as c:
            await c.post(
                "/api/v1/auth/user/login",
                json={"email": persona.email, "password": PASSWORD},
            )

        await db_session.refresh(persona)
        assert persona.last_login_at is not None

    async def test_should_reject_a_real_person_without_hash(self, db_session):
        persona = await _persona(db_session, con_password=False)

        async with _cliente(await _sesion_como_en_produccion(db_session)) as c:
            r = await c.post(
                "/api/v1/auth/user/login",
                json={"email": persona.email, "password": PASSWORD},
            )

        assert r.status_code == 401, r.text

    async def test_should_reject_a_deactivated_person(self, db_session):
        """El paso 8 del recorrido de USR.4: desactivar cierra la puerta."""
        persona = await _persona(db_session, activa=False)

        async with _cliente(await _sesion_como_en_produccion(db_session)) as c:
            r = await c.post(
                "/api/v1/auth/user/login",
                json={"email": persona.email, "password": PASSWORD},
            )

        assert r.status_code == 401, r.text

    async def test_should_let_in_a_person_without_organization(self, db_session):
        """Entra, y con la lista vacía no abre ningún chatbot de organización."""
        persona = await _persona(db_session, con_organizacion=False)

        async with _cliente(await _sesion_como_en_produccion(db_session)) as c:
            r = await c.post(
                "/api/v1/auth/user/login",
                json={"email": persona.email, "password": PASSWORD},
            )

        assert r.status_code == 200, r.text
        from server.app.core.auth import decode_token

        assert not decode_token(r.json()["access_token"]).organizacion_ids
