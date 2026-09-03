"""Tools MCP de registro de actividad y anonimización (REG.4).

Tres tools, y las tres envuelven endpoints `Deploy: edge` de la API:

- `registrar_actividad` → `POST /api/v1/actividad` (REG.2). Es el camino para que un agente que
  trabaja *fuera* de la plataforma —un asistente de escritorio, un agente de código— quede en el
  registro de usos de IA de su organización.
- `detectar_pii` → `POST /api/v1/anonimizacion/spans` (REG.3).
- `anonimizar_texto` → `POST /api/v1/anonimizacion/replace` (REG.3).

**Sin puerta de confirmación en `registrar_actividad`.** `update_chatbot` tiene una porque muta un
chatbot en producción in-place y un error ahí lo nota quien esté usando el asistente. Registrar
actividad es añadir metadatos: no muta nada, y una tool que un agente va a llamar de forma
rutinaria dejaría de llamarse si cada vez pidiera permiso — con lo que el registro quedaría vacío,
que es peor que cualquier entrada de más.

**Los errores no se silencian.** `ApiClient` ya traduce 401/403/422 a excepciones legibles con el
cuerpo del servidor en `detail`; el SDK MCP las reporta al cliente. Un `except` aquí convertiría
«te falta el scope `actividad:write`» en «no se pudo registrar», que es justo el mensaje que no
deja arreglar nada.
"""
from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from api_client import ApiClient

ACTIVIDAD_PATH = "/api/v1/actividad"
SPANS_PATH = "/api/v1/anonimizacion/spans"
REPLACE_PATH = "/api/v1/anonimizacion/replace"

ClientProvider = Callable[[], ApiClient]


async def run_registrar_actividad_core(
    client: ApiClient, evento: dict[str, Any]
) -> dict:
    """Envía el evento tal cual: el contrato lo valida el servidor.

    No se rellena ni se completa nada aquí. Un valor por defecto puesto en el cliente MCP sería
    un dato del registro que no declaró quien lo usó, y el registro dejaría de decir la verdad.
    """
    return await client.post(ACTIVIDAD_PATH, json=evento)


async def run_detectar_pii_core(client: ApiClient, text: str) -> dict:
    return await client.post(SPANS_PATH, json={"text": text})


async def run_anonimizar_texto_core(client: ApiClient, text: str) -> dict:
    return await client.post(REPLACE_PATH, json={"text": text})


def register_actividad_tools(mcp: FastMCP, *, client_provider: ClientProvider) -> None:
    @mcp.tool()
    async def registrar_actividad(evento: dict) -> dict:
        """Declara un uso de IA ocurrido fuera de la plataforma. [scope actividad:write]

        El evento lleva **metadatos de gobernanza, nunca el contenido**: cuándo ocurrió, quién,
        con qué herramienta y agente, para qué, con qué modelo y qué categorías de datos tocó. Si
        hace falta dejar prueba de un texto concreto, va su SHA-256 en `payload_hash`. El contrato
        rechaza cualquier campo de contenido, así que mandar el prompt no lo registra: falla.

        La organización sale del token, no se elige. Devuelve `id` y `registrado_en`.
        """
        return await run_registrar_actividad_core(client_provider(), evento)

    @mcp.tool()
    async def detectar_pii(text: str) -> dict:
        """Localiza datos personales en un texto sin modificarlo. [scope anonimizacion:use]

        Devuelve `spans` con posición, tipo y un sustituto propuesto. Úsalo para decidir o
        mostrar; para obtener el texto ya limpio, `anonimizar_texto`.
        """
        return await run_detectar_pii_core(client_provider(), text)

    @mcp.tool()
    async def anonimizar_texto(text: str) -> dict:
        """Sustituye los datos personales de un texto. [scope anonimizacion:use]

        Devuelve `text_anonimizado` y `spans_aplicados`, que describe exactamente lo que se
        sustituyó en ese texto. Ni el original ni el resultado se registran en el servidor.
        """
        return await run_anonimizar_texto_core(client_provider(), text)
