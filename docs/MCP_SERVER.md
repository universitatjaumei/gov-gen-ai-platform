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
| `verificaciones:use` | `verificar_citas`, `consultar_vigencia`, `auditar_codigo`, `reglas_de_auditoria` |

Los tres scopes los puede emitir tanto un superadministrador como un administrador de
organización. `verificaciones:use` es **uno para los tres servicios** y no uno por servicio: son la misma capacidad —comprobar con la vara de la plataforma algo que se produjo fuera— y
partirlo obligaría a pedir tres permisos para un caso de uso. `chatbots:write` es la excepción, y por un motivo concreto: muta un chatbot en
producción in-place. Registrar actividad añade metadatos y no muta nada.

**`registrar_actividad` no pide confirmación**, a diferencia de `update_chatbot`. Es una tool que
un agente llama de forma rutinaria; con una puerta delante, se dejaría de llamar y el registro
quedaría vacío — que es peor que una entrada de más. Y el contrato del evento **rechaza cualquier
campo de contenido**: mandar el prompt no lo registra, falla. El contrato campo a campo está en
[`REGISTRO_ACTIVIDAD_IA.md`](REGISTRO_ACTIVIDAD_IA.md).

**Los campos del evento viajan en el esquema de la tool** (REG.7), con la descripción de cada uno:
qué formato lleva la marca de tiempo, que el hash es un SHA-256 y de dónde sacar los códigos de
`categorias_datos`. Se declaraba como un `dict` opaco, así que el cliente recibía `{"type":
"object", "additionalProperties": true}` —ni un nombre de campo, y encima prometiendo que cualquier
extra valía cuando el servidor los rechaza—. Un guardarraíl del lado del servidor comprueba que la
firma y el contrato no divergen; no puede vivir aquí porque este paquete no importa `server.app`.

### Las tools de verificaciones (VAS.4)

Prestan tres comprobaciones que la plataforma ya se aplica a sí misma, para que quien desarrolle
fuera herede la misma vara. Las tres son **deterministas**: la misma entrada da la misma salida.

| Tool | Qué contesta |
|---|---|
| `verificar_citas` | Si un texto cumple «ninguna afirmación sin fuente resoluble», con el texto ya corregido y el desglose de qué se degradó y qué perdió el enlace |
| `consultar_vigencia` | Si la plataforma pondría un aviso de vigencia sobre un documento del corpus, y **el texto del aviso** |
| `auditar_codigo` | El nivel de riesgo de un script, cada hallazgo con su línea, y si puede pasar a revisión humana |
| `reglas_de_auditoria` | La caja de herramientas: con qué se puede escribir código que pase |

Tres cosas que conviene saber antes de usarlas:

**No hay segunda implementación.** Cada una envuelve la función que usa el motor, con un test que
compara los dos veredictos. Así que lo que responden aquí es lo que el asistente haría con lo
mismo — que es el sentido de prestarlas.

**El texto no se guarda.** Ni la respuesta que se verifica ni el código que se audita tocan
registros ni base de datos. De la auditoría se conserva sólo el SHA-256.

**Sólo `auditar_codigo` deja evento** en el registro de actividad, con el hash y el nivel de
riesgo: auditar es un acto de gobernanza y tiene que constar. Verificar citas y consultar vigencia
son comprobaciones sin estado, y un evento por comprobación duplicaría el registro sin decir nada
nuevo.

### Ejemplo de sesión: auditar un script antes de compartirlo

Es el caso de la Instrucció 02/2026: un script de nivel 2 que **no** va a correr en la plataforma
—una automatización local de un servicio— pasa igualmente por la misma vara.

```
> Antes de subir este script al repositorio del servicio, pásalo por la auditoría de la
  plataforma y dime si algo no pasaría.

[reglas_de_auditoria]  → 16 módulos permitidos, 6 reglas, version_auditor 3f9c…
[auditar_codigo]       → CRITICAL
                         · forbidden-call, línea 12: llamada peligrosa 'eval()'
                         · module-not-whitelisted, línea 1: 'csv' no está en la lista blanca
                         code_sha256 9130c489…

El script no pasaría: el `eval()` de la línea 12 es crítico y no se acepta con una revisión
humana. El `import csv` de la línea 1 sí: es un hueco en la lista blanca y quien revise puede
aceptarlo mirándolo.

Queda constancia en el registro de actividad de tu organización, con el hash y el nivel.
```

Lo que **no** hace: ejecutar el script. La auditoría es estática; ejecutar es el sandbox, y eso
vive dentro de la plataforma.

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
