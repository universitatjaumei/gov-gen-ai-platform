"""LLMSpecService — 9R.4.1.

Convierte texto en lenguaje natural en un ReportTemplateDraft estructurado.
No persiste nada; solo propone. La validación estructural es responsabilidad
de DraftValidator (9R.4.2).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
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

PROMPT_VERSION = "llm_spec_v2"

#: Cada bloque tiene campos propios y obligatorios. Sin esto en el prompt, el modelo propone
#: estructuras razonables que el contrato rechaza, y el usuario ve un error del servidor por
#: algo que no hizo mal.
_CAMPOS_OBLIGATORIOS = (
    "Every block needs: id, title, order. Additionally, by kind:\n"
    "- STATIC_TEXT: content (the literal text).\n"
    "- USER_INPUT: field_type (text | number | date).\n"
    "- DETERMINISTIC_DATA: source_pipeline (excel | pdf_text | pdf_table | manual |"
    " admin_script).\n"
    "- TABLE: data_block_ref (the id of a DETERMINISTIC_DATA block in this same template).\n"
    "- CHART: data_block_ref, and optionally config with chart_type"
    " (bar | line | pie | scatter | histogram).\n"
    "- AI_ASSISTED_TEXT, AI_SUMMARY, AI_REWRITE: ai_prompt_template_id and review_policy_id."
    " Use 'generic_report_v1' and 'required' unless the request says otherwise.\n"
    "- CITATION_BLOCK: source_block_refs (list of block ids).\n"
    "- REVIEW_GATE: review_policy_id.\n"
    "A TABLE or CHART without a DETERMINISTIC_DATA block to point at is invalid: add the"
    " data block first.\n"
    # Sin esto, `DraftValidator` devuelve ok=False en toda propuesta con IA y el botón de
    # aprobar —que exige ok=true— no se habilita nunca. Es decir: la pantalla entera era
    # inutilizable para el caso normal.
    "If the template has ANY of AI_ASSISTED_TEXT, AI_SUMMARY or AI_REWRITE, it MUST also"
    " include one REVIEW_GATE block: a human approves the AI text before the report is"
    " assembled.\n"
    # Igual que con los bloques: enumerar `required_slots` sin decir cómo es un slot
    # producía `{'id': ..., 'block_ref': ...}` y un 422 en cada propuesta con datos.
    "Each entry of proposed_inputs.required_slots / optional_slots is:\n"
    '  {"slot_id": "budget_data", "kind": "excel",'
    ' "label": {"es": "...", "ca": "...", "en": "..."}}\n'
    "kind is one of: pdf, excel, csv, text, number, date, selector. `label` is an object"
    " with the three languages, never a plain string. Do not add fields like `id` or"
    " `block_ref`: a slot does not point at a block; a DETERMINISTIC_DATA block declares"
    " which pipeline reads it.\n"
)


class PropuestaInvalidaError(ValueError):
    """El modelo devolvió una estructura que el contrato de plantilla no acepta.

    Es un fallo **del modelo**, no del servidor: sale como error de dominio para que el
    router lo traduzca a 422 en vez de dejar una traza de pydantic en el log y un 500 en la
    pantalla de quien solo pidió un informe con una tabla.
    """


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
        # Enumerar los tipos sin decir qué exige cada uno producía propuestas que no
        # validaban y salían como 500. Visto en la primera petición real (VER.3): un bloque
        # TABLE sin `data_block_ref`, que es obligatorio.
        + _CAMPOS_OBLIGATORIOS
        + _esquema_del_contrato()
        + "Respond ONLY with valid JSON — no markdown, no explanation."
        + admin_note
    )


@lru_cache(maxsize=1)
def _esquema_del_contrato() -> str:
    """El JSON Schema real de las tres piezas que el modelo tiene que producir.

    Describir el contrato a mano fue un juego del topo: faltaba `data_block_ref`, luego el
    `REVIEW_GATE`, luego la forma de `InputSlot`, luego el título de sección llegaba como
    diccionario i18n. El contrato lo conoce pydantic, así que se lo damos tal cual y deja de
    adivinarse. `lru_cache` porque generarlo cuesta y no cambia en caliente.
    """
    esquema = {
        "proposed_sections": TypeAdapter(list[SectionContract]).json_schema(),
        "proposed_blocks": TypeAdapter(list[BlockContract]).json_schema(),
        "proposed_inputs": TypeAdapter(InputContract).json_schema(),
    }
    return (
        "The exact JSON Schema of these three fields follows. It is authoritative: any field"
        " name or type not in it will be rejected.\n"
        + json.dumps(esquema, ensure_ascii=False)
        + "\n"
    )


def _extract_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    return text.strip()


#: Un solo reintento: si la segunda tampoco valida, el problema no es de forma.
INTENTOS_DE_PROPUESTA = 2

_REINTENTO = (
    "Your previous answer did not validate against the schema. Fix EXACTLY this and return"
    " the whole JSON again:\n{error}"
)


class LLMSpecService:
    """Servicio de especificación de plantillas vía LLM. Sin acceso a BD."""

    def __init__(self, llm: Any, model_name: str, prompt_version: str = PROMPT_VERSION) -> None:
        self._llm = llm
        self._model_name = model_name
        self._prompt_version = prompt_version

    async def _proponer(self, messages: list[dict]) -> dict:
        """Una vuelta: pide, extrae el JSON y comprueba que las tres piezas validan.

        La validación va aquí y no en el llamador para que el reintento pueda usar el error
        como respuesta al modelo; devolver el dict ya comprobado deja al llamador con la
        construcción del borrador y nada más.
        """
        respuesta = await self._llm.ainvoke(messages)
        raw = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
        try:
            data = json.loads(_extract_json(raw))
        except json.JSONDecodeError as fallo:
            raise PropuestaInvalidaError(f"la respuesta no es JSON: {fallo}") from fallo

        try:
            [SectionContract(**s) for s in data.get("proposed_sections", [])]
            [_BLOCK_ADAPTER.validate_python(b) for b in data.get("proposed_blocks", [])]
            InputContract(
                **data.get("proposed_inputs", {"required_slots": [], "optional_slots": []})
            )
        except Exception as fallo:  # noqa: BLE001 — pydantic levanta varios tipos
            raise PropuestaInvalidaError(str(fallo)) from fallo
        return data

    async def propose_template(
        self,
        prompt_nl: str,
        owner_kind: Literal["admin", "user"],
    ) -> ReportTemplateDraft:
        messages = [
            {"role": "system", "content": _build_system_prompt(owner_kind)},
            {"role": "user", "content": prompt_nl},
        ]

        # Un reintento con el error como respuesta, igual que `etl_factory`: la mayoría de
        # estos fallos son de forma y el modelo los corrige en cuanto se le dice cuál es,
        # sin que quien pidió el informe tenga que reformular su petición.
        ultimo_fallo: str | None = None
        for intento in range(INTENTOS_DE_PROPUESTA):
            if ultimo_fallo is not None:
                messages = messages + [
                    {"role": "user", "content": _REINTENTO.format(error=ultimo_fallo)}
                ]
            try:
                data = await self._proponer(messages)
                break
            except PropuestaInvalidaError as fallo:
                ultimo_fallo = str(fallo)
                if intento == INTENTOS_DE_PROPUESTA - 1:
                    raise

        sections = [SectionContract(**s) for s in data.get("proposed_sections", [])]
        blocks = [_BLOCK_ADAPTER.validate_python(b) for b in data.get("proposed_blocks", [])]
        inputs = InputContract(
            **data.get("proposed_inputs", {"required_slots": [], "optional_slots": []})
        )

        return ReportTemplateDraft(
            proposed_profile=data.get("proposed_profile", "GENERIC_REPORT"),
            proposed_sections=sections,
            proposed_blocks=blocks,
            proposed_inputs=inputs,
            rationale=data.get("rationale", ""),
            model_used=self._model_name,
            prompt_version=self._prompt_version,
        )
