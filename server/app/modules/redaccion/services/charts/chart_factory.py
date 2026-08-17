"""ChartFactory — de una frase a un gráfico (9R.5.7, reordenada en PRO.8).

Dos caminos, y el orden importa:

1. **`generate_chart_from_nl`** rellena `ChartConfiguration` —un contrato cerrado que el
   renderizador determinista sabe dibujar—. Es el camino normal.
2. **`generate_script`** pide código matplotlib y lo audita. Es el último recurso, para lo que
   el catálogo no puede expresar.

Hasta PRO.8 sólo existía el segundo, y era el que se usaba **siempre**: pedir «barras
horizontales» costaba modelo + auditoría + sandbox para lo que es un campo. Es el mismo patrón
que PRO.4 aplicó al ETL, y por la misma razón: un plan declarativo se puede enseñar al usuario
antes de aplicarlo, y el RunManifest lo guarda sin opaco.
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from server.app.modules.redaccion.services.actividades_llm import (
    ActividadLLM,
    PROMPT_POR_ACTIVIDAD,
    rellenar,
)
from server.app.modules.redaccion.services.anonymization.hooks import (
    apply_post_llm,
    apply_pre_llm,
)
from server.app.modules.redaccion.services.charts.chart_configuration import (
    ChartConfiguration,
    catalogo_de_configuracion,
)
from server.app.modules.redaccion.services.script_auditor import AuditResult, ScriptSecurityAuditor

MAX_REFINEMENT_ITERATIONS = 3

_PROMPT_VERSION = "chart_proposal_v1"
_PROMPT_VERSION_CONFIG = "chart_configuration_v1"

_SYSTEM_PROMPT = """\
Eres un asistente experto en visualización de datos con Python (matplotlib, seaborn).

REGLAS ESTRICTAS:
1. La variable `df` (pandas DataFrame) ya está cargada. NO la crees de nuevo.
2. Usa `matplotlib.pyplot` o `seaborn`. NO uses plotly ni pandas.plot().
3. NO llames a `plt.show()` ni `plt.savefig()`. El renderizador los maneja.
4. Solo imports permitidos: pandas, matplotlib, seaborn, numpy, io, math, re.
5. Devuelve ÚNICAMENTE el código Python. Sin explicaciones, sin markdown.
"""


class _NoEncajaEnElCatalogo(Exception):
    """El modelo ha dicho, a propósito, que la petición no cabe en la configuración.

    Se distingue de un JSON inválido porque **no se reintenta**: reintentar una respuesta
    deliberada quema dos llamadas para volver a oír lo mismo. Sólo se reintenta lo que el
    modelo puede corregir.
    """


class ChartScript(BaseModel):
    code: str
    audit_result: AuditResult
    model_used: str
    prompt_version: str = _PROMPT_VERSION


class ChartPlan(BaseModel):
    """Cómo se va a dibujar el gráfico: con configuración, o con código si no hay otra.

    `mode` es lo que la pantalla necesita para saber si puede enseñar el plan (configuración) o
    tiene que enseñar código que además exige aprobación.
    """

    mode: Literal["configuration", "script"]
    configuration: ChartConfiguration | None = None
    script_code: str | None = None
    script_audit: AuditResult | None = None
    model_used: str = ""
    prompt_version: str = _PROMPT_VERSION_CONFIG
    refinement_iterations: int = 0


class ChartFactory:
    """Traduce una petición en lenguaje natural a un gráfico."""

    def __init__(self, llm: Any, model_name: str = "", system_prompt: str | None = None) -> None:
        self._llm = llm
        self._model_name = model_name
        self._auditor = ScriptSecurityAuditor()
        # PRO.8 — el prompt puede venir de la biblioteca (PRO.2.1).
        self._system_prompt = system_prompt

    # ------------------------------------------------------------------
    # Camino normal: configuración declarativa
    # ------------------------------------------------------------------

    async def generate_chart_from_nl(
        self,
        nl_prompt: str,
        schema: dict[str, Any],
        anonymization_context: Any = None,
    ) -> ChartPlan:
        """La configuración del gráfico, y sólo si no encaja, un script auditado."""
        nl_prompt_for_llm = apply_pre_llm(nl_prompt, anonymization_context)
        last_error: str | None = None
        iterations = 0

        while iterations < MAX_REFINEMENT_ITERATIONS:
            raw = await self._invoke(
                self._build_config_messages(nl_prompt_for_llm, schema, last_error)
            )
            raw = apply_post_llm(raw, anonymization_context)
            try:
                configuracion = self._parse_configuration_payload(raw)
                return ChartPlan(
                    mode="configuration",
                    configuration=configuracion,
                    model_used=self._model_name,
                    refinement_iterations=iterations,
                )
            except _NoEncajaEnElCatalogo:
                break
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_error = str(exc)[:500]
                iterations += 1

        # Lo que el catálogo no expresa se programa, y se audita como cualquier otro script.
        script = await self.generate_script(
            nl_prompt, schema, anonymization_context=anonymization_context
        )
        return ChartPlan(
            mode="script",
            script_code=script.code,
            script_audit=script.audit_result,
            model_used=self._model_name,
            refinement_iterations=iterations,
        )

    # ------------------------------------------------------------------
    # Último recurso: script matplotlib
    # ------------------------------------------------------------------

    async def generate_script(
        self,
        nl_prompt: str,
        schema: dict[str, Any],
        anonymization_context: Any = None,
    ) -> ChartScript:
        """Genera y audita un script matplotlib para el prompt y esquema dados.

        Si se pasa `anonymization_context` (Fase 13), el prompt NL se sustituye
        antes del LLM y el código generado se revierte después.
        """
        # PRE-HOOK Fase 13.
        nl_prompt_for_llm = apply_pre_llm(nl_prompt, anonymization_context)
        user_msg = (
            f"ESQUEMA DE DATOS:\n"
            f"  Columnas: {schema.get('columns', [])}\n"
            f"  Tipos:    {schema.get('dtypes', {})}\n\n"
            f"PETICIÓN: {nl_prompt_for_llm}"
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        raw = await self._invoke(messages)
        code = self._extract_code(raw)
        # POST-HOOK Fase 13.
        code = apply_post_llm(code, anonymization_context)
        audit = self._auditor.audit(code)
        return ChartScript(
            code=code,
            audit_result=audit,
            model_used=self._model_name,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_config_messages(
        self, nl_prompt: str, schema: dict[str, Any], last_error: str | None
    ) -> list[dict[str, str]]:
        user_msg = (
            f"ESQUEMA: {json.dumps(schema, ensure_ascii=False)}\n"
            f"PETICIÓN: {nl_prompt}"
        )
        if last_error:
            user_msg += (
                "\n\nINTENTO ANTERIOR INVÁLIDO. Error de validación:\n"
                f"{last_error}\n"
                "Devuelve un JSON corregido que cumpla el contrato."
            )
        prompt = rellenar(
            self._system_prompt or PROMPT_POR_ACTIVIDAD[ActividadLLM.CONFIGURACION_DE_GRAFICO],
            {
                "esquema_de_configuracion": catalogo_de_configuracion(),
                "esquema_de_datos": json.dumps(schema, ensure_ascii=False),
            },
        )
        return [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg},
        ]

    @staticmethod
    def _parse_configuration_payload(raw: str) -> ChartConfiguration:
        payload = json.loads(ChartFactory._strip_fences(raw))
        if not isinstance(payload, dict):
            raise ValueError("la respuesta no es un objeto JSON")
        configuracion = payload.get("configuration")
        if not isinstance(configuracion, dict) or not configuracion:
            # Vacío es la señal acordada con el modelo para «esto no cabe en el catálogo».
            raise _NoEncajaEnElCatalogo("configuration vacía")
        return ChartConfiguration.model_validate(configuracion)

    async def _invoke(self, messages: list[dict[str, str]]) -> str:
        response = await self._llm.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    @staticmethod
    def _strip_fences(raw: str) -> str:
        fenced = re.search(r"```(?:json)?\s*\n(.*?)```", raw, re.DOTALL)
        return (fenced.group(1) if fenced else raw).strip()

    @staticmethod
    def _extract_code(raw: str) -> str:
        fenced = re.search(r"```(?:python)?\s*\n(.*?)```", raw, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        return raw.strip()
