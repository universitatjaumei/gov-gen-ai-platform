"""UserReviewGateNode — transiciona bloques IA a needs_review y pausa si quedan pendientes (9R.6.4/9R.6.6)."""
from __future__ import annotations

from datetime import datetime, timezone

from server.app.modules.redaccion.contracts.runtime import WorkspaceState

_AI_BLOCK_KINDS = frozenset({"AI_ASSISTED_TEXT", "AI_SUMMARY", "AI_REWRITE"})

# Target status when regenerating a failed block (based on failure_kind)
_REGEN_TARGET: dict[str, str] = {
    "ai_failed": "extracted",
    "extraction_failed": "draft",
    "script_failed": "draft",
    "validation_failed": "draft",
}


class UserReviewGateNode:
    """Transiciona todos los bloques IA de ai_generated → needs_review.

    Si quedan bloques en needs_review → status='in_review' (grafo pausa).
    Si todos los bloques IA están approved/locked → el grafo continúa.

    Maneja regenerate_blocks (9R.6.6): resetea bloques fallidos al estado de origen apropiado.
    Maneja skip_blocks (9R.6.6): filtra la petición de skip para bloques no requeridos únicamente.
    """

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        spec_by_id = {b.id: b for b in state.spec.blocks}
        updated_blocks = dict(state.blocks)
        now = datetime.now(timezone.utc)

        # Procesar regenerate_blocks: resetear bloques fallidos a su estado de origen
        for block_id in state.regenerate_blocks:
            block_state = updated_blocks.get(block_id)
            if block_state is None:
                continue
            target_status = _REGEN_TARGET.get(block_state.failure_kind or "", "draft")
            updated_blocks[block_id] = block_state.model_copy(update={
                "status": target_status,
                "failure_kind": None,
                "last_error_message": None,
                "last_updated_by": "system",
                "updated_at": now,
            })

        # Validar skip_blocks: solo se permiten bloques no requeridos
        new_skip = {
            bid for bid in state.skip_blocks
            if bid in spec_by_id and not spec_by_id[bid].required
        }

        # Transicionar ai_generated → needs_review
        for block_contract in state.spec.blocks:
            if block_contract.kind not in _AI_BLOCK_KINDS:
                continue
            block_id = block_contract.id
            block_state = updated_blocks.get(block_id)
            if block_state is None or block_state.status != "ai_generated":
                continue
            updated_blocks[block_id] = block_state.model_copy(update={
                "status": "needs_review",
                "last_updated_by": "system",
                "updated_at": now,
            })

        # Comprobar si quedan bloques pendientes de revisión
        ai_ids = {b.id for b in state.spec.blocks if b.kind in _AI_BLOCK_KINDS}
        pending = any(
            updated_blocks[bid].status == "needs_review"
            for bid in ai_ids
            if bid in updated_blocks
        )

        patch: dict = {
            "blocks": updated_blocks,
            "regenerate_blocks": set(),
            "skip_blocks": new_skip,
        }
        if pending:
            patch["status"] = "in_review"
        return patch


def review_gate_router(state: WorkspaceState) -> str:
    """Ruta condicional: 'pause' si hay revisión pendiente, 'continue' si todos aprobados."""
    return "pause" if state.status == "in_review" else "continue"
