"""AdminScriptExtractionPipeline — ejecución de scripts aprobados en sandbox (9R.5.4).

Solo ejecuta código que haya superado: auditoría AST + auditoría IA + aprobación HITL.
Como última defensa, re-audita antes de ejecutar. La ejecución usa subprocess
con tiempo límite para aislamiento y control de recursos.

Protocolo del script de usuario:
  - Variables disponibles: file_path (str), raw_text (str), options (dict)
  - El script debe asignar la variable `result` (dict) con las claves:
      tables   : list[dict]  → cada dict: name, headers, rows, source_page
      metrics  : list[dict]  → cada dict: name, value, unit (opcional)
      free_text: str | None
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
    ExtractedMetric,
    ExtractedTable,
)
from server.app.modules.redaccion.services.script_auditor import ScriptSecurityAuditor

_AUDITOR = ScriptSecurityAuditor()
_DEFAULT_TIMEOUT_SECONDS = 30


class AdminScriptExtractionPipeline:
    """Ejecuta scripts de extracción aprobados por admin/partner en sandbox restringido."""

    pipeline_id = "admin_script_pipeline_v1"

    def supports(self, source_kind: str) -> bool:
        return source_kind == "admin_script"

    def extract(self, inp: ExtractionInput) -> ExtractionResult:
        code: str = inp.options.get("code", "")
        approved: bool = inp.options.get("approved", False)
        timeout: int = int(inp.options.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS))

        if not approved:
            return ExtractionResult(
                warnings=[ExtractionWarning(
                    code="SCRIPT_NOT_APPROVED",
                    message="El script no ha sido aprobado mediante revisión HITL.",
                    severity="error",
                )],
                provenance=self._provenance(),
            )

        if not code.strip():
            return ExtractionResult(
                warnings=[ExtractionWarning(
                    code="SCRIPT_EMPTY",
                    message="No se proporcionó código de script.",
                    severity="error",
                )],
                provenance=self._provenance(),
            )

        # Última defensa: re-auditar antes de ejecutar
        audit = _AUDITOR.audit(code)
        if not audit.approved:
            summary = "; ".join(audit.findings[:3])
            return ExtractionResult(
                warnings=[ExtractionWarning(
                    code="SCRIPT_SECURITY_VIOLATION",
                    message=f"El script no supera la auditoría de seguridad: {summary}",
                    severity="error",
                )],
                provenance=self._provenance(),
            )

        return self._execute_in_sandbox(code, inp, timeout)

    # ------------------------------------------------------------------
    # Sandbox
    # ------------------------------------------------------------------

    def _execute_in_sandbox(
        self, code: str, inp: ExtractionInput, timeout: int
    ) -> ExtractionResult:
        file_path = (
            str(Path(inp.file_ref.bucket) / inp.file_ref.key)
            if inp.file_ref
            else ""
        )
        raw_text = inp.raw_text or ""

        wrapper = _build_wrapper(code, file_path, raw_text, inp.options)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(wrapper)
            tmp_path = f.name

        try:
            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if proc.returncode != 0:
                return ExtractionResult(
                    warnings=[ExtractionWarning(
                        code="SCRIPT_EXECUTION_ERROR",
                        message=(proc.stderr or "Error desconocido al ejecutar el script.")[:500],
                        severity="error",
                    )],
                    provenance=self._provenance(),
                )

            try:
                data: dict = json.loads(proc.stdout)
            except (json.JSONDecodeError, ValueError):
                data = {}

            return _dict_to_result(data, self._provenance())

        except subprocess.TimeoutExpired:
            return ExtractionResult(
                warnings=[ExtractionWarning(
                    code="SCRIPT_TIMEOUT",
                    message=f"El script excedió el tiempo límite de {timeout} segundos.",
                    severity="error",
                )],
                provenance=self._provenance(),
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _provenance(self) -> ExtractionProvenance:
        return ExtractionProvenance(
            pipeline_id=self.pipeline_id,
            source_ref="admin_script",
            extracted_at=datetime.now(timezone.utc),
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_wrapper(code: str, file_path: str, raw_text: str, options: dict) -> str:
    """Envuelve el código de usuario para capturar la variable `result` como JSON.

    Usa repr() para file_path, raw_text y options: produce literales Python válidos
    (True/False/None) en lugar de JSON (true/false/null).
    """
    return f"""\
import sys, json, math, re, datetime, collections, typing, io

try:
    import pandas
except ImportError:
    pandas = None

file_path = {repr(file_path)}
raw_text = {repr(raw_text)}
options = {repr(options)}

# --- script de usuario ---
{code}
# --- fin script de usuario ---

_r = globals().get("result", {{}})
print(json.dumps(_r, default=str))
"""


def _dict_to_result(data: dict, provenance: ExtractionProvenance) -> ExtractionResult:
    """Convierte el dict devuelto por el script en ExtractionResult."""
    tables = [
        ExtractedTable(
            name=t.get("name", f"table_{i}"),
            headers=t.get("headers", []),
            rows=t.get("rows", []),
            source_page=t.get("source_page"),
        )
        for i, t in enumerate(data.get("tables", []))
    ]
    metrics = [
        ExtractedMetric(
            name=m.get("name", f"metric_{i}"),
            value=m.get("value", 0),
            unit=m.get("unit"),
        )
        for i, m in enumerate(data.get("metrics", []))
    ]
    return ExtractionResult(
        tables=tables,
        metrics=metrics,
        free_text=data.get("free_text"),
        provenance=provenance,
    )
