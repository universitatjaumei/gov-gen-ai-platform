# 🛠️ CONTRIBUTING — Manual de desarrollo de Gov Gen AI Platform

Normas obligatorias para evolucionar y mantener la plataforma. Aplican a todo colaborador,
humano o agente de IA.

> **Fuentes de verdad** (este manual las resume; no las sustituye):
> - `docs/Arquitectura.md` — **qué** es la plataforma y qué principios la rigen (módulos, roles, privacidad, frontera Cloud/Edge, stack). Decisiones estructurales.
> - `planificacion/PLAN_DESARROLLO.md` — **cuándo y en qué orden** se construye (3 Fases Funcionales, calendario).
> - `planificacion/Plan_TDD_Fase1.md` / `planificacion/Plan_TDD_Fase2.md` / `planificacion/Plan_TDD_Fase3.md` — **cómo** se construye cada pieza (prompts TDD Red/Green).
> - `CLAUDE.md` — **reglas operativas** para agentes (retirada de legacy, frontera edge/cloud, portabilidad, shell, migraciones). En caso de conflicto, **CLAUDE.md manda**.
> - `planificacion/PROJECT_STATE.md` — estado actual y cursor de cada plan.

---

## 🌐 Dónde trabajas: principal y fork

Antes de *cómo* se contribuye, **dónde**.

| Repositorio | Papel | Qué entra |
|---|---|---|
| GitHub — `ModestoFabra/gov-gen-ai-platform` | **Principal** (*upstream*) | Lo que sirve a cualquier organización que despliegue la plataforma. |
| El fork de cada organización que despliega | **Despliegue y desarrollo propio** | Su configuración, sus integraciones internas, y los desarrollos que responden a necesidades suyas. |

El proyecto nace de la actividad investigadora del grupo **INNOVAP** (Derecho Público e Innovación)
y está destinado a varias administraciones —con atención particular a las entidades locales—, no a
una sola institución. **La regla vale igual para todas, incluida la universidad donde nació**: no
hay fork privilegiado, y por eso aquí no se nombra ninguno. De ahí sale la única regla dura de esta
sección:

**Lo específico de una institución no entra en el principal.** Se queda en su fork y sube por
*pull request* sólo si se puede generalizar. Si las necesidades de una institución entraran directas
en el principal, el principal acabaría siendo el sistema de esa institución.

### Qué se puede generalizar (y sube), y qué no

| Sube al principal | Se queda en el fork |
|---|---|
| Un módulo nuevo, o una capacidad que cualquier organización pueda activar. | Configuración de la institución: organizaciones, chatbots, temas visuales, prompts propios. |
| Un arreglo de un defecto real, con su test. | Integraciones con sistemas internos que sólo esa institución tiene. |
| Una opción de configuración que hace parametrizable algo que estaba fijo. | Corpus, datos y credenciales. Nunca salen del fork ni del despliegue. |
| Mejoras de accesibilidad, i18n, rendimiento, seguridad. | Cambios que presuponen la estructura organizativa de una institución concreta. |

Antes de abrir un *pull request* hacia el principal, pregúntate si otra administración querría ese
cambio. Si la respuesta es «le daría igual», es material de fork; si es «lo necesita pero al revés»,
lo que sube es la **opción de configuración**, no la decisión.

### Cómo se prepara la contribución

- Se sincroniza con el principal antes de empezar, y se trabaja sobre rama, no sobre `main`.
- Se respeta todo lo de este manual: **TDD** (no hay PR sin tests), Conventional Commits, retirada
  del legacy, frontera edge/cloud y estándares técnicos.
- El *pull request* explica **qué problema resuelve para cualquier organización**, no sólo para la
  que lo envía.
- Nada de secretos, datos reales ni corpus institucional en el diff. Ver §6.

---

## 🎯 0. Pre-flight (obligatorio)

- **Entorno Python con `uv`.** Toda ejecución de backend, tests o scripts se hace vía `uv run …`. En Windows, **nunca** invoques `python` directamente (te redirige a la Microsoft Store); usa el ejecutor `uv`. Si añades dependencias, ejecuta `uv sync` antes de continuar.
- **Shell del proyecto: PowerShell 5.1.** El operador `&&` **no existe** y provoca error de parseo. Encadena con `;` o `; if ($?) { … }`. Usa rutas absolutas al cambiar de directorio (ver `CLAUDE.md` → "Reglas de comandos de shell").
- **Stack local**: `docker compose up -d` levanta PostgreSQL+pgvector, MinIO y el microservicio `script-sandbox`. Backend: `cd server; uv run pytest`. Frontend: `cd frontend; npm test`.
- **Dependencia de sistema (SSO SAML)**: el SP SAML usa `python3-saml`, que depende de `xmlsec` (libxml2 + libxmlsec1). En Windows el wheel de `xmlsec` ya las incluye; en imágenes Docker Debian/Ubuntu añade `libxml2-dev libxmlsec1-dev pkg-config` (apt) antes de `uv sync`.

---

## 🤖 1. Reglas para agentes de IA

- **Análisis previo obligatorio**: antes de proponer cambios, lee `docs/Arquitectura.md` (soberanía del dato, jerarquía de servicios, frontera Cloud/Edge) y `CLAUDE.md` (reglas duras). Localiza el cursor en `planificacion/PROJECT_STATE.md`.
- **Inyección de dependencias, no instanciación manual**: en el servidor FastAPI usa `Depends`. **No** instancies servicios a mano ni accedas a sus métodos privados a través de la frontera HTTP.
- **Autonomía con responsabilidad**: ejecuta cambios alineados con la arquitectura y reporta tras la ejecución. Si detectas código que viola los estándares, propón la refactorización.
- **Divide y vencerás**: descompón tareas complejas en pasos pequeños y verificables.
- **Actualiza `planificacion/PROJECT_STATE.md`** al cerrar cualquier prompt que avance un paso de un plan.

---

## 🧱 2. Estructura del monorepo

```
server/        FastAPI (AGPLv3) — modules/{automation,agents_hub,redaccion,expedientes}, core/, services/, api/, routers/, migrations/
frontend/      React + Vite + TS (MIT) — src/{admin,widget,agent,redaccion,shared}
client_app/    Agente de ejecución local (Thin Client, sin UI). El resto es legacy NiceGUI pendiente de retirada.
mcp_server/    Servidor MCP stdio (paquete uv autocontenido, sin imports de server/app)
shared/        Tipos y contratos compartidos
_legacy_nicegui/   Cuarentena de larga duración durante la migración (solo lectura; borrado final manual al cierre de Fase 1)
```

Si escribes código nuevo en `client_app/` fuera del agente de ejecución local, para y consulta si pertenece al servidor o al frontend.

---

## 🔄 3. Ciclo de trabajo (TDD + Git)

- 🔴 **RED**: escribe el test en la carpeta `tests/` correspondiente y comprueba que falla. No hay PR sin tests.
- 🟢 **GREEN**: implementa el mínimo necesario para pasar.
- 🔵 **REFACTOR**: limpia manteniendo los tests en verde.
- 💾 **COMMIT**: commit inmediato tras GREEN, con **Conventional Commits** (`feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`). Menciona qué tests pasan. **No** incluyas líneas `Co-Authored-By` de Claude.

---

## 💻 4. Estándares técnicos

- **Asincronía total**: prohibido I/O síncrono en el servidor. Usa `async/await`; envuelve librerías síncronas (Docling, LibreOffice, etc.) en `asyncio.to_thread`.
- **Tipado estricto**: type hints en todas las funciones (Python) y sin `any` implícito (TypeScript).
- **Contract-First (frontend)**: la única fuente de verdad de datos es el backend. Usa los tipos y hooks generados por **Orval** desde `openapi.json`; **prohibido** definir interfaces de datos a mano o hacer `fetch` crudo saltándose el cliente generado. Formularios con `react-hook-form` + `zodResolver` alineados al contrato.
- **SDUI / HATEOAS**: el frontend no conoce campos a priori ni calcula permisos. Renderiza formularios iterando el `ui_contract` del backend y botones iterando `acciones_permitidas`. Nada de `if (rol === …) mostrarBoton()`.
- **i18n obligatorio**: ningún string hardcodeado en la UI. Usa `i18next` con locales `ca` / `es` / `en` en `frontend/src/shared/i18n/`. (El antiguo `translations.json` de NiceGUI es legacy.)
- **Sin features no pedidas**: no añadas manejo de errores, validaciones, flags ni abstracciones para escenarios fuera de la tarea.
- **Migraciones**: cuando toques `server/migrations/versions/`, aplica la migración con `uv run alembic upgrade <rev>` (ver `CLAUDE.md`).

---

## 🚧 5. Frontera Edge/Cloud y desacoplamiento (muro de seguridad)

Regulado en runtime por `DEPLOY_MODE=cloud|edge|all`. Ver el detalle completo en `CLAUDE.md` → "Frontera Edge-Cloud".

- **Dos `DeclarativeBase`**: `HubConfigBase` (config, se sincroniza cloud→edge) y `HubOperationalBase` (solo edge). **Sin `relationship()` cross-base**; navega por `*_id` con query explícito.
- **Un módulo edge no importa de un módulo cloud.** La configuración se lee vía `ConfigProvider`, no importando modelos de config directamente.
- **`client_app/` no puede importar de `server/`.** El Thin Client se comunica con el servidor por API/WebSocket.
- **Etiqueta cada router nuevo** con `Deploy: cloud|edge|shared` en su docstring y regístralo en `_register_cloud`/`_register_edge`.

---

## 🔒 6. Seguridad y privacidad

- **Aislamiento multi-tenant**: cada consulta de datos de una Organización se filtra por el claim de organización del principal; ningún acceso cruzado sin rol global. Es una regla dura verificada por tests de aislamiento en CI.
- **Scripts generados por IA**: pasan por el `ScriptSecurityAuditor` (análisis AST) y se ejecutan en el **microservicio `script-sandbox`** (aislado, sin red, sin FS del host, no-root). El servidor no ejecuta código generado in-process.
- **Datos PII y anonimización**: los servicios edge entregan datos ya anonimizados al `model_factory` antes de cualquier LLM externo. En despliegue Edge, el Vault de identidades no sale del nodo institucional. No aplica al chatbot público de información pública.
- **Secretos por variable de entorno**: nunca hardcodees claves, DSN ni contraseñas. `DATABASE_URL` (async) y `DATABASE_URL_SYNC` (Alembic) solo desde env. En producción, Secret Manager.
- **Almacenamiento de ficheros de negocio**: siempre vía `StorageService` (`fsspec`), nunca `open()`/`shutil` directos a disco (rompe Cloud Run y acopla al SO).

---

## 🧹 7. Retirada de legacy (borra, no comentes)

- Una migración **no está completa** hasta retirar el código original. Sin código muerto, imports sin usar ni comentarios `# TODO: migrate`.
- **Caso A** (NiceGUI con migración activa): al cerrar el prompt GREEN, mover el fichero a `_legacy_nicegui/` manteniendo la ruta relativa. `_legacy_nicegui/` es **solo lectura** y cuarentena de larga duración; el borrado definitivo lo hace el usuario al cierre de la Fase 1.
- **Caso B** (código huérfano sin migración): borrar directamente. El historial de git es la fuente de verdad del pasado.
- Nada nuevo entra en `_legacy_archive/`. Sin shims de retrocompatibilidad ni alias `_old_*`.

Ver el procedimiento completo en `CLAUDE.md` → "Regla crítica: migración = código nuevo + retirada del legacy".
