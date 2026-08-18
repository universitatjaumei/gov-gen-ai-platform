"""DraftValidator — 9R.4.2.

Valida la estructura de un ReportTemplateDraft propuesto por el LLM y lo
normaliza (IDs únicos, orden por sección) antes de que pueda persistirse
o usarse como base de un workspace.
"""
from __future__ import annotations

import uuid

from pydantic import TypeAdapter

from server.app.modules.redaccion.contracts.blocks import BlockContract
from server.app.modules.redaccion.contracts.drafts import (
    DraftValidationError,
    ReportTemplateDraft,
    ReportTemplateDraftValidationResult,
)

_BLOCK_ADAPTER: TypeAdapter[BlockContract] = TypeAdapter(BlockContract)

_AI_KINDS = frozenset({"AI_ASSISTED_TEXT", "AI_SUMMARY", "AI_REWRITE"})
_DATA_REF_KINDS = frozenset({"CHART", "TABLE"})
#: Bloques que producen una tabla de la que otro puede tirar.
_DATA_SOURCE_KINDS = frozenset({"DETERMINISTIC_DATA", "DATA_TRANSFORM"})
_VALID_PROFILES = frozenset({
    "GENERIC_REPORT",
    "ANNUAL_REPORT",
    "DOCTORATE_PROGRAM_REPORT",
    "CONTRACT_REPORT",
    "FREEFORM_MEMO",
})


class DraftValidator:
    """Validador determinista de ReportTemplateDraft. Mismo input → mismo output."""

    def validate(self, draft: ReportTemplateDraft) -> ReportTemplateDraftValidationResult:
        errors: list[DraftValidationError] = []

        # 1. Profile pertenece al registry
        if draft.proposed_profile not in _VALID_PROFILES:
            errors.append(DraftValidationError(
                field="proposed_profile",
                message=f"Unknown profile: {draft.proposed_profile!r}. "
                        f"Valid values: {sorted(_VALID_PROFILES)}",
            ))

        block_by_id: dict[str, BlockContract] = {b.id: b for b in draft.proposed_blocks}
        # GUI.3 — un bloque de transformación también da datos, y de hecho es el que los da
        # **utilizables**: la cadena de una hoja real es extraer → limpiar → dibujar. Exigir que
        # un CHART apuntara a un `DETERMINISTIC_DATA` tumbaba la propuesta entera en cuanto se
        # metía la limpieza en medio, que es justo cuando el gráfico vale algo.
        deterministic_ids = {
            b.id  # type: ignore[union-attr]
            for b in draft.proposed_blocks
            if b.kind in _DATA_SOURCE_KINDS  # type: ignore[union-attr]
        }

        for block in draft.proposed_blocks:
            bid = block.id  # type: ignore[union-attr]
            kind = block.kind  # type: ignore[union-attr]

            # 2. depends_on referencian bloques existentes
            for ref in block.depends_on:  # type: ignore[union-attr]
                if ref.block_id not in block_by_id:
                    errors.append(DraftValidationError(
                        field=f"blocks[{bid}].depends_on",
                        message=f"Block {bid!r} depends on unknown block {ref.block_id!r}",
                    ))

            # 3. CHART/TABLE referencian un DETERMINISTIC_DATA presente
            if kind in _DATA_REF_KINDS:
                ref_id = getattr(block, "data_block_ref", None)
                if not ref_id or ref_id not in block_by_id:
                    errors.append(DraftValidationError(
                        field=f"blocks[{bid}].data_block_ref",
                        message=f"{kind} block {bid!r} references missing block {ref_id!r}",
                    ))
                elif ref_id not in deterministic_ids:
                    errors.append(DraftValidationError(
                        field=f"blocks[{bid}].data_block_ref",
                        message=f"{kind} block {bid!r} must reference a block that produces data "
                                f"({', '.join(sorted(_DATA_SOURCE_KINDS))}), "
                                f"got {block_by_id[ref_id].kind!r}",  # type: ignore[union-attr]
                    ))

            # GUI.3 — la transformación apunta a su origen por `config.source_block_ref`. Sin
            # comprobarlo, una referencia inventada deja el bloque sin datos en tiempo de
            # ejecución y sin nada que explique por qué.
            if kind == "DATA_TRANSFORM":
                origen = getattr(getattr(block, "config", None), "source_block_ref", None)
                origen_id = getattr(origen, "block_id", None)
                if not origen_id or origen_id not in block_by_id:
                    errors.append(DraftValidationError(
                        field=f"blocks[{bid}].config.source_block_ref",
                        message=f"DATA_TRANSFORM block {bid!r} reads from unknown block "
                                f"{origen_id!r}",
                    ))
                elif origen_id not in deterministic_ids:
                    errors.append(DraftValidationError(
                        field=f"blocks[{bid}].config.source_block_ref",
                        message=f"DATA_TRANSFORM block {bid!r} must read from a block that "
                                f"produces data, got {block_by_id[origen_id].kind!r}",  # type: ignore[union-attr]
                    ))

        # 4. REVIEW_GATE obligatoria si hay bloques AI
        has_ai = any(b.kind in _AI_KINDS for b in draft.proposed_blocks)  # type: ignore[union-attr]
        has_gate = any(b.kind == "REVIEW_GATE" for b in draft.proposed_blocks)  # type: ignore[union-attr]
        if has_ai and not has_gate:
            errors.append(DraftValidationError(
                field="blocks",
                message="Draft has AI blocks but no REVIEW_GATE block",
            ))

        if errors:
            return ReportTemplateDraftValidationResult(ok=False, errors=errors)

        normalized = _normalize(draft)
        return ReportTemplateDraftValidationResult(ok=True, normalized_draft=normalized, errors=[])


# ---------------------------------------------------------------------------
# Normalización
# ---------------------------------------------------------------------------

def _normalize(draft: ReportTemplateDraft) -> ReportTemplateDraft:
    # 1. IDs únicos: reasigna duplicados
    seen: set[str] = set()
    deduped: list[BlockContract] = []
    for block in draft.proposed_blocks:
        bid = block.id  # type: ignore[union-attr]
        if bid in seen:
            new_id = f"block_{uuid.uuid4().hex[:8]}"
            data = block.model_dump()
            data["id"] = new_id
            block = _BLOCK_ADAPTER.validate_python(data)
        seen.add(block.id)  # type: ignore[union-attr]
        deduped.append(block)

    # 2. Orden por sección / posición dentro de sección
    section_position: dict[str, tuple[int, int]] = {}
    for si, section in enumerate(draft.proposed_sections):
        for bi, bid in enumerate(section.block_ids):
            section_position[bid] = (si, bi)

    deduped.sort(key=lambda b: section_position.get(
        b.id,  # type: ignore[union-attr]
        (len(draft.proposed_sections), getattr(b, "order", 0)),
    ))

    return ReportTemplateDraft(
        proposed_profile=draft.proposed_profile,
        proposed_sections=draft.proposed_sections,
        proposed_blocks=deduped,
        proposed_inputs=draft.proposed_inputs,
        rationale=draft.rationale,
        model_used=draft.model_used,
        prompt_version=draft.prompt_version,
    )
