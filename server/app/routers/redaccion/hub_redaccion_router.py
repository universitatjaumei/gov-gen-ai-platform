"""Endpoints hub/redaccion — 9R.4.4 / 9R.7.2.

Deploy: edge
Template update notice, migración de workspaces, lectura de workspace/blocks/warnings.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.contracts.template import ReportTemplateSpec
from server.app.modules.redaccion.contracts.ui import ReportUIContract
from server.app.modules.redaccion.database.models import HubWorkspaceBlock
from server.app.modules.redaccion.database.repos import (
    ReportTemplateVersionRepo,
    WorkspaceBlockRepo,
    WorkspaceRepo,
)
from server.app.modules.redaccion.services.template_migration_service import (
    CompatibilityConflictError,
    NewVersionNotice,
    TemplateMigrationService,
    WorkspaceNotFoundError,
    WorkspaceOwnershipError,
)

router = APIRouter(prefix="/hub/redaccion", tags=["hub-redaccion"])

# ---------------------------------------------------------------------------
# DTOs — workspace / blocks / warnings (9R.7.2)
# ---------------------------------------------------------------------------

class BlockStateOut(BaseModel):
    block_id: str
    kind: str
    status: str
    content: dict | None = None
    failure_kind: str | None = None
    last_error_message: str | None = None
    retry_attempts: int = 0
    updated_at: datetime


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    template_version_id: uuid.UUID
    status: str
    blocks: list[BlockStateOut]
    created_at: datetime
    updated_at: datetime


class BlockPatchRequest(BaseModel):
    action: Literal["approve", "reject", "regenerate"]
    note: str | None = None


class ExtractionWarningOut(BaseModel):
    block_id: str | None = None
    message: str
    kind: str
    severity: str = "warning"


_KIND_TO_SEVERITY: dict[str, str] = {
    "type_mismatch": "error",
    "validation_failed": "error",
    "low_confidence": "warning",
    "missing_data": "warning",
}

_ACTION_TO_STATUS: dict[str, str] = {
    "approve": "approved",
    "reject": "rejected",
    "regenerate": "extracted",
}

# ---------------------------------------------------------------------------
# DTOs — migrate (9R.4.4)
# ---------------------------------------------------------------------------

class MigrateRequest(BaseModel):
    target_version_id: uuid.UUID


class MigrateResponse(BaseModel):
    new_workspace_id: uuid.UUID


@router.get(
    "/template-versions/{version_id}/ui-contract",
    response_model=ReportUIContract,
)
async def get_template_ui_contract(
    version_id: uuid.UUID,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportUIContract:
    """Devuelve el ReportUIContract de una versión de plantilla."""
    version = await ReportTemplateVersionRepo(session).get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Template version not found")
    spec = ReportTemplateSpec.model_validate(version.spec_json)
    return spec.ui_contract


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceOut,
    operation_id="getWorkspaceById",
)
async def get_workspace_by_id(
    workspace_id: uuid.UUID,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceOut:
    """Devuelve el workspace con todos sus bloques."""
    workspace = await WorkspaceRepo(session).get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    blocks = await WorkspaceBlockRepo(session).list(workspace_id)
    return WorkspaceOut(
        id=workspace.id,
        template_version_id=workspace.template_version_id,
        status=workspace.status,
        blocks=[
            BlockStateOut(
                block_id=b.block_id,
                kind=b.kind,
                status=b.status,
                content=b.content_json,
                failure_kind=b.failure_kind,
                last_error_message=b.last_error_message,
                retry_attempts=b.retry_attempts,
                updated_at=b.updated_at,
            )
            for b in blocks
        ],
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


@router.patch(
    "/workspaces/{workspace_id}/blocks/{block_id}",
    response_model=BlockStateOut,
    operation_id="patchWorkspaceBlock",
)
async def patch_workspace_block(
    workspace_id: uuid.UUID,
    block_id: str,
    body: BlockPatchRequest,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BlockStateOut:
    """Aprueba, rechaza o solicita regeneración de un bloque."""
    stmt = select(HubWorkspaceBlock).where(
        and_(
            HubWorkspaceBlock.workspace_id == workspace_id,
            HubWorkspaceBlock.block_id == block_id,
        )
    )
    result = await session.execute(stmt)
    block = result.scalar_one_or_none()
    if block is None:
        raise HTTPException(status_code=404, detail="Block not found")

    block.status = _ACTION_TO_STATUS[body.action]
    await session.commit()
    await session.refresh(block)
    return BlockStateOut(
        block_id=block.block_id,
        kind=block.kind,
        status=block.status,
        content=block.content_json,
        failure_kind=block.failure_kind,
        last_error_message=block.last_error_message,
        retry_attempts=block.retry_attempts,
        updated_at=block.updated_at,
    )


@router.get(
    "/workspaces/{workspace_id}/warnings",
    response_model=list[ExtractionWarningOut],
    operation_id="getWorkspaceWarnings",
)
async def get_workspace_warnings(
    workspace_id: uuid.UUID,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ExtractionWarningOut]:
    """Lista de avisos de extracción del workspace."""
    workspace = await WorkspaceRepo(session).get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return [
        ExtractionWarningOut(
            block_id=w.get("block_id"),
            message=w.get("message", ""),
            kind=w.get("kind", ""),
            severity=_KIND_TO_SEVERITY.get(w.get("kind", ""), "warning"),
        )
        for w in (workspace.warnings_json or [])
    ]


@router.get(
    "/workspaces/{workspace_id}/template-update-notice",
    response_model=NewVersionNotice,
    responses={204: {"description": "Workspace already at latest version"}},
)
async def template_update_notice(
    workspace_id: uuid.UUID,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NewVersionNotice | Response:
    """Devuelve aviso de nueva versión disponible, o 204 si ya está alineado."""
    service = TemplateMigrationService(session)
    try:
        notice = await service.detect_new_version(workspace_id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if notice is None:
        return Response(status_code=204)
    return notice


@router.post(
    "/workspaces/{workspace_id}/migrate",
    response_model=MigrateResponse,
    status_code=201,
)
async def migrate_workspace(
    workspace_id: uuid.UUID,
    body: MigrateRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MigrateResponse:
    """Crea workspace nuevo contra target_version_id, archiva el antiguo."""
    service = TemplateMigrationService(session)
    try:
        new_workspace = await service.migrate_workspace(
            workspace_id,
            body.target_version_id,
            uuid.UUID(user.user_id),
        )
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except WorkspaceOwnershipError:
        raise HTTPException(
            status_code=403,
            detail="Only the workspace owner can trigger migration",
        )
    except CompatibilityConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"compatibility_errors": exc.compatibility_errors},
        )

    return MigrateResponse(new_workspace_id=new_workspace.id)
