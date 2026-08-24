"""¿Puede un administrador cualquiera tocar una plantilla que no es suya?

Comprobación, no arreglo: sale de la conversación sobre reutilizar plantillas entre municipios.
Si la respuesta es sí, el nivel de plataforma que ya existe (`owner_kind='platform'`) no está
protegido, y eso no es una carencia futura sino un agujero de hoy que el piloto de una sola
organización esconde.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.database.models import HubReportTemplate
from server.app.routers.redaccion.hub_redaccion_router import router

pytestmark = pytest.mark.asyncio


def _cliente(session, principal: UserInfo) -> AsyncClient:
    async def _sesion():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: principal
    app.dependency_overrides[get_session] = _sesion
    app.include_router(router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _admin_ajeno() -> UserInfo:
    """Un administrador de otra organización: rol legítimo, plantilla que no es suya."""
    return UserInfo(
        user_id="admin-de-otro-municipio",
        email="admin@otro-ayuntamiento.es",
        role="admin",
        organizacion_ids=(str(uuid.uuid4()),),
    )


async def _plantilla_de_plataforma(session) -> HubReportTemplate:
    fila = HubReportTemplate(
        name="Informe de seguimiento de la Diputación",
        report_profile="seguimiento",
        owner_kind="platform",
        owner_id=None,
        is_global=True,
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def test_should_not_let_a_foreign_admin_rename_a_platform_template(db_session):
    plantilla = await _plantilla_de_plataforma(db_session)

    async with _cliente(db_session, _admin_ajeno()) as cliente:
        respuesta = await cliente.patch(
            f"/api/v1/hub/redaccion/templates/{plantilla.id}",
            json={"name": "Mío ahora"},
        )

    assert respuesta.status_code == 403, respuesta.text


async def test_should_not_let_a_foreign_admin_archive_a_platform_template(db_session):
    """El peor de los dos: archivar la saca de la lista de **todos** y bloquea crear informes
    nuevos con ella (409 TEMPLATE_ARCHIVED)."""
    plantilla = await _plantilla_de_plataforma(db_session)

    async with _cliente(db_session, _admin_ajeno()) as cliente:
        respuesta = await cliente.delete(
            f"/api/v1/hub/redaccion/templates/{plantilla.id}"
        )

    assert respuesta.status_code == 403, respuesta.text


async def test_should_not_let_a_foreign_admin_touch_a_users_template(db_session):
    """Una plantilla de una persona concreta, tocada por un administrador que no es de su
    organización. Hoy las plantillas no tienen `organizacion_id` —lo añade MT.4—, así que no
    hay nada contra lo que comprobar: sólo se comprueba que quien llama es administrador."""
    fila = HubReportTemplate(
        name="Borrador personal de alguien",
        report_profile="seguimiento",
        owner_kind="user",
        owner_id=uuid.uuid4(),
        is_global=False,
    )
    db_session.add(fila)
    await db_session.commit()
    await db_session.refresh(fila)

    async with _cliente(db_session, _admin_ajeno()) as cliente:
        respuesta = await cliente.patch(
            f"/api/v1/hub/redaccion/templates/{fila.id}", json={"name": "Renombrada"}
        )

    assert respuesta.status_code == 403, respuesta.text
