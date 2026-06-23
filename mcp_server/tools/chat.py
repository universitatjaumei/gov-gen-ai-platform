"""Tool MCP de chat de prueba (MCP.4).

Cierra el bucle configurar→probar→ajustar: lanza una pregunta contra un chatbot ya
configurado y devuelve la respuesta + las citas/evidencias, para evaluar la config.

Envuelve `POST /api/v1/hub/chat/{chatbot_id}` (`hub_chat`, `Deploy: edge`), que
responde como **Server-Sent Events** (eventos `status`/`token`/`done`/`error`).
``ApiClient.post`` consume el stream completo; aquí se parsea: se concatenan los
``token`` y se extraen ``sources``/metadatos del evento ``done``.

Nota dev/prod: en desarrollo (`DEPLOY_MODE=all`) chat (edge) y configuración (cloud)
conviven en el mismo servidor, así que un único `GOVGENAI_API_BASE_URL` sirve para
todo. En despliegue real son superficies distintas (edge vs cloud) y `test_chat`
apunta al edge; las tools de chatbots/plantillas, al cloud.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from api_client import ApiClient, ApiError


def chat_path(chatbot_id: str) -> str:
    return f"/api/v1/hub/chat/{chatbot_id}"


ClientProvider = Callable[[], ApiClient]


def parse_chat_sse(raw: str) -> dict:
    """Parsea el stream SSE del chat en una respuesta estructurada.

    Concatena los deltas de los eventos ``token`` y toma ``sources`` y metadatos del
    evento ``done``. Un evento ``error`` se eleva como ``ApiError`` legible.
    """
    answer_parts: list[str] = []
    done: dict[str, Any] = {}
    error_message: str | None = None

    for block in raw.split("\n\n"):
        event: str | None = None
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
        if not data_lines:
            continue
        try:
            data = json.loads("\n".join(data_lines))
        except ValueError:
            continue
        if event == "token":
            answer_parts.append(data.get("delta", ""))
        elif event == "done":
            done = data
        elif event == "error":
            error_message = data.get("message", "chat error")

    if error_message is not None:
        raise ApiError(f"El chat devolvió un error: {error_message}")

    return {
        "answer": "".join(answer_parts),
        "sources": done.get("sources", []),
        "interaction_id": done.get("interaction_id"),
        "language_fallback": done.get("language_fallback"),
        "translation_warning": done.get("translation_warning"),
    }


async def run_test_chat_core(
    client: ApiClient,
    chatbot_id: str,
    message: str,
    lang: str | None = None,
) -> dict:
    # El endpoint detecta el idioma automáticamente; `lang` se acepta por estabilidad
    # de la API de la tool pero hoy no se reenvía (el body solo lleva `message`).
    raw = await client.post(chat_path(chatbot_id), json={"message": message})
    return parse_chat_sse(raw if isinstance(raw, str) else json.dumps(raw))


def register_chat_tools(mcp: FastMCP, *, client_provider: ClientProvider) -> None:
    @mcp.tool()
    async def test_chat(chatbot_id: str, message: str, lang: str | None = None) -> dict:
        """Lanza una pregunta de prueba a un chatbot y devuelve respuesta + citas.

        Úsalo para evaluar la configuración de un bot tras ajustarla. [scope chat:test]
        Devuelve ``answer`` (texto agregado), ``sources`` (evidencias), e
        ``interaction_id``/``language_fallback``/``translation_warning``.
        """
        return await run_test_chat_core(client_provider(), chatbot_id, message, lang)
