# Plan de Desarrollo: Gov Gen AI Platform
## Integración AI Agents Hub + AutomatIA

*Fecha: 2026-04-22 | Estado: Pendiente de arranque*

---

## Situación de partida

El proyecto existe localmente en esta carpeta **sin git inicializado**. Contiene:

- `server/` — FastAPI funcional con módulo `brain/` (automation), servicios de billing, auth por cabecera, multi-tenancy partner/admin, LLM gateway multi-proveedor
- `client_app/` — Cliente NiceGUI (a deprecar progresivamente; pasará a ser agente de ejecución local ligero)
- Sin frontend React, sin pgvector, sin módulo `agents_hub`

**Documentos de referencia:**
- `Arquitectura.md` — Arquitectura funcional del AI Agents Hub
- `modulo_AI_agents-hub.md` — Plan de integración Hub + AutomatIA (decisiones adoptadas)
- `ARCHITECTURE_old.md` — Arquitectura técnica de AutomatIA (GovGenAI)
- `PLAN_TDD_DETALLADO.md` — Plan TDD detallado del Hub (guía para fases 3-4 y 9-10)

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
| 4C.1 | Automation > Flujos | Partner/Admin | Reemplaza vista NiceGUI de flujos |
| 4C.2 | Automation > PDF extractor | Partner/Admin | Reemplaza vista NiceGUI de extracción |
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

---

### FASE 5 — Auth OIDC/SAML + MCP Client
*Duración estimada: 2-3 semanas | Junio-Julio 2026*

| ID | Tarea | Detalle |
|---|---|---|
| 5.1 | OIDC/SAML | Integración con proveedor institucional; modo agente requiere usuario identificado |
| 5.2 | MCP Client | Conexión segura con Oracle/sistemas externos; implementación única compartida por Automation y Hub |
| 5.3 | Agente de ejecución local | Proceso ligero sin UI; recibe jobs por websocket/polling; ejecuta scripts y RPA locales; reporta resultados al servidor |

---

### FASE 6 — Gestor de Expedientes
*Duración estimada: 8-9 semanas | Julio-Noviembre 2026*

| Sprint | Contenido | Duración | Prerequisito |
|---|---|---|---|
| E1 | Schema BD, CRUD expedientes, API base, AdaptadorNativo | 1 semana | Hub infrastructure (pgvector) |
| E2 | Motor LangGraph con checkpointing, nodos estándar, AdaptadorREST | 2 semanas | LangGraph Hub operativo |
| E3 | AuditService, ExplicabilidadService, endpoint `/informe`, tests RIA | 1 semana | Sprint E2 |
| E4 | Frontend React: lista, detalle, bandeja de aprobaciones, configurador | 3 semanas | Auth OIDC/SAML, Sprint E2 |
| E5 | AdaptadorOracle vía MCP Client, sincronización bidireccional | 1 semana | MCP Client (Fase 5) |

---

## Calendario general

| Fecha | Hito |
|---|---|
| **Abril 2026** | Fase 0: Git + GitHub + Docker PostgreSQL + pgvector operativo |
| **Abril-Mayo 2026** | Fase 1: Frontend React scaffolding + Fase 2: Schema Hub |
| **Mayo-Junio 2026** | Fase 3: Módulo Hub backend (Docling, LangGraph, API) |
| **Junio 2026** | Fase 5: Auth OIDC/SAML |
| **Julio-Agosto 2026** | Fase 4: Frontend Hub completo + primera UI Automation en React |
| **Agosto 2026** | Paper enviado (cumplimiento difusión subvención) |
| **Septiembre 2026** | Repositorio público bajo AGPLv3 en GitHub |
| **Julio-Octubre 2026** | Fase 6: Gestor de Expedientes |
| **Octubre 2026** | Piloto institucional: plataforma completa (Hub + Automation) en producción |

---

## Plan de arranque inmediato (próximas 2 semanas)

```
Semana 1:
  Día 1-2  → git init + GitHub repo + .gitignore + LICENSE (AGPLv3 + MIT)
  Día 2-3  → Docker Compose con PostgreSQL + pgvector
  Día 3-4  → Alembic setup + primera migration del schema existente
  Día 4-5  → Renombrar brain/ → automation/; verificar que todos los tests pasan

Semana 2:
  Día 1-2  → Scaffolding frontend/ con Vite + React + TS + Tailwind + i18next
  Día 3-4  → Auth JWT en frontend + login conectado al server
  Día 5    → Schema Hub: tablas chatbots, knowledge_bases, document_chunks, conversations
```

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
