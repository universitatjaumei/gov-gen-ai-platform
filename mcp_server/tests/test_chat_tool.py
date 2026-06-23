"""Tests MCP.4 — tool test_chat + smoke de documentación.

Sin red (respx). El endpoint de chat responde SSE; se verifica que la tool agrega
los tokens y extrae las citas, y el mapeo de errores (403→ScopeError, 404→legible,
evento error→ApiError).
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from api_client import ApiClient
from errors import ApiError, ScopeError
from server import build_server
from tools.chat import chat_path, parse_chat_sse, run_test_chat_core

BASE = "http://testserver"
PAT = "pat_abcd1234_secretsecretsecret"
CB1 = "11111111-1111-1111-1111-111111111111"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def make_client() -> ApiClient:
    return ApiClient(BASE, PAT)


def _sse_stream() -> str:
    return (
        'event: status\ndata: {"node": "detect_language", "msg": "..."}\n\n'
        'event: token\ndata: {"delta": "Hola"}\n\n'
        'event: token\ndata: {"delta": " mundo"}\n\n'
        'event: done\ndata: {"interaction_id": "int-1", "sources": '
        '[{"document_id": "d1", "title": "Doc", "url": "http://x", "score": 0.9}], '
        '"language_fallback": false, "translation_warning": null}\n\n'
    )


# ---------------------------------------------------------------------------
# Parser SSE
# ---------------------------------------------------------------------------

def test_parse_chat_sse_aggregates_tokens_and_sources():
    result = parse_chat_sse(_sse_stream())
    assert result["answer"] == "Hola mundo"
    assert result["interaction_id"] == "int-1"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["title"] == "Doc"


def test_parse_chat_sse_error_event_raises():
    raw = 'event: error\ndata: {"message": "boom"}\n\n'
    with pytest.raises(ApiError) as exc:
        parse_chat_sse(raw)
    assert "boom" in str(exc.value)


# ---------------------------------------------------------------------------
# run_test_chat_core (respx)
# ---------------------------------------------------------------------------

@respx.mock
async def test_chat_calls_endpoint_and_returns_answer_with_sources():
    route = respx.post(f"{BASE}{chat_path(CB1)}").mock(
        return_value=httpx.Response(
            200, text=_sse_stream(), headers={"content-type": "text/event-stream"}
        )
    )
    client = make_client()
    try:
        result = await run_test_chat_core(client, CB1, "¿Hola?")
    finally:
        await client.aclose()
    assert route.called
    assert b"Hola" in route.calls.last.request.content  # mensaje enviado
    assert result["answer"] == "Hola mundo"
    assert result["sources"][0]["url"] == "http://x"


@respx.mock
async def test_chat_without_scope_raises_scope_error():
    respx.post(f"{BASE}{chat_path(CB1)}").mock(
        return_value=httpx.Response(403, json={"code": "PAT_SCOPE_MISSING", "missing": ["chat:test"]})
    )
    client = make_client()
    try:
        with pytest.raises(ScopeError):
            await run_test_chat_core(client, CB1, "hola")
    finally:
        await client.aclose()


@respx.mock
async def test_chat_404_chatbot_not_found_raises_legible_error():
    respx.post(f"{BASE}{chat_path(CB1)}").mock(
        return_value=httpx.Response(404, json={"detail": f"Chatbot {CB1} not found"})
    )
    client = make_client()
    try:
        with pytest.raises(ApiError) as exc:
            await run_test_chat_core(client, CB1, "hola")
    finally:
        await client.aclose()
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Registro + documentación
# ---------------------------------------------------------------------------

async def test_chat_tool_registered_on_server():
    srv = build_server(client_provider=lambda: None, config_provider=lambda: None)
    names = {t.name for t in await srv.list_tools()}
    assert "test_chat" in names


def test_docs_mcp_server_lists_all_tools():
    doc = (_REPO_ROOT / "docs" / "MCP_SERVER.md").read_text(encoding="utf-8")
    for tool in (
        "list_templates",
        "create_template",
        "publish_template_version",
        "update_chatbot",
        "assign_child",
        "test_chat",
    ):
        assert tool in doc, f"{tool} no documentado en MCP_SERVER.md"
    assert "claude mcp add" in doc
