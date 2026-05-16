"""Tests del DataTransformationNode + cadena con ChartBlock — 9R.5.8 (RED → GREEN)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd
import pytest

from server.app.modules.redaccion.blocks.handlers import ChartHandler
from server.app.modules.redaccion.contracts.block_io import BlockReference
from server.app.modules.redaccion.contracts.blocks import (
    ChartBlock,
    ChartBlockConfig,
    DataTransformBlock,
    DataTransformBlockConfig,
    DeterministicDataBlock,
)
from server.app.modules.redaccion.contracts.inputs import InputContract
from server.app.modules.redaccion.contracts.runtime import BlockState, WorkspaceState
from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ExportPolicy,
    ReportTemplateSpec,
    ReviewPolicy,
)
from server.app.modules.redaccion.contracts.ui import ReportUIContract
from server.app.modules.redaccion.graph.nodes.data_transformation import DataTransformationNode
from server.app.modules.redaccion.services.transformation.operations import (
    FilterOp,
    GroupByOp,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bs(block_id: str, kind: str, status: str = "draft", content: dict | None = None) -> BlockState:
    return BlockState(
        block_id=block_id, kind=kind, status=status, content=content,
        last_updated_by="system", updated_at=_now(),
    )


def _empty_ui() -> ReportUIContract:
    return ReportUIContract(
        wizard_steps=[], dropzones=[], manual_fields=[],
        block_editor_enabled=False, ai_review_panel_enabled=False,
        preview_layout="markdown",
    )


def _make_state(spec: ReportTemplateSpec, blocks: dict[str, BlockState], block_outputs: dict[str, dict] | None = None) -> WorkspaceState:
    return WorkspaceState(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks=blocks,
        block_outputs=block_outputs or {},
        status="drafting",
        warnings=[],
        spec=spec,
        artifacts_normalized={},
    )


class TestDataTransformationNode:

    @pytest.mark.asyncio
    async def test_data_transform_node_runs_between_extraction_and_ai(self):
        """El nodo debe procesar bloques DATA_TRANSFORM sobre datos ya extraídos
        y dejar el output disponible en block_outputs para los nodos siguientes."""
        source_rows = [
            {"region": "N", "units": 10},
            {"region": "S", "units": 20},
            {"region": "E", "units": 30},
        ]
        cfg = DataTransformBlockConfig(
            mode="deterministic",
            source_block_ref=BlockReference(block_id="b_data"),
            operations=[FilterOp(col="units", comparator=">", value=15)],
        )
        dt_block = DataTransformBlock(
            id="b_dt", title="filtrado",
            depends_on=[BlockReference(block_id="b_data")],
            config=cfg,
        )
        spec = ReportTemplateSpec(
            sections=[],
            blocks=[
                DeterministicDataBlock(id="b_data", title="Datos", source_pipeline="excel"),
                dt_block,
            ],
            input_contract=InputContract(),
            ui_contract=_empty_ui(),
            ai_block_policy=AIBlockPolicy.ALLOWED,
            review_policy=ReviewPolicy.NONE,
            export_policy=ExportPolicy.DOCX,
        )
        state = _make_state(
            spec,
            blocks={
                "b_data": _bs("b_data", kind="DETERMINISTIC_DATA", status="extracted",
                              content={"rows": source_rows}),
                "b_dt":   _bs("b_dt",   kind="DATA_TRANSFORM",     status="draft"),
            },
            block_outputs={"b_data": {"rows": source_rows}},
        )

        node = DataTransformationNode(llm_service=None)
        patch = await node(state)

        assert "blocks" in patch
        assert patch["blocks"]["b_dt"].status == "extracted"
        rows = patch["blocks"]["b_dt"].content["rows"]
        assert len(rows) == 2
        assert all(r["units"] > 15 for r in rows)
        # block_outputs available downstream
        assert patch["block_outputs"]["b_dt"]["rows"] == rows

    @pytest.mark.asyncio
    async def test_data_transform_node_marks_failed_on_invalid_operation(self):
        """Un fallo en un DATA_TRANSFORM se aísla en el bloque (failure_kind=script_failed),
        no aborta el grafo."""
        cfg = DataTransformBlockConfig(
            mode="deterministic",
            source_block_ref=BlockReference(block_id="b_data"),
            # operations requires a "join" with no resolver → raises ValueError at execute time.
            operations=[
                {"op": "join", "other_block_ref": "b_missing", "on": "region"},  # type: ignore[list-item]
            ],
        )
        dt_block = DataTransformBlock(
            id="b_dt", title="x",
            depends_on=[BlockReference(block_id="b_data")],
            config=cfg,
        )
        spec = ReportTemplateSpec(
            sections=[], blocks=[
                DeterministicDataBlock(id="b_data", title="Datos", source_pipeline="excel"),
                dt_block,
            ],
            input_contract=InputContract(), ui_contract=_empty_ui(),
            ai_block_policy=AIBlockPolicy.ALLOWED, review_policy=ReviewPolicy.NONE,
            export_policy=ExportPolicy.DOCX,
        )
        rows = [{"region": "N", "units": 1}]
        state = _make_state(
            spec,
            blocks={
                "b_data": _bs("b_data", kind="DETERMINISTIC_DATA", status="extracted", content={"rows": rows}),
                "b_dt":   _bs("b_dt",   kind="DATA_TRANSFORM",     status="extracted"),
            },
            block_outputs={"b_data": {"rows": rows}},
        )

        node = DataTransformationNode(llm_service=None)
        patch = await node(state)

        assert patch["blocks"]["b_dt"].status == "failed"
        assert patch["blocks"]["b_dt"].failure_kind in {"script_failed", "validation_failed"}


# ---------------------------------------------------------------------------
# Chain with ChartBlock consuming DATA_TRANSFORM output
# ---------------------------------------------------------------------------

class TestDataTransformChainsWithChart:

    @pytest.mark.asyncio
    async def test_data_transform_block_chains_with_chart_block_consuming_output(self):
        """ChartBlock con data_block_ref apuntando al DATA_TRANSFORM debe leer
        las filas transformadas y renderizar un gráfico determinista."""
        source_rows = [
            {"region": "N", "units": 10},
            {"region": "N", "units": 15},
            {"region": "S", "units": 20},
            {"region": "S", "units": 25},
            {"region": "E", "units": 30},
        ]
        dt_cfg = DataTransformBlockConfig(
            mode="deterministic",
            source_block_ref=BlockReference(block_id="b_data"),
            operations=[GroupByOp(cols=["region"], agg_dict={"units": "sum"})],
        )
        dt_block = DataTransformBlock(
            id="b_dt", title="agrupado",
            depends_on=[BlockReference(block_id="b_data")],
            config=dt_cfg,
        )
        chart_block = ChartBlock(
            id="b_chart", title="bar",
            data_block_ref="b_dt",
            config=ChartBlockConfig(chart_type="bar", x_axis="region", y_axis="units"),
        )
        spec = ReportTemplateSpec(
            sections=[],
            blocks=[
                DeterministicDataBlock(id="b_data", title="Datos", source_pipeline="excel"),
                dt_block, chart_block,
            ],
            input_contract=InputContract(), ui_contract=_empty_ui(),
            ai_block_policy=AIBlockPolicy.ALLOWED, review_policy=ReviewPolicy.NONE,
            export_policy=ExportPolicy.DOCX,
        )
        state = _make_state(
            spec,
            blocks={
                "b_data":  _bs("b_data",  "DETERMINISTIC_DATA", "extracted", {"rows": source_rows}),
                "b_dt":    _bs("b_dt",    "DATA_TRANSFORM",     "draft"),
                "b_chart": _bs("b_chart", "CHART",              "draft"),
            },
            block_outputs={"b_data": {"rows": source_rows}},
        )

        # 1. Run DATA_TRANSFORM node first.
        node = DataTransformationNode(llm_service=None)
        patch = await node(state)
        merged_blocks = {**state.blocks, **patch["blocks"]}
        merged_outputs = {**state.block_outputs, **patch["block_outputs"]}
        next_state = state.model_copy(update={"blocks": merged_blocks, "block_outputs": merged_outputs})

        # 2. ChartHandler consumes the transformed rows.
        chart_handler = ChartHandler()
        chart_result = await chart_handler.execute(chart_block, next_state)
        assert chart_result["mode"] == "deterministic"
        assert isinstance(chart_result["image_bytes"], bytes)
        assert chart_result["image_bytes"][:4] == b"\x89PNG"

        # Verify DATA_TRANSFORM rows aggregated as expected.
        dt_rows = next_state.blocks["b_dt"].content["rows"]
        n_row = next(r for r in dt_rows if r["region"] == "N")
        assert n_row["units"] == 25
