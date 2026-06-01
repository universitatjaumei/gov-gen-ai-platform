"""Tests SBX.3 — verifican que cada pipeline usa SandboxClient inyectado.

No levanta subprocess real; usa stubs inline para máxima velocidad.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import pandas as pd
import pytest

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
)


def _provenance() -> ExtractionProvenance:
    return ExtractionProvenance(
        pipeline_id="test_stub",
        source_ref="test",
        extracted_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# AdminScriptExtractionPipeline
# ---------------------------------------------------------------------------

async def test_admin_script_pipeline_uses_sandbox_client_and_propagates_warnings() -> None:
    """Cuando el SandboxClient devuelve SCRIPT_TIMEOUT, el pipeline lo propaga sin modificar."""
    from server.app.modules.redaccion.pipelines.admin_script_pipeline import (
        AdminScriptExtractionPipeline,
    )

    expected = ExtractionResult(
        warnings=[
            ExtractionWarning(
                code="SCRIPT_TIMEOUT",
                message="El script excedió el tiempo límite de 30s.",
                severity="error",
            )
        ],
        provenance=_provenance(),
    )

    class _StubClient:
        async def execute_extraction_script(
            self, *, code: str, file_path: Any, raw_text: Any, options: Any, timeout_seconds: Any = None
        ) -> ExtractionResult:
            return expected

    pipeline = AdminScriptExtractionPipeline(client=_StubClient())
    inp = ExtractionInput(
        source_kind="admin_script",
        raw_text="",
        options={"approved": True, "code": "result = {}"},
    )
    result = await pipeline.extract_async(inp)

    assert result is expected
    assert result.warnings[0].code == "SCRIPT_TIMEOUT"


async def test_admin_script_pipeline_re_audits_before_calling_client() -> None:
    """Un script con eval() no debe llegar nunca al SandboxClient."""
    from server.app.modules.redaccion.pipelines.admin_script_pipeline import (
        AdminScriptExtractionPipeline,
    )

    called = False

    class _StubClient:
        async def execute_extraction_script(self, **kwargs: Any) -> ExtractionResult:
            nonlocal called
            called = True
            raise AssertionError("Sandbox must NOT be called for unsafe code")

    pipeline = AdminScriptExtractionPipeline(client=_StubClient())
    inp = ExtractionInput(
        source_kind="admin_script",
        raw_text="",
        options={"approved": True, "code": "import os\nos.system('echo hack')"},
    )
    result = await pipeline.extract_async(inp)

    assert not called, "Sandbox client was called despite re-audit failure"
    warning_codes = [w.code for w in result.warnings]
    assert "SCRIPT_SECURITY_VIOLATION" in warning_codes


# ---------------------------------------------------------------------------
# render_chart_from_script
# ---------------------------------------------------------------------------

async def test_chart_renderer_uses_sandbox_client_and_returns_bytes() -> None:
    """render_chart_from_script delega la ejecución al SandboxClient inyectado."""
    from server.app.modules.redaccion.services.charts.chart_renderer import render_chart_from_script

    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

    class _StubClient:
        async def execute_chart_script(
            self,
            *,
            code: str,
            dataframe_csv: str,
            output_format: Literal["png", "svg"] = "png",
            timeout_seconds: Any = None,
        ) -> bytes:
            return fake_png

    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    result = await render_chart_from_script(
        "fig, ax = plt.subplots()\nax.plot(df['x'], df['y'])",
        df,
        sandbox_client=_StubClient(),
    )
    assert result == fake_png


# ---------------------------------------------------------------------------
# ETLService fallback
# ---------------------------------------------------------------------------

async def test_etl_service_fallback_uses_sandbox_client() -> None:
    """ETLService._execute_fallback_script delega al SandboxClient inyectado."""
    from server.app.modules.redaccion.services.transformation.etl_service import ETLService

    returned_csv = "col_a,col_b\n10,20\n30,40\n"

    class _StubClient:
        async def execute_etl_script(
            self, *, code: str, dataframe_csv: str, timeout_seconds: Any = None
        ) -> str:
            return returned_csv

    svc = ETLService(sandbox_client=_StubClient())
    df = pd.DataFrame({"col_a": [1], "col_b": [2]})
    result = await svc._execute_fallback_script("def transform(df): return df", df)

    assert list(result.columns) == ["col_a", "col_b"]
    assert len(result) == 2
    assert result.iloc[0]["col_a"] == 10


# ---------------------------------------------------------------------------
# scripts_router wiring
# ---------------------------------------------------------------------------

async def test_scripts_router_test_proposal_uses_async_pipeline() -> None:
    """Smoke: test_proposal acepta sandbox como dependencia inyectable."""
    import inspect

    from fastapi import FastAPI

    from server.app.core.sandbox_client import LocalSandboxClient, get_sandbox_client
    from server.app.routers.redaccion.scripts_router import router, test_proposal

    # Verify endpoint signature declares sandbox
    sig = inspect.signature(test_proposal)
    assert "sandbox" in sig.parameters, "test_proposal debe tener parámetro 'sandbox'"

    # Verify dependency can be overridden via app.dependency_overrides
    app = FastAPI()
    app.include_router(router)
    local = LocalSandboxClient()
    app.dependency_overrides[get_sandbox_client] = lambda: local

    assert get_sandbox_client in app.dependency_overrides
    assert app.dependency_overrides[get_sandbox_client]() is local
