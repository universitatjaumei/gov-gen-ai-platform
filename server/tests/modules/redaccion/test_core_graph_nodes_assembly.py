"""Tests 9R.6.4 — UserReviewGateNode / ApplyUserEditsNode / FinalAssemblerNode (RED → GREEN)."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

import pytest

from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock, StaticTextBlock
from server.app.modules.redaccion.contracts.inputs import InputContract
from server.app.modules.redaccion.contracts.runtime import BlockState, WorkspaceState
from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ExportPolicy,
    ReportTemplateSpec,
    ReviewPolicy,
    SectionContract,
)
from server.app.modules.redaccion.contracts.ui import ReportUIContract


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _block(block_id: str, kind: str, status: str, content: dict | None = None) -> BlockState:
    return BlockState(
        block_id=block_id,
        kind=kind,
        status=status,
        content=content,
        last_updated_by="system",
        updated_at=_now(),
    )


def _make_spec(
    block_ids_in_section: list[str] | None = None,
    extra_blocks=None,
) -> ReportTemplateSpec:
    blocks = [
        AIAssistedTextBlock(
            id="b_ai", title="Resumen", ai_prompt_template_id="t1", review_policy_id="r1",
        ),
    ]
    if extra_blocks:
        blocks.extend(extra_blocks)

    section_block_ids = block_ids_in_section or [b.id for b in blocks]
    return ReportTemplateSpec(
        sections=[SectionContract(id="s1", title="Sección 1", order=1, block_ids=section_block_ids)],
        blocks=blocks,
        input_contract=InputContract(),
        ui_contract=ReportUIContract(
            wizard_steps=[], dropzones=[], manual_fields=[],
            block_editor_enabled=False, ai_review_panel_enabled=False,
            preview_layout="markdown",
        ),
        ai_block_policy=AIBlockPolicy.ALLOWED,
        review_policy=ReviewPolicy.NONE,
        export_policy=ExportPolicy.DOCX,
    )


def _make_state(**overrides) -> WorkspaceState:
    defaults = dict(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks={"b_ai": _block("b_ai", "AI_ASSISTED_TEXT", "ai_generated",
                               content={"text": "Texto IA"})},
        status="drafting",
        warnings=[],
        spec=_make_spec(),
    )
    defaults.update(overrides)
    return WorkspaceState(**defaults)


# ---------------------------------------------------------------------------
# UserReviewGateNode
# ---------------------------------------------------------------------------

class TestUserReviewGateNode:

    @pytest.mark.asyncio
    async def test_review_gate_pauses_graph_until_all_ai_blocks_approved(self) -> None:
        from server.app.modules.redaccion.graph.nodes.review_gate import UserReviewGateNode

        state = _make_state(blocks={
            "b_ai": _block("b_ai", "AI_ASSISTED_TEXT", "ai_generated", content={"text": "X"}),
        })
        node = UserReviewGateNode()
        patch = await node(state)

        assert patch["blocks"]["b_ai"].status == "needs_review"
        assert patch.get("status") == "in_review"

    @pytest.mark.asyncio
    async def test_review_gate_continues_when_all_ai_blocks_approved(self) -> None:
        from server.app.modules.redaccion.graph.nodes.review_gate import UserReviewGateNode

        state = _make_state(blocks={
            "b_ai": _block("b_ai", "AI_ASSISTED_TEXT", "approved", content={"text": "X"}),
        })
        node = UserReviewGateNode()
        patch = await node(state)

        assert "status" not in patch  # no pausa


# ---------------------------------------------------------------------------
# FinalAssemblerNode
# ---------------------------------------------------------------------------

class TestFinalAssemblerNode:

    @pytest.mark.asyncio
    async def test_final_assembler_only_includes_approved_blocks(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        spec = _make_spec(
            block_ids_in_section=["b_approved", "b_pending"],
            extra_blocks=[
                StaticTextBlock(id="b_approved", title="Aprobado", content="Contenido aprobado"),
                StaticTextBlock(id="b_pending",  title="Pendiente", content=""),
            ],
        )
        state = _make_state(
            spec=spec,
            blocks={
                "b_ai":       _block("b_ai",       "AI_ASSISTED_TEXT", "needs_review"),
                "b_approved": _block("b_approved", "STATIC_TEXT",      "approved",
                                     content={"text": "Contenido aprobado"}),
                "b_pending":  _block("b_pending",  "STATIC_TEXT",      "needs_review"),
            },
        )
        node = FinalAssemblerNode()
        patch = await node(state)

        doc = patch["final_document"]
        assert "Aprobado" in doc
        assert "Pendiente" not in doc

    @pytest.mark.asyncio
    async def test_final_assembler_computes_document_hash(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        spec = _make_spec(
            block_ids_in_section=["b_ai"],
            extra_blocks=[],
        )
        state = _make_state(
            spec=spec,
            blocks={
                "b_ai": _block("b_ai", "AI_ASSISTED_TEXT", "approved",
                               content={"text": "Texto final"}),
            },
        )
        node = FinalAssemblerNode()
        patch = await node(state)

        expected_hash = hashlib.sha256(patch["final_document"].encode()).hexdigest()
        assert patch["final_document_hash"] == expected_hash
        assert patch["status"] == "assembled"

    @pytest.mark.asyncio
    async def test_review_gate_prevents_unapproved_ai_blocks_in_final_document(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        state = _make_state(blocks={
            "b_ai": _block("b_ai", "AI_ASSISTED_TEXT", "needs_review", content={"text": "Borrador"}),
        })
        node = FinalAssemblerNode()
        patch = await node(state)

        # needs_review no se incluye → documento vacío o sin el bloque
        assert "Borrador" not in patch.get("final_document", "")


# ---------------------------------------------------------------------------
# ApplyUserEditsNode
# ---------------------------------------------------------------------------

class TestApplyUserEditsNode:

    @pytest.mark.asyncio
    async def test_apply_user_edits_preserves_original_ai_content(self) -> None:
        from server.app.modules.redaccion.graph.nodes.apply_user_edits import ApplyUserEditsNode

        original_content = {"text": "Texto generado por IA", "model_used": "claude"}
        state = _make_state(
            blocks={
                "b_ai": _block("b_ai", "AI_ASSISTED_TEXT", "needs_review",
                               content=original_content),
            },
            user_edits={"b_ai": {"text": "Texto corregido por el usuario"}},
        )
        node = ApplyUserEditsNode()
        patch = await node(state)

        b = patch["blocks"]["b_ai"]
        assert b.content["text"] == "Texto corregido por el usuario"
        assert b.original_ai_content == original_content
        assert b.last_updated_by == "user"
