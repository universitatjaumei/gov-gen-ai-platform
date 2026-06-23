"""Tests de scaffolding del servidor MCP (MCP.1).

Sin red real: respx intercepta httpx. Se prueba el cliente (auth + mapeo de
errores), la carga de configuración y el registro/lectura de los resources base.
"""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from api_client import ApiClient
from config import Config, ConfigError, load_config
from errors import ApiError, AuthError, ScopeError, ServerError, ValidationError
from resources import (
    GRAPH_PROFILES_URI,
    KNOWN_REPORT_PROFILES,
    PROFILES_URI,
    TEMPLATE_SCHEMA_PATH,
    TEMPLATE_SCHEMA_URI,
)
from server import build_server

BASE = "http://testserver"
PAT = "pat_abcd1234_secretsecretsecret"


def make_client() -> ApiClient:
    return ApiClient(BASE, PAT)


def make_config(graph_path) -> Config:
    return Config(api_base_url=BASE, pat=PAT, graph_profiles_path=graph_path)


# ---------------------------------------------------------------------------
# ApiClient: autenticación
# ---------------------------------------------------------------------------

@respx.mock
async def test_api_client_injects_bearer_header_on_every_request():
    route = respx.get(f"{BASE}/ping").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = make_client()
    try:
        result = await client.get("/ping")
    finally:
        await client.aclose()

    assert result == {"ok": True}
    assert route.called
    assert route.calls.last.request.headers["authorization"] == f"Bearer {PAT}"


# ---------------------------------------------------------------------------
# ApiClient: mapeo de errores
# ---------------------------------------------------------------------------

@respx.mock
async def test_maps_401_to_auth_error():
    respx.get(f"{BASE}/x").mock(
        return_value=httpx.Response(401, json={"detail": "token revoked"})
    )
    client = make_client()
    try:
        with pytest.raises(AuthError) as exc:
            await client.get("/x")
    finally:
        await client.aclose()
    assert exc.value.status_code == 401


@respx.mock
async def test_maps_403_to_scope_error():
    respx.post(f"{BASE}/y").mock(
        return_value=httpx.Response(403, json={"detail": "PAT_SCOPE_MISSING"})
    )
    client = make_client()
    try:
        with pytest.raises(ScopeError) as exc:
            await client.post("/y", json={})
    finally:
        await client.aclose()
    assert exc.value.status_code == 403
    assert exc.value.detail == {"detail": "PAT_SCOPE_MISSING"}


@respx.mock
async def test_maps_422_to_validation_error_with_body():
    body = {"detail": [{"loc": ["body", "name"], "msg": "field required"}]}
    respx.post(f"{BASE}/v").mock(return_value=httpx.Response(422, json=body))
    client = make_client()
    try:
        with pytest.raises(ValidationError) as exc:
            await client.post("/v", json={})
    finally:
        await client.aclose()
    assert exc.value.status_code == 422
    assert exc.value.detail == body


@respx.mock
async def test_maps_400_to_validation_error():
    # 400 Bad Request (reglas de negocio del servidor) → ValidationError, igual que 422.
    respx.patch(f"{BASE}/c").mock(
        return_value=httpx.Response(400, json={"detail": "límite 128K excedido"})
    )
    client = make_client()
    try:
        with pytest.raises(ValidationError) as exc:
            await client.patch("/c", json={})
    finally:
        await client.aclose()
    assert exc.value.status_code == 400


@respx.mock
async def test_maps_5xx_to_server_error():
    respx.get(f"{BASE}/boom").mock(return_value=httpx.Response(503, text="down"))
    client = make_client()
    try:
        with pytest.raises(ServerError) as exc:
            await client.get("/boom")
    finally:
        await client.aclose()
    assert exc.value.status_code == 503
    assert exc.value.detail == "down"


@respx.mock
async def test_other_4xx_maps_to_generic_api_error():
    respx.get(f"{BASE}/missing").mock(return_value=httpx.Response(404, json={"detail": "nope"}))
    client = make_client()
    try:
        with pytest.raises(ApiError) as exc:
            await client.get("/missing")
    finally:
        await client.aclose()
    assert exc.value.status_code == 404
    # No es ninguna de las subclases específicas.
    assert not isinstance(exc.value, (AuthError, ScopeError, ValidationError, ServerError))


@respx.mock
async def test_returns_none_on_204():
    respx.delete(f"{BASE}/z").mock(return_value=httpx.Response(204))
    client = make_client()
    try:
        assert await client.delete("/z") is None
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

def test_missing_pat_raises_config_error():
    with pytest.raises(ConfigError) as exc:
        load_config({"GOVGENAI_API_BASE_URL": BASE})
    assert "GOVGENAI_PAT" in str(exc.value)


def test_missing_both_lists_both_vars():
    with pytest.raises(ConfigError) as exc:
        load_config({})
    msg = str(exc.value)
    assert "GOVGENAI_API_BASE_URL" in msg
    assert "GOVGENAI_PAT" in msg


def test_load_config_ok_with_defaults():
    cfg = load_config({"GOVGENAI_API_BASE_URL": BASE, "GOVGENAI_PAT": PAT})
    assert cfg.api_base_url == BASE
    assert cfg.pat == PAT
    assert cfg.graph_profiles_path.name == "GRAPH_PROFILES.md"


# ---------------------------------------------------------------------------
# Servidor MCP: registro y lectura de resources
# ---------------------------------------------------------------------------

async def test_server_lists_expected_resources(tmp_path):
    srv = build_server(
        client_provider=lambda: None,
        config_provider=lambda: make_config(tmp_path / "g.md"),
    )
    listed = await srv.list_resources()
    uris = {str(r.uri).rstrip("/") for r in listed}
    assert {TEMPLATE_SCHEMA_URI, PROFILES_URI, GRAPH_PROFILES_URI} <= uris


@respx.mock
async def test_template_schema_resource_fetches_schema_from_api(tmp_path):
    schema = {
        "title": "ReportTemplateSpec",
        "type": "object",
        "properties": {"sections": {"type": "array"}},
    }
    respx.get(f"{BASE}{TEMPLATE_SCHEMA_PATH}").mock(
        return_value=httpx.Response(200, json=schema)
    )
    client = make_client()
    srv = build_server(
        client_provider=lambda: client,
        config_provider=lambda: make_config(tmp_path / "g.md"),
    )
    try:
        contents = list(await srv.read_resource(TEMPLATE_SCHEMA_URI))
    finally:
        await client.aclose()

    assert contents
    payload = json.loads(contents[0].content)
    assert payload["title"] == "ReportTemplateSpec"


async def test_profiles_resource_returns_known_profiles(tmp_path):
    srv = build_server(
        client_provider=lambda: None,
        config_provider=lambda: make_config(tmp_path / "g.md"),
    )
    contents = list(await srv.read_resource(PROFILES_URI))
    payload = json.loads(contents[0].content)
    assert payload["profiles"] == KNOWN_REPORT_PROFILES
    assert "GENERIC_REPORT" in payload["profiles"]


async def test_graph_profiles_resource_reads_markdown_file(tmp_path):
    doc = tmp_path / "GRAPH_PROFILES.md"
    doc.write_text("# Graph Profiles\nGuía de perfiles.", encoding="utf-8")
    srv = build_server(
        client_provider=lambda: None,
        config_provider=lambda: make_config(doc),
    )
    contents = list(await srv.read_resource(GRAPH_PROFILES_URI))
    assert "Graph Profiles" in contents[0].content
