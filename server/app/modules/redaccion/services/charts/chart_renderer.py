"""ChartRenderer — renderiza scripts matplotlib vía SandboxClient (SBX.3).

La auditoría AST defensiva se mantiene en la API antes de enviar al sandbox.
El aislamiento subprocess se delega al SandboxClient.
"""
from __future__ import annotations

import io

import pandas as pd

from server.app.core.sandbox_client import LocalSandboxClient, SandboxClient
from server.app.modules.redaccion.services.script_auditor import ScriptSecurityAuditor


class ChartRenderError(Exception):
    pass


_AUDITOR = ScriptSecurityAuditor()


async def render_chart_from_script(
    code: str,
    df: pd.DataFrame,
    output_format: str = "png",
    timeout: int = 30,
    sandbox_client: SandboxClient | None = None,
) -> bytes:
    """Audita y ejecuta *code* vía SandboxClient; devuelve bytes de la imagen.

    Raises:
        ChartRenderError: si la auditoría falla o el sandbox devuelve error.
    """
    audit = _AUDITOR.audit(code)
    if not audit.approved:
        raise ChartRenderError(
            "Auditoría de seguridad rechazó el script: "
            + "; ".join(f.message for f in audit.findings)
        )

    client: SandboxClient = sandbox_client or LocalSandboxClient()
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)

    return await client.execute_chart_script(
        code=code,
        dataframe_csv=csv_buf.getvalue(),
        output_format=output_format,  # type: ignore[arg-type]
        timeout_seconds=timeout,
    )
