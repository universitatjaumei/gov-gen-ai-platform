"""Cliente MCP del sistema de publicación del cliente (SYNC.1). Deploy: edge.

**Esto es ETL, no una operación agéntica.** Un script llama a la tool, recibe texto, calcula
hash y escribe: cero tokens de modelo y cero trazas Langfuse en esta ruta. La distinción no
es estética. El token del dataset viaja como **argumento de la tool**, así que si la llamada
se hiciera desde un agente con trazas activas el token quedaría escrito en el almacén de
trazas, que es un sitio del que nadie lo borra. Aquí no hay agente, y el token no se registra
ni siquiera en depuración: `_redactado()` lo sustituye antes de que nada llegue al log.

Dos datasets, y es la decisión que hace el coste proporcional a los cambios y no al tamaño
del corpus:

- **ÍNDICE** — una entrada por norma con id estable, `content_hash` y el bloque de metadatos.
  Pequeño, se pide entero y a menudo.
- **CONTENIDO** — el `.md`. Solo se pide si el índice dice que algo cambió.

`execute_dataset` es la única tool que expone el servicio y admite solo `dataset_code` y
`token`, así que el contenido es todo o nada: la granularidad se consigue **no pidiéndolo**,
no pidiendo trozos.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)

TOOL = "execute_dataset"
# El corpus completo ronda los ~10 MB (≈380 normas × ~25k caracteres), que está en la zona
# de los límites de respuesta de una Lambda. No es un límite que impongamos: es el tamaño a
# partir del cual conviene sospechar de una respuesta que no parsea.
UMBRAL_SOSPECHA_TRUNCADO = 1_000_000


class PublicationSyncError(Exception):
    """El servicio de publicación no ha devuelto un dataset utilizable.

    Siempre ruidoso y nunca degradado a «vacío»: un censo que llega a medias y se toma por
    bueno **despublica** las normas que faltan. Es el peor fallo posible de este módulo, y
    es silencioso por naturaleza, así que se convierte en excepción lo antes posible.
    """


class Transport(Protocol):
    """Lo único que el cliente necesita del mundo exterior: mandar un JSON-RPC y leer otro."""

    async def call(self, payload: dict) -> dict: ...


def _redactado(payload: dict) -> dict:
    """Copia del payload con el token sustituido, para poder volcarlo sin filtrarlo."""
    copia = json.loads(json.dumps(payload))
    argumentos = copia.get("params", {}).get("arguments", {})
    if "token" in argumentos:
        argumentos["token"] = "***"
    return copia


class _HttpTransport:
    """POST JSON-RPC. Se inyecta un doble en los tests para no montar un servidor."""

    def __init__(self, url: str, timeout: float) -> None:
        self._url = url
        self._timeout = timeout

    async def call(self, payload: dict) -> dict:
        import httpx

        async with httpx.AsyncClient(timeout=self._timeout) as cliente:
            respuesta = await cliente.post(self._url, json=payload)
            respuesta.raise_for_status()
            return respuesta.json()


class PublicationMcpClient:
    """Llama a `execute_dataset` y devuelve la lista de registros del dataset."""

    def __init__(
        self,
        url: str,
        token: str,
        transport: Transport | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._url = url
        self._token = token
        self._transport = transport or _HttpTransport(url, timeout)
        self._siguiente_id = 0

    async def execute_dataset(self, dataset_code: str) -> list[dict[str, Any]]:
        self._siguiente_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._siguiente_id,
            "method": "tools/call",
            "params": {
                "name": TOOL,
                "arguments": {"dataset_code": dataset_code, "token": self._token},
            },
        }
        # El dataset sí se registra —sin él no se puede depurar un sync—; el token no.
        logger.debug("execute_dataset: %s", _redactado(payload))

        try:
            respuesta = await self._transport.call(payload)
        except PublicationSyncError:
            raise
        except Exception as exc:
            raise PublicationSyncError(
                f"El dataset {dataset_code} no responde: {type(exc).__name__}"
            ) from exc

        return self._registros(dataset_code, respuesta)

    def _registros(self, dataset_code: str, respuesta: dict) -> list[dict[str, Any]]:
        if error := respuesta.get("error"):
            raise PublicationSyncError(
                f"El dataset {dataset_code} devolvio un error JSON-RPC: "
                f"{error.get('message', error)}"
            )

        contenido = (respuesta.get("result") or {}).get("content") or []
        textos = [b.get("text", "") for b in contenido if b.get("type") == "text"]
        if not textos:
            raise PublicationSyncError(
                f"El dataset {dataset_code} no trae ningun bloque de texto"
            )
        texto = "".join(textos)

        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as exc:
            pista = (
                " La respuesta ocupa mas de 1 MB, asi que lo mas probable es que venga "
                "truncada por el limite de respuesta del servicio."
                if len(texto) > UMBRAL_SOSPECHA_TRUNCADO
                else ""
            )
            raise PublicationSyncError(
                f"El dataset {dataset_code} no parsea como JSON ({len(texto)} caracteres): "
                f"{exc}.{pista} No se sincroniza nada: un censo parcial produciria "
                "despublicaciones falsas."
            ) from exc

        if not isinstance(datos, list):
            raise PublicationSyncError(
                f"El dataset {dataset_code} deberia ser una lista de registros y es "
                f"{type(datos).__name__}. No se sincroniza nada."
            )
        return datos
