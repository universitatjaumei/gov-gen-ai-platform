"""Tests 9R.6.6 — Fallos controlados: BlockState=failed, BlockExecutor, propagación de dependencias (RED→GREEN)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.app.modules.redaccion.contracts.runtime import (
    BlockState,
    WorkspaceBlockedByFailedBlocksError,
    WorkspaceState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _block(block_id: str, status: str, kind: str = "DETERMINISTIC_DATA", **extra) -> BlockState:
    return BlockState(
        block_id=block_id,
        kind=kind,
        status=status,
        last_updated_by="system",
        updated_at=_now(),
        **extra,
    )


def _make_state(**overrides) -> WorkspaceState:
    defaults = dict(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks={},
        status="drafting",
        warnings=[],
    )
    defaults.update(overrides)
    return WorkspaceState(**defaults)


def _mock_tracing():
    span = MagicMock()
    span.set_attribute = MagicMock()
    span.add_event = MagicMock()
    span.end = MagicMock()
    tracing = MagicMock()
    tracing.open_trace = MagicMock(return_value=span)
    tracing.node_span = MagicMock(return_value=span)
    return tracing, span


def _make_spec(blocks_cfg: list[dict]):
    """Construye un ReportTemplateSpec mínimo con los bloques indicados."""
    from server.app.modules.redaccion.contracts.template import (
        ReportTemplateSpec,
        SectionContract,
        InputContract,
        AIBlockPolicy,
        ReviewPolicy,
        ExportPolicy,
    )
    from server.app.modules.redaccion.contracts.ui import ReportUIContract
    from server.app.modules.redaccion.contracts.blocks import (
        DeterministicDataBlock,
        AIAssistedTextBlock,
    )

    spec_blocks = []
    for cfg in blocks_cfg:
        kind = cfg.get("kind", "DETERMINISTIC_DATA")
        if kind == "DETERMINISTIC_DATA":
            spec_blocks.append(DeterministicDataBlock(
                id=cfg["id"],
                title=cfg.get("title", cfg["id"]),
                required=cfg.get("required", False),
                depends_on=cfg.get("depends_on", []),
                source_pipeline=cfg.get("source_pipeline", "excel"),
                order=cfg.get("order", 0),
            ))
        elif kind in ("AI_ASSISTED_TEXT", "AI_SUMMARY", "AI_REWRITE"):
            spec_blocks.append(AIAssistedTextBlock(
                id=cfg["id"],
                title=cfg.get("title", cfg["id"]),
                required=cfg.get("required", False),
                depends_on=cfg.get("depends_on", []),
                ai_prompt_template_id=cfg.get("prompt_id", "prompt_v1"),
                review_policy_id="required",
                order=cfg.get("order", 0),
            ))

    return ReportTemplateSpec(
        sections=[SectionContract(id="s1", title="Section 1", order=0, block_ids=[b["id"] for b in blocks_cfg])],
        blocks=spec_blocks,
        input_contract=InputContract(required_slots=[], optional_slots=[]),
        ui_contract=ReportUIContract(
            wizard_steps=[], dropzones=[], manual_fields=[],
            block_editor_enabled=False, ai_review_panel_enabled=False,
            preview_layout="markdown",
        ),
        ai_block_policy=AIBlockPolicy.ALLOWED,
        review_policy=ReviewPolicy.REQUIRED,
        export_policy=ExportPolicy.PDF,
    )


# ---------------------------------------------------------------------------
# 1. BlockState — máquina de estados con subtipos de fallo
# ---------------------------------------------------------------------------

class TestBlockStateMachine:

    def test_block_state_machine_supports_failed_state_with_subtypes(self) -> None:
        for fk in ("extraction_failed", "ai_failed", "script_failed", "validation_failed"):
            b = _block("b1", "draft")
            failed = b.model_copy(update={
                "status": "failed",
                "failure_kind": fk,
                "last_error_message": "some error",
            })
            assert failed.status == "failed"
            assert failed.failure_kind == fk

    def test_block_state_machine_failed_to_regenerate_returns_to_correct_origin_state(self) -> None:
        # failed → extracted (valid transition for ai regenerate)
        b = _block("b1", "failed", failure_kind="ai_failed")
        b.validate_transition("extracted")  # must not raise

        # failed → draft (valid transition for extraction retry)
        b2 = _block("b1", "failed", failure_kind="extraction_failed")
        b2.validate_transition("draft")  # must not raise

        # failed → ai_generated (valid transition)
        b3 = _block("b1", "failed", failure_kind="ai_failed")
        b3.validate_transition("ai_generated")  # must not raise


# ---------------------------------------------------------------------------
# 2. BlockExecutor — política de retry
# ---------------------------------------------------------------------------

class TestBlockExecutor:

    @pytest.mark.asyncio
    async def test_block_executor_retries_once_on_llm_timeout(self) -> None:
        from server.app.modules.redaccion.services.block_executor import BlockExecutor, LLMTimeoutError

        call_count = 0

        async def flaky_node(block, state):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMTimeoutError("timeout")
            return {"ok": True}

        tracing, span = _mock_tracing()
        executor = BlockExecutor(tracing, retry_delay_seconds=0)
        state = _make_state()
        result = await executor.execute(flaky_node, MagicMock(id="b1"), state)

        assert result.status == "success"
        assert result.retry_attempts == 1
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_block_executor_no_retry_on_script_runtime_exception(self) -> None:
        from server.app.modules.redaccion.services.block_executor import BlockExecutor, ScriptRuntimeError

        call_count = 0

        async def script_error_node(block, state):
            nonlocal call_count
            call_count += 1
            raise ScriptRuntimeError("bug in script")

        tracing, span = _mock_tracing()
        executor = BlockExecutor(tracing, retry_delay_seconds=0)
        result = await executor.execute(script_error_node, MagicMock(id="b1"), _make_state())

        assert result.status == "failed"
        assert result.failure_kind == "script_failed"
        assert call_count == 1  # no retry

    @pytest.mark.asyncio
    async def test_block_executor_no_retry_on_ast_validation_error(self) -> None:
        from server.app.modules.redaccion.services.block_executor import BlockExecutor, ASTValidationError

        call_count = 0

        async def ast_error_node(block, state):
            nonlocal call_count
            call_count += 1
            raise ASTValidationError("unsafe code detected")

        tracing, span = _mock_tracing()
        executor = BlockExecutor(tracing, retry_delay_seconds=0)
        result = await executor.execute(ast_error_node, MagicMock(id="b1"), _make_state())

        assert result.status == "failed"
        assert result.failure_kind == "script_failed"
        assert call_count == 1  # no retry

    @pytest.mark.asyncio
    async def test_block_executor_emits_error_span_on_each_attempt(self) -> None:
        from server.app.modules.redaccion.services.block_executor import BlockExecutor, LLMTimeoutError

        async def always_fails(block, state):
            raise LLMTimeoutError("network error")

        tracing, span = _mock_tracing()
        executor = BlockExecutor(tracing, retry_delay_seconds=0)
        result = await executor.execute(always_fails, MagicMock(id="b1"), _make_state())

        assert result.status == "failed"
        # span.add_event("error", ...) called once per attempt (max 2 attempts)
        assert span.add_event.call_count == 2
        for call_args in span.add_event.call_args_list:
            assert call_args.args[0] == "error"


# ---------------------------------------------------------------------------
# 3. DeterministicExtractionNode — fallos por bloque
# ---------------------------------------------------------------------------

class TestDeterministicExtractionFailures:

    @pytest.mark.asyncio
    async def test_core_graph_continues_with_independent_blocks_when_one_fails(self) -> None:
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import DeterministicExtractionNode
        from server.app.modules.redaccion.pipelines.contracts import ExtractionResult, ExtractionProvenance

        spec = _make_spec([
            {"id": "b_fail", "kind": "DETERMINISTIC_DATA", "source_pipeline": "excel"},
            {"id": "b_ok", "kind": "DETERMINISTIC_DATA", "source_pipeline": "excel"},
        ])

        call_count = 0
        _prov = ExtractionProvenance(pipeline_id="excel", source_ref="b/k", extracted_at=_now())

        class FailFirstPipeline:
            def extract(self, inp):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ValueError("extraction error on first block")
                return ExtractionResult(tables=[], metrics=[], free_text="ok", warnings=[], provenance=_prov)

        factory = MagicMock()
        factory.get = MagicMock(return_value=FailFirstPipeline())

        blocks = {
            "b_fail": _block("b_fail", "draft"),
            "b_ok": _block("b_ok", "draft"),
        }
        state = _make_state(spec=spec, blocks=blocks, artifacts_normalized={"slot_a": "bucket/key.xlsx"})
        node = DeterministicExtractionNode(factory)
        patch = await node(state)

        assert patch["blocks"]["b_fail"].status == "failed"
        assert patch["blocks"]["b_fail"].failure_kind == "extraction_failed"
        # Second block was processed (call_count == 2)
        assert call_count == 2
        assert patch["blocks"]["b_ok"].status == "extracted"

    @pytest.mark.asyncio
    async def test_core_graph_marks_dependent_blocks_as_validation_failed(self) -> None:
        from server.app.modules.redaccion.services.block_executor import propagate_dependency_failures
        from server.app.modules.redaccion.contracts.block_io import BlockReference

        spec = _make_spec([
            {"id": "b_a", "kind": "DETERMINISTIC_DATA", "source_pipeline": "excel"},
            {"id": "b_b", "kind": "DETERMINISTIC_DATA", "source_pipeline": "excel",
             "depends_on": [BlockReference(block_id="b_a")]},
        ])

        blocks = {
            "b_a": _block("b_a", "failed", failure_kind="extraction_failed"),
            "b_b": _block("b_b", "draft"),
        }
        result = propagate_dependency_failures(spec, blocks)

        assert result["b_b"].status == "failed"
        assert result["b_b"].failure_kind == "validation_failed"
        assert "b_a" in (result["b_b"].last_error_message or "")

    @pytest.mark.asyncio
    async def test_partial_outputs_preserved_under_block_outputs_partial(self) -> None:
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import DeterministicExtractionNode

        spec = _make_spec([{"id": "b1", "kind": "DETERMINISTIC_DATA", "source_pipeline": "excel"}])

        factory = MagicMock()
        factory.get = MagicMock(side_effect=ValueError("pipeline not found"))

        blocks = {"b1": _block("b1", "draft")}
        state = _make_state(spec=spec, blocks=blocks, artifacts_normalized={"s": "b/k"})
        node = DeterministicExtractionNode(factory)
        patch = await node(state)

        assert patch["block_outputs"].get("b1") == {"partial": {}}


# ---------------------------------------------------------------------------
# 4. AuditLogNode — registra bloques fallidos en el manifest
# ---------------------------------------------------------------------------

class TestAuditLogWithFailures:

    @pytest.mark.asyncio
    async def test_audit_log_node_records_failed_blocks_in_manifest_with_attempts(self) -> None:
        from server.app.modules.redaccion.graph.nodes.audit_log import AuditLogNode
        from server.app.modules.redaccion.graph.tracing import NoOpTracingService

        repo = AsyncMock()
        repo.save = AsyncMock(return_value=None)
        node = AuditLogNode(repo, NoOpTracingService())

        blocks = {
            "b_ok": _block("b_ok", "approved"),
            "b_fail": _block(
                "b_fail", "failed",
                failure_kind="extraction_failed",
                last_error_message="file not found",
                retry_attempts=1,
            ),
        }
        state = _make_state(blocks=blocks, status="error")
        await node(state)

        repo.save.assert_awaited_once()
        saved_orm = repo.save.call_args.args[0]
        payload = saved_orm.payload_json
        assert len(payload["failed_blocks"]) == 1
        fb = payload["failed_blocks"][0]
        assert fb["block_id"] == "b_fail"
        assert fb["failure_kind"] == "extraction_failed"
        assert fb["retry_attempts"] == 1


# ---------------------------------------------------------------------------
# 5. UserReviewGateNode — regenerate y skip
# ---------------------------------------------------------------------------

class TestReviewGateFailures:

    @pytest.mark.asyncio
    async def test_user_review_gate_allows_regenerate_on_failed_block(self) -> None:
        from server.app.modules.redaccion.graph.nodes.review_gate import UserReviewGateNode

        spec = _make_spec([
            {"id": "b_ai", "kind": "AI_ASSISTED_TEXT", "prompt_id": "p1"},
        ])
        blocks = {
            "b_ai": _block("b_ai", "failed", kind="AI_ASSISTED_TEXT", failure_kind="ai_failed"),
        }
        state = _make_state(
            spec=spec,
            blocks=blocks,
            regenerate_blocks={"b_ai"},
        )
        node = UserReviewGateNode()
        patch = await node(state)

        # Should be reset to "extracted" (ai_failed → extracted)
        assert patch["blocks"]["b_ai"].status == "extracted"
        assert patch["blocks"]["b_ai"].failure_kind is None
        # regenerate_blocks consumed
        assert patch["regenerate_blocks"] == set()

    @pytest.mark.asyncio
    async def test_user_review_gate_allows_skip_only_if_block_not_required(self) -> None:
        from server.app.modules.redaccion.graph.nodes.review_gate import UserReviewGateNode

        spec = _make_spec([
            {"id": "b_opt", "kind": "DETERMINISTIC_DATA", "required": False},
            {"id": "b_req", "kind": "DETERMINISTIC_DATA", "required": True},
        ])
        blocks = {
            "b_opt": _block("b_opt", "failed", failure_kind="extraction_failed"),
            "b_req": _block("b_req", "failed", failure_kind="extraction_failed"),
        }
        state = _make_state(
            spec=spec,
            blocks=blocks,
            skip_blocks={"b_opt", "b_req"},
        )
        node = UserReviewGateNode()
        patch = await node(state)

        # Only non-required block survives in skip_blocks
        assert "b_opt" in patch["skip_blocks"]
        assert "b_req" not in patch["skip_blocks"]


# ---------------------------------------------------------------------------
# 6. FinalAssemblerNode — bloqueo por bloque requerido fallido
# ---------------------------------------------------------------------------

class TestFinalAssemblerFailures:

    @pytest.mark.asyncio
    async def test_final_assembler_rejects_when_required_block_failed_validation(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        spec = _make_spec([
            {"id": "b_req", "kind": "DETERMINISTIC_DATA", "required": True},
        ])
        blocks = {
            "b_req": _block("b_req", "failed", failure_kind="validation_failed"),
        }
        state = _make_state(spec=spec, blocks=blocks)
        node = FinalAssemblerNode()

        with pytest.raises(WorkspaceBlockedByFailedBlocksError) as exc_info:
            await node(state)

        assert "b_req" in exc_info.value.failed_block_ids

    @pytest.mark.asyncio
    async def test_final_assembler_allows_skip_for_optional_failed_block(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        spec = _make_spec([
            {"id": "b_opt", "kind": "DETERMINISTIC_DATA", "required": False},
        ])
        blocks = {
            "b_opt": _block("b_opt", "failed", failure_kind="extraction_failed"),
        }
        state = _make_state(spec=spec, blocks=blocks, skip_blocks={"b_opt"})
        node = FinalAssemblerNode()

        # Must not raise — optional failed block in skip_blocks is allowed
        result = await node(state)
        assert result.get("status") == "assembled"


# ─────────────── INF.2 — `assembled` tiene que significar «se puede exportar» ───────────────
#
# En las pruebas humanas del 2026-08-20 el workspace quedo en `assembled` con dos bloques de IA
# en `failed`: la insignia decia «Listo para exportar» y la vista previa y la exportacion
# devolvian 409 por esos mismos bloques.
#
# La causa: el ensamblador se bloqueaba solo si un bloque **`required`** estaba `failed`, y
# `required` es `False` por defecto en todo bloque —el modelo que propone la plantilla no lo
# pone nunca—. O sea que la guarda no se disparaba jamas en una plantilla propuesta por IA.
#
# La regla pasa a ser la misma que usan la vista previa y la exportacion: un bloque de IA sin
# aprobar deja el informe en `in_review`, que es lo que de verdad hay que hacer con el.

class TestElEnsambladoNoMiente:
    async def test_should_not_declare_assembled_with_unapproved_ai_blocks(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        spec = _make_spec([
            {"id": "t_datos", "kind": "DETERMINISTIC_DATA"},
            {"id": "v_texto", "kind": "AI_ASSISTED_TEXT"},
        ])
        state = _make_state(
            spec=spec,
            blocks={
                "t_datos": _block("t_datos", "extracted", content={"tables": []}),
                # Ni `approved` ni `locked`: exactamente el caso del usuario.
                "v_texto": _block("v_texto", "failed", kind="AI_ASSISTED_TEXT",
                                  failure_kind="ai_failed"),
            },
        )

        salida = await FinalAssemblerNode()(state)

        assert salida.get("status") != "assembled", (
            "un informe con un apartado de IA sin aprobar no esta listo para exportar"
        )
        assert salida.get("status") == "in_review"

    async def test_should_declare_assembled_when_every_ai_block_is_approved(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        spec = _make_spec([{"id": "v_texto", "kind": "AI_ASSISTED_TEXT"}])
        state = _make_state(
            spec=spec,
            blocks={"v_texto": _block("v_texto", "approved", kind="AI_ASSISTED_TEXT",
                                      content={"text": "Valoracion aprobada."})},
        )

        salida = await FinalAssemblerNode()(state)

        assert salida.get("status") == "assembled"

    async def test_should_declare_assembled_for_a_report_without_ai_blocks(self) -> None:
        """Nada transiciona un `DETERMINISTIC_DATA` a `approved`: exigirselo lo dejaria
        inalcanzable, que es el error que la vista previa ya cometio una vez."""
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        spec = _make_spec([{"id": "t_datos", "kind": "DETERMINISTIC_DATA"}])
        state = _make_state(
            spec=spec,
            blocks={"t_datos": _block("t_datos", "extracted", content={"tables": []})},
        )

        salida = await FinalAssemblerNode()(state)

        assert salida.get("status") == "assembled"

    async def test_should_ignore_a_block_someone_decided_to_skip(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import FinalAssemblerNode

        spec = _make_spec([{"id": "v_texto", "kind": "AI_ASSISTED_TEXT"}])
        state = _make_state(
            spec=spec,
            blocks={"v_texto": _block("v_texto", "failed", kind="AI_ASSISTED_TEXT")},
            skip_blocks=["v_texto"],
        )

        salida = await FinalAssemblerNode()(state)

        assert salida.get("status") == "assembled", (
            "un apartado descartado a conciencia no puede seguir bloqueando el informe"
        )
