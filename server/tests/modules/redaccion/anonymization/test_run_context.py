"""Tests del RunAnonymizationContext — Fase 13 (NER reversible).

Cubre los 5 tests de "unit tests del context" del prompt 13.1:
- substitute por longitud descendente
- reverse sólo en exact matches
- substitución de PII en JSON / strings citados
- máscara Disposición 7 con letra de control preservada
- Disposición 7 NO es reversible
"""

from __future__ import annotations

import uuid

from server.app.modules.redaccion.services.anonymization.run_context import (
    AnonymizationMode,
    AnonymizationSummary,
    PiiSpan,
    RunAnonymizationContext,
    disposition_7_mask,
    is_masked_under_disposition_7,
)


def _make_ctx(
    forward: dict[str, str],
    *,
    mode: AnonymizationMode = AnonymizationMode.REPLACE,
    spans: list[PiiSpan] | None = None,
) -> RunAnonymizationContext:
    return RunAnonymizationContext(
        workspace_id=uuid.uuid4(),
        mode=mode,
        spans=spans or [],
        forward_map=forward,
        reverse_map={v: k for k, v in forward.items()},
    )


# ──────────────────────────────────────────────────────────────────
# Substitute / reverse
# ──────────────────────────────────────────────────────────────────


def test_substitute_orders_by_length_descending_to_avoid_partial_matches() -> None:
    ctx = _make_ctx(
        {
            "Juan": "Carlos",  # short
            "Juan García": "María López",  # long, contiene el short como prefijo
        }
    )
    out = ctx.substitute("El informe lo firma Juan García en nombre de Juan.")
    # "Juan García" debe sustituirse primero como bloque completo.
    assert "María López" in out
    # "Juan" suelto se sustituye después.
    assert out.endswith("Carlos.")
    # El nombre largo no debe quedar contaminado por el corto.
    assert "María Carlos" not in out
    assert "Carlos García" not in out


def test_reverse_only_replaces_exact_matches_no_false_positives() -> None:
    ctx = _make_ctx({"Juan García": "Carlos Pérez"})
    # El LLM "alucina" un nombre tipo Faker que NO está en reverse_map.
    llm_output = (
        "Según el documento, Carlos Pérez participó en la reunión. "
        "También se menciona a Pedro Martínez (no anonimizado por nosotros)."
    )
    out = ctx.reverse(llm_output)
    assert "Juan García" in out  # sintético conocido → revertido
    assert "Pedro Martínez" in out  # alucinación → queda tal cual
    assert "Carlos Pérez" not in out


def test_substitute_handles_pii_appearing_in_json_or_quoted_string() -> None:
    ctx = _make_ctx({"juan@example.com": "fake01@example.org"})
    text = '{"author": "juan@example.com", "note": "Contacto: juan@example.com"}'
    out = ctx.substitute(text)
    assert "juan@example.com" not in out
    assert out.count("fake01@example.org") == 2


# ──────────────────────────────────────────────────────────────────
# Disposición 7 (LOPDGDD)
# ──────────────────────────────────────────────────────────────────


def test_disposition_7_masks_dni_with_check_letter_preserved() -> None:
    assert disposition_7_mask("DNI", "12345678Z") == "****5678Z"
    # Mayúsculas / minúsculas: la letra se normaliza.
    assert disposition_7_mask("DNI", "87654321a") == "****4321A"
    # NIE: preserva prefijo y letra de control.
    assert disposition_7_mask("NIE", "X1234567L") == "X***4567L"
    # Pasaporte (formato variable): conserva últimos 4 caracteres.
    assert disposition_7_mask("PASSPORT", "AAB123456") == "*****3456"


def test_disposition_7_is_not_reversible_for_dni() -> None:
    """Bajo Disposición 7, el sintético DE DNI/NIE es una máscara que NUNCA entra al reverse_map.
    El output final del usuario queda enmascarado por diseño.
    """
    workspace_id = uuid.uuid4()
    ctx = RunAnonymizationContext(
        workspace_id=workspace_id,
        mode=AnonymizationMode.REPLACE_WITH_DISPOSITION_7,
        spans=[
            PiiSpan(
                type="DNI",
                original="12345678Z",
                synthetic="****5678Z",
                masked=True,
            ),
        ],
        forward_map={"12345678Z": "****5678Z"},
        # reverse_map NO contiene "****5678Z" → la máscara nunca se revierte.
        reverse_map={},
    )

    substituted = ctx.substitute("El titular es 12345678Z, pendiente de verificar.")
    assert "12345678Z" not in substituted
    assert "****5678Z" in substituted

    # Intento de revertir: el sintético máscara NO debe ser sustituido por el original.
    reverted = ctx.reverse(substituted)
    assert "12345678Z" not in reverted
    assert "****5678Z" in reverted

    # is_masked_under_disposition_7 confirma el modo + tipo.
    assert is_masked_under_disposition_7("DNI", AnonymizationMode.REPLACE_WITH_DISPOSITION_7)
    assert not is_masked_under_disposition_7("PERSON", AnonymizationMode.REPLACE_WITH_DISPOSITION_7)
    assert not is_masked_under_disposition_7("DNI", AnonymizationMode.REPLACE)


# ──────────────────────────────────────────────────────────────────
# Modes: OFF / DETECT_ONLY pasan texto sin cambios
# ──────────────────────────────────────────────────────────────────


def test_off_mode_returns_text_unchanged() -> None:
    ctx = _make_ctx({"Juan García": "Carlos Pérez"}, mode=AnonymizationMode.OFF)
    text = "Juan García asistió."
    assert ctx.substitute(text) == text
    assert ctx.reverse("Carlos Pérez asistió.") == "Carlos Pérez asistió."


def test_detect_only_mode_does_not_substitute_in_prompt() -> None:
    ctx = _make_ctx({"Juan García": "Carlos Pérez"}, mode=AnonymizationMode.DETECT_ONLY)
    assert ctx.substitute("Juan García asistió.") == "Juan García asistió."


# ──────────────────────────────────────────────────────────────────
# AnonymizationSummary — sólo metadata
# ──────────────────────────────────────────────────────────────────


def test_summary_counts_by_type_excludes_originals_and_synthetics() -> None:
    ctx = _make_ctx(
        {"Juan García": "Carlos Pérez", "ana@x.com": "f@y.com"},
        spans=[
            PiiSpan(type="PERSON", original="Juan García", synthetic="Carlos Pérez"),
            PiiSpan(type="EMAIL", original="ana@x.com", synthetic="f@y.com"),
            PiiSpan(type="PERSON", original="Luis", synthetic="Pedro"),
        ],
    )
    summary = AnonymizationSummary.from_context(ctx)
    assert summary.total_spans == 3
    assert summary.counts_by_type == {"PERSON": 2, "EMAIL": 1}
    # Ningún campo del summary contiene originales ni sintéticos.
    dumped = summary.model_dump()
    assert "Juan García" not in str(dumped)
    assert "Carlos Pérez" not in str(dumped)
    assert "ana@x.com" not in str(dumped)
