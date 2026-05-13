"""FinalAssemblerNode — ensambla el documento Markdown final y calcula su hash (9R.6.4/9R.6.6)."""
from __future__ import annotations

import hashlib

from server.app.modules.redaccion.contracts.runtime import (
    WorkspaceBlockedByFailedBlocksError,
    WorkspaceState,
)

_INCLUDABLE_STATUSES = frozenset({"approved", "locked"})


class FinalAssemblerNode:
    """Renderiza el Markdown ensamblado solo con bloques en estado approved/locked.

    Respeta el orden de secciones y bloques definido en el spec.
    Calcula final_document_hash (SHA-256).
    Transición workspace: * → assembled.

    Lanza WorkspaceBlockedByFailedBlocksError si algún bloque requerido tiene status=failed
    y no está en skip_blocks.
    """

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        # Verificar bloques requeridos fallidos que no estén en skip_blocks
        failed_required = [
            b.id
            for b in state.spec.blocks
            if b.required
            and b.id not in state.skip_blocks
            and state.blocks.get(b.id) is not None
            and state.blocks[b.id].status == "failed"
        ]
        if failed_required:
            raise WorkspaceBlockedByFailedBlocksError(failed_required)

        block_index = {b.id: b for b in state.spec.blocks}
        parts: list[str] = []

        for section in sorted(state.spec.sections, key=lambda s: s.order):
            section_parts: list[str] = []

            ordered_blocks = sorted(
                (block_index[bid] for bid in section.block_ids if bid in block_index),
                key=lambda b: b.order,
            )

            for block_contract in ordered_blocks:
                block_state = state.blocks.get(block_contract.id)
                if block_state is None or block_state.status not in _INCLUDABLE_STATUSES:
                    continue

                text = ""
                if block_state.content:
                    text = block_state.content.get("text") or str(block_state.content)

                section_parts.append(f"### {block_contract.title}\n\n{text}")

            if section_parts:
                parts.append(f"## {section.title}\n\n" + "\n\n".join(section_parts))

        document = "\n\n".join(parts)
        doc_hash = hashlib.sha256(document.encode()).hexdigest()

        return {
            "final_document": document,
            "final_document_hash": doc_hash,
            "status": "assembled",
        }
