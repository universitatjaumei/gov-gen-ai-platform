"""ApplyUserEditsNode — aplica ediciones manuales preservando el original IA (9R.6.4)."""
from __future__ import annotations

from datetime import datetime, timezone

from server.app.modules.redaccion.contracts.runtime import WorkspaceState


class ApplyUserEditsNode:
    """Aplica `state.user_edits[block_id]` sobre el contenido del bloque.

    Guarda el contenido IA original en `original_ai_content` para auditoría.
    Solo sobreescribe bloques que existan en user_edits.
    """

    async def __call__(self, state: WorkspaceState) -> dict:
        if not state.user_edits:
            return {}

        updated_blocks = dict(state.blocks)
        now = datetime.now(timezone.utc)

        for block_id, edit in state.user_edits.items():
            block_state = updated_blocks.get(block_id)
            if block_state is None:
                continue

            original = block_state.content
            updated_blocks[block_id] = block_state.model_copy(update={
                "content": {**(original or {}), **edit},
                "original_ai_content": original,
                "last_updated_by": "user",
                "updated_at": now,
            })

        return {"blocks": updated_blocks}
