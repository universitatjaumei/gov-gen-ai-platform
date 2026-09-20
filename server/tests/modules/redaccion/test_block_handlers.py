"""9R.3.1 + 9R.3.2 — BlockHandlers + BlockStateMachine.

Tests RED → GREEN.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers para BlockState
# ---------------------------------------------------------------------------

def _make_state(status: str = "draft", block_id: str = "b1"):
    from server.app.modules.redaccion.contracts.runtime import BlockState
    return BlockState(
        block_id=block_id,
        kind="STATIC_TEXT",
        status=status,
        content=None,
        citations=None,
        last_updated_by="system",
        updated_at=_now(),
        approval=None,
    )


def _make_workspace(blocks: dict | None = None):
    from server.app.modules.redaccion.contracts.runtime import WorkspaceState
    return WorkspaceState(
        workspace_id=uuid4(),
        template_version_id=uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks=blocks or {},
        status="draft",
        warnings=[],
        run_manifest_id=None,
    )


# ---------------------------------------------------------------------------
# 9R.3.1 — Handlers
# ---------------------------------------------------------------------------

class TestBlockHandlerContract:
    def test_block_contract_has_required_fields(self):
        from server.app.modules.redaccion.blocks.handlers import (
            StaticTextHandler,
            AIAssistedTextHandler,
            DeterministicDataHandler,
        )
        assert hasattr(StaticTextHandler, "uses_ai")
        assert hasattr(StaticTextHandler, "requires_approval")
        assert StaticTextHandler.uses_ai is False

        assert AIAssistedTextHandler.uses_ai is True
        assert AIAssistedTextHandler.requires_approval is True

        assert DeterministicDataHandler.uses_ai is False

    def test_ai_block_requires_review_policy(self):
        from server.app.modules.redaccion.blocks.handlers import (
            AIAssistedTextHandler,
            AISummaryHandler,
            AIRewriteHandler,
        )
        for cls in (AIAssistedTextHandler, AISummaryHandler, AIRewriteHandler):
            assert cls.requires_approval is True, f"{cls.__name__} must require approval"

    def test_data_block_requires_extraction_source(self):
        from server.app.modules.redaccion.blocks.handlers import (
            DeterministicDataHandler,
        )
        from server.app.modules.redaccion.contracts.blocks import DeterministicDataBlock
        handler = DeterministicDataHandler()
        block = DeterministicDataBlock(id="b1", title="Datos", source_pipeline="EXCEL")
        # valid block passes
        handler.validate(block)

    def test_chart_block_depends_on_data_block(self):
        from server.app.modules.redaccion.blocks.handlers import ChartHandler
        from server.app.modules.redaccion.contracts.blocks import ChartBlock
        handler = ChartHandler()
        block = ChartBlock(id="b_chart", title="Gràfic", data_block_ref="b_data")
        assert block.data_block_ref == "b_data"
        handler.validate(block)

    def test_chart_handler_rejects_missing_data_block_ref(self):
        """ChartHandler.validate raises if data_block_ref not present in workspace blocks."""
        from server.app.modules.redaccion.blocks.handlers import (
            ChartHandler,
            BlockHandlerValidationError,
        )
        from server.app.modules.redaccion.contracts.blocks import ChartBlock
        handler = ChartHandler()
        block = ChartBlock(id="b_chart", title="Gràfic", data_block_ref="b_missing")
        ws = _make_workspace(blocks={})  # b_missing not in workspace
        with pytest.raises(BlockHandlerValidationError, match="data_block_ref"):
            handler.validate_in_context(block, ws)

    def test_review_gate_blocks_final_assembly_until_approved(self):
        from server.app.modules.redaccion.blocks.handlers import (
            ReviewGateHandler,
            BlockHandlerValidationError,
        )
        from server.app.modules.redaccion.contracts.blocks import ReviewGateBlock
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        handler = ReviewGateHandler()
        block = ReviewGateBlock(
            id="b_gate", title="Porta", review_policy_id="rp-1",
            depends_on=[BlockReference(block_id="b_ai", projection="raw")],
        )
        # workspace has b_ai in needs_review → gate should block
        ws = _make_workspace(blocks={"b_ai": _make_state("needs_review", "b_ai")})
        with pytest.raises(BlockHandlerValidationError, match="not approved"):
            handler.validate_in_context(block, ws)

    def test_block_contract_is_serializable(self):
        from server.app.modules.redaccion.blocks.handlers import StaticTextHandler
        from server.app.modules.redaccion.contracts.blocks import StaticTextBlock
        handler = StaticTextHandler()
        block = StaticTextBlock(id="b1", title="Intro", content="Hola")
        manifest = handler.to_manifest(block)
        assert isinstance(manifest, dict)
        assert manifest["block_id"] == "b1"
        assert manifest["kind"] == "STATIC_TEXT"

    def test_ai_handler_records_model_and_prompt_version_to_manifest(self):
        from server.app.modules.redaccion.blocks.handlers import AIAssistedTextHandler
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock
        handler = AIAssistedTextHandler()
        block = AIAssistedTextBlock(
            id="b_ai", title="Text IA",
            ai_prompt_template_id="generic_report_v1",
            review_policy_id="rp-1",
        )
        manifest = handler.to_manifest(block)
        assert "ai_prompt_template_id" in manifest
        assert manifest["ai_prompt_template_id"] == "generic_report_v1"
        assert "review_policy_id" in manifest


# ---------------------------------------------------------------------------
# 9R.3.2 — BlockStateMachine
# ---------------------------------------------------------------------------

class TestBlockStateMachine:
    def test_block_state_machine_allows_extract_from_draft(self):
        from server.app.modules.redaccion.services.block_state_machine import (
            BlockStateMachine,
            BlockTransitionEvent,
        )
        machine = BlockStateMachine()
        block = _make_state("draft")
        new_block, audit = machine.transition(block, BlockTransitionEvent.EXTRACT)
        assert new_block.status == "extracted"
        assert audit.from_status == "draft"
        assert audit.to_status == "extracted"

    def test_block_state_machine_blocks_direct_ai_to_approved(self):
        from server.app.modules.redaccion.services.block_state_machine import (
            BlockStateMachine,
            BlockTransitionEvent,
        )
        from server.app.modules.redaccion.contracts.runtime import InvalidBlockTransitionError
        machine = BlockStateMachine()
        block = _make_state("ai_generated")
        with pytest.raises(InvalidBlockTransitionError):
            machine.transition(block, BlockTransitionEvent.APPROVE)

    def test_block_state_machine_locked_block_is_terminal(self):
        from server.app.modules.redaccion.services.block_state_machine import (
            BlockStateMachine,
            BlockTransitionEvent,
        )
        from server.app.modules.redaccion.contracts.runtime import InvalidBlockTransitionError
        machine = BlockStateMachine()
        block = _make_state("locked")
        with pytest.raises(InvalidBlockTransitionError):
            machine.transition(block, BlockTransitionEvent.EXTRACT)

    def test_block_state_machine_rejected_block_can_regenerate(self):
        from server.app.modules.redaccion.services.block_state_machine import (
            BlockStateMachine,
            BlockTransitionEvent,
        )
        machine = BlockStateMachine()
        block = _make_state("rejected")
        new_block, audit = machine.transition(block, BlockTransitionEvent.REGENERATE)
        assert new_block.status == "ai_generated"

    def test_final_assembler_blocks_when_required_block_not_approved(self):
        from server.app.modules.redaccion.services.block_state_machine import (
            check_assembly_readiness,
        )
        blocks = {
            "b1": _make_state("approved", "b1"),
            "b2": _make_state("needs_review", "b2"),
        }
        from server.app.modules.redaccion.contracts.blocks import (
            StaticTextBlock,
            AIAssistedTextBlock,
        )
        contracts = [
            StaticTextBlock(id="b1", title="T1", required=True),
            AIAssistedTextBlock(
                id="b2", title="T2", required=True,
                ai_prompt_template_id="p1", review_policy_id="r1",
            ),
        ]
        blocking = check_assembly_readiness(blocks, contracts)
        assert "b2" in blocking
        assert "b1" not in blocking

    def test_block_transition_emits_audit_event(self):
        from server.app.modules.redaccion.services.block_state_machine import (
            BlockStateMachine,
            BlockTransitionEvent,
        )
        machine = BlockStateMachine()
        block = _make_state("needs_review")
        _, audit = machine.transition(block, BlockTransitionEvent.APPROVE)
        assert audit.event == BlockTransitionEvent.APPROVE.value
        assert audit.from_status == "needs_review"
        assert audit.to_status == "approved"
        assert audit.timestamp is not None
