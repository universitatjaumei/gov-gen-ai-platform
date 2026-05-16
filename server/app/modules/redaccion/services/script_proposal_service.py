"""ScriptProposalService — 9R.5.5 Parte 3.

Genera scripts Python de extracción a partir de prompts NL del usuario y
audita el resultado con ScriptSecurityAuditor (9R.5.4). NO persiste.

Reutiliza el mismo contrato de salida que AdminScriptExtractionPipeline:
- variables disponibles: file_path (str), raw_text (str), options (dict)
- el script debe asignar `result: dict` con tables/metrics/free_text.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel

from server.app.modules.redaccion.services.script_auditor import (
    AuditResult,
    ScriptSecurityAuditor,
    WHITELIST_MODULES,
)


PROMPT_VERSION = "script_proposal_v1"


def _build_system_prompt(sample_schema: dict[str, Any] | None) -> str:
    schema_hint = ""
    if sample_schema:
        schema_hint = (
            "\n\nSCHEMA DE LOS DATOS DE ENTRADA (informativo):\n"
            f"{sample_schema}\n"
        )
    whitelist = sorted(WHITELIST_MODULES)
    return (
        "Eres un asistente experto en escribir scripts de extracción de datos en Python.\n"
        "\n"
        "REGLAS DURAS:\n"
        f"- Sólo puedes importar de esta lista blanca: {whitelist}.\n"
        "- Está PROHIBIDO usar eval, exec, __import__, compile, open.\n"
        "- Está PROHIBIDO usar subprocess, os.system, requests, urllib, socket, "
        "ni cualquier acceso a la red o al sistema.\n"
        "- El script DEBE asignar la variable `result` (dict) con las claves:\n"
        "    tables   : list[dict]  → cada dict: name, headers, rows, source_page\n"
        "    metrics  : list[dict]  → cada dict: name, value, unit (opcional)\n"
        "    free_text: str | None\n"
        "- Variables disponibles para tu script: file_path (str), raw_text (str), options (dict).\n"
        "- Usa preferentemente pandas y openpyxl para Excel; pdfplumber para PDFs.\n"
        "- Devuelve SÓLO código Python, sin explicaciones ni markdown."
        f"{schema_hint}"
    )


_FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "user": (
            "Extrae todas las filas del Excel y devuelve una tabla con sus columnas."
        ),
        "assistant": (
            "import pandas as pd\n"
            "\n"
            "df = pd.read_excel(file_path)\n"
            "result = {\n"
            "    'tables': [{\n"
            "        'name': 'sheet1',\n"
            "        'headers': list(df.columns),\n"
            "        'rows': df.astype(str).values.tolist(),\n"
            "        'source_page': None,\n"
            "    }],\n"
            "    'metrics': [],\n"
            "    'free_text': None,\n"
            "}\n"
        ),
    },
    {
        "user": "Devuelve el texto plano del PDF.",
        "assistant": (
            "import pdfplumber\n"
            "\n"
            "with pdfplumber.open(file_path) as pdf:\n"
            "    text = '\\n\\n'.join(p.extract_text() or '' for p in pdf.pages)\n"
            "result = {'tables': [], 'metrics': [], 'free_text': text}\n"
        ),
    },
    {
        "user": (
            "Lee el Excel y calcula la suma de la columna 'importe' agrupada por "
            "'departamento'; devuelve una tabla con dos columnas."
        ),
        "assistant": (
            "import pandas as pd\n"
            "\n"
            "df = pd.read_excel(file_path)\n"
            "agg = df.groupby('departamento')['importe'].sum().reset_index()\n"
            "result = {\n"
            "    'tables': [{\n"
            "        'name': 'importe_por_departamento',\n"
            "        'headers': ['departamento', 'importe_total'],\n"
            "        'rows': agg.astype(str).values.tolist(),\n"
            "        'source_page': None,\n"
            "    }],\n"
            "    'metrics': [],\n"
            "    'free_text': None,\n"
            "}\n"
        ),
    },
]


def _extract_code(text: str) -> str:
    """Si el LLM devuelve markdown fences, extrae solo el código."""
    m = re.search(r"```(?:python)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    return text.strip()


class ProposalResult(BaseModel):
    """Resultado de `ScriptProposalService.propose()`. Sin persistencia."""

    code: str
    audit_result: AuditResult
    model_used: str
    prompt_version: str = PROMPT_VERSION
    rationale: str | None = None


class ScriptProposalService:
    """Genera scripts a partir de NL + audita con ScriptSecurityAuditor."""

    def __init__(
        self,
        llm: Any,
        script_auditor: ScriptSecurityAuditor | None = None,
        model_name: str = "unknown",
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self._llm = llm
        self._auditor = script_auditor or ScriptSecurityAuditor()
        self._model_name = model_name
        self._prompt_version = prompt_version

    async def propose(
        self,
        prompt_nl: str,
        sample_schema: dict[str, Any] | None = None,
        owner_kind: Literal["user", "platform"] = "user",
    ) -> ProposalResult:
        system_prompt = _build_system_prompt(sample_schema)
        if owner_kind == "platform":
            system_prompt += (
                "\n\nCONTEXTO: este script será propuesto para una plantilla GLOBAL "
                "(uso por toda la plataforma). Sé especialmente conservador con las "
                "operaciones; evita asumir nombres de columna concretos si no aparecen "
                "en el SCHEMA."
            )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for example in _FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": example["user"]})
            messages.append({"role": "assistant", "content": example["assistant"]})
        messages.append({"role": "user", "content": prompt_nl})

        response = await self._llm.ainvoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
        code = _extract_code(raw)
        audit = self._auditor.audit(code)

        return ProposalResult(
            code=code,
            audit_result=audit,
            model_used=self._model_name,
            prompt_version=self._prompt_version,
        )
