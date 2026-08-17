"""ScriptProposalService — 9R.5.5 Parte 3.

Genera scripts Python de extracción a partir de prompts NL del usuario y
audita el resultado con ScriptSecurityAuditor (9R.5.4). NO persiste.

Reutiliza el mismo contrato de salida que AdminScriptExtractionPipeline:
- variables disponibles: file_path (str), raw_text (str), options (dict)
- el script debe asignar `result: dict` con tables/metrics/free_text.
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel

from server.app.modules.redaccion.services.script_auditor import (
    AuditResult,
    MODULOS_PROHIBIDOS,
    NOMBRES_PROHIBIDOS,
    RiskLevel,
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
    # PRO.2 — las listas se leen del auditor, no se reescriben aquí. Un prompt que enumera a
    # mano lo que otro fichero bloquea divergen en el primer cambio, y el síntoma es una
    # propuesta rechazada sin motivo entendible.
    whitelist = sorted(WHITELIST_MODULES)
    prohibidos = sorted(MODULOS_PROHIBIDOS)
    por_forma = sorted(n for n in NOMBRES_PROHIBIDOS if not n.startswith("__"))
    dunders = sorted(n for n in NOMBRES_PROHIBIDOS if n.startswith("__"))
    return (
        "Eres un asistente experto en escribir scripts de extracción de datos en Python.\n"
        "\n"
        "REGLAS DURAS:\n"
        f"- Sólo puedes importar de esta lista blanca: {whitelist}.\n"
        "  Importar cualquier otro módulo es una ADVERTENCIA: el script no se ejecuta hasta "
        "que una persona la acepta, así que no lo hagas sin necesidad.\n"
        f"- Estos módulos están PROHIBIDOS y son un rechazo inmediato: {prohibidos}.\n"
        "- Está PROHIBIDO usar eval, exec, __import__, compile, open.\n"
        "- Está PROHIBIDO usar estos nombres, incluso de la forma más inocente: "
        f"{por_forma}. Dan alcance al intérprete y el auditor los marca como CRÍTICO "
        "aunque los uses para algo razonable (`getattr(df, metodo)` también cuenta).\n"
        f"- Está PROHIBIDO tocar estos atributos: {dunders}.\n"
        "- Está PROHIBIDO escribir una ruta absoluta —ni `C:\\...`, ni `C:/...`, ni "
        "`/etc/...`, `/home/...`, `/tmp/...`—, ni siquiera en un comentario: es CRÍTICO. "
        "El único fichero que puedes leer es el que llega en `file_path`.\n"
        "- El script DEBE asignar la variable `result` (dict) con las claves:\n"
        "    tables   : list[dict]  → cada dict: name, headers, rows, source_page\n"
        "    metrics  : list[dict]  → cada dict: name, value, unit (opcional)\n"
        "    free_text: str | None\n"
        "- Variables disponibles para tu script: file_path (str), raw_text (str), options (dict).\n"
        "- Usa preferentemente pandas y openpyxl para Excel; pdfplumber para PDFs.\n"
        "- Devuelve SÓLO código Python, sin explicaciones ni markdown."
        f"{schema_hint}"
    )


AUDITOR_PROMPT_VERSION = "script_audit_v1"

_AUDITOR_SYSTEM_PROMPT = (
    "Eres un revisor de seguridad y de calidad de scripts de extracción de datos.\n"
    "\n"
    "El script que vas a leer **ya ha pasado un análisis estático** que bloquea por su forma "
    "las llamadas peligrosas, la introspección del intérprete, los módulos prohibidos y las "
    "rutas absolutas. Tu trabajo NO es repetir ese análisis: es mirar lo que un AST no puede "
    "ver.\n"
    "\n"
    "Fíjate en:\n"
    "- Si el script hace lo que el usuario pidió, o algo parecido pero distinto.\n"
    "- Si asume nombres de columna, hojas o formatos que no consten en la petición.\n"
    "- Si puede devolver datos vacíos o basura sin fallar, que es peor que fallar.\n"
    "- Si mete en `free_text` información que no debería salir del fichero de entrada.\n"
    "\n"
    "Responde SÓLO con este JSON, sin markdown ni explicaciones alrededor:\n"
    '{"veredicto": "acepta|duda|rechaza", "motivos": ["...", "..."]}\n'
    "\n"
    "`acepta` es «hace lo pedido y no veo riesgo»; `duda` es «funciona pero asume algo»; "
    "`rechaza` es «no hace lo pedido o es peligroso por lo que hace, no por cómo está "
    "escrito». Sé concreto y breve: cada motivo, una frase."
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


_VEREDICTOS = ("acepta", "duda", "rechaza")


def _leer_veredicto(texto: str, model_name: str) -> RevisionDelModelo:
    """El veredicto del auditor, y `duda` cuando no se le entiende.

    Un auditor que responde en prosa no puede convertirse en un «acepta» silencioso: el valor
    por defecto de una respuesta ilegible es la sospecha, no la aprobación. Y el texto crudo
    se conserva como motivo, porque es lo que permite saber si el prompt hay que afinarlo.
    """
    bruto = (texto or "").strip()
    bloque = re.search(r"\{[\s\S]*\}", bruto)
    if bloque:
        try:
            datos = json.loads(bloque.group(0))
        except json.JSONDecodeError:
            datos = None
        if isinstance(datos, dict) and datos.get("veredicto") in _VEREDICTOS:
            motivos = datos.get("motivos") or []
            return RevisionDelModelo(
                veredicto=datos["veredicto"],
                motivos=[str(m) for m in motivos] if isinstance(motivos, list) else [str(motivos)],
                model_used=model_name,
            )

    return RevisionDelModelo(
        veredicto="duda",
        motivos=[f"El auditor no devolvió un veredicto legible: {bruto[:300]}"],
        model_used=model_name,
    )


class RevisionDelModelo(BaseModel):
    """Lo que el modelo auditor opina del script — PRO.2.

    Es un segundo par de ojos, no una puerta: el veredicto **no toca** `audit_result`. La
    auditoría determinista es la que no se puede convencer; ésta explica, y lo que explica
    viaja con la propuesta hasta quien la revisa.
    """

    veredicto: Literal["acepta", "duda", "rechaza"]
    motivos: list[str]
    model_used: str
    prompt_version: str = AUDITOR_PROMPT_VERSION


class ProposalResult(BaseModel):
    """Resultado de `ScriptProposalService.propose()`. Sin persistencia."""

    code: str
    audit_result: AuditResult
    model_used: str
    prompt_version: str = PROMPT_VERSION
    rationale: str | None = None
    revision_del_modelo: RevisionDelModelo | None = None


class ScriptProposalService:
    """Genera scripts a partir de NL + audita con ScriptSecurityAuditor."""

    def __init__(
        self,
        llm: Any,
        script_auditor: ScriptSecurityAuditor | None = None,
        model_name: str = "unknown",
        prompt_version: str = PROMPT_VERSION,
        auditor_llm: Any = None,
        auditor_model_name: str = "",
    ) -> None:
        self._llm = llm
        self._auditor = script_auditor or ScriptSecurityAuditor()
        self._model_name = model_name
        self._prompt_version = prompt_version
        self._auditor_llm = auditor_llm
        self._auditor_model_name = auditor_model_name

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

        # Primero el AST, que no se puede convencer; después el modelo, que explica.
        audit = self._auditor.audit(code)
        revision = await self._revisar_con_modelo(code, prompt_nl, audit)

        return ProposalResult(
            code=code,
            audit_result=audit,
            model_used=self._model_name,
            prompt_version=self._prompt_version,
            revision_del_modelo=revision,
        )

    async def _revisar_con_modelo(
        self, code: str, prompt_nl: str, audit: AuditResult
    ) -> RevisionDelModelo | None:
        """El segundo par de ojos, cuando hay algo que mirar.

        No se pide sobre un script CRÍTICO: no se va a ejecutar nunca, así que juzgar su
        semántica es pagar una llamada por una opinión sobre código muerto. Y los hallazgos
        deterministas ya dicen qué línea es y por qué.
        """
        if self._auditor_llm is None or audit.risk_level == RiskLevel.CRITICAL:
            return None

        peticion = (
            f"PETICIÓN DEL USUARIO:\n{prompt_nl}\n\n"
            f"SCRIPT PROPUESTO:\n```python\n{code}\n```"
        )
        respuesta = await self._auditor_llm.ainvoke([
            {"role": "system", "content": _AUDITOR_SYSTEM_PROMPT},
            {"role": "user", "content": peticion},
        ])
        texto = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
        return _leer_veredicto(texto, self._auditor_model_name)
