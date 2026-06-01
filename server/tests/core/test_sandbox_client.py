"""Tests del SandboxClient (HttpSandboxClient, LocalSandboxClient, get_sandbox_client).

Usa respx para mockear httpx.AsyncClient sin levantar el contenedor Docker.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest
import respx

from server.app.modules.redaccion.pipelines.contracts import ExtractionResult
from server.app.modules.redaccion.services.charts.chart_renderer import ChartRenderError
from server.app.core.sandbox_client import (
    HttpSandboxClient,
    LocalSandboxClient,
    SandboxUnavailableError,
    get_sandbox_client,
)

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

_BASE = "http://script-sandbox:5000"

_EXTRACTION_200 = {
    "result": {
        "tables": [{"name": "t1", "headers": ["a", "b"], "rows": [["1", "2"]]}],
        "metrics": [{"name": "total", "value": 99}],
        "free_text": None,
    },
    "stdout_truncated": False,
}

_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8  # magic + padding

_CSV_TEXT = "a,b\n1,2\n3,4\n"

_SIMPLE_CODE = "result = {'metrics': [{'name': 'x', 'value': 1}]}\n"


@pytest.fixture
def http_client() -> HttpSandboxClient:
    return HttpSandboxClient(base_url=_BASE, connect_timeout=5.0, max_retries=1, default_timeout=30)


# --------------------------------------------------------------------------
# HttpSandboxClient — execute_extraction_script
# --------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_extraction_serializes_and_parses_response(http_client):
    respx.post(f"{_BASE}/execute-extraction").mock(
        return_value=httpx.Response(200, json=_EXTRACTION_200)
    )
    result = await http_client.execute_extraction_script(
        code="result = {}", file_path=None, raw_text=None, options={}
    )
    assert isinstance(result, ExtractionResult)
    assert result.tables[0].name == "t1"
    assert result.metrics[0].name == "total"
    assert result.metrics[0].value == 99


@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_extraction_returns_warning_when_sandbox_returns_422_audit(http_client):
    respx.post(f"{_BASE}/execute-extraction").mock(
        return_value=httpx.Response(
            422,
            json={"code": "SCRIPT_AUDIT_FAILED", "findings": ["CRITICO: llamada peligrosa 'eval()'"]},
        )
    )
    result = await http_client.execute_extraction_script(
        code="eval('1+1')", file_path=None, raw_text=None, options={}
    )
    assert isinstance(result, ExtractionResult)
    assert len(result.warnings) == 1
    assert result.warnings[0].code == "SCRIPT_SECURITY_VIOLATION"
    assert "eval" in result.warnings[0].message


@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_extraction_returns_warning_when_sandbox_returns_504(http_client):
    respx.post(f"{_BASE}/execute-extraction").mock(
        return_value=httpx.Response(504, json={"code": "SCRIPT_TIMEOUT"})
    )
    result = await http_client.execute_extraction_script(
        code="while True: pass", file_path=None, raw_text=None, options={}, timeout_seconds=1
    )
    assert isinstance(result, ExtractionResult)
    assert len(result.warnings) == 1
    assert result.warnings[0].code == "SCRIPT_TIMEOUT"


@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_extraction_returns_warning_when_sandbox_returns_500(http_client):
    respx.post(f"{_BASE}/execute-extraction").mock(
        return_value=httpx.Response(
            500,
            json={"code": "SCRIPT_EXECUTION_ERROR", "stderr_truncated": "RuntimeError: boom"},
        )
    )
    result = await http_client.execute_extraction_script(
        code="raise RuntimeError('boom')", file_path=None, raw_text=None, options={}
    )
    assert isinstance(result, ExtractionResult)
    assert len(result.warnings) == 1
    assert result.warnings[0].code == "SCRIPT_EXECUTION_ERROR"
    assert "boom" in result.warnings[0].message


@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_extraction_raises_SandboxUnavailableError_on_connect_error(http_client):
    # max_retries=1 → 2 intentos totales, ambos fallan
    respx.post(f"{_BASE}/execute-extraction").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(SandboxUnavailableError):
        await http_client.execute_extraction_script(
            code="result = {}", file_path=None, raw_text=None, options={}
        )


@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_extraction_retries_once_on_connect_error(http_client):
    call_count = 0

    def _side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("first attempt failed")
        return httpx.Response(200, json=_EXTRACTION_200)

    respx.post(f"{_BASE}/execute-extraction").mock(side_effect=_side_effect)

    result = await http_client.execute_extraction_script(
        code="result = {}", file_path=None, raw_text=None, options={}
    )
    assert call_count == 2
    assert isinstance(result, ExtractionResult)


# --------------------------------------------------------------------------
# HttpSandboxClient — execute_chart_script
# --------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_chart_returns_bytes(http_client):
    respx.post(f"{_BASE}/execute-chart").mock(
        return_value=httpx.Response(200, content=_PNG_BYTES, headers={"content-type": "image/png"})
    )
    data = await http_client.execute_chart_script(
        code="plt.figure()", dataframe_csv="x,y\n1,2\n"
    )
    assert isinstance(data, bytes)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_chart_raises_ChartRenderError_on_422(http_client):
    respx.post(f"{_BASE}/execute-chart").mock(
        return_value=httpx.Response(
            422,
            json={"code": "SCRIPT_AUDIT_FAILED", "findings": ["ADVERTENCIA: módulo 'subprocess'"]},
        )
    )
    with pytest.raises(ChartRenderError):
        await http_client.execute_chart_script(
            code="import subprocess", dataframe_csv="x,y\n1,2\n"
        )


# --------------------------------------------------------------------------
# HttpSandboxClient — execute_etl_script
# --------------------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_http_client_execute_etl_returns_csv_string(http_client):
    respx.post(f"{_BASE}/execute-etl").mock(
        return_value=httpx.Response(200, content=_CSV_TEXT.encode(), headers={"content-type": "text/csv"})
    )
    csv_out = await http_client.execute_etl_script(
        code="def transform(df): return df", dataframe_csv=_CSV_TEXT
    )
    assert isinstance(csv_out, str)
    assert "a,b" in csv_out


# --------------------------------------------------------------------------
# LocalSandboxClient — execute_extraction_script
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_client_execute_extraction_matches_http_client_behavior():
    """LocalSandboxClient y HttpSandboxClient producen ExtractionResult equivalente."""
    local = LocalSandboxClient()

    # LocalSandboxClient: resultado real vía subprocess
    local_result = await local.execute_extraction_script(
        code=_SIMPLE_CODE,
        file_path=None,
        raw_text=None,
        options={},
    )
    assert isinstance(local_result, ExtractionResult)
    assert len(local_result.metrics) == 1
    assert local_result.metrics[0].name == "x"
    assert local_result.metrics[0].value == 1

    # HttpSandboxClient mocked: mismo código → mismo resultado
    with respx.mock:
        respx.post(f"{_BASE}/execute-extraction").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": {
                        "tables": [],
                        "metrics": [{"name": "x", "value": 1}],
                        "free_text": None,
                    },
                    "stdout_truncated": False,
                },
            )
        )
        http = HttpSandboxClient(base_url=_BASE, connect_timeout=5.0, max_retries=0, default_timeout=30)
        http_result = await http.execute_extraction_script(
            code=_SIMPLE_CODE,
            file_path=None,
            raw_text=None,
            options={},
        )

    assert isinstance(http_result, ExtractionResult)
    assert http_result.metrics[0].name == local_result.metrics[0].name
    assert http_result.metrics[0].value == local_result.metrics[0].value


# --------------------------------------------------------------------------
# get_sandbox_client factory
# --------------------------------------------------------------------------

def test_get_sandbox_client_returns_http_in_production():
    with patch.dict(os.environ, {"SANDBOX_MODE": "http"}, clear=False):
        # Asegurar que TESTING no activa el modo local
        os.environ.pop("TESTING", None)
        client = get_sandbox_client()
    assert isinstance(client, HttpSandboxClient)


def test_get_sandbox_client_returns_local_when_testing_env_set():
    with patch.dict(os.environ, {"TESTING": "1"}, clear=False):
        client = get_sandbox_client()
    assert isinstance(client, LocalSandboxClient)
