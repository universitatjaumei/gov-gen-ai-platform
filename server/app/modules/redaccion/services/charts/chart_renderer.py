"""ChartRenderer — renderiza scripts matplotlib en un subproceso aislado (9R.5.7).

Patrón análogo al sandbox de AdminScriptExtractionPipeline (9R.5.4):
  1. Audita el AST antes de ejecutar.
  2. Escribe df a CSV en /tmp.
  3. Construye un script wrapper que carga df, inyecta el código del usuario y llama plt.savefig.
  4. Ejecuta en un subproceso con timeout.
  5. Lee los bytes del fichero de salida.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pandas as pd

from server.app.modules.redaccion.services.script_auditor import ScriptSecurityAuditor


class ChartRenderError(Exception):
    pass


_AUDITOR = ScriptSecurityAuditor()

_WRAPPER_TEMPLATE = textwrap.dedent("""\
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    import io, math, re

    df = pd.read_csv({csv_path!r})

    # --- user code ---
    {user_code}
    # --- end user code ---

    plt.savefig({output_path!r}, format={output_format!r}, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close("all")
""")


def render_chart_from_script(
    code: str,
    df: pd.DataFrame,
    output_format: str = "png",
    timeout: int = 30,
) -> bytes:
    """Audita y ejecuta *code* en un subproceso; devuelve bytes de la imagen.

    Raises:
        ChartRenderError: si la auditoría falla, el subproceso termina con error
                          o agota el timeout.
    """
    audit = _AUDITOR.audit(code)
    if not audit.approved:
        raise ChartRenderError(
            f"Auditoría de seguridad rechazó el script: {audit.findings}"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = str(Path(tmpdir) / "data.csv")
        out_path = str(Path(tmpdir) / f"chart.{output_format}")
        script_path = str(Path(tmpdir) / "run.py")

        df.to_csv(csv_path, index=False)

        wrapper = _WRAPPER_TEMPLATE.format(
            csv_path=csv_path,
            user_code=code,
            output_path=out_path,
            output_format=output_format,
        )
        Path(script_path).write_text(wrapper, encoding="utf-8")

        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise ChartRenderError(f"El script superó el timeout de {timeout}s")

        if result.returncode != 0:
            raise ChartRenderError(
                f"El script falló (rc={result.returncode}): {result.stderr[:500]}"
            )

        out_file = Path(out_path)
        if not out_file.exists():
            raise ChartRenderError("El script no generó ninguna imagen de salida")

        return out_file.read_bytes()
