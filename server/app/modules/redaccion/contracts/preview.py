"""PreviewPayload contract — vista previa imprimible y anexo de auditoría (1C.3).

Deploy: edge
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TocEntry(BaseModel):
    level: int
    title: str


class PreviewBlock(BaseModel):
    block_id: str
    kind: str
    state: str
    html: str
    citations: list[UUID] = []


class PreviewSection(BaseModel):
    level: int
    title: str
    blocks: list[PreviewBlock] = []


class PreviewAuditEntry(BaseModel):
    chunk_id: UUID
    source_url: str | None = None
    source_filename: str | None = None
    page: int | None = None
    model_used: str | None = None
    prompt_version: str | None = None
    approvals: list[UUID] = []


class PreviewPayload(BaseModel):
    workspace_id: UUID
    template_version_id: UUID
    cover: PreviewSection
    toc: list[TocEntry] = []
    body: list[PreviewSection] = []
    audit_annex: list[PreviewAuditEntry] = []
    manifest_id: UUID
    generated_at: datetime
