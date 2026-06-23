"""Tests MCP.2 — tools de plantillas de redacción.

Sin red: respx intercepta httpx. Se prueba el mapeo tool→endpoint, el gating de
escritura (sin confirm no persiste) y el mapeo de errores del servidor.
"""
from __future__ import annotations

import httpx
import pytest
import respx

from api_client import ApiClient
from errors import ScopeError, ValidationError, ApiError
from server import build_server
from tools.templates import (
    APPROVE_AS_TEMPLATE_PATH,
    TEMPLATES_PATH,
    VALIDATE_PATH,
    create_template_core,
    get_template_spec_core,
    list_templates_core,
    publish_template_version_core,
    publish_versions_path,
    template_version_path,
    validate_template_draft_core,
)

BASE = "http://testserver"
PAT = "pat_abcd1234_secretsecretsecret"


def make_client() -> ApiClient:
    return ApiClient(BASE, PAT)


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_templates_calls_endpoint():
    payload = [{"id": "t1", "name": "Informe"}]
    route = respx.get(f"{BASE}{TEMPLATES_PATH}").mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = make_client()
    try:
        result = await list_templates_core(client)
    finally:
        await client.aclose()
    assert route.called
    assert result == payload


@respx.mock
async def test_get_template_spec_calls_endpoint():
    version_id = "11111111-1111-1111-1111-111111111111"
    payload = {"id": version_id, "version": 2, "spec": {"sections": []}}
    route = respx.get(f"{BASE}{template_version_path(version_id)}").mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = make_client()
    try:
        result = await get_template_spec_core(client, version_id)
    finally:
        await client.aclose()
    assert route.called
    assert result["spec"] == {"sections": []}


@respx.mock
async def test_get_template_spec_404_raises_api_error():
    version_id = "22222222-2222-2222-2222-222222222222"
    respx.get(f"{BASE}{template_version_path(version_id)}").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    client = make_client()
    try:
        with pytest.raises(ApiError) as exc:
            await get_template_spec_core(client, version_id)
    finally:
        await client.aclose()
    assert exc.value.status_code == 404


@respx.mock
async def test_validate_template_draft_returns_validator_result():
    result_body = {
        "ok": False,
        "errors": [{"loc": ["proposed_blocks"], "msg": "missing review gate", "type": "value_error"}],
    }
    route = respx.post(f"{BASE}{VALIDATE_PATH}").mock(
        return_value=httpx.Response(200, json=result_body)
    )
    client = make_client()
    try:
        result = await validate_template_draft_core(client, {"proposed_profile": "GENERIC_REPORT"})
    finally:
        await client.aclose()
    assert route.called
    assert result["ok"] is False
    assert result["errors"][0]["loc"] == ["proposed_blocks"]


# ---------------------------------------------------------------------------
# create_template — gating de escritura
# ---------------------------------------------------------------------------

@respx.mock
async def test_create_template_confirm_false_only_validates():
    validate_route = respx.post(f"{BASE}{VALIDATE_PATH}").mock(
        return_value=httpx.Response(200, json={"ok": True, "errors": []})
    )
    approve_route = respx.post(f"{BASE}{APPROVE_AS_TEMPLATE_PATH}").mock(
        return_value=httpx.Response(201, json={"template_id": "x"})
    )
    client = make_client()
    try:
        result = await create_template_core(
            client, {"proposed_profile": "GENERIC_REPORT"}, name="Plantilla", confirm=False
        )
    finally:
        await client.aclose()
    assert validate_route.called
    assert not approve_route.called  # NO persiste sin confirm
    assert result["created"] is False
    assert result["validation"]["ok"] is True


@respx.mock
async def test_create_template_confirm_true_creates():
    created_body = {"template_id": "tpl-1", "version_id": "ver-1", "name": "Plantilla"}
    approve_route = respx.post(f"{BASE}{APPROVE_AS_TEMPLATE_PATH}").mock(
        return_value=httpx.Response(201, json=created_body)
    )
    client = make_client()
    try:
        result = await create_template_core(
            client, {"proposed_profile": "GENERIC_REPORT"}, name="Plantilla", confirm=True
        )
    finally:
        await client.aclose()
    assert approve_route.called
    assert result["created"] is True
    assert result["result"]["template_id"] == "tpl-1"
    # El body enviado anida draft + name + is_global.
    sent = approve_route.calls.last.request
    assert b"draft" in sent.content
    assert b"Plantilla" in sent.content


@respx.mock
async def test_create_template_422_raises_validation_error():
    respx.post(f"{BASE}{APPROVE_AS_TEMPLATE_PATH}").mock(
        return_value=httpx.Response(
            422, json=[{"loc": ["name"], "msg": "required", "type": "value_error"}]
        )
    )
    client = make_client()
    try:
        with pytest.raises(ValidationError) as exc:
            await create_template_core(
                client, {"proposed_profile": "GENERIC_REPORT"}, name="x", confirm=True
            )
    finally:
        await client.aclose()
    assert exc.value.status_code == 422
    assert exc.value.detail[0]["loc"] == ["name"]


@respx.mock
async def test_create_template_without_scope_raises_scope_error():
    respx.post(f"{BASE}{APPROVE_AS_TEMPLATE_PATH}").mock(
        return_value=httpx.Response(403, json={"code": "PAT_SCOPE_MISSING", "missing": ["redaccion:templates:write"]})
    )
    client = make_client()
    try:
        with pytest.raises(ScopeError):
            await create_template_core(
                client, {"proposed_profile": "GENERIC_REPORT"}, name="x", confirm=True
            )
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# publish_template_version — dry_run / append-only
# ---------------------------------------------------------------------------

@respx.mock
async def test_publish_confirm_false_uses_dry_run_without_publishing():
    template_id = "tpl-1"
    route = respx.post(f"{BASE}{publish_versions_path(template_id)}").mock(
        return_value=httpx.Response(201, json={"published": False, "version": 2, "version_id": None})
    )
    client = make_client()
    try:
        result = await publish_template_version_core(
            client, template_id, {"sections": []}, confirm=False
        )
    finally:
        await client.aclose()
    assert route.called
    assert route.calls.last.request.url.params.get("dry_run") == "true"
    assert result["published"] is False


@respx.mock
async def test_publish_confirm_true_publishes():
    template_id = "tpl-1"
    route = respx.post(f"{BASE}{publish_versions_path(template_id)}").mock(
        return_value=httpx.Response(201, json={"published": True, "version": 2, "version_id": "ver-2"})
    )
    client = make_client()
    try:
        result = await publish_template_version_core(
            client, template_id, {"sections": []}, confirm=True
        )
    finally:
        await client.aclose()
    assert route.called
    assert route.calls.last.request.url.params.get("dry_run") is None
    assert result["published"] is True
    assert result["result"]["version_id"] == "ver-2"


@respx.mock
async def test_publish_without_scope_raises_scope_error():
    template_id = "tpl-1"
    respx.post(f"{BASE}{publish_versions_path(template_id)}").mock(
        return_value=httpx.Response(403, json={"code": "PAT_SCOPE_MISSING"})
    )
    client = make_client()
    try:
        with pytest.raises(ScopeError):
            await publish_template_version_core(
                client, template_id, {"sections": []}, confirm=True
            )
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Registro de tools en el servidor
# ---------------------------------------------------------------------------

async def test_template_tools_registered_on_server(tmp_path):
    srv = build_server(
        client_provider=lambda: None,
        config_provider=lambda: None,
    )
    tools = await srv.list_tools()
    names = {t.name for t in tools}
    assert {
        "list_templates",
        "get_template_spec",
        "validate_template_draft",
        "create_template",
        "publish_template_version",
    } <= names
