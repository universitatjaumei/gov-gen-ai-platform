"""Tests para PreviewBuilderService — TDD RED → GREEN (1C.3)."""
from __future__ import annotations

import pytest

from server.app.modules.redaccion.services.preview_builder import (
    PendingBlocksError,
    PreviewBuilderService,
)


class TestPreviewBuilder:

    @pytest.mark.asyncio
    async def test_payload_contains_only_approved_or_locked_blocks(
        self, builder: PreviewBuilderService, workspace_all_approved
    ) -> None:
        payload = await builder.build_payload(workspace_all_approved.id)
        for section in payload.body:
            for block in section.blocks:
                assert block.state in ("approved", "locked")

    @pytest.mark.asyncio
    async def test_returns_409_when_blocks_pending_review(
        self, builder: PreviewBuilderService, workspace_with_needs_review
    ) -> None:
        with pytest.raises(PendingBlocksError) as exc:
            await builder.build_payload(workspace_with_needs_review.id)
        assert len(exc.value.pending_block_ids) >= 1

    @pytest.mark.asyncio
    async def test_orders_blocks_by_template_section(
        self, builder: PreviewBuilderService, workspace_with_3_sections
    ) -> None:
        payload = await builder.build_payload(workspace_with_3_sections.id)
        titles = [s.title for s in payload.body]
        assert titles == ["Introducción", "Marco Legal", "Conclusiones"]

    @pytest.mark.asyncio
    async def test_export_service_uses_same_payload(
        self,
        builder: PreviewBuilderService,
        export_service,
        workspace_all_approved,
        storage_mock,
    ) -> None:
        preview_payload = await builder.build_payload(workspace_all_approved.id)
        await export_service.export(workspace_all_approved.id, format="docx")
        export_payload = export_service.last_payload_used
        assert export_payload.workspace_id == preview_payload.workspace_id
        assert [b.block_id for s in export_payload.body for b in s.blocks] == [
            b.block_id for s in preview_payload.body for b in s.blocks
        ]

    @pytest.mark.asyncio
    async def test_audit_annex_lists_all_chunks_used_by_approved_blocks(
        self, builder: PreviewBuilderService, workspace_with_citations
    ) -> None:
        payload = await builder.build_payload(workspace_with_citations.id)
        cited_ids = {c for s in payload.body for b in s.blocks for c in b.citations}
        annex_ids = {entry.chunk_id for entry in payload.audit_annex}
        assert cited_ids.issubset(annex_ids)
