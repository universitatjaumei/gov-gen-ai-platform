"""SEG.4 — editar lo que propuso la IA sin perder lo que propuso.

El endpoint ya existía y ya guardaba el contenido anterior en un evento de auditoría con su
actor. Lo que faltaba para que sirva de verdad son dos cosas:

1. Que **el texto original de la IA siga consultable desde la pantalla**. El evento de auditoría
   es el registro autoritativo, pero ninguna superficie lo expone, así que sin esto el técnico
   edita a ciegas y no puede volver atrás.
2. Que se sepa **quién editó y cuándo**, que es lo que convierte una edición en supervisión
   efectiva (P3) y no en un cambio anónimo.

Y una que se comprueba porque es fácil de romper: editar **no aprueba**. El bloque sigue su
camino por la máquina de estados.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.routers.redaccion._actor import user_to_uuid
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubWorkspace,
    HubWorkspaceBlock,
)
from server.app.routers.redaccion.workspaces_router import EditBlockRequest, edit_block

_TECNICO = UserInfo(user_id="7", email="tecnico@uji.es", role="admin")


async def _workspace_con_bloque_de_ia(session: AsyncSession) -> tuple[uuid.UUID, str]:
    # `hub_workspaces.template_version_id` tiene FK: sin plantilla y versión reales, el insert
    # revienta antes de llegar a lo que se quiere probar.
    plantilla = HubReportTemplate(
        name="Informe de seguimiento (prueba SEG.4)",
        report_profile="GENERIC_REPORT",
        owner_kind="platform",
    )
    session.add(plantilla)
    await session.flush()

    version = HubReportTemplateVersion(
        template_id=plantilla.id,
        version=1,
        spec_json={},
        created_by=uuid.uuid4(),
    )
    session.add(version)
    await session.flush()

    workspace = HubWorkspace(
        template_version_id=version.id,
        # El propietario es quien edita: el endpoint devuelve 403 a quien no lo es, y eso ya
        # esta probado en su sitio.
        owner_id=user_to_uuid(_TECNICO.user_id),
        status="in_review",
    )
    session.add(workspace)
    await session.flush()

    bloque = HubWorkspaceBlock(
        workspace_id=workspace.id,
        block_id="v_matricula",
        kind="AI_ASSISTED_TEXT",
        status="needs_review",
        content_json={
            "text": "La matrícula desciende un 6 % respecto al curso anterior.",
            "model_used": "gemini-2.5-flash",
            "prompt_version": "valoracion_de_tendencia_v1",
            "context_scope": "anchored",
            "context_block_ids": ["t_matricula"],
        },
    )
    session.add(bloque)
    # El id se lee ANTES del commit: `expire_on_commit` expira los atributos y leerlos
    # despues dispara una recarga sincrona que revienta con MissingGreenlet. Es la misma trampa
    # que tumbo el alta de plantillas y ocho endpoints de scripts_router.
    workspace_id = workspace.id
    await session.commit()
    return workspace_id, "v_matricula"


@pytest.mark.asyncio
async def test_editar_conserva_el_texto_original_de_la_ia(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id, block_id = await _workspace_con_bloque_de_ia(session)

            resultado = await edit_block(
                workspace_id=workspace_id,
                block_id=block_id,
                body=EditBlockRequest(content={
                    "text": "La matrícula desciende, en línea con la caída de la oferta.",
                }),
                user=_TECNICO,
                session=session,
            )

            assert "desciende, en línea" in resultado.content["text"]
            assert resultado.content["original_ai_text"] == (
                "La matrícula desciende un 6 % respecto al curso anterior."
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_editar_dice_quien_y_cuando(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id, block_id = await _workspace_con_bloque_de_ia(session)

            resultado = await edit_block(
                workspace_id=workspace_id, block_id=block_id,
                body=EditBlockRequest(content={"text": "Texto del técnico."}),
                user=_TECNICO, session=session,
            )

            assert resultado.content["edited_by"] == "tecnico@uji.es"
            assert resultado.content["edited_at"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_una_segunda_edicion_no_pisa_el_original_de_la_ia(db_url):
    """El original es lo que escribió la IA, no la edición anterior."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id, block_id = await _workspace_con_bloque_de_ia(session)

            await edit_block(
                workspace_id=workspace_id, block_id=block_id,
                body=EditBlockRequest(content={"text": "Primera edición."}),
                user=_TECNICO, session=session,
            )
            segunda = await edit_block(
                workspace_id=workspace_id, block_id=block_id,
                body=EditBlockRequest(content={"text": "Segunda edición."}),
                user=_TECNICO, session=session,
            )

            assert segunda.content["text"] == "Segunda edición."
            assert segunda.content["original_ai_text"] == (
                "La matrícula desciende un 6 % respecto al curso anterior."
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_editar_no_aprueba_el_bloque(db_url):
    """La supervisión no se salta por editar: el bloque sigue pendiente de aprobación."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id, block_id = await _workspace_con_bloque_de_ia(session)

            resultado = await edit_block(
                workspace_id=workspace_id, block_id=block_id,
                body=EditBlockRequest(content={"text": "Editado."}),
                user=_TECNICO, session=session,
            )

            assert resultado.status == "needs_review"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_editar_conserva_la_procedencia_del_modelo(db_url):
    """Qué modelo y con qué instrucciones se redactó no se pierde al editar: es la evidencia."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id, block_id = await _workspace_con_bloque_de_ia(session)

            resultado = await edit_block(
                workspace_id=workspace_id, block_id=block_id,
                body=EditBlockRequest(content={"text": "Editado."}),
                user=_TECNICO, session=session,
            )

            assert resultado.content["model_used"] == "gemini-2.5-flash"
            assert resultado.content["prompt_version"] == "valoracion_de_tendencia_v1"
            assert resultado.content["context_block_ids"] == ["t_matricula"]
    finally:
        await engine.dispose()
