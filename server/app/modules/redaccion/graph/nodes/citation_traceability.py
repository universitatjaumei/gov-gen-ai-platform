"""CitationAndTraceabilityNode — adjunta citaciones a bloques IA referenciando datos origen (9R.6.3)."""
from __future__ import annotations

from server.app.modules.redaccion.contracts.runtime import Citation, WorkspaceState

_AI_BLOCK_KINDS = frozenset({"AI_ASSISTED_TEXT", "AI_SUMMARY", "AI_REWRITE"})


class CitationAndTraceabilityNode:
    """Para cada bloque IA en estado ai_generated, adjunta Citation de los bloques fuente (depends_on)."""

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        updated_blocks = dict(state.blocks)

        for block_contract in state.spec.blocks:
            if block_contract.kind not in _AI_BLOCK_KINDS:
                continue

            block_id = block_contract.id
            block_state = updated_blocks.get(block_id)
            if block_state is None or block_state.status != "ai_generated":
                continue

            citations: list[Citation] = []
            for ref in block_contract.depends_on:
                source_state = state.blocks.get(ref.block_id)
                if source_state is None or not source_state.content:
                    continue

                excerpt: str | None = None
                if ref.projection == "field" and ref.field_path:
                    excerpt = str(source_state.content.get(ref.field_path, ""))[:300]
                elif ref.projection == "summary":
                    excerpt = str(source_state.content.get("free_text", ""))[:300]
                else:
                    excerpt = str(source_state.content)[:300]

                citations.append(Citation(
                    source_document=ref.block_id,
                    excerpt=excerpt or None,
                ))

            if citations:
                updated_blocks[block_id] = block_state.model_copy(
                    update={"citations": citations}
                )

        return {"blocks": updated_blocks}
