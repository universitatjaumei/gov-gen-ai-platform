"""Block transition endpoints — 9R.8.1.

Deploy: edge
Approve, reject, regenerate, edit blocks and resume workspace from review gate.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
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
