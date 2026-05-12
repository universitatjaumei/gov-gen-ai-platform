"""Contratos de runtime del DraftingCoreGraph — 9R.1.3.

WorkspaceState es el estado que fluye por el grafo durante una ejecución.
BlockState tiene una máquina de estados explícita; las transiciones inválidas
levantan InvalidBlockTransitionError.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from server.app.modules.redaccion.contracts.template import ReportProfileId

# ---------------------------------------------------------------------------
# Estados
# ---------------------------------------------------------------------------

BlockStatus = Literal[
    "draft",
    "missing_input",
    "extracted",
    "ai_generated",
    "needs_review",
    "approved",
    "rejected",
    "locked",
]

WorkspaceStatus = Literal[
    "draft",
    "ingesting",
    "extracting",
    "drafting",
    "in_review",
    "assembled",
    "exported",
    "error",
]

# Transiciones válidas por estado origen
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft":         {"missing_input", "extracted", "ai_generated"},
    "missing_input": {"extracted"},
    "extracted":     {"ai_generated", "needs_review"},
    "ai_generated":  {"needs_review"},
    "needs_review":  {"approved", "rejected"},
    "rejected":      {"ai_generated", "draft"},
    "approved":      {"locked"},
    "locked":        set(),
}


# ---------------------------------------------------------------------------
# Excepción de transición inválida
# ---------------------------------------------------------------------------

class InvalidBlockTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Invalid block transition: {from_status!r} → {to_status!r}"
        )
        self.from_status = from_status
        self.to_status = to_status


# ---------------------------------------------------------------------------
# Tipos de apoyo
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    source_document: str
    page: int | None = None
    cell_ref: str | None = None
    excerpt: str | None = None


class ApprovalRecord(BaseModel):
    approved_by: UUID
    approved_at: datetime
    note: str | None = None


class InputArtifact(BaseModel):
    slot_id: str
    filename: str
    storage_path: str
    size_bytes: int
    uploaded_at: datetime


class ExtractionWarning(BaseModel):
    block_id: str | None = None
    message: str
    kind: str  # "missing_data" | "low_confidence" | "type_mismatch" | …


# ---------------------------------------------------------------------------
# BlockState
# ---------------------------------------------------------------------------

class BlockState(BaseModel):
    block_id: str
    kind: str
    status: BlockStatus
    content: dict | None = None
    citations: list[Citation] | None = None
    last_updated_by: Literal["system", "user", "ai"]
    updated_at: datetime
    approval: ApprovalRecord | None = None

    def validate_transition(self, new_status: BlockStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidBlockTransitionError(self.status, new_status)


# ---------------------------------------------------------------------------
# WorkspaceState
# ---------------------------------------------------------------------------

class WorkspaceState(BaseModel):
    workspace_id: UUID
    template_version_id: UUID
    report_profile: ReportProfileId
    inputs: dict[str, InputArtifact]
    blocks: dict[str, BlockState]
    block_outputs: dict[str, dict] = {}
    status: WorkspaceStatus
    warnings: list[ExtractionWarning]
    run_manifest_id: UUID | None = None
