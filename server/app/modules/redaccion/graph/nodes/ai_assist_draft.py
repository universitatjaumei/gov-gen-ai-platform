"""AIAssistDraftNode — genera texto IA para bloques AI_ASSISTED_TEXT / AI_SUMMARY / AI_REWRITE (9R.6.3/9R.6.6/9R.5.9)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol

from server.app.modules.redaccion.contracts.runtime import ExtractionWarning, WorkspaceState
from server.app.modules.redaccion.services.anonymization.hooks import (
    apply_post_llm,
    apply_pre_llm,
)

_AI_BLOCK_KINDS = frozenset({"AI_ASSISTED_TEXT", "AI_SUMMARY", "AI_REWRITE"})
_SKIP_STATUSES = frozenset({"approved", "locked"})
_MARKDOWN_LIMIT = 30_000


class LLMService(Protocol):
    model_name: str

    async def generate(self, prompt: str, context: str) -> str: ...


def _block_text(content: dict) -> str:
    """Extrae el texto más rico disponible del contenido de un bloque.

    Preferencia (9R.5.9): document.markdown > free_text > repr(content).
    Si el documento es complex_tables, añade un volcado JSON de las tablas.
    """
    doc = content.get("document")
    if isinstance(doc, dict) and doc.get("markdown"):
        text = doc["markdown"][:_MARKDOWN_LIMIT]
        if doc.get("extraction_strategy") == "complex_tables":
            pages = doc.get("pages") or []
            tables = [tbl for p in pages for tbl in (p.get("tables") or [])]
            if tables:
                text += f"\n\ntables_json:\n{json.dumps(tables, ensure_ascii=False)[:10_000]}"
        return text
    if content.get("free_text"):
        return str(content["free_text"])
    return str(content)


def _build_context(blocks: dict) -> str:
    """Solo incluye bloques en estado `extracted` o `approved`."""
    parts = []
    for bid, bstate in sorted(blocks.items()):
        if bstate.status in ("extracted", "approved") and bstate.content:
            parts.append(f"[{bid}]\n{_block_text(bstate.content)}")
    return "\n\n".join(parts)


class AIAssistDraftNode:
    """Invoca el LLM para generar borradores de bloques IA usando solo datos validados como contexto.

    En caso de fallo por bloque: marca status=failed(ai_failed) y continúa con el resto.
    """

    def __init__(self, llm_service: Any) -> None:
        self._llm = llm_service

    async def __call__(self, state: WorkspaceState) -> dict:
        if state.spec is None:
            return {}

        context = _build_context(state.blocks)
        anon_ctx = state.anonymization_context
        # PRE-HOOK (Fase 13): sustituimos PII en el contexto antes de cualquier LLM call.
        llm_context = apply_pre_llm(context, anon_ctx)
        updated_blocks = dict(state.blocks)
        new_warnings = list(state.warnings)
        now = datetime.now(timezone.utc)

        for block_contract in state.spec.blocks:
            if block_contract.kind not in _AI_BLOCK_KINDS:
                continue

            block_id = block_contract.id
            if block_id not in updated_blocks:
                continue

            block_state = updated_blocks[block_id]
            if block_state.status in _SKIP_STATUSES:
                continue

            try:
                raw_text = await self._llm.generate(
                    prompt=block_contract.ai_prompt_template_id,
                    context=llm_context,
                )
                # POST-HOOK (Fase 13): revertimos sintético → original en el output.
                text = apply_post_llm(raw_text, anon_ctx)
            except Exception as exc:
                new_warnings.append(ExtractionWarning(
                    block_id=block_id, message=str(exc), kind="ai_error",
                ))
                updated_blocks[block_id] = block_state.model_copy(update={
                    "status": "failed",
                    "failure_kind": "ai_failed",
                    "last_error_message": str(exc)[:500],
                    "last_updated_by": "system",
                    "updated_at": now,
                })
                continue

            updated_blocks[block_id] = block_state.model_copy(update={
                "content": {
                    "text": text,
                    "model_used": self._llm.model_name,
                    "prompt_version": block_contract.ai_prompt_template_id,
                },
                "status": "ai_generated",
                "last_updated_by": "ai",
                "updated_at": now,
            })

        return {"blocks": updated_blocks, "warnings": new_warnings}
