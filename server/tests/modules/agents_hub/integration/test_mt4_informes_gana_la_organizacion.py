"""MT.4 — Informes gana la dimensión que no tiene, y la escalera completa de elevación.

`owner_kind` admitía `user`, `platform` y `superadmin`: **no existía `organizacion`**. Una
plantilla era de una persona o de todo el mundo, sin nada en medio. Es la carencia más profunda
de las seis de la auditoría, porque no es un filtro que falte sino una dimensión que no está.

La escalera que pidió el usuario el 2026-08-24 es **usuario → organización → plataforma**, y los
dos extremos ya existían: en esta base hay 20 plantillas de plataforma, 2 personales de un
superadministrador y 1 de un usuario. Lo que MT.4 añade es el escalón de en medio.

**Dos cosas que este prompt tiene que no romper**, y que son la mitad del trabajo:

1. El nivel de plataforma **se sigue viendo desde todas las organizaciones**. Es lo que permite
   que la Diputación comparta una plantilla, y en esta base son 20 de 23 filas.
2. Un administrador tiene que poder **adaptar** lo heredado. El arreglo del 2026-08-24 dejó las
   plantillas de plataforma a mano sólo del superadministrador, así que sin bifurcar, «heredado»
   pasó a significar «mírala y no la toques».
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.config_models import HubOrganizacion
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
)
from server.app.routers.redaccion.hub_redaccion_router import router

pytestmark = pytest.mark.asyncio

OWNER_ORGANIZACION = "organizacion"


def _cliente(session, principal: UserInfo) -> AsyncClient:
    async def _sesion():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: principal
    app.dependency_overrides[get_session] = _sesion
    app.include_router(router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _organizacion(session, nombre="Vila-real") -> HubOrganizacion:
    fila = HubOrganizacion(
        name=f"{nombre} {uuid.uuid4().hex[:6]}", partner_id=f"p-{uuid.uuid4().hex[:6]}"
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _plantilla(session, **campos) -> HubReportTemplate:
    campos.setdefault("name", f"Plantilla {uuid.uuid4().hex[:6]}")
    campos.setdefault("report_profile", "seguimiento")
    campos.setdefault("owner_kind", "platform")
    # MT.4 — `is_global` ya no se asigna: se deriva de `owner_kind`.
    campos.pop("is_global", None)
    fila = HubReportTemplate(**campos)
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


def _admin_de(organizacion) -> UserInfo:
    return UserInfo(
        user_id=f"admin-{uuid.uuid4().hex[:6]}",
        email="admin@ayuntamiento.es",
        role="admin",
        organizacion_ids=(str(organizacion.id),),
    )


class TestElEscalonQueFaltaba:

    async def test_should_accept_organizacion_as_an_owner_kind(self, db_session):
        organizacion = await _organizacion(db_session)

        plantilla = await _plantilla(
            db_session,
            owner_kind=OWNER_ORGANIZACION,
            organizacion_id=organizacion.id,
        )

        assert plantilla.owner_kind == OWNER_ORGANIZACION
        assert plantilla.organizacion_id == organizacion.id

    async def test_should_reject_an_organisation_owner_without_organizacion_id(self, db_session):
        """Coherencia entre las dos columnas, **en la base y no sólo en el modelo**: sin esto
        queda una plantilla «de organización» que no dice de cuál, y ninguna consulta la
        encuentra ni la excluye."""
        from sqlalchemy.exc import IntegrityError

        db_session.add(
            HubReportTemplate(
                name="De nadie en concreto",
                report_profile="seguimiento",
                owner_kind=OWNER_ORGANIZACION,
                organizacion_id=None,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_should_leave_existing_templates_untouched(self, db_session):
        """Las que ya existen quedan a nulo, que es su significado de siempre: de plataforma o
        de su persona. La fase 1 no cambia comportamiento."""
        antigua = await _plantilla(db_session, owner_kind="platform")

        assert antigua.organizacion_id is None
        assert antigua.is_global is True


class TestLoQueNoSePuedeRomper:

    async def test_should_keep_the_platform_level_visible_to_everyone(self, db_session):
        """**El test que protege lo que ya funcionaba.** El nivel de plataforma existía desde
        antes de MT y es lo que permite que la Diputación comparta una plantilla: en esta base
        son 20 de 23 filas. Añadir el escalón de en medio no puede dejar de verlo."""
        organizacion = await _organizacion(db_session)
        de_plataforma = await _plantilla(db_session, owner_kind="platform")

        async with _cliente(db_session, _admin_de(organizacion)) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/redaccion/templates")).json()

        assert str(de_plataforma.id) in {p["id"] for p in cuerpo}

    async def test_should_show_an_admin_the_templates_of_their_organisation(self, db_session):
        organizacion = await _organizacion(db_session)
        propia = await _plantilla(
            db_session,
            owner_kind=OWNER_ORGANIZACION,
            organizacion_id=organizacion.id,
        )

        async with _cliente(db_session, _admin_de(organizacion)) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/redaccion/templates")).json()

        assert str(propia.id) in {p["id"] for p in cuerpo}

    async def test_should_not_show_the_templates_of_another_organisation(self, db_session):
        """**El test que importa.** Una plantilla de informe lleva la estructura del informe de
        otro ayuntamiento: qué mide, cómo lo agrupa y qué valora."""
        ajena = await _organizacion(db_session, "Onda")
        propia = await _organizacion(db_session, "Nules")
        de_otro = await _plantilla(
            db_session,
            owner_kind=OWNER_ORGANIZACION,
            organizacion_id=ajena.id,
        )

        async with _cliente(db_session, _admin_de(propia)) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/redaccion/templates")).json()

        assert str(de_otro.id) not in {p["id"] for p in cuerpo}


class TestQuienPuedeTocarQue:

    async def test_should_let_an_admin_manage_the_templates_of_their_organisation(
        self, db_session
    ):
        """Lo que el arreglo del 2026-08-24 no pudo permitir porque no había columna contra la
        que comprobar: un administrador gestiona lo de su organización."""
        organizacion = await _organizacion(db_session)
        propia = await _plantilla(
            db_session,
            owner_kind=OWNER_ORGANIZACION,
            organizacion_id=organizacion.id,
        )

        async with _cliente(db_session, _admin_de(organizacion)) as cliente:
            respuesta = await cliente.patch(
                f"/api/v1/hub/redaccion/templates/{propia.id}", json={"name": "Renombrada"}
            )

        assert respuesta.status_code == 200, respuesta.text

    async def test_should_not_let_an_admin_touch_another_organisations_template(
        self, db_session
    ):
        ajena = await _organizacion(db_session, "Onda")
        propia = await _organizacion(db_session, "Nules")
        de_otro = await _plantilla(
            db_session,
            owner_kind=OWNER_ORGANIZACION,
            organizacion_id=ajena.id,
        )

        async with _cliente(db_session, _admin_de(propia)) as cliente:
            respuesta = await cliente.patch(
                f"/api/v1/hub/redaccion/templates/{de_otro.id}", json={"name": "Mía"}
            )

        assert respuesta.status_code == 403, respuesta.text

    async def test_should_still_reserve_the_platform_level_to_a_superadmin(self, db_session):
        """No se afloja lo que se cerró el 2026-08-24: la de todos no puede ser de cualquiera."""
        organizacion = await _organizacion(db_session)
        de_plataforma = await _plantilla(db_session, owner_kind="platform")

        async with _cliente(db_session, _admin_de(organizacion)) as cliente:
            respuesta = await cliente.patch(
                f"/api/v1/hub/redaccion/templates/{de_plataforma.id}",
                json={"name": "La cambio para todos"},
            )

        assert respuesta.status_code == 403, respuesta.text


class TestAdaptarLoHeredadoSinRomperloParaLosDemas:

    async def test_should_fork_an_inherited_template_into_the_organisation(self, db_session):
        """**Sin esto, «heredado» significa «mírala y no la toques».** El arreglo del
        2026-08-24 dejó las plantillas de plataforma a mano sólo del superadministrador, que es
        correcto para *modificarlas*; adaptarlas es otra operación y necesita salida propia.

        Bifurcar **copia**, no mueve: la de plataforma sigue intacta para los demás.
        """
        organizacion = await _organizacion(db_session)
        original = await _plantilla(db_session, owner_kind="platform", name="De la Diputación")
        version = HubReportTemplateVersion(
            template_id=original.id, version=1, spec_json={"a": 1}, created_by=uuid.uuid4()
        )
        db_session.add(version)
        await db_session.commit()
        await db_session.refresh(version)
        original.current_version_id = version.id
        await db_session.commit()

        async with _cliente(db_session, _admin_de(organizacion)) as cliente:
            respuesta = await cliente.post(
                f"/api/v1/hub/redaccion/templates/{original.id}/fork"
            )

        assert respuesta.status_code == 201, respuesta.text
        copia = respuesta.json()
        assert copia["id"] != str(original.id)
        assert copia["owner_kind"] == OWNER_ORGANIZACION

        await db_session.refresh(original)
        assert original.owner_kind == "platform", "bifurcar no mueve el original"
        assert original.name == "De la Diputación"

    async def test_should_copy_the_content_and_not_just_the_name(self, db_session):
        """Una bifurcación que no se lleve la versión vigente es una plantilla vacía con el
        nombre de otra: se abriría sin nada dentro, y el fallo aparecería en el piloto."""
        organizacion = await _organizacion(db_session)
        original = await _plantilla(db_session, owner_kind="platform")
        version = HubReportTemplateVersion(
            template_id=original.id,
            version=3,
            spec_json={"bloques": ["uno", "dos"]},
            created_by=uuid.uuid4(),
        )
        db_session.add(version)
        await db_session.commit()
        await db_session.refresh(version)
        original.current_version_id = version.id
        await db_session.commit()

        async with _cliente(db_session, _admin_de(organizacion)) as cliente:
            copia = (
                await cliente.post(f"/api/v1/hub/redaccion/templates/{original.id}/fork")
            ).json()

        versiones = (
            await db_session.execute(
                select(HubReportTemplateVersion).where(
                    HubReportTemplateVersion.template_id == uuid.UUID(copia["id"])
                )
            )
        ).scalars().all()
        assert len(versiones) == 1
        assert versiones[0].spec_json == {"bloques": ["uno", "dos"]}

    async def test_should_record_where_the_fork_came_from(self, db_session):
        """La procedencia de MT.4.2 aplicada a su primer caso real: sin ella, «la Diputación ha
        corregido la plantilla, tienes la v3 y hay v4» no se puede decir nunca."""
        organizacion = await _organizacion(db_session)
        original = await _plantilla(db_session, owner_kind="platform")
        version = HubReportTemplateVersion(
            template_id=original.id, version=2, spec_json={}, created_by=uuid.uuid4()
        )
        db_session.add(version)
        await db_session.commit()
        await db_session.refresh(version)
        original.current_version_id = version.id
        await db_session.commit()

        async with _cliente(db_session, _admin_de(organizacion)) as cliente:
            copia = (
                await cliente.post(f"/api/v1/hub/redaccion/templates/{original.id}/fork")
            ).json()

        fila = await db_session.get(HubReportTemplate, uuid.UUID(copia["id"]))
        assert fila.derivado_de == original.id
        assert fila.version_de_origen == 2


class TestUnSoloSitioParaUnSoloHecho:

    async def test_should_collapse_is_global_into_one_source_of_truth(self, db_session):
        """`is_global` se calculaba en el router como `owner_kind == "platform"` **y además** se
        guardaba en su propia columna, así que dos sitios tenían el mismo hecho. Dos sitios para
        un hecho terminan discrepando, y cuando discrepan no hay cómo saber cuál manda.

        Ahora se **deriva**, y este test lo fija por los dos lados: el valor sale de
        `owner_kind`, y **no se puede escribir** — que es lo que impide que vuelva a haber dos.
        """
        de_plataforma = await _plantilla(db_session, owner_kind="platform")
        de_una_persona = await _plantilla(db_session, owner_kind="user")

        assert de_plataforma.is_global is True
        assert de_una_persona.is_global is False

        with pytest.raises(AttributeError):
            de_una_persona.is_global = True
