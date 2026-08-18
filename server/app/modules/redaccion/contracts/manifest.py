"""DraftingRunManifest — trazabilidad de cada ejecución del DraftingCoreGraph (9R.6.5 / 9R.9.1).

Frozen: el manifest es inmutable una vez emitido. No hay endpoint de actualización.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from server.app.modules.redaccion.contracts.runtime import (
    ApprovalRecord,
    Citation,
    ExtractionWarning,
)
from server.app.modules.redaccion.services.anonymization.run_context import (
    AnonymizationSummary,
)


class FailedBlockInfo(BaseModel):
    block_id: str
    failure_kind: str
    last_error_message: str | None = None
    retry_attempts: int = 0


class UploadedDocumentInfo(BaseModel):
    slot_id: str
    filename: str
    storage_path: str
    size_bytes: int
    uploaded_at: datetime


class InputContractValidationResult(BaseModel):
    valid: bool
    missing_required: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExtractedBlockSummary(BaseModel):
    block_id: str
    kind: str
    status: str
    extraction_strategy: str | None = None
    warning_count: int = 0


class AIBlockSummary(BaseModel):
    block_id: str
    kind: str
    status: str
    model_used: str | None = None
    prompt_version: str | None = None
    #: SEG.1 — de qué se apoyó el modelo para escribir esto. `anchored` = sólo las tablas que el
    #: apartado declara; `full` = todo el informe, que es el alcance de las plantillas antiguas.
    #: Una valoración cuya fuente no consta no se puede auditar, así que consta.
    context_scope: str | None = None
    context_block_ids: list[str] = Field(default_factory=list)


class DraftingRunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    template_id: UUID | None = None
    template_version_id: UUID
    report_profile: str
    uploaded_documents: list[UploadedDocumentInfo] = Field(default_factory=list)
    input_contract_validation: InputContractValidationResult = Field(
        default_factory=lambda: InputContractValidationResult(valid=True)
    )
    extracted_blocks: list[ExtractedBlockSummary] = Field(default_factory=list)
    ai_blocks: list[AIBlockSummary] = Field(default_factory=list)
    model_used: str | None = None
    prompt_versions: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    warnings: list[ExtractionWarning] = Field(default_factory=list)
    user_approvals: list[ApprovalRecord] = Field(default_factory=list)
    failed_blocks: list[FailedBlockInfo] = Field(default_factory=list)
    final_document_hash: str | None = None
    status_at_close: str
    # Fase 13 — sólo metadata (counts_by_type, mode). Sin originales ni sintéticos.
    anonymization_summary: AnonymizationSummary | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
