"""Tests del InitAnonymizationNode y de los hooks pre/post-LLM en AIAssistDraftNode.

Cubre los grupos "Nodo init" y "Integración hooks en grafo" del prompt 13.1.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.modules.redaccion.contracts.runtime import (
    BlockState,
    WorkspaceState,
)
from server.app.modules.redaccion.graph.nodes.ai_assist_draft import AIAssistDraftNode
from server.app.modules.redaccion.graph.nodes.init_anonymization import InitAnonymizationNode
from server.app.modules.redaccion.services.anonymization.run_context import (
    AnonymizationMode,
    PiiSpan,
    RunAnonymizationContext,
)


# ──────────────────────────────────────────────────────────────────
# Fakes
# ──────────────────────────────────────────────────────────────────


class _FakeDetector:
    """Detector determinista basado en una lista cerrada de (texto, tipo)."""

    def __init__(self, hits: list[tuple[str, str]]) -> None:
        self._hits = hits

    def detect_spans(self, text: str) -> list[Any]:
        spans: list[Any] = []
        for needle, pii_type in self._hits:
            if needle in text:
                spans.append(
                    SimpleNamespace(
                        start=text.index(needle),
                        end=text.index(needle) + len(needle),
                        type=pii_type,
                        original_text=needle,
                        suggested_fake=f"FAKE_{pii_type}_{needle[:3]}",
                        confidence=0.9,
                    )
                )
        return spans


class _FakeFaker:
    """FakerGenerator determinista: prefijo SYN_ + tipo + 6 primeros chars del original."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def generate(self, entity_type: str, original: str, context: str = "") -> str:
        self.calls.append((entity_type, original, context))
        return f"SYN_{entity_type}_{original[:6]}"


def _make_state(
    *,
    mode: str = "replace",
    inputs_text: dict[str, str] | None = None,
    blocks: dict[str, BlockState] | None = None,
) -> WorkspaceState:
    # `inputs_text` se vuelca en artifacts_normalized (markdown post-normalización).
    return WorkspaceState(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks=blocks or {},
        status="extracting",
        warnings=[],
        artifacts_normalized=inputs_text or {},
        anonymization_mode=mode,
    )


def _make_block(
    block_id: str,
    *,
    content: dict | None = None,
    status: str = "extracted",
) -> BlockState:
    return BlockState(
        block_id=block_id,
        kind="DETERMINISTIC_DATA",
        status=status,  # type: ignore[arg-type]
        content=content,
        last_updated_by="system",
        updated_at=datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────────────────────────
# InitAnonymizationNode
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_init_anonymization_node_detects_all_pii_in_inputs_and_extracted_blocks() -> None:
    detector = _FakeDetector(
        hits=[("Juan García", "PERSON"), ("juan@example.com", "EMAIL")]
    )
    faker = _FakeFaker()
    state = _make_state(
        inputs_text={"main": "Documento firmado por Juan García."},
        blocks={
            "block_a": _make_block(
                "block_a", content={"free_text": "Contacto: juan@example.com"}
            ),
        },
    )

    node = InitAnonymizationNode(detector, faker)
    out = await node(state)
    ctx: RunAnonymizationContext = out["anonymization_context"]

    types = {span.type for span in ctx.spans}
    originals = {span.original for span in ctx.spans}
    assert types == {"PERSON", "EMAIL"}
    assert {"Juan García", "juan@example.com"} <= originals
    # source_block_id se rellena para spans encontrados en bloques.
    by_orig = {s.original: s.source_block_id for s in ctx.spans}
    assert by_orig["juan@example.com"] == "block_a"
    assert by_orig["Juan García"] == "main"


@pytest.mark.asyncio
async def test_init_anonymization_node_generates_unique_synthetics_per_span() -> None:
    detector = _FakeDetector(
        hits=[("Juan García", "PERSON"), ("María López", "PERSON")]
    )
    faker = _FakeFaker()
    state = _make_state(
        inputs_text={"main": "Juan García y María López asistieron."},
    )

    node = InitAnonymizationNode(detector, faker)
    out = await node(state)
    ctx: RunAnonymizationContext = out["anonymization_context"]

    synthetics = {span.synthetic for span in ctx.spans}
    assert len(synthetics) == 2
    assert ctx.forward_map["Juan García"] != ctx.forward_map["María López"]
    # Mapas son inversos.
    for orig, synth in ctx.forward_map.items():
        assert ctx.reverse_map[synth] == orig


@pytest.mark.asyncio
async def test_init_anonymization_node_off_mode_returns_empty_context() -> None:
    detector = _FakeDetector(hits=[("Juan García", "PERSON")])
    faker = _FakeFaker()
    state = _make_state(
        mode="off",
        inputs_text={"main": "Juan García firmó."},
    )

    node = InitAnonymizationNode(detector, faker)
    out = await node(state)
    ctx: RunAnonymizationContext = out["anonymization_context"]

    assert ctx.mode == AnonymizationMode.OFF
    assert ctx.spans == []
    assert ctx.forward_map == {}
    assert ctx.reverse_map == {}
    # En OFF NO se llama al detector (atajo) — sin asserts duros sobre calls.


@pytest.mark.asyncio
async def test_init_anonymization_node_detect_only_records_spans_without_mapping() -> None:
    detector = _FakeDetector(hits=[("Juan García", "PERSON")])
    faker = _FakeFaker()
    state = _make_state(
        mode="detect_only",
        inputs_text={"main": "Firma: Juan García."},
    )

    node = InitAnonymizationNode(detector, faker)
    out = await node(state)
    ctx: RunAnonymizationContext = out["anonymization_context"]

    # Sí registra spans para auditoría, pero no hay mapas → substitute/reverse son no-op.
    assert len(ctx.spans) == 1
    assert ctx.forward_map == {}
    assert ctx.reverse_map == {}
    assert ctx.substitute("Juan García") == "Juan García"


# ──────────────────────────────────────────────────────────────────
# Hooks integration: AIAssistDraftNode
# ──────────────────────────────────────────────────────────────────


class _SpyLLM:
    """LLM que captura el `context` recibido y devuelve un texto fijado por el test."""

    model_name = "spy-llm"

    def __init__(self, return_text: str) -> None:
        self._return_text = return_text
        self.received_context: str | None = None
        self.received_prompt: str | None = None

    async def generate(self, prompt: str, context: str) -> str:
        self.received_context = context
        self.received_prompt = prompt
        return self._return_text


def _spec_with_ai_block(block_id: str = "ai_block") -> Any:
    """Mock minimal de ReportTemplateSpec con un solo bloque IA."""
    block_contract = SimpleNamespace(
        id=block_id,
        kind="AI_ASSISTED_TEXT",
        ai_prompt_template_id="prompt_v1",
    )
    return SimpleNamespace(blocks=[block_contract])


def _state_with_ai_block(
    *,
    context_text: str,
    anonymization_context: Any,
) -> WorkspaceState:
    state = WorkspaceState(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={},
        blocks={
            "ai_block": BlockState(
                block_id="ai_block",
                kind="AI_ASSISTED_TEXT",
                status="extracted",  # type: ignore[arg-type]
                content=None,
                last_updated_by="system",
                updated_at=datetime.now(timezone.utc),
            ),
            "data_block": _make_block(
                "data_block",
                content={"free_text": context_text},
                status="extracted",
            ),
        },
        status="drafting",
        warnings=[],
        anonymization_context=anonymization_context,
    )
    state.spec = _spec_with_ai_block("ai_block")
    return state


@pytest.mark.asyncio
async def test_ai_node_receives_anonymized_context_when_mode_replace() -> None:
    ctx = RunAnonymizationContext(
        workspace_id=uuid.uuid4(),
        mode=AnonymizationMode.REPLACE,
        spans=[PiiSpan(type="PERSON", original="Juan García", synthetic="Carlos Pérez")],
        forward_map={"Juan García": "Carlos Pérez"},
        reverse_map={"Carlos Pérez": "Juan García"},
    )
    llm = _SpyLLM(return_text="Resumen elaborado por Carlos Pérez.")
    state = _state_with_ai_block(
        context_text="Documento firmado por Juan García.",
        anonymization_context=ctx,
    )

    out = await AIAssistDraftNode(llm)(state)

    # PRE-HOOK: el contexto enviado al LLM contiene el sintético, NO el original.
    assert "Carlos Pérez" in (llm.received_context or "")
    assert "Juan García" not in (llm.received_context or "")
    # POST-HOOK: el contenido final del bloque IA contiene el original.
    block = out["blocks"]["ai_block"]
    assert "Juan García" in block.content["text"]
    assert "Carlos Pérez" not in block.content["text"]


@pytest.mark.asyncio
async def test_ai_node_output_is_reversed_after_llm_response() -> None:
    ctx = RunAnonymizationContext(
        workspace_id=uuid.uuid4(),
        mode=AnonymizationMode.REPLACE,
        spans=[PiiSpan(type="EMAIL", original="ana@x.com", synthetic="f@y.com")],
        forward_map={"ana@x.com": "f@y.com"},
        reverse_map={"f@y.com": "ana@x.com"},
    )
    llm = _SpyLLM(return_text="Contacto: f@y.com (responde en 24h).")
    state = _state_with_ai_block(
        context_text="Email: ana@x.com",
        anonymization_context=ctx,
    )
    out = await AIAssistDraftNode(llm)(state)
    assert out["blocks"]["ai_block"].content["text"] == "Contacto: ana@x.com (responde en 24h)."


@pytest.mark.asyncio
async def test_detect_only_mode_does_not_substitute_in_prompt() -> None:
    ctx = RunAnonymizationContext(
        workspace_id=uuid.uuid4(),
        mode=AnonymizationMode.DETECT_ONLY,
        spans=[PiiSpan(type="PERSON", original="Juan García", synthetic="Juan García")],
        forward_map={},  # no mapping en detect_only
        reverse_map={},
    )
    llm = _SpyLLM(return_text="OK")
    state = _state_with_ai_block(
        context_text="Firma: Juan García.",
        anonymization_context=ctx,
    )
    await AIAssistDraftNode(llm)(state)
    assert "Juan García" in (llm.received_context or "")


@pytest.mark.asyncio
async def test_off_mode_passes_real_pii_to_llm() -> None:
    state = _state_with_ai_block(
        context_text="Firma: Juan García.",
        anonymization_context=None,  # OFF = sin contexto
    )
    llm = _SpyLLM(return_text="Resumen sobre Juan García.")
    out = await AIAssistDraftNode(llm)(state)
    assert "Juan García" in (llm.received_context or "")
    # Sin hook post, el output queda igual.
    assert out["blocks"]["ai_block"].content["text"] == "Resumen sobre Juan García."
