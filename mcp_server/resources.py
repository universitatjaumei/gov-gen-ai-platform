"""Resources base del servidor MCP (MCP.1).

Tres resources que Claude consume como contexto de autoría:

- ``govgenai://redaccion/template-schema`` — JSON Schema de ``ReportTemplateSpec``.
  Fuente: endpoint del servidor ``GET /api/v1/hub/redaccion/template-schema``
  (garantizado en MCP.2). Dinámico: cambia con el código del backend, por eso se
  obtiene por HTTP y no se empaqueta.

- ``govgenai://redaccion/profiles`` — catálogo de perfiles de informe válidos.
  Fuente empaquetada: refleja ``ReportProfileId`` en
  ``server/app/modules/redaccion/contracts/template.py``. Es un Literal cerrado de
  baja rotación; mantener sincronizado aquí (o sustituir por endpoint si se añade).

- ``govgenai://docs/graph-profiles`` — guía de perfiles de grafo.
  Fuente empaquetada por ruta: lee ``docs/GRAPH_PROFILES.md`` del repo
  (configurable vía ``GOVGENAI_GRAPH_PROFILES_PATH``). Única fuente de verdad, sin
  copia duplicada.
"""
from __future__ import annotations

import json
from typing import Callable

from mcp.server.fastmcp import FastMCP

from api_client import ApiClient
from config import Config

TEMPLATE_SCHEMA_URI = "govgenai://redaccion/template-schema"
PROFILES_URI = "govgenai://redaccion/profiles"
GRAPH_PROFILES_URI = "govgenai://docs/graph-profiles"
CHATBOT_ENUMS_URI = "govgenai://chatbots/enums"
CHATBOT_SCHEMA_URI = "govgenai://chatbots/schema"

# Endpoint que sirve ReportTemplateSpec.model_json_schema() — añadido en MCP.2.
TEMPLATE_SCHEMA_PATH = "/api/v1/hub/redaccion/template-schema"

# OpenAPI vivo de la API; ChatbotCreate/ChatbotUpdate salen de components.schemas.
OPENAPI_PATH = "/openapi.json"

# Enums válidos de configuración de chatbot. Fuente documentada: campos de
# HubChatbot / ChatbotCreate (hub_chatbots_router.py) + perfiles de grafo (9B).
# public_graph_profile/kind/language_mode son `str` libres en el contrato (no
# enums de esquema), por eso se enumeran aquí; retrieval_mode sí es Literal.
CHATBOT_ENUMS: dict[str, list[str]] = {
    "retrieval_mode": ["RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR"],
    "public_graph_profile": [
        "PUBLIC_KB_RICH",
        "PUBLIC_PORTAL_AGGREGATOR",
        "PUBLIC_PORTAL_ROUTER",
    ],
    "kind": ["atomic", "router"],
    "language_mode": ["prefer", "strict", "neutral"],
}

# Espejo de ReportProfileId (contracts/template.py). Fuente de verdad documentada.
KNOWN_REPORT_PROFILES: list[str] = [
    "GENERIC_REPORT",
    "ANNUAL_REPORT",
    "DOCTORATE_PROGRAM_REPORT",
    "CONTRACT_REPORT",
    "FREEFORM_MEMO",
]

ClientProvider = Callable[[], ApiClient]
ConfigProvider = Callable[[], Config]


def register_resources(
    mcp: FastMCP,
    *,
    client_provider: ClientProvider,
    config_provider: ConfigProvider,
) -> None:
    """Registra los tres resources base en el servidor FastMCP.

    Los providers se resuelven de forma perezosa (al leer el resource), de modo
    que construir el servidor no requiere configuración de entorno: el PAT solo
    se necesita cuando un resource toca la API.
    """

    @mcp.resource(
        TEMPLATE_SCHEMA_URI,
        name="report_template_schema",
        title="JSON Schema de ReportTemplateSpec",
        description=(
            "JSON Schema de la spec de plantilla de informe. Redacta los drafts "
            "de plantilla contra este contrato."
        ),
        mime_type="application/json",
    )
    async def report_template_schema() -> str:
        schema = await client_provider().get(TEMPLATE_SCHEMA_PATH)
        return json.dumps(schema, ensure_ascii=False, indent=2)

    @mcp.resource(
        PROFILES_URI,
        name="report_profiles",
        title="Perfiles de informe válidos",
        description="Catálogo de report_profile admitidos por una plantilla.",
        mime_type="application/json",
    )
    def report_profiles() -> str:
        return json.dumps({"profiles": KNOWN_REPORT_PROFILES}, ensure_ascii=False, indent=2)

    @mcp.resource(
        GRAPH_PROFILES_URI,
        name="graph_profiles_guide",
        title="Guía de perfiles de grafo",
        description="Contenido de docs/GRAPH_PROFILES.md como guía de configuración.",
        mime_type="text/markdown",
    )
    def graph_profiles_guide() -> str:
        return config_provider().graph_profiles_path.read_text(encoding="utf-8")


def register_chatbot_resources(
    mcp: FastMCP,
    *,
    client_provider: ClientProvider,
) -> None:
    """Resources de configuración de chatbots (MCP.3).

    - ``govgenai://chatbots/enums`` — enums válidos (empaquetado, ver CHATBOT_ENUMS).
    - ``govgenai://chatbots/schema`` — JSON Schema de ChatbotCreate/ChatbotUpdate
      extraído del ``/openapi.json`` vivo (sin acoplar al backend ni duplicar).
    """

    @mcp.resource(
        CHATBOT_ENUMS_URI,
        name="chatbot_enums",
        title="Enums de configuración de chatbot",
        description="Valores válidos de retrieval_mode, public_graph_profile, kind, language_mode.",
        mime_type="application/json",
    )
    def chatbot_enums() -> str:
        return json.dumps(CHATBOT_ENUMS, ensure_ascii=False, indent=2)

    @mcp.resource(
        CHATBOT_SCHEMA_URI,
        name="chatbot_schema",
        title="JSON Schema de ChatbotCreate/ChatbotUpdate",
        description="Esquemas de creación/actualización de chatbot (desde /openapi.json).",
        mime_type="application/json",
    )
    async def chatbot_schema() -> str:
        spec = await client_provider().get(OPENAPI_PATH)
        schemas = (spec or {}).get("components", {}).get("schemas", {})
        out = {name: schemas.get(name) for name in ("ChatbotCreate", "ChatbotUpdate")}
        return json.dumps(out, ensure_ascii=False, indent=2)
