"""VER.4 — `POST /run` contra una sesión real, no mockeada.

Al pulsar «Generar informe» en la pantalla nueva, el endpoint daba **500** con
`MissingGreenlet`: `run_workspace` leía `workspace.status` para el evento de auditoría
**después** de que `start_run` hiciera `commit()`, y con `expire_on_commit` eso dispara una
recarga perezosa síncrona sobre una `AsyncSession` de asyncpg.

Es el mismo patrón que tumbó `create_template` y ocho endpoints de `scripts_router` el
2026-08-14, y por la misma razón no lo cazaba nada: los tests de este endpoint mockean la
sesión con `AsyncMock`, que no reproduce `expire_on_commit`.

Consecuencia real: el 202 nunca llegaba, así que **la tarea de fondo no se encolaba** y el
workspace se quedaba en `drafting` para siempre. Justo lo que VER.1 quiso evitar, entrando
por otra puerta.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubWorkspace,
)
from server.app.routers.redaccion._actor import user_to_uuid
from server.app.routers.redaccion.workspaces_router import run_workspace

_USUARIO = UserInfo(user_id="1", email="fabra@uji.es", role="superadmin")


class _Tareas:
    def __init__(self) -> None:
        self.encoladas: list = []

    def add_task(self, funcion, *args, **kwargs) -> None:
        self.encoladas.append((funcion, args))


async def _workspace(session) -> uuid.UUID:
    plantilla = HubReportTemplate(
        name=f"Plantilla {uuid.uuid4().hex[:6]}",
        report_profile="GENERIC_REPORT",
        owner_kind="platform",
        is_global=True,
    )
    session.add(plantilla)
    await session.flush()

    version = HubReportTemplateVersion(
        template_id=plantilla.id, version=1, spec_json={}, created_by=uuid.uuid4()
    )
    session.add(version)
    await session.flush()

    workspace = HubWorkspace(
        template_version_id=version.id,
        owner_id=user_to_uuid(_USUARIO.user_id),
        status="draft",
    )
    session.add(workspace)
    await session.flush()
    return workspace.id


@pytest.mark.asyncio
async def test_should_approve_a_block_without_a_500(db_url):
    """Las cuatro transiciones —aprobar, rechazar, regenerar, editar— construían la respuesta
    leyendo el bloque **después** del commit, así que devolvían 500 con `MissingGreenlet`: la
    revisión entera era inutilizable. Tercera aparición del mismo patrón en el módulo, y
    tampoco la cazaba nada porque los tests de estos endpoints mockean la sesión.
    """
    from server.app.modules.redaccion.database.models import HubWorkspaceBlock
    from server.app.routers.redaccion.workspaces_router import approve_block

    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id = await _workspace(session)
            session.add(HubWorkspaceBlock(
                workspace_id=workspace_id,
                block_id="b_resumen",
                kind="AI_ASSISTED_TEXT",
                status="needs_review",
                content_json={"text": "Redactado."},
            ))
            await session.commit()

            salida = await approve_block(
                workspace_id=workspace_id,
                block_id="b_resumen",
                user=_USUARIO,
                session=session,
            )

            assert salida.status == "approved"
            assert salida.content == {"text": "Redactado."}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_should_actually_persist_the_uploaded_input(db_url):
    """La subida devolvía 200 con la ruta del fichero y `inputs_json` se quedaba **vacío**.

    Mutar el JSONB en sitio y reasignar el mismo objeto no marca la columna como sucia, así
    que SQLAlchemy no emitía UPDATE. Visto en VER.4: la extracción no encontraba el Excel
    que se acababa de subir, y el informe salía sin datos.
    """
    from server.app.core.storage import StorageService
    from server.app.routers.redaccion.workspaces_router import upload_workspace_input

    class _FicheroFalso:
        """`read_within_limit` lee por trozos hasta recibir vacío: si siempre devuelve algo,
        cree que el fichero no acaba nunca y lo rechaza por tamaño."""

        filename = "datos.xlsx"

        def __init__(self) -> None:
            self._pendiente = b"contenido"

        async def read(self, *_args, **_kwargs):
            trozo, self._pendiente = self._pendiente, b""
            return trozo

    class _Almacen:
        async def put(self, *_args, **_kwargs):
            return None

    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id = await _workspace(session)
            await session.commit()

            await upload_workspace_input(
                workspace_id=workspace_id,
                slot_id="datos_excel",
                file=_FicheroFalso(),
                user=_USUARIO,
                session=session,
                storage=_Almacen(),  # type: ignore[arg-type]
            )

            workspace = await session.get(HubWorkspace, workspace_id)
            await session.refresh(workspace)
            assert "datos_excel" in (workspace.inputs_json or {}), (
                "la subida no llegó a la base: el informe se generará sin datos"
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_should_accept_the_run_and_queue_the_generation_against_a_real_session(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id = await _workspace(session)
            await session.commit()

            tareas = _Tareas()
            salida = await run_workspace(
                workspace_id=workspace_id,
                background_tasks=tareas,
                user=_USUARIO,
                session=session,
            )

            assert salida.status == "queued"
            assert tareas.encoladas, "sin tarea encolada el informe no se genera nunca"

            workspace = await session.get(HubWorkspace, workspace_id)
            await session.refresh(workspace)
            assert workspace.status == "drafting"
    finally:
        await engine.dispose()
