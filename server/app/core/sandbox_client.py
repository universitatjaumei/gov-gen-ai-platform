"""SandboxClient — cliente HTTP que habla con el microservicio script-sandbox (SBX.1/SBX.2).

Capa de infraestructura compartida (Deploy: shared), análoga a StorageService.
Los módulos edge que ejecutan scripts de usuario lo usan como dependencia inyectada.

Dos implementaciones:
- HttpSandboxClient: producción y CI con Docker Compose.
- LocalSandboxClient: desarrollo y tests sin Docker (subprocess inline).

La factoría `get_sandbox_client()` selecciona la implementación según
`SANDBOX_MODE` y la variable `TESTING=1`.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx

from server.app.core.config import get_settings
from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
    ExtractedMetric,
    ExtractedTable,
)


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class SandboxUnavailableError(Exception):
    """El microservicio script-sandbox no responde tras los reintentos configurados."""


# ---------------------------------------------------------------------------
# Protocol — contrato que ambas implementaciones satisfacen
# ---------------------------------------------------------------------------

class SandboxClient(Protocol):
    async def execute_extraction_script(
        self,
        *,
        code: str,
        file_path: str | None,
        raw_text: str | None,
        options: dict[str, Any],
        timeout_seconds: int | None = None,
        file_bytes: bytes | None = None,
        file_name: str = "",
    ) -> ExtractionResult:
        """Ejecuta un script de extracción y devuelve ExtractionResult.

        `file_bytes` es el **contenido** del fichero (PRO.2): `file_path` sólo servía cuando
        el sandbox compartía sistema de archivos con la API, que no es el caso ni en Docker
        ni con `StorageService` sobre GCS. Con contenido, el sandbox lo materializa en su
        propio temporal y le pasa esa ruta al script.

        Errores del sandbox → ExtractionResult con warnings (nunca lanza excepciones).
        Error de red (ConnectError tras reintentos) → SandboxUnavailableError.
        """
        ...

    async def execute_chart_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        output_format: Literal["png", "svg"] = "png",
        timeout_seconds: int | None = None,
    ) -> bytes:
        """Ejecuta un script matplotlib y devuelve bytes de la imagen.

        Cualquier error del sandbox → ChartRenderError.
        """
        ...

    async def execute_etl_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        timeout_seconds: int | None = None,
    ) -> str:
        """Ejecuta un script ETL y devuelve el CSV transformado como string.

        Cualquier error del sandbox → ValueError con mensaje descriptivo.
        """
        ...


# ---------------------------------------------------------------------------
# Helpers de parseo compartidos
# ---------------------------------------------------------------------------

def _make_provenance(pipeline_id: str) -> ExtractionProvenance:
    return ExtractionProvenance(
        pipeline_id=pipeline_id,
        source_ref="sandbox",
        extracted_at=datetime.now(timezone.utc),
    )


def _parse_extraction_json(data: dict, pipeline_id: str) -> ExtractionResult:
    """Convierte el JSON devuelto por /execute-extraction (200) en ExtractionResult."""
    payload = data.get("result", data)
    tables = [
        ExtractedTable(
            name=t.get("name", f"table_{i}"),
            headers=t.get("headers", []),
            rows=t.get("rows", []),
            source_page=t.get("source_page"),
        )
        for i, t in enumerate(payload.get("tables", []))
    ]
    metrics = [
        ExtractedMetric(
            name=m.get("name", f"metric_{i}"),
            value=m.get("value", 0),
            unit=m.get("unit"),
        )
        for i, m in enumerate(payload.get("metrics", []))
    ]
    return ExtractionResult(
        tables=tables,
        metrics=metrics,
        free_text=payload.get("free_text"),
        provenance=_make_provenance(pipeline_id),
    )


def _extraction_with_warning(code: str, message: str, pipeline_id: str) -> ExtractionResult:
    return ExtractionResult(
        warnings=[ExtractionWarning(code=code, message=message, severity="error")],
        provenance=_make_provenance(pipeline_id),
    )


# ---------------------------------------------------------------------------
# HttpSandboxClient
# ---------------------------------------------------------------------------

class HttpSandboxClient:
    """Cliente HTTP async que habla con el microservicio script-sandbox.

    Reintenta solo en httpx.ConnectError (error de red, no error funcional del script).
    """

    def __init__(
        self,
        base_url: str | None = None,
        connect_timeout: float | None = None,
        max_retries: int | None = None,
        default_timeout: int | None = None,
    ) -> None:
        s = get_settings()
        self._base_url = base_url if base_url is not None else s.sandbox_base_url
        self._connect_timeout = connect_timeout if connect_timeout is not None else s.sandbox_connect_timeout_seconds
        self._max_retries = max_retries if max_retries is not None else s.sandbox_max_retries_on_connect_error
        self._default_timeout = default_timeout if default_timeout is not None else s.sandbox_timeout_seconds_default

    _PIPELINE_ID = "http_sandbox_client"

    async def execute_extraction_script(
        self,
        *,
        code: str,
        file_path: str | None,
        raw_text: str | None,
        options: dict[str, Any],
        timeout_seconds: int | None = None,
        file_bytes: bytes | None = None,
        file_name: str = "",
    ) -> ExtractionResult:
        t = timeout_seconds or self._default_timeout
        payload = {
            "code": code,
            "file_path": file_path or "",
            "raw_text": raw_text or "",
            "options": options,
            "timeout_seconds": t,
            "file_bytes_b64": (
                base64.b64encode(file_bytes).decode("ascii") if file_bytes else ""
            ),
            "file_name": file_name,
        }
        resp = await self._post_with_retry("/execute-extraction", payload, script_timeout=t)

        if resp.status_code == 200:
            return _parse_extraction_json(resp.json(), self._PIPELINE_ID)

        body = resp.json()
        error_code: str = body.get("code", "UNKNOWN")

        if resp.status_code == 422 and error_code == "SCRIPT_AUDIT_FAILED":
            findings = body.get("findings", [])
            msg = "; ".join(findings)[:500]
            return _extraction_with_warning("SCRIPT_SECURITY_VIOLATION", msg, self._PIPELINE_ID)

        if resp.status_code == 422:
            return _extraction_with_warning(error_code, body.get("message", ""), self._PIPELINE_ID)

        if resp.status_code == 504:
            return _extraction_with_warning(
                "SCRIPT_TIMEOUT",
                f"El script excedió el tiempo límite de {t}s.",
                self._PIPELINE_ID,
            )

        # 500 SCRIPT_EXECUTION_ERROR
        return _extraction_with_warning(
            "SCRIPT_EXECUTION_ERROR",
            body.get("stderr_truncated", resp.text[:500]),
            self._PIPELINE_ID,
        )

    async def execute_chart_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        output_format: Literal["png", "svg"] = "png",
        timeout_seconds: int | None = None,
    ) -> bytes:
        t = timeout_seconds or self._default_timeout
        payload = {
            "code": code,
            "data_csv": dataframe_csv,
            "output_format": output_format,
            "timeout_seconds": t,
        }
        resp = await self._post_with_retry("/execute-chart", payload, script_timeout=t)

        if resp.status_code == 200:
            return resp.content

        body_text = resp.text[:300]
        from server.app.modules.redaccion.services.charts.chart_renderer import ChartRenderError
        raise ChartRenderError(f"Sandbox error {resp.status_code}: {body_text}")

    async def execute_etl_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        timeout_seconds: int | None = None,
    ) -> str:
        t = timeout_seconds or self._default_timeout
        payload = {
            "code": code,
            "data_csv": dataframe_csv,
            "timeout_seconds": t,
        }
        resp = await self._post_with_retry("/execute-etl", payload, script_timeout=t)

        if resp.status_code == 200:
            return resp.text

        raise ValueError(f"Sandbox ETL error {resp.status_code}: {resp.text[:300]}")

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    async def _post_with_retry(
        self, path: str, payload: dict, script_timeout: int
    ) -> httpx.Response:
        """POST con reintento en ConnectError. La read timeout excede el timeout del script."""
        read_timeout = max(script_timeout + 30, 60)
        # httpx.Timeout(default, connect=x) sets default for read/write/pool and overrides connect.
        timeout = httpx.Timeout(read_timeout, connect=self._connect_timeout)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(base_url=self._base_url, timeout=timeout) as client:
                    return await client.post(path, json=payload)
            except httpx.ConnectError as exc:
                last_exc = exc
                if attempt >= self._max_retries:
                    raise SandboxUnavailableError(
                        f"No se puede conectar al sandbox '{self._base_url}' "
                        f"tras {attempt + 1} intento(s): {exc}"
                    ) from exc

        raise SandboxUnavailableError("Max retries exceeded") from last_exc


# ---------------------------------------------------------------------------
# LocalSandboxClient — SOLO para tests y desarrollo sin Docker
# ---------------------------------------------------------------------------

class LocalSandboxClient:
    """Ejecuta scripts de usuario en un subproceso local, sin contenedor Docker.

    ADVERTENCIA: este cliente es SOLO para tests y desarrollo local.
    No proporciona aislamiento de red ni de sistema de archivos.
    En producción siempre se usa HttpSandboxClient.
    """

    _PIPELINE_ID = "local_sandbox_client"

    async def execute_extraction_script(
        self,
        *,
        code: str,
        file_path: str | None,
        raw_text: str | None,
        options: dict[str, Any],
        timeout_seconds: int | None = None,
        file_bytes: bytes | None = None,
        file_name: str = "",
    ) -> ExtractionResult:
        if not code or not code.strip():
            return _extraction_with_warning(
                "SCRIPT_EMPTY", "El código de script está vacío.", self._PIPELINE_ID
            )

        timeout = timeout_seconds or 30

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mismo contrato que el sandbox HTTP: con contenido, el fichero se materializa
            # y el script recibe esa ruta.
            ruta = file_path or ""
            if file_bytes is not None:
                destino = Path(tmpdir) / (Path(file_name or "entrada.bin").name or "entrada.bin")
                destino.write_bytes(file_bytes)
                ruta = str(destino)

            wrapper = _build_local_extraction_wrapper(code, ruta, raw_text or "", options)

            try:
                sub = await asyncio.to_thread(_run_sync, wrapper, timeout)
            except TimeoutError:
                return _extraction_with_warning(
                    "SCRIPT_TIMEOUT", f"Timeout tras {timeout}s.", self._PIPELINE_ID
                )

            return _resultado_local(sub, self._PIPELINE_ID)

    async def execute_chart_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        output_format: Literal["png", "svg"] = "png",
        timeout_seconds: int | None = None,
    ) -> bytes:
        timeout = timeout_seconds or 30

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "data.csv"
            out_path = Path(tmpdir) / f"chart.{output_format}"
            script_path = Path(tmpdir) / "run.py"

            csv_path.write_text(dataframe_csv, encoding="utf-8")
            wrapper = (
                "import pandas as pd\n"
                'import matplotlib; matplotlib.use("Agg")\n'
                "import matplotlib.pyplot as plt\n"
                "import seaborn as sns, numpy as np, io, math, re\n"
                f"df = pd.read_csv({str(csv_path)!r})\n"
                f"{code}\n"
                f"plt.savefig({str(out_path)!r}, format={output_format!r},"
                f' dpi=150, bbox_inches="tight", facecolor="white")\n'
                "plt.close('all')\n"
            )
            script_path.write_text(wrapper, encoding="utf-8")

            sub = await asyncio.to_thread(_run_sync, None, timeout, script_path=str(script_path))
            if sub["returncode"] != 0:
                from server.app.modules.redaccion.services.charts.chart_renderer import ChartRenderError
                raise ChartRenderError(f"LocalSandboxClient chart error: {sub['stderr'][:300]}")
            if not out_path.exists():
                from server.app.modules.redaccion.services.charts.chart_renderer import ChartRenderError
                raise ChartRenderError("LocalSandboxClient: el script no generó imagen.")
            return out_path.read_bytes()

    async def execute_etl_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        timeout_seconds: int | None = None,
    ) -> str:
        timeout = timeout_seconds or 30

        with tempfile.TemporaryDirectory() as tmpdir:
            in_csv = Path(tmpdir) / "in.csv"
            out_csv = Path(tmpdir) / "out.csv"
            script_path = Path(tmpdir) / "run.py"

            in_csv.write_text(dataframe_csv, encoding="utf-8")
            wrapper = f"""\
import sys
import pandas as pd
df = pd.read_csv({str(in_csv)!r})
{code}
_t = globals().get("transform")
if not callable(_t):
    print("ETL_TRANSFORM_UNDEFINED", file=sys.stderr)
    sys.exit(7)
_t(df.copy()).to_csv({str(out_csv)!r}, index=False)
"""
            script_path.write_text(wrapper, encoding="utf-8")

            sub = await asyncio.to_thread(_run_sync, None, timeout, script_path=str(script_path))
            if sub["returncode"] == 7:
                raise ValueError("ETL script must define a transform(df) function")
            if sub["returncode"] != 0:
                raise ValueError(f"LocalSandboxClient ETL error: {sub['stderr'][:300]}")
            if not out_csv.exists():
                raise ValueError("LocalSandboxClient: el script no generó CSV.")
            return out_csv.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers locales de subprocess
# ---------------------------------------------------------------------------

def _resultado_local(sub: dict, pipeline_id: str) -> ExtractionResult:
    if sub["returncode"] != 0:
        return _extraction_with_warning(
            "SCRIPT_EXECUTION_ERROR", sub["stderr"][:500], pipeline_id
        )

    try:
        data = json.loads(sub["stdout"])
    except (json.JSONDecodeError, ValueError):
        data = {}

    return _parse_extraction_json({"result": data}, pipeline_id)


def _build_local_extraction_wrapper(
    code: str, file_path: str, raw_text: str, options: dict
) -> str:
    return f"""\
import sys, json, math, re, datetime, collections, typing, io
try:
    import pandas
except ImportError:
    pandas = None
file_path = {file_path!r}
raw_text = {raw_text!r}
options = {options!r}
# --- script de usuario ---
{code}
# --- fin script de usuario ---
_r = globals().get("result", {{}})
print(json.dumps(_r, default=str))
"""


#: Lo único que un intérprete necesita para arrancar. Todo lo demás —secretos incluidos— se
#: queda fuera del subproceso (SEC.9.6).
_VARIABLES_QUE_PASAN = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "LANG", "LC_ALL", "PYTHONIOENCODING")


def _entorno_minimo() -> dict[str, str]:
    """El entorno del subproceso, construido por lista blanca y no por herencia.

    Por lista blanca a propósito: una lista negra («quita `JWT_SECRET_KEY`, `DATABASE_URL`…»)
    hay que ampliarla cada vez que aparece un secreto nuevo, y nadie se acuerda. Con lista
    blanca, el secreto que se añada mañana ya no viaja.
    """
    entorno = {
        nombre: os.environ[nombre]
        for nombre in _VARIABLES_QUE_PASAN
        if nombre in os.environ
    }
    entorno.setdefault("PYTHONIOENCODING", "utf-8")

    # Un «hogar» de usar y tirar. Varias librerías escriben caché en el perfil del usuario
    # —matplotlib es la que lo destapó: sin sitio donde escribir su configuración, ni se
    # importa—. Apuntarlas al temporal las deja funcionar **y** es mejor aislamiento que
    # heredar `USERPROFILE`, que le daría al script el escritorio de quien ejecuta el servidor.
    temporal = tempfile.gettempdir()
    for variable in ("MPLCONFIGDIR", "HOME", "USERPROFILE", "XDG_CACHE_HOME"):
        entorno.setdefault(variable, temporal)
    return entorno


def _run_sync(
    wrapper_code: str | None,
    timeout: int,
    *,
    script_path: str | None = None,
) -> dict[str, Any]:
    """Ejecuta un wrapper en un subproceso síncrono. Devuelve {returncode, stdout, stderr}."""
    tmp_path: str | None = None

    try:
        if script_path:
            run_path = script_path
        else:
            fd, tmp_path = tempfile.mkstemp(suffix=".py", text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(wrapper_code or "")
            run_path = tmp_path

        proc = subprocess.Popen(
            [sys.executable, run_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            # SEC.9.6 — sin `env=`, el subproceso hereda `os.environ` entero: `JWT_SECRET_KEY`,
            # `DATABASE_URL` y `AUTOMATIA_SIGNING_KEY` quedaban al alcance de un script
            # generado por un modelo. El ejecutor local es de desarrollo, así que esto no
            # sustituye al aislamiento del servicio `script-sandbox`; lo que hace es que el
            # modo de desarrollo no reparta los secretos del desarrollador.
            env=_entorno_minimo(),
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            raise TimeoutError(f"Script exceeded {timeout}s")

        return {
            "returncode": proc.returncode if proc.returncode is not None else -1,
            "stdout": stdout or "",
            "stderr": stderr or "",
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_sandbox_client() -> SandboxClient:
    """Factory para FastAPI `Depends`. Selecciona implementación según entorno."""
    s = get_settings()
    if s.sandbox_mode == "local" or os.getenv("TESTING") == "1":
        return LocalSandboxClient()
    return HttpSandboxClient(
        base_url=s.sandbox_base_url,
        connect_timeout=s.sandbox_connect_timeout_seconds,
        max_retries=s.sandbox_max_retries_on_connect_error,
        default_timeout=s.sandbox_timeout_seconds_default,
    )
