"""PreviewPayload contract — vista previa imprimible y anexo de auditoría (1C.3).

Deploy: edge
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TocEntry(BaseModel):
    level: int
    title: str


class PreviewBlock(BaseModel):
    block_id: str
    kind: str
    state: str
    html: str
    citations: list[UUID] = []
    # PRO.5 — el contenido estructurado y las imágenes, **sólo en proceso**.
    #
    # `exclude=True` a propósito: los dos existen para que la exportación a DOCX escriba una
    # tabla como tabla y un gráfico como imagen (volcaba `html` como párrafo de texto, así que
    # desde PRO.3 el documento llevaba `<table>…</table>` escrito dentro). En la respuesta HTTP
    # no aportan nada —el `html` ya lleva la imagen incrustada— y `bytes` no es serializable a
    # JSON: el intento devolvía un 500 al pedir la vista previa. Así el contrato del frontend
    # no cambia y el payload no lleva la imagen dos veces.
    content: dict | None = Field(default=None, exclude=True)
    images: dict[str, bytes] = Field(default_factory=dict, exclude=True)


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
