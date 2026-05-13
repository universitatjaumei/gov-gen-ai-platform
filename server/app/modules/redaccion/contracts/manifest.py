"""DraftingRunManifest — trazabilidad de cada ejecución del DraftingCoreGraph (9R.6.5 / 9R.9.1).

Versión inicial con los campos mínimos necesarios para AuditLogNode.
9R.9.1 añadirá UploadedDocumentInfo, ExtractedBlockSummary, AIBlockSummary y el endpoint REST.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field

from server.app.modules.redaccion.contracts.runtime import ApprovalRecord, ExtractionWarning


class FailedBlockInfo(BaseModel):
    block_id: str
    failure_kind: str
    last_error_message: str | None = None
    retry_attempts: int = 0


class DraftingRunManifest(BaseModel):
    id: UUID
    workspace_id: UUID
    template_version_id: UUID
    report_profile: str
    warnings: list[ExtractionWarning] = Field(default_factory=list)
    user_approvals: list[ApprovalRecord] = Field(default_factory=list)
    failed_blocks: list[FailedBlockInfo] = Field(default_factory=list)
    final_document_hash: str | None = None
    status_at_close: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
