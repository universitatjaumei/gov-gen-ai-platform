"""9R.1.3 — WorkspaceState + BlockState + ReportTemplateDraft.

Tests RED → GREEN. Verifica el estado de runtime del DraftingCoreGraph y el contrato
del draft generado por el LLM.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from server.app.modules.redaccion.contracts.runtime import (
    ApprovalRecord,
    BlockState,
    Citation,
    ExtractionWarning,
    InputArtifact,
    InvalidBlockTransitionError,
    WorkspaceState,
)
from server.app.modules.redaccion.contracts.drafts import (
    DraftValidationError,
    ReportTemplateDraft,
    ReportTemplateDraftValidationResult,
)
from server.app.modules.redaccion.contracts.blocks import StaticTextBlock
from server.app.modules.redaccion.contracts.inputs import InputContract


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _block_state(status: str = "draft", kind: str = "STATIC_TEXT") -> BlockState:
    return BlockState(
        block_id="b1",
        kind=kind,
        status=status,
        content=None,
        citations=None,
        last_updated_by="system",
        updated_at=_now(),
        approval=None,
    )


def _minimal_workspace() -> WorkspaceState:
    return WorkspaceState(
        workspace_id=uuid4(),
        template_version_id=uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks={"b1": _block_state()},
        status="draft",
        warnings=[],
        run_manifest_id=None,
    )


def _minimal_draft() -> ReportTemplateDraft:
    return ReportTemplateDraft(
        proposed_profile="GENERIC_REPORT",
        proposed_sections=[],
        proposed_blocks=[StaticTextBlock(id="b1", title="Intro")],
        proposed_inputs=InputContract(),
        rationale="Informe genèric estàndard",
        model_used="claude-sonnet-4-6",
        prompt_version="v1.0",
    )


# ---------------------------------------------------------------------------
# WorkspaceState
# ---------------------------------------------------------------------------

class TestWorkspaceState:
    def test_workspace_state_serializes_with_block_status(self):
        ws = _minimal_workspace()
        data = ws.model_dump()
        assert data["blocks"]["b1"]["status"] == "draft"
        assert data["status"] == "draft"
        assert "workspace_id" in data

    def test_workspace_state_accepts_extraction_warnings(self):
        ws = _minimal_workspace()
        ws2 = ws.model_copy(update={
            "warnings": [ExtractionWarning(
                block_id="b1",
                message="Columna 'importe' no encontrada",
                kind="missing_data",
            )]
        })
        assert len(ws2.warnings) == 1
        assert ws2.warnings[0].kind == "missing_data"

    def test_workspace_state_inputs_keyed_by_slot_id(self):
        artifact = InputArtifact(
            slot_id="memoria",
            filename="memoria.pdf",
            storage_path="gs://bucket/memoria.pdf",
            size_bytes=102400,
            uploaded_at=_now(),
        )
        ws = _minimal_workspace()
        ws2 = ws.model_copy(update={"inputs": {"memoria": artifact}})
        assert ws2.inputs["memoria"].filename == "memoria.pdf"


# ---------------------------------------------------------------------------
# BlockState — transiciones
# ---------------------------------------------------------------------------

class TestBlockStateTransitions:
    def test_block_state_status_transition_valid_paths(self):
        bs = _block_state("draft")
        # draft → extracted (válido)
        bs.validate_transition("extracted")

        bs2 = _block_state("extracted")
        bs2.validate_transition("ai_generated")

        bs3 = _block_state("needs_review")
        bs3.validate_transition("approved")

        bs4 = _block_state("needs_review")
        bs4.validate_transition("rejected")

        bs5 = _block_state("approved")
        bs5.validate_transition("locked")

    def test_block_state_rejects_invalid_status_transition(self):
        # draft → approved sin pasar por needs_review
        bs = _block_state("draft")
        with pytest.raises(InvalidBlockTransitionError) as exc_info:
            bs.validate_transition("approved")
        assert exc_info.value.from_status == "draft"
        assert exc_info.value.to_status == "approved"

    def test_block_state_locked_has_no_valid_transitions(self):
        bs = _block_state("locked")
        with pytest.raises(InvalidBlockTransitionError):
            bs.validate_transition("draft")

    def test_block_state_rejected_can_retry_to_ai_generated(self):
        bs = _block_state("rejected")
        # No debe lanzar excepción
        bs.validate_transition("ai_generated")

    def test_block_state_with_approval_record(self):
        approval = ApprovalRecord(
            approved_by=uuid4(),
            approved_at=_now(),
            note="Revisat i acceptat",
        )
        bs = _block_state("approved")
        bs2 = bs.model_copy(update={"approval": approval})
        assert bs2.approval.note == "Revisat i acceptat"

    def test_block_state_with_citations(self):
        cit = Citation(source_document="memoria.pdf", page=3, excerpt="Total: 150.000 €")
        bs = _block_state("extracted")
        bs2 = bs.model_copy(update={"citations": [cit]})
        assert bs2.citations[0].source_document == "memoria.pdf"


# ---------------------------------------------------------------------------
# ReportTemplateDraft
# ---------------------------------------------------------------------------

class TestReportTemplateDraft:
    def test_report_template_draft_includes_model_and_prompt_version(self):
        draft = _minimal_draft()
        assert draft.model_used == "claude-sonnet-4-6"
        assert draft.prompt_version == "v1.0"
        assert draft.proposed_profile == "GENERIC_REPORT"

    def test_report_template_draft_requires_rationale(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ReportTemplateDraft(
                proposed_profile="GENERIC_REPORT",
                proposed_sections=[],
                proposed_blocks=[],
                proposed_inputs=InputContract(),
                # rationale missing
                model_used="claude-sonnet-4-6",
                prompt_version="v1.0",
            )

    def test_invalid_draft_returns_normalized_errors(self):
        result = ReportTemplateDraftValidationResult(
            ok=False,
            normalized_draft=None,
            errors=[
                DraftValidationError(field="proposed_blocks", message="No blocks defined"),
                DraftValidationError(field="proposed_profile", message="Unknown profile"),
            ],
        )
        assert not result.ok
        assert len(result.errors) == 2
        assert result.errors[0].field == "proposed_blocks"

    def test_valid_draft_result_contains_normalized_draft(self):
        result = ReportTemplateDraftValidationResult(
            ok=True,
            normalized_draft=_minimal_draft(),
            errors=[],
        )
        assert result.ok
        assert result.normalized_draft is not None
        assert result.normalized_draft.model_used == "claude-sonnet-4-6"
