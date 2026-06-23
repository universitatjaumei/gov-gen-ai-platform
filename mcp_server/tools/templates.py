"""Tools MCP de autoría de plantillas de redacción (MCP.2).

Envuelven endpoints `Deploy: edge` ya existentes (+ los nuevos de MCP.2):

- lectura: `list_templates`, `get_template_spec`        [scope redaccion:templates:read]
- validación sin persistir: `validate_template_draft`   [read]
- escritura *gated*: `create_template`, `publish_template_version`  [scope ...:write]

Gate de escritura por construcción (cumple la regla HITL de
`REDACCION_CONTRACT_FIRST.md` con el admin como aprobador): las tools de escritura
NO persisten salvo confirmación explícita (`confirm=True`). Sin confirmar solo
validan y devuelven el plan. El versionado es append-only en el servidor:
`publish_template_version` solo añade, nunca corrompe una versión publicada.

La lógica vive en funciones `_core` (reciben el ``ApiClient`` explícito, testeables
con respx); los decoradores `@mcp.tool()` son envoltorios finos que resuelven el
cliente vía ``client_provider``.
"""
from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from api_client import ApiClient

# Rutas absolutas (incluyen /api/v1: el base_url del ApiClient es el host de la API).
TEMPLATES_PATH = "/api/v1/hub/redaccion/templates"
VALIDATE_PATH = "/api/v1/redaccion/llm-drafts/validate"
APPROVE_AS_TEMPLATE_PATH = "/api/v1/redaccion/llm-drafts/approve-as-template"


def template_version_path(version_id: str) -> str:
    return f"/api/v1/hub/redaccion/template-versions/{version_id}"


def publish_versions_path(template_id: str) -> str:
    return f"/api/v1/hub/redaccion/templates/{template_id}/versions"


ClientProvider = Callable[[], ApiClient]


# ---------------------------------------------------------------------------
# Lógica core (testeable con un ApiClient real + respx)
# ---------------------------------------------------------------------------

async def list_templates_core(client: ApiClient) -> Any:
    return await client.get(TEMPLATES_PATH)


async def get_template_spec_core(client: ApiClient, version_id: str) -> Any:
    return await client.get(template_version_path(version_id))


async def validate_template_draft_core(client: ApiClient, draft: dict) -> Any:
    return await client.post(VALIDATE_PATH, json=draft)


async def create_template_core(
    client: ApiClient,
    draft: dict,
    name: str,
    is_global: bool = False,
    confirm: bool = False,
) -> dict:
    if not confirm:
        validation = await client.post(VALIDATE_PATH, json=draft)
        return {"created": False, "validation": validation}
    created = await client.post(
        APPROVE_AS_TEMPLATE_PATH,
        json={"draft": draft, "name": name, "is_global": is_global},
    )
    return {"created": True, "result": created}


async def publish_template_version_core(
    client: ApiClient,
    template_id: str,
    spec: dict,
    confirm: bool = False,
) -> dict:
    payload = {"spec_json": spec}
    if not confirm:
        result = await client.post(
            publish_versions_path(template_id),
            params={"dry_run": "true"},
            json=payload,
        )
        return {"published": False, "result": result}
    result = await client.post(publish_versions_path(template_id), json=payload)
    return {"published": True, "result": result}


# ---------------------------------------------------------------------------
# Registro de tools MCP
# ---------------------------------------------------------------------------

def register_template_tools(mcp: FastMCP, *, client_provider: ClientProvider) -> None:
    @mcp.tool()
    async def list_templates() -> Any:
        """Lista las plantillas visibles (globales + propias).

        [scope redaccion:templates:read]
        """
        return await list_templates_core(client_provider())

    @mcp.tool()
    async def get_template_spec(version_id: str) -> Any:
        """Devuelve la spec completa de una versión de plantilla.

        [scope redaccion:templates:read]
        """
        return await get_template_spec_core(client_provider(), version_id)

    @mcp.tool()
    async def validate_template_draft(draft: dict) -> Any:
        """Valida un ReportTemplateDraft con el DraftValidator. NO persiste.

        Devuelve el resultado del validador (errores con loc/msg/type).
        [scope redaccion:templates:read]
        """
        return await validate_template_draft_core(client_provider(), draft)

    @mcp.tool()
    async def create_template(
        draft: dict,
        name: str,
        is_global: bool = False,
        confirm: bool = False,
    ) -> dict:
        """Crea una plantilla a partir de un ReportTemplateDraft. [scope ...:write]

        ``confirm=False`` (por defecto) solo valida el draft y devuelve el plan, sin
        crear nada. ``confirm=True`` persiste la plantilla (+ versión 1) y devuelve
        sus identificadores. ``is_global=True`` requiere rol admin en el servidor.
        """
        return await create_template_core(
            client_provider(), draft, name, is_global=is_global, confirm=confirm
        )

    @mcp.tool()
    async def publish_template_version(
        template_id: str,
        spec: dict,
        confirm: bool = False,
    ) -> dict:
        """Publica una nueva versión (append-only) de una plantilla. [scope ...:write]

        ``confirm=False`` (por defecto) valida la spec contra ReportTemplateSpec y
        calcula la versión resultante SIN publicar. ``confirm=True`` publica la nueva
        versión y devuelve su ``version_id``. Nunca muta versiones existentes.
        """
        return await publish_template_version_core(
            client_provider(), template_id, spec, confirm=confirm
        )
