"""AdminScriptExtractionPipeline — ejecución de scripts aprobados vía SandboxClient (SBX.3).

El aislamiento subprocess se delega al SandboxClient (HttpSandboxClient en producción,
LocalSandboxClient en tests). La auditoría AST defensiva se mantiene en la API:
defensa en profundidad — aunque el sandbox también audita.

Protocolo del script de usuario:
  - Variables disponibles: file_path (str), raw_text (str), options (dict)
  - El script debe asignar la variable `result` (dict) con las claves:
      tables   : list[dict]  → cada dict: name, headers, rows, source_page
      metrics  : list[dict]  → cada dict: name, value, unit (opcional)
      free_text: str | None
"""
from __future__ import annotations

from datetime import datetime, timezone

from server.app.core.sandbox_client import LocalSandboxClient, SandboxClient
from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
)
from server.app.modules.redaccion.services.script_auditor import ScriptSecurityAuditor

_AUDITOR = ScriptSecurityAuditor()
_DEFAULT_TIMEOUT_SECONDS = 30


class AdminScriptExtractionPipeline:
    """Ejecuta scripts de extracción aprobados vía SandboxClient."""

    pipeline_id = "admin_script_pipeline_v1"

    def __init__(self, client: SandboxClient | None = None) -> None:
        self._client: SandboxClient = client or LocalSandboxClient()

    def supports(self, source_kind: str) -> bool:
        return source_kind == "admin_script"

    async def extract_async(self, inp: ExtractionInput) -> ExtractionResult:
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

        # Defensa en profundidad: re-auditar antes de enviar al sandbox.
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

        file_path: str | None = None
        if inp.file_ref:
            import os
            from pathlib import Path
            file_path = str(Path(inp.file_ref.bucket) / inp.file_ref.key)

        return await self._client.execute_extraction_script(
            code=code,
            file_path=file_path,
            raw_text=inp.raw_text,
            options=inp.options,
            timeout_seconds=timeout,
        )

    def _provenance(self) -> ExtractionProvenance:
        return ExtractionProvenance(
            pipeline_id=self.pipeline_id,
            source_ref="admin_script",
            extracted_at=datetime.now(timezone.utc),
        )
