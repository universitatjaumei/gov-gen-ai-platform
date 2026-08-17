"""PreviewBuilderService — construye PreviewPayload desde workspace + manifest (1C.3).

Deploy: edge
Rechaza con PendingBlocksError si hay bloques no aprobados ni locked.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from server.app.modules.redaccion.contracts.preview import (
    PreviewAuditEntry,
    PreviewBlock,
    PreviewPayload,
    PreviewSection,
    TocEntry,
)
from server.app.modules.redaccion.contracts.template import SectionContract

_APPROVED_STATES = frozenset({"approved", "locked"})
_NIL_UUID = UUID("00000000-0000-0000-0000-000000000000")
_section_adapter: TypeAdapter[list[SectionContract]] = TypeAdapter(list[SectionContract])


#: Los bloques cuyo texto lo escribió un modelo: los únicos que esperan una aprobación.
_TIPOS_DE_IA = frozenset({"AI_ASSISTED_TEXT", "AI_SUMMARY", "AI_REWRITE"})


def bloques_pendientes(bloques: list[Any]) -> list[str]:
    """Los que impiden la vista previa, que son solo los de IA sin aprobar.

    Exigirla a **todos** la hacía inalcanzable por construcción: nada transiciona un
    `STATIC_TEXT` o un `DETERMINISTIC_DATA` a `approved`, así que la pantalla respondía 409
    para siempre. Misma regla que el ensamblado final, y por el mismo motivo: lo que se
    revisa es lo que escribió el modelo.
    """
    return [
        b.block_id
        for b in bloques
        if b.kind in _TIPOS_DE_IA and b.status not in _APPROVED_STATES
    ]


class PendingBlocksError(Exception):
    """Raised when blocks are not yet approved or locked."""

    def __init__(self, pending_block_ids: list[str]) -> None:
        super().__init__(
            f"Cannot build preview: blocks pending — {pending_block_ids}"
        )
        self.pending_block_ids = pending_block_ids


class PreviewBuilderService:
    """Builds a PreviewPayload from current workspace state."""

    def __init__(
        self,
        workspace_repo: Any,
        block_repo: Any,
        template_version_repo: Any,
        manifest_repo: Any,
    ) -> None:
        self._workspace_repo = workspace_repo
        self._block_repo = block_repo
        self._template_version_repo = template_version_repo
        self._manifest_repo = manifest_repo

    async def build_payload(self, workspace_id: UUID) -> PreviewPayload:
        workspace = await self._workspace_repo.get(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace {workspace_id} not found")

        blocks = await self._block_repo.list(workspace_id)

        pending = bloques_pendientes(blocks)
        if pending:
            raise PendingBlocksError(pending)

        template_version = await self._template_version_repo.get(
            workspace.template_version_id
        )
        manifests = await self._manifest_repo.list(workspace_id)
        manifest = max(manifests, key=lambda m: m.created_at) if manifests else None

        sections = _extract_sections(
            template_version.spec_json if template_version else {}
        )
        block_map = {b.block_id: b for b in blocks}

        toc: list[TocEntry] = []
        body: list[PreviewSection] = []
        for sec in sections:
            toc.append(TocEntry(level=1, title=sec.title))
            preview_blocks = [
                _build_preview_block(block_map[bid])
                for bid in sec.block_ids
                if bid in block_map
            ]
            body.append(PreviewSection(level=1, title=sec.title, blocks=preview_blocks))

        audit_annex = _build_audit_annex(blocks)

        cover = PreviewSection(
            level=0,
            title=str(workspace_id),
            blocks=[],
        )

        return PreviewPayload(
            workspace_id=workspace_id,
            template_version_id=UUID(str(workspace.template_version_id)),
            cover=cover,
            toc=toc,
            body=body,
            audit_annex=audit_annex,
            manifest_id=UUID(str(manifest.id)) if manifest else _NIL_UUID,
            generated_at=datetime.now(timezone.utc),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_sections(spec_json: dict) -> list[SectionContract]:
    raw = spec_json.get("sections", [])
    return _section_adapter.validate_python(raw)


def _block_content_to_html(content: dict | None) -> str:
    if not content:
        return ""
    text = content.get("text") or content.get("value") or ""
    return f"<p>{_html.escape(str(text))}</p>" if text else ""


def _extract_citation_uuids(citations_json: list | None) -> list[UUID]:
    if not citations_json:
        return []
    result = []
    for cit in citations_json:
        if isinstance(cit, dict) and cit.get("chunk_id"):
            try:
                result.append(UUID(str(cit["chunk_id"])))
            except (ValueError, AttributeError):
                pass
    return result


def _build_preview_block(block: Any) -> PreviewBlock:
    return PreviewBlock(
        block_id=block.block_id,
        kind=block.kind,
        state=block.status,
        html=_block_content_to_html(block.content_json),
        citations=_extract_citation_uuids(block.citations_json),
    )


def _build_audit_annex(blocks: list[Any]) -> list[PreviewAuditEntry]:
    seen: dict[UUID, PreviewAuditEntry] = {}
    for block in blocks:
        for chunk_id in _extract_citation_uuids(block.citations_json):
            if chunk_id not in seen:
                seen[chunk_id] = PreviewAuditEntry(chunk_id=chunk_id)
    return list(seen.values())
