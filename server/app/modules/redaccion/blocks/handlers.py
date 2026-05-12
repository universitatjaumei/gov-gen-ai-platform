"""Handlers de bloque para el DraftingCoreGraph — 9R.3.1.

Cada handler encapsula el comportamiento de un tipo de bloque:
  validate(block)                     — verifica integridad estructural
  validate_in_context(block, state)   — verifica dependencias en el workspace
  execute(block, state) -> dict       — produce el content del bloque
  to_manifest(block) -> dict          — qué se serializa en DraftingRunManifest
"""
from __future__ import annotations

from typing import Any

from server.app.modules.redaccion.contracts.blocks import (
    AIAssistedTextBlock,
    AIRewriteBlock,
    AISummaryBlock,
    ChartBlock,
    CitationBlock,
    DeterministicDataBlock,
    ReviewGateBlock,
    StaticTextBlock,
    TableBlock,
    UserInputBlock,
)
from server.app.modules.redaccion.contracts.runtime import WorkspaceState


class BlockHandlerValidationError(Exception):
    pass


# ---------------------------------------------------------------------------
# Base helper
# ---------------------------------------------------------------------------

def _base_manifest(block_id: str, kind: str) -> dict[str, Any]:
    return {"block_id": block_id, "kind": kind}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

class StaticTextHandler:
    """Bloque de texto estático definido en la plantilla. No usa IA."""

    uses_ai: bool = False
    requires_approval: bool = False

    def validate(self, block: StaticTextBlock) -> None:
        pass  # siempre válido

    def validate_in_context(self, block: StaticTextBlock, state: WorkspaceState) -> None:
        pass

    def execute(self, block: StaticTextBlock, state: WorkspaceState) -> dict:
        return {"text": block.content}

    def to_manifest(self, block: StaticTextBlock) -> dict:
        return {**_base_manifest(block.id, block.kind), "content_length": len(block.content)}


class UserInputHandler:
    """Bloque de entrada de usuario. No usa IA; el usuario rellena el campo."""

    uses_ai: bool = False
    requires_approval: bool = False

    def validate(self, block: UserInputBlock) -> None:
        pass

    def validate_in_context(self, block: UserInputBlock, state: WorkspaceState) -> None:
        pass

    def execute(self, block: UserInputBlock, state: WorkspaceState) -> dict:
        # El contenido llega del frontend; execute solo devuelve lo que ya tiene el estado
        bs = state.blocks.get(block.id)
        return bs.content or {} if bs else {}

    def to_manifest(self, block: UserInputBlock) -> dict:
        return {**_base_manifest(block.id, block.kind), "field_type": block.field_type}


class DeterministicDataHandler:
    """Bloque de datos extraídos por un pipeline determinista. Delega en ExtractionPipeline."""

    uses_ai: bool = False
    requires_approval: bool = False

    def validate(self, block: DeterministicDataBlock) -> None:
        if not block.source_pipeline:
            raise BlockHandlerValidationError(
                f"DeterministicDataBlock {block.id!r} requires source_pipeline"
            )

    def validate_in_context(self, block: DeterministicDataBlock, state: WorkspaceState) -> None:
        self.validate(block)

    def execute(self, block: DeterministicDataBlock, state: WorkspaceState) -> dict:
        # La ejecución real delega en ExtractionPipelineFactory (implementado en 9R.5)
        return {"pipeline": block.source_pipeline, "rows": []}

    def to_manifest(self, block: DeterministicDataBlock) -> dict:
        return {**_base_manifest(block.id, block.kind), "source_pipeline": block.source_pipeline}


class TableHandler:
    """Bloque de tabla estructurada. Consume el output de un DETERMINISTIC_DATA."""

    uses_ai: bool = False
    requires_approval: bool = False

    def validate(self, block: TableBlock) -> None:
        if not block.data_block_ref:
            raise BlockHandlerValidationError(
                f"TableBlock {block.id!r} requires data_block_ref"
            )

    def validate_in_context(self, block: TableBlock, state: WorkspaceState) -> None:
        self.validate(block)
        if block.data_block_ref not in state.blocks:
            raise BlockHandlerValidationError(
                f"TableBlock {block.id!r}: data_block_ref={block.data_block_ref!r} not found in workspace"
            )

    def execute(self, block: TableBlock, state: WorkspaceState) -> dict:
        source = state.blocks.get(block.data_block_ref)
        return {"source_block_id": block.data_block_ref, "rows": source.content or {} if source else {}}

    def to_manifest(self, block: TableBlock) -> dict:
        return {**_base_manifest(block.id, block.kind), "data_block_ref": block.data_block_ref}


class ChartHandler:
    """Bloque de gráfico. Consume DETERMINISTIC_DATA o TABLE."""

    uses_ai: bool = False
    requires_approval: bool = False

    def validate(self, block: ChartBlock) -> None:
        if not block.data_block_ref:
            raise BlockHandlerValidationError(
                f"ChartBlock {block.id!r} requires data_block_ref"
            )

    def validate_in_context(self, block: ChartBlock, state: WorkspaceState) -> None:
        self.validate(block)
        if block.data_block_ref not in state.blocks:
            raise BlockHandlerValidationError(
                f"ChartBlock {block.id!r}: data_block_ref={block.data_block_ref!r} not found in workspace"
            )

    def execute(self, block: ChartBlock, state: WorkspaceState) -> dict:
        return {"source_block_id": block.data_block_ref, "chart_type": "bar"}

    def to_manifest(self, block: ChartBlock) -> dict:
        return {**_base_manifest(block.id, block.kind), "data_block_ref": block.data_block_ref}


class AIAssistedTextHandler:
    """Bloque de texto asistido por IA. Requiere aprobación HITL antes de ensamblar."""

    uses_ai: bool = True
    requires_approval: bool = True

    def validate(self, block: AIAssistedTextBlock) -> None:
        if not block.review_policy_id:
            raise BlockHandlerValidationError(
                f"AIAssistedTextBlock {block.id!r} requires review_policy_id"
            )

    def validate_in_context(self, block: AIAssistedTextBlock, state: WorkspaceState) -> None:
        self.validate(block)

    def execute(self, block: AIAssistedTextBlock, state: WorkspaceState) -> dict:
        # La generación real la hace AIAssistDraftNode (9R.6.3)
        return {"ai_draft": "", "prompt_template_id": block.ai_prompt_template_id}

    def to_manifest(self, block: AIAssistedTextBlock) -> dict:
        return {
            **_base_manifest(block.id, block.kind),
            "ai_prompt_template_id": block.ai_prompt_template_id,
            "review_policy_id": block.review_policy_id,
        }


class AISummaryHandler:
    """Bloque de resumen generado por IA. Requiere aprobación HITL."""

    uses_ai: bool = True
    requires_approval: bool = True

    def validate(self, block: AISummaryBlock) -> None:
        if not block.review_policy_id:
            raise BlockHandlerValidationError(
                f"AISummaryBlock {block.id!r} requires review_policy_id"
            )

    def validate_in_context(self, block: AISummaryBlock, state: WorkspaceState) -> None:
        self.validate(block)

    def execute(self, block: AISummaryBlock, state: WorkspaceState) -> dict:
        return {"ai_summary": "", "prompt_template_id": block.ai_prompt_template_id}

    def to_manifest(self, block: AISummaryBlock) -> dict:
        return {
            **_base_manifest(block.id, block.kind),
            "ai_prompt_template_id": block.ai_prompt_template_id,
            "review_policy_id": block.review_policy_id,
        }


class AIRewriteHandler:
    """Bloque de reescritura asistida por IA. Requiere aprobación HITL."""

    uses_ai: bool = True
    requires_approval: bool = True

    def validate(self, block: AIRewriteBlock) -> None:
        if not block.review_policy_id:
            raise BlockHandlerValidationError(
                f"AIRewriteBlock {block.id!r} requires review_policy_id"
            )

    def validate_in_context(self, block: AIRewriteBlock, state: WorkspaceState) -> None:
        self.validate(block)

    def execute(self, block: AIRewriteBlock, state: WorkspaceState) -> dict:
        return {"ai_rewrite": "", "prompt_template_id": block.ai_prompt_template_id}

    def to_manifest(self, block: AIRewriteBlock) -> dict:
        return {
            **_base_manifest(block.id, block.kind),
            "ai_prompt_template_id": block.ai_prompt_template_id,
            "review_policy_id": block.review_policy_id,
        }


class CitationBlockHandler:
    """Bloque de citas y fuentes. Agrega referencias de otros bloques."""

    uses_ai: bool = False
    requires_approval: bool = False

    def validate(self, block: CitationBlock) -> None:
        pass

    def validate_in_context(self, block: CitationBlock, state: WorkspaceState) -> None:
        pass

    def execute(self, block: CitationBlock, state: WorkspaceState) -> dict:
        citations = []
        for ref_id in block.source_block_refs:
            bs = state.blocks.get(ref_id)
            if bs and bs.citations:
                citations.extend([c.model_dump() for c in bs.citations])
        return {"citations": citations}

    def to_manifest(self, block: CitationBlock) -> dict:
        return {
            **_base_manifest(block.id, block.kind),
            "source_block_refs": block.source_block_refs,
        }


class ReviewGateHandler:
    """Porta de revisión. Bloquea el ensamblado hasta que todos los depends_on estén approved/locked."""

    uses_ai: bool = False
    requires_approval: bool = True

    def validate(self, block: ReviewGateBlock) -> None:
        if not block.review_policy_id:
            raise BlockHandlerValidationError(
                f"ReviewGateBlock {block.id!r} requires review_policy_id"
            )

    def validate_in_context(self, block: ReviewGateBlock, state: WorkspaceState) -> None:
        self.validate(block)
        for dep_ref in block.depends_on:
            dep_id = dep_ref.block_id
            dep_state = state.blocks.get(dep_id)
            if dep_state is None:
                raise BlockHandlerValidationError(
                    f"ReviewGateBlock {block.id!r}: dependency {dep_id!r} not found"
                )
            if dep_state.status not in ("approved", "locked"):
                raise BlockHandlerValidationError(
                    f"ReviewGateBlock {block.id!r}: dependency {dep_id!r} is not approved "
                    f"(status={dep_state.status!r})"
                )

    def execute(self, block: ReviewGateBlock, state: WorkspaceState) -> dict:
        return {"gate_passed": True, "review_policy_id": block.review_policy_id}

    def to_manifest(self, block: ReviewGateBlock) -> dict:
        return {
            **_base_manifest(block.id, block.kind),
            "review_policy_id": block.review_policy_id,
        }
