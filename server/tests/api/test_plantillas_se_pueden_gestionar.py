"""GUI.1 + GUI.2 — una plantilla se puede renombrar y retirar.

Encontrado por el usuario probando: «se han creado muchas plantillas, se ven en dos pantallas y
no hay ninguna opción para borrarlas o editarlas». Al mirarlo, no faltaba el botón: **faltaban
los endpoints**. `hub_redaccion_router` tenía `GET /templates` y `POST /templates` y nada más, así
que la lista de una instalación sólo podía crecer.

Se **archiva**, no se borra, y es decisión del usuario: un informe firmado no puede quedarse sin
la plantilla con la que se hizo. Archivar la saca de las dos listas y deja los informes intactos.

Contra sesión real, como `test_create_template_endpoint`: los tests que mockean la sesión de este
router no ven `expire_on_commit`, que es justo lo que rompió el alta de plantillas en MAN.2.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.routers.redaccion.hub_redaccion_router import (
    TemplateCreateIn,
    TemplatePatchIn,
    archive_template,
    create_template,
    create_workspace_endpoint,
    get_workspace_by_id,
    list_templates,
    patch_template,
    restore_template,
    WorkspaceCreateIn,
)

_ADMIN = UserInfo(user_id="1", email="fabra@uji.es", role="superadmin")


async def _crear(session, nombre: str):
    return await create_template(
        body=TemplateCreateIn(name=nombre), user=_ADMIN, session=session
    )


async def _nombres(session) -> list[str]:
    return [t.name for t in await list_templates(user=_ADMIN, session=session)]


# ----------------------------------------------------------------------
# Archivar
# ----------------------------------------------------------------------


async def test_una_plantilla_archivada_desaparece_de_la_lista(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Plantilla de prueba GUI")
            assert "Plantilla de prueba GUI" in await _nombres(session)

            await archive_template(
                template_id=plantilla.id, user=_ADMIN, session=session
            )

            assert "Plantilla de prueba GUI" not in await _nombres(session)
    finally:
        await engine.dispose()


async def test_la_archivada_sigue_ahi_para_quien_la_pida(db_url):
    """Los informes hechos con ella tienen que seguir abriéndose: la fila no se va."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Plantilla con informes")
            await archive_template(template_id=plantilla.id, user=_ADMIN, session=session)

            todas = await list_templates(
                user=_ADMIN, session=session, include_archived=True
            )
            fila = next(t for t in todas if t.id == plantilla.id)
            assert fila.archived is True
    finally:
        await engine.dispose()


async def test_un_informe_de_una_plantilla_archivada_sigue_abriendose(db_url):
    """Es la razón de archivar en vez de borrar. Si esto falla, el archivado no sirve."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Plantilla del informe firmado")
            creado = await create_workspace_endpoint(
                body=WorkspaceCreateIn(template_version_id=plantilla.current_version_id),
                user=_ADMIN,
                session=session,
            )

            await archive_template(template_id=plantilla.id, user=_ADMIN, session=session)

            abierto = await get_workspace_by_id(
                workspace_id=creado.workspace_id, user=_ADMIN, session=session
            )
            assert abierto.id == creado.workspace_id
    finally:
        await engine.dispose()


async def test_no_se_puede_empezar_un_informe_nuevo_con_una_archivada(db_url):
    """Retirada es retirada: sirve para consultar lo hecho, no para empezar algo nuevo."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Plantilla retirada")
            await archive_template(template_id=plantilla.id, user=_ADMIN, session=session)

            with pytest.raises(HTTPException) as fallo:
                await create_workspace_endpoint(
                    body=WorkspaceCreateIn(
                        template_version_id=plantilla.current_version_id
                    ),
                    user=_ADMIN,
                    session=session,
                )
            assert fallo.value.status_code == 409
            assert fallo.value.detail["code"] == "TEMPLATE_ARCHIVED"
    finally:
        await engine.dispose()


async def test_archivar_dos_veces_no_es_un_error(db_url):
    """Idempotente: quien pulsa dos veces no merece un 500."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Plantilla doblemente archivada")
            await archive_template(template_id=plantilla.id, user=_ADMIN, session=session)
            await archive_template(template_id=plantilla.id, user=_ADMIN, session=session)
    finally:
        await engine.dispose()


async def test_se_puede_recuperar_lo_archivado_por_error(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Plantilla recuperada")
            await archive_template(template_id=plantilla.id, user=_ADMIN, session=session)

            vuelta = await restore_template(
                template_id=plantilla.id, user=_ADMIN, session=session
            )
            assert vuelta.archived is False
            assert "Plantilla recuperada" in await _nombres(session)
    finally:
        await engine.dispose()


async def test_archivar_algo_que_no_existe_es_un_404(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            with pytest.raises(HTTPException) as fallo:
                await archive_template(
                    template_id=uuid.uuid4(), user=_ADMIN, session=session
                )
            assert fallo.value.status_code == 404
    finally:
        await engine.dispose()


async def test_solo_un_administrador_archiva(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Plantilla ajena")
            with pytest.raises(HTTPException) as fallo:
                await archive_template(
                    template_id=plantilla.id,
                    user=UserInfo(user_id="9", email="x@uji.es", role="user"),
                    session=session,
                )
            assert fallo.value.status_code == 403
    finally:
        await engine.dispose()


# ----------------------------------------------------------------------
# Renombrar
# ----------------------------------------------------------------------


async def test_una_plantilla_se_puede_renombrar(db_url):
    """Lo mínimo de «editar»: el nombre es lo que se ve en las dos listas."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Nombre provisional")

            cambiada = await patch_template(
                template_id=plantilla.id,
                body=TemplatePatchIn(
                    name="Ejecución presupuestaria trimestral", description="Para Gerencia"
                ),
                user=_ADMIN,
                session=session,
            )
            assert cambiada.name == "Ejecución presupuestaria trimestral"
            assert cambiada.description == "Para Gerencia"

            nombres = await _nombres(session)
            assert "Ejecución presupuestaria trimestral" in nombres
            assert "Nombre provisional" not in nombres
    finally:
        await engine.dispose()


async def test_renombrar_no_publica_una_version_nueva(db_url):
    """El nombre es de la plantilla; el contenido, de la versión. Renombrar no toca informes."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Antes")
            antes = plantilla.current_version_id

            cambiada = await patch_template(
                template_id=plantilla.id,
                body=TemplatePatchIn(name="Después"),
                user=_ADMIN,
                session=session,
            )
            assert cambiada.current_version_id == antes
    finally:
        await engine.dispose()


async def test_solo_la_descripcion_tambien_vale(db_url):
    """Un PATCH sin nombre no borra el nombre."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = await _crear(session, "Nombre que se queda")
            cambiada = await patch_template(
                template_id=plantilla.id,
                body=TemplatePatchIn(description="sólo la descripción"),
                user=_ADMIN,
                session=session,
            )
            assert cambiada.name == "Nombre que se queda"
            assert cambiada.description == "sólo la descripción"
    finally:
        await engine.dispose()


def test_un_nombre_en_blanco_no_pasa_la_validacion():
    """Una fila sin nombre en la lista es una fila que nadie puede identificar."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TemplatePatchIn(name="   ")


async def test_renombrar_lo_que_no_existe_es_un_404(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            with pytest.raises(HTTPException) as fallo:
                await patch_template(
                    template_id=uuid.uuid4(),
                    body=TemplatePatchIn(name="x"),
                    user=_ADMIN,
                    session=session,
                )
            assert fallo.value.status_code == 404
    finally:
        await engine.dispose()
