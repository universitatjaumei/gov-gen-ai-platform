# Instrucciones para agentes de programación

## Contexto del proyecto

Gov Gen AI Platform es el resultado de integrar **AI Agents Hub** (chatbots RAG, LangGraph) y **AutomatIA**
(automatización, scripts, RPA) en un monorepo. El plan de desarrollo completo está en `PLAN_DESARROLLO.md`.

El cliente NiceGUI (`client_app/`) está siendo migrado progresivamente al servidor FastAPI y al frontend React.
**El código NiceGUI es legacy y debe eliminarse** a medida que cada módulo quede cubierto en el nuevo sistema.

---

## Regla crítica: migración = código nuevo + borrado del legacy

Una tarea de migración **no está completa** hasta que se elimine el código original.
No dejes código muerto, imports sin usar, archivos vacíos ni comentarios `# TODO: migrate`.

### Definición de "migración completa" (checklist obligatorio)

Antes de cerrar cualquier tarea de migración, verifica y ejecuta cada punto:

- [ ] La nueva implementación tiene tests que pasan (`pytest` o equivalente)
- [ ] El endpoint o servicio nuevo está integrado y verificado end-to-end
- [ ] El archivo o módulo legacy correspondiente está **eliminado** (no comentado, no archivado)
- [ ] Los imports del legacy han sido eliminados de todos los ficheros que los referenciaban
- [ ] No quedan referencias al código eliminado en ningún fichero del proyecto (`grep -r` antes de cerrar)
- [ ] El `docker compose up` + suite de tests completa sigue pasando tras el borrado

---

## Normas generales de limpieza

**Borra, no comentes.**
Si el código ya no se usa, elimínalo. Los comentarios `# deprecated`, `# old version` o `# legacy`
son deuda técnica disfrazada. El historial de git es la fuente de verdad del pasado.

**Borra, no archives.**
El directorio `_legacy_archive/` existe por razones históricas. No añadas nada nuevo ahí.
Si hay algo en `_legacy_archive/` que ya esté migrado, bórralo también.

**Sin backwards-compatibility shims.**
No renombres variables a `_old_foo`, no re-exportes símbolos eliminados, no añadas
comentarios `# removed` donde había código. Si algo se elimina, se elimina limpiamente.

**Sin código muerto especulativo.**
No dejes funciones, clases o módulos "por si acaso se necesitan en el futuro".
Si no se usa ahora, no existe.

---

## Estructura de módulos y dónde vive cada cosa

```
server/app/modules/automation/   ← lógica de flows, ETL, PDF, scripts (migrado desde client_app)
server/app/modules/agents_hub/   ← RAG, LangGraph, chatbots, Docling
server/app/core/                 ← servicios compartidos: LLM gateway, auth, tenancy, MCP
frontend/src/automation/         ← UI de flujos y scripts (reemplaza vistas NiceGUI)
frontend/src/widget/             ← chatbot público embebible
frontend/src/agent/              ← modo agente expandido
frontend/src/admin/              ← panel admin hub + plataforma
client_app/                      ← SOLO agente de ejecución local (RPA, folder watcher)
                                    Todo lo demás aquí es legacy pendiente de migrar
```

Si estás escribiendo código nuevo en `client_app/` fuera del agente de ejecución local,
para y consulta si pertenece al servidor o al frontend.

---

## Estándares de desarrollo

- **TDD obligatorio**: escribe el test antes del código de producción. No hay PR sin tests.
- **Asincronía total**: prohibidos métodos síncronos para I/O en el servidor. Usa `async/await`.
- **Sin instanciar servicios manualmente**: usa inyección de dependencias (FastAPI `Depends`).
- **i18n obligatorio en el frontend**: ningún string hardcodeado en la UI. Usa `i18next`.
- **Sin features no pedidas**: no añadas manejo de errores, validaciones, flags ni abstracciones
  para escenarios que no están en la tarea actual.

---

## Frontera Edge-Cloud (preparación del despliegue híbrido)

El sistema se despliega en dos modos:

1. **Cloud-only** — toda la lógica corre en el servidor del partner/admin; los
   datos se anonimizan antes de enviarse al LLM. Protección de datos por contrato.
2. **Edge + Cloud** — la lógica operacional (RAG, grafos, ingesta, automation,
   tratamiento de expedientes) corre en un **edge node** dentro de la nube del
   cliente; el **cloud** (admin/partner) sólo conserva configuración
   administrativa y métricas anonimizadas. Requisito regulatorio estricto.

El mismo codebase sirve a ambos modos. Para que eso siga siendo cierto, respeta
**dos fronteras** a la vez: la de datos (modelos ORM) y la de aplicación
(routers y módulos). La línea base de este split se establece en los prompts
**9.6.5** (capa ORM, `ConfigProvider`, sync API) y **9.6.6** (`DEPLOY_MODE`,
clasificación de routers/módulos) del `PLAN_TDD_DETALLADO.md`.

### 1. Frontera de datos (modelos ORM)

Dos `DeclarativeBase` separadas:

- **`HubConfigBase`** → se sincroniza cloud→edge. Modelos: `HubClient`,
  `HubChatbot`, `HubLLMConfig`, `HubPromptTemplate`.
- **`HubOperationalBase`** → vive sólo en el edge. Modelos: `HubDocumentChunk`,
  `HubInteraction`, `HubIngestionJob`.

**Reglas duras**:

- **Sin `relationship()` cross-base**. Si un modelo operacional necesita un
  chatbot, consulta por `chatbot_id` con un query explícito — no navegues por
  `.chatbot`. Las FK con `ondelete="CASCADE"` se conservan; la navegación ORM
  no.
- **Los servicios edge no importan modelos de config directamente**. El acceso
  a configuración pasa por `ConfigProvider` (protocolo con `LocalConfigProvider`
  por defecto; `RemoteConfigProvider` llegará cuando se implemente la sync API
  real).
- **El router `edge_sync`** (`/api/v1/edge/config`, `/api/v1/edge/telemetry`)
  es la única superficie que ve ambos mundos.

### 2. Frontera de aplicación (routers y módulos)

Clasificación, regulada en runtime por `DEPLOY_MODE=cloud|edge|all` (default
`all`, comportamiento actual):

| Capa | Cloud (admin/partner) | Edge (cliente) | Compartidos |
|---|---|---|---|
| **Routers HTTP** | `auth_router`, `hub_chatbots_router`, `hub_clients_router`, `library_router`, futuros `/hub/prompts`, `/hub/themes` | `hub_chat_router`, `ingestion_router`, `hub_tasks_router`, `hub_feedback_router`, futuros `/automation/*` | `edge_sync_router` (servido por cloud, consumido por edge) |
| **Módulos lógica** | `services/prompt_service` (CRUD), gestión partners / billing | `agents_hub/agent/` (graph, task_runner, tools, hitl), `agents_hub/ingestion/`, `agents_hub/services/retriever`, `agents_hub/evaluation/`, **`modules/automation/` íntegro** | `core/auth`, `services/model_factory`, `services/embedding_service`, `services/config_provider` |

**Reglas duras**:

- **Un módulo edge no puede importar** desde un módulo cloud (ni routers ni
  servicios admin/billing/partners). La configuración se lee vía
  `ConfigProvider`.
- **Los grafos LangGraph, el task runner y los tools** son edge: no leen
  `HubChatbot` ni `HubPromptTemplate` directamente.
- **El módulo `modules/automation/` es edge**: factories, flows, ETL, PDF y
  scripts procesan documentos/expedientes del cliente. No importa routers
  cloud ni gestión admin.
- **Al registrar un router nuevo** en `main.py`, **etiquétalo** en su docstring
  (`Deploy: cloud|edge|shared`) y regístralo en la función `_register_cloud`,
  `_register_edge` o ambas.
- **La anonimización previa al LLM** es responsabilidad edge: los servicios
  edge entregan datos ya anonimizados a `model_factory`; el factory no
  anonimiza.

### Si dudas dónde va algo nuevo

Pregunta:

- ¿Toca datos del cliente final (conversaciones, documentos, expedientes,
  chunks, embeddings)? → **edge**.
- ¿Sólo toca configuración, prompts, chatbots, clientes, partners, billing,
  usuarios? → **cloud**.
- ¿Ambos? Probablemente hay que partir la responsabilidad en dos servicios.

Si violas estas reglas, bloqueas el despliegue edge. Para, reconsidera, o
razona en el PR por qué es inevitable.
