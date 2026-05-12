"""Endpoints hub/redaccion — 9R.4.4.

Deploy: edge
Template update notice + migración explícita de workspaces a nueva versión.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.services.template_migration_service import (
    CompatibilityConflictError,
    NewVersionNotice,
    TemplateMigrationService,
    WorkspaceNotFoundError,
    WorkspaceOwnershipError,
)

router = APIRouter(prefix="/hub/redaccion", tags=["hub-redaccion"])


class MigrateRequest(BaseModel):
    target_version_id: uuid.UUID


class MigrateResponse(BaseModel):
    new_workspace_id: uuid.UUID


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
