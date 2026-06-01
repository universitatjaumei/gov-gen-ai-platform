"""ChartFactory — generación de scripts matplotlib vía LLM (9R.5.7).

Patrón análogo a ScriptProposalService (9R.5.4): LLM propone código,
ScriptSecurityAuditor (con whitelist ampliada para charts) audita antes
de devolver el resultado.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from server.app.modules.redaccion.services.anonymization.hooks import (
    apply_post_llm,
    apply_pre_llm,
)
from server.app.modules.redaccion.services.script_auditor import AuditResult, ScriptSecurityAuditor

_PROMPT_VERSION = "chart_proposal_v1"

_SYSTEM_PROMPT = """\
Eres un asistente experto en visualización de datos con Python (matplotlib, seaborn).

REGLAS ESTRICTAS:
1. La variable `df` (pandas DataFrame) ya está cargada. NO la crees de nuevo.
2. Usa `matplotlib.pyplot` o `seaborn`. NO uses plotly ni pandas.plot().
3. NO llames a `plt.show()` ni `plt.savefig()`. El renderizador los maneja.
4. Solo imports permitidos: pandas, matplotlib, seaborn, numpy, io, math, re.
5. Devuelve ÚNICAMENTE el código Python. Sin explicaciones, sin markdown.
"""


class ChartScript(BaseModel):
    code: str
    audit_result: AuditResult
    model_used: str
    prompt_version: str = _PROMPT_VERSION


class ChartFactory:
    """Genera scripts matplotlib a partir de un prompt en lenguaje natural."""

    def __init__(self, llm: Any, model_name: str = "") -> None:
        self._llm = llm
        self._model_name = model_name
        self._auditor = ScriptSecurityAuditor()

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
        response = await self._llm.ainvoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
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

    @staticmethod
    def _extract_code(raw: str) -> str:
        fenced = re.search(r"```(?:python)?\s*\n(.*?)```", raw, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        return raw.strip()
