"""Tests del DataTransformBlock (contract + handler + manifest) — 9R.5.8 (RED → GREEN)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from server.app.modules.redaccion.blocks.handlers import DataTransformHandler
from server.app.modules.redaccion.contracts.block_io import BlockReference
from server.app.modules.redaccion.contracts.blocks import (
    DataTransformBlock,
    DataTransformBlockConfig,
)
from server.app.modules.redaccion.contracts.runtime import BlockState, WorkspaceState
from server.app.modules.redaccion.services.transformation.operations import (
    FilterOp,
    GroupByOp,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _block_state(block_id: str, kind: str, status: str = "draft", content: dict | None = None) -> BlockState:
    return BlockState(
        block_id=block_id,
        kind=kind,
        status=status,
        content=content,
        last_updated_by="system",
        updated_at=_now(),
    )


def _state_with_source_rows(rows: list[dict]) -> WorkspaceState:
    return WorkspaceState(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks={
            "b_data": _block_state("b_data", kind="DETERMINISTIC_DATA", status="extracted",
                                   content={"rows": rows}),
            "b_dt":   _block_state("b_dt",   kind="DATA_TRANSFORM",     status="draft"),
        },
        block_outputs={"b_data": {"rows": rows}},
        status="drafting",
        warnings=[],
    )


# ---------------------------------------------------------------------------
# DataTransformBlockConfig contract
# ---------------------------------------------------------------------------

class TestDataTransformContract:

    def test_deterministic_requires_operations(self):
        with pytest.raises(Exception):
            DataTransformBlockConfig(
                mode="deterministic",
                source_block_ref=BlockReference(block_id="b_data"),
                operations=None,
            )

    def test_ai_requires_nl_instruction(self):
        with pytest.raises(Exception):
            DataTransformBlockConfig(
                mode="ai",
                source_block_ref=BlockReference(block_id="b_data"),
                nl_instruction=None,
            )

    def test_data_transform_block_is_in_discriminated_union(self):
        cfg = DataTransformBlockConfig(
            mode="deterministic",
            source_block_ref=BlockReference(block_id="b_data"),
            operations=[FilterOp(col="x", comparator=">", value=0)],
        )
        block = DataTransformBlock(id="b_dt", title="t", config=cfg)
        assert block.kind == "DATA_TRANSFORM"


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class TestDataTransformHandler:

    @pytest.mark.asyncio
    async def test_data_transform_block_handler_resolves_source_via_block_ref(self):
        rows = [
            {"region": "N", "units": 10},
            {"region": "S", "units": 20},
            {"region": "E", "units": 30},
        ]
        state = _state_with_source_rows(rows)
        cfg = DataTransformBlockConfig(
            mode="deterministic",
            source_block_ref=BlockReference(block_id="b_data"),
            operations=[FilterOp(col="units", comparator=">", value=15)],
        )
        block = DataTransformBlock(
            id="b_dt", title="filtrado",
            depends_on=[BlockReference(block_id="b_data")],
            config=cfg,
        )

        handler = DataTransformHandler()
        result = await handler.execute(block, state)

        assert "rows" in result
        assert len(result["rows"]) == 2
        assert all(r["units"] > 15 for r in result["rows"])
        assert result["operations_applied"][0]["op"] == "filter"
        assert result["model_used"] is None
        assert result["source_block_id"] == "b_data"

    def test_data_transform_block_persists_operations_in_manifest(self):
        cfg = DataTransformBlockConfig(
            mode="deterministic",
            source_block_ref=BlockReference(block_id="b_data"),
            operations=[
                FilterOp(col="units", comparator=">", value=15),
                GroupByOp(cols=["region"], agg_dict={"units": "sum"}),
            ],
        )
        block = DataTransformBlock(id="b_dt", title="x", config=cfg)
        handler = DataTransformHandler()

        manifest = handler.to_manifest(block)
        assert manifest["kind"] == "DATA_TRANSFORM"
        assert manifest["mode"] == "deterministic"
        ops = manifest["operations_applied"]
        assert len(ops) == 2
        assert ops[0]["op"] == "filter"
        assert ops[1]["op"] == "groupby"
        assert manifest["source_block_id"] == "b_data"

    @pytest.mark.asyncio
    async def test_data_transform_block_handler_ai_mode_invokes_llm(self):
        rows = [{"region": "N", "units": 10}, {"region": "S", "units": 20}]
        state = _state_with_source_rows(rows)

        ops_json = json.dumps({
            "mode": "operations",
            "operations": [{"op": "filter", "col": "units", "comparator": ">", "value": 15}],
        })
        llm = MagicMock()
        llm_resp = MagicMock(); llm_resp.content = ops_json
        llm.ainvoke = AsyncMock(return_value=llm_resp)

        cfg = DataTransformBlockConfig(
            mode="ai",
            source_block_ref=BlockReference(block_id="b_data"),
            nl_instruction="filtra unidades > 15",
        )
        block = DataTransformBlock(
            id="b_dt", title="x",
            depends_on=[BlockReference(block_id="b_data")],
            config=cfg,
        )

        handler = DataTransformHandler(llm=llm, model_name="claude-test")
        result = await handler.execute(block, state)
        assert len(result["rows"]) == 1
        assert result["model_used"] == "claude-test"
