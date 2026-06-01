"""DraftingRunManifest endpoints — 9R.9.1.

Deploy: edge
Expone el registro de auditoría de cada ejecución del DraftingCoreGraph.
Inmutable: solo GET, sin update.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session
from server.app.modules.redaccion.contracts.manifest import DraftingRunManifest
from server.app.modules.redaccion.database.models import HubRunManifest

router = APIRouter(prefix="/redaccion", tags=["redaccion-manifests"])


async def _load_manifest(orm: HubRunManifest) -> DraftingRunManifest:
    return DraftingRunManifest.model_validate(orm.payload_json)


@router.get(
    "/workspaces/{workspace_id}/manifest",
    response_model=DraftingRunManifest,
    operation_id="getWorkspaceManifest",
)
async def get_workspace_manifest(
    workspace_id: uuid.UUID,
    _user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DraftingRunManifest:
    """Devuelve el manifest más reciente del workspace."""
    stmt = (
        select(HubRunManifest)
        .where(HubRunManifest.workspace_id == workspace_id)
        .order_by(HubRunManifest.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    orm = result.scalar_one_or_none()
    if orm is None:
        raise HTTPException(status_code=404, detail="No manifest found for workspace")
    return await _load_manifest(orm)


@router.get(
    "/manifests/{manifest_id}",
    response_model=DraftingRunManifest,
    operation_id="getManifestById",
)
async def get_manifest_by_id(
    manifest_id: uuid.UUID,
    _user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DraftingRunManifest:
    """Devuelve un manifest por su ID único."""
    orm = await session.get(HubRunManifest, manifest_id)
    if orm is None:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return await _load_manifest(orm)
