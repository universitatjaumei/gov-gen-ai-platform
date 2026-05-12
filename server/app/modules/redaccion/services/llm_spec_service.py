"""LLMSpecService — 9R.4.1.

Convierte texto en lenguaje natural en un ReportTemplateDraft estructurado.
No persiste nada; solo propone. La validación estructural es responsabilidad
de DraftValidator (9R.4.2).
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import TypeAdapter

from server.app.modules.redaccion.contracts.blocks import BlockContract
from server.app.modules.redaccion.contracts.drafts import ReportTemplateDraft
from server.app.modules.redaccion.contracts.inputs import InputContract
from server.app.modules.redaccion.contracts.template import SectionContract

_BLOCK_KINDS = [
    "STATIC_TEXT",
    "USER_INPUT",
    "DETERMINISTIC_DATA",
    "TABLE",
    "CHART",
    "AI_ASSISTED_TEXT",
    "AI_SUMMARY",
    "AI_REWRITE",
    "CITATION_BLOCK",
    "REVIEW_GATE",
]

_BLOCK_ADAPTER: TypeAdapter[BlockContract] = TypeAdapter(BlockContract)

PROMPT_VERSION = "llm_spec_v1"


def _build_system_prompt(owner_kind: Literal["admin", "user"]) -> str:
    admin_note = ""
    if owner_kind == "admin":
        admin_note = (
            "\n- You are acting as a platform administrator. "
            "You may suggest is_global=true for templates intended for all users."
        )

    return (
        "You are an expert at designing report templates for government and academic institutions.\n"
        "Given a natural language description, return a JSON object with EXACTLY this structure:\n"
        "{\n"
        '  "proposed_profile": "<one of: GENERIC_REPORT, ANNUAL_REPORT, DOCTORATE_PROGRAM_REPORT,'
        ' CONTRACT_REPORT, FREEFORM_MEMO>",\n'
        '  "proposed_sections": [{"id": "s1", "title": "...", "order": 1, "block_ids": ["b1"]}],\n'
        '  "proposed_blocks": [{"kind": "STATIC_TEXT", "id": "b1", "title": "..."}],\n'
        '  "proposed_inputs": {"required_slots": [], "optional_slots": []},\n'
        '  "rationale": "Why this structure fits the request."\n'
        "}\n"
        f"Valid 'kind' values for blocks: {_BLOCK_KINDS}.\n"
        "Do NOT use any block kind not in this list.\n"
        "Respond ONLY with valid JSON — no markdown, no explanation."
        + admin_note
    )


def _extract_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    return text.strip()


class LLMSpecService:
    """Servicio de especificación de plantillas vía LLM. Sin acceso a BD."""

    def __init__(self, llm: Any, model_name: str, prompt_version: str = PROMPT_VERSION) -> None:
        self._llm = llm
        self._model_name = model_name
        self._prompt_version = prompt_version

    async def propose_template(
        self,
        prompt_nl: str,
        owner_kind: Literal["admin", "user"],
    ) -> ReportTemplateDraft:
        messages = [
            {"role": "system", "content": _build_system_prompt(owner_kind)},
            {"role": "user", "content": prompt_nl},
        ]
        response = await self._llm.ainvoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
        data = json.loads(_extract_json(raw))

        sections = [SectionContract(**s) for s in data.get("proposed_sections", [])]
        blocks = [_BLOCK_ADAPTER.validate_python(b) for b in data.get("proposed_blocks", [])]
        inputs_data = data.get("proposed_inputs", {"required_slots": [], "optional_slots": []})
        inputs = InputContract(**inputs_data)

        return ReportTemplateDraft(
            proposed_profile=data.get("proposed_profile", "GENERIC_REPORT"),
            proposed_sections=sections,
            proposed_blocks=blocks,
            proposed_inputs=inputs,
            rationale=data.get("rationale", ""),
            model_used=self._model_name,
            prompt_version=self._prompt_version,
        )
