"""INF.2 — el servidor dice qué se puede hacer con cada bloque.

El módulo tenía **tres reglas distintas** para «qué está pendiente», y un bloque de IA que
falla cae en el hueco entre las tres:

1. `preview_builder.bloques_pendientes`: pendiente = bloque de IA fuera de {approved, locked}.
2. `AIBlockReviewPanel`: pendiente = bloque en `needs_review`, y solo esos se pintan.
3. `FinalAssemblerNode`: se bloquea solo si un bloque **`required`** está `failed`, y
   `required` es `False` por defecto en todos los bloques.

Resultado medido en las pruebas humanas del 2026-08-20: el workspace llegó a `assembled` con
dos bloques de IA en `failed` —la insignia decía «Listo para exportar»—, la vista previa y la
exportación devolvían 409 por esos mismos bloques, y el panel anunciaba «Todos los apartados
aprobados» sin ofrecer un solo botón.

Lo que arregla esto no es una regla nueva, es **una sola**: el servidor calcula qué se puede
hacer con cada bloque y el cliente itera la lista. Regla maestra nº2 de `CLAUDE.md`.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubWorkspace,
    HubWorkspaceBlock,
)
from server.app.routers.redaccion._actor import user_to_uuid
from server.app.routers.redaccion.hub_redaccion_router import (
    BlockPatchRequest,
    patch_workspace_block,
)

_USUARIO = UserInfo(user_id="1", email="admin@example.local", role="superadmin")


async def _workspace_con_bloque(session, *, status: str, failure_kind: str | None = None):
    """Un workspace con un solo bloque de IA en el estado que pida el test.

    Los modelos se importan **arriba**, no dentro del test: el fixture `db_url` crea el esquema
    con los modelos ya registrados en la metadata, asi que un import perezoso deja la tabla sin
    crear y el test muere con `UndefinedTableError`.
    """
    plantilla = HubReportTemplate(
        name=f"P {uuid.uuid4().hex[:6]}",
        report_profile="GENERIC_REPORT",
        owner_kind="platform",
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
        status="in_review",
    )
    session.add(workspace)
    await session.flush()
    workspace_id = workspace.id

    session.add(HubWorkspaceBlock(
        workspace_id=workspace_id,
        block_id="v_resumen",
        kind="AI_ASSISTED_TEXT",
        status=status,
        failure_kind=failure_kind,
        content_json={"text": "Redactado."},
    ))
    await session.commit()
    return workspace_id


class TestLoQueSePuedeHacerConUnBloque:
    """Las acciones salen de `_VALID_TRANSITIONS`, no de una lista escrita a mano."""

    def test_should_offer_regenerate_and_edit_on_a_failed_ai_block(self):
        """El caso del usuario: un bloque de IA en `failed` tenía que ofrecer salida.

        `failed → ai_generated` **ya era una transición válida**, así que regenerar siempre
        estuvo permitido por el servidor. Lo que no había era forma de pedirlo: el panel no
        pintaba el bloque.
        """
        from server.app.modules.redaccion.services.block_actions import acciones_permitidas

        acciones = acciones_permitidas(kind="AI_ASSISTED_TEXT", status="failed")

        assert "regenerate" in acciones
        assert "edit" in acciones
        assert "approve" not in acciones, (
            "aprobar un bloque que fallo aprobaria un texto que no existe"
        )

    def test_should_offer_approve_and_reject_on_a_block_awaiting_review(self):
        from server.app.modules.redaccion.services.block_actions import acciones_permitidas

        acciones = acciones_permitidas(kind="AI_ASSISTED_TEXT", status="needs_review")

        assert "approve" in acciones
        assert "reject" in acciones
        assert "edit" in acciones

    def test_should_not_offer_regenerate_on_a_block_awaiting_review(self):
        """`needs_review → ai_generated` **no** es una transición válida.

        El panel pintaba «Regenerar» en los bloques pendientes de revisión, y ese botón
        devolvía 422. Derivar las acciones de la tabla de transiciones lo hace imposible: si
        el servidor no lo acepta, la lista no lo ofrece.
        """
        from server.app.modules.redaccion.services.block_actions import acciones_permitidas

        assert "regenerate" not in acciones_permitidas(
            kind="AI_ASSISTED_TEXT", status="needs_review"
        )

    def test_should_offer_nothing_on_a_locked_block(self):
        from server.app.modules.redaccion.services.block_actions import acciones_permitidas

        assert acciones_permitidas(kind="AI_ASSISTED_TEXT", status="locked") == []

    def test_should_not_offer_review_actions_on_a_data_block(self):
        """Un `DETERMINISTIC_DATA` no se aprueba ni se regenera: no lo escribió un modelo.

        Su arreglo vive en el formulario de datos de partida, no en el bloque, y desde INF.1
        ese es el único camino para relanzar.
        """
        from server.app.modules.redaccion.services.block_actions import acciones_permitidas

        acciones = acciones_permitidas(kind="DETERMINISTIC_DATA", status="missing_input")

        assert "approve" not in acciones
        assert "regenerate" not in acciones

    @pytest.mark.parametrize("status", ["draft", "missing_input", "extracted", "ai_generated",
                                        "needs_review", "approved", "rejected", "locked", "failed"])
    def test_should_only_offer_actions_the_state_machine_accepts(self, status):
        """Guardarraíl: nada de lo que se ofrece puede ser rechazado por la máquina de estados.

        Es la propiedad que hace útil el contrato. Si se rompe, la pantalla vuelve a pintar
        botones que devuelven 422, que es lo que hacía «Regenerar».
        """
        from server.app.modules.redaccion.contracts.runtime import _VALID_TRANSITIONS
        from server.app.modules.redaccion.services.block_actions import (
            _DESTINO_DE_LA_ACCION,
            acciones_permitidas,
        )

        for accion in acciones_permitidas(kind="AI_ASSISTED_TEXT", status=status):
            destino = _DESTINO_DE_LA_ACCION.get(accion)
            if destino is None:
                continue  # `edit` no transiciona: se valida aparte
            assert destino in _VALID_TRANSITIONS.get(status, set()), (
                f"se ofrece {accion!r} desde {status!r} y la maquina de estados lo rechaza"
            )




# ─────────── El endpoint que usa el panel tiene que respetar la misma regla ───────────
#
# Hay **dos** endpoints para transicionar un bloque y no hacian lo mismo:
#
#   PATCH /redaccion/workspaces/{id}/blocks/{bid}/approve|reject|regenerate
#       pasa por `BlockStateMachine` y rechaza con 422 lo que la tabla no permite.
#   PATCH /hub/redaccion/workspaces/{id}/blocks/{bid}   <- el que usa `AIBlockReviewPanel`
#       escribia el estado directamente desde `_ACTION_TO_STATUS`, **sin validar nada**.
#
# Y sus mapas discrepaban: `regenerate` llevaba a `extracted` en uno y a `ai_generated` en el
# otro. Con el endpoint ciego, `acciones_permitidas` seria decorativo: la pantalla ofreceria lo
# correcto y el servidor aceptaria cualquier cosa igual.


@pytest.mark.asyncio
async def test_should_refuse_a_transition_the_state_machine_forbids(db_url):
    """Regenerar un bloque pendiente de revision no es valido: 422, y el estado no se mueve."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id = await _workspace_con_bloque(session, status="needs_review")

            with pytest.raises(HTTPException) as fallo:
                await patch_workspace_block(
                    workspace_id=workspace_id,
                    block_id="v_resumen",
                    body=BlockPatchRequest(action="regenerate"),
                    user=_USUARIO,
                    session=session,
                )
            assert fallo.value.status_code == 422

        async with AsyncSession(engine) as session:
            fila = (await session.execute(
                select(HubWorkspaceBlock).where(HubWorkspaceBlock.workspace_id == workspace_id)
            )).scalars().one()
            assert fila.status == "needs_review", (
                "el endpoint ciego movia el estado a 'extracted' sin que nada lo autorizara"
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_should_regenerate_a_failed_block_and_report_it_as_ai_generated(db_url):
    """El caso del usuario: regenerar un bloque `failed` si vale, y lleva a `ai_generated`.

    El mapa del endpoint ciego decia `extracted`, que no es el destino que la maquina de
    estados define para REGENERATE.
    """
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            workspace_id = await _workspace_con_bloque(
                session, status="failed", failure_kind="ai_failed"
            )

            salida = await patch_workspace_block(
                workspace_id=workspace_id,
                block_id="v_resumen",
                body=BlockPatchRequest(action="regenerate"),
                user=_USUARIO,
                session=session,
            )

            assert salida.status == "ai_generated"
            assert "regenerate" not in salida.acciones_permitidas, (
                "ya se ha pedido: ofrecerlo otra vez invita a pulsar dos veces"
            )
    finally:
        await engine.dispose()
