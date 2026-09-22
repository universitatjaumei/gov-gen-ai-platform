# Plan de Desarrollo: Gov Gen AI Platform

> **Aviso de lectura — esto es un plan, no una descripcion del sistema.**
>
> Escrito en futuro y **antes de decisiones que despues se revirtieron**. Las dos mayores: el
> cliente NiceGUI, retirado entero el 2026-09-04 con 574 ficheros, y Docling, retirado en el
> bloque EXT.3. Lo que este documento da por hecho puede no existir en el arbol.
>
> No se ha enmendado a proposito: un plan corregido a posteriori para que parezca acertado deja de
> servir para lo unico que sirve un plan viejo, que es entender por que se decidio lo que se
> decidio. Para saber que hace el sistema **hoy**: [`../docs/ESPECIFICACIONES.md`](../docs/ESPECIFICACIONES.md).

## Integración AI Agents Hub + AutomatIA

*Última actualización: 2026-05-03 | Estado: Fases TDD 0-8 completadas; próxima Fase TDD 9 (Frontend React) bajo Fase Funcional 1.A*

> **Reorganización de mayo 2026 (Prompt 2).** Este plan se estructura ahora explícitamente
> en **tres Fases Funcionales** (Hub Informativo y Redacción · Automatización y Thin Client ·
> Gestor de Expedientes). Las antiguas "Fases 0–10" técnicas y las "Fases TDD 0–22" siguen
> existiendo como granularidad de ejecución, pero quedan **reagrupadas** bajo la nueva
> estructura funcional. Ver §"Estructura del proyecto por Fases Funcionales" y
> §"Relación entre Arquitectura y Planificación".

---

## Situación actual (2026-04-24)

Repositorio `gov-gen-ai-platform` en GitHub (`universitatjaumei`), monorepo con:

- `server/` — FastAPI sobre PostgreSQL + pgvector; módulos `automation/` y `agents_hub/` operativos; JWT real; Docker multi-stage CPU-only; CI/CD en GitHub Actions; observabilidad LangFuse; servicio de feedback.
- `client_app/` — Cliente NiceGUI legacy, pendiente de migración progresiva al server y al frontend React (ver Subfases **2.A** Thin Client, **2.B** Migración UI y **2.C** Servicios migrados). El agente ligero de ejecución local (thin client) aún no existe; se creará en la Subfase 2.A.
- `frontend/` — **Aún no creado**. Scaffolding en la próxima Fase 1 del plan (equivale a Fase 9 del PLAN_TDD_DETALLADO).

**Estado por fase TDD** (ver `Plan_TDD_Fase1.md` / `Plan_TDD_Fase2.md` / `Plan_TDD_Fase3.md` para el detalle):

| Fase TDD | Contenido | Fase Funcional | Estado |
|---|---|---|---|
| 0 | Infraestructura heredada de AutomatIA | F1 (base) | ✅ |
| 1 | Auth JWT | F1 (base) | ✅ 2026-04-22 |
| 2 | Base de datos + pgvector + retriever híbrido | F1 (base) | ✅ 2026-04-23 |
| 3 | Ingestión Docling | F1 (base) | ✅ 2026-04-23 |
| 4 | Agente LangGraph + RAGAS + HITL | F1 (base) | ✅ 2026-04-23 |
| 5 | API endpoints chat SSE + export PDF/MD | F1 (base) | ✅ 2026-04-23 |
| 6 | Tests E2E + CI/CD | F1 (base) | ✅ 2026-04-23 |
| 7 | Docker multi-stage + docker-compose prod | F1 (base) | ✅ 2026-04-23 |
| 8 | LangFuse + FeedbackService | F1 (base) | ✅ 2026-04-23 |
| 9 | Frontend React (Admin Hub + Widget + Migración NiceGUI) | F1.A/B/C + F2.B | ⏳ Pendiente |
| 10 | Sistema de temas y panel de IA | F1.B | ⏳ Pendiente |
| 11 | Autoinstalación | F1.B / transversal | ⏳ Pendiente |
| 12 | Gestor de Expedientes | F3.A | ⏳ Pendiente |
| 13 | Privacidad y anonimización reversible NER (Zero-Knowledge) | F1.C (motor) + F2.A (Vault Edge) | ⏳ Pendiente |
| 14 | Sandbox distribuido Edge ↔ Thin-client | F2.A | ⏳ Pendiente |
| 15 | RunManifest + AuditService + Script Registry unificados (IA Frugal) | F2.C | ⏳ Pendiente |
| 16 | Determinista-first + Fábricas como nodos LangGraph | F2.C + F3.B | ⏳ Pendiente |
| 17 | Agente Analista + base vectorial de normativa | F3.B | ⏳ Pendiente |
| 18 | Bridges semánticos ampliados (multi-contexto) | F2.C | ⏳ Pendiente |
| 19 | Adaptadores UJI + Gestión 400 + capa ENI/ENS | F3.C | ⏳ Pendiente |
| 20 | Accesibilidad WCAG 2.2 AA + admin conversacional | Transversal (F1+F2+F3) | ⏳ Pendiente |
| 21 | RPA web (diferido a v2) | Diferido v2 | ⏳ Fuera del alcance v1 |
| 22 | Microservicios Embedding + Docling (diferido post-cloud) | Diferido post-cloud | ⏳ Diferido — activar si cold start >15s o RAM >2 GB en Cloud Run |

**Documentos de referencia:**
- `Descripción y funcionalidades.md` — Visión funcional GovGenAI (malla agéntica, PMDS, zero-knowledge, RunManifest, IA frugal)
- `docs/Arquitectura.md` — Arquitectura funcional y técnica unificada (principios irreversibles, roles, Cloud/Edge, privacidad selectiva)
- `modulo_AI_agents-hub.md` — Plan de integración Hub + AutomatIA (decisiones adoptadas)
- `ARCHITECTURE_old.md` — Arquitectura técnica de AutomatIA (GovGenAI)
- `Plan_TDD_Fase1.md` / `Plan_TDD_Fase2.md` / `Plan_TDD_Fase3.md` — Prompts atómicos TDD por Fase Funcional (sustituyen al antiguo `PLAN_TDD_DETALLADO.md`)

---

## Estructura del proyecto por Fases Funcionales

> **Sección añadida (Prompt 2 — mayo 2026).** Establece el agrupamiento de alto nivel
> que rige el resto del plan. Cualquier "Fase TDD" o "Sprint" mencionado más abajo se
> ejecuta dentro de una de las tres Fases Funcionales aquí definidas.

El proyecto se organiza en **tres Fases Funcionales** secuenciales. Cada una entrega
un producto con valor propio; ninguna depende de la siguiente para ser útil.

| Fase Funcional | Entregable de producto | Subfases |
| :---- | :---- | :---- |
| **Fase 1 — Hub Informativo y Redacción (MVP)** | Plataforma capaz de informar (chatbots públicos con RAG sobre webs/PDFs institucionales) y de redactar borradores asistidos (modo agente con privacidad NER). Primer despliegue público. | 1.A Chatbots Públicos y Spiders · 1.B Identidad, Personalización y Despliegue Cloud · 1.C Privacidad y Generación de Informes |
| **Fase 2 — Automatización y Thin Client** | Plataforma capaz de orquestar flujos y scripts en el Edge y en el agente local del User. Migración completa del legacy NiceGUI. | 2.A Thin Client + Sandbox · 2.B Migración UI Automation (NiceGUI → React) · 2.C IA Frugal, Skill & Script Library, Servicios migrados |
| **Fase 3 — Gestor de Expedientes e Integración Institucional** | Plataforma capaz de tramitar expedientes administrativos auditables conforme a RIA, integrada con UJI y Gestión 400 mediante MCP, con capa ENI/ENS. | 3.A Motor de Expedientes · 3.B Malla Agéntica Avanzada · 3.C Adaptadores MCP + ENI/ENS |

### Criterio de prioridad

- La **Subfase 1.A es la prioridad máxima**: es la que habilita el primer despliegue
  con valor visible para una Organización piloto.
- Una vez cerrada 1.A, se pueden paralelizar 1.B y 1.C según equipo disponible.
- Las Fases 2 y 3 **no se inician hasta que el MVP de Fase 1 esté en piloto**, salvo
  paralelizaciones puntuales (p. ej. Thin Client si un flujo crítico lo requiere).

### Alcance MVP de Fase 1 — qué entra y qué queda fuera

#### Incluido en el MVP de Fase 1

- Hub backend operativo (RAG, LangGraph dual chatbot/agente, RAGAS, HITL, observabilidad,
  feedback) — **ya completado en Fases TDD 0–8**.
- Spiders modulares + Asistente HITL de configuración (Subfase 1.A).
- Frontend React Admin Hub (Chatbots, Organizaciones, Documentos, Informes) — Bloque 4A.
- Widget embebible bilingüe con sincronización de idioma (Bloque 4B).
- Auth OIDC/SAML para modo agente identificado (Subfase 1.B).
- Sistema de temas en cascada Plataforma → Organización → Chatbot (Subfase 1.B).
- Despliegue staging en Google Cloud (Cloud SQL + Cloud Run + Secret Manager + GCS).
- Privacidad NER reversible aplicada a expedientes y a la generación de informes
  (Subfase 1.C). Vault de identidades en BD del Edge cuando aplique.
- Focus Mode + DrawerHub como infraestructura de diseño reutilizable (Subfase 1.C).
- Workspace de redacción de informes con citas trazables y exportación maquetada
  (DOCX/ODT, integración Google Drive opcional).
- Accesibilidad WCAG 2.2 AA en todas las pantallas frontend (transversal).

#### Conscientemente fuera del MVP de Fase 1

| Funcionalidad | Va a | Motivo |
| :---- | :---- | :---- |
| Migración de UI de Automation (Flujos, Scripts, Extractor PDF) | Fase 2.B | No es necesaria para informar ni para redactar informes |
| Thin Client / agente de ejecución local | Fase 2.A | El MVP corre íntegramente en Cloud/Edge servidor |
| Skill & Script Library + IA Frugal + Cache semántico | Fase 2.C | Se introduce cuando hay volumen real de scripts en producción |
| RunManifest + AuditService unificado | Fase 2.C | Versión scoped suficiente para Fase 1; auditoría plena llega con automation |
| Bridges semánticos cross-contexto | Fase 2.C | No hay aún múltiples sistemas externos donde mediar |
| Gestor de Expedientes y motor de tramitación multi-fase | Fase 3.A/B | Producto distinto; depende de OIDC, MCP y servicios migrados |
| Adaptadores UJI / Gestión 400 + capa ENI/ENS | Fase 3.C | Sólo necesarios cuando exista expediente que sincronizar |
| RPA web (Playwright) | Diferido a v2 | Peso del runtime vs. valor real del piloto |
| Microservicios Embedding/Docling separados | Diferido post-cloud | Activar sólo si métricas de Cloud Run lo exigen |

### Subfases por Fase Funcional (vista compacta)

```
Fase 1 — Hub Informativo y Redacción (MVP)
├── 1.A  Chatbots Públicos y Spiders            ← prioridad máxima
├── 1.B  Identidad, Temas y Despliegue Cloud
└── 1.C  Privacidad NER, Focus Mode e Informes

Fase 2 — Automatización y Thin Client
├── 2.A  Thin Client + Sandbox distribuido
├── 2.B  Migración UI NiceGUI → React (Flujos, PDF, Scripts)
└── 2.C  IA Frugal, Skill & Script Library, Servicios migrados

Fase 3 — Gestor de Expedientes e Integración Institucional
├── 3.A  Motor de Expedientes (LangGraph + checkpointing)
├── 3.B  Malla Agéntica (Analista, Validador, Snapshots, Fairness)
└── 3.C  Adaptadores MCP (UJI, Gestión 400) + ENI/ENS
```

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
10. **Servicios legacy se migran, no se reimplementan**: Privacidad (anonymizer), sandbox, manifest, audit, script registry, fábricas deterministas y bridges existen en `client_app/` con tests y se migran al server reutilizando código + tests. Aplica la regla de CLAUDE.md: migración = código nuevo en server + ubicación en carpeta legacy para borrado final.
11. **Alcance v1 de integración con tramitación**: Adaptadores para dos sistemas: plataforma propia UJI y Gestión 400 (opensea). Capa transversal obligatoria ENI (DIR3, eEMGDE, CSV, formatos de evidencia) y ENS (categorización, controles). El `AdaptadorOracle` genérico previsto antes queda descartado.
12. **Privacidad scoped**: Anonimización reversible NER se aplica a informes, expedientes y automatización. No se aplica al chatbot informativo con información pública. Se aplica selectivamente a los expedientes, informes y procesos seleccionados. 
13. **RPA web diferido a v2**: Playwright y `web_watcher` no se migran al thin client en v1. Si un flujo crítico del piloto lo exige, se despliega un worker Playwright dedicado en el Edge node.


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
| Multi-tenancy SuperAdmin/Admin/Organización | `server/app/database/models` + `api/deps.py` | Operativo (refactor de nomenclatura aplicado en Fase 1) |
| Billing engine | `server/app/services/billing_engine.py` | Operativo |
| Dynamic prompts | `server/` | Parcial — extender para Hub |
| TDD framework + tests | `server/tests/` | Operativo |
| Docker + FastAPI async | `server/` | Operativo |

El Hub se construye **encima** de esta base, sin duplicar infraestructura.

---

## Hoja de ruta por fases

> **Reorganización (Prompt 2 — mayo 2026).** El detalle técnico de las antiguas
> "Fase 0" a "Fase 10" se conserva íntegro pero se reagrupa bajo las tres **Fases
> Funcionales**. Cada bloque indica su pertenencia (`F1.A`, `F2.B`, etc.) para que la
> trazabilidad con el resto del plan y con los `Plan_TDD_Fase{1,2,3}.md` sea directa.

---

# FASE FUNCIONAL 1 — Hub Informativo y Redacción (MVP)

*Duración estimada: 8–10 semanas | Mayo–Agosto 2026 | **Prioridad máxima en Subfase 1.A***

Recoge todas las piezas necesarias para que la plataforma pueda **informar** (chatbots
públicos con RAG sobre webs y PDFs institucionales) y **redactar** (modo agente con
privacidad y exportación maquetada). Incluye toda la base ya completada en las
Fases TDD 0–8 más las piezas pendientes de Subfases 1.A, 1.B y 1.C.

## F1 · Base ya completada (antiguas Fases TDD 0–8)
*Estado: ✅ completado entre 2026-04-22 y 2026-04-23*

### Antigua Fase 0 — Git, repositorio e infraestructura base
*Duración estimada: 1 semana*

| ID | Tarea | Detalle |
|---|---|---|
| ~~0.1~~ | ~~Inicializar git~~ ✅ | `git init`, `.gitignore`, dos ficheros `LICENSE` (AGPLv3 server, MIT frontend) |
| ~~0.2~~ | ~~Crear repositorio GitHub~~ ✅ | Nuevo repo `gov-gen-ai-platform`, push inicial. Transferido a `universitatjaumei` el 2026-09-10 |
| ~~0.3~~ | ~~Docker Compose unificado~~ ✅ | `docker-compose.yml` con PostgreSQL+pgvector y MinIO. Pendiente: `docker compose up` tras instalar Docker Desktop |
| ~~0.4~~ | ~~Alembic~~ ✅ | `alembic.ini` + `migrations/env.py` listos. Pendiente: `alembic revision --autogenerate` + `upgrade head` tras levantar PG |
| ~~0.5~~ | ~~Renombrar `brain/` → `automation/`~~ ✅ | Módulo renombrado, todos los imports actualizados, legacy eliminado |
| 0.6 | Auth JWT | Migrar de cabecera `X-License-Key` + Bearer email a JWT estándar (base para OIDC/SAML) |

**Criterio de éxito**: `docker compose up` levanta server sobre PostgreSQL; todos los tests existentes pasan.

---

### Antigua Fase 1 — Scaffolding Frontend React + Vite
*Duración estimada: 1 semana*

| ID | Tarea | Detalle |
|---|---|---|
| 1.1 | Crear `frontend/` | `npm create vite@latest frontend -- --template react-ts` |
| 1.2 | Stack base | Tailwind CSS + **shadcn/ui**, React Router v6, i18next (CA/ES/EN), @tanstack/react-query, react-hook-form + zod |
| 1.3 | Auth frontend | JWT + interceptores Axios, rutas protegidas por rol (SuperAdmin, Admin, User) |
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

### Antigua Fase 2 — Infraestructura Hub
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
organizaciones (antes clients)     chatbots
admins (antes partners)            knowledge_bases
users                              documents
llm_configs           ──────────►  document_chunks + vector (pgvector)
prompts                            conversations
executions                         messages
...                                feedback_ratings
                                   ragas_evaluations
```

**Criterio de éxito**: Se pueden insertar y recuperar chunks vectoriales desde tests de integración.

---

### Antigua Fase 3 — Módulo Agents Hub Backend
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
GET    /hub/chatbots                → listado de chatbots del Admin
POST   /hub/admin/chatbots          → crear/configurar chatbot
POST   /hub/admin/knowledge-bases   → gestión de bases de conocimiento
POST   /hub/feedback                → valoración del usuario (estrellas)
GET    /hub/admin/ragas             → métricas de calidad
```

**Criterio de éxito**: El endpoint `/hub/chat` responde con RAG funcional sobre documentos ingestados.

---

## F1 · Subfases pendientes (1.A, 1.B, 1.C)

### Subfase 1.A — Chatbots Públicos y Spiders
*Duración estimada: 3–4 semanas | Mayo–Junio 2026 | **Prioridad máxima — habilita el primer despliegue***

Esta subfase introduce la capacidad de generar chatbots informativos sobre cualquier
web institucional gracias a una arquitectura modular de **Spider Skills** y un
**Asistente de Ingestión HITL**. Aplica directamente la filosofía Skill & Script
Library de la arquitectura (§2.4).

| ID | Tarea | Usuarios | Detalle |
|---|---|---|---|
| 1.A.1 | Modelo de datos `HubIngestionSource` + `spider_skill` + `config_json` | — | Migración Alembic; vinculación a Organización |
| 1.A.2 | Registro de Spider Skills + clase base `BaseSpiderSkill` | — | Patrón abstracto + singleton `SpiderRegistry` |
| 1.A.3 | Spider genérico (crawl_depth + filtros regex) | SuperAdmin | Indexa jerarquías web |
| 1.A.4 | Spider especializado UJI Normativa | SuperAdmin | Lógica para reglamentos UJI |
| 1.A.5 | Spider especializado UJI Procedimientos | SuperAdmin | Lógica para catálogo de trámites |
| 1.A.6 | Orquestador `IngestionWatcher` multivía | — | Selecciona Skill por `spider_skill` y aplica `config_json` |
| 1.A.7 | UI dinámica de configuración de fuentes | Admin | Formulario que se adapta al Skill seleccionado |
| 1.A.8 | Asistente de Ingestión HITL (analyze-html) | Admin | Endpoint `POST /api/v1/hub/admin/analyze-html` que propone selectores CSS a partir del view-source |
| 1.A.9 | Validación en vivo de `config_json` | Admin | Botón "Probar Configuración" que hace una extracción real con los selectores propuestos |
| 1.A.10 | Bucle de aprendizaje de la skill | — | `extraction_confidence` y guardado en Skill & Script Library |

**Frontend (Bloque 4A — Admin Hub)** — pantallas necesarias para 1.A:

| ID | Tarea | Usuarios | Detalle |
|---|---|---|---|
| 4A.1 | Setup shadcn/ui + i18n + auth context | Admin / SuperAdmin | Base del SPA; login conectado al server |
| 4A.2 | Layout unificado | Admin / SuperAdmin | Sidebar seccional: Hub / Automatización / Plataforma |
| 4A.3 | Hub > Chatbots | Admin | CRUD: listar, crear, editar, desactivar |
| 4A.4 | Hub > Organizaciones | Admin | CRUD Organizaciones + asignación de chatbots |
| 4A.5 | Hub > Documentos | Admin | Upload, listado y borrado por chatbot |
| 4A.6 | Hub > Informes | Admin / SuperAdmin | Tabla interacciones, filtro puntuación, export |

**Criterio de éxito 1.A**: una Organización piloto puede crear su chatbot informativo con
el Asistente HITL sobre su web pública en menos de 30 minutos, y el chatbot responde con
citas trazables a la normativa indexada.

---

### Subfase 1.B — Identidad, Personalización Visual y Despliegue Cloud
*Duración estimada: 2–3 semanas | Junio 2026*

Habilita el modo agente identificado (necesario para Subfase 1.C) y el primer despliegue
público con marca institucional.

| ID | Tarea | Detalle |
|---|---|---|
| 1.B.1 | Auth OIDC/SAML | Integración con proveedor institucional; modo agente requiere User identificado *(antes Fase 5.1)* |
| 1.B.2 | Sistema de temas en cascada | Variables CSS, presets (Oscuro, Universidad), editor visual *(antes Fase TDD 10)* |
| 1.B.3 | Despliegue staging Cloud | Google Cloud: Secret Manager, Cloud SQL (PostgreSQL+pgvector), Cloud Run, GCS |

**Cascada de temas (nomenclatura actualizada §4 docs/Arquitectura.md):**
```
Plataforma (defaults globales — SuperAdmin)
    └── Organización (logo, colores corporativos — Admin)
            └── Chatbot (overrides por instancia: botón flotante, avatar — Admin)
```

**Frontend (Bloque 4B — Widget y modo agente):**

| ID | Tarea | Usuarios | Detalle |
|---|---|---|---|
| 4B.1 | Widget embebible | Users anónimos | Bundle independiente (Vite library mode); iframe; bilingüe; sincronización idioma página host |
| 4B.2 | Chat SSE + feedback | Users | Stream en tiempo real; valoración 1–5 estrellas |
| 4B.3 | Modo agente expandido (esqueleto) | Users identificados | Layout y enrutado; el contenido completo se cierra en 1.C |

**Criterio de éxito 1.B**: widget con la marca de la Organización accesible desde una URL
pública de pruebas en GCP; OIDC/SAML operativo.

---

### Subfase 1.C — Privacidad NER, Focus Mode e Informes
*Duración estimada: 3 semanas | Junio–Julio 2026*

Materializa el principio de privacidad selectiva (§7 docs/Arquitectura.md) y entrega el
workspace de redacción asistida.

| ID | Tarea | Origen | Destino | Detalle |
|---|---|---|---|---|
| 1.C.1 | Privacidad reversible (anonimización NER) | `app/modules/privacy/anonymizer.py` (1010 LoC), `app/services/anonymization_service.py`, `app/utils/pii_detector.py`, `app/services/privacy_guardian.py`, `app/services/screenshot_guard.py` | `server/app/core/privacy/` | Migración as-is del motor NER. Vault de mapeos pseudónimo↔real en Edge (cifrado at rest). Hook pre/post-LLM en grafo de informes. **No aplica al chatbot informativo público.** *(antes Fase 6.1)* |
| 1.C.2 | Políticas de privacidad selectiva | — | `HubOrganizacion.default_privacy_policy`, `HubTipoExpediente.requires_anonymization`, `HubChatbot.anonymize_output` | Modelado en BD según §7.2 docs/Arquitectura.md |
| 1.C.3 | Focus Mode + DrawerHub | — | `frontend/src/shared/layout/` | Infraestructura transversal Zustand + Sheet shadcn/ui. Drawer con pestañas dinámicas (Informe vs. Flujo). Reutilizable en Fase 2.B *(antes prompt 9.12.a)* |
| 1.C.4 | Workspace de informes (Dropzone + live preview) | — | `frontend/src/agent/` | Modo agente expandido con Dropzone PDFs, live preview del borrador, "Solicitar cambios" |
| 1.C.5 | Exportación maquetada DOCX/ODT | — | `server/app/modules/agents_hub/services/export_service.py` | Plantillas Jinja2/Docx con índice automático, citas a pie de página, anexo de auditoría con `RunManifest` (versión scoped, no la unificada de Fase 2.C). Estilos del Sistema de Temas |
| 1.C.6 | Driver Google Drive (opcional) | — | `export_service.py` | Subida a carpeta institucional via `google-api-python-client` + selector de destino en UI |
| 1.C.7 | Memoria de estilo separada de identidad | — | `user_preferences_vector` | Re-anonimización antes de extraer patrones (§7.4 docs/Arquitectura.md) |

**Criterio de éxito 1.C**: un User identificado puede subir un PDF con datos personales,
obtener un informe con citas a normativa pública y exportarlo en DOCX maquetado,
sin que ningún dato identificativo haya salido del Edge.

---

## F1 · Bloques transversales aplicables al MVP

### Accesibilidad WCAG 2.2 AA *(transversal — aplica también a F2 y F3)*
*Duración estimada: integrada en cada subfase | antes Fase 8*

| ID | Tarea | Detalle |
|---|---|---|
| A11Y.1 | WCAG 2.2 AA criterio obligatorio | En cada pantalla de Bloques 4A/4B y workspace de informes |
| A11Y.2 | Tests automáticos a11y | `@axe-core/react` en Vitest; Lighthouse CI con umbral a11y ≥ 95 |
| A11Y.3 | Reutilización de tests legacy | Migrar `client_app/tests/a11y/test_accessibility.py` |

### Consola conversacional de administración
*Aplica a Fase 1, intensifica en Fases 2 y 3 | antes Fase 8.4*

Interfaz en lenguaje natural dentro del panel Admin que permite *"crea un chatbot
para el padrón que use el LLM local y lea estos PDFs"* y ejecuta la configuración.

---

# FASE FUNCIONAL 2 — Automatización y Thin Client

*Duración estimada: 8–10 semanas | Agosto–Octubre 2026*
*Prerequisito: Fase 1 desplegada en piloto*

Migra el sistema legacy NiceGUI a la arquitectura distribuida Edge + Thin Client y
materializa la Skill & Script Library completa (§2.4 docs/Arquitectura.md).

## Subfase 2.A — Thin Client + Sandbox distribuido
*Duración estimada: 2–3 semanas*

| ID | Tarea | Detalle |
|---|---|---|
| 2.A.1 | Thin Client (agente de ejecución local) | Proceso sin UI; patrón GitLab Runner; recibe jobs por WebSocket; ejecuta scripts Python firmados; reporta resultados. **Sin Playwright** (ver decisión 13). *(antes Fase 5.3 + Bloque 4D)* |
| 2.A.2 | Sandbox distribuido Edge ↔ Thin-client | Migrar `sandbox_worker.py` al thin client; mantener `safety_sandbox.py` (auditoría AST) en server. Contrato: server firma → thin client verifica + ejecuta + devuelve `RunManifest` firmado *(antes Fase 5.4)* |
| 2.A.3 | Emparejamiento seguro Thin Client ↔ Edge | Token de enrolment, refresh de credenciales, registro de capacidades, heartbeat, actualización remota *(antes Fase 5.5)* |
| 2.A.4 | Skill de Sincronización de Workspace | Detección automática de Google Drive File Stream / OneDrive en Windows/Linux; handler `FILE_GENERATED`; movimiento firmado de archivos a la carpeta sincronizada de la Organización *(NUEVA)* |
| 2.A.5 | Vault de identidades en Edge (completo) | Materialización del Vault del §7.3 docs/Arquitectura.md una vez exista despliegue Edge real |

**Criterio de éxito 2.A**: un Thin Client en una estación Windows/Linux ejecuta un script
Python firmado recibido del Edge node, con aislamiento de red, FS y proceso, y devuelve
un `RunManifest` firmado verificable por el server.

## Subfase 2.B — Migración UI NiceGUI → React
*Duración estimada: 3 semanas | antes Bloque 4C*

| ID | Tarea | Usuarios | Detalle |
|---|---|---|---|
| 2.B.0 | Guía transversal de separación de lógica | — | Reglas reutilizables para dividir código NiceGUI entre servidor FastAPI y estado React (aplica a 2.B.1/2.B.2/2.B.3) *(antes 4C.0)* |
| 2.B.1 | Automation > Flujos | Admin | Reemplaza vista NiceGUI de flujos; reutiliza Focus Mode (entregado en 1.C) *(antes 4C.1)* |
| 2.B.2a | Refactor backend PDF extractor a Docling | — | Sustituye `pdfplumber` + `fitz` por Docling. Nueva API upload-first; borra `extraction_strategies.py` y `PdfReaderDual` *(antes 4C.1b)* |
| 2.B.2 | Automation > PDF Extractor | Admin | UI sobre los contratos Docling definidos en 2.B.2a *(antes 4C.2)* |
| 2.B.3 | Automation > Scripts | Admin | Reemplaza vista NiceGUI de scripts *(antes 4C.3)* |
| 2.B.4 | Limpieza NiceGUI | — | Borrado módulo a módulo (ver CLAUDE.md) *(antes 4C.4)* |

**Criterio de éxito 2.B**:
- Las pantallas de flujos, extractor PDF y scripts funcionan en React contra el backend FastAPI.
- El extractor PDF corre sobre Docling en el servidor; `pdfplumber`, `fitz` y `PdfReaderDual` están eliminados del repositorio.
- `client_app/app/ui/` no contiene ningún fichero de UI (solo queda `client_app/local_agent/` como proceso sin UI).
- `grep -r "from client_app.app.ui" .` no devuelve coincidencias.

## Subfase 2.C — IA Frugal, Skill & Script Library, Servicios migrados
*Duración estimada: 3–4 semanas*

Migra los servicios transversales del `client_app/` al server FastAPI y materializa la
**Skill & Script Library** completa (§2.4 docs/Arquitectura.md). Aplica la regla de CLAUDE.md:
al cerrar cada subtarea, el código legacy correspondiente debe moverse a carpeta legacy para eliminacion final y sin referencias en el repo.

| ID | Tarea | Origen legacy | Destino server | Detalle |
|---|---|---|---|---|
| 2.C.1 | MCP Client compartido | — | `server/app/core/mcp/` | Implementación única para Automation y Hub *(antes Fase 5.2)* |
| 2.C.2 | RunManifest + AuditService unificados | `app/services/manifest_generator.py`, `manifest_signature_service.py`, `enterprise_audit_service.py`, `external_script_audit_service.py` | `server/app/core/manifest/` + `server/app/core/audit/` | Formato único de `run_manifest.json` y cadena de hash firmada válida para automation y expedientes. Reemplaza la versión scoped de Fase 1.C *(antes Fase 6.2)* |
| 2.C.3 | Skill & Script Library + IA Frugal | `app/services/script_library_service.py` (840 LoC), `flow_registry_service.py`, `script_generator_service.py`, `script_adaptation_service.py`, `custom_script_service.py`, `validation_loop.py` | `server/app/modules/automation/scripts/` | Tabla `scripts_aprobados` con hash + versión + tenant + etiqueta semántica + `is_learned_skill` + `usage_context` (vector). Endpoint de búsqueda por taxonomía. Métricas de reuso (% tareas resueltas sin LLM) *(antes Fase 6.3, evolucionado)* |
| 2.C.4 | Cache semántico pre-LLM | — (ampliación sobre 2.C.3) | `server/app/modules/automation/scripts/semantic_cache.py` | Campo `intent_embedding` (BGE-M3); búsqueda por similaridad antes de invocar LLM. **Evaluar en piloto**: si la Library por taxonomía resuelve >80% de reuso, no se activa *(antes Fase 6.4)* |
| 2.C.5 | Determinista-first + Fábricas invocables | `app/services/deterministic_etl_service.py`, `deterministic_graphics_service.py`, `app/modules/factory/etl_factory.py`, `graphics_factory.py`, `report_factory.py`, `app/services/report_factory.py` | `server/app/modules/automation/factories/` | Fábricas expuestas como módulos invocables desde flujos y desde grafos LangGraph (Fase 3). Lógica "determinista por defecto, LLM si no encaja" preservada *(antes Fase 6.5)* |
| 2.C.6 | Bridges semánticos ampliados | `app/services/bridge_creator.py`, `bridge_generation_service.py`, `library_bridge.py` | `server/app/modules/automation/bridge/` | Interfaz común reutilizable desde flujos, expedientes y adaptadores de tramitación (Fase 3). Detección de discordancias entre esquemas UJI ↔ Gestión 400 *(antes Fase 6.6)* |
| 2.C.7 | Nodo `SkillExtractor` (LangGraph) | — | `server/app/modules/automation/factories/skill_extractor_node.py` | Tras `NodoHuman` con resultado aprobado: analiza el `RunManifest`, genera resumen procedimental y guarda como Skill etiquetada en la Library |
| 2.C.8 | Limpieza legacy post-migración | — | — | `grep -r` de referencias eliminadas; borrado de ficheros migrados de `client_app/`; suite de tests verde *(antes Fase 6.7)* |

**Criterio de éxito 2.C**: todos los servicios listados operan desde el server, con tests
verdes en `server/tests/`. `client_app/app/services/` y `client_app/app/modules/privacy|sandbox|factory`
no contienen ningún fichero migrado. La Skill & Script Library puede proponer una skill
aprendida con score >0.85 cuando el agente detecta una tramitación similar a una previa
exitosa.

### Aclaración sobre la ejecución de scripts en Fase 2

Como regla general los scripts de automatización **se ejecutan en el Edge**. En el módulo
de informes (Fase 1.C) ya se ejecutaban allí para entregar informes rápidos íntegramente
en la nube institucional. En esta Fase 2 se habilita además la capacidad del **Thin Client**
para recibir y ejecutar esos mismos scripts sobre **carpetas locales** y para tareas de
automatización que requieren recursos locales (ver §2.3 docs/Arquitectura.md).

---

# FASE FUNCIONAL 3 — Gestor de Expedientes e Integración Institucional

*Duración estimada: 9–10 semanas | Octubre 2026 – Enero 2027*
*Prerequisitos: Fase 2 completada (servicios migrados, Thin Client, MCP Client)*

Construye el motor de tramitación administrativa multi-fase, auditable y conforme con el
RIA, reutilizando toda la infraestructura de Fases 1 y 2. Sustituye la antigua Fase 7.

## Subfase 3.A — Motor de Expedientes
*Duración estimada: 3 semanas*

| ID | Tarea | Duración | Detalle |
|---|---|---|---|
| 3.A.1 | Schema BD, CRUD expedientes, API base, AdaptadorNativo | 1 semana | Tablas `tipos_expediente`, `expedientes`, `fases_expediente`, `acciones_fase`, `ejecuciones_accion`, `documentos_expediente`, `audit_expediente` *(antes Sprint E1)* |
| 3.A.2 | Motor LangGraph con checkpointing + nodos estándar | 2 semanas | NodoLLM, NodoScript, NodoHuman, NodoRPA-local (delegado al Thin Client de F2.A), NodoAPIExterna, NodoNotificacion *(antes Sprint E2)* |

## Subfase 3.B — Malla Agéntica Avanzada
*Duración estimada: 4 semanas*

| ID | Tarea | Duración | Detalle |
|---|---|---|---|
| 3.B.1 | Agente Analista + base vectorial de normativa | 1–1.5 semanas | KB vectorial `regulation` (BOE, DOGC, ordenanzas UJI, normativa autonómica/local). Nodo previo al enrutado que clasifica intención y devuelve normativa con cita trazable *(antes Sprint E2.5)* |
| 3.B.2 | Nodo Fábrica + Nodo Validador/Crítico | 1 semana | Wrappers LangGraph para fábricas migradas en F2.C.5 + scripts del Registry F2.C.3. Validador previo al `NodoHuman` con AST + `external_script_audit` + `validation_loop`; etiqueta `segura | requiere_revisión | bloqueada` *(antes Sprint E2.6)* |
| 3.B.3 | Snapshots Administrativos (Histórico KB) | 1 semana | `valid_from` / `valid_to` en `HubDocument`; tabla `HubKnowledgeSnapshot`; parámetro `as_of_date` en retrievers; endpoint `GET /api/v1/hub/knowledge/snapshot/{chatbot_id}` *(NUEVO — seguridad jurídica)* |
| 3.B.4 | Dashboard de Sesgo y Equidad (Fairness Audit) | 1 semana | `FairnessScore` extendiendo RAGAS; análisis por colectivo/tipo de trámite; integración con AuditService en expedientes de "Alto Riesgo"; pantalla `FairnessDashboard.tsx` *(NUEVO — RIA Art. 15)* |
| 3.B.5 | Integración con RunManifest + AuditService unificados | 1 semana | Endpoint `/informe` PDF con cadena completa (incl. *Learning Trace*); tests de cumplimiento RIA *(antes Sprint E3)* |
| 3.B.6 | Frontend React expedientes | 3 semanas | Lista, detalle (timeline + documentos + audit), bandeja de aprobaciones HITL, configurador de tipos por formulario estructurado *(antes Sprint E4)* |

## Subfase 3.C — Adaptadores MCP y Capa ENI/ENS
*Duración estimada: 1.5–2 semanas | antes Sprint E5*

| ID | Tarea | Detalle |
|---|---|---|
| 3.C.1 | Interfaz común `AdaptadorTramitacion` (Protocol) | `consultar_expediente`, `crear_tramitacion`, `actualizar_estado`, `adjuntar_documento`, `publicar_resolucion`, `obtener_documentos` |
| 3.C.2 | `AdaptadorUJI` | Cliente HTTP contra el API institucional de la Universitat Jaume I |
| 3.C.3 | `AdaptadorGestion400` | Cliente contra el API público de opensea |
| 3.C.4 | Capa ENI transversal | Resolvedor DIR3 + enriquecedor eEMGDE + generador/verificador CSV + empaquetador de evidencia |
| 3.C.5 | Capa ENS | Política por tipo de expediente (categorización alta/media/baja) aplicada al sandbox + audit |

**Criterio de éxito Fase 3**: un tipo de expediente configurable lee datos de UJI o
Gestión 400, pasa por el Agente Analista, invoca una Fábrica de F2.C.5, es auditado por
el Validador, se suspende en HITL y al ser aprobado publica la resolución en el sistema
origen con evidencia ENI y registro RIA completo.

### Aclaración sobre la ejecución de scripts en Fase 3

Si en la tramitación de expedientes se utiliza algún script de la Skill & Script Library
(F2.C.3) o se generan scripts ad-hoc para tramitación, la **ejecución se hace en el Edge**.
La orquestación administrativa llama al script en el Edge para extraer información,
transformar documentos o validar documentos aportados por el ciudadano.

---

# Fases técnicas transversales y diferidas

> Las antiguas **Fases 5, 6, 7 y 8** han sido **reagrupadas** dentro de las Fases
> Funcionales 1, 2 y 3 (ver detalle ↑). Sus contenidos no se duplican aquí; la trazabilidad
> antiguo→nuevo está marcada con la nota *"antes Fase X.Y"* en cada subtask de las
> Fases Funcionales.
>
> Sólo se conservan en este apartado los bloques **realmente diferidos** (no asignados a
> ninguna de las tres Fases Funcionales del piloto v1).

---

### Diferido post-cloud — Microservicios de computación pesada
*Activar solo cuando los criterios de métricas se cumplan en Cloud Run*

BGE-M3 (~1.1 GB) y Docling (CPU-intensivo) se ejecutan actualmente in-process. Esto es correcto hasta el primer despliegue. Si en Cloud Run el cold start supera 15 s o la RAM supera 2 GB, extraer a microservicios independientes.

| Criterio de activación | Métrica |
|---|---|
| Cold start API > 15 s | Cloud Run request latency (p95 de arranque en frío) |
| RAM > 2 GB por instancia | Cloud Run container memory usage |
| Necesidad de escala independiente | — |

**Implementación**: ver **Fase TDD 22** en `Plan_TDD_Fase2.md` (3 prompts atómicos: embedding service, docling service, integración docker-compose). La abstracción `EmbeddingService` (protocolo) ya existe en el servidor; solo hay que añadir `HttpEmbeddingService` y `HttpDoclingProcessor`.

---

### Diferido a v2 — RPA web
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

| Fecha | Fase Funcional / Subfase | Hito |
|---|---|---|
| **Abril 2026** | F1 (base) | Git + GitHub + Docker PostgreSQL + pgvector operativo ✅ |
| **Abril 2026** | F1 (base) | Schema Hub + retriever híbrido + Docling + LangGraph + RAGAS + HITL + API + CI/CD + observabilidad ✅ (Fases TDD 0–8) |
| **Mayo–Junio 2026** | **Fase 1.A** | Spider Skills + Asistente HITL ingestión + Bloque 4A Admin Hub *(prioridad máxima)* |
| **Junio 2026** | **Fase 1.B** | Auth OIDC/SAML + Sistema de Temas + Despliegue staging Cloud + Bloque 4B Widget |
| **Junio–Julio 2026** | **Fase 1.C** | Privacidad NER reversible + Focus Mode + Workspace de informes + exportación maquetada |
| **Julio 2026** | F1 transversal | A11y WCAG 2.2 AA cubierta en todas las pantallas de F1 |
| **Julio–Agosto 2026** | **MVP F1 desplegado** — primera Organización piloto activa |
| **Agosto 2026** | Difusión | Paper enviado (cumplimiento subvención) |
| **Agosto 2026** | F1 | Repositorio público bajo AGPLv3 en GitHub |
| **Agosto–Septiembre 2026** | **Fase 2.A** | Thin Client + Sandbox distribuido + Skill de sincronización Workspace |
| **Septiembre 2026** | **Fase 2.B** | Migración UI NiceGUI → React (Flujos, PDF Extractor con Docling, Scripts) + limpieza legacy |
| **Septiembre–Octubre 2026** | **Fase 2.C** | MCP Client + RunManifest/AuditService unificados + Skill & Script Library + IA Frugal + Determinista-first + Bridges |
| **Octubre 2026** | **Fase 3.A** | Motor de Expedientes (LangGraph + checkpointing) |
| **Noviembre 2026** | **Fase 3.B** | Malla Agéntica (Analista, Validador, Snapshots, Fairness Dashboard) + Frontend expedientes |
| **Diciembre 2026** | **Fase 3.C** | AdaptadorUJI + AdaptadorGestion400 + Capa ENI/ENS |
| **Enero 2027** | **Piloto v1 completo** | Plataforma con Hub + Automation + Expedientes en producción. Sin RPA web (diferido a v2) |

---

## Siguiente iteración (próximas 2 semanas, desde 2026-05-03)

Entrada en **Subfase 1.A — Chatbots Públicos y Spiders** (prioridad máxima dentro de la Fase Funcional 1). Continúa con la Fase TDD 9 (Frontend React Bloque 4A) y comienza el desarrollo de las Spider Skills modulares.

```
Semana 1:
  Día 1-2  → Scaffolding frontend/ con Vite + React + TS + Tailwind + shadcn/ui
  Día 2-3  → i18next con locales es / ca / en
  Día 3-4  → Auth context JWT + rutas protegidas por rol (SuperAdmin/Admin/User)
  Día 4-5  → Layout sidebar seccional (Hub / Automatización / Plataforma)

Semana 2:
  Día 1-2  → Hub > Pantalla de Chatbots (4A.3)
  Día 3    → Hub > Pantalla de Organizaciones (4A.4)
  Día 4    → Hub > Pantalla de Documentos (4A.5)
  Día 5    → Hub > Pantalla de Informes (4A.6)
```

**Al cerrar estas dos semanas**: Bloque 4A del Admin Hub operativo end-to-end contra el
server FastAPI ya funcional, listo para conectarse a las Spider Skills (1.A.1–1.A.10) que
se desarrollan en paralelo. Una vez cubierto 1.A se decide si continuar con 1.B
(OIDC/SAML + temas + deploy staging) o intercalar 1.C (privacidad NER + informes)
según prioridad de la Organización piloto.

---

## Relación entre Arquitectura y Planificación

> **Sección añadida (Prompt 2 — mayo 2026).** Aclara la división de responsabilidades
> entre los tres documentos vivos del proyecto y evita duplicación.

`docs/Arquitectura.md`, este documento y los `Plan_TDD_Fase{1,2,3}.md` son **complementarios
y no se solapan**:

| Documento | Naturaleza | Pregunta a la que responde |
| :---- | :---- | :---- |
| **`docs/Arquitectura.md`** | Estado objetivo · Decisiones **irreversibles** | **¿Qué es** la plataforma y qué principios la rigen? (módulos, roles, privacidad, Cloud/Edge, stack) |
| **`PLAN_DESARROLLO.md`** *(este documento)* | Plan de ejecución · Revisable sprint a sprint | **¿Cuándo y en qué orden** se materializa la arquitectura? (3 Fases Funcionales, sub-fases, calendario) |
| **`Plan_TDD_Fase1.md` / `Plan_TDD_Fase2.md` / `Plan_TDD_Fase3.md`** | Detalle TDD por prompt · Ejecutable | **¿Cómo se construye** cada pieza, paso a paso? (prompts atómicos Red/Green) |

### Trazabilidad principios arquitectónicos → Fases Funcionales

| Principio o pieza arquitectónica | Materialización en la planificación |
| :---- | :---- |
| **§2.1 Determinista-first** (Arquitectura) | Criterio aplicable a todas las fases. Materialización fuerte en **F2.C.5** (Fábricas invocables) y **F3.B.2** (Validador/Crítico) |
| **§2.2 Human-in-the-Loop** | Presente desde **F1** (HITL en chat agente, asistente HITL de ingestión). Se intensifica en **F3.A/B** (NodoHuman en cada tipo de expediente) |
| **§2.3 Frontera Cloud / Edge** | Frontera de aplicación ya establecida (Fases TDD 9.6.5 / 9.6.6). Materialización del Edge real en **F2.A** (Thin Client + Sandbox + Vault). Reglas duras de ejecución de scripts aplicadas en F2.C y F3 |
| **§2.4 Skill & Script Library + autoaprendizaje controlado** | Esqueleto en **F1.A** (Spider Skills + Asistente HITL). Núcleo en **F2.C.3 / F2.C.4 / F2.C.7** (Library + Cache semántico + SkillExtractor). Reuso autónomo en **F3.B** (skills aplicadas a tramitación) |
| **§4 Roles cerrados (SuperAdmin/Admin/Organización/User)** | Refactor de nomenclatura aplicado en código y BD durante **F1**; consolidado al inicio de cada Plan TDD por fase |
| **§5 Templates en cascada Plataforma → Organización → Chatbot** | Implementado en **F1.B.2** (sistema de temas) |
| **§7.2 Privacidad selectiva por políticas** | Modelado en **F1.C.2**; aplicación efectiva en F1.C (informes), F2 (automation) y F3 (expedientes) |
| **§7.3 Vault de identidades en Edge** | Motor migrado en **F1.C.1**; Vault Edge completo en **F2.A.5** cuando exista despliegue Edge real |
| **§9 Gestor de Expedientes (módulo)** | **Fase Funcional 3 íntegra** |

### Lo que NO está en este documento

- **Detalle técnico de cada prompt** → vive en `Plan_TDD_Fase{1,2,3}.md`.
- **Cualquier principio o decisión irreversible** → vive en `docs/Arquitectura.md`.
- **Estado actual de implementación** (qué está hecho ahora mismo, líneas modificadas, tests verdes) → vive en el repositorio (commits, README de cada módulo).

---

## Modelo de licenciamiento

```
┌──────────────────────────────┬──────────────────────────────────┐
│        AGPLv3 (libre)        │  Licencia Comercial (en su caso) │
├──────────────────────────────┼──────────────────────────────────┤
│ Instituciones públicas       │ Partners comerciales             │
│ Auto-hosted / on-premise     │ Soporte y SLA garantizados       │
│ Sin soporte                  │ Integraciones premium            │
│ Contribuciones obligatorias  │ Uso en productos privativos      │
│                              │ Modelo de negocio para partners  │
└──────────────────────────────┴──────────────────────────────────┘
```


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
| Almacenamiento objetos | fsspec + gcsfs/s3fs — GCS en producción, MinIO en dev (misma interfaz) |
| CI/CD | GitHub Actions / Bitbucket Pipelines |
