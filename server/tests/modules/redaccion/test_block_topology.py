"""9R.3.3 — BlockReference + projection + topological sort + cycle detection.

Tests RED → GREEN.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_block_state(status: str = "draft", block_id: str = "b1"):
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


def _make_workspace(blocks=None, block_outputs=None):
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
        block_outputs=block_outputs or {},
    )


# ---------------------------------------------------------------------------
# BlockReference
# ---------------------------------------------------------------------------

class TestBlockReference:
    def test_block_reference_serializable_in_openapi_with_discriminator(self):
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        ref = BlockReference(block_id="b1", projection="raw")
        schema = BlockReference.model_json_schema()
        assert "block_id" in str(schema)
        assert "projection" in str(schema)
        data = ref.model_dump()
        ref2 = BlockReference(**data)
        assert ref2.block_id == "b1"
        assert ref2.projection == "raw"
        assert ref2.field_path is None

    def test_block_reference_field_projection_requires_field_path(self):
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="field_path"):
            BlockReference(block_id="b1", projection="field", field_path=None)

    def test_block_reference_field_projection_accepts_field_path(self):
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        ref = BlockReference(block_id="b1", projection="field", field_path="rows[0].total")
        assert ref.field_path == "rows[0].total"


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------

class TestBlockTopologySort:
    def test_topology_sort_orders_blocks_by_dependencies(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import StaticTextBlock

        topology = BlockTopology()
        block_a = StaticTextBlock(id="a", title="A", depends_on=[])
        block_b = StaticTextBlock(
            id="b", title="B",
            depends_on=[BlockReference(block_id="a", projection="raw")],
        )
        block_c = StaticTextBlock(
            id="c", title="C",
            depends_on=[BlockReference(block_id="b", projection="raw")],
        )
        # Pass in reverse order to verify sort works
        sorted_blocks = topology.sort([block_c, block_b, block_a])
        ids = [b.id for b in sorted_blocks]
        assert ids.index("a") < ids.index("b")
        assert ids.index("b") < ids.index("c")

    def test_topology_detect_cycle_returns_offending_block_ids(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import StaticTextBlock

        topology = BlockTopology()
        block_x = StaticTextBlock(
            id="x", title="X",
            depends_on=[BlockReference(block_id="y", projection="raw")],
        )
        block_y = StaticTextBlock(
            id="y", title="Y",
            depends_on=[BlockReference(block_id="x", projection="raw")],
        )
        offenders = topology.detect_cycles([block_x, block_y])
        assert len(offenders) > 0
        assert set(offenders) == {"x", "y"}

    def test_draft_validator_rejects_cyclic_depends_on_with_422(self):
        """detect_cycles returns offending blocks; a DraftValidator (9R.4.2) will
        use this to return HTTP 422 with loc pointing to the offending block."""
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import StaticTextBlock

        topology = BlockTopology()
        a = StaticTextBlock(id="a", title="A", depends_on=[BlockReference(block_id="b", projection="raw")])
        b = StaticTextBlock(id="b", title="B", depends_on=[BlockReference(block_id="c", projection="raw")])
        c = StaticTextBlock(id="c", title="C", depends_on=[BlockReference(block_id="a", projection="raw")])
        offenders = topology.detect_cycles([a, b, c])
        assert set(offenders) == {"a", "b", "c"}

    def test_acyclic_graph_returns_empty_offenders(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import StaticTextBlock

        topology = BlockTopology()
        a = StaticTextBlock(id="a", title="A", depends_on=[])
        b = StaticTextBlock(id="b", title="B", depends_on=[BlockReference(block_id="a", projection="raw")])
        assert topology.detect_cycles([a, b]) == []


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------

class TestBlockProjection:
    def test_projection_raw_returns_full_output(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock

        topology = BlockTopology()
        block = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="r1",
            depends_on=[BlockReference(block_id="b_data", projection="raw")],
        )
        ws = _make_workspace(block_outputs={"b_data": {"rows": [1, 2, 3], "total": 6}})
        inputs = topology.resolve_inputs(ws, block)
        assert inputs["b_data"] == {"rows": [1, 2, 3], "total": 6}

    def test_projection_summary_returns_summary_field_when_present(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock

        topology = BlockTopology()
        block = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="r1",
            depends_on=[BlockReference(block_id="b_data", projection="summary")],
        )
        ws = _make_workspace(block_outputs={"b_data": {"summary": "Resumen corto", "rows": [1, 2]}})
        inputs = topology.resolve_inputs(ws, block)
        assert inputs["b_data"] == "Resumen corto"

    def test_projection_summary_falls_back_to_truncated_string_when_no_summary(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock

        topology = BlockTopology()
        block = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="r1",
            depends_on=[BlockReference(block_id="b_data", projection="summary")],
        )
        big_output = {"value": "x" * 2000}
        ws = _make_workspace(block_outputs={"b_data": big_output})
        inputs = topology.resolve_inputs(ws, block)
        assert isinstance(inputs["b_data"], str)
        assert len(inputs["b_data"]) <= 1000

    def test_projection_field_resolves_dot_path(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock

        topology = BlockTopology()
        block = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="r1",
            depends_on=[BlockReference(block_id="b_data", projection="field", field_path="summary")],
        )
        ws = _make_workspace(block_outputs={"b_data": {"summary": "Texto corto"}})
        inputs = topology.resolve_inputs(ws, block)
        assert inputs["b_data"] == "Texto corto"

    def test_projection_field_resolves_index_path(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock

        topology = BlockTopology()
        block = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="r1",
            depends_on=[BlockReference(block_id="b_data", projection="field", field_path="rows[1].total")],
        )
        ws = _make_workspace(block_outputs={
            "b_data": {"rows": [{"total": 10}, {"total": 99}]}
        })
        inputs = topology.resolve_inputs(ws, block)
        assert inputs["b_data"] == 99

    def test_projection_field_rejects_unsafe_expressions(self):
        from server.app.modules.redaccion.services.block_topology import (
            BlockTopology,
            UnsafeFieldPathError,
        )
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock

        topology = BlockTopology()
        for unsafe_path in ["eval('x')", "__class__", "os.system('rm -rf /')"]:
            block = AIAssistedTextBlock(
                id="b_ai", title="AI",
                ai_prompt_template_id="p1", review_policy_id="r1",
                depends_on=[BlockReference(
                    block_id="b_data", projection="field", field_path=unsafe_path
                )],
            )
            ws = _make_workspace(block_outputs={"b_data": {"value": 1}})
            with pytest.raises(UnsafeFieldPathError):
                topology.resolve_inputs(ws, block)

    def test_ai_node_reads_dependencies_via_projection_not_state(self):
        """resolve_inputs reads from block_outputs, not from state.blocks content."""
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock

        topology = BlockTopology()
        block = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="r1",
            depends_on=[BlockReference(block_id="b_data", projection="raw")],
        )
        # state.blocks has content=None but block_outputs has the real extraction
        ws = _make_workspace(
            blocks={"b_data": _make_block_state("extracted", "b_data")},
            block_outputs={"b_data": {"rows": [1, 2, 3]}},
        )
        inputs = topology.resolve_inputs(ws, block)
        assert inputs["b_data"] == {"rows": [1, 2, 3]}
        # state.blocks["b_data"].content is None; inputs came from block_outputs
        assert ws.blocks["b_data"].content is None


# ---------------------------------------------------------------------------
# Dependency readiness
# ---------------------------------------------------------------------------

class TestBlockDependencyChecks:
    def test_block_blocked_until_dependencies_approved_or_locked(self):
        from server.app.modules.redaccion.services.block_topology import BlockTopology
        from server.app.modules.redaccion.contracts.block_io import BlockReference
        from server.app.modules.redaccion.contracts.blocks import AIAssistedTextBlock

        topology = BlockTopology()
        block = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="r1",
            depends_on=[BlockReference(block_id="b_data", projection="raw")],
        )
        ws_blocking = _make_workspace(blocks={"b_data": _make_block_state("draft", "b_data")})
        blocking = topology.check_dependencies_ready(block, ws_blocking)
        assert "b_data" in blocking

        ws_ok = _make_workspace(blocks={"b_data": _make_block_state("approved", "b_data")})
        blocking_ok = topology.check_dependencies_ready(block, ws_ok)
        assert "b_data" not in blocking_ok

    def test_block_outputs_persisted_to_workspace_state(self):
        from server.app.modules.redaccion.contracts.runtime import WorkspaceState
        ws = _make_workspace()
        assert hasattr(ws, "block_outputs")
        assert isinstance(ws.block_outputs, dict)
        ws2 = ws.model_copy(update={"block_outputs": {"b1": {"value": 42}}})
        assert ws2.block_outputs["b1"]["value"] == 42
