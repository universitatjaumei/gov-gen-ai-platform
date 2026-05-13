"""Tests 9R.6.2 — DeterministicExtractionNode / DataQualityCheckNode / MissingDataQuestionNode."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from server.app.modules.redaccion.contracts.inputs import InputContract, InputSlot
from server.app.modules.redaccion.contracts.runtime import (
    BlockState,
    ExtractionWarning,
    InputArtifact,
    WorkspaceState,
)
from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ExportPolicy,
    ReportTemplateSpec,
    ReviewPolicy,
)
from server.app.modules.redaccion.contracts.ui import ReportUIContract
from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionProvenance,
    ExtractionResult,
    ExtractedMetric,
    ExtractedTable,
    ExtractionWarning as PipelineWarning,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_block_state(block_id: str, kind: str = "DETERMINISTIC_DATA", status: str = "missing_input") -> BlockState:
    return BlockState(
        block_id=block_id,
        kind=kind,
        status=status,
        last_updated_by="system",
        updated_at=_now(),
    )


def _make_spec(blocks_extra=None) -> ReportTemplateSpec:
    from server.app.modules.redaccion.contracts.blocks import DeterministicDataBlock

    blocks = [
        DeterministicDataBlock(id="b1", title="Datos Excel", source_pipeline="excel"),
    ]
    if blocks_extra:
        blocks.extend(blocks_extra)

    return ReportTemplateSpec(
        sections=[],
        blocks=blocks,
        input_contract=InputContract(
            required_slots=[
                InputSlot(slot_id="datos_excel", kind="excel", label={"es": "Datos Excel"}),
            ],
        ),
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
        blocks={"b1": _make_block_state("b1")},
        status="extracting",
        warnings=[],
        spec=_make_spec(),
        artifacts_normalized={"datos_excel": "bucket/datos.xlsx"},
    )
    defaults.update(overrides)
    return WorkspaceState(**defaults)


def _ok_result() -> ExtractionResult:
    return ExtractionResult(
        tables=[ExtractedTable(name="t1", headers=["A", "B"], rows=[["1", "2"]])],
        metrics=[ExtractedMetric(name="total", value=42)],
        provenance=ExtractionProvenance(
            pipeline_id="excel_pipeline_v1",
            source_ref="bucket/datos.xlsx",
            extracted_at=_now(),
        ),
    )


def _mock_factory(result: ExtractionResult | None = None) -> MagicMock:
    pipeline = MagicMock()
    pipeline.extract.return_value = result or _ok_result()
    factory = MagicMock()
    factory.get.return_value = pipeline
    return factory


# ---------------------------------------------------------------------------
# DeterministicExtractionNode
# ---------------------------------------------------------------------------

class TestDeterministicExtractionNode:

    @pytest.mark.asyncio
    async def test_deterministic_extraction_writes_to_block_content(self) -> None:
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            DeterministicExtractionNode,
        )

        factory = _mock_factory()
        state = _make_state()
        node = DeterministicExtractionNode(factory)

        patch = await node(state)

        block = patch["blocks"]["b1"]
        assert block.content is not None
        assert block.content["tables"][0]["name"] == "t1"
        assert block.content["metrics"][0]["name"] == "total"

    @pytest.mark.asyncio
    async def test_core_graph_runs_deterministic_extraction_before_ai(self) -> None:
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            DeterministicExtractionNode,
        )

        factory = _mock_factory()
        state = _make_state()
        node = DeterministicExtractionNode(factory)

        patch = await node(state)

        factory.get.assert_called_once_with("excel")
        assert patch["blocks"]["b1"].status == "extracted"

    @pytest.mark.asyncio
    async def test_core_graph_blocks_when_required_input_missing(self) -> None:
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            DeterministicExtractionNode,
        )

        factory = _mock_factory()
        state = _make_state(artifacts_normalized={})  # sin artefactos
        node = DeterministicExtractionNode(factory)

        patch = await node(state)

        factory.get.assert_not_called()
        warning_kinds = [w.kind for w in patch["warnings"]]
        assert "missing_input" in warning_kinds


# ---------------------------------------------------------------------------
# DataQualityCheckNode
# ---------------------------------------------------------------------------

class TestDataQualityCheckNode:

    @pytest.mark.asyncio
    async def test_data_quality_check_pauses_graph_on_critical_warning(self) -> None:
        from server.app.modules.redaccion.graph.nodes.data_quality_check import DataQualityCheckNode

        critical_warning = ExtractionWarning(
            block_id="b1",
            message="No tables found in the PDF.",
            kind="no_tables_found",
        )
        state = _make_state(warnings=[critical_warning])
        node = DataQualityCheckNode()

        patch = await node(state)

        assert patch.get("status") == "in_review"

    @pytest.mark.asyncio
    async def test_data_quality_check_passes_without_critical_warnings(self) -> None:
        from server.app.modules.redaccion.graph.nodes.data_quality_check import DataQualityCheckNode

        state = _make_state(warnings=[])
        node = DataQualityCheckNode()

        patch = await node(state)

        assert "status" not in patch


# ---------------------------------------------------------------------------
# MissingDataQuestionNode
# ---------------------------------------------------------------------------

class TestMissingDataQuestionNode:

    @pytest.mark.asyncio
    async def test_missing_data_question_emits_actionable_message(self) -> None:
        from server.app.modules.redaccion.graph.nodes.missing_data_question import MissingDataQuestionNode

        warning = ExtractionWarning(
            block_id="datos_excel",
            message="Faltan tablas.",
            kind="no_tables_found",
        )
        state = _make_state(warnings=[warning])
        node = MissingDataQuestionNode()

        patch = await node(state)

        hitl_questions = [w for w in patch["warnings"] if w.kind == "hitl_question"]
        assert len(hitl_questions) == 1
        assert "datos_excel" in hitl_questions[0].message
        assert patch["status"] == "in_review"
