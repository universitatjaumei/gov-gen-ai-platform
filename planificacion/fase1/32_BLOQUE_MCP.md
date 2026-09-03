## Bloque MCP — Servidor MCP stdio para autoría de plantillas y configuración de chatbots (PENDIENTE)

> **Posición en orden de ejecución**: tras el Bloque AUTH (que aporta el PAT que MCP consume) y antes de Fase 11.

**Origen**: `docs/mcp.md` (valoraciones 1 y 2). Decisiones de planificación tomadas (2026-06-11): **opción A (servidor MCP stdio local, wrapper de la API HTTP)** y alcance **completo** = plantillas (valoración 1) + chatbots (valoración 2) + `test_chat` (fase 2 de mcp.md).

**Por qué encaja sin reabrir nada (resumen de mcp.md)**: la arquitectura contract-first hace el trabajo. El servidor MCP es **un cliente HTTP más** de la API existente (`hub_redaccion_router`/`hub_chatbots_router`), igual que el frontend. No cruza bases ORM ni importa módulos prohibidos. Las piezas críticas ya existen: `DraftValidator`, versionado append-only de plantillas (`ReportTemplateVersionRepo` sin `update()`), `ReportTemplateSpec.model_json_schema()`.

**Ubicación del paquete**: `mcp_server/` en la raíz del repo (paquete independiente con su propio `pyproject.toml`, SDK oficial `mcp`). **No** vive bajo `server/app/` — es un cliente, no parte del servidor. No importa nada de `server/app`; habla con la API por HTTP.

**Autenticación**: el servidor MCP lee un **PAT** (Bloque AUTH) de variable de entorno y lo envía en `Authorization: Bearer pat_…`. Los scopes del PAT acotan lo que el servidor puede hacer (lectura vs escritura).

**HITL por construcción (regla dura nº4 de `REDACCION_CONTRACT_FIRST.md`)**: con MCP el humano está en el bucle (aprueba cada tool call en Claude Code). Se refuerza: tools de lectura/validación libres; las de escritura (`publish_template_version`, `create_template`, `update_chatbot`) exigen un **flag explícito de confirmación** y devuelven el resultado del validador / un *diff* antes de persistir.

**Reglas duras del bloque MCP**:
- El servidor MCP **no** importa código de `server/app`; solo cliente HTTP (`httpx`).
- Toda escritura requiere `confirm=True` (o `dry_run=False` explícito) y el scope de PAT correspondiente; sin él, el tool devuelve el plan/diff sin ejecutar.
- Errores HTTP (401/403/422) del servidor se mapean a errores de tool legibles, nunca se silencian.
- Tests sin red: `respx`/transport mock de httpx; se prueba el mapeo tool→llamada HTTP y el gating de escritura, no el servidor real.

---

### Prompt MCP.1 (RED/GREEN) — Scaffolding del servidor MCP stdio + cliente API con PAT + resources

**Modelo sugerido**: **Opus** — primer contacto con el SDK MCP y el transporte stdio, diseño de la arquitectura del cliente (auth PAT, mapeo de errores, resources); decisiones que condicionan MCP.2–MCP.4.

**Objetivo**: crear el paquete `mcp_server/` con el SDK oficial `mcp` (FastMCP), transporte stdio, un cliente HTTP autenticado por PAT y los *resources* base (JSON Schema de `ReportTemplateSpec`, registry de profiles, guía `GRAPH_PROFILES.md`).

**Contexto**: SDK oficial Python `mcp` (FastMCP: `@mcp.tool()`, `@mcp.resource()`, `mcp.run()` stdio). El JSON Schema de `ReportTemplateSpec` se expone como resource; para no acoplar el cliente al backend, se obtiene de un endpoint nuevo del servidor (ver MCP.2) o, de forma transitoria, de `openapi.json`. Config por entorno: `GOVGENAI_API_BASE_URL`, `GOVGENAI_PAT`.

**Instrucciones al agente**:
```markdown
# PROMPT MCP.1 (RED/GREEN) — Scaffolding MCP stdio + auth PAT

## Paquete mcp_server/ (raíz del repo, pyproject propio)
- deps: mcp, httpx, pydantic. NO depende de server/app.
- mcp_server/config.py: GOVGENAI_API_BASE_URL, GOVGENAI_PAT (desde env); error claro si faltan.
- mcp_server/api_client.py: ApiClient(httpx.AsyncClient) con base_url + header
  Authorization: Bearer <PAT>. Métodos get/post/patch/delete que mapean
  401->AuthError, 403->ScopeError, 422->ValidationError (con el body), 5xx->ServerError.
- mcp_server/server.py: FastMCP("govgenai"); registra resources base; mcp.run() stdio.

## Resources base (mcp_server/resources/)
- resource "govgenai://redaccion/template-schema" -> JSON Schema de ReportTemplateSpec
  (vía GET del endpoint del servidor; en MCP.2 se garantiza el endpoint).
- resource "govgenai://redaccion/profiles" -> registry de report profiles.
- resource "govgenai://docs/graph-profiles" -> contenido de docs/GRAPH_PROFILES.md
  (servido vía endpoint o empaquetado; documentar la fuente).

## Tests (mínimo 8) — mcp_server/tests/test_scaffolding.py (respx)
- ApiClient inyecta Authorization: Bearer <PAT> en cada request.
- 401 -> AuthError; 403 -> ScopeError; 422 -> ValidationError con detalle del body.
- El servidor MCP arranca y lista los resources esperados (in-memory client del SDK mcp).
- resource template-schema devuelve el JSON Schema (respx-mock del endpoint).
- Falta de GOVGENAI_PAT -> error de configuración claro al iniciar.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; `mcp_server` arranca en stdio (`uv run mcp run mcp_server/server.py` o equivalente) y lista resources. Sin imports de `server/app` (grep limpio).

---

### Prompt MCP.2 (RED/GREEN) — Tools de plantillas (redacción) con gate de escritura HITL

**Modelo sugerido**: **Sonnet** — toolset acotado sobre endpoints ya existentes; el SDK ya está cableado en MCP.1.

**Objetivo**: exponer la autoría de `ReportTemplateSpec` como tools MCP: lectura (`list_templates`, `get_template_spec`), validación sin persistir (`validate_template_draft`) y escritura gated (`create_template`, `publish_template_version`).

**Contexto**: endpoints en `hub_redaccion_router` / `llm_drafts_router` (`Deploy: edge`); `DraftValidator` ya expuesto vía `/validate`. Versionado append-only: `publish_template_version` solo añade, nunca corrompe una versión publicada. Si no existe aún un endpoint que devuelva `ReportTemplateSpec.model_json_schema()`, **añadirlo** en el servidor (GET `/api/v1/hub/redaccion/template-schema`, `Deploy: edge`) — alimenta el resource de MCP.1.

**Instrucciones al agente**:
```markdown
# PROMPT MCP.2 (RED/GREEN) — Tools de plantillas

## Backend (si falta): GET /api/v1/hub/redaccion/template-schema -> ReportTemplateSpec.model_json_schema()
  Deploy: edge. operation_id explícito. Test del endpoint.

## Tools (mcp_server/tools/templates.py)
- list_templates() -> GET /hub/redaccion/templates                 [scope redaccion:templates:read]
- get_template_spec(version_id) -> GET .../template-versions/{id}   [read]
- validate_template_draft(spec: dict) -> POST .../validate          [read] (no persiste; devuelve
    el resultado del DraftValidator: errores con loc/msg/type).
- create_template(draft: dict, confirm: bool=False)                 [scope redaccion:templates:write]
    - confirm=False -> ejecuta solo la validación y devuelve el plan; NO crea.
    - confirm=True  -> POST de creación; devuelve el id/version creados.
- publish_template_version(template_id, spec: dict, confirm: bool=False)  [write]
    - confirm=False -> valida (DraftValidator) y devuelve el resultado SIN publicar.
    - confirm=True  -> publica (append-only) y devuelve la nueva version_id.

## Tests (mínimo 10) — mcp_server/tests/test_templates_tools.py (respx)
- cada tool de lectura llama al endpoint correcto y devuelve el payload mapeado.
- validate_template_draft devuelve el resultado del validador (incluye errores).
- create_template/publish con confirm=False -> NO hace POST (solo valida) y devuelve el plan.
- create_template/publish con confirm=True -> hace el POST y devuelve el id.
- 422 del validador -> ValidationError legible.
- escritura sin scope (403 del servidor) -> ScopeError clara.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; endpoint `template-schema` en OpenAPI; gating de escritura verificado (sin confirm no persiste).

---

### Prompt MCP.3 (RED/GREEN) — Tools de chatbots (configuración cloud) con diff/dry_run

**Modelo sugerido**: **Sonnet** — segundo namespace de tools sobre `hub_chatbots_router`; patrón establecido en MCP.2.

**Objetivo**: exponer la configuración de chatbots como tools MCP (namespace `chatbots_*`), mitigando el riesgo de mutación in-place con *diff* y `dry_run`.

**Contexto**: `hub_chatbots_router` (`Deploy: cloud`, roles admin/partner). Versionado in-place sin historial: una escritura errónea muta un bot en producción y el widget público cambia al instante (ver mcp.md valoración 2). Por eso `update_chatbot` ecoa el *diff* (config actual → propuesta) y admite `dry_run`. `GET /hub/chatbots/{id}/corpus-stats` ya recomienda modo según corpus.

**Instrucciones al agente**:
```markdown
# PROMPT MCP.3 (RED/GREEN) — Tools de chatbots

## Resources (mcp_server/resources/)
- enums válidos (public_graph_profile, retrieval_mode, kinds) y JSON Schema de
  ChatbotCreate/ChatbotUpdate (vía endpoint de esquema o openapi.json).

## Tools (mcp_server/tools/chatbots.py)
Lectura [scope chatbots:read]:
- list_clients(), list_chatbots(client_id?), get_chatbot(id),
  get_corpus_stats(id), list_prompt_templates(chatbot_id?)
Escritura [scope chatbots:write]:
- create_chatbot(payload, confirm=False)   # confirm=False -> valida y devuelve plan
- update_chatbot(id, patch, dry_run=True)   # dry_run=True -> devuelve diff actual→propuesta
                                             #   sin persistir; dry_run=False -> aplica el PATCH
- update_prompt_template(id, payload, confirm=False)
- assign_child(router_id, child_id, confirm=False) / unassign_child(...)

## Tests (mínimo 10) — mcp_server/tests/test_chatbots_tools.py (respx)
- lecturas llaman al endpoint correcto (incluye corpus-stats con su recomendación).
- update_chatbot(dry_run=True) hace GET del estado actual, devuelve diff, NO hace PATCH.
- update_chatbot(dry_run=False) hace el PATCH.
- create/assign con confirm=False -> no persiste.
- escritura sin scope chatbots:write -> ScopeError.
- validaciones del servidor (límite 128K MD_LONG_CONTEXT, jerarquía) -> 422 -> ValidationError.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; diff/dry_run verificados; ningún import de `server/app`.

---

### Prompt MCP.4 (RED/GREEN) — Tool `test_chat` + documentación `MCP_SERVER.md` + registro `claude mcp add`

**Modelo sugerido**: **Sonnet** — un tool adicional + documentación; alcance cerrado.

**Objetivo**: cerrar el bucle configurar→probar→ajustar con un tool de chat de prueba, y documentar instalación, scopes y seguridad del servidor MCP.

**Contexto**: `hub_chat_router` (`Deploy: edge`) sirve el chat. En dev (`DEPLOY_MODE=all`) chat y config conviven; en despliegue real son superficies distintas (edge vs cloud) — documentarlo. Este prompt **no** requiere `.bat` de pruebas manuales (no es UI de navegador, es integración MCP/CLI); en su lugar incluye una verificación de integración con Claude Code.

**Instrucciones al agente**:
```markdown
# PROMPT MCP.4 (RED/GREEN) — test_chat + docs

## Tool (mcp_server/tools/chat.py)
- test_chat(chatbot_id, message, lang?) -> POST al endpoint de chat (hub_chat)  [scope chat:test]
  Devuelve la respuesta + evidencias/citas para evaluar la config del bot.
  Documentar la nota dev/prod (misma vs distinta superficie).

## docs/MCP_SERVER.md
- Propósito y arquitectura (cliente HTTP stdio, opción A de mcp.md).
- Variables de entorno (GOVGENAI_API_BASE_URL, GOVGENAI_PAT) y cómo emitir el PAT (Bloque AUTH UI).
- Mapa de scopes -> tools (qué scope necesita cada tool).
- Registro en Claude Code: `claude mcp add govgenai -- uv run mcp run mcp_server/server.py`
  (con las env vars). Ejemplo de sesión: redactar una plantilla y publicarla con confirm.
- Seguridad: HITL por aprobación de tool calls, escritura gated, PAT revocable, sin acceso a server/app.
- Referencia de toolset completa (resources + tools de MCP.2/MCP.3/MCP.4).

## Tests (mínimo 4) — mcp_server/tests/test_chat_tool.py (respx)
- test_chat llama al endpoint de chat con el mensaje y devuelve respuesta + citas.
- escritura/uso sin scope chat:test -> ScopeError.
- 404 chatbot inexistente -> error legible.
- doc smoke: el README/MCP_SERVER.md existe y lista los tools (test de presencia opcional).

## Verificación de integración (manual, sin .bat)
Documentar en la respuesta los pasos para registrar el servidor en Claude Code con un PAT
real emitido desde la UI (AUTH.4) y ejecutar test_chat contra un chatbot existente.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; `docs/MCP_SERVER.md` completo; instrucciones de `claude mcp add` en la respuesta. **Cierra el Bloque MCP.**

---

**Objetivo de la Fase**: Empaquetar el sistema completo para que cualquier institución pública pueda desplegarlo con un solo comando, sin depender de servicios de pago ni de conocimientos avanzados de infraestructura.

**Dependencias**: Fases 1-10 (sistema completo funcional)

**Conceptos clave**:
- **Docker Compose "One-Click"**: Un único archivo levanta todo el stack (Backend, Frontend, BD, MinIO, Ollama).
- **Variables de entorno documentadas**: Cada parámetro con comentarios explicativos para facilitar la adaptación.
- **Script de inicialización**: Automatiza migraciones, creación de superusuario y carga de datos de ejemplo.

---

### Prompt 11.1 - Generador de Configuración (.env.example)

**Modelo sugerido**: **Sonnet** — generador de plantillas .env con comentarios didácticos.

**Objetivo**: Crear un script de configuración inicial que genere un archivo `.env` completo y autodocumentado.

**Instrucciones**:

```
Crea un script de configuración inicial que genere un archivo `.env` completo. Debe incluir comentarios didácticos para que un técnico de otra institución sepa exactamente dónde poner su URL de Oracle, sus claves de modelo o su configuración de SSO. Incluye una sección de 'Modo Local' para funcionar 100% sin servicios de pago (usando Ollama para el LLM y MinIO para el almacenamiento).

SECCIONES DEL .env:
- # === BASE DE DATOS ===
- # === AUTENTICACIÓN SSO (OIDC/SAML) ===
- # === MODELOS DE LENGUAJE (elegir uno) ===
  - Opción A: Google Vertex AI
  - Opción B: OpenAI
  - Opción C: Local (Ollama) — sin coste
- # === ALMACENAMIENTO DE ARCHIVOS ===
  - Opción A: Google Cloud Storage / AWS S3
  - Opción B: MinIO (local, sin coste)
- # === CONECTIVIDAD INSTITUCIONAL (MCP) ===
```

---

### Prompt 11.2 - Docker Compose de Producción "One-Click"

**Modelo sugerido**: **Sonnet** — YAML de Compose + perfiles dev/prod. Trabajo declarativo.

**Objetivo**: Diseñar un archivo `docker-compose.prod.yml` que levante todo el stack con un solo comando.

**Instrucciones**:

```
Diseña un archivo `docker-compose.prod.yml` que levante TODO el stack:

1. El Backend (FastAPI).
2. El Frontend (React ya compilado en Nginx).
3. La Base de Datos (PostgreSQL + pgvector).
4. Un servicio de MinIO (para no depender de Google Cloud Storage).
5. Un servicio de Ollama opcional para correr modelos locales.

Todo debe estar conectado en una red interna segura. Añadir healthchecks para cada servicio y un volumen persistente para la base de datos y MinIO.

| Componente | Opción Cloud (GCP/Azure) | Opción Autoinstalable (Local) |
|------------|--------------------------|-------------------------------|
| **Cerebro (LLM)** | Vertex AI / OpenAI | Ollama / Llama 3 |
| **Archivos** | GCS / S3 | MinIO (Docker) |
| **Identidad** | Google Auth | Keycloak / LDAP |
| **Despliegue** | Terraform / Kubernetes | Docker Compose |
```

---

### Prompt 11.3 - Script de Inicialización y Semillas

**Modelo sugerido**: **Sonnet** — script de bootstrap + seed data. Patrón script + ORM.

**Objetivo**: Automatizar completamente la primera instalación del sistema.

**Instrucciones**:

```
Crea un script `setup.sh` que automatice la primera instalación:

1. Verificar los requisitos del sistema (Docker instalado, puertos 80/443/5432 libres).
2. Ejecutar las migraciones de base de datos (Alembic).
3. Crear el primer usuario 'SuperAdmin' interactivamente.
4. Cargar un 'Chatbot de Ejemplo' con prompts básicos de bienvenida en los tres idiomas (es, ca, en).
5. Mostrar un resumen de la instalación con las URLs de acceso al frontend y al panel de administración.

CRITERIOS DE ACEPTACIÓN:
- El script debe ser idempotente: ejecutarlo dos veces no debe duplicar datos.
- Debe funcionar tanto en Linux como en macOS.
```


---

# COMPLECIÓN DE FASE 1 — Bloques nuevos (planificados 2026-07-11)

> Bloques añadidos a partir de la valoración de `docs/VALORACION_PROYECTO.md` (aprobada por el usuario).
> Todos los prompts son **autocontenidos** y siguen el ciclo TDD RED → GREEN.
>
> **Orden de ejecución recomendado** (se inserta sobre el cursor actual, 11.x):
>
> ```
> Bloque ROL  →  Fase 11 (11.1–11.3)  →  Bloque SEC  →  Bloque CAL  →  Bloque ING.0  →  Deploy GCP (D.1–D.5)
> ```
>
> **Justificación del orden**:
> - **ROL primero**: el renombrado de roles es transversal y toca los mismos modelos de autenticación que `SEC.1`/`SEC.2`. Hacerlo antes evita trabajo doble y evita que Deploy (D.x) arrastre nomenclatura vieja.
> - **SEC antes de Deploy**: son fallos que, desplegados, quedarían públicos. Es bloqueante de `D.1`.
> - **CAL e ING.0** se cierran antes de abrir el repositorio bajo AGPLv3 (deuda de reglas del proyecto + corpus real del piloto).
>
> **Nota sobre `D.1`/`D.2`**: la autenticación pública del widget por API key (M1 de la valoración) ya está cubierta por `D.1`; la migración de secretos a Secret Manager (parte de A3) ya está en `D.2`. El bloque SEC **no los duplica** y asume que se ejecutan en Deploy. La **rotación** de las credenciales actualmente en `.env` (A3) es una acción de operaciones, no un prompt de código: hágase al migrar a Secret Manager.

---
