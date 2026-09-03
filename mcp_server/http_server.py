"""Servidor MCP remoto: streamable HTTP con el token de cada cliente (REG.4).

Es la «opción B» que `docs/mcp.md` dejó anotada en 2026-06-06 sin caso de uso; el bloque REG lo
trajo. El servidor stdio de `server.py` **no cambia**: sigue siendo mono-usuario y sigue leyendo
`GOVGENAI_PAT` del entorno, que ahí es lo correcto —un proceso, una persona, un token—.

**Lo que cambia aquí es de dónde sale la credencial.** Un servicio remoto atiende a varios
clientes a la vez. Si el operador plantara un PAT en su entorno, todos actuarían con él: mismos
permisos, misma organización y mismo rastro en el registro de actividad. La trazabilidad que el
bloque REG existe para dar se perdería justo en la superficie que más la necesita. Así que el
token es el `Authorization: Bearer` de cada petición MCP entrante, y viaja de ahí al `ApiClient`
de esa llamada y de nadie más.

Y si no viene, la tool falla con un mensaje que dice qué falta. Llamar a la API sin credencial
sólo conseguiría que el 401 del servidor llegara disfrazado de avería nuestra.

**Dos decisiones del transporte:**

*Sin sesión* (`stateless_http`). No hay nada que guardar entre peticiones: cada llamada trae su
propia credencial. A cambio, el proxy inverso puede repartir sin afinidad y un reinicio del
servicio no deja clientes con una sesión que ya no existe.

*Respuestas JSON* en vez de SSE. Estas tres tools son petición y respuesta, sin progreso ni
elicitación que haya que ir emitiendo; y un flujo SSE a través de un proxy inverso funciona sólo
si alguien se acordó de desactivar el buffering, que es una avería silenciosa esperando su
momento.

**El paquete sigue sin importar `server/app`** (regla de MCP.1, con test): es un cliente HTTP más,
como el frontend, y eso es lo que le permite desplegarse como el proceso pequeño que es.

Arranque local (desde `mcp_server/`):

    GOVGENAI_API_BASE_URL=http://localhost:8000 \\
    GOVGENAI_MCP_ALLOWED_HOSTS=localhost:8080 \\
        uv run uvicorn http_server:app --factory --port 8080
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Mapping

# Permite ejecutar por ruta resolviendo los imports hermanos sin instalar el paquete.
_PKG_DIR = str(Path(__file__).resolve().parent)
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from api_client import ApiClient
from config import HttpConfig, load_http_config
from tools.actividad import register_actividad_tools

_TIMEOUT = 30.0


class PatAusenteError(RuntimeError):
    """La petición MCP no trae un PAT utilizable.

    Es error del cliente, y el mensaje lo dice para que se pueda arreglar sin leer nuestro código.
    """


def pat_de_las_cabeceras(cabeceras: Mapping[str, str]) -> str:
    """Extrae el PAT de `Authorization`, o explica qué falta.

    Se exige el esquema `Bearer` explícitamente en vez de aceptar cualquier cosa: un cliente mal
    configurado que mande `Basic` recibe aquí un mensaje útil, y no un 401 del servidor que le
    haría buscar el problema en su token.
    """
    bruto = (cabeceras.get("authorization") or "").strip()
    if not bruto:
        raise PatAusenteError(
            "Falta el PAT. Este servidor MCP no tiene token propio: cada cliente presenta el "
            "suyo en la cabecera `Authorization: Bearer pat_...` al conectarse."
        )

    esquema, _, valor = bruto.partition(" ")
    if esquema.lower() != "bearer" or not valor.strip():
        raise PatAusenteError(
            f"El PAT se presenta como `Authorization: Bearer pat_...`; llegó el esquema "
            f"`{esquema}`."
        )
    return valor.strip()


def build_http_server(config: HttpConfig | None = None) -> FastMCP:
    """Construye el servidor MCP remoto con las tools de actividad y anonimización."""
    cfg = config or load_http_config()

    pool = httpx.AsyncClient(base_url=cfg.api_base_url.rstrip("/"), timeout=_TIMEOUT)

    @asynccontextmanager
    async def _ciclo(_servidor: FastMCP):
        # El pool se comparte entre clientes con tokens distintos porque la cabecera se pone por
        # petición (ver `ApiClient._request`); lo que se comparte son conexiones, no identidades.
        try:
            yield {}
        finally:
            await pool.aclose()

    mcp = FastMCP(
        "govgenai-remoto",
        stateless_http=True,
        json_response=True,
        lifespan=_ciclo,
        transport_security=TransportSecuritySettings(
            allowed_hosts=list(cfg.allowed_hosts),
            allowed_origins=list(cfg.allowed_origins),
        ),
    )

    def client_provider() -> ApiClient:
        """Un `ApiClient` con el token de **esta** petición.

        Se lee del contexto en cada llamada y no se guarda en ninguna variable de módulo: con dos
        clientes en vuelo a la vez, un token guardado se mezclaría con el del otro. Hay un test
        que lo comprueba con dos peticiones concurrentes.
        """
        peticion = mcp.get_context().request_context.request
        if peticion is None:  # pragma: no cover - sólo si se monta sobre otro transporte
            raise PatAusenteError(
                "Esta tool necesita el PAT de la petición HTTP entrante y aquí no hay ninguna."
            )
        return ApiClient(cfg.api_base_url, pat_de_las_cabeceras(peticion.headers), client=pool)

    register_actividad_tools(mcp, client_provider=client_provider)
    return mcp


def build_http_app(config: HttpConfig | None = None) -> Starlette:
    """La aplicación ASGI, para servirla con uvicorn detrás del proxy inverso."""
    return build_http_server(config).streamable_http_app()


def app() -> Starlette:  # pragma: no cover - punto de entrada de uvicorn --factory
    return build_http_app()
