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

from server.app.api.deps import get_current_user, get_session, require_module
from server.app.modules.redaccion.contracts.manifest import DraftingRunManifest
from server.app.modules.redaccion.database.models import HubRunManifest, HubWorkspace
from server.app.routers.redaccion._actor import es_propietario

router = APIRouter(prefix="/redaccion", tags=["redaccion-manifests"],
    # INF.7 — el modulo se exige a nivel de router: asi no se puede olvidar en un
    # endpoint nuevo del mismo fichero, que es como se abrieron los agujeros que SEC.8.1
    # tuvo que cerrar uno a uno.
    dependencies=[Depends(require_module("informes"))],
)


async def _load_manifest(orm: HubRunManifest) -> DraftingRunManifest:
    return DraftingRunManifest.model_validate(orm.payload_json)


async def _assert_propietario(session: AsyncSession, workspace_id, user) -> None:
    """SEC.8.1: el manifest lleva el `payload_json` de la ejecución —lo extraído del
    expediente, los bloques generados—, así que su lectura tiene que estar tan protegida
    como el workspace del que sale. Estos dos endpoints declaraban el usuario y no lo
    usaban: bastaba un UUID para leer el contenido ajeno.
    """
    workspace = await session.get(HubWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not es_propietario(user.user_id, workspace.owner_id):
        raise HTTPException(status_code=403, detail="Not the workspace owner")


@router.get(
    "/workspaces/{workspace_id}/manifest",
    response_model=DraftingRunManifest,
    operation_id="getWorkspaceManifest",
)
async def get_workspace_manifest(
    workspace_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DraftingRunManifest:
    """Devuelve el manifest más reciente del workspace."""
    await _assert_propietario(session, workspace_id, user)
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
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DraftingRunManifest:
    """Devuelve un manifest por su ID único."""
    orm = await session.get(HubRunManifest, manifest_id)
    if orm is None:
        raise HTTPException(status_code=404, detail="Manifest not found")
    await _assert_propietario(session, orm.workspace_id, user)
    return await _load_manifest(orm)
