"""Tests 9R.6.5 — AuditLogNode + DraftingRunManifest + TracingService (RED → GREEN)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from server.app.modules.redaccion.contracts.runtime import BlockState, WorkspaceState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_state(**overrides) -> WorkspaceState:
    defaults = dict(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks={},
        status="assembled",
        warnings=[],
        final_document_hash="abc123",
    )
    defaults.update(overrides)
    return WorkspaceState(**defaults)


def _mock_repo() -> MagicMock:
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=None)
    return repo


def _mock_tracing() -> MagicMock:
    span = MagicMock()
    span.set_attribute = MagicMock()
    span.add_event = MagicMock()
    span.end = MagicMock()
    tracing = MagicMock()
    tracing.open_trace = MagicMock(return_value=span)
    tracing.node_span = MagicMock(return_value=span)
    return tracing, span


# ---------------------------------------------------------------------------
# AuditLogNode — manifest
# ---------------------------------------------------------------------------

class TestAuditLogNode:

    @pytest.mark.asyncio
    async def test_core_graph_generates_run_manifest(self) -> None:
        from server.app.modules.redaccion.graph.nodes.audit_log import AuditLogNode
        from server.app.modules.redaccion.graph.tracing import NoOpTracingService

        repo = _mock_repo()
        node = AuditLogNode(repo, NoOpTracingService())
        state = _make_state()

        patch = await node(state)

        assert patch.get("run_manifest_id") is not None

    @pytest.mark.asyncio
    async def test_run_manifest_persisted_after_audit_log_node(self) -> None:
        from server.app.modules.redaccion.graph.nodes.audit_log import AuditLogNode
        from server.app.modules.redaccion.graph.tracing import NoOpTracingService

        repo = _mock_repo()
        node = AuditLogNode(repo, NoOpTracingService())
        await node(_make_state())

        repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_workspace_run_manifest_id_updated(self) -> None:
        from server.app.modules.redaccion.graph.nodes.audit_log import AuditLogNode
        from server.app.modules.redaccion.graph.tracing import NoOpTracingService

        repo = _mock_repo()
        node = AuditLogNode(repo, NoOpTracingService())
        patch = await node(_make_state())

        assert isinstance(patch["run_manifest_id"], uuid.UUID)

    @pytest.mark.asyncio
    async def test_core_graph_generates_manifest_even_on_error(self) -> None:
        from server.app.modules.redaccion.graph.nodes.audit_log import AuditLogNode
        from server.app.modules.redaccion.graph.tracing import NoOpTracingService

        repo = _mock_repo()
        node = AuditLogNode(repo, NoOpTracingService())
        # Estado en error — el nodo debe ejecutarse igualmente
        state = _make_state(status="error", final_document_hash=None)
        patch = await node(state)

        repo.save.assert_awaited_once()
        assert patch.get("run_manifest_id") is not None

    @pytest.mark.asyncio
    async def test_core_graph_supports_admin_template_and_ad_hoc_workspace(self) -> None:
        from server.app.modules.redaccion.graph.nodes.audit_log import AuditLogNode
        from server.app.modules.redaccion.graph.tracing import NoOpTracingService

        repo = _mock_repo()
        node = AuditLogNode(repo, NoOpTracingService())

        for profile in ("GENERIC_REPORT", "ANNUAL_REPORT", "DOCTORATE_PROGRAM_REPORT"):
            repo.save.reset_mock()
            state = _make_state(report_profile=profile)
            patch = await node(state)
            repo.save.assert_awaited_once()
            assert patch["run_manifest_id"] is not None


# ---------------------------------------------------------------------------
# TracingService — instrumentación Langfuse
# ---------------------------------------------------------------------------

class TestTracingService:

    @pytest.mark.asyncio
    async def test_core_graph_opens_root_langfuse_span_with_workspace_id(self) -> None:
        from server.app.modules.redaccion.graph.nodes.audit_log import AuditLogNode

        tracing, span = _mock_tracing()
        state = _make_state()
        node = AuditLogNode(_mock_repo(), tracing)
        await node(state)

        tracing.open_trace.assert_called_once_with(
            "redaccion.run",
            workspace_id=str(state.workspace_id),
            template_version_id=str(state.template_version_id),
        )

    @pytest.mark.asyncio
    async def test_root_span_attribute_run_manifest_id_set_after_audit_log(self) -> None:
        from server.app.modules.redaccion.graph.nodes.audit_log import AuditLogNode

        tracing, span = _mock_tracing()
        node = AuditLogNode(_mock_repo(), tracing)
        patch = await node(_make_state())

        span.set_attribute.assert_called_once_with(
            "run_manifest_id", str(patch["run_manifest_id"])
        )
        span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_each_node_opens_child_span_under_root(self) -> None:
        from server.app.modules.redaccion.graph.tracing import traced_node

        tracing, span = _mock_tracing()

        async def dummy_node(state):
            return {}

        wrapped = traced_node(dummy_node, tracing, "my_node")
        await wrapped(_make_state())

        tracing.node_span.assert_called_once_with("my_node")
        span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_node_records_model_and_token_attributes_on_span(self) -> None:
        from server.app.modules.redaccion.contracts.runtime import BlockState
        from server.app.modules.redaccion.graph.tracing import traced_node

        tracing, span = _mock_tracing()

        ai_block = BlockState(
            block_id="b_ai", kind="AI_ASSISTED_TEXT", status="ai_generated",
            content={"text": "X", "model_used": "claude-test", "prompt_version": "v1"},
            last_updated_by="ai", updated_at=_now(),
        )

        async def ai_node(state):
            return {"blocks": {"b_ai": ai_block}}

        wrapped = traced_node(ai_node, tracing, "ai_assist_draft")
        await wrapped(_make_state())

        set_calls = {c.args[0]: c.args[1] for c in span.set_attribute.call_args_list}
        assert set_calls.get("model_used") == "claude-test"
        assert set_calls.get("prompt_version") == "v1"

    @pytest.mark.asyncio
    async def test_failed_node_emits_error_event_on_span(self) -> None:
        from server.app.modules.redaccion.graph.tracing import traced_node

        tracing, span = _mock_tracing()

        async def failing_node(state):
            raise RuntimeError("LLM timeout")

        wrapped = traced_node(failing_node, tracing, "ai_assist_draft")

        with pytest.raises(RuntimeError):
            await wrapped(_make_state())

        span.add_event.assert_called_once()
        event_name = span.add_event.call_args.args[0]
        assert event_name == "error"
        kwargs = span.add_event.call_args.kwargs
        assert kwargs.get("type") == "RuntimeError"
        assert "LLM timeout" in kwargs.get("message", "")
        span.end.assert_called_once()
