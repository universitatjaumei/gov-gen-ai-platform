## Bloque REG — La plataforma como registro de actividad IA y servicios hacia fuera (PENDIENTE, planificado el 2026-08-31)

> **Posición en orden de ejecución**: tras el **Bloque Deploy (D)**. REG.1–REG.3 y REG.5 podrían
> ejecutarse antes en local, pero REG.4 (MCP remoto) solo existe de verdad con el servidor
> accesible desde fuera, y partir el bloque no compra nada.

**Origen**: reunión con desarrollo del 2026-08-31 y su valoración en
`docs/EVOLUCIO_I_ASPECTES_PENDENTS.md`. Desarrollo planteó que la plataforma no podrá
actuar como registro de las actividades de IA que ocurren **fuera** de ella (Claude Cowork,
Copilot, agentes de terceros) y propuso exponer un servicio MCP o endpoints para que esos agentes
registren sus usos y consuman la anonimización. La valoración lo acepta con un matiz: no es una
re-arquitectura, es girar hacia fuera piezas que ya existen — el servidor MCP (Bloque MCP), los
PAT con scopes (AUTH.3) y el módulo de anonimización (`modules/redaccion/services/anonymization/`).

**Qué es y qué no es**: esto es **registro de gobernanza** — quién usó qué agente, con qué
finalidad, sobre qué categorías de datos — al servicio del AI Act (conservación de logs,
arts. 12 y 26) y del registro de actividades de tratamiento del RGPD (art. 30). **No** es trazado
técnico: el trazado token a token ya lo cubre Langfuse dentro de la plataforma y no se reconstruye.

**Decisiones tomadas en la valoración (revisables en la reunión, ver §Para la reunión del informe)**:
- **Auth**: se reutiliza el PAT con dos scopes nuevos (`actividad:write`, `anonimizacion:use`);
  la organización del evento se deriva del dueño del token. Un token de servicio no personal
  solo se añade si la reunión lo exige — sería un prompt más, no un rediseño.
- **Esquema del evento**: propio y mínimo, con nombres de campo mapeables a las convenciones
  semánticas OTel GenAI (documentado en REG.6). Adoptar el estándar entero arrastra campos de
  observabilidad que aquí no aplican.

**Reglas duras del bloque REG**:
- **Metadatos sí, payloads no.** El contrato del evento no tiene ningún campo de contenido y
  rechaza campos no declarados (`extra="forbid"`). Si un caso exige evidencia del contenido,
  `payload_hash` (SHA-256) — nunca el payload. El registro no puede convertirse en un segundo
  sitio donde viven los datos personales.
- **El servicio de anonimización no registra el texto** que recibe: ni en logs ni en BD, por
  construcción y con test.
- `mcp_server/` **sigue sin importar** `server/app`: cliente HTTP puro, como estableció MCP.1.
- Todo endpoint nuevo del bloque es **`Deploy: edge`** (datos del cliente final), etiquetado en
  el docstring y registrado en `_register_edge`.
- El módulo de anonimización **no se muda** de `modules/redaccion/`: dos consumidores edge no
  justifican la mudanza. Si aparece un tercero, se mueve entonces (y se dice en el PR).

---

### Prompt REG.1 (RED/GREEN) — El contrato del evento de actividad y su tabla

**Modelo sugerido**: **Sonnet** — el contrato quedó cerrado en la valoración; alcance acotado a
un modelo, una migración y su contrato Pydantic.

**Objetivo**: crear el contrato `ActividadIAEvent` y la tabla `hub_actividad_ia`
(`HubOperationalBase`, `__ambito__ = "organizacion"`), con migración Alembic aplicada.

**Contexto**: el evento es de gobernanza, no de observabilidad. `HubInteraction` no se toca ni se
sobrecarga: registra conversaciones internas y tiene otra forma (mensajes, feedback, veredictos).
La tabla nueva referencia a la organización por FK con el patrón del resto de tablas
operacionales; sin `relationship()` cross-base, como siempre.

**Instrucciones al agente**:
```markdown
# PROMPT REG.1 (RED/GREEN) — Contrato ActividadIAEvent + tabla hub_actividad_ia

## Contrato Pydantic (server/app/modules/agents_hub/... junto a los contratos existentes)
- ActividadIAEvent con model_config extra="forbid" y estos campos, todos sin contenido:
  - ocurrido_en: datetime (aware; lo declara el cliente)
  - actor: str(255) — identificador opaco del usuario en la herramienta externa
  - herramienta: str(100) — p. ej. "claude-cowork", "copilot", "cursor"
  - agente: str(255) | None — nombre del agente/bot concreto dentro de la herramienta
  - finalidad: str — descripción corta del uso declarado
  - modelo_usado: str(100) | None
  - categorias_datos: list[str] — categorías declaradas (p. ej. "datos_identificativos");
    lista libre, SIN Enum: es vocabulario, no estructura (misma regla que el corpus)
  - payload_hash: str(64) | None — SHA-256 hex, opcional
- Ningún campo de texto libre largo salvo finalidad; ningún campo llamado contenido,
  mensaje, prompt ni equivalente. Test que lo fija: extra="forbid" rechaza payload/content.

## Modelo ORM (operational_models.py)
- HubActividadIA en HubOperationalBase, __tablename__="hub_actividad_ia",
  __ambito__="organizacion".
- Columnas: las del contrato + id UUID pk, organizacion_id UUID FK (mismo patrón y
  ondelete que las tablas operacionales vecinas), registrado_en timestamptz
  server_default now(). categorias_datos como JSONB.
- Índices: organizacion_id, ocurrido_en, herramienta.

## Migración
- Alembic autogenerate + revisión manual; aplicar con uv run alembic upgrade <rev>.

## Tests (mínimo 6) — tests/modules/agents_hub/test_reg1_actividad_ia.py
- El contrato rechaza campos no declarados (extra="forbid"): payload, content, prompt.
- ocurrido_en naive -> error de validación (la lección de ACT.1: aware contra naive).
- El modelo declara __ambito__="organizacion" (el guardarraíl de MT.1 lo exige igualmente).
- Insert y lectura round-trip con categorias_datos como lista.
- payload_hash admite None y valida longitud 64 hex si viene.
- La migración deja la tabla con los índices declarados.
```

**Verificación**: suite del directorio + `tests/infra/test_suite_hygiene.py` verdes; `alembic
current` muestra la revisión; el inventario de `docs/MULTITENENCIA.md` actualizado con la tabla
nueva (lo exige su test).

---

### Prompt REG.2 (RED/GREEN) — El endpoint de registro y los dos scopes nuevos

**Modelo sugerido**: **Sonnet** — endpoint único sobre contrato ya definido; el patrón de scopes
está establecido en AUTH.3.

**Objetivo**: `POST /api/v1/actividad` (`Deploy: edge`) que persiste un `ActividadIAEvent`
autenticado por PAT con el scope nuevo `actividad:write`; añadir también `anonimizacion:use` al
catálogo (lo consume REG.3).

**Contexto**: catálogo de scopes en `server/app/core/auth/pat/scopes.py`, con techo por rol
(`_ROLE_SCOPES`). La organización del evento **no viene en el payload**: se deriva del principal
dueño del PAT, igual que acota el resto de la tenencia (`core/auth/tenancy.py`). Un agente
externo que registra actividad no elige en nombre de qué organización lo hace.

**Instrucciones al agente**:
```markdown
# PROMPT REG.2 (RED/GREEN) — POST /api/v1/actividad + scopes actividad:write y anonimizacion:use

## Scopes (core/auth/pat/scopes.py)
- ACTIVIDAD_WRITE = "actividad:write"; ANONIMIZACION_USE = "anonimizacion:use".
- Techo por rol: ambos emisibles por superadmin y admin.

## Router (server/app/routers/actividad_router.py — Deploy: edge, en _register_edge)
- POST /api/v1/actividad: recibe ActividadIAEvent, exige PAT con actividad:write,
  organizacion_id = la del dueño del token, 201 con {id, registrado_en}.
- Sin GET en este prompt (la lectura es REG.5). Sin rate limit propio: hereda el general.

## Tests (mínimo 7) — tests/api/test_reg2_registro_actividad.py
- 201 y fila persistida con la organización del dueño del PAT.
- PAT sin el scope -> 403; sin auth -> 401.
- JWT de sesión sin PAT -> 403 (la escritura es para clientes máquina; decisión del bloque).
- Campo extra en el payload (p. ej. "prompt") -> 422.
- organizacion_id en el payload -> 422 (no es un campo del contrato).
- Dos PAT de organizaciones distintas escriben en organizaciones distintas.
```

**Verificación**: suite de `tests/api` del fichero + higiene verdes; el endpoint aparece en
OpenAPI con `operation_id` explícito; `grep` de que el router está etiquetado `Deploy: edge`.
`test_sec96_controles_declarados_y_no_aplicados.py` sigue verde (el endpoint nuevo declara sus
controles).

---

### Prompt REG.3 (RED/GREEN) — La anonimización como servicio

**Modelo sugerido**: **Sonnet** — expone un servicio existente detrás de dos endpoints; la parte
delicada (no registrar el texto) está cerrada por regla del bloque.

**Objetivo**: `POST /api/v1/anonimizacion/spans` (detección) y `POST /api/v1/anonimizacion/replace`
(sustitución) sobre `PiiDetector.detect_spans` y el anonimizador existentes, scope
`anonimizacion:use`, sin persistir ni registrar el texto.

**Contexto**: `PiiDetector` (`modules/redaccion/services/anonymization/pii_detector.py`) ya
detecta spans en texto libre y degrada a regex si spaCy no carga; el anonimizador y las políticas
viven al lado. El router nuevo **importa el servicio donde está** (edge→edge, legal); no se muda.
Estos endpoints son la alternativa a que cada herramienta externa resuelva la PII por su cuenta.

**Instrucciones al agente**:
```markdown
# PROMPT REG.3 (RED/GREEN) — /api/v1/anonimizacion/spans y /replace

## Router (server/app/routers/anonimizacion_router.py — Deploy: edge, en _register_edge)
- POST /api/v1/anonimizacion/spans: {text: str(max 200_000)} -> {spans: list[PiiSpan]}.
- POST /api/v1/anonimizacion/replace: {text} -> {text_anonimizado, spans_aplicados}.
  Sustitución con la política por defecto; SIN parámetro de política en este prompt
  (no anticipar: se añade cuando un consumidor real la pida).
- Exigen PAT con anonimizacion:use (mismo patrón que REG.2). Stateless: nada a BD.

## La regla de oro, con test
- Ningún logger recibe el texto de entrada ni el anonimizado: test con caplog a nivel
  DEBUG que llama a ambos endpoints con un texto centinela ("SENTINELA_PII_123") y
  afirma que el centinela no aparece en ningún registro capturado.

## Tests (mínimo 8) — tests/api/test_reg3_anonimizacion_servicio.py
- spans detecta un DNI y un email de ejemplo (los patrones regex existentes).
- replace devuelve el texto sin el DNI original y con los spans aplicados.
- Texto > 200_000 -> 422.
- Sin scope -> 403; sin auth -> 401.
- El test del centinela en logs, para los dos endpoints.
- Nada persiste: recuento de filas de las tablas operacionales igual antes y después.
```

**Verificación**: suite del fichero + higiene verdes; los dos endpoints en OpenAPI; el test del
centinela pasa con `caplog` a DEBUG (es el test del camino bueno de la regla, no una guarda
defensiva sin vigilar).

---

### Prompt REG.4 (RED/GREEN) — El MCP remoto: mismo paquete, segundo transporte, token por petición

**Modelo sugerido**: **Opus** — transporte streamable HTTP nuevo en `mcp_server/` y cambio del
modelo de auth (de PAT-de-entorno a token por petición); decisiones que condicionan cómo se
despliega y quién puede conectarse.

**Objetivo**: extender `mcp_server/` con transporte **streamable HTTP** y un namespace nuevo de
tools (`registrar_actividad`, `detectar_pii`, `anonimizar_texto`) que llaman a los endpoints de
REG.2/REG.3 **con el token que presenta cada cliente conectado**, no con el de entorno.

**Contexto**: es la «opción B» que `docs/mcp.md` dejó anotada en 2026-06-06, con el caso de uso
que entonces faltaba. El stdio actual lee `GOVGENAI_PAT` de entorno porque es mono-usuario; un
MCP remoto multi-cliente debe propagar el `Authorization: Bearer` de cada petición entrante al
`ApiClient`, y sin token la tool falla con error legible, no con 500. El proceso se despliega en
la VM detrás del reverse proxy de D.4-VM (ruta `/mcp`), como servicio propio del Compose — sigue
sin importar `server/app`.

**Instrucciones al agente**:
```markdown
# PROMPT REG.4 (RED/GREEN) — mcp_server con streamable HTTP + namespace actividad/anonimizacion

## Transporte (mcp_server/)
- Segundo punto de entrada: servidor FastMCP con transporte streamable HTTP.
  El stdio existente no cambia y conserva GOVGENAI_PAT de entorno.
- Auth por petición: el Bearer de la petición MCP entrante se propaga al ApiClient
  de esa llamada. Sin token -> error de tool claro ("falta el PAT"), nunca 500.
- El paquete sigue sin importar server/app (grep limpio, como en MCP.1).

## Tools nuevas (mcp_server/tools/actividad.py)
- registrar_actividad(evento: dict) -> POST /api/v1/actividad. SIN gate confirm:
  registrar es append-only de metadatos, no muta nada (a diferencia de update_chatbot,
  cuyo gate existe porque muta producción in-place).
- detectar_pii(text: str) -> POST /api/v1/anonimizacion/spans.
- anonimizar_texto(text: str) -> POST /api/v1/anonimizacion/replace.
- Errores HTTP mapeados como en MCP.1 (401->AuthError, 403->ScopeError, 422->ValidationError).

## Despliegue
- Servicio en el docker-compose de la VM (D.4-VM) tras el reverse proxy, ruta /mcp.
  Anotarlo en el runbook de despliegue que D.4-VM haya dejado; no levantar nada aquí.

## Tests (mínimo 9) — mcp_server/tests/test_actividad_tools.py (respx)
- El Bearer de la petición entrante llega en Authorization al endpoint de la API.
- Dos clientes con tokens distintos -> cada llamada sale con su token (sin fugas entre
  peticiones concurrentes).
- Sin token -> error de tool legible, sin llamada HTTP.
- Cada tool llama a su endpoint y devuelve el payload mapeado.
- 403 del servidor -> ScopeError con el scope que falta en el mensaje.
- 422 -> ValidationError con el detalle del body.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; el servidor arranca en streamable
HTTP en local y un cliente MCP (p. ej. Claude Code con `claude mcp add --transport http`) lista
las tres tools; grep sin imports de `server/app`.

---

### Prompt REG.5 (RED/GREEN) — Leer y exportar el registro, acotado por organización

**Modelo sugerido**: **Sonnet** — lectura paginada con filtros sobre una tabla propia; el patrón
de acotación por tenencia está establecido.

**Objetivo**: `GET /api/v1/actividad` (paginado, filtros por herramienta y rango de fechas) y
`GET /api/v1/actividad/export` (CSV), para sesión JWT con rol admin/superadmin, acotados a la
organización del principal.

**Contexto**: la lectura es para personas (el panel), así que autentica la sesión JWT, no el PAT.
La acotación la decide `core/auth/tenancy.py`, como en el resto de listados. `Deploy: edge` — el
registro es dato operacional del cliente y se consulta donde vive.

**Instrucciones al agente**:
```markdown
# PROMPT REG.5 (RED/GREEN) — GET /api/v1/actividad + export CSV

## Endpoints (en actividad_router.py)
- GET /api/v1/actividad?herramienta=&desde=&hasta=&page=&size= -> página de eventos,
  orden ocurrido_en desc. Solo admin/superadmin; acotado a la organización del principal.
- GET /api/v1/actividad/export con los mismos filtros -> CSV (streaming), cabeceras con
  los nombres de campo del contrato.

## Tests (mínimo 7) — tests/api/test_reg5_lectura_registro.py
- Dos organizaciones sembradas: cada admin ve solo la suya (el test de MT de siempre).
- Filtros por herramienta y por rango de fechas.
- Orden y paginación estables (el desempate determinista que DET.1 exige a los listados).
- Rol user -> 403.
- El CSV abre con las cabeceras del contrato y contiene los eventos filtrados.
```

**Verificación**: suite del fichero + higiene verdes; contrato OpenAPI regenerado si cambió
(`openapi.json` + Orval, que REG.6 consume).

---

### Prompt REG.6 (RED/GREEN) — La vista del registro en el panel y el contrato documentado

**Modelo sugerido**: **Sonnet** — tabla con filtros sobre hooks Orval generados; el trabajo de
diseño ya está hecho en las vistas vecinas del admin.

**Objetivo**: página «Registro de actividad IA» en el panel admin (tabla paginada, filtros por
herramienta y fechas, botón de exportar CSV), i18n es/ca/en, y la documentación del contrato en
`docs/REGISTRO_ACTIVIDAD_IA.md`.

**Contexto**: hooks y tipos generados por Orval desde `openapi.json` (REG.5); `react-hook-form` +
`zodResolver` si hay formulario de filtros. Verificación en navegador por el agente, como manda
la metodología; el `.bat` humano del bloque queda para lo irreducible (probar el registro desde
una herramienta externa real con un PAT real).

**Instrucciones al agente**:
```markdown
# PROMPT REG.6 (RED/GREEN) — Vista admin del registro + docs/REGISTRO_ACTIVIDAD_IA.md

## Frontend (frontend/src/admin/)
- Página «Registro de actividad IA»: tabla paginada (ocurrido_en, herramienta, agente,
  actor, finalidad, modelo_usado, categorias_datos), filtros por herramienta y rango de
  fechas, botón que descarga el CSV del endpoint de export.
- Hooks Orval generados; ningún tipo duplicado a mano. i18n es/ca/en, cero strings
  hardcodeados.
- Tests de frontend: la tabla se construye desde la respuesta del hook (nada hardcodeado),
  los filtros disparan la query con los parámetros, el botón de export apunta al endpoint.

## Documentación (docs/REGISTRO_ACTIVIDAD_IA.md)
- El contrato del evento campo a campo, con el mapeo a las convenciones OTel GenAI
  (qué campo nuestro corresponde a qué atributo gen_ai.*, y cuáles no tienen equivalente
  a propósito).
- Cómo dar de alta un agente externo: emitir el PAT con los scopes, ejemplo curl del
  POST /api/v1/actividad y ejemplo de conexión MCP (streamable HTTP).
- La regla «metadatos sí, payloads no» y su porqué, para que un integrador no pida
  añadir el campo de contenido.

## Cierre
- Actualizar docs/mcp.md: la opción B deja de ser futurible; enlazar a este bloque.
```

**Verificación**: vitest verde (`--no-file-parallelism`); verificación en navegador con la
extensión de Chrome (tabla renderizada con datos sembrados, filtros funcionando, consola y red
limpias); `docs/REGISTRO_ACTIVIDAD_IA.md` existe y el enlace desde `docs/mcp.md` también.

---

---

### Prompts REG.7-REG.9 (añadidos el 2026-09-04, tras revisar el bloque con el usuario)

**De dónde salen.** Al cerrar el bloque, la pregunta fue si hace falta documentar lo que se puede
registrar y cómo, o si la conexión MCP ya intercambia esa información. Comprobándolo aparecieron
tres huecos, y los tres se cerraron aquí.

**REG.7 — La tool MCP declara el contrato.** `registrar_actividad` recibía `evento: dict`, así que
el esquema de `tools/list` era `{"type": "object", "additionalProperties": true}`: sin un nombre de
campo, y prometiendo que cualquier extra valía cuando el servidor los rechaza con 422. Se tipa la
firma con descripción por campo, y un guardarraíl **del lado del servidor** —`mcp_server/` no
puede importar `server.app`— comprueba que no divergen.

**REG.8 — El catálogo de categorías de datos.** `categorias_datos` es vocabulario abierto y no
había catálogo: si cada herramienta inventa sus códigos, el registro deja de poder agregarse, que
es para lo que existe. `GET /api/v1/actividad/categorias` sobre `hub_vocabulary_terms` con el eje
nuevo `categoria_dades`. **Se anuncia, no se impone**: el `POST` sigue aceptando cualquier código,
porque rechazarlo convertiría «esta categoría no está dada de alta» en «este uso de IA no queda
registrado», y los sin catalogar se ven en el panel tal como llegaron.

**REG.9 — El rechazo se explica.** «Extra inputs are not permitted» dice qué y no dice por qué, y
quien lo lee concluye razonablemente que al esquema le falta un campo. Un `model_validator` en
`mode="before"` distingue dos malentendidos —mandar contenido y mandar `organizacion_id`— y en los
dos casos señala la salida y el documento.
