# Servidor MCP de Gov Gen AI Platform

Servidor **MCP (Model Context Protocol)** que permite a un cliente como **Claude Code** autorar
plantillas de informe, configurar chatbots y probarlos, hablando con la API de la plataforma.
Cierra el bucle **configurar → probar → ajustar** desde una conversación, sin construir UI a
medida.

> Bloque MCP (MCP.1–MCP.4) del `planificacion/Plan_TDD_Fase1.md`. Diseño = **opción A** de
> [`docs/mcp.md`](mcp.md): un cliente HTTP local, no una superficie nueva en el server.

## Dos transportes, y no son intercambiables

| | **stdio** (MCP.1) | **streamable HTTP** (REG.4) |
|---|---|---|
| Quién lo usa | una persona en su máquina | varios clientes a la vez, por la red |
| De dónde sale el token | `GOVGENAI_PAT` del entorno | la cabecera `Authorization` de cada petición |
| Qué expone | plantillas, chatbots, chat de prueba | registro de actividad y anonimización |
| Cómo se arranca | `mcp run server.py` | `uvicorn http_server:app --factory` |

**El modelo de autenticación es la diferencia que importa.** En stdio, un proceso equivale a una
persona, así que un token en el entorno dice exactamente quién actúa. En un servicio remoto
multi-cliente, ese mismo token uniformaría a todos: mismos permisos, misma organización y mismo
rastro en el registro de actividad. Por eso el transporte HTTP **no admite** `GOVGENAI_PAT` y lo
exige por petición; hay un guardarraíl que impide reintroducirlo en el despliegue.

El transporte HTTP se despliega como servicio propio detrás del proxy inverso, en `/mcp`. Cómo se
conecta un cliente y cómo se comprueba tras desplegar está en
[`DESPLIEGUE_PROTOTIPO_GCP.md`](DESPLIEGUE_PROTOTIPO_GCP.md) §3.septies.

---

## 1. Propósito y arquitectura

```
Claude Code  ──stdio──►  mcp_server/ (FastMCP)  ──HTTPS + PAT──►  API Gov Gen AI
                          (cliente, sin estado)                   (FastAPI)
```

- El servidor MCP es **un cliente HTTP más** de la API (como el frontend): no
  importa nada de `server/app` ni cruza la frontera edge/cloud. Vive en
  [`mcp_server/`](../mcp_server/) como proyecto `uv` autocontenido.
- Transporte **stdio**: Claude Code lo arranca como subproceso y habla por
  stdin/stdout. No expone ningún puerto.
- Toda la autenticación es por **PAT** (Personal Access Token) revocable.

### Nota dev/prod (edge vs cloud)

En desarrollo (`DEPLOY_MODE=all`) el chat (**edge**) y la configuración de
plantillas/chatbots (**cloud**/edge) conviven en el mismo servidor, así que un único
`GOVGENAI_API_BASE_URL` cubre todas las tools. En despliegue real son **superficies
distintas**: `test_chat` apunta al **edge** (cliente), mientras que las tools de
chatbots son **cloud** (admin/partner) y las de plantillas, **edge**. Si edge y cloud
tienen URLs distintas, hoy se registran dos instancias del servidor MCP con
`GOVGENAI_API_BASE_URL` distinto (una por superficie).

---

## 2. Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `GOVGENAI_API_BASE_URL` | sí | URL base de la API, p. ej. `http://localhost:8000` |
| `GOVGENAI_PAT` | sí (**solo stdio**) | Personal Access Token (`pat_<prefix>_<secret>`) |
| `GOVGENAI_GRAPH_PROFILES_PATH` | no | Ruta a `GRAPH_PROFILES.md` (default `<repo>/docs/GRAPH_PROFILES.md`) |
| `GOVGENAI_MCP_ALLOWED_HOSTS` | sí (**solo HTTP**) | Valores admitidos de la cabecera `Host`, separados por comas. Sin ellos el transporte responde **421 a todo**: el SDK valida el `Host` contra esta lista para prevenir *DNS rebinding*, y detrás del proxy inverso ese `Host` es el del dominio, no `localhost` |
| `GOVGENAI_MCP_ALLOWED_ORIGINS` | no (**solo HTTP**) | Igual, para la cabecera `Origin` |

### Cómo emitir el PAT

Desde la UI del hub (Bloque AUTH, prompt AUTH.4): **`/hub/access-tokens`** →
"Crear token". Elige los **scopes** según lo que vayas a hacer (ver mapa abajo),
opcionalmente una caducidad, y **copia el token en claro** (se muestra una sola vez).
El token es revocable desde la misma pantalla.

> Recuerda: un **partner** no puede emitir el scope `chatbots:write` (la mutación
> in-place de chatbots en producción se reserva a admin; ver `docs/mcp.md` val. 2).

---

## 3. Mapa de scopes → tools

| Scope | Tools |
|---|---|
| `redaccion:templates:read` | `list_templates`, `get_template_spec`, `validate_template_draft` |
| `redaccion:templates:write` | `create_template`, `publish_template_version` |
| `chatbots:read` | `list_clients`, `list_chatbots`, `get_chatbot`, `get_corpus_stats`, `list_prompt_templates` |
| `chatbots:write` | `create_chatbot`, `update_chatbot`, `update_prompt_template`, `assign_child`, `unassign_child` |
| `chat:test` | `test_chat` |
| `chat:debug` | inspección del prompt final (`debug_bypass`) — enseña el system prompt entero |
| `chat:onbehalf` | preguntar **en nombre de otra persona** (cabecera `X-GovGenAI-Actor`) |

Emite el PAT con el conjunto mínimo de scopes para la tarea. Las tools de lectura no
necesitan scopes de escritura.

`chat:onbehalf` es el más delicado de los tres últimos: habilita que el portador del token
declare quién pregunta. Sin él, la cabecera se ignora **sin error** y todo queda atribuido al
dueño del token, que es lo que hace inservible un PAT robado para suplantar a nadie. Solo lo
necesita un cliente de confianza que atienda a varias personas —el Pipe de Open WebUI—; una
integración de una sola persona no debe llevarlo.

---

### Las tools del transporte HTTP (REG.4)

| Scope | Tools |
|---|---|
| `actividad:write` | `registrar_actividad` |
| `anonimizacion:use` | `detectar_pii`, `anonimizar_texto` |

Los dos scopes los puede emitir tanto un superadministrador como un administrador de
organización. `chatbots:write` es la excepción, y por un motivo concreto: muta un chatbot en
producción in-place. Registrar actividad añade metadatos y no muta nada.

**`registrar_actividad` no pide confirmación**, a diferencia de `update_chatbot`. Es una tool que
un agente llama de forma rutinaria; con una puerta delante, se dejaría de llamar y el registro
quedaría vacío — que es peor que una entrada de más. Y el contrato del evento **rechaza cualquier
campo de contenido**: mandar el prompt no lo registra, falla. El contrato campo a campo está en
[`REGISTRO_ACTIVIDAD_IA.md`](REGISTRO_ACTIVIDAD_IA.md).

## 4. Registro en Claude Code

```bash
claude mcp add govgenai \
  --env GOVGENAI_API_BASE_URL=http://localhost:8000 \
  --env GOVGENAI_PAT=pat_xxxxxxxx_yyyyyyyyyyyy \
  -- uv run --directory /ruta/al/repo/mcp_server mcp run server.py
```

- `--env` inyecta las variables en el subproceso del servidor MCP.
- `uv run --directory .../mcp_server` ejecuta dentro del proyecto del servidor (su
  propio venv). Alternativa equivalente: `uv run python server.py`.
- Verifica con `claude mcp list` y, dentro de Claude Code, pide listar los recursos
  `govgenai://...` o invocar `list_templates`.

### Ejemplo de sesión (autoría de plantilla)

1. Lee el contrato: recurso `govgenai://redaccion/template-schema`.
2. "Redacta un draft de plantilla GENERIC_REPORT con secciones X/Y/Z."
3. `validate_template_draft(draft)` → corrige hasta `ok: true`.
4. `create_template(draft, name="...", confirm=false)` → revisa el plan.
5. `create_template(..., confirm=true)` → crea la plantilla + versión 1.
6. Más tarde, nueva versión: `publish_template_version(template_id, spec, confirm=false)`
   (valida en dry-run) → `confirm=true` publica (append-only, nunca corrompe versiones).

### Ejemplo de sesión (configurar y probar un chatbot)

1. `get_corpus_stats(id)` → modo de retrieval recomendado según el corpus.
2. `update_chatbot(id, {"retrieval_mode": "...", "retrieval_top_k": ...})` con
   `dry_run=true` → revisa el **diff** actual→propuesta.
3. `update_chatbot(..., dry_run=false)` → aplica el cambio.
4. `test_chat(id, "pregunta de evaluación")` → respuesta + citas; ajusta y repite.

---

## 5. Seguridad

- **HITL por construcción.** El humano aprueba cada *tool call* en Claude Code. Además,
  toda escritura está *gated*: `create_template`/`publish_template_version`/
  `create_chatbot`/`update_prompt_template`/`assign_child`/`unassign_child` no
  persisten sin `confirm=true`, y `update_chatbot` es `dry_run=true` por defecto
  (devuelve el diff, no aplica). Esto cumple la regla HITL de
  `REDACCION_CONTRACT_FIRST.md` con el admin como aprobador.
- **PAT revocable y con scopes.** Cada token porta un techo de scopes por rol y puede
  revocarse al instante desde `/hub/access-tokens`. El servidor MCP nunca persiste el
  PAT: lo lee del entorno en cada arranque.
- **Versionado append-only de plantillas.** `publish_template_version` solo añade; una
  versión publicada jamás se muta.
- **Sin acceso a `server/app`.** El servidor MCP solo habla HTTP; no puede tocar la BD
  ni los módulos internos. Cualquier validación de negocio (límite 128K de
  `MD_LONG_CONTEXT`, jerarquía de routers, etc.) la aplica la API y el cliente la
  reporta como error legible (`ValidationError`/`ScopeError`/`AuthError`).

---

## 6. Referencia de toolset

### Resources

| URI | Contenido |
|---|---|
| `govgenai://redaccion/template-schema` | JSON Schema de `ReportTemplateSpec` |
| `govgenai://redaccion/profiles` | Perfiles de informe válidos |
| `govgenai://docs/graph-profiles` | `docs/GRAPH_PROFILES.md` |
| `govgenai://chatbots/enums` | Enums de config de chatbot |
| `govgenai://chatbots/schema` | `ChatbotCreate`/`ChatbotUpdate` (de `/openapi.json`) |

### Tools

**Plantillas de redacción (MCP.2)** — `list_templates`, `get_template_spec`,
`validate_template_draft`, `create_template`, `publish_template_version`.

**Configuración de chatbots (MCP.3)** — `list_clients`, `list_chatbots`,
`get_chatbot`, `get_corpus_stats`, `list_prompt_templates`, `create_chatbot`,
`update_chatbot`, `update_prompt_template`, `assign_child`, `unassign_child`.

**Chat de prueba (MCP.4)** — `test_chat(chatbot_id, message, lang?)`: lanza una
pregunta y devuelve `answer` + `sources` (consume el stream SSE del endpoint de chat).

Detalle de firmas y efectos en [`mcp_server/README.md`](../mcp_server/README.md).

---

## 7. Verificación de integración (manual, sin `.bat`)

Este bloque es integración MCP/CLI, no UI de navegador, así que no lleva `.bat`. Para
validar de extremo a extremo con un PAT real:

1. Arranca la plataforma (`docker compose up -d`) y asegúrate de que la API responde
   en `GOVGENAI_API_BASE_URL`.
2. Emite un PAT desde **`/hub/access-tokens`** con scopes `chat:test` (+ `chatbots:read`
   para inspeccionar). Copia el token.
3. Registra el servidor con el comando `claude mcp add` de la §4, usando ese PAT.
4. En Claude Code: `list_chatbots()` para obtener un `chatbot_id` existente.
5. `test_chat(chatbot_id, "¿Qué trámites puedo hacer?")` → debe devolver `answer` y
   `sources`. Si el PAT no tiene `chat:test`, la tool falla con `ScopeError` (403).
6. Revoca el PAT desde la UI y repite: la siguiente llamada debe fallar con `AuthError`.
