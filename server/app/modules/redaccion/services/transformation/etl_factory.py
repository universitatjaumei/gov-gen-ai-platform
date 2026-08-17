"""ETLFactory — NL → operaciones declarativas, con refinamiento y fallback a script (9R.5.8).

Patrón análogo a ChartFactory (9R.5.7) y ScriptProposalService (9R.5.4):
  - El LLM propone JSON con un catálogo cerrado de operaciones.
  - Si la respuesta no valida → reintento con el error como feedback (hasta MAX_REFINEMENT_ITERATIONS).
  - Si tras MAX intentos sigue fallando → fallback: pedir un script Python
    `def transform(df)` y auditarlo con `ScriptSecurityAuditor`.

El motivo de preferir operaciones declarativas frente al script directo del
legacy es la auditabilidad: la UI puede mostrar las operaciones al usuario
antes de aplicarlas y el RunManifest las preserva sin opaco.
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from server.app.modules.redaccion.services.anonymization.hooks import (
    apply_post_llm,
    apply_pre_llm,
)
from server.app.modules.redaccion.services.script_auditor import (
    AuditResult,
    ScriptSecurityAuditor,
)
from server.app.modules.redaccion.services.actividades_llm import (
    ActividadLLM,
    PROMPT_POR_ACTIVIDAD,
    rellenar,
)
from server.app.modules.redaccion.services.transformation.operations import (
    Operation,
    catalogo_de_operaciones,
    parse_operations,
)

MAX_REFINEMENT_ITERATIONS = 3

_PROMPT_VERSION = "etl_operations_v1"

_SYSTEM_PROMPT = """\
Eres un planificador de transformaciones tabulares. Dado un esquema y una
instrucción en lenguaje natural, produces un plan declarativo en JSON.

DEVUELVE ÚNICAMENTE JSON VÁLIDO sin texto adicional, sin markdown, sin fences.

FORMATO:
{
  "mode": "operations",
  "operations": [ ... ]
}

CADA OPERACIÓN DEBE SER UNA DE ESTAS:
  {"op": "filter",    "col": <str>, "comparator": "==|!=|>|<|>=|<=|contains|not_contains|in|isnull|notnull", "value": <any>}
  {"op": "aggregate", "col": <str>, "function": "sum|mean|min|max|count|median|std"}
  {"op": "join",      "other_block_ref": <str>, "on": <str|list[str]>, "how": "inner|left|right|outer"}
  {"op": "pivot",     "index": <str|list[str]>, "columns": <str>, "values": <str>, "aggfunc": "sum|mean|min|max|count"}
  {"op": "normalize", "cols": [<str>], "method": "min_max|z_score"}
  {"op": "groupby",   "cols": [<str>], "agg_dict": {<col>: "sum|mean|min|max|count|median|std"}}

REGLAS:
  - Usa solo columnas presentes en el esquema.
  - No inventes operaciones nuevas; si la petición no encaja, devuelve {"mode": "operations", "operations": []}.
  - El campo "mode" es siempre "operations".
"""

_FALLBACK_SCRIPT_SYSTEM_PROMPT = """\
La petición no encaja en el catálogo de operaciones declarativas. Genera un
script Python con una función:

    def transform(df: pd.DataFrame) -> pd.DataFrame: ...

REGLAS:
  - Solo imports de: pandas, numpy, re, math, datetime, collections, json, io, unicodedata.
  - No uses open, eval, exec, __import__, subprocess, os.system u otros builtins peligrosos.
  - Devuelve únicamente código Python, sin explicaciones, sin markdown.
"""


class ETLPlan(BaseModel):
    """Plan de transformación devuelto por el ETLFactory.

    En modo "operations" lleva la lista lista para aplicar.
    En modo "script" lleva el código + el resultado de la auditoría.
    """

    mode: str  # "operations" | "script"
    operations: list[Operation] = []
    script_code: str | None = None
    script_audit: AuditResult | None = None
    model_used: str = ""
    prompt_version: str = _PROMPT_VERSION
    refinement_iterations: int = 0


class ETLFactory:
    """Convierte instrucciones en lenguaje natural en planes ETL auditables."""

    def __init__(
        self, llm: Any, model_name: str = "", system_prompt: str | None = None
    ) -> None:
        self._llm = llm
        self._model_name = model_name
        self._auditor = ScriptSecurityAuditor()
        # PRO.4 — el prompt puede venir de la biblioteca (PRO.2.1); por defecto, el del
        # catálogo de actividades.
        self._system_prompt = system_prompt

    async def generate_operations_from_nl(
        self,
        nl_prompt: str,
        schema: dict[str, Any],
        anonymization_context: Any = None,
    ) -> ETLPlan:
        """Si se pasa `anonymization_context` (Fase 13), el prompt se sustituye
        antes del LLM y el raw output se revierte antes de parsearlo, para que
        las operaciones y/o el script resultantes operen sobre valores originales.
        """
        # PRE-HOOK Fase 13.
        nl_prompt_for_llm = apply_pre_llm(nl_prompt, anonymization_context)
        last_error: str | None = None
        iterations = 0

        while iterations < MAX_REFINEMENT_ITERATIONS:
            messages = self._build_messages(nl_prompt_for_llm, schema, last_error)
            raw = await self._invoke(messages)
            # POST-HOOK Fase 13 sobre el raw text antes de parsear JSON.
            raw = apply_post_llm(raw, anonymization_context)
            try:
                ops = self._parse_operations_payload(raw)
                return ETLPlan(
                    mode="operations",
                    operations=ops,
                    model_used=self._model_name,
                    refinement_iterations=iterations,
                )
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_error = str(exc)[:500]
                iterations += 1

        # Fallback: pide un script Python y audítalo.
        script_messages = [
            {"role": "system", "content": _FALLBACK_SCRIPT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"ESQUEMA: {json.dumps(schema, ensure_ascii=False)}\n"
                    f"INSTRUCCIÓN: {nl_prompt_for_llm}\n"
                    f"FALLO PREVIO: {last_error or 'plan inválido'}"
                ),
            },
        ]
        raw_script = await self._invoke(script_messages)
        code = self._extract_python_code(raw_script)
        # POST-HOOK Fase 13 en el código generado.
        code = apply_post_llm(code, anonymization_context)
        audit = self._auditor.audit(code)
        return ETLPlan(
            mode="script",
            script_code=code,
            script_audit=audit,
            model_used=self._model_name,
            refinement_iterations=MAX_REFINEMENT_ITERATIONS,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        nl_prompt: str,
        schema: dict[str, Any],
        last_error: str | None,
    ) -> list[dict[str, str]]:
        user_msg = (
            f"ESQUEMA: {json.dumps(schema, ensure_ascii=False)}\n"
            f"INSTRUCCIÓN: {nl_prompt}"
        )
        if last_error:
            user_msg += (
                "\n\nINTENTO ANTERIOR INVÁLIDO. Error de validación:\n"
                f"{last_error}\n"
                "Devuelve un JSON corregido que cumpla el esquema."
            )
        return [
            {"role": "system", "content": self._prompt_del_sistema(schema)},
            {"role": "user", "content": user_msg},
        ]

    def _prompt_del_sistema(self, schema: dict[str, Any]) -> str:
        """El prompt con el catálogo de operaciones **generado del contrato**.

        PRO.4 — aquí había una lista escrita a mano con las seis operaciones de 9R.5.8. Al
        portar las diez de limpieza del legacy, una lista a mano se queda corta en el primer
        cambio y el síntoma es un modelo que no usa la mitad del catálogo. Es el mismo arreglo
        que VER.3 hizo con el borrador de plantillas: el esquema real, no una copia.
        """
        return rellenar(
            self._system_prompt or PROMPT_POR_ACTIVIDAD[ActividadLLM.TRANSFORMACION_ETL],
            {
                "esquema_de_operaciones": catalogo_de_operaciones(),
                "esquema_de_datos": json.dumps(schema, ensure_ascii=False),
            },
        )

    async def _invoke(self, messages: list[dict[str, str]]) -> str:
        response = await self._llm.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    @staticmethod
    def _parse_operations_payload(raw: str) -> list[Operation]:
        cleaned = ETLFactory._strip_fences(raw)
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("Top-level response is not a JSON object")
        if data.get("mode") != "operations":
            raise ValueError(f"Unexpected mode in response: {data.get('mode')!r}")
        ops_payload = data.get("operations")
        if not isinstance(ops_payload, list) or not ops_payload:
            raise ValueError("Response contains no operations")
        return parse_operations(ops_payload)

    @staticmethod
    def _strip_fences(raw: str) -> str:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        return raw.strip()

    @staticmethod
    def _extract_python_code(raw: str) -> str:
        fenced = re.search(r"```(?:python)?\s*(.*?)```", raw, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        return raw.strip()
