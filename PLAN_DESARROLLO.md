# Plan de Desarrollo: Gov Gen AI Platform
## Integración AI Agents Hub + AutomatIA

*Última actualización: 2026-04-24 | Estado: Fases TDD 0-8 completadas; próxima Fase 9 (Frontend React)*

---

## Situación actual (2026-04-24)

Repositorio `gov-gen-ai-platform` en GitHub (ModestoFabra), monorepo con:

- `server/` — FastAPI sobre PostgreSQL + pgvector; módulos `automation/` y `agents_hub/` operativos; JWT real; Docker multi-stage CPU-only; CI/CD en GitHub Actions; observabilidad LangFuse; servicio de feedback.
- `client_app/` — Cliente NiceGUI legacy, pendiente de migración progresiva al server y al frontend React (ver Fase 4C y Fase 6). El agente ligero de ejecución local (thin client) aún no existe; se creará en Fase 5.
- `frontend/` — **Aún no creado**. Scaffolding en la próxima Fase 1 del plan (equivale a Fase 9 del PLAN_TDD_DETALLADO).

**Estado por fase TDD** (ver `PLAN_TDD_DETALLADO.md` para el detalle):

| Fase TDD | Contenido | Estado |
|---|---|---|
| 0 | Infraestructura heredada de AutomatIA | ✅ |
| 1 | Auth JWT | ✅ 2026-04-22 |
| 2 | Base de datos + pgvector + retriever híbrido | ✅ 2026-04-23 |
| 3 | Ingestión Docling | ✅ 2026-04-23 |
| 4 | Agente LangGraph + RAGAS + HITL | ✅ 2026-04-23 |
| 5 | API endpoints chat SSE + export PDF/MD | ✅ 2026-04-23 |
| 6 | Tests E2E + CI/CD | ✅ 2026-04-23 |
| 7 | Docker multi-stage + docker-compose prod | ✅ 2026-04-23 |
| 8 | LangFuse + FeedbackService | ✅ 2026-04-23 |
| 9 | Frontend React (Admin Hub + Widget + Migración NiceGUI) | ⏳ Pendiente |
| 10 | Sistema de temas y panel de IA | ⏳ Pendiente |
| 11 | Autoinstalación | ⏳ Pendiente |
| 12 | Gestor de Expedientes | ⏳ Pendiente (se ejecuta bajo la Fase 7 de este plan, ampliada con Analista/Validador/UJI/G400) |
| 13 | Privacidad y anonimización reversible NER (Zero-Knowledge) | ⏳ Pendiente (Fase 6.1 de este plan) |
| 14 | Sandbox distribuido Edge ↔ Thin-client | ⏳ Pendiente (Fase 5.4–5.5 de este plan) |
| 15 | RunManifest + AuditService + Script Registry unificados (IA Frugal) | ⏳ Pendiente (Fase 6.2–6.4 de este plan) |
| 16 | Determinista-first + Fábricas como nodos LangGraph | ⏳ Pendiente (Fase 6.5 + Fase 7.E2.6 de este plan) |
| 17 | Agente Analista + base vectorial de normativa | ⏳ Pendiente (Fase 7.E2.5 de este plan) |
| 18 | Bridges semánticos ampliados (multi-contexto) | ⏳ Pendiente (Fase 6.6 de este plan) |
| 19 | Adaptadores UJI + Gestión 400 + capa ENI/ENS | ⏳ Pendiente (Fase 7.E5 de este plan) |
| 20 | Accesibilidad WCAG 2.2 AA + admin conversacional | ⏳ Pendiente (Fase 8 de este plan) |
| 21 | RPA web (diferido a v2) | ⏳ Fuera del alcance v1 (Fase 9 de este plan) |

**Documentos de referencia:**
- `Descripción y funcionalidades.md` — Visión funcional GovGenAI (malla agéntica, PMDS, zero-knowledge, RunManifest, IA frugal)
- `Arquitectura.md` — Arquitectura funcional del AI Agents Hub
- `modulo_AI_agents-hub.md` — Plan de integración Hub + AutomatIA (decisiones adoptadas)
- `ARCHITECTURE_old.md` — Arquitectura técnica de AutomatIA (GovGenAI)
- `PLAN_TDD_DETALLADO.md` — Plan TDD detallado del Hub (prompts atómicos por fase)

---

## Decisiones adoptadas

1. **Arquitectura servidor-first**: Todos los módulos en el servidor FastAPI. NiceGUI reemplazado por React + agente de ejecución local ligero (sin UI), siguiendo el patrón GitLab Runner.
2. **Monorepo**: Un solo repositorio GitHub con `server/`, `frontend/` y `client_app/` (agente local).
3. **Nuevo repositorio GitHub** (no branch de automatia, ya que no hay git previo y el alcance cambia sustancialmente).
4. **Dual-license**: AGPLv3 para instituciones públicas / Licencia comercial para partners.
5. **Frontend**: React + Vite + TypeScript + Tailwind CSS + **shadcn/ui** + i18next (CA/ES/EN). Panel admin unificado (Hub + Automatización + Plataforma); widget embebible como bundle independiente (Vite library mode).
6. **pgvector**: Introducido en el sprint de Infraestructura Hub, sin esperar a necesitarlo en Automation.
7. **Auth**: Migrar de `X-License-Key` + Bearer email a JWT real en Fase 0; OIDC/SAML en Q2 2026.
8. **MCP Client**: Implementado una sola vez, compartido por Automation y Hub.
9. **Topología 2 nodos (v1)**: Edge node (institución, on-prem o cloud institucional) con server FastAPI + PostgreSQL/pgvector + MinIO + LLM gateway, y Thin client (estaciones del tramitador) sin UI que ejecuta scripts firmados en sandbox. Sin arquitectura multi-tier cloud-edge clásica hasta v2.
10. **Servicios legacy se migran, no se reimplementan**: Privacidad (anonymizer), sandbox, manifest, audit, script registry, fábricas deterministas y bridges existen en `client_app/` con tests y se migran al server reutilizando código + tests. Aplica la regla de CLAUDE.md: migración = código nuevo en server + borrado total del legacy.
11. **Alcance v1 de integración con tramitación**: Adaptadores para dos sistemas: plataforma propia UJI y Gestión 400 (opensea). Capa transversal obligatoria ENI (DIR3, eEMGDE, CSV, formatos de evidencia) y ENS (categorización, controles). El `AdaptadorOracle` genérico previsto antes queda descartado.
12. **Privacidad scoped**: Anonimización reversible NER se aplica a expedientes y automatización. No se aplica al chatbot informativo con información pública.
13. **RPA web diferido a v2**: Playwright y `web_watcher` no se migran al thin client en v1. Si un flujo crítico del piloto lo exige, se despliega un worker Playwright dedicado en el Edge node.

## Decisiones pendientes

1. **Nombre del repositorio/plataforma**: ¿`gov-gen-ai-platform`, `automatia-hub`, u otro? Afecta URLs, marca y README.
2. **Visibilidad inicial del repo**: AGPLv3 implica publicarlo para cumplir la subvención. ¿Desde el primer día o tras el piloto (sep 2026)?
3. **Proveedor OIDC para fase inicial**: ¿Keycloak institucional ya disponible, o JWT propio hasta Q2?
4. **Prioridad de arranque**: ¿Frontend (demo visual para stakeholders) o Hub backend (chatbot funcional)?

---

## Estructura objetivo del repositorio (monorepo)

```
gov-gen-ai-platform/
├── server/                         # FastAPI — dual-license AGPLv3/Comercial
│   ├── app/
│   │   ├── modules/
│   │   │   ├── automation/         # Renombrado desde brain/ (existente)
│   │   │   └── agents_hub/         # NUEVO — RAG, LangGraph, chatbots
│   │   ├── core/                   # Auth, LLM gateway, tenancy, MCP (extender)
│   │   └── api/v1/                 # Routers (extender)
│   └── migrations/                 # Alembic (nuevo)
├── client_app/                     # Agente de ejecución local (sin UI)
├── frontend/                       # NUEVO — React + Vite (MIT)
│   └── src/
│       ├── widget/                 # Chatbot público embebible (iframe)
│       ├── agent/                  # Modo agente expandido (Dropzone, live preview)
│       ├── admin/                  # Panel admin hub + plataforma
│       └── automation/             # UI flujos/scripts (reemplaza NiceGUI)
└── shared/                         # Tipos y contratos compartidos
```

---

## Lo que NO hay que construir de cero (herencia de AutomatIA)

| Componente | Ubicación actual | Estado |
|---|---|---|
| LLM Gateway multi-proveedor (BYOK) | `server/app/services/ai_brain.py` | Operativo |
| Multi-tenancy Admin/Partner | `server/app/database/models` + `api/deps.py` | Operativo |
| Billing engine | `server/app/services/billing_engine.py` | Operativo |
| Dynamic prompts | `server/` | Parcial — extender para Hub |
| TDD framework + tests | `server/tests/` | Operativo |
| Docker + FastAPI async | `server/` | Operativo |

El Hub se construye **encima** de esta base, sin duplicar infraestructura.

---

## Hoja de ruta por fases

### FASE 0 — Git, repositorio e infraestructura base
*Duración estimada: 1 semana*

| ID | Tarea | Detalle |
|---|---|---|
| ~~0.1~~ | ~~Inicializar git~~ ✅ | `git init`, `.gitignore`, dos ficheros `LICENSE` (AGPLv3 server, MIT frontend) |
| ~~0.2~~ | ~~Crear repositorio GitHub~~ ✅ | Nuevo repo `gov-gen-ai-platform` (ModestoFabra), push inicial |
| ~~0.3~~ | ~~Docker Compose unificado~~ ✅ | `docker-compose.yml` con PostgreSQL+pgvector y MinIO. Pendiente: `docker compose up` tras instalar Docker Desktop |
| ~~0.4~~ | ~~Alembic~~ ✅ | `alembic.ini` + `migrations/env.py` listos. Pendiente: `alembic revision --autogenerate` + `upgrade head` tras levantar PG |
| ~~0.5~~ | ~~Renombrar `brain/` → `automation/`~~ ✅ | Módulo renombrado, todos los imports actualizados, legacy eliminado |
| 0.6 | Auth JWT | Migrar de cabecera `X-License-Key` + Bearer email a JWT estándar (base para OIDC/SAML) |

**Criterio de éxito**: `docker compose up` levanta server sobre PostgreSQL; todos los tests existentes pasan.

---

### FASE 1 — Scaffolding Frontend React + Vite
*Duración estimada: 1 semana*

| ID | Tarea | Detalle |
|---|---|---|
| 1.1 | Crear `frontend/` | `npm create vite@latest frontend -- --template react-ts` |
| 1.2 | Stack base | Tailwind CSS + **shadcn/ui**, React Router v6, i18next (CA/ES/EN), @tanstack/react-query, react-hook-form + zod |
| 1.3 | Auth frontend | JWT + interceptores Axios, rutas protegidas por rol (Admin, Partner, EndUser) |
| 1.4 | Panel Admin unificado (esqueleto) | Sidebar seccional: Hub / Automatización / Plataforma; layout conectado al server |
| 1.5 | CI/CD básico | GitHub Actions: lint + tests en cada push a main |

**Stack completo**:
```
Vite + React + TypeScript
Tailwind CSS + shadcn/ui (componentes accesibles sobre Radix UI)
@tanstack/react-query    → estado del servidor (fetch, cache, invalidación)
@tanstack/react-table    → tablas de datos
react-hook-form + zod    → formularios con validación
recharts                 → gráficas en informes
i18next + react-i18next  → CA / ES / EN
```

**Criterio de éxito**: Frontend arranca con login funcional conectado al server FastAPI existente.

---

### FASE 2 — Infraestructura Hub
*Duración estimada: 1 semana | Sprint "Infraestructura Hub" (Abril 2026)*

| ID | Tarea | Detalle |
|---|---|---|
| 2.1 | pgvector | Migration Alembic: `CREATE EXTENSION IF NOT EXISTS vector` |
| 2.2 | Schema Hub | Tablas: `chatbots`, `knowledge_bases`, `documents`, `document_chunks` (embedding `vector(1024)`), `conversations`, `messages`, `feedback_ratings`, `ragas_evaluations` |
| 2.3 | EmbeddingService | Servicio compartido BGE-M3 — reutilizable también por Automation |
| 2.4 | Docker Compose | Actualizar si se añaden dependencias nuevas |

```
Schema existente (AutomatIA)       Nuevas tablas (Hub)
────────────────────────────       ───────────────────
clients                            chatbots
partners                           knowledge_bases
users                              documents
llm_configs           ──────────►  document_chunks + vector (pgvector)
prompts                            conversations
executions                         messages
...                                feedback_ratings
                                   ragas_evaluations
```

**Criterio de éxito**: Se pueden insertar y recuperar chunks vectoriales desde tests de integración.

---

### FASE 3 — Módulo Agents Hub Backend
*Duración estimada: 5-6 semanas | Sprint "Módulo Hub" (Mayo-Junio 2026)*

| ID | Tarea | Duración | Equivale a fase Hub original |
|---|---|---|---|
| 3.1 | Ingestor Docling (PDF + web con Playwright) | 1 semana | Fases 3.1-3.8 |
| 3.2 | Ingesta prioritaria de usuario (PDFs temporales) | 2 días | Fase 3.9 |
| 3.3 | Grafo LangGraph dual (chatbot / agente) | 1.5 semanas | Fases 4.6, 4.9, 4.11 |
| 3.4 | RAGAS evaluation service | 3 días | Fases 4.7-4.8 |
| 3.5 | API endpoints Hub | 1 semana | Fases 5.1-5.4 |
| 3.6 | Dynamic Prompts Hub | 2 días | Fase 4.10 |
| 3.7 | Model Selector Hub (perfil por chatbot) | 2 días | Fase 4.10 |

**Endpoints principales:**
```
POST   /hub/chat                    → conversación chatbot o agente
GET    /hub/chatbots                → listado de chatbots del partner
POST   /hub/admin/chatbots          → crear/configurar chatbot
POST   /hub/admin/knowledge-bases   → gestión de bases de conocimiento
POST   /hub/feedback                → valoración del usuario (estrellas)
GET    /hub/admin/ragas             → métricas de calidad
```

**Criterio de éxito**: El endpoint `/hub/chat` responde con RAG funcional sobre documentos ingestados.

---

### FASE 4 — Frontend completo (Hub, Widget, Automatización)
*Duración estimada: 6-8 semanas | Julio-Septiembre 2026*

Se ejecuta en cuatro bloques secuenciales. Ver Fase 9 del PLAN_TDD_DETALLADO.md para prompts detallados.

**Bloque 4A — Admin Hub** *(prioridad)*

| ID | Tarea | Usuarios | Detalle |
|---|---|---|---|
| 4A.1 | Setup shadcn/ui + i18n + auth context | Admin/Partner | Base del SPA; login conectado al server |
| 4A.2 | Layout unificado | Admin/Partner | Sidebar seccional: Hub / Automatización / Plataforma |
| 4A.3 | Hub > Chatbots | Partner | CRUD: listar, crear, editar, desactivar |
| 4A.4 | Hub > Clientes | Partner | CRUD clientes + asignación de chatbots |
| 4A.5 | Hub > Documentos | Partner | Upload, listado y borrado por chatbot |
| 4A.6 | Hub > Informes | Admin/Partner | Tabla interacciones, filtro puntuación, export |

**Bloque 4B — Widget y modo agente**

| ID | Tarea | Usuarios | Detalle |
|---|---|---|---|
| 4B.1 | Widget embebible | Ciudadanos anónimos | Bundle independiente (Vite library mode); iframe; bilingüe; sincronización idioma página host |
| 4B.2 | Chat SSE + feedback | Usuarios finales | Stream en tiempo real; valoración 1–5 estrellas |
| 4B.3 | Modo agente expandido | Personal identificado | Dropzone PDFs, live preview borrador, "Solicitar cambios" |

**Bloque 4C — Automatización (migración NiceGUI)**

| ID | Tarea | Usuarios | Detalle |
|---|---|---|---|
| 4C.0 | Guía transversal de separación de lógica | — | Reglas reutilizables para dividir código NiceGUI entre servidor FastAPI y estado React (aplica a 4C.1/4C.2/4C.3) |
| 4C.1a | Focus Mode React (LayoutContext + DrawerHub) | Partner/Admin | Replica el drawer de 3 pestañas (Configuración / Data Pills / Copilot) y el colapso del sidebar. Prerequisito de 4C.1 |
| 4C.1 | Automation > Flujos | Partner/Admin | Reemplaza vista NiceGUI de flujos; usa Focus Mode |
| 4C.1b | Refactor backend PDF extractor a Docling | — | Sustituye `pdfplumber` + `fitz` por Docling. Nueva API upload-first; borra `extraction_strategies.py` y `PdfReaderDual`. Prerequisito de 4C.2 |
| 4C.2 | Automation > PDF extractor | Partner/Admin | Reemplaza vista NiceGUI de extracción (UI sobre los contratos Docling definidos en 4C.1b) |
| 4C.3 | Automation > Scripts | Partner/Admin | Reemplaza vista NiceGUI de scripts |
| 4C.4 | Limpieza NiceGUI | — | Borrado módulo a módulo (ver CLAUDE.md) |

**Bloque 4D — Agente de ejecución local**

| ID | Tarea | Detalle |
|---|---|---|
| 4D.1 | `client_app/local_agent/` | Proceso sin UI; patrón GitLab Runner; WebSocket con el server |

**Sistema de temas (Fase 10, tras este bloque):**
```
Plataforma (defaults globales — Admin)
    └── Cliente (logo, colores corporativos — Partner)
            └── Chatbot (overrides por instancia: botón flotante, avatar — Partner)
```

**Criterio de éxito de Bloque 4A**: Panel admin operativo con CRUD de chatbots y documentos.
**Criterio de éxito de Bloque 4B**: Widget funcional embebible en página HTML externa.
**Criterio de éxito de Bloque 4C**:
- Las pantallas de flujos, extractor PDF y scripts funcionan en React contra el backend FastAPI.
- El extractor PDF corre sobre Docling en el servidor; `pdfplumber`, `fitz` y `PdfReaderDual` están eliminados del repositorio.
- `client_app/app/ui/` no contiene ningún fichero de UI (solo queda `client_app/local_agent/` como proceso sin UI).
- `grep -r "from client_app.app.ui" .` no devuelve coincidencias.

---

### FASE 5 — Auth OIDC/SAML + MCP Client + Thin client
*Duración estimada: 3-4 semanas | Junio-Julio 2026*

| ID | Tarea | Detalle |
|---|---|---|
| 5.1 | OIDC/SAML | Integración con proveedor institucional; modo agente requiere usuario identificado |
| 5.2 | MCP Client | Conexión segura con sistemas externos; implementación única compartida por Automation y Hub |
| 5.3 | Thin client (agente de ejecución local) | Proceso sin UI; patrón GitLab Runner; recibe jobs por WebSocket; ejecuta scripts Python firmados; reporta resultados. Sin Playwright (ver decisión 13) |
| 5.4 | Sandbox distribuido Edge ↔ Thin-client | Migrar `sandbox_worker.py` al thin client; mantener `safety_sandbox.py` (auditoría AST) en server. Contrato: server firma el script → thin client verifica firma + ejecuta en sandbox → devuelve resultado + manifest firmado |
| 5.5 | Emparejamiento seguro thin client ↔ Edge | Token de enrolment inicial, refresh de credenciales, registro de capacidades declaradas por el thin client; heartbeat; actualización remota |

**Criterio de éxito**: Un thin client instalado en una estación Windows/Linux ejecuta un script Python firmado recibido del Edge node, con aislamiento de red, FS y proceso, y devuelve un RunManifest firmado que el server puede verificar.

---

### FASE 6 — Migración de servicios legacy NiceGUI al server
*Duración estimada: 4-5 semanas | Julio-Agosto 2026*

Esta fase migra los servicios transversales de `client_app/` al server FastAPI. Todos los componentes existen con tests en el legacy; esta fase es **migración + integración**, no desarrollo nuevo. Aplica la regla de CLAUDE.md: al cerrar cada subtarea, el código legacy correspondiente debe estar eliminado y sin referencias en el repo.

| ID | Tarea | Origen legacy | Destino server | Detalle |
|---|---|---|---|---|
| 6.1 | Privacidad reversible (anonimización NER) | `app/modules/privacy/anonymizer.py` (1010 LoC), `app/services/anonymization_service.py`, `app/utils/pii_detector.py`, `app/services/privacy_guardian.py`, `app/services/screenshot_guard.py` | `server/app/core/privacy/` | Vault de mapeos pseudónimo↔real en Edge (cifrado at rest). Hook pre/post-LLM en grafo de expedientes y en automation. **No aplica al chatbot informativo.** Migrar tests `test_ner_upgrade`, `test_etl_anonymization_ia`, `test_rpa_anonymization`, `test_privacy_audit`, `test_privacy_consent` |
| 6.2 | RunManifest + AuditService unificados | `app/services/manifest_generator.py`, `manifest_signature_service.py`, `enterprise_audit_service.py`, `external_script_audit_service.py` | `server/app/core/manifest/` + `server/app/core/audit/` | Formato único de `run_manifest.json` y cadena de hash firmada válida para automation y expedientes. Reemplaza el AuditService scoped de la antigua Fase 6.E3. No aplica al chatbot informativo |
| 6.3 | Script Registry + IA Frugal | `app/services/script_library_service.py` (840 LoC), `flow_registry_service.py`, `script_generator_service.py`, `script_adaptation_service.py`, `custom_script_service.py`, `validation_loop.py` | `server/app/modules/automation/scripts/` | Tabla `scripts_aprobados` con hash + versión + tenant + etiqueta semántica. Endpoint de búsqueda por taxonomía (reuso directo). Métricas de reuso (% tareas resueltas sin LLM) expuestas al panel admin |
| 6.4 | Cache semántico pre-LLM (opcional) | — (ampliación sobre 6.3) | `server/app/modules/automation/scripts/semantic_cache.py` | Campo `intent_embedding` (bge-m3) sobre `scripts_aprobados`; búsqueda por similaridad antes de invocar LLM. **Evaluar en piloto**: si el Script Registry por taxonomía resuelve >80% de reuso, no se activa. Test A/B con métricas de la 6.3 |
| 6.5 | Determinista-first + Fábricas invocables | `app/services/deterministic_etl_service.py`, `deterministic_graphics_service.py`, `app/modules/factory/etl_factory.py`, `graphics_factory.py`, `report_factory.py`, `app/services/report_factory.py` | `server/app/modules/automation/factories/` | Fábricas expuestas como módulos invocables desde flujos y desde grafos LangGraph (Fase 7). Lógica "determinista por defecto, LLM si no encaja" preservada |
| 6.6 | Bridges semánticos ampliados | `app/services/bridge_creator.py`, `bridge_generation_service.py`, `library_bridge.py` | `server/app/modules/automation/bridge/` | Interfaz común reutilizable desde flujos, expedientes y adaptadores de tramitación (Fase 7). Detección de discordancias entre esquemas UJI ↔ Gestión 400 |
| 6.7 | Limpieza legacy post-migración | — | — | `grep -r` de referencias eliminadas; borrado de ficheros migrados de `client_app/`; ejecución completa de la suite de tests (server + frontend) |

**Criterio de éxito**: Todos los servicios listados operan desde el server, con sus tests verdes en `server/tests/`. `client_app/app/services/` y `client_app/app/modules/privacy|sandbox|factory` no contienen ningún fichero migrado. `grep -r "from client_app.app.services"` y `grep -r "from client_app.app.modules.privacy"` devuelven 0 coincidencias en el resto del repo.

---

### FASE 7 — Gestor de Expedientes con malla agéntica
*Duración estimada: 9-10 semanas | Agosto-Noviembre 2026*
*Prerequisitos: Fase 5 (OIDC/SAML, MCP, thin client) y Fase 6 (servicios migrados)*

Esta fase sustituye la antigua Fase 6. Añade la **especialización agéntica** descrita en `Descripción y funcionalidades.md` (Agente Analista, Fábricas como nodos, Agente Validador/Crítico) y reorienta los adaptadores a UJI + Gestión 400 con capa ENI/ENS.

| Sprint | Contenido | Duración | Prerequisito |
|---|---|---|---|
| E1 | Schema BD, CRUD expedientes, API base, AdaptadorNativo | 1 semana | Fase 2 (pgvector) |
| E2 | Motor LangGraph con checkpointing + nodos estándar (LLM, Script, Human, RPA-local, APIExterna, Notificación) | 2 semanas | Fase 3 (LangGraph Hub) |
| E2.5 | **Nodo Agente Analista + base vectorial de normativa** *(NUEVO)* | 1-1.5 semanas | E2 |
| E2.6 | **Nodo Fábrica + Nodo Validador/Crítico** *(NUEVO)* | 1 semana | E2 + Fase 6.5 + Fase 6.2 |
| E3 | Integración con RunManifest + AuditService unificados (Fase 6.2); endpoint `/informe` PDF; tests de cumplimiento RIA | 1 semana | Fase 6.2 |
| E4 | Frontend React: lista, detalle, bandeja de aprobaciones, configurador de tipos | 3 semanas | Auth OIDC/SAML, E2 |
| E5 | **AdaptadorUJI + AdaptadorGestion400 + capa ENI/ENS** *(REEMPLAZA AdaptadorOracle)* | 1.5-2 semanas | MCP Client (Fase 5), E2 |

**Detalle de sprints nuevos:**

- **E2.5 — Agente Analista + BD normativa**
  - KB vectorial `regulation` ingerida por Docling: BOE, DOGC, ordenanzas UJI, normativa autonómica y local relevante
  - Nodo LangGraph previo al enrutado que clasifica intención del tramitador e identifica normativa aplicable
  - Output del nodo alimenta al siguiente nodo (LLM o Script) como contexto + citas normativas
  - Tests: clasificación correcta en golden-set de peticiones, normativa devuelta con referencia trazable

- **E2.6 — Fábricas como nodos + Validador/Crítico**
  - Wrappers LangGraph para `etl_factory`, `graphics_factory`, `report_factory` (migradas en Fase 6.5) y para cualquier script aprobado en el Registry (Fase 6.3)
  - Nodo Validador intercalado antes del `NodoHuman`: invoca `external_script_audit` (Fase 6.2) + `validation_loop` (Fase 6.3) + heurísticas AST; etiqueta la propuesta como `segura | requiere_revisión | bloqueada`
  - Tests: el Validador bloquea código con llamadas a red/subprocess/exec; el humano nunca recibe scripts marcados como `bloqueada`

- **E5 — Adaptadores UJI + Gestión 400 + ENI/ENS**
  - Interfaz común `AdaptadorTramitacion` (Protocol): `consultar_expediente`, `crear_tramitacion`, `actualizar_estado`, `adjuntar_documento`, `publicar_resolucion`, `obtener_documentos`
  - `AdaptadorUJI`: cliente HTTP contra el API institucional de la Universitat Jaume I
  - `AdaptadorGestion400`: cliente contra el API público de opensea
  - Capa ENI transversal: resolvedor DIR3 + enriquecedor eEMGDE + generador/verificador CSV + empaquetador de evidencia
  - Capa ENS: política por tipo de expediente (categorización alta/media/baja) aplicada al sandbox + audit
  - Tests: flujo completo consulta → proceso → validación → publicación contra mock de cada adaptador; serialización ENI válida (schema XSD)

**Criterio de éxito global**: Un tipo de expediente configurable que lee datos de UJI o Gestión 400, pasa por el Agente Analista, invoca una Fábrica, es auditado por el Validador, se suspende en HITL, y al ser aprobado publica la resolución en el sistema origen con evidencia ENI y registro RIA completo.

---

### FASE 8 — Accesibilidad y admin conversacional
*Duración estimada: 2-3 semanas | Septiembre-Octubre 2026 | Transversal*

| ID | Tarea | Detalle |
|---|---|---|
| 8.1 | WCAG 2.2 AA transversal | Criterio de aceptación obligatorio en cada pantalla del Bloque 4A/4B/4C y en las pantallas de expedientes (Fase 7.E4). Audit inicial con axe DevTools |
| 8.2 | Tests automáticos a11y | `@axe-core/react` integrado en Vitest; Lighthouse CI en GitHub Actions con umbrales mínimos (a11y ≥ 95) |
| 8.3 | Reutilización de tests legacy | Migrar `client_app/tests/a11y/test_accessibility.py` como seed para el frontend nuevo |
| 8.4 | Consola conversacional de administración | Interfaz en lenguaje natural dentro del panel Admin que permite al partner decir *"crea un chatbot para el padrón que use el LLM local y lea estos PDFs"* y ejecutar la configuración. Usa el grafo del Hub con tools de administración (crear chatbot, asignar KB, subir documentos). Integrar en Fase 10 del PLAN_TDD |

**Criterio de éxito**: Lighthouse a11y ≥ 95 en todas las rutas del frontend; consola conversacional capaz de completar al menos 5 casos de configuración habituales sin que el admin toque un formulario.

---

### FASE 9 — RPA web (diferido a v2)
*Fuera del alcance del piloto v1*

Decisión documentada: ni `client_app/app/core/rpa_executor.py` (1049 LoC) ni `client_app/app/services/web_watcher_service.py` (878 LoC) se migran al thin client en v1. El peso de Playwright (~300-400 MB de navegadores + dependencias del SO) choca con el objetivo de thin client ligero.

**Durante v1 (piloto octubre 2026):**
- El código RPA web legacy queda intacto en `client_app/` pero **no se incluye en el empaquetado del nuevo thin client**.
- Documentado en README y CLAUDE.md como "módulo no soportado en v1".
- Si algún flujo crítico del piloto **requiere** web RPA, se despliega un **único worker Playwright centralizado** en el Edge node (Docker headless) que recibe los mismos jobs que el thin client recibiría.

**v2 (post-piloto):**
- Decisión entre (a) re-empaquetar Playwright en el thin client con instalador propio, o (b) mantener el worker centralizado en Edge.
- Depende de cuánta demanda real de web RPA aparezca durante el piloto.

---

## Calendario general

| Fecha | Hito |
|---|---|
| **Abril 2026** | Fase 0: Git + GitHub + Docker PostgreSQL + pgvector operativo ✅ |
| **Abril-Mayo 2026** | Fase 1: Frontend React scaffolding + Fase 2: Schema Hub ✅ |
| **Mayo-Junio 2026** | Fase 3: Módulo Hub backend (Docling, LangGraph, API) ✅ |
| **Julio-Agosto 2026** | Fase 4: Frontend Hub completo + Fase 4C migración UI Automation |
| **Junio-Julio 2026** | Fase 5: Auth OIDC/SAML + MCP Client + Thin client + Sandbox distribuido |
| **Julio-Agosto 2026** | Fase 6: Migración servicios legacy (privacidad, manifest/audit, registry, fábricas, bridges) |
| **Agosto 2026** | Paper enviado (cumplimiento difusión subvención) |
| **Agosto-Noviembre 2026** | Fase 7: Gestor de Expedientes con malla agéntica (Analista, Validador, Fábricas) + Adaptadores UJI/Gestión 400 + ENI/ENS |
| **Septiembre 2026** | Repositorio público bajo AGPLv3 en GitHub |
| **Septiembre-Octubre 2026** | Fase 8: Accesibilidad WCAG 2.2 AA + admin conversacional (transversal) |
| **Octubre 2026** | Piloto institucional v1: plataforma completa (Hub + Automation + Expedientes) en producción. Sin RPA web (Fase 9 diferida a v2) |

---

## Siguiente iteración (próximas 2 semanas, desde 2026-04-24)

Entrada en Fase TDD 9 — Frontend React (equivale a la Fase 1 de este plan más el Bloque 4A).

```
Semana 1 (2026-04-24 → 2026-05-01):
  Día 1-2  → Scaffolding frontend/ con Vite + React + TS + Tailwind + shadcn/ui
  Día 2-3  → i18next con locales es / ca / en (Prompt 9.2)
  Día 3-4  → Auth context JWT + rutas protegidas por rol (Prompt 9.3)
  Día 4-5  → Layout sidebar seccional (Hub / Automatización / Plataforma) (Prompt 9.4)

Semana 2 (2026-05-01 → 2026-05-08):
  Día 1-2  → Hub > Pantalla de Chatbots (Prompt 9.5)
  Día 3    → Hub > Pantalla de Clientes (Prompt 9.6)
  Día 4    → Hub > Pantalla de Documentos (Prompt 9.7)
  Día 5    → Hub > Pantalla de Informes (Prompt 9.8)
```

**Al cerrar estas dos semanas**: Bloque 4A del Admin Hub operativo end-to-end contra el server FastAPI ya funcional. A partir de ahí se decide si continuar con Bloque 4B (Widget + modo agente) o paralelizar con la Fase 5 (OIDC/SAML + thin client) si el piloto de octubre lo exige.

---

## Modelo de licenciamiento

```
┌──────────────────────────────┬──────────────────────────────────┐
│        AGPLv3 (libre)        │     Licencia Comercial           │
├──────────────────────────────┼──────────────────────────────────┤
│ Instituciones públicas       │ Partners comerciales             │
│ Auto-hosted / on-premise     │ Soporte y SLA garantizados       │
│ Sin soporte                  │ Integraciones premium            │
│ Contribuciones obligatorias  │ Uso en productos privativos      │
│ Cumple requisito subvención  │ Modelo de negocio para partners  │
└──────────────────────────────┴──────────────────────────────────┘
```

- `server/` → dual-license AGPLv3 / Comercial
- `frontend/` → MIT
- `client_app/` (agente local) → Apache 2.0 / MIT

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 async, uv |
| Orquestación agéntica | LangGraph |
| Base de datos | PostgreSQL + pgvector |
| Embeddings | BGE-M3 |
| Ingesta documentos | Docling (IBM) + Playwright (webs dinámicas) |
| Evaluación calidad | RAGAS |
| Migraciones | Alembic |
| LLM providers | Google Gemini, OpenRouter, OpenAI, Azure OpenAI, Ollama |
| Conectividad institucional | MCP (Model Context Protocol) |
| Frontend | React + Vite + TypeScript |
| Estilos | Tailwind CSS + CSS Custom Properties |
| i18n | i18next (CA/ES/EN) |
| Contenedores | Docker + Docker Compose |
| Almacenamiento objetos | MinIO (compatible S3) |
| CI/CD | GitHub Actions / Bitbucket Pipelines |
