"""Block transition endpoints — 9R.8.1.

Deploy: edge
Approve, reject, regenerate, edit blocks and resume workspace from review gate.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.core.storage import StorageService, get_storage_service
from server.app.modules.redaccion.contracts.runtime import BlockState, InvalidBlockTransitionError
from server.app.modules.redaccion.database.models import (
    HubWorkspace,
    HubWorkspaceAuditEvent,
    HubWorkspaceBlock,
)
from server.app.modules.redaccion.services.block_state_machine import (
    BlockStateMachine,
    BlockTransitionEvent,
)
from server.app.modules.redaccion.contracts.state_update import (
    WorkspaceStatePatch,
    WorkspaceStatePatchResponse,
    WorkspaceStateConflictResponse,
)
from server.app.modules.redaccion.services.autosave_service import (
    ConflictError,
    InvalidTransitionError as AutosaveInvalidTransitionError,
    WorkspaceAutosaveService,
    WorkspaceNotFoundError,
)
from server.app.modules.redaccion.services.workspace_run_service import (
    InputsNotReadyError,
    WorkspaceRunService,
)
from server.app.modules.redaccion.contracts.preview import PreviewPayload
from server.app.modules.redaccion.services.preview_builder import (
    PendingBlocksError,
    PreviewBuilderService,
)
from server.app.modules.redaccion.database.repos import (
    RunManifestRepo,
    ReportTemplateVersionRepo,
    WorkspaceBlockRepo,
    WorkspaceRepo,
)

router = APIRouter(prefix="/redaccion/workspaces", tags=["redaccion-workspaces"])

_sm = BlockStateMachine()


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

class BlockTransitionOut(BaseModel):
    block_id: str
    kind: str
    status: str
    content: dict | None = None
    updated_at: datetime


class EditBlockRequest(BaseModel):
    content: dict


class ResumeOut(BaseModel):
    workspace_id: uuid.UUID
    status: str


class InputUploadOut(BaseModel):
    slot_id: str
    filename: str
    storage_path: str
    size_bytes: int
    uploaded_at: datetime


class RunStartedOut(BaseModel):
    run_id: uuid.UUID
    workspace_id: uuid.UUID
    status: str  # queued | running | completed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _block_to_state(block: HubWorkspaceBlock) -> BlockState:
    return BlockState(
        block_id=block.block_id,
        kind=block.kind,
        status=block.status,  # type: ignore[arg-type]
        content=block.content_json,
        last_updated_by="user",
        updated_at=block.updated_at,
        failure_kind=block.failure_kind,  # type: ignore[arg-type]
        last_error_message=block.last_error_message,
        retry_attempts=block.retry_attempts,
    )


def _block_out(block: HubWorkspaceBlock) -> BlockTransitionOut:
    return BlockTransitionOut(
        block_id=block.block_id,
        kind=block.kind,
        status=block.status,
        content=block.content_json,
        updated_at=block.updated_at,
    )


async def _get_workspace(
    workspace_id: uuid.UUID,
    user: UserInfo,
    session: AsyncSession,
) -> HubWorkspace:
    workspace = await session.get(HubWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if str(workspace.owner_id) != user.user_id:
        raise HTTPException(status_code=403, detail="Not the workspace owner")
    return workspace


async def _get_block(
    workspace_id: uuid.UUID,
    block_id: str,
    session: AsyncSession,
) -> HubWorkspaceBlock:
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
    return block


async def _apply_transition(
    workspace_id: uuid.UUID,
    block_id: str,
    event: BlockTransitionEvent,
    user: UserInfo,
    session: AsyncSession,
) -> BlockTransitionOut:
    workspace = await _get_workspace(workspace_id, user, session)
    block = await _get_block(workspace_id, block_id, session)

    block_state = _block_to_state(block)
    try:
        new_state, audit = _sm.transition(block_state, event, actor=user.user_id)
    except InvalidBlockTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    block.status = new_state.status
    block.updated_at = new_state.updated_at

    audit_event = HubWorkspaceAuditEvent(
        workspace_id=workspace.id,
        block_id=block.block_id,
        event=audit.event,
        from_status=audit.from_status,
        to_status=audit.to_status,
        actor=audit.actor,
    )
    session.add(audit_event)
    await session.commit()

    return _block_out(block)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.patch(
    "/{workspace_id}/blocks/{block_id}/approve",
    response_model=BlockTransitionOut,
    operation_id="approveBlock",
)
async def approve_block(
    workspace_id: uuid.UUID,
    block_id: str,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BlockTransitionOut:
    """Aprueba un bloque en estado needs_review."""
    return await _apply_transition(workspace_id, block_id, BlockTransitionEvent.APPROVE, user, session)


@router.patch(
    "/{workspace_id}/blocks/{block_id}/reject",
    response_model=BlockTransitionOut,
    operation_id="rejectBlock",
)
async def reject_block(
    workspace_id: uuid.UUID,
    block_id: str,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BlockTransitionOut:
    """Rechaza un bloque en estado needs_review."""
    return await _apply_transition(workspace_id, block_id, BlockTransitionEvent.REJECT, user, session)


@router.patch(
    "/{workspace_id}/blocks/{block_id}/regenerate",
    response_model=BlockTransitionOut,
    operation_id="regenerateBlock",
)
async def regenerate_block(
    workspace_id: uuid.UUID,
    block_id: str,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BlockTransitionOut:
    """Solicita regeneración IA de un bloque rechazado (solo ese bloque)."""
    return await _apply_transition(workspace_id, block_id, BlockTransitionEvent.REGENERATE, user, session)


@router.patch(
    "/{workspace_id}/blocks/{block_id}/edit",
    response_model=BlockTransitionOut,
    operation_id="editBlock",
)
async def edit_block(
    workspace_id: uuid.UUID,
    block_id: str,
    body: EditBlockRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BlockTransitionOut:
    """Sobreescribe el contenido de un bloque; registra el original en auditoría."""
    await _get_workspace(workspace_id, user, session)
    block = await _get_block(workspace_id, block_id, session)

    original_content = block.content_json

    audit_event = HubWorkspaceAuditEvent(
        workspace_id=workspace_id,
        block_id=block.block_id,
        event="edit",
        from_status=block.status,
        to_status=block.status,
        actor=user.user_id,
        metadata_json={"original_content": original_content},
    )
    session.add(audit_event)

    block.content_json = body.content
    block.updated_at = datetime.now(timezone.utc)

    await session.commit()
    return _block_out(block)


@router.post(
    "/{workspace_id}/resume",
    response_model=ResumeOut,
    operation_id="resumeWorkspace",
)
async def resume_workspace(
    workspace_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResumeOut:
    """Reanuda el grafo de redacción desde la review gate."""
    workspace = await _get_workspace(workspace_id, user, session)

    if workspace.status != "in_review":
        raise HTTPException(
            status_code=422,
            detail=f"Workspace must be in 'in_review' state to resume, got '{workspace.status}'",
        )

    workspace.status = "drafting"

    audit_event = HubWorkspaceAuditEvent(
        workspace_id=workspace_id,
        block_id=None,
        event="resume",
        from_status="in_review",
        to_status="drafting",
        actor=user.user_id,
    )
    session.add(audit_event)
    await session.commit()

    return ResumeOut(workspace_id=workspace_id, status="drafting")


# ---------------------------------------------------------------------------
# 9R.10.2 — Upload de inputs y arranque de ejecución
# ---------------------------------------------------------------------------

@router.post(
    "/{workspace_id}/inputs/{slot_id}",
    response_model=InputUploadOut,
    status_code=status.HTTP_201_CREATED,
    operation_id="uploadWorkspaceInput",
)
async def upload_workspace_input(
    workspace_id: uuid.UUID,
    slot_id: str,
    file: UploadFile = File(...),
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage_service),
) -> InputUploadOut:
    """Sube un archivo a un slot de inputs del workspace.

    El archivo se persiste en StorageService con clave
    `redaccion/{workspace_id}/inputs/{slot_id}/{filename}` y se registra una
    entrada en `HubWorkspace.inputs_json[slot_id]`. Si el slot ya tenía un
    archivo, se sobreescribe (los archivos previos quedan en storage como
    huérfanos hasta la limpieza periódica).
    """
    workspace = await _get_workspace(workspace_id, user, session)

    content = await file.read()
    filename = file.filename or f"{slot_id}.bin"
    storage_path = f"redaccion/{workspace_id}/inputs/{slot_id}/{filename}"
    await storage.put(storage_path, content)

    uploaded_at = datetime.now(timezone.utc)
    entry = {
        "slot_id": slot_id,
        "filename": filename,
        "storage_path": storage_path,
        "size_bytes": len(content),
        "uploaded_at": uploaded_at.isoformat(),
    }

    inputs = workspace.inputs_json
    if not isinstance(inputs, dict):
        inputs = {}
    inputs[slot_id] = entry
    workspace.inputs_json = inputs

    audit_event = HubWorkspaceAuditEvent(
        workspace_id=workspace_id,
        block_id=None,
        event="input_uploaded",
        from_status=workspace.status,
        to_status=workspace.status,
        actor=user.user_id,
        metadata_json={"slot_id": slot_id, "filename": filename, "size_bytes": len(content)},
    )
    session.add(audit_event)
    await session.commit()

    return InputUploadOut(
        slot_id=slot_id,
        filename=filename,
        storage_path=storage_path,
        size_bytes=len(content),
        uploaded_at=uploaded_at,
    )


@router.post(
    "/{workspace_id}/run",
    response_model=RunStartedOut,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="runWorkspace",
)
async def run_workspace(
    workspace_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RunStartedOut:
    """Encola la ejecución del DraftingCoreGraph para el workspace.

    Transiciona `workspace.status` de `draft|ingesting` a `drafting`. La
    ejecución real del grafo se enchufa a un background task en follow-ups; el
    endpoint devuelve un `run_id` inmediato con `status='queued'` para que el
    frontend pueda consultar el manifest cuando esté disponible.
    """
    workspace = await _get_workspace(workspace_id, user, session)

    svc = WorkspaceRunService(session=session)
    try:
        # session.get ya está hecho por _get_workspace; start_run lo repite a
        # través del repo. En MVP es aceptable: el coste de un get adicional
        # es despreciable frente a la simplicidad del wire-up.
        result = await svc.start_run(workspace_id, validate=False)
    except InputsNotReadyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    audit_event = HubWorkspaceAuditEvent(
        workspace_id=workspace_id,
        block_id=None,
        event="run_started",
        from_status=workspace.status,
        to_status="drafting",
        actor=user.user_id,
        metadata_json={"run_id": str(result.run_id)},
    )
    session.add(audit_event)
    await session.commit()

    return RunStartedOut(
        run_id=result.run_id,
        workspace_id=workspace_id,
        status=result.status,
    )


@router.patch(
    "/{workspace_id}/state",
    response_model=WorkspaceStatePatchResponse,
    operation_id="patchWorkspaceState",
    responses={
        409: {"model": WorkspaceStateConflictResponse, "description": "Optimistic conflict"},
        422: {"description": "Invalid BlockState transition"},
        404: {"description": "Workspace not found or not owned by user"},
    },
)
async def patch_workspace_state(
    workspace_id: uuid.UUID,
    patch: WorkspaceStatePatch,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceStatePatchResponse:
    """Autosave atómico (1C.1) con concurrencia optimista.

    - 200: aplicado, devuelve nuevas versiones.
    - 409: workspace_version o block_version desactualizada (con `current_workspace_version`
      y `conflicting_block_ids`).
    - 422: transición de BlockState inválida.
    - 404: workspace inexistente o no pertenece al usuario.
    """
    service = WorkspaceAutosaveService(session=session)
    try:
        return await service.apply_patch(workspace_id, user.user_id, patch)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found") from exc
    except ConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "current_workspace_version": exc.current_workspace_version,
                "conflicting_block_ids": [str(b) for b in exc.conflicting_block_ids],
            },
        ) from exc
    except AutosaveInvalidTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# 1C.3 — Vista previa imprimible
# ---------------------------------------------------------------------------

@router.get(
    "/{workspace_id}/preview",
    response_model=PreviewPayload,
    operation_id="getWorkspacePreview",
    responses={
        409: {"description": "Blocks pending review"},
        404: {"description": "Workspace not found"},
    },
)
async def get_workspace_preview(
    workspace_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PreviewPayload:
    """Devuelve el PreviewPayload para vista previa e impresión.

    Deploy: edge
    Retorna 409 si hay bloques en estado distinto a approved/locked.
    """
    await _get_workspace(workspace_id, user, session)

    builder = PreviewBuilderService(
        workspace_repo=WorkspaceRepo(session),
        block_repo=WorkspaceBlockRepo(session),
        template_version_repo=ReportTemplateVersionRepo(session),
        manifest_repo=RunManifestRepo(session),
    )
    try:
        return await builder.build_payload(workspace_id)
    except PendingBlocksError as exc:
        raise HTTPException(
            status_code=409,
            detail={"pending_block_ids": exc.pending_block_ids},
        ) from exc
