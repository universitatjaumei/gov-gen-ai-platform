"""Contratos del patch de autosave del workspace (1C.1).

Versiones optimistas:
- `expected_workspace_version` se compara con `hub_workspaces.version`.
- `expected_block_version` se compara con `hub_workspace_blocks.version`.
Si alguno está desactualizado → ConflictError → 409.

Deploy: edge
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


BlockState = Literal[
    "draft",
    "missing_input",
    "extracted",
    "ai_generated",
    "needs_review",
    "approved",
    "rejected",
    "locked",
    "failed",
]


class BlockUpdate(BaseModel):
    block_id: UUID
    state: BlockState | None = None
    content: dict | None = None
    expected_block_version: int = Field(..., ge=1)


class WorkspaceStatePatch(BaseModel):
    expected_workspace_version: int = Field(..., ge=1)
    block_updates: list[BlockUpdate] = Field(default_factory=list)


class WorkspaceStatePatchResponse(BaseModel):
    workspace_version: int
    updated_block_versions: dict[UUID, int]
    saved_at: datetime


class WorkspaceStateConflictResponse(BaseModel):
    """Body de 409: el cliente puede inspeccionar y refetchear o resolver."""

    current_workspace_version: int
    conflicting_block_ids: list[UUID] = Field(default_factory=list)
