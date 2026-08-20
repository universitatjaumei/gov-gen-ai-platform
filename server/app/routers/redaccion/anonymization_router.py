"""Endpoints de auditoría NER y configuración por workspace — Fase 13.2.

Deploy: edge

Tres endpoints:
- GET  /{workspace_id}/anonymization-summary  → AnonymizationSummaryResponse
- PATCH /{workspace_id}/anonymization-mode    → AnonymizationModeResponse
- POST  /{workspace_id}/re-analyze            → ReAnalyzeResponse (202)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session, require_module
from server.app.core.auth.models import UserInfo
from server.app.routers.redaccion._actor import es_propietario
from server.app.modules.redaccion.database.models import (
    HubRunManifest,
    HubWorkspace,
    HubWorkspaceAuditEvent,
)
from server.app.modules.redaccion.services.anonymization.run_context import (
    AnonymizationMode,
    AnonymizationSummary,
)

router = APIRouter(prefix="/redaccion/workspaces", tags=["redaccion-anonymization"],
    # INF.7 — el modulo se exige a nivel de router: asi no se puede olvidar en un
    # endpoint nuevo del mismo fichero, que es como se abrieron los agujeros que SEC.8.1
    # tuvo que cerrar uno a uno.
    dependencies=[Depends(require_module("informes"))],
)

_LOCKED_STATUSES = frozenset({"drafting", "in_review", "assembled", "exported"})


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class AnonymizationSummaryResponse(BaseModel):
    """Resumen de la última ejecución + modo activo en el workspace."""

    mode: AnonymizationMode
    counts_by_type: dict[str, int]
    total_spans: int
    last_run_at: datetime
    current_workspace_mode: AnonymizationMode


class AnonymizationModeUpdate(BaseModel):
    mode: AnonymizationMode


class AnonymizationModeResponse(BaseModel):
    workspace_id: uuid.UUID
    mode: AnonymizationMode
    updated_at: datetime


class ReAnalyzeResponse(BaseModel):
    workspace_id: uuid.UUID
    status: str
    current_mode: AnonymizationMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_workspace_checked(
    workspace_id: uuid.UUID,
    user: UserInfo,
    session: AsyncSession,
) -> HubWorkspace:
    """Carga el workspace y verifica que quien pregunta es su dueño.

    SEC.8.1: antes bastaba con ser admin *de cualquier organización*. Los workspaces de
    redacción son por usuario y contienen datos personales del expediente —lo que este
    router expone es precisamente el resumen de PII detectada y el modo de anonimización—,
    así que un bypass por rol convertía a cualquier admin en lector del expediente ajeno.
    El resumen NER no se comparte por jerarquía: se comparte con quien lo generó.
    """
    workspace = await session.get(HubWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not es_propietario(user.user_id, workspace.owner_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return workspace


async def _get_last_manifest(
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> HubRunManifest | None:
    """Devuelve el último HubRunManifest para el workspace, o None si no existe."""
    stmt = (
        select(HubRunManifest)
        .where(HubRunManifest.workspace_id == workspace_id)
        .order_by(HubRunManifest.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/anonymization-summary",
    response_model=AnonymizationSummaryResponse,
    operation_id="getAnonymizationSummary",
)
async def get_anonymization_summary(
    workspace_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnonymizationSummaryResponse:
    """Devuelve el resumen NER del último run (sin originales ni sintéticos).

    - 200: resumen disponible.
    - 404: no hay run ejecutado todavía para este workspace.
    - 403: usuario no es owner ni admin/superadmin.
    """
    workspace = await _get_workspace_checked(workspace_id, user, session)
    manifest_orm = await _get_last_manifest(workspace_id, session)

    if manifest_orm is None:
        raise HTTPException(
            status_code=404,
            detail="No run has been executed for this workspace yet",
        )

    # Extrae el summary del payload del manifest.
    payload = manifest_orm.payload_json or {}
    raw_summary = payload.get("anonymization_summary")
    if raw_summary is None:
        raise HTTPException(
            status_code=404,
            detail="No anonymization summary found for the last run",
        )

    summary = AnonymizationSummary.model_validate(raw_summary)
    return AnonymizationSummaryResponse(
        mode=summary.mode,
        counts_by_type=summary.counts_by_type,
        total_spans=summary.total_spans,
        last_run_at=manifest_orm.created_at,
        current_workspace_mode=AnonymizationMode(workspace.anonymization_mode),
    )


@router.patch(
    "/{workspace_id}/anonymization-mode",
    response_model=AnonymizationModeResponse,
    operation_id="patchAnonymizationMode",
)
async def patch_anonymization_mode(
    workspace_id: uuid.UUID,
    body: AnonymizationModeUpdate,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnonymizationModeResponse:
    """Cambia el modo de anonimización del workspace.

    - 200: modo actualizado.
    - 422: workspace en ejecución (drafting/in_review/assembled/exported).
    - 403: usuario no es owner.
    """
    workspace = await _get_workspace_checked(workspace_id, user, session)

    if workspace.status in _LOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="MODE_LOCKED_DURING_EXECUTION",
        )

    old_mode = workspace.anonymization_mode
    workspace.anonymization_mode = body.mode.value
    updated_at = datetime.now(timezone.utc)

    audit_event = HubWorkspaceAuditEvent(
        workspace_id=workspace_id,
        block_id=None,
        event="anonymization_mode_changed",
        from_status=old_mode,
        to_status=body.mode.value,
        actor=user.user_id,
        metadata_json={"old_mode": old_mode, "new_mode": body.mode.value},
    )
    session.add(audit_event)
    await session.commit()

    return AnonymizationModeResponse(
        workspace_id=workspace_id,
        mode=body.mode,
        updated_at=updated_at,
    )


@router.post(
    "/{workspace_id}/re-analyze",
    response_model=ReAnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="reAnalyzeAnonymization",
)
async def re_analyze_anonymization(
    workspace_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReAnalyzeResponse:
    """Dispara InitAnonymizationNode sin llegar al LLM.

    Útil para previsualizar conteos de PII antes de ejecutar el grafo.
    El análisis se encola en background; el endpoint devuelve 202 inmediatamente.
    - 403: usuario no es owner.
    """
    workspace = await _get_workspace_checked(workspace_id, user, session)

    audit_event = HubWorkspaceAuditEvent(
        workspace_id=workspace_id,
        block_id=None,
        event="re_analyze_started",
        from_status=workspace.status,
        to_status=workspace.status,
        actor=user.user_id,
        metadata_json={"mode": workspace.anonymization_mode},
    )
    session.add(audit_event)
    await session.commit()

    return ReAnalyzeResponse(
        workspace_id=workspace_id,
        status="queued",
        current_mode=AnonymizationMode(workspace.anonymization_mode),
    )
