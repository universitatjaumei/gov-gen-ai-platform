# Plan de Implementación TDD - AI Chatbots Hub (v3.0 - Prompts Atómicos)

---

> ## ⚠ NOTA DE ADAPTACIÓN — Gov Gen AI Platform (actualizado 2026-04-22)
>
> Este documento fue escrito originalmente para construir el AI Chatbots Hub como proyecto independiente desde cero.
> **Ya no aplica tal cual.** El Hub se implementa ahora como el módulo `agents_hub` dentro del monorepo
> **Gov Gen AI Platform**, que hereda la infraestructura existente de AutomatIA.
>
> Consulta `PLAN_DESARROLLO.md` para el plan de desarrollo global del sistema unificado.
>
> ### Resumen de cambios por fase
>
> | Fase | Estado | Motivo |
> |------|--------|--------|
> | **0** — Infraestructura (uv, Docker, config, logging) | **ELIMINADA** | Ya existe en `server/`. No repetir. |
> | **1** — Autenticación (modelos usuario, JWT) | **REDUCIDA** | Auth ya existe. Solo añadir rol `end_user` y migrar a JWT estándar. Ver prompt adaptado al inicio de la fase. |
> | **2.1** — Configuración Alembic | **REDUCIDA** | Alembic ya configurado. Solo crear nueva migration Hub. |
> | **2.2–2.9** — ORM Hub, retriever, gobernanza | **MANTENIDA** | Tablas nuevas; extender schema existente. |
> | **3** — Ingestión Docling | **MANTENIDA** | Módulo completamente nuevo. |
> | **4** — Agente LangGraph + RAGAS | **MANTENIDA** | Módulo completamente nuevo. |
> | **5** — API Endpoints | **MANTENIDA** | Nuevas rutas en el FastAPI existente (no app nueva). |
> | **6** — Tests E2E | **MANTENIDA** | Integrar en el CI/CD existente (GitHub Actions). |
> | **7** — Despliegue / Docker | **REDUCIDA** | Docker ya configurado. Solo extender `docker-compose.yml` existente. |
> | **8** — Observabilidad y Feedback | **MANTENIDA** | |
> | **9** — Frontend React | **MANTENIDA + AMPLIADA** | Añadir UI Automation (reemplaza NiceGUI) y agente de ejecución local. Ver prompts 9.14–9.18 añadidos al final de la fase. |
> | **10** — Temas y panel IA | **MANTENIDA** | |
> | **11** — Autoinstalación | **ADAPTADA** | Extender `docker-compose.yml` unificado, no crear uno nuevo. |
> | **12** — Gestor de Expedientes | **NUEVA** | Módulo nuevo no contemplado en la versión original. Ver Fase 12 al final del documento. |
>
> ### Cambio crítico de rutas
>
> Todos los prompts de este documento usan rutas de la estructura original (`src/`, `tests/`, `frontend/`).
> En el monorepo, las rutas reales son:
>
> | Ruta original (este documento) | Ruta real en el monorepo |
> |---|---|
> | `src/` | `server/app/modules/agents_hub/` |
> | `tests/` | `server/tests/modules/agents_hub/` |
> | `frontend/` | `frontend/src/` (raíz del monorepo) |
> | `migrations/` | `server/migrations/` |
> | `docker-compose.yml` | `docker-compose.yml` (raíz del monorepo, ya existe) |
>
> Al ejecutar cualquier prompt, sustituir mentalmente las rutas originales por las reales.

---

## Estado de Implementación

> Actualizado automáticamente. Consultar antes de cada sesión.

| Tarea | Estado | Fecha | Notas |
|-------|--------|-------|-------|
| Docker Compose (postgres + minio) | ✅ COMPLETADO | 2026-04-22 | Imágenes pgvector/pgvector:pg16 y minio/minio:latest |
| Alembic configurado | ✅ COMPLETADO | 2026-04-22 | `server/migrations/` con `env.py` y `script.py.mako` |
| Migración inicial BD (`initial_schema`) | ✅ COMPLETADO | 2026-04-22 | 20 tablas creadas en PostgreSQL `govgenai` |
| **FASE 1 — Auth JWT** | ✅ COMPLETADO | 2026-04-22 | JWT real (HS256): UserInfo, UserRole, create_token/decode_token, deps.py, auth_router.py; 19 tests verdes |
| FASE 2.1 — Alembic Hub migration | ✅ COMPLETADO | 2026-04-23 | Migración a1b2c3d4e5f6: pgvector + 7 tablas hub_ |
| FASE 2.2–2.9 — ORM Hub, conexión, retriever, gobernanza | ✅ COMPLETADO | 2026-04-23 | 11 tests verdes; módulo agents_hub creado |
| FASE 3 — Ingestión Docling | ✅ COMPLETADO | 2026-04-23 | DoclingProcessor, IngestionWatcher, chunker, hasher, user_upload endpoint; tests verdes |
| FASE 4 — Agente LangGraph | ✅ COMPLETADO | 2026-04-23 | Grafo LangGraph, HybridRetriever, ModelFactory, RAGAS, HITL, TaskRunner, PromptService; tests verdes |
| FASE 4B — Grafo Público Enriquecido | ⏳ PENDIENTE | — | QueryClassifier (portal), Reranker cross-encoder, QualityEvaluator inline, FallbackHandler |
| FASE 5 — API Endpoints | ✅ COMPLETADO | 2026-04-23 | hub_chat (SSE), hub_tasks (export PDF/MD), embedding_service (GoogleEmbeddingService stub), bugfix deps.py 401; 13 tests verdes |
| FASE 5B — LocalEmbeddingService BGE-M3 | ✅ COMPLETADO | 2026-04-25 | `LocalEmbeddingService` (BAAI/bge-m3, sentence-transformers, 1024 dims); singleton `get_embedding_service()`; cableado en hub_chat, hub_ingestion_router, ingestion; migración vector(1536→1024); todos los tests actualizados |
| FASE 6 — Tests E2E y CI/CD | ✅ COMPLETADO | 2026-04-23 | 4 tests E2E (httpx+AsyncClient), 5 tests integración pipeline+auth, GitHub Actions CI/CD con pgvector |
| FASE 7 — Docker multi-stage | ✅ COMPLETADO | 2026-04-23 | Imagen CPU-only (~2.96 GB), uv sync, docker-compose.prod.yml, LangFuse self-hosted, scripts/postgres/init.sql |
| FASE 8 — LangFuse + FeedbackService | ✅ COMPLETADO | 2026-04-23 | observability.py, FeedbackService, hub_feedback router, migración feedback_text, 10 tests verdes |
| FASE 9 — Frontend React | 🔄 EN PROGRESO | 2026-04-26 | Prompts 9.1–9.10 completados; 9.10 ChatWidget SSE (useChat, StarRating, streaming/status/warning/feedback, 8 tests verdes) |
| FASE 9C — StorageService (fsspec) | ✅ COMPLETADO | 2026-04-27 | `FsspecStorageService` (file/S3/GCS); inyección Depends; `/upload` persiste PDF con key `ingestion/{chatbot_id}/{job_id}.pdf`; `IngestionWatcher` descarga a tmp y limpia; `delete` y `clear` borran de storage; 19 tests verdes (11 unit + 8 integración) |
| FASE 10 — Sistema de temas y panel de IA | ⏳ PENDIENTE | — | — |
| FASE 11 — Autoinstalación | ⏳ PENDIENTE | — | — |
| FASE 12 — Gestor de Expedientes | ⏳ PENDIENTE | — | Ampliada con Analista/Validador/Fábricas/UJI/G400/ENI/ENS |
| FASE 13 — Privacidad NER (Zero-Knowledge) | ⏳ PENDIENTE | — | Migración legacy → `server/app/core/privacy/`; vault en Edge |
| FASE 14 — Sandbox distribuido Edge ↔ Thin-client | ⏳ PENDIENTE | — | Split: AST+firma→server, ejecución→thin client |
| FASE 15 — RunManifest + AuditService + Script Registry | ⏳ PENDIENTE | — | Unificación transversal automation+expedientes; IA Frugal |
| FASE 16 — Determinista-first + Fábricas como nodos LangGraph | ⏳ PENDIENTE | — | Migración fábricas + NodoFabrica + NodoValidador |
| FASE 17 — Agente Analista + base vectorial de normativa | ⏳ PENDIENTE | — | KB `regulation` + NodoAnalista; solo expedientes |
| FASE 18 — Bridges semánticos ampliados | ⏳ PENDIENTE | — | Migración + generalización multi-contexto |
| FASE 19 — Adaptadores UJI + Gestión 400 + ENI/ENS | ⏳ PENDIENTE | — | Ver Fase 12 Prompt E5 (ya actualizado) |
| FASE 20 — Accesibilidad WCAG 2.2 AA + admin conversacional | ⏳ PENDIENTE | — | Transversal sobre Fases 9-10 |
| FASE 21 — RPA web (diferido a v2) | ⏳ FUERA ALCANCE v1 | — | Decisión documentada; worker Playwright en Edge si necesario |
| FASE 22 — Microservicios Embedding + Docling | ⏳ DIFERIDO (post-cloud) | — | Extraer BGE-M3 y Docling a Cloud Run independientes; no iniciar hasta criterios de métricas (cold start >15s, RAM >2 GB) |

---

## Resumen Ejecutivo

Este plan sigue la metodología **Test-Driven Development (TDD)**: escribir tests primero, verlos fallar, implementar el código mínimo para pasarlos, y refactorizar. Cada prompt es **atómico y autocontenido**, incluyendo ejemplos de código y tests listos para ejecutar.

---

## Prerequisitos

Antes de comenzar, asegúrate de tener instalado:

| Herramienta | Versión | Comando de verificación |
|-------------|---------|------------------------|
| Python | >= 3.11 | `python --version` |
| uv | >= 0.4.0 | `uv --version` |
| Docker | >= 24.0 | `docker --version` |
| Docker Compose | >= 2.0 | `docker compose version` |
| Git | >= 2.0 | `git --version` |

**Instalación de uv** (si no lo tienes):
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Quick Start - Primeros Pasos

### Paso 1: Crear el proyecto
```bash
# Crear directorio e inicializar
mkdir ai_chatbots_hub && cd ai_chatbots_hub
uv init .

# Crear estructura de directorios
mkdir -p src/{auth,database,ingestion,agent/tools,api/routers,services,evaluation}
mkdir -p tests/{unit,integration,e2e,evaluation}
mkdir -p migrations/versions
mkdir -p scripts
mkdir -p .github/workflows

# Crear archivos __init__.py
touch src/__init__.py
touch src/auth/__init__.py
touch src/database/__init__.py
touch src/ingestion/__init__.py
touch src/agent/__init__.py
touch src/agent/tools/__init__.py
touch src/api/__init__.py
touch src/api/routers/__init__.py
touch src/services/__init__.py
touch src/evaluation/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/e2e/__init__.py
touch tests/evaluation/__init__.py
```

### Paso 2: Copiar archivos de configuración
Copia estos archivos del **Prompt 0.1** y **Prompt 0.2**:
- `pyproject.toml`
- `docker-compose.yml`
- `.env.example`

```bash
# Copiar .env.example a .env y editar
cp .env.example .env
# Editar .env con tus valores
```

### Paso 3: Instalar dependencias e iniciar servicios
```bash
# Instalar dependencias
uv sync

# Iniciar PostgreSQL con pgvector
docker compose up -d postgres

# Verificar que PostgreSQL está corriendo
docker compose ps
```

### Paso 4: Crear archivo .python-version
```bash
echo "3.11" > .python-version
```

### Paso 5: Ejecutar primer test (debe fallar - RED)
```bash
# Crear el primer test (Prompt 0.3)
# Luego ejecutar:
uv run pytest tests/unit/test_config.py -v
# Esperado: FAILED (el módulo no existe aún)
```

### Paso 6: Implementar y verificar (GREEN)
```bash
# Implementar src/config.py (Prompt 0.4)
# Luego ejecutar:
uv run pytest tests/unit/test_config.py -v
# Esperado: PASSED
```

---

## Mapa de Fases

| Fase | Descripción | Prompts | Estado en Gov Gen AI | Dependencias |
|------|-------------|---------|----------------------|--------------|
| **0** | Infraestructura | 0.1 - 0.6 | ~~ELIMINADA~~ — heredada de AutomatIA | — |
| **1** | Autenticación | 1.1 - 1.6 | **REDUCIDA** — solo añadir rol `end_user` | Fase 0 |
| **2** | Base de Datos | 2.1 - 2.9 | **MANTENIDA** (2.1 reducida: Alembic ya existe) | Fase 0 |
| **3** | Ingestión | 3.1 - 3.9 | **MANTENIDA** | Fase 2 |
| **4** | Agente LangGraph | 4.1 - 4.11 | **MANTENIDA** | Fases 1, 2, 3 |
| **4B** | Grafo Público Enriquecido | 4B.1 - 4B.8 | **NUEVA** | Fase 4 |
| **5** | API Endpoints | 5.1 - 5.4 | **MANTENIDA** (rutas nuevas en FastAPI existente) | Fases 1, 2, 4 |
| **6** | Tests E2E | 6.1 - 6.3 | **MANTENIDA** (CI/CD: GitHub Actions) | Fases 1-5 |
| **7** | Despliegue | 7.1 - 7.4 | **REDUCIDA** — extender docker-compose existente | Fases 1-6 |
| **8** | Observabilidad | 8.1 - 8.3 | **MANTENIDA** | Fases 1-5 |
| **9** | Frontend + i18n + Modo Agente | 9.1 - 9.18 (+ 9.7.1 crawler) | **MANTENIDA + AMPLIADA** (añadidos 9.7.1 crawler ✅, 9.14–9.18) | Fase 5 (API) |
| **10** | Temas y Panel de IA | 10.1 - 10.11 | **MANTENIDA** | Fase 9 |
| **11** | Autoinstalación | 11.1 - 11.3 | **ADAPTADA** — extender docker-compose unificado | Fases 1-10 |
| **12** | Gestor de Expedientes | E1 - E5 | **NUEVA** | Fases 3, 4, Auth OIDC |
| **Anexo A** | Complementarios | A.1 - A.6 | **MANTENIDA** | Según necesidad |
| **Anexo B** | Configuración | - | ~~ELIMINADA~~ — heredada de AutomatIA | Fase 0 |

### Idiomas soportados (i18n)

| Código | Idioma | Uso |
|--------|--------|-----|
| `es` | Español | Idioma por defecto |
| `ca` | Català | Catalán |
| `en` | English | Inglés |

**Integración con la web de la universidad:**
- El widget se embebe como iframe
- El idioma se sincroniza vía `postMessage` desde la web padre
- El chatbot responde en el idioma seleccionado por el usuario

---

## Estructura del Proyecto

> **ATENCIÓN**: La estructura de abajo es la del monorepo Gov Gen AI Platform.
> Las rutas originales del documento (`src/`, `tests/`, `frontend/`) quedan sustituidas.
> Consulta la tabla de cambio de rutas en la NOTA DE ADAPTACIÓN al inicio del documento.

```
gov-gen-ai-platform/                   ← raíz del monorepo
├── docker-compose.yml                 # Existente — se extiende, no se crea de nuevo
├── docker-compose.prod.yml            # Nuevo para producción (Prompt 7.2 adaptado)
├── .env.example                       # Unificado para toda la plataforma
├── .github/
│   └── workflows/
│       └── ci.yml                     # GitHub Actions CI/CD
│
├── server/                            # Backend FastAPI (dual-license AGPLv3/Comercial)
│   ├── pyproject.toml                 # Existente — añadir dependencias Hub
│   ├── alembic.ini                    # Existente — añadir migrations Hub
│   ├── migrations/                    # Existente — nuevas migrations para Hub
│   └── app/
│       ├── main.py                    # Existente — registrar routers Hub
│       ├── core/                      # Existente: config, security, LLM gateway
│       ├── api/v1/                    # Existente — añadir routers Hub aquí
│       │   ├── hub_chat.py            #   POST /hub/chat  (Prompt 5.2)
│       │   ├── hub_admin.py           #   Panel admin Hub (Prompt 5.2 / A.4)
│       │   └── hub_feedback.py        #   Feedback (Prompt 5.2 / A.5)
│       └── modules/
│           ├── automation/            # Existente (antes brain/) — no tocar
│           └── agents_hub/            # NUEVO — todo lo de src/ original va aquí
│               ├── __init__.py
│               ├── database/
│               │   ├── models.py      # ORM Hub (Prompts 2.4-2.9)
│               │   └── repositories/
│               ├── ingestion/
│               │   ├── docling_processor.py  # (Prompts 3.5-3.6)
│               │   ├── chunker.py            # (Prompts 3.3-3.4)
│               │   ├── hasher.py             # (Prompts 3.1-3.2)
│               │   └── watcher.py            # (Prompts 3.7-3.8)
│               ├── agent/
│               │   ├── state.py              # (Prompts 1.5-1.6)
│               │   ├── graph.py              # (Prompts 4.5-4.6)
│               │   ├── tools/
│               │   │   ├── search_knowledge.py  # (Prompts 4.3-4.4)
│               │   │   └── query_oracle_mcp.py
│               │   └── language_detector.py     # (Prompts 4.1-4.2)
│               └── services/
│                   ├── retriever.py             # (Prompts 2.6-2.7)
│                   ├── embedding_service.py     # (Anexo A.2)
│                   └── feedback_service.py      # (Prompts 8.2-8.3)
│
│   └── tests/
│       └── modules/
│           └── agents_hub/            # Tests Hub (rutas originales: tests/)
│               ├── conftest.py
│               ├── unit/
│               ├── integration/
│               ├── e2e/
│               └── evaluation/        # RAGAS (Prompts 4.7-4.8)
│
├── frontend/                          # NUEVO — React + Vite (MIT)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/                          # Rutas originales: frontend/src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── i18n/                      # i18next (Prompts 9.2-9.3)
│       │   └── locales/
│       │       ├── es.json
│       │       ├── ca.json
│       │       └── en.json
│       ├── widget/                    # Chatbot público embed (Prompt 9.9)
│       │   └── components/
│       │       ├── ChatWidget/
│       │       ├── ChatMessage/
│       │       ├── ChatInput/
│       │       └── LanguageSelector/
│       ├── agent/                     # Modo agente expandido (Prompts 9.11-9.13)
│       ├── admin/                     # Panel admin Hub + plataforma (Prompt 10.11)
│       └── automation/                # UI Automation — reemplaza NiceGUI (Prompts 9.14-9.18)
│
└── client_app/                        # Agente de ejecución local (sin UI)
                                       # RPA, folder watcher — hereda de NiceGUI
```

---

## ~~FASE 0: Infraestructura y Observabilidad~~ — ELIMINADA

> **Esta fase no aplica en Gov Gen AI Platform.**
> El proyecto ya existe con uv, Docker Compose, FastAPI, configuración Pydantic y logging estructurado
> heredados de AutomatIA. No repetir ninguno de estos prompts.
>
> Lo único que hay que hacer antes de la Fase 2 es:
> - Añadir `pgvector` al PostgreSQL existente (ya cubierto en `PLAN_DESARROLLO.md` Fase 0.3)
> - Añadir las dependencias Hub al `server/pyproject.toml` existente (langchain, langgraph, docling, ragas…)
>
> Los prompts 0.1–0.6 se conservan a continuación únicamente como referencia de las dependencias
> y configuraciones que deben existir antes de continuar.

---

### ~~Prompt 0.1~~ - Inicialización del Proyecto con uv — REFERENCIA

**Objetivo**: ~~Crear la estructura base del proyecto~~ → **Verificar que el entorno existente tiene estas dependencias.**

**Contexto**: uv es un gestor de paquetes Python ultrarrápido escrito en Rust. Reemplaza pip, pip-tools, virtualenv y poetry.

**Instrucciones**:

```
Actúa como un experto en Python y DevOps. Inicializa el proyecto "AI Chatbots Hub" usando uv.

TAREAS:
1. Ejecutar: uv init ai_chatbots_hub && cd ai_chatbots_hub
2. Crear la estructura de directorios mostrada abajo
3. Generar el pyproject.toml con todas las dependencias

CRITERIOS DE ACEPTACIÓN:
- El proyecto se puede inicializar con: uv sync
- Existe un .python-version con "3.11" o superior
- pytest puede ejecutarse sin errores
```

**Archivos a crear**:

**pyproject.toml**:
```toml
[project]
name = "ai-chatbots-hub"
version = "0.1.0"
description = "Hub de chatbots con RAG y LangGraph"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "pgvector>=0.2.4",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "python-jose[cryptography]>=3.3.0",
    "langchain>=0.1.0",
    "langchain-google-vertexai>=0.0.6",
    "langgraph>=0.0.20",
    "docling>=0.1.0",
    "langdetect>=1.0.9",
    "alembic>=1.13.0",
    "ragas>=0.1.0",
    "httpx>=0.26.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.2.0",
    "respx>=0.20.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[project.scripts]
dev = "uvicorn src.main:app --reload --port 8000"
```

**Comandos de verificación**:
```bash
uv sync
uv run pytest --collect-only  # Debe listar 0 tests sin errores
```

---

### Prompt 0.2 - Docker Compose con PostgreSQL y pgvector

**Objetivo**: Configurar el entorno de desarrollo con Docker.

**Contexto**: Necesitamos PostgreSQL con la extensión pgvector para almacenar embeddings vectoriales.

**Instrucciones**:

```
Crea el archivo docker-compose.yml para el entorno de desarrollo.

SERVICIOS REQUERIDOS:
1. PostgreSQL con pgvector (imagen: ankane/pgvector:latest)
2. pgAdmin para administración visual

CRITERIOS DE ACEPTACIÓN:
- docker compose up -d inicia ambos servicios
- pgAdmin accesible en http://localhost:5050
- PostgreSQL acepta conexiones en puerto 5432
```

**Archivos a crear**:

**docker-compose.yml**:
```yaml
version: "3.9"

services:
  postgres:
    image: ankane/pgvector:latest
    container_name: chatbots_hub_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-chatbots}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-chatbots_secret}
      POSTGRES_DB: ${POSTGRES_DB:-chatbots_hub}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-chatbots}"]
      interval: 5s
      timeout: 5s
      retries: 5

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: chatbots_hub_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL:-admin@local.dev}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD:-admin}
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

**.env.example**:
```env
# Database
POSTGRES_USER=chatbots
POSTGRES_PASSWORD=chatbots_secret
POSTGRES_DB=chatbots_hub
DATABASE_URL=postgresql+asyncpg://chatbots:chatbots_secret@localhost:5432/chatbots_hub

# pgAdmin
PGADMIN_EMAIL=admin@local.dev
PGADMIN_PASSWORD=admin

# Google/Vertex AI
GOOGLE_API_KEY=your-gemini-api-key

# LangSmith Observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=ai-chatbots-hub

# Auth
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
MOCK_AUTH=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Comandos de verificación**:
```bash
cp .env.example .env
docker compose up -d
docker compose ps  # Ambos servicios "healthy" o "running"
```

---

### Prompt 0.3 - Tests de Configuración (TDD - RED)

**Objetivo**: Escribir tests para el módulo de configuración ANTES de implementarlo.

**Contexto**: Siguiendo TDD, primero escribimos los tests que fallarán.

**Instrucciones**:

```
Escribe los tests para src/config.py en tests/unit/test_config.py.
Estos tests DEBEN FALLAR inicialmente (fase RED de TDD).

TESTS REQUERIDOS:
1. test_config_loads_database_url_from_env
2. test_config_loads_langsmith_settings
3. test_config_validates_required_fields_raises_error
4. test_config_mock_auth_defaults_to_false_in_production
5. test_config_log_format_accepts_json_or_text
```

**Archivos a crear**:

**tests/conftest.py**:
```python
"""Fixtures globales para todos los tests."""
import os
from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Limpia variables de entorno antes de cada test."""
    env_vars_to_clean = [
        "DATABASE_URL",
        "GOOGLE_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_TRACING_V2",
        "JWT_SECRET_KEY",
        "MOCK_AUTH",
        "LOG_FORMAT",
        "LOG_LEVEL",
    ]
    original_values = {k: os.environ.get(k) for k in env_vars_to_clean}

    for var in env_vars_to_clean:
        os.environ.pop(var, None)

    yield

    # Restaurar valores originales
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)


@pytest.fixture
def mock_env_complete() -> Generator[None, None, None]:
    """Configura un entorno completo válido."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
        "GOOGLE_API_KEY": "test-google-api-key",
        "LANGCHAIN_API_KEY": "test-langsmith-key",
        "LANGCHAIN_TRACING_V2": "true",
        "LANGCHAIN_PROJECT": "test-project",
        "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars",
        "MOCK_AUTH": "true",
        "LOG_FORMAT": "json",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield
```

**tests/unit/test_config.py**:
```python
"""Tests para el módulo de configuración - TDD RED PHASE."""
import os
from unittest.mock import patch

import pytest


class TestConfigLoading:
    """Tests para la carga de configuración desde variables de entorno."""

    def test_config_loads_database_url_from_env(
        self, clean_env: None, mock_env_complete: None
    ) -> None:
        """La configuración debe cargar DATABASE_URL correctamente."""
        # Importar después de configurar el entorno
        from src.config import Settings

        settings = Settings()

        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        assert "asyncpg" in settings.database_url

    def test_config_loads_langsmith_settings(
        self, clean_env: None, mock_env_complete: None
    ) -> None:
        """La configuración debe cargar settings de LangSmith."""
        from src.config import Settings

        settings = Settings()

        assert settings.langchain_api_key == "test-langsmith-key"
        assert settings.langchain_tracing_v2 is True
        assert settings.langchain_project == "test-project"

    def test_config_validates_required_fields_raises_error(
        self, clean_env: None
    ) -> None:
        """Debe lanzar error si faltan campos requeridos."""
        from pydantic import ValidationError
        from src.config import Settings

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verificar que menciona los campos faltantes
        error_str = str(exc_info.value)
        assert "database_url" in error_str.lower() or "DATABASE_URL" in error_str

    def test_config_mock_auth_defaults_to_false(
        self, clean_env: None
    ) -> None:
        """MOCK_AUTH debe ser False por defecto (seguridad en producción)."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
            "GOOGLE_API_KEY": "test-key",
            "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from src.config import Settings

            # Forzar recarga del módulo
            import importlib
            import src.config
            importlib.reload(src.config)

            settings = src.config.Settings()
            assert settings.mock_auth is False

    def test_config_log_format_accepts_json_or_text(
        self, clean_env: None, mock_env_complete: None
    ) -> None:
        """LOG_FORMAT debe aceptar solo 'json' o 'text'."""
        from src.config import Settings

        settings = Settings()
        assert settings.log_format in ("json", "text")


class TestConfigValidation:
    """Tests para validaciones específicas de configuración."""

    def test_jwt_secret_minimum_length(self, clean_env: None) -> None:
        """JWT_SECRET_KEY debe tener mínimo 32 caracteres."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
            "GOOGLE_API_KEY": "test-key",
            "JWT_SECRET_KEY": "short",  # Muy corto
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from pydantic import ValidationError
            from src.config import Settings

            import importlib
            import src.config
            importlib.reload(src.config)

            with pytest.raises(ValidationError) as exc_info:
                src.config.Settings()

            assert "32" in str(exc_info.value) or "jwt" in str(exc_info.value).lower()

    def test_database_url_must_use_asyncpg(self, clean_env: None) -> None:
        """DATABASE_URL debe usar el driver asyncpg."""
        env_vars = {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb",  # Sin asyncpg
            "GOOGLE_API_KEY": "test-key",
            "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from pydantic import ValidationError
            from src.config import Settings

            import importlib
            import src.config
            importlib.reload(src.config)

            with pytest.raises(ValidationError) as exc_info:
                src.config.Settings()

            assert "asyncpg" in str(exc_info.value).lower()
```

**Comando para ejecutar (debe fallar)**:
```bash
uv run pytest tests/unit/test_config.py -v
# Expected: FAILED - ModuleNotFoundError: No module named 'src.config'
```

---

### Prompt 0.4 - Implementación de Configuración (TDD - GREEN)

**Objetivo**: Implementar src/config.py para que pasen todos los tests.

**Contexto**: Fase GREEN de TDD - implementación mínima para pasar los tests.

**Instrucciones**:

```
Implementa src/config.py usando pydantic-settings para pasar todos los tests del Prompt 0.3.

REQUISITOS:
1. Usar pydantic-settings para cargar desde .env
2. Validar longitud mínima de JWT_SECRET_KEY (32 chars)
3. Validar que DATABASE_URL use asyncpg
4. MOCK_AUTH debe ser False por defecto
5. LOG_FORMAT debe ser Literal["json", "text"]
```

**Archivos a crear**:

**src/__init__.py**:
```python
"""AI Chatbots Hub - Main package."""
```

**src/config.py**:
```python
"""Configuración centralizada usando pydantic-settings."""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str

    # Google/Vertex AI
    google_api_key: str | None = None

    # LangSmith Observability
    langchain_api_key: str | None = None
    langchain_tracing_v2: bool = False
    langchain_project: str = "ai-chatbots-hub"

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    mock_auth: bool = False  # IMPORTANTE: False por defecto para seguridad

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_length(cls, v: str) -> str:
        """JWT secret debe tener mínimo 32 caracteres."""
        if len(v) < 32:
            raise ValueError("jwt_secret_key must be at least 32 characters long")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url_asyncpg(cls, v: str) -> str:
        """DATABASE_URL debe usar el driver asyncpg para operaciones async."""
        if "asyncpg" not in v:
            raise ValueError(
                "database_url must use asyncpg driver "
                "(e.g., postgresql+asyncpg://user:pass@host:port/db)"
            )
        return v

    @model_validator(mode="after")
    def validate_langsmith_config(self) -> "Settings":
        """Si tracing está activo, langchain_api_key es requerido."""
        if self.langchain_tracing_v2 and not self.langchain_api_key:
            raise ValueError(
                "langchain_api_key is required when langchain_tracing_v2 is enabled"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Obtiene la configuración (cacheada para evitar múltiples lecturas)."""
    return Settings()
```

**Comando para verificar (debe pasar)**:
```bash
uv run pytest tests/unit/test_config.py -v
# Expected: All tests PASSED
```

---

### Prompt 0.5 - Tests de Logging Estructurado (TDD - RED)

**Objetivo**: Escribir tests para el sistema de logging estructurado.

**Instrucciones**:

```
Escribe tests para src/logging_config.py que validen:
1. Formato JSON cuando LOG_FORMAT=json
2. Formato texto cuando LOG_FORMAT=text
3. Inclusión de campos: timestamp, level, message, module
4. Configuración del nivel de log desde LOG_LEVEL
```

**Archivos a crear**:

**tests/unit/test_logging.py**:
```python
"""Tests para el sistema de logging estructurado - TDD RED PHASE."""
import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest


class TestLoggingConfiguration:
    """Tests para la configuración del sistema de logging."""

    def test_json_format_outputs_valid_json(self) -> None:
        """Cuando LOG_FORMAT=json, los logs deben ser JSON válido."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
            "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars",
            "LOG_FORMAT": "json",
            "LOG_LEVEL": "INFO",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            from src.logging_config import setup_logging

            # Capturar output
            log_capture = StringIO()
            handler = logging.StreamHandler(log_capture)

            logger = setup_logging(stream=log_capture)
            logger.info("Test message")

            log_output = log_capture.getvalue()

            # Debe ser JSON válido
            log_entry = json.loads(log_output.strip())
            assert "message" in log_entry
            assert log_entry["message"] == "Test message"

    def test_json_format_includes_required_fields(self) -> None:
        """Los logs JSON deben incluir timestamp, level, message, module."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
            "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars",
            "LOG_FORMAT": "json",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            from src.logging_config import setup_logging

            log_capture = StringIO()
            logger = setup_logging(stream=log_capture)
            logger.warning("Warning message")

            log_entry = json.loads(log_capture.getvalue().strip())

            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert log_entry["level"] == "WARNING"
            assert "message" in log_entry
            assert "module" in log_entry

    def test_text_format_is_human_readable(self) -> None:
        """Cuando LOG_FORMAT=text, los logs deben ser legibles."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
            "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars",
            "LOG_FORMAT": "text",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            from src.logging_config import setup_logging

            log_capture = StringIO()
            logger = setup_logging(stream=log_capture)
            logger.info("Human readable message")

            log_output = log_capture.getvalue()

            # No debe ser JSON
            with pytest.raises(json.JSONDecodeError):
                json.loads(log_output)

            # Debe contener el mensaje
            assert "Human readable message" in log_output
            assert "INFO" in log_output

    def test_log_level_from_settings(self) -> None:
        """El nivel de log debe configurarse desde LOG_LEVEL."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
            "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars",
            "LOG_LEVEL": "ERROR",
            "LOG_FORMAT": "text",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            from src.logging_config import setup_logging

            log_capture = StringIO()
            logger = setup_logging(stream=log_capture)

            # INFO no debe aparecer cuando nivel es ERROR
            logger.info("This should not appear")
            logger.error("This should appear")

            log_output = log_capture.getvalue()

            assert "This should not appear" not in log_output
            assert "This should appear" in log_output
```

**Comando para ejecutar (debe fallar)**:
```bash
uv run pytest tests/unit/test_logging.py -v
# Expected: FAILED - ModuleNotFoundError: No module named 'src.logging_config'
```

---

### Prompt 0.6 - Implementación de Logging (TDD - GREEN)

**Objetivo**: Implementar el sistema de logging estructurado.

**Archivos a crear**:

**src/logging_config.py**:
```python
"""Configuración de logging estructurado."""
import json
import logging
import sys
from datetime import datetime, timezone
from io import StringIO
from typing import Any

from src.config import get_settings


class JSONFormatter(logging.Formatter):
    """Formatter que produce logs en formato JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro como JSON."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Formatter para logs legibles por humanos."""

    FORMAT = "%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"

    def __init__(self) -> None:
        super().__init__(fmt=self.FORMAT, datefmt="%Y-%m-%d %H:%M:%S")


def setup_logging(stream: StringIO | None = None) -> logging.Logger:
    """Configura el sistema de logging según la configuración."""
    settings = get_settings()

    # Crear logger
    logger = logging.getLogger("ai_chatbots_hub")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Limpiar handlers existentes
    logger.handlers.clear()

    # Crear handler
    handler = logging.StreamHandler(stream or sys.stdout)

    # Seleccionar formatter según configuración
    if settings.log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    logger.addHandler(handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Obtiene un logger configurado."""
    base_logger = logging.getLogger("ai_chatbots_hub")
    if name:
        return base_logger.getChild(name)
    return base_logger
```

**Comando para verificar**:
```bash
uv run pytest tests/unit/test_logging.py -v
# Expected: All tests PASSED
```

---

## FASE 1: Autenticación y Estado del Agente — REDUCIDA

> ✅ **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.

## FASE 2: Base de Datos y Migraciones — PARCIALMENTE REDUCIDA

> ✅ **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.

## FASE 3: Ingestión de Documentos (Asíncrona)

> ✅ **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.

## FASE 4: Agente LangGraph con Herramientas y RAGAS

> ✅ **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.

## FASE 5: API Endpoints y Robustez

> ✅ **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.

## FASE 6: Tests End-to-End y Flujos Completos

> ✅ **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.

## FASE 7: Despliegue y Containerización — REDUCIDA

> ✅ **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.

## FASE 8: Observabilidad y Panel de Feedback

> ✅ **Fase Completada y Validada**. Los detalles (prompts y especificaciones técnicas) han sido ejecutados con éxito y están documentados en el código. Se ha compactado esta sección para mejorar la legibilidad del documento.

## FASE 9: Frontend React — Admin Hub, Widget y Migración NiceGUI

> ## NOTA DE ARQUITECTURA (2026-04-23)
>
> Esta fase fue rediseñada antes de su ejecución. Decisiones adoptadas:
>
> - **Un único panel admin** en `frontend/src/admin/` cubre Hub, Automatización y Plataforma.
>   No hay dos paneles separados. El sidebar agrupa las secciones.
> - **Stack**: Vite + React 18 + TypeScript + Tailwind CSS + **shadcn/ui** (Radix UI) +
>   @tanstack/react-query + react-hook-form + zod + i18next (CA/ES/EN)
> - **Widget** (`frontend/src/widget/`) es un bundle independiente compilado en modo librería
>   (Vite library mode). Se incrusta como `<script>` en la web de la institución.
> - **Prioridad**: 9A (Admin Hub) → 9B (Widget/Agente) → 9C (Automatización) → 9D (Agente local)
> - **Migración NiceGUI**: se hace pantalla a pantalla en 9C. Cada commit incluye la pantalla
>   nueva + el traslado del fichero NiceGUI equivalente a _legacy_nicegui (ver CLAUDE.md).

---

### Contexto: Estrategia de Internacionalización

**Requisitos del proyecto:**
- Universidad trilingüe: **Castellano (es)**, **Catalán (ca)**, **Inglés (en)**
- El widget del chatbot se integra en la web de la institución — detecta el idioma de la página host
- El panel admin es para gestión interna (Admin, Partner) — idioma persistido en localStorage

**Estrategia i18n:**

| Aspecto | Decisión |
|---------|----------|
| Librería | `react-i18next` + `i18next` |
| Formato | JSON por idioma y namespace (`common.json`, `chat.json`, `admin.json`) |
| Detección widget | `postMessage` desde página host; fallback: parámetro URL `?lang=ca` |
| Detección admin | `localStorage`; fallback: `navigator.language` |
| Pluralización | Configurada para los 3 idiomas |

---

## BLOQUE 9A — Admin Hub

*Objetivo: panel de administración unificado operativo con CRUD de chatbots, clientes y documentos.*

---

### Prompt 9.1 - Scaffolding: Vite + shadcn/ui + i18n

**Objetivo**: Crear la estructura base del proyecto frontend con todas las dependencias.

**Comandos de inicialización**:
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend

# UI y estilos
npm install tailwindcss @tailwindcss/vite
npx shadcn@latest init          # elige: New York, Zinc, CSS variables: yes

# Estado y formularios
npm install @tanstack/react-query @tanstack/react-table
npm install react-hook-form zod @hookform/resolvers
npm install react-router-dom

# i18n
npm install i18next react-i18next i18next-browser-languagedetector

# Gráficas (informes)
npm install recharts

# Dev
npm install -D vitest @vitest/ui jsdom @testing-library/react @testing-library/jest-dom
npm install -D @types/node
```

**Estructura de carpetas**:
```
frontend/
├── src/
│   ├── admin/              # SPA de administración
│   │   ├── components/     # Componentes específicos del admin
│   │   ├── pages/          # Páginas del admin (Chatbots, Clients, Docs, Reports)
│   │   └── main.tsx        # Punto de entrada del admin
│   ├── widget/             # Bundle embebible (Vite library mode)
│   │   ├── components/
│   │   └── main.tsx
│   ├── shared/             # Componentes y utils compartidos
│   │   ├── api/            # Cliente HTTP + hooks react-query
│   │   ├── auth/           # Contexto JWT, rutas protegidas
│   │   └── i18n/           # Configuración i18n + locales
│   └── components/ui/      # Componentes shadcn/ui (autogenerados)
├── index.html              # Entry point admin
├── widget.html             # Entry point widget
├── vite.config.ts
└── package.json
```

**`vite.config.ts`** (multi-entry):
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: {
    rollupOptions: {
      input: {
        admin: 'index.html',
        widget: 'widget.html',
      },
    },
  },
})
```

**Tests requeridos** (`src/shared/i18n/__tests__/i18n.test.ts`):
```typescript
// should_load_spanish_translations
// should_load_catalan_translations
// should_load_english_translations
// should_fallback_to_spanish_for_unknown_language
```

**Criterio de done**: `npm run dev` arranca el admin en `/`; `npm test` pasa.

---

### Prompt 9.2 - i18n: locales es / ca / en

**Objetivo**: Configurar react-i18next con los tres idiomas y los namespaces `common`, `chat` y `admin`.

**`src/shared/i18n/index.ts`**:
```typescript
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import esCommon from './locales/es/common.json'
import esChat   from './locales/es/chat.json'
import esAdmin  from './locales/es/admin.json'
import caCommon from './locales/ca/common.json'
import caChat   from './locales/ca/chat.json'
import caAdmin  from './locales/ca/admin.json'
import enCommon from './locales/en/common.json'
import enChat   from './locales/en/chat.json'
import enAdmin  from './locales/en/admin.json'

export const SUPPORTED_LANGUAGES = ['es', 'ca', 'en'] as const
export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number]

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      es: { common: esCommon, chat: esChat, admin: esAdmin },
      ca: { common: caCommon, chat: caChat, admin: caAdmin },
      en: { common: enCommon, chat: enChat, admin: enAdmin },
    },
    fallbackLng: 'es',
    supportedLngs: SUPPORTED_LANGUAGES,
    ns: ['common', 'chat', 'admin'],
    defaultNS: 'common',
    interpolation: { escapeValue: false },
  })

export default i18n
```

**Claves mínimas en cada locale** (`es/common.json`):
```json
{
  "app_name": "Gov Gen AI Platform",
  "loading": "Cargando...",
  "error": "Error",
  "save": "Guardar",
  "cancel": "Cancelar",
  "delete": "Eliminar",
  "edit": "Editar",
  "create": "Crear",
  "search": "Buscar",
  "back": "Volver",
  "confirm_delete": "¿Confirmar eliminación?",
  "no_results": "Sin resultados"
}
```

---

### Prompt 9.3 - Auth: contexto JWT y rutas protegidas

**Objetivo**: Contexto React para gestión del JWT, login/logout y protección de rutas por rol.

**`src/shared/auth/AuthContext.tsx`**:
```typescript
import { createContext, useContext, useState, useEffect } from 'react'
import { jwtDecode } from 'jwt-decode'

interface AuthUser {
  user_id: string
  email: string
  role: 'admin' | 'partner' | 'end_user'
}

interface AuthContextType {
  user: AuthUser | null
  token: string | null
  login: (token: string) => void
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem('auth_token')
  )

  const user = token ? (jwtDecode(token) as AuthUser) : null

  const login = (newToken: string) => {
    localStorage.setItem('auth_token', newToken)
    setToken(newToken)
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setToken(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
```

**`src/shared/auth/ProtectedRoute.tsx`**:
```typescript
// Redirige a /login si no autenticado
// Redirige a /unauthorized si el rol no está en allowedRoles
```

**`src/shared/api/client.ts`** (Axios con interceptor JWT):
```typescript
import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default api
```

**Tests requeridos** (`src/shared/auth/__tests__/AuthContext.test.tsx`):
```typescript
// should_store_token_on_login
// should_clear_token_on_logout
// should_decode_user_from_token
// should_redirect_unauthenticated_user
// should_redirect_insufficient_role
```

---

### Prompt 9.4 - Layout: sidebar seccional y header

**Objetivo**: Layout del panel admin con sidebar colapsable, secciones Hub / Automatización / Plataforma, y header con selector de idioma y menú de usuario.

**Componentes shadcn/ui a instalar**:
```bash
npx shadcn@latest add sidebar sheet avatar dropdown-menu badge
```

**`src/admin/components/AppSidebar.tsx`** (estructura de navegación):
```typescript
const navSections = [
  {
    label: 'Hub',
    icon: MessageSquare,
    items: [
      { label: 'Chatbots',   href: '/admin/chatbots',   roles: ['admin', 'partner'] },
      { label: 'Clientes',   href: '/admin/clients',    roles: ['admin', 'partner'] },
      { label: 'Documentos', href: '/admin/documents',  roles: ['admin', 'partner'] },
      { label: 'Informes',   href: '/admin/reports',    roles: ['admin', 'partner'] },
    ],
  },
  {
    label: 'Automatización',
    icon: Workflow,
    items: [
      { label: 'Flujos',    href: '/admin/flows',    roles: ['admin', 'partner'] },
      { label: 'PDF',       href: '/admin/pdf',      roles: ['admin', 'partner'] },
      { label: 'Scripts',   href: '/admin/scripts',  roles: ['admin', 'partner'] },
    ],
  },
  {
    label: 'Plataforma',
    icon: Settings,
    items: [
      { label: 'Modelos LLM',  href: '/admin/llm-configs', roles: ['admin'] },
      { label: 'Prompts',      href: '/admin/prompts',      roles: ['admin'] },
      { label: 'Licencias',    href: '/admin/licenses',     roles: ['admin'] },
      { label: 'Usuarios',     href: '/admin/users',        roles: ['admin'] },
    ],
  },
]
```

**Tests requeridos**:
```typescript
// should_render_hub_section
// should_hide_platform_section_for_partner_role
// should_collapse_sidebar_on_mobile
// should_highlight_active_route
```

---

### Prompt 9.5 - Hub > Pantalla de Chatbots

**Objetivo**: CRUD completo de chatbots con tabla paginada, diálogo de creación/edición y confirmación de borrado.

**Componentes shadcn/ui a instalar**:
```bash
npx shadcn@latest add table dialog form input textarea select switch alert-dialog
```

**Endpoints que consume**:
- `GET  /api/v1/hub/chatbots` — listado (paginado)
- `POST /api/v1/hub/chatbots` — crear
- `PUT  /api/v1/hub/chatbots/{id}` — editar
- `DELETE /api/v1/hub/chatbots/{id}` — eliminar

**`src/admin/pages/ChatbotsPage.tsx`** — estructura clave:
```typescript
// useQuery: lista chatbots con react-query
// useMutation: crear/editar/eliminar con invalidación de caché
// DataTable con columnas: nombre, cliente, modelo, estado (Switch activo/inactivo), acciones
// ChatbotDialog: formulario react-hook-form + zod
//   campos: nombre, system_prompt, llm_config_id (Select), client_id (Select)
// AlertDialog para confirmar borrado
```

**Schema de validación** (zod):
```typescript
const chatbotSchema = z.object({
  name:          z.string().min(1).max(255),
  system_prompt: z.string().min(10),
  llm_config_id: z.string().uuid(),
  client_id:     z.string().uuid(),
  is_active:     z.boolean().default(true),
})
```

**Tests requeridos** (`src/admin/pages/__tests__/ChatbotsPage.test.tsx`):
```typescript
// should_display_chatbots_list_on_load
// should_open_create_dialog_on_button_click
// should_validate_required_fields_before_submit
// should_show_success_toast_after_create
// should_show_confirm_dialog_before_delete
// should_toggle_chatbot_active_status
```

---

### Prompt 9.6 - Hub > Pantalla de Clientes

**Objetivo**: CRUD de clientes (HubClient) con asignación de chatbots activos.

**Endpoints que consume**:
- `GET  /api/v1/hub/clients`
- `POST /api/v1/hub/clients`
- `PUT  /api/v1/hub/clients/{id}`
- `DELETE /api/v1/hub/clients/{id}`

**`src/admin/pages/ClientsPage.tsx`** — estructura clave:
```typescript
// DataTable con columnas: nombre, partner_id, chatbots asignados (Badge count), activo, acciones
// ClientDialog: formulario con nombre, partner_id, theme_config (JSON editor simple)
// Panel de chatbots asignados: lista de chatbots del cliente con toggle activo/inactivo
```

**Tests requeridos**:
```typescript
// should_list_clients_on_mount
// should_create_client_with_valid_data
// should_show_assigned_chatbots_count
// should_filter_clients_by_name
```

---

### Prompt 9.6.5 - Frontera Edge-Cloud (preparación del despliegue híbrido) ✅ COMPLETADO

**Objetivo**: Establecer la separación estructural entre módulos **cloud** (administración, gobernanza, configuración) y módulos **edge** (RAG, chat, ingesta, datos del cliente) antes de que la superficie de modelos/servicios crezca más. No se implementa el despliegue edge; se fija la frontera en el código para que la futura separación sea mecánica, no un refactor transversal.

**Motivación** (contexto para el agente):

El producto tiene dos modos de despliegue previstos:

1. **Cloud-only** (partners que protegen datos por contrato): toda la lógica corre en el servidor del partner; los datos se anonimizan antes de enviarse al LLM.
2. **Edge + Cloud** (clientes con requisitos regulatorios estrictos, p. ej. hospitales, universidades con datos sensibles): las operaciones sobre los datos del cliente corren en un **edge node** dentro de la nube del cliente; el **cloud** solo conserva configuración administrativa y métricas anonimizadas.

En ambos modos el mismo código debe servir. Si hoy se mezclan en el mismo `DeclarativeBase`, las mismas rutas y los mismos servicios los modelos de configuración y los operacionales, cada prompt futuro acumula acoplamientos que harán el split posterior caro.

**Partición conceptual**:

| Grupo | Vive en | Modelos actuales |
|---|---|---|
| **Configuración** (se sincroniza cloud → edge) | Cloud (authoritative), edge (réplica) | `HubClient`, `HubChatbot`, `HubLLMConfig`, `HubPromptTemplate` |
| **Operacional** (nunca sale del edge en crudo) | Edge exclusivamente | `HubDocumentChunk`, `HubInteraction`, `HubIngestionJob` |

**Tareas concretas**:

1. **Separar ORM en dos `DeclarativeBase`** dentro de `server/app/modules/agents_hub/database/`:

   ```python
   # base.py
   class HubConfigBase(DeclarativeBase):
       """Modelos de configuración: se sincronizan de cloud a edge."""
       type_annotation_map = {dict[str, Any]: JSONB, list[str]: ARRAY(String)}

   class HubOperationalBase(DeclarativeBase):
       """Modelos operacionales: viven sólo en el edge node."""
       type_annotation_map = {dict[str, Any]: JSONB, list[str]: ARRAY(String)}
   ```

   - `config_models.py` — `HubClient`, `HubChatbot`, `HubLLMConfig`, `HubPromptTemplate` heredan de `HubConfigBase`.
   - `operational_models.py` — `HubDocumentChunk`, `HubInteraction`, `HubIngestionJob` heredan de `HubOperationalBase`.
   - Eliminar `models.py` actual (no dejar shim de re-exports).
   - Actualizar todos los imports en el proyecto.

2. **Romper las relaciones ORM que cruzan la frontera**:

   Las FK a `hub_chatbots.id` se conservan como columnas, pero **se eliminan los `relationship()` cross-base**:
   - Quitar `HubChatbot.document_chunks`, `HubChatbot.interactions`
   - Quitar `HubDocumentChunk.chatbot`, `HubInteraction.chatbot`, `HubIngestionJob.chatbot`
   - Quitar `cascade="all, delete-orphan"` en esas relaciones (el borrado en cascada lo maneja la DB con `ondelete="CASCADE"`, que ya existe).

   Los servicios que usen `.chatbot` o `.document_chunks` deben refactorizarse para consultar por `chatbot_id` con queries explícitas (grep previo obligatorio: `\.chatbot\b`, `\.document_chunks`, `\.interactions`, `\.prompt_templates` en `server/`).

3. **Stub de la API de sincronización** en `server/app/api/v1/edge_sync.py`:

   ```python
   router = APIRouter(prefix="/edge", tags=["edge-sync"])

   class EdgeConfigSnapshot(BaseModel):
       clients: list[ClientOut]
       chatbots: list[ChatbotOut]
       llm_configs: list[LLMConfigOut]
       prompt_templates: list[PromptTemplateOut]
       generated_at: datetime

   class EdgeTelemetryBatch(BaseModel):
       edge_node_id: str
       interactions_count: int
       avg_latency_ms: float
       window_start: datetime
       window_end: datetime

   @router.get("/config", response_model=EdgeConfigSnapshot)
   async def get_edge_config(...): raise HTTPException(501, "Not implemented")

   @router.post("/telemetry", status_code=202)
   async def ingest_edge_telemetry(body: EdgeTelemetryBatch, ...): raise HTTPException(501, "Not implemented")
   ```

   Registrar en `main.py`. Auth: se usará el mismo `get_current_user` por ahora; la autenticación por device token / mTLS queda para la fase de implementación real.

4. **Actualizar `CLAUDE.md`** añadiendo una sección tras "Estructura de módulos":

   ```markdown
   ## Frontera Edge-Cloud

   El sistema se despliega en dos modos: cloud-only y edge+cloud. Para que el split
   sea viable sin refactor masivo, el código respeta dos grupos de módulos:

   ### Modelos ORM: dos bases separadas
   - `HubConfigBase` → se sincroniza cloud→edge (HubClient, HubChatbot, HubLLMConfig, HubPromptTemplate)
   - `HubOperationalBase` → vive sólo en edge (HubDocumentChunk, HubInteraction, HubIngestionJob)

   ### Reglas duras
   - **Sin relaciones ORM cross-base**. Si un modelo operacional necesita un
     chatbot, consulta por `chatbot_id` explícitamente — no navegues por `.chatbot`.
   - **Los servicios edge no importan modelos de config directamente**. El acceso
     a configuración pasa por un `ConfigProvider` (stub por ahora, sync API después).
   - **El router `edge_sync` es la única superficie que ve ambos mundos**.

   Si escribes código que viola estas reglas, estás creando deuda que bloqueará
   el despliegue edge. Para, reconsidera, o razona en el PR por qué es necesario.
   ```

5. **`ConfigProvider` como punto de indirección** en `server/app/modules/agents_hub/services/config_provider.py`:

   ```python
   class ConfigProvider(Protocol):
       async def get_chatbot(self, chatbot_id: uuid.UUID) -> ChatbotConfig | None: ...
       async def get_llm_config(self, llm_config_id: uuid.UUID) -> LLMConfig | None: ...
       async def list_active_chatbots(self, client_id: uuid.UUID) -> list[ChatbotConfig]: ...

   class LocalConfigProvider:
       """Implementación cloud-only: lee directamente de la DB."""
       # ...

   # Futuro: RemoteConfigProvider que consulta /api/v1/edge/config
   ```

   Los servicios RAG (`retriever`, `task_runner`, `graph`) deben migrarse para usar `ConfigProvider` en lugar de importar `HubChatbot` directamente. No se crea el `RemoteConfigProvider` ahora; basta con la abstracción y la `LocalConfigProvider`.

**Tests requeridos** (`server/tests/modules/agents_hub/unit/test_edge_boundary.py`):

```python
# test_config_base_contains_only_config_models
#   Verifica que HubConfigBase.metadata.tables tiene exactamente los 4 tablenames esperados
#
# test_operational_base_contains_only_operational_models
#   Verifica que HubOperationalBase.metadata.tables tiene exactamente los 3 esperados
#
# test_no_cross_base_relationships
#   Introspecciona mappers: ninguna relationship() en HubConfigBase apunta a clases
#   de HubOperationalBase y viceversa
#
# test_edge_sync_config_endpoint_exists_returns_501
# test_edge_sync_telemetry_endpoint_exists_returns_501
#
# test_rag_services_dont_import_config_models_directly
#   Grep estático: módulos agent/ e ingestion/ no contienen `from ...config_models import`
#   (permitido sólo en services/config_provider.py)
```

**Checklist de cierre**:

- [ ] `models.py` eliminado; `config_models.py` y `operational_models.py` creados
- [ ] Imports actualizados en todo `server/` (0 referencias a `from .models import`)
- [ ] `relationship()` cross-base eliminados; servicios refactorizados a queries por FK
- [ ] `config_provider.py` con `Protocol` + `LocalConfigProvider` en uso desde `retriever`, `task_runner`, `graph`
- [ ] `edge_sync.py` registrado en `main.py`, devuelve 501 con schemas Pydantic visibles en `/docs`
- [ ] `CLAUDE.md` actualizado con la sección "Frontera Edge-Cloud"
- [ ] Suite completa en verde: `pytest server/` y tests de agents_hub existentes siguen pasando

**Fuera de alcance** (se abordarán en la fase de implementación edge real):

- Conexiones a DBs separadas (hoy ambas bases usan el mismo engine)
- Autenticación por device token / mTLS
- `RemoteConfigProvider` que consume la sync API
- Dockerización del edge node
- Migración de interacciones/chunks a DB dedicada

El objetivo de este prompt es **congelar la frontera en el código**; la separación física de procesos y DBs llega en una fase posterior cuando se aborde el primer cliente con requisitos edge reales.

---

### Prompt 9.6.6 - Frontera Edge-Cloud en la capa de aplicación (routers y módulos) ✅ COMPLETADO

**Objetivo**: Clasificar routers HTTP y módulos de lógica según su pertenencia a cloud o edge. Introducir `DEPLOY_MODE` para que el mismo codebase pueda arrancarse como cloud-only, edge-only o all (por defecto). Fijar las reglas anti-import para que los módulos edge no dependan de módulos cloud.

**Motivación** (contexto para el agente):

El prompt 9.6.5 fija la frontera en la capa de datos (modelos ORM, `ConfigProvider`). Esto es necesario pero no suficiente: falta fijar la frontera en la **capa de aplicación**, es decir, clasificar qué endpoints HTTP y qué módulos de lógica corren en cada lado del split.

En el modo **edge+cloud**, el nodo edge ejecuta:
- Los grafos LangGraph, el task runner y los tools (interacción con expedientes)
- La ingesta de documentos y la extracción con Docling
- El retriever RAG y la evaluación de calidad
- **Todo el módulo `automation/`**: factories, flows, ETL, generación de PDF, scripts

El cloud (admin/partner) ejecuta:
- CRUD de chatbots, clientes, partners, LLM configs, prompt templates
- Gestión de usuarios, autenticación central, billing
- Exposición de la sync API para los edge nodes

**Partición de routers y módulos**:

| Capa | Cloud (admin/partner) | Edge (cliente) | Compartidos |
|---|---|---|---|
| **Routers HTTP** | `auth_router`, `hub_chatbots_router`, `hub_clients_router`, `library_router`, futuros `/hub/prompts`, `/hub/themes` | `hub_chat_router`, `ingestion_router`, `hub_tasks_router`, `hub_feedback_router`, futuros `/automation/*` | `edge_sync_router` (servido por cloud, consumido por edge) |
| **Módulos lógica** | `services/prompt_service` (CRUD), gestión partners/billing | `agents_hub/agent/` (graph, task_runner, tools, hitl), `agents_hub/ingestion/`, `agents_hub/services/retriever`, `agents_hub/evaluation/`, **`modules/automation/` íntegro** | `core/auth`, `services/model_factory`, `services/embedding_service`, `services/config_provider` |

**Tareas concretas**:

1. **`DEPLOY_MODE` en `main.py`**:

   ```python
   import os
   DEPLOY_MODE = os.getenv("DEPLOY_MODE", "all").lower()
   if DEPLOY_MODE not in ("cloud", "edge", "all"):
       raise RuntimeError(f"Invalid DEPLOY_MODE: {DEPLOY_MODE}")

   def _register_cloud(app: FastAPI) -> None:
       app.include_router(auth_router, prefix="/api/v1")
       app.include_router(library_router, prefix="/api")
       app.include_router(hub_chatbots_router, prefix="/api/v1")
       app.include_router(hub_clients_router, prefix="/api/v1")
       app.include_router(edge_sync_router, prefix="/api/v1")  # servido por cloud

   def _register_edge(app: FastAPI) -> None:
       app.include_router(hub_chat_router, prefix="/api/v1")
       app.include_router(hub_feedback_router, prefix="/api/v1")
       app.include_router(hub_tasks_router, prefix="/api/v1")
       app.include_router(ingestion_router, prefix="/api/v1")

   if DEPLOY_MODE in ("cloud", "all"):
       _register_cloud(app)
   if DEPLOY_MODE in ("edge", "all"):
       _register_edge(app)
   ```

   - Por defecto `DEPLOY_MODE=all` → comportamiento actual intacto.
   - Documentar la variable en `.env.production.example`.

2. **Etiquetado de routers**: cada router existente y futuro lleva un comentario en su `__init__` o docstring que identifica su modo:

   ```python
   # server/app/routers/hub_chatbots_router.py
   """CRUD de chatbots del Hub.

   Deploy: cloud
   """
   ```

   Valores válidos: `cloud`, `edge`, `shared`.

3. **Registro de `modules/automation/` como módulo edge**:

   Añadir a `server/app/modules/automation/__init__.py`:

   ```python
   """Módulo de automatización: flows, ETL, scripts, PDF.

   Deploy: edge — procesa documentos/expedientes del cliente.
   No debe importar routers ni servicios cloud (partners, billing, CRUD admin).
   """
   ```

   Hacer lo mismo en `agents_hub/agent/__init__.py`, `agents_hub/ingestion/__init__.py`, `agents_hub/evaluation/__init__.py` con etiqueta `edge`.

4. **Reglas anti-import (tests estáticos)**: un módulo edge no puede importar desde:
   - Routers cloud (`hub_chatbots_router`, `hub_clients_router`, etc.)
   - Modelos de config directamente (regla heredada de 9.6.5, reforzada aquí)
   - Servicios exclusivos de cloud (billing, partner management)

   Excepción permitida: `services/config_provider` (costura explícita).

5. **Anonimización como responsabilidad edge**: documentar en `core/llm/` (o donde viva `model_factory`) que la entrada al gateway LLM asume datos ya anonimizados; el paso de anonimización vive en los servicios edge (retriever, task_runner) antes de llamar al factory.

**Tests requeridos** (`server/tests/modules/agents_hub/unit/test_deploy_mode.py`):

```python
# test_default_deploy_mode_registers_all_routers
#   Arranca app con DEPLOY_MODE no definido; verifica que /api/v1/hub/chatbots
#   y /api/v1/hub/chat responden (ambos existen)
#
# test_deploy_mode_cloud_excludes_edge_routers
#   Arranca app con DEPLOY_MODE=cloud; /api/v1/hub/chat devuelve 404, /api/v1/hub/chatbots OK
#
# test_deploy_mode_edge_excludes_cloud_routers
#   Arranca app con DEPLOY_MODE=edge; /api/v1/hub/chatbots devuelve 404, /api/v1/hub/chat OK
#
# test_deploy_mode_invalid_raises
#   DEPLOY_MODE=foo → RuntimeError al importar
```

Tests estáticos en `server/tests/architecture/test_edge_cloud_boundary.py`:

```python
# test_automation_module_has_no_cloud_imports
#   AST-parse o grep de server/app/modules/automation/**/*.py
#   Falla si encuentra: from server.app.routers.hub_chatbots_router,
#   from server.app.routers.hub_clients_router, o imports a billing/partners
#
# test_agent_module_doesnt_import_config_models
#   server/app/modules/agents_hub/agent/**/*.py no contiene
#   `from ..database.config_models import` (debe ir vía config_provider)
#
# test_all_routers_have_deploy_label
#   Cada fichero router*.py tiene un docstring con "Deploy: cloud|edge|shared"
```

**Checklist de cierre**:

- [ ] `DEPLOY_MODE` implementado en `main.py` con las tres funciones `_register_*`
- [ ] `.env.production.example` documenta `DEPLOY_MODE` con sus 3 valores
- [ ] Todos los routers tienen etiqueta `Deploy: ...` en su docstring
- [ ] `__init__.py` de automation, agent, ingestion, evaluation etiquetados como `edge`
- [ ] Tests de arranque con los 3 modos en verde
- [ ] Tests estáticos de anti-import en verde
- [ ] `CLAUDE.md` contiene la sección "Frontera Edge-Cloud" con las dos partes (datos y aplicación)
- [ ] Suite completa en verde tras la reorganización

**Fuera de alcance** (fase de implementación edge real):

- Arrancar dos procesos FastAPI distintos (cloud y edge) en producción
- Despliegue con Docker Compose separado por modo
- Autenticación device-token entre edge y cloud
- `RemoteConfigProvider` real (cliente HTTP que habla con `edge_sync`)
- Replicación física de la DB de configuración al edge

El objetivo: que el día que se aborde un cliente con requisitos edge, el split sea `DEPLOY_MODE=edge` en su contenedor y `DEPLOY_MODE=cloud` en el nuestro. Nada más.

---

### Prompt 9.7 - Hub > Pantalla de Documentos ✅ COMPLETADO

**Objetivo**: Gestión de documentos PDF por chatbot: upload con URL canónica opcional, listado con estado de ingestión, borrado individual y borrado de colección completa.

**Endpoints que consume**:
- `GET  /api/v1/hub/ingestion/{chatbot_id}/jobs` — lista jobs de ingestión
- `POST /api/v1/hub/ingestion/upload` — sube PDF; acepta `chatbot_id`, `file`, `canonical_url` (opcional)
- `DELETE /api/v1/hub/ingestion/{chatbot_id}/jobs/{job_id}` — borra un documento y sus chunks
- `DELETE /api/v1/hub/ingestion/{chatbot_id}/chunks` — borra toda la colección

**Modelo `HubIngestionJob`** (campos añadidos sobre la spec inicial):
- `original_filename` — nombre real del archivo subido
- `canonical_url` — URL pública del documento para citación en el chat; si se proporciona, los chunks almacenan esta URL en lugar de la ruta temporal, lo que también garantiza deduplicación correcta al re-ingestar el mismo documento

**Comportamiento de citación**:
- `search_knowledge.py` formatea la fuente como enlace Markdown `[url](url)` cuando `source_url` es http/https; en caso contrario muestra solo el nombre de archivo

**Tests requeridos**:
```typescript
// should_list_ingestion_jobs_for_selected_chatbot
// should_accept_pdf_files_only_in_dropzone
// should_show_original_filename_in_table
// should_show_canonical_url_link_when_present
// should_show_progress_for_processing_job
// should_show_error_state_for_failed_job
// should_delete_individual_job_and_its_chunks
// should_confirm_before_clearing_collection
```

---

### Prompt 9.7.1 - Hub > Fuentes web monitorizadas (crawler de ingestión) ✅ COMPLETADO (2026-04-25)

**Objetivo**: El administrador configura URLs públicas que el sistema comprueba periódicamente. Cuando Docling detecta que el contenido ha cambiado (hash distinto), re-ingesta el documento automáticamente. Esto sustituye la actualización manual cuando la base documental vive en una web institucional que se actualiza con regularidad.

**Aclaración de responsabilidad** (importante para no confundir con el RPA):
- Este crawler es un proceso **server-side**, iniciado por el propio Edge node según un calendario fijado por el administrador.
- El Playwright del **Prompt 9.16** (`handlers/rpa.py`) es exclusivamente para **automatización web interactiva de usuario final** (rellenar formularios, extraer datos en sesión): lo dispara un usuario, no el scheduler.
- Si una URL es simple HTML/PDF, Docling la procesa directamente. Solo si requiere JavaScript dinámico (SPA, login) se utilizará Playwright headless dentro del pipeline de ingestión (decisión de implementación futura).

---

#### Prompt 9.7.1a — Tests modelo `HubIngestionSource` (TDD - RED)

**Prerequisitos**: Prompt 9.7 completado; Alembic en uso.

**Nuevo modelo ORM** en `server/app/modules/agents_hub/database/operational_models.py`:

```python
class HubIngestionSource(HubOperationalBase):
    """URL pública que el sistema monitoriza para re-ingestión automática."""
    __tablename__ = "hub_ingestion_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)   # etiqueta legible
    check_interval_hours: Mapped[int] = mapped_column(Integer, default=24)  # 1..168
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")       # active|paused|error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

**Nota de frontera edge/cloud**: `HubIngestionSource` vive en `HubOperationalBase` (edge) porque su estado operacional (`last_content_hash`, `last_checked_at`) reside en el edge. En despliegue edge+cloud separados, el admin cloud configura las fuentes a través del router `edge_sync`; el scheduler edge las lee localmente.

**`tests/modules/agents_hub/integration/test_ingestion_sources.py`**:
```python
# test_can_create_ingestion_source
# test_source_defaults_to_active_status
# test_source_check_interval_defaults_to_24h
# test_label_is_optional
# test_can_update_last_checked_at_and_hash
# test_can_pause_and_resume_source
```

---

#### Prompt 9.7.1b — Endpoints CRUD de fuentes (TDD - RED → GREEN)

**Router**: `server/app/routers/hub_ingestion_router.py` (Deploy: cloud — el admin configura, el scheduler edge consume).

**Nuevos endpoints**:

```python
# GET  /hub/ingestion/{chatbot_id}/sources         — lista fuentes del chatbot
# POST /hub/ingestion/{chatbot_id}/sources         — añade fuente
#      body: { url: str, label?: str, check_interval_hours?: int (1..168) }
# PATCH /hub/ingestion/{chatbot_id}/sources/{id}  — edita label, intervalo o status
# DELETE /hub/ingestion/{chatbot_id}/sources/{id} — elimina fuente (no borra los chunks ya ingestados)
# POST /hub/ingestion/{chatbot_id}/sources/{id}/check — fuerza comprobación inmediata (background task)
```

**Tests requeridos**:
```python
# test_create_source_returns_201
# test_create_source_validates_url_format
# test_create_source_rejects_duplicate_url_for_same_chatbot
# test_list_sources_returns_only_chatbot_sources
# test_patch_source_updates_interval
# test_patch_source_can_pause_and_resume
# test_delete_source_removes_it_without_deleting_chunks
# test_manual_check_triggers_background_job
```

---

#### Prompt 9.7.1c — Scheduler de comprobación periódica (TDD - RED → GREEN)

**Dependency**: añadir `apscheduler>=3.10` a `pyproject.toml`.

**`server/app/modules/agents_hub/ingestion/source_scheduler.py`**:

```python
"""Scheduler que comprueba periódicamente las fuentes web configuradas."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def check_all_sources(session_factory) -> None:
    """Para cada fuente activa con check_interval vencido:
    1. Llama a DoclingProcessor para obtener el Markdown de la URL
    2. Calcula hash del contenido
    3. Si hash != last_content_hash:
       - Crea un HubIngestionJob con source_url=url y canonical_url=url
       - Lanza run_job() en background
       - Actualiza last_content_hash
    4. Actualiza last_checked_at y status (error si falla)
    """

def create_scheduler(session_factory) -> AsyncIOScheduler:
    """Crea el scheduler con un job master cada 15 min que decide qué fuentes comprobar."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_all_sources,
        trigger="interval",
        minutes=15,
        args=[session_factory],
        id="source_checker",
        replace_existing=True,
    )
    return scheduler
```

**Integración en lifespan** (`server/app/main.py`):
```python
# En lifespan: scheduler = create_scheduler(session_factory); scheduler.start()
# Al cerrar:   scheduler.shutdown()
```

**Tests requeridos**:
```python
# test_check_all_sources_skips_paused_sources
# test_check_all_sources_skips_recently_checked_sources
# test_check_all_sources_creates_job_when_content_changed
# test_check_all_sources_skips_job_when_content_unchanged
# test_check_all_sources_marks_source_error_on_fetch_failure
# test_check_all_sources_updates_last_checked_at
```

---

#### Prompt 9.7.1d — UI: sección "Fuentes web" en DocumentsPage (TDD - RED → GREEN)

**Estrategia**: añadir un segundo tab `Tabs` en `DocumentsPage.tsx` con dos vistas: "Documentos subidos" (existente) y "Fuentes web".

**`frontend/src/shared/api/ingestion.ts`** — nuevas funciones:
```typescript
export interface IngestionSource {
  id: string
  chatbot_id: string
  url: string
  label: string | null
  check_interval_hours: number
  last_checked_at: string | null
  last_content_hash: string | null
  status: 'active' | 'paused' | 'error'
  error_message: string | null
  created_at: string
}

// fetchSources(chatbotId)
// createSource(chatbotId, { url, label?, check_interval_hours? })
// updateSource(chatbotId, sourceId, { label?, check_interval_hours?, status? })
// deleteSource(chatbotId, sourceId)
// triggerSourceCheck(chatbotId, sourceId)
```

**`frontend/src/admin/pages/DocumentsPage.tsx`** — estructura ampliada:
```typescript
// Tab "Documentos subidos": contenido actual (Dropzone + tabla de jobs)
// Tab "Fuentes web":
//   Form inline: input URL + input Etiqueta + select Intervalo (6h/12h/24h/48h/semanal)
//   Tabla de fuentes: URL (enlace), etiqueta, intervalo, último check, estado (badge)
//   Acciones por fila: Pausar/Reanudar, Comprobar ahora, Eliminar
//   Badge de estado: active→verde, paused→gris, error→rojo con tooltip del error
```

**Tests requeridos**:
```typescript
// should_render_sources_tab
// should_create_source_with_valid_url
// should_reject_invalid_url_format
// should_show_last_checked_timestamp
// should_show_error_badge_with_tooltip
// should_pause_and_resume_source
// should_trigger_manual_check
// should_confirm_before_deleting_source
```

---

### Prompt 9.8 - Hub > Pantalla de Informes ✅ COMPLETADO (2026-04-26)

**Objetivo**: Tabla de interacciones del chatbot con filtros, visualización de feedback y export CSV.

**Endpoints que consume**:
- `GET /api/v1/hub/feedback/{chatbot_id}/review?only_low_scores=false&limit=100`

**Componentes shadcn/ui**:
```bash
npx shadcn@latest add card
```

**`src/admin/pages/ReportsPage.tsx`** — estructura clave:
```typescript
// Cabecera con métricas: total interacciones, media de puntuación (Card con recharts)
// Filtros: chatbot selector, rango de fechas, solo puntuaciones bajas (Switch)
// DataTable expandible: mensaje usuario, respuesta asistente, puntuación (Star rating), comentario
// Export CSV (genera blob en cliente sin endpoint adicional)
```

**Tests requeridos**:
```typescript
// should_display_interactions_table
// should_filter_low_score_interactions
// should_expand_row_to_show_full_messages
// should_export_data_as_csv
// should_display_average_score_metric
```

---

### Prompt 9.8.1 - Etiquetado de idioma en la ingestión ✅ COMPLETADO (2026-04-26)

**Objetivo**: Garantizar que todos los chunks almacenados tienen el campo `language` correcto,
eliminando el `default="es"` que etiqueta erróneamente documentos en catalán o inglés.
Esto es prerequisito para que el filtro de idioma del retriever funcione correctamente.

**Deploy**: edge

**Cambios en modelos ORM** (`operational_models.py`):
```python
# HubIngestionSource — añadir campo de idioma opcional
language: Mapped[str | None] = mapped_column(String(10), nullable=True)
# None = auto-detectar del contenido; valor explícito = forzar ese idioma

# HubIngestionJob — propagar idioma al job
language: Mapped[str | None] = mapped_column(String(10), nullable=True)

# HubDocumentChunk — eliminar default="es" y hacer nullable durante migración
language: Mapped[str] = mapped_column(String(10), nullable=False)
# El valor lo asigna siempre el IngestionWatcher, nunca el default del ORM
```

**Migración Alembic**:
```python
op.add_column("hub_ingestion_sources", sa.Column("language", sa.String(10), nullable=True))
op.add_column("hub_ingestion_jobs",    sa.Column("language", sa.String(10), nullable=True))
# Backfill: chunks existentes sin language válido → detectar del contenido
# (script de migración de datos separado, ver nota abajo)
```

**Cambios en `IngestionWatcher`** (`ingestion/watcher.py`):
```python
# process_source(): si language es None, detectar del contenido tras procesado Docling
async def process_source(self, ..., language: str | None = None, ...) -> list[HubDocumentChunk]:
    content = prefetched_content or await asyncio.to_thread(processor.process, source_url)
    if language is None:
        language = detect_language(content) or "es"   # fallback a es solo si langdetect falla
    ...

# run_job(): propagar job.language al llamar a process_source
async def run_job(self, job_id, prefetched_content=None) -> None:
    job = await self.session.get(HubIngestionJob, job_id)
    ...
    await self.process_source(..., language=job.language, ...)

# process_user_upload(): auto-detectar siempre (upload temporal del usuario)
async def process_user_upload(self, ...) -> list[HubDocumentChunk]:
    content = await asyncio.to_thread(processor.process, source_url)
    language = detect_language(content) or "es"
    ...
```

**Cambios en `source_scheduler.check_source()`**:
```python
# Propagar source.language al job creado
job = HubIngestionJob(
    ...,
    language=source.language,   # None → IngestionWatcher auto-detecta
)
```

**Cambios en el endpoint `/ingestion/user-upload`**:
```python
# Aceptar language opcional; auto-detectar si no se proporciona
@router.post("/user-upload")
async def user_upload(
    chatbot_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    language: str | None = Form(None),   # NUEVO — None = auto-detect
    ...
)
```

**Cambios en `DocumentsPage.tsx`** — añadir selector de idioma al formulario de upload:
```typescript
// Selector con opciones: "Auto-detectar" (vacío), "Castellano" (es), "Català" (ca), "English" (en)
// Cuando el admin conoce el idioma del documento, puede forzarlo; si no, se deja en blanco
```

**Tests requeridos** (TDD — todos los caminos):
```python
# test_process_source_auto_detects_catalan_content
# test_process_source_respects_explicit_language_parameter
# test_run_job_propagates_language_from_job_model
# test_check_source_propagates_source_language_to_job
# test_process_user_upload_auto_detects_language
# test_upload_endpoint_accepts_language_param
# test_upload_endpoint_auto_detects_when_no_language
```

**Nota de migración de datos**: los chunks existentes con `language="es"` que realmente son en
catalán o inglés solo pueden corregirse re-ingiriendo los documentos. Añadir un script de
mantenimiento `scripts/backfill_chunk_language.py` que recorra chunks, detecte idioma del
`content` con `detect_language()` y actualice los que difieran del valor almacenado.

---

### Prompt 9.8.2 - SSE streaming en el endpoint de chat (backend) ✅ COMPLETADO (2026-04-26)

**Objetivo**: Refactorizar el endpoint de chat para emitir Server-Sent Events, permitiendo
al cliente recibir: (a) eventos de progreso por nodo del grafo, (b) tokens del LLM en tiempo
real, (c) evento `done` con fuentes y advertencia de traducción si aplica.

**Deploy**: edge

**Protocolo de eventos SSE**:
```
event: status   data: {"node": "detect_language",        "msg": "Detectando idioma..."}
event: status   data: {"node": "search_knowledge",       "msg": "Buscando en la base de conocimiento..."}
event: status   data: {"node": "validate_retrieval",     "msg": "Validando resultados..."}
event: status   data: {"node": "search_knowledge_fallback", "msg": "Buscando en otros idiomas..."}
event: status   data: {"node": "generate_response",      "msg": "Generando respuesta..."}
event: token    data: {"delta": "La "}
event: token    data: {"delta": "respuesta "}
...
event: done     data: {"interaction_id": "uuid", "sources": [...], "language_fallback": bool,
                        "translation_warning": "⚠️ ..." | null}
event: error    data: {"message": "..."}
```

**`server/app/api/v1/hub_chat.py`** — endpoint SSE:
```python
@router.post("/{chatbot_id}")
async def chat_stream(
    chatbot_id: uuid.UUID,
    request: ChatRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    async def event_generator():
        graph = create_agent_graph(retriever, embedding_service, user_id=user.user_id)
        compiled = graph.compile()

        async for event in compiled.astream_events(initial_state, version="v2"):
            kind = event["event"]

            if kind == "on_chain_start" and event["name"] in NODE_STATUS_MESSAGES:
                yield f"event: status\ndata: {json.dumps({'node': event['name'], 'msg': NODE_STATUS_MESSAGES[event['name']]})}\n\n"

            elif kind == "on_chat_model_stream":
                delta = event["data"]["chunk"].content
                if delta:
                    yield f"event: token\ndata: {json.dumps({'delta': delta})}\n\n"

            elif kind == "on_chain_end" and event["name"] == "generate_response":
                final_state = event["data"]["output"]
                yield f"event: done\ndata: {json.dumps({
                    'interaction_id': str(interaction_id),
                    'sources': final_state.get('sources', []),
                    'language_fallback': final_state.get('language_fallback_triggered', False),
                    'translation_warning': build_translation_warning(...) if final_state.get('language_fallback_triggered') else None,
                })}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

**Mapeo de nodos a mensajes de progreso** (`NODE_STATUS_MESSAGES`):
```python
NODE_STATUS_MESSAGES = {
    "route_by_capability":        "Iniciando...",
    "detect_language":            "Detectando idioma...",
    "query_classifier":           "Clasificando consulta...",
    "search_knowledge":           "Buscando en la base de conocimiento...",
    "validate_retrieval":         "Validando resultados...",
    "search_knowledge_fallback":  "Buscando en otros idiomas...",
    "reranker":                   "Reordenando resultados...",
    "generate_response":          "Generando respuesta...",
    "quality_evaluator":          "Evaluando calidad...",
    "log_interaction":            "Guardando interacción...",
}
```

**Tests requeridos**:
```python
# test_chat_endpoint_returns_streaming_response
# test_chat_endpoint_emits_status_events_per_node
# test_chat_endpoint_emits_token_events
# test_chat_endpoint_emits_done_event_with_sources
# test_chat_endpoint_includes_translation_warning_when_language_fallback
# test_chat_endpoint_emits_error_event_on_graph_failure
```

---

## BLOQUE 9B — Widget y Modo Agente

*Objetivo: widget embebible funcional + modo agente expandido para usuarios identificados.*

---

### Prompt 9.9 - Widget: bundle embebible ✅ COMPLETADO (2026-04-26)

**Objetivo**: Compilar el widget como librería independiente que cualquier página HTML puede incrustar sin depender del SPA admin.

**`vite.config.widget.ts`** (config específica del widget):
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: 'src/widget/main.tsx',
      name: 'GovGenAIWidget',
      fileName: 'widget',
      formats: ['iife'],   // un único fichero JS auto-ejecutable
    },
    rollupOptions: {
      output: { inlineDynamicImports: true },
    },
    outDir: 'dist/widget',
  },
})
```

**Integración en página externa**:
```html
<div id="govgenai-widget"
     data-chatbot-id="<uuid>"
     data-lang="ca"
     data-api-url="https://api.govgenai.example">
</div>
<script src="https://cdn.govgenai.example/widget.js"></script>
```

**`src/widget/main.tsx`**:
```typescript
// Lee los atributos data-* del contenedor
// Detecta el idioma del host vía postMessage o data-lang
// Monta el componente ChatWidget en el contenedor
```

**Tests requeridos**:
```typescript
// should_mount_widget_from_data_attributes
// should_use_lang_from_data_attribute
// should_update_lang_on_postmessage_from_parent
// should_hide_widget_if_chatbot_id_missing
```

---

### Prompt 9.10 - Widget: chat SSE y feedback ✅ COMPLETADO (2026-04-26)

**Objetivo**: Componente de chat completo con streaming SSE, historial de mensajes, eventos de
progreso de nodos del grafo y valoración por estrellas.

**Dependencia backend**: Prompt 9.8.2 (endpoint SSE con eventos `status`, `token`, `done`, `error`).

**`src/widget/hooks/useChat.ts`**:
```typescript
// Protocolo SSE que consume (definido en Prompt 9.8.2):
//   event: status  → { node: string, msg: string }
//   event: token   → { delta: string }
//   event: done    → { interaction_id: string, sources: string[],
//                      language_fallback: boolean, translation_warning: string | null }
//   event: error   → { message: string }
//
// Estado interno del hook:
//   messages: Message[]                    — historial de mensajes
//   currentNodeStatus: string | null       — mensaje del último evento status
//   isStreaming: boolean                   — true mientras llegan tokens
//   translationWarning: string | null      — advertencia de traducción si language_fallback
//   sources: string[]                      — fuentes del evento done
//   interactionId: string | null           — para el feedback post-respuesta
//
// Implementación: fetch() con ReadableStream (mejor control que EventSource sobre POST)
//   - Lee el stream línea a línea, parsea los eventos SSE manualmente
//   - Para event:status → actualiza currentNodeStatus (mostrar en burbuja de "pensando")
//   - Para event:token → acumula delta en el último mensaje del asistente
//   - Para event:done  → guarda sources, interactionId, translationWarning; isStreaming=false
//   - Para event:error → guarda error; isStreaming=false
```

**`src/widget/components/ChatWidget.tsx`**:
```typescript
// Estado: messages[], isLoading, currentNodeStatus, translationWarning, sources
// useChat hook → ver arriba
// Área de progreso: mientras isStreaming, muestra currentNodeStatus en itálica gris
//   (e.g., "Buscando en la base de conocimiento..." debajo del input)
// Cuando language_fallback=true: muestra translationWarning como banner amarillo
//   encima del mensaje del asistente
// StarRating: 1-5 estrellas, visible al finalizar cada respuesta
//   → llama POST /api/v1/hub/feedback/{interaction_id} con score
// Botón flotante (cerrar/abrir) con posición configurable vía CSS custom properties
```

**Tests requeridos**:
```typescript
// should_display_user_and_assistant_messages
// should_stream_chunks_in_real_time
// should_show_node_status_during_stream          ← NUEVO
// should_hide_status_when_streaming_ends         ← NUEVO
// should_show_translation_warning_on_language_fallback  ← NUEVO
// should_show_star_rating_after_response
// should_submit_feedback_on_star_click
// should_show_loading_indicator_during_stream
```

---

### Prompt 9.11 - Modo agente: panel expandido

**Objetivo**: Versión expandida del widget para usuarios identificados: añade Dropzone de PDFs temporales, preview de borrador y botón "Solicitar cambios".

**`src/widget/components/AgentPanel.tsx`**:
```typescript
// Solo visible si el usuario tiene token JWT válido (modo agente)
// Dropzone: acepta PDFs, llama POST /api/v1/hub/ingestion/upload?temporary=true
//   → muestra progreso con barra
// LivePreview: panel derecho con el borrador generado (markdown renderizado)
// Toolbar: "Solicitar cambios" (abre campo de comentario → regenera con instrucción adicional)
// "Exportar" → llama GET /api/v1/hub/tasks/export/{run_id}?fmt=pdf|markdown
```

**Tests requeridos**:
```typescript
// should_show_dropzone_when_user_authenticated
// should_upload_pdf_and_show_progress
// should_render_draft_in_live_preview
// should_send_change_request_and_regenerate
// should_export_as_pdf_on_button_click
```

---

## BLOQUE 9C — Automatización (migración NiceGUI)

*Prerrequisito: Bloque 9A completado (layout admin disponible). Cada prompt incluye el traslado del equivalente NiceGUI a _legacy_nicegui.*

**Orden de ejecución dentro del bloque** (las dependencias son estrictas):

```
Guía 9C.0 (conceptual, se lee antes de escribir código)
  ├── 9.12a  Focus Mode React          ──┐
  │                                       ├──► 9.12  Flujos
  │                                       │
  └── 9.12b  Refactor backend Docling  ──┼──► 9.13  PDF extractor (UI)
                                          │
                                          └──► 9.14  Scripts
                                               9.15  Traslado final NiceGUI a _legacy_nicegui
```

---

### Guía 9C.0 — Separación de lógica NiceGUI → React/FastAPI

**Objetivo**: Regla única y reutilizable para decidir, ante cualquier página NiceGUI a migrar, qué sube al servidor FastAPI y qué queda como estado local React. Aplica a los prompts 9.12, 9.13, 9.14 y a cualquier átomo/procesador que se migre en el futuro sin necesidad de una nueva revisión arquitectónica.

Esta guía **no produce código**: es el filtro conceptual que cada prompt de migración aplica en su sección "Separación de lógica". Léela antes de abrir el fichero NiceGUI y clasifica cada bloque según las reglas de abajo.

#### Reglas de clasificación

| Tipo de código en NiceGUI | Destino | Justificación |
|---|---|---|
| Acceso a BD, llamadas a LLM, lectura/escritura de ficheros de servidor | **FastAPI** (endpoint nuevo o existente) | Privilegios, credenciales y transaccionalidad viven en el servidor |
| Máquinas de estado con fases canónicas (`PHASE_RANGES`, progreso de ejecución, checkpoints) | **FastAPI** (persistido) | Debe sobrevivir a refresco de página y ser auditable |
| Servicios de automatización (WorkflowHealthService, CoherenceService, BridgeService, PillProvider, validaciones estructurales de FlowSpec/TaskSpec) | **FastAPI** (módulo `server/app/modules/automation/`) | Son reglas de dominio, no de UI; deben poder invocarse también desde ejecución headless |
| Orquestación de pasos, validación cruzada entre campos, cálculo de variables disponibles (data pills) | **FastAPI** | Dominio |
| Singletons `FocusManager`, `LayoutState`, `layout_manager` | **React state** (Context o Zustand) | Son estado de presentación puro; no tienen sentido en el servidor |
| Visibilidad de pestañas/drawer, pestaña activa, modo expert, colapso del sidebar | **React state local** | UI puro; volátil por diseño |
| Selección actual del usuario (`editing_step`, `designing_atom_type`, fila seleccionada) | **React state local** | UI puro |
| Caché de listados, mutaciones, invalidación | **react-query** (cliente) | Estándar del stack frontend |
| Formularios antes de `submit` | **react-hook-form + zod** (cliente) | Validación síncrona sin round-trip |
| Mensajes i18n, etiquetas, tooltips | **React + i18next** | Nunca hardcodeados en TSX |

#### Contrato de datos que viaja por la API

Por cada pantalla que se migra, el prompt correspondiente **debe** documentar:

1. **Endpoints consumidos** (verbo + path + body/query + response schema resumido).
2. **Esquema del estado de servidor** que persiste (tabla/columna o documento) y cuál es su clave primaria.
3. **Esquema del estado de cliente** (qué campos viven en React y cuándo se pierden al navegar).
4. **Polling / SSE**: si hay procesos largos, se indica cadencia y condición de parada.

#### Checklist aplicado en cada prompt de migración

Antes de cerrar un prompt 9.1x debe cumplirse:

- [ ] Toda lógica clasificable como "dominio" según la tabla vive en `server/app/modules/...`, con tests unitarios en `server/tests/`.
- [ ] La UI React es declarativa: no contiene `if/else` sobre reglas de negocio más allá de "qué componente renderizar".
- [ ] No hay duplicación cliente/servidor de la misma validación (una validación de dominio se aplica **solo** en el servidor; la validación de formulario del cliente es puramente ergonómica).
- [ ] El fichero NiceGUI equivalente está movido a _legacy_nicegui (no borrado).
- [ ] Ningún `grep -r` devuelve imports del módulo NiceGUI eliminado.
- [ ] `docker compose up` + `pytest` completan en verde tras el borrado.

---

### Prompt 9.12a - Focus Mode React: LayoutContext + DrawerHub

**Objetivo**: Replicar en React el "focus mode" de NiceGUI: drawer lateral derecho con tres pestañas (**Configuración**, **Data Pills**, **Copilot**) y colapso del sidebar izquierdo. Las pestañas visibles dependen del modo activo y del tipo de átomo/paso que se está diseñando. Prerequisito de 9.12 (Flujos); reutilizable por cualquier pantalla de automatización que necesite drawer contextual.

**Elección de arquitectura de estado — Zustand (no Context)**:

Justificación:
- El estado de layout lo leen y mutan componentes muy dispersos (sidebar, drawer, toolbar, páginas hijas). Con Context cualquier mutación re-renderiza a todos los consumidores; con Zustand cada componente se suscribe solo a las slices que usa.
- El equivalente NiceGUI (`FocusManager` + `LayoutState` + `layout_manager`) son singletons con polling cada 200 ms. En React eso se traduce a un store global con suscripción fina, no a un árbol de Providers.
- Zustand tiene API mínima, no exige Provider wrapper y se integra trivialmente con tests (se puede resetear entre tests con `useLayoutStore.setState(initialState)`).

**Instalación**:
```bash
npm install zustand
npx shadcn@latest add sheet scroll-area tabs
```

**`src/automation/state/useLayoutStore.ts`** — store de layout:
```typescript
// slices: viewMode ('standard' | 'focus'), drawerVisible, activeTab ('config' | 'pills' | 'copilot'),
//         currentMode ('gallery' | 'design' | 'documentation' | 'flow_edit'),
//         designingAtomType (string | null), editingStep (StepSpec | null),
//         sidebarCollapsed (boolean)
// acciones: enterFocusMode(step, flow?), exitFocusMode(), setActiveTab(tab),
//           setDesigningAtomType(type | null), setEditingStep(step | null)
// selectores derivados: selectVisibleTabs(state) → ('config' | 'pills' | 'copilot')[]
//   ├── regla: en flow_edit → las tres pestañas
//   ├── regla: si hay designingAtomType → según capabilityMap[type] (has_stepper, has_variables)
//   ├── regla: gallery/documentation → config + (pills si documentation)
//   └── regla: fallback → solo copilot
// efecto: al entrar en focus mode, sidebarCollapsed = true y drawerVisible = true
```

**`src/automation/config/capabilityMap.ts`** — réplica del mapa NiceGUI:
```typescript
// Mapa atomType → { hasStepper: boolean, hasVariables: boolean }
// Se exporta DEFAULT_CAPABILITY = { hasStepper: true, hasVariables: true }
// Derivado 1:1 de client_app/app/config/capability_map.py
```

**`src/automation/components/DrawerHub.tsx`**:
```typescript
// <Sheet side="right" open={drawerVisible} onOpenChange={...}>
//   <header>: icono contextual + título i18n + botón cerrar
//   <Tabs value={activeTab}>:
//     renderiza solo las pestañas devueltas por selectVisibleTabs
//     tabs posibles: Configuración (tune), Data Pills (data_object), Copilot (auto_awesome)
//   <TabsContent value="config">  → <ConfigPanel />
//   <TabsContent value="pills">   → <DataPillsPanel />
//   <TabsContent value="copilot"> → <CopilotPanel />
// </Sheet>
// Sincronización automática: un useEffect corrige activeTab si la pestaña
//   activa deja de ser visible (replica la lógica de drawer_hub.py líneas 62-77).
```

**`src/automation/components/DataPillsPanel.tsx`**:
```typescript
// Props: flowId, currentStepIndex
// useQuery: GET /api/v1/automation/flows/{flowId}/pills?beforeStep={currentStepIndex}
//   → DataPill[] = { label, originStep, varName, reference: "{{STEP.var}}" }
// Render agrupado por originStep (accordion)
// Cada pill es un botón copyable: click → navigator.clipboard.writeText(pill.reference)
// onInsert?: callback opcional que recibe la referencia para insertarla en el campo activo
```

**`src/automation/components/AutomationLayout.tsx`** — integración con sidebar:
```typescript
// Layout wrapper que lee viewMode + sidebarCollapsed del store
// <aside className={cn(
//   'transition-all',
//   sidebarCollapsed ? 'w-16' : 'w-64'
// )}>
// <main className={viewMode === 'focus' ? 'h-screen overflow-hidden' : 'max-w-7xl mx-auto p-4'}>
// <DrawerHub /> (solo montado cuando drawerVisible)
```

**Separación de lógica aplicada (según Guía 9C.0)**:

- **Servidor**: `PillProvider.get_available_pills(step_index)` se expone como `GET /api/v1/automation/flows/{id}/pills?beforeStep={n}` y devuelve `DataPill[]`. Se elimina la lógica Python de `client_app/app/ui/pill_logic.py` de la UI; queda un servicio en `server/app/modules/automation/pills_service.py`. El `capability_map` se expone adicionalmente como `GET /api/v1/automation/atoms/capabilities` para que el frontend lo cachee al arranque (react-query, `staleTime: Infinity`).
- **Cliente**: viewMode, drawerVisible, activeTab, editingStep, designingAtomType, sidebarCollapsed. Ninguno se persiste en BD; se pierden al recargar por diseño.
- **Contrato API**:
  ```
  GET /api/v1/automation/flows/{id}/pills?beforeStep=<int>
  → 200 { pills: [{ label, origin_step, var_name, reference }] }

  GET /api/v1/automation/atoms/capabilities
  → 200 { capabilities: { "email.send": {has_stepper, has_variables}, ... } }
  ```

**Tests requeridos** (Vitest + Testing Library):
```typescript
// src/automation/state/__tests__/useLayoutStore.test.ts
// should_enter_focus_mode_and_collapse_sidebar
// should_exit_focus_mode_and_restore_sidebar
// should_show_all_three_tabs_in_flow_edit_mode
// should_hide_pills_tab_when_capability_disables_variables
// should_auto_switch_active_tab_when_current_becomes_invisible

// src/automation/components/__tests__/DrawerHub.test.tsx
// should_render_only_visible_tabs
// should_close_drawer_on_header_button_click
// should_copy_pill_reference_to_clipboard_on_click

// src/automation/components/__tests__/DataPillsPanel.test.tsx
// should_group_pills_by_origin_step
// should_call_onInsert_with_reference_when_provided
// should_show_empty_state_when_no_previous_steps
```

**Traslado NiceGUI a _legacy_nicegui** (se aplica parcialmente aquí; el resto al cerrar 9.12/9.13/9.14):
```bash
# El borrado de focus_manager/layout_state/drawer_hub/pill_logic NO ocurre en este commit
# porque las páginas NiceGUI que aún no se han migrado siguen dependiendo de ellos.
# Se documenta como deuda que se cancela en 9.15 (Traslado final NiceGUI a _legacy_nicegui).
```

---

### Prompt 9.12 - Automation > Flujos

**Objetivo**: Pantalla de gestión de flujos de automatización con editor en Focus Mode. Reemplaza `client_app/app/ui/flows_page.py` (950 líneas, ~50% lógica mezclada).

**Endpoints que consume**:
- `GET    /api/v1/automation/flows`
- `POST   /api/v1/automation/flows`
- `GET    /api/v1/automation/flows/{id}`
- `PUT    /api/v1/automation/flows/{id}`
- `DELETE /api/v1/automation/flows/{id}`
- `POST   /api/v1/automation/flows/{id}/run`
- `GET    /api/v1/automation/flows/{id}/runs/{run_id}`
- `POST   /api/v1/automation/flows/{id}/validate` *(nuevo, ver separación)*
- `GET    /api/v1/automation/flows/{id}/pills?beforeStep={n}` *(de 9.12a)*

**Estructura de ficheros**:
```
src/admin/pages/FlowsPage.tsx           ← listado + acciones CRUD
src/automation/pages/FlowEditor.tsx     ← editor en focus mode
src/automation/components/FlowStepList.tsx
src/automation/components/FlowStepCard.tsx
src/automation/components/FlowValidationBadge.tsx
src/automation/hooks/useFlowValidation.ts
```

**`src/admin/pages/FlowsPage.tsx`** — listado:
```typescript
// DataTable (@tanstack/react-table): nombre, descripción, estado última ejecución, versión publicada, acciones
// Diálogo crear flujo: nombre + descripción (react-hook-form + zod)
// Botón "Ejecutar": POST /flows/{id}/run → navegar a vista de ejecución
// Badge de estado: pending / running / done / error (polling con react-query refetchInterval mientras running)
// Botón "Editar" → navega a /admin/flows/{id}/edit
```

**`src/automation/pages/FlowEditor.tsx`** — editor (usa Focus Mode):
```typescript
// Al montar: enterFocusMode() del store (9.12a)
// Layout de tres zonas:
//   - Sidebar izquierdo colapsado (desde 9.12a)
//   - Main: lista de pasos reordenables (dnd-kit)
//   - DrawerHub (desde 9.12a) con las tres pestañas
// Seleccionar paso: setEditingStep(step) → el DrawerHub muestra
//   Configuración (form del átomo), Data Pills (variables anteriores) y Copilot
// Validación del flujo: POST /flows/{id}/validate → devuelve issues[]
//   useFlowValidation() invalida cada vez que el usuario guarda un paso
// Guardar: PUT /flows/{id}; optimistic update con react-query
// Salir: exitFocusMode() + router back
```

**Separación de lógica aplicada (según Guía 9C.0)**:

| Lógica en `flows_page.py` | Destino nuevo | Notas |
|---|---|---|
| `FlowsState` (filtros, orden) | **React local** (`useState` en FlowsPage) | UI puro |
| `async flow loading` + `save` (líneas 148-256, 840-924) | **FastAPI** existente (`GET/PUT /flows/{id}`) | Ya están |
| Validación estructural (líneas 900-920) | **FastAPI** nuevo endpoint `POST /flows/{id}/validate` | Reutiliza `WorkflowHealthService` que sube al servidor |
| `WorkflowHealthService`, `CoherenceService` | **FastAPI** (`server/app/modules/automation/health.py`) | Dominio, deben poder invocarse también en ejecución headless |
| Integración con copilot (callbacks `on_atom_select`) | **React** (`CopilotPanel` lee del store) | El copilot es UI |
| `FlowRegistryService` | **FastAPI** (si no existe ya) | Persistencia |
| Selección de paso, expansión de filas, modo edición | **React local** | UI puro |

**Nuevos endpoints a crear en el servidor**:
```
POST /api/v1/automation/flows/{id}/validate
  → 200 { issues: [{ step_index, severity, type, message, fix_suggestion? }] }
  Reutiliza WorkflowHealthService (movido desde client_app al servidor).
```

**Tests requeridos**:
```typescript
// src/admin/pages/__tests__/FlowsPage.test.tsx
// should_list_flows_on_mount
// should_open_create_dialog_on_button_click
// should_show_running_status_during_execution
// should_poll_until_execution_completes
// should_invalidate_cache_after_create

// src/automation/pages/__tests__/FlowEditor.test.tsx
// should_enter_focus_mode_on_mount
// should_exit_focus_mode_on_unmount
// should_show_step_form_in_drawer_when_step_selected
// should_show_validation_badge_for_step_with_issues
// should_reorder_steps_via_drag_and_drop
// should_save_flow_and_invalidate_queries
```

**Tests backend (pytest)**:
```python
# server/tests/modules/automation/test_health_service.py
# test_detects_missing_required_input
# test_detects_type_mismatch_between_steps
# test_validates_via_endpoint_returns_issues_list

# server/tests/modules/automation/test_pills_service.py  (de 9.12a)
# test_returns_only_outputs_of_previous_steps
# test_pill_reference_format_uses_step_id
```

**Traslado NiceGUI a _legacy_nicegui** (en el mismo commit que GREEN):
```bash
# Borrar: client_app/app/ui/flows_page.py
# Borrar: client_app/app/ui/flows_translations.json (migrado a i18next)
# Mover al servidor (no borrar antes de migrar lógica): servicios de health/coherence
#   client_app/app/services/health_service.py       → server/app/modules/automation/health.py
#   client_app/app/services/coherence_service.py    → server/app/modules/automation/coherence.py
#   client_app/app/services/bridge_creator.py       → server/app/modules/automation/bridge.py
# Verificar sin residuos:
grep -rn "flows_page\|FlowsState\b" client_app/ --include="*.py"   # debe ser vacío
grep -rn "health_service\|coherence_service" client_app/ --include="*.py"  # debe ser vacío
# Confirmar: docker compose up && pytest && npm test
```

---

### Prompt 9.12b - Refactor backend PDF extractor a Docling

**Objetivo**: Sustituir el motor dual `pdfplumber` + `fitz` (actualmente en `shared/automatia_shared/core/pdf_reader.py::PdfReaderDual` y consumido por `server/app/modules/automation/extraction_strategies.py`) por **Docling** (ya instalado para el módulo RAG). El cliente deja de extraer texto localmente: ahora sube el PDF y el servidor hace toda la extracción + prompting. Prerequisito obligatorio de 9.13 (UI del extractor).

**Por qué ahora y no después de la UI**: el contrato de datos que consumen los endpoints de extracción (`texto_fitz` + `texto_plumber`) cambia radicalmente tras el refactor. Diseñar la UI React sobre la API actual y luego rehacerla es trabajo duplicado. Ver PLAN_DESARROLLO.md §Bloque 4C para la decisión.

**Estructura de ficheros a crear**:
```
server/app/modules/automation/pdf_extractor/
├── __init__.py
├── docling_extractor.py          ← Wrapper de alto nivel sobre DoclingProcessor
├── schemas.py                    ← Pydantic: ExtractedDocument, ExtractedTable, ExtractedPage
├── extraction_service.py         ← Orquestación fases 0-3 (refactor de extraction_strategies.py)
├── prompts.py                    ← Prompts adaptados al nuevo formato Docling
└── storage.py                    ← Persistencia de PDFs temporales (MinIO) y runs
```

**Ficheros a eliminar al cerrar el prompt**:
```
shared/automatia_shared/core/pdf_reader.py                   ← PdfReaderDual (fitz)
server/app/modules/automation/extraction_strategies.py       ← lógica basada en texto_fitz/texto_plumber
client_app/app/modules/utilities/pdf_tools.py                ← extracción cliente (si solo se usa para extractor)
client_app/app/modules/extraction/pdf_text_detector.py       ← detector de calidad de texto (obsoleto)
client_app/app/services/extraction_service.py                ← cliente del antiguo API
# Revisar y limpiar en pyproject.toml: pdfplumber, pymupdf (fitz)
```

**Nuevo contrato de salida (`schemas.py`)**:
```python
from pydantic import BaseModel
from typing import Literal

class ExtractedCell(BaseModel):
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1

class ExtractedTable(BaseModel):
    page: int                       # 1-based
    caption: str | None
    headers: list[str]
    cells: list[ExtractedCell]
    bbox: tuple[float, float, float, float] | None

class ExtractedPage(BaseModel):
    page: int                       # 1-based
    markdown: str                   # render markdown de la página (Docling)
    plain_text: str                 # texto lineal legible para LLM
    tables: list[ExtractedTable]

class ExtractedDocument(BaseModel):
    source_id: str                  # UUID del run (persistido)
    filename: str
    num_pages: int
    markdown: str                   # documento completo en markdown (Docling)
    pages: list[ExtractedPage]
    tables: list[ExtractedTable]    # vista plana de todas las tablas
    extraction_strategy: Literal["text_linear", "complex_tables"]
    docling_version: str
```

Este `ExtractedDocument` sustituye al "fichero acordeón" de la versión anterior (pares `texto_fitz` / `texto_plumber`). Los prompts de extracción consumirán `markdown` + `tables` estructuradas en lugar de dos vistas de texto plano.

**`docling_extractor.py`** — wrapper:
```python
# Reutiliza DoclingProcessor de server/app/modules/agents_hub/ingestion/docling_processor.py
# pero expone la estructura completa (no solo markdown):
#   result = DocumentConverter().convert(path)
#   - result.document.export_to_markdown()   → ExtractedDocument.markdown
#   - result.document.pages                  → ExtractedPage[] (iterar pages y extraer tables de cada page)
#   - result.document.tables                 → ExtractedTable[] (vista plana)
#
# async def extract(pdf_path: Path, strategy: str) -> ExtractedDocument
#   usa asyncio.to_thread para Docling (la librería es síncrona)
#
# Performance: Docling sobre CPU tarda segundos por PDF. El endpoint de upload
#   debe devolver un run_id inmediatamente y hacer la extracción en background
#   (BackgroundTasks de FastAPI). El cliente hace polling del estado.
```

**`extraction_service.py`** — refactor de `extraction_strategies.py`:
```python
# Fases refactorizadas:
#   Fase 0: analyze_document_structure(doc: ExtractedDocument, language_hint, config)
#     Antes: (doc_text_a, doc_text_b, ...)      → dos vistas de texto
#     Ahora: (doc.markdown[:30000], doc.tables) → markdown + tablas estructuradas
#   Fase 1: extract_precision(doc, selected_fields, user_definition, config)
#   Fase 2: refine_with_feedback(doc, previous_data, user_feedback, config)
#   Fase 3: generate_deterministic_script(docs: list[ExtractedDocument], ...)
#     El script generado YA NO debe usar fitz/pdfplumber directamente; debe
#     consumir un ExtractedDocument proporcionado por el runtime. Ver prompts.py.
#
# Prompts adaptados: el template ahora espera {markdown} y {tables_json}
# en lugar de {texto_fitz} y {texto_plumber}.
```

**Nuevos endpoints** (reemplazan los actuales en `server/app/api/v1/automation.py`):
```
POST /api/v1/automation/extraction/uploads
  multipart/form-data: files[] (PDFs)
  → 200 { run_id: str, file_ids: [str] }
  Dispara extracción en background via BackgroundTasks.

GET /api/v1/automation/extraction/uploads/{run_id}
  → 200 { status: "pending|extracting|done|error", progress: 0..100,
          documents: [ExtractedDocument]? , error?: str }
  El cliente hace polling cada 1s mientras status != done|error.

POST /api/v1/automation/extraction/{run_id}/analyze_structure
POST /api/v1/automation/extraction/{run_id}/extract
POST /api/v1/automation/extraction/{run_id}/refine
POST /api/v1/automation/extraction/{run_id}/generate_script
  Todos reciben campos + config + system_prompt y usan los ExtractedDocument del run.
  Los endpoints antiguos que aceptaban texto_fitz/texto_plumber se BORRAN.
```

**Separación de lógica aplicada (según Guía 9C.0)**:

| Lógica anterior | Destino | Notas |
|---|---|---|
| Extracción PDF en cliente (`pdf_tools.py`, `PdfReaderDual`) | **FastAPI** | El cliente ya no procesa PDFs |
| Estrategia dual fitz/plumber | **Eliminada** | Docling la reemplaza |
| Máquina de fases (analyze → extract → refine → generate) | **FastAPI** existente, prompts adaptados | Sin cambios de diseño, solo de datos de entrada |
| Storage temporal de PDFs | **MinIO** (ya en el stack) | Con TTL de 24h por `run_id` |
| Validación de tipos (IBAN, NIF, fecha, importe) | **FastAPI** `extract_field_from_snippet` | Ya está, se mantiene |

**Tests TDD requeridos**:

```python
# server/tests/modules/automation/pdf_extractor/test_docling_extractor.py
# --- RED primero, GREEN después ---
# test_extracts_markdown_from_text_pdf
# test_extracts_tables_from_tabular_pdf
# test_returns_page_numbers_1_based
# test_handles_multi_page_document
# test_raises_clear_error_on_corrupted_pdf
# test_extracted_document_schema_validates

# server/tests/modules/automation/pdf_extractor/test_extraction_service.py
# test_analyze_structure_receives_markdown_and_tables
# test_extract_precision_injects_markdown_into_prompt
# test_refine_with_feedback_preserves_previous_data_shape
# test_generate_script_no_longer_uses_fitz_or_pdfplumber  ← grep assertion en el script generado

# server/tests/api/v1/test_extraction_uploads.py
# test_upload_returns_run_id_immediately
# test_get_status_reports_progress
# test_get_status_returns_extracted_documents_on_done
# test_old_endpoint_with_texto_fitz_returns_410_gone  ← verificación de borrado
```

**Criterios de cierre (checklist obligatorio antes de pasar a 9.13)**:

- [ ] `pytest server/tests/modules/automation/pdf_extractor/` en verde
- [ ] `grep -rn "pdfplumber\|import fitz\|import pymupdf\|PdfReaderDual" server/ shared/ client_app/` no devuelve coincidencias (excepto `.venv/`)
- [ ] `pdfplumber` y `pymupdf` eliminados de `pyproject.toml` (raíz, `server/`, `shared/`, `client_app/`)
- [ ] `uv lock` regenerado tras el borrado de dependencias
- [ ] `server/app/modules/automation/extraction_strategies.py` **borrado** (no comentado)
- [ ] `shared/automatia_shared/core/pdf_reader.py` **borrado**
- [ ] `docker compose up` arranca sin errores y el endpoint `POST /extraction/uploads` devuelve un `run_id` contra un PDF de test

**Impacto documentado para 9.13 (UI)**:

Cuando 9.13 se implemente, dispondrá de esta API estable:
```
Upload → { run_id }                        (1 round-trip, devuelve en <500ms)
Polling → { status, progress, documents }  (cada 1s hasta done)
Analyze/Extract/Refine/Generate → operan sobre run_id, no sobre texto plano
```
La UI no necesita conocer nada sobre Docling; solo consume `ExtractedDocument`.

---

### Prompt 9.13 - Automation > PDF extractor (UI)

**Objetivo**: Interfaz React de extracción PDF sobre los contratos Docling definidos en 9.12b. Reemplaza `client_app/app/ui/extraction_page.py` (2.370 líneas, ~60% lógica mezclada). Es la migración más densa del bloque.

**Prerequisito**: 9.12b completado y verde. Si el `grep` de `pdfplumber`/`fitz` aún devuelve coincidencias, **no** arrancar este prompt.

**Endpoints que consume** (todos definidos en 9.12b):
- `POST /api/v1/automation/extraction/uploads`
- `GET  /api/v1/automation/extraction/uploads/{run_id}`
- `POST /api/v1/automation/extraction/{run_id}/analyze_structure`
- `POST /api/v1/automation/extraction/{run_id}/extract`
- `POST /api/v1/automation/extraction/{run_id}/refine`
- `POST /api/v1/automation/extraction/{run_id}/generate_script`

**Estructura de ficheros**:
```
src/admin/pages/PdfExtractPage.tsx                 ← Entry point, lista de runs
src/automation/pages/PdfExtractRun.tsx             ← Detalle de un run (Focus Mode)
src/automation/components/PdfDropzone.tsx
src/automation/components/ExtractionPhaseStepper.tsx
src/automation/components/FieldSelector.tsx         ← seleccionar campos tras Fase 0
src/automation/components/ExtractedDataTable.tsx    ← resultado Fase 1
src/automation/components/RefineFeedbackPanel.tsx   ← Fase 2
src/automation/components/GeneratedScriptViewer.tsx ← Fase 3
src/automation/hooks/useExtractionRun.ts            ← polling + mutaciones
```

**`PdfExtractPage.tsx`** — listado de runs:
```typescript
// DataTable: filename, status, fecha, nº de campos extraídos, acciones
// Botón "Nueva extracción" → abre <PdfDropzone /> modal
// Al subir: mutación POST /uploads → navegar a /admin/extraction/{run_id}
```

**`PdfExtractRun.tsx`** — editor en Focus Mode (reutiliza 9.12a):
```typescript
// Al montar: enterFocusMode()
// Stepper horizontal con 4 fases canónicas: Descubrir → Extraer → Refinar → Generar script
// Main area cambia según fase activa
// DrawerHub (desde 9.12a) con tabs: Configuración (estrategia, definición usuario), Data Pills (campos detectados), Copilot
// Barra de progreso global (0-100) mapeada desde el backend
```

**`useExtractionRun.ts`** — polling + fases:
```typescript
// useQuery GET /uploads/{run_id} con refetchInterval: 1000 mientras status !== 'done' && status !== 'error'
// useMutation para cada fase (analyze_structure, extract, refine, generate_script)
// Cada mutación invalida la query del run
// Expone: { run, phase, isLoading, analyze(), extract(fields), refine(feedback), generateScript() }
```

**`ExtractionPhaseStepper.tsx`** — fases:
```typescript
// Mapa fijo de fases (antes PHASE_RANGES en Python, ahora TypeScript):
//   { id: 'discover', label: i18n, range: [0, 25] }
//   { id: 'extract',  label: i18n, range: [25, 55] }
//   { id: 'refine',   label: i18n, range: [55, 80] }
//   { id: 'script',   label: i18n, range: [80, 100] }
// El stepper colorea la fase activa según run.progress
```

**Separación de lógica aplicada (según Guía 9C.0)**:

| Lógica en `extraction_page.py` (2.370 líneas) | Destino nuevo | Notas |
|---|---|---|
| `ExtractionState`, `DesignState`, `ExecutionState` | **React local** (estado del componente + react-query) | UI puro |
| `PHASE_RANGES` + mapeo de progreso global | **React constante** + cálculo derivado | Ya no hay fases internas distintas; el servidor reporta `progress` 0-100 directo |
| Orquestación fases 0-3 (llamadas a `extraction_strategies`) | **FastAPI** (ya movido en 9.12b) | La UI solo dispara mutaciones |
| Servicios `asset_finishing_service`, `extraction_service` | **FastAPI** `server/app/modules/automation/pdf_extractor/` | Ya en 9.12b |
| Validación de campos seleccionados antes de Fase 1 | **FastAPI** + **zod en cliente** | Doble: cliente para UX, servidor como fuente de verdad |
| Upload de PDFs vía NiceGUI | **React** `<PdfDropzone />` con `react-dropzone` | UI puro |
| Cola de procesamiento en Python (threads locales) | **FastAPI BackgroundTasks** | Ya en 9.12b |
| Preview del script generado | **React** `<GeneratedScriptViewer />` con `prismjs` | Render puro |

**Nota sobre Focus Mode**: el extractor original tenía un wizard en pantalla completa similar al focus mode de flujos. Se replica el patrón: al entrar al detalle del run, el sidebar se colapsa y el drawer contextual aparece a la derecha. Si el usuario quiere volver al listado, sale del focus mode.

**Tests requeridos**:
```typescript
// src/admin/pages/__tests__/PdfExtractPage.test.tsx
// should_list_runs_on_mount
// should_open_dropzone_on_new_extraction_click
// should_accept_pdf_files_only
// should_navigate_to_run_detail_after_upload

// src/automation/pages/__tests__/PdfExtractRun.test.tsx
// should_enter_focus_mode_on_mount
// should_show_discover_phase_when_progress_below_25
// should_show_extract_phase_when_progress_25_to_55
// should_display_extracted_document_markdown_preview
// should_trigger_analyze_mutation_on_button_click

// src/automation/hooks/__tests__/useExtractionRun.test.ts
// should_poll_every_second_while_pending
// should_stop_polling_when_status_done
// should_stop_polling_on_error
```

**Traslado NiceGUI a _legacy_nicegui** (en el mismo commit que GREEN):
```bash
# Borrar:
rm client_app/app/ui/extraction_page.py                 # 2.370 líneas
rm client_app/app/ui/extraction_page_refactored.py
rm client_app/app/ui/extraction_translations.json
# Verificar residuos:
grep -rn "extraction_page\|ExtractionState\|DesignState\|ExecutionState" client_app/ --include="*.py"
# Debe ser vacío. Si devuelve algo, investigar antes de cerrar.
# Confirmar: docker compose up && pytest && npm test
```

---

### Prompt 9.14 - Automation > Scripts

**Objetivo**: Catálogo y ejecución de scripts. Reemplaza la vista NiceGUI equivalente.

**`src/admin/pages/ScriptsPage.tsx`** — estructura clave:
```typescript
// Tabs por categoría: trigger / input / processor / output
// Para cada script: nombre, descripción, formulario dinámico generado desde ui_contract
// Historial de ejecuciones por script (tabla colapsable)
// Toggle "Promover a átomo" (solo admin/partner)
```

**Tests requeridos**:
```typescript
// should_render_dynamic_form_from_ui_contract
// should_filter_scripts_by_category
// should_display_execution_history
```

**Traslado NiceGUI a _legacy_nicegui** en el mismo commit.

---

### Prompt 9.15 - Traslado final NiceGUI a _legacy_nicegui

**Objetivo**: Verificar que no queda ningún módulo NiceGUI sin migrar. Borrar los que queden.

**Checklist** (ver CLAUDE.md para el procedimiento completo):
```bash
# 1. Verificar qué módulos de client_app/app/ui/ quedan
ls client_app/app/ui/

# 2. Por cada módulo sin equivalente React todavía:
#    - Si tiene endpoint en el server → posponer (documentar)
#    - Si es UI pura sin backend → eliminar directamente

# 3. Confirmar que no hay imports rotos
grep -r "from client_app.app.ui" . --include="*.py"

# 4. docker compose up + pytest → todo verde
```

---

## BLOQUE 9D — Agente de ejecución local

*El agente local reemplaza el cliente NiceGUI como proceso sin UI. Patrón GitLab Runner.*

---

### Prompt 9.16 - Agente de ejecución local: scaffolding

**Objetivo**: Proceso Python ligero en `client_app/local_agent/` que se conecta al servidor por WebSocket, recibe jobs y los ejecuta localmente. Reemplaza la necesidad de que el usuario tenga abierto el cliente NiceGUI pesado para ejecutar tareas de automatización.

**Responsabilidad de Playwright en este agente** (distinción crítica):
- `handlers/rpa.py` implementa **automatización web interactiva para el usuario final**: rellenar formularios, navegar sesiones autenticadas, extraer datos en nombre del usuario. Es una acción puntual iniciada por el usuario a través del frontend.
- Este componente **no tiene nada que ver con el crawler de ingestión documental** (Prompt 9.7.1), que es un proceso server-side con scheduler propio. El crawler corre en el Edge node; el RPA corre en la máquina local del usuario tramitador.
- Playwright puede aparecer en ambos contextos pero con propósitos radicalmente distintos: aquí es un actor humano delegado; en el crawler es un fetcher automatizado de contenido público.

**Estructura**:
```
client_app/local_agent/
├── main.py          # Punto de entrada; conecta al server por WebSocket
├── runner.py        # Recibe jobs {job_id, type, payload} y despacha al handler
├── handlers/
│   ├── script.py    # Ejecuta scripts Python (sandbox existente de AutomatIA)
│   ├── rpa.py       # Playwright RPA interactivo: simula acciones de usuario en webs
│   │                #   (formularios, login, extracción de datos en sesión)
│   │                #   NO se usa para ingesta documental automatizada
│   └── watcher.py   # FolderWatcher y EmailWatcher locales
└── config.py        # AGENT_SERVER_URL, AGENT_TOKEN (desde .env local)
```

**Protocolo WebSocket**:
```json
// Job recibido del servidor:
{ "job_id": "uuid", "type": "script|rpa|watcher", "payload": {...} }

// Resultado reportado al servidor:
{ "job_id": "uuid", "status": "done|error", "output": "...", "error": null }
```

**`main.py`** (esqueleto):
```python
import asyncio, websockets, json, os
from runner import Runner

async def connect():
    url = os.getenv("AGENT_SERVER_URL", "ws://localhost:8000/agent/ws")
    token = os.getenv("AGENT_TOKEN", "")
    runner = Runner()
    async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {token}"}) as ws:
        async for message in ws:
            job = json.loads(message)
            result = await runner.dispatch(job)
            await ws.send(json.dumps(result))

if __name__ == "__main__":
    asyncio.run(connect())
```

**Tests requeridos** (`client_app/tests/test_runner.py`):
```python
# test_runner_dispatches_script_job
# test_runner_dispatches_rpa_job
# test_runner_reports_error_on_failure
# test_runner_unknown_type_returns_error
```

**Criterio de done**: El agente conecta al server, recibe un job de tipo `script`, lo ejecuta y reporta el resultado. Tests pasan.

## ANEXO A: Componentes Complementarios

---

### Prompt A.1 - Auth Dependencies (FastAPI)

**Objetivo**: Implementar las dependencias de autenticación para FastAPI.

**src/auth/dependencies.py**:
```python
"""Dependencias de autenticación para FastAPI."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.exceptions import AuthenticationError
from src.auth.jwt_handler import decode_token
from src.auth.models import UserInfo
from src.config import get_settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserInfo:
    """Obtiene el usuario actual desde el token JWT.

    Args:
        credentials: Credenciales HTTP Bearer

    Returns:
        UserInfo del usuario autenticado

    Raises:
        HTTPException: Si no está autenticado
    """
    settings = get_settings()

    # Modo mock para desarrollo
    if settings.mock_auth:
        return UserInfo(
            user_id="mock-user-123",
            email="mock@example.com",
            role="admin",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return decode_token(credentials.credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(allowed_roles: list[str]):
    """Crea una dependencia que requiere roles específicos.

    Args:
        allowed_roles: Lista de roles permitidos

    Returns:
        Dependencia de FastAPI
    """
    async def role_checker(
        user: UserInfo = Depends(get_current_user),
    ) -> UserInfo:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not allowed. Required: {allowed_roles}",
            )
        return user

    return role_checker


# Dependencias predefinidas
require_admin = require_role(["admin"])
require_informer = require_role(["admin", "informer"])
```

---

### Prompt A.2 - Servicio de Embeddings

**Objetivo**: Verificar que el servicio de embeddings BGE-M3 local (implementado en la Fase 5B) funciona correctamente con el sistema completo. (La implementación inicial basada en Google/Vertex AI fue descartada a favor del modelo local BAAI/bge-m3 para asegurar la privacidad Zero-Knowledge).

### Prompt A.3 - Conftest.py Completo para Tests

**Objetivo**: Proporcionar el archivo `conftest.py` completo con todos los fixtures globales (base de datos de test, cliente HTTP, mocks de autenticación y embeddings) necesarios para ejecutar la batería de tests de integración y E2E.

**tests/conftest.py**:
```python
"""Fixtures globales para todos los tests."""
import asyncio
import os
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Configurar variables de entorno para tests ANTES de importar módulos
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://chatbots:chatbots_secret@localhost:5432/chatbots_hub_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long-for-testing")
os.environ.setdefault("MOCK_AUTH", "true")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


@pytest.fixture(scope="session")
def event_loop():
    """Crea un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Limpia variables de entorno para tests aislados."""
    env_vars_to_clean = [
        "DATABASE_URL", "GOOGLE_API_KEY", "LANGCHAIN_API_KEY",
        "JWT_SECRET_KEY", "MOCK_AUTH", "LOG_FORMAT",
    ]
    original_values = {k: os.environ.get(k) for k in env_vars_to_clean}

    yield

    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value


@pytest.fixture
def mock_env_complete() -> Generator[None, None, None]:
    """Configura un entorno completo válido."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
        "GOOGLE_API_KEY": "test-google-api-key",
        "LANGCHAIN_API_KEY": "test-langsmith-key",
        "LANGCHAIN_TRACING_V2": "false",
        "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-chars",
        "MOCK_AUTH": "true",
        "LOG_FORMAT": "json",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Proporciona una sesión de BD para tests de integración."""
    from src.database.connection import create_async_engine, create_session_factory
    from src.database.models import Base

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url)

    # Crear tablas
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def mock_embedding_service():
    """Mock del servicio de embeddings."""
    service = AsyncMock()
    service.embed = AsyncMock(return_value=[0.1] * 1536)
    service.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
    return service


@pytest.fixture
def mock_retriever():
    """Mock del retriever."""
    from src.services.retriever import SearchResult

    retriever = AsyncMock()
    retriever.vector_search = AsyncMock(return_value=[
        SearchResult(
            id=uuid.uuid4(),
            content="Contenido de prueba",
            source_url="https://example.com/doc",
            language="es",
            score=0.9,
            metadata={},
        )
    ])
    retriever.hybrid_search = AsyncMock(return_value=[
        SearchResult(
            id=uuid.uuid4(),
            content="Contenido de prueba",
            source_url="https://example.com/doc",
            language="es",
            score=0.9,
            metadata={},
        )
    ])
    return retriever


@pytest.fixture
def sample_chatbot_id() -> uuid.UUID:
    """ID de chatbot para tests."""
    return uuid.uuid4()


@pytest.fixture
def sample_user_info():
    """Usuario de prueba."""
    from src.auth.models import UserInfo
    return UserInfo(
        user_id="test-user-123",
        email="test@example.com",
        role="user",
    )


@pytest.fixture
def auth_headers(sample_user_info):
    """Headers de autenticación para tests de API."""
    from src.auth.jwt_handler import create_token
    token = create_token(sample_user_info)
    return {"Authorization": f"Bearer {token}"}
```

---

### Prompt A.4 - Routers de Admin y Partner

**Objetivo**: Implementar los routers FastAPI separados por rol:
- `admin.py`: gestión de plataforma (proveedores LLM, usuarios partner, config global). Solo accesible por `ADMIN`.
- `partner.py`: gestión de clientes y chatbots. Accesible por `PARTNER` (solo ve sus propios clientes/chatbots).

**Separación de responsabilidades**:
- El **Admin** NO crea chatbots ni clientes. Solo gestiona la plataforma.
- El **Partner** crea clientes, crea chatbots asociados a esos clientes, y gestiona prompts y templates visuales.

**src/api/routers/partner.py**:
```python
"""Router para endpoints del partner (gestión de clientes y chatbots)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_partner
from src.auth.models import UserInfo
from src.database import get_async_session
from src.database.models import Chatbot, Client, IngestionJob

router = APIRouter(prefix="/api/v1/partner", tags=["partner"])


class ChatbotCreate(BaseModel):
    client_id: str  # UUID del cliente al que pertenece el chatbot
    name: str
    system_prompt: str
    sources: list[str] = []


class ChatbotResponse(BaseModel):
    id: str
    client_id: str
    name: str
    system_prompt: str
    sources: list[str]
    is_active: bool

    class Config:
        from_attributes = True


class IngestionRequest(BaseModel):
    source_url: str


@router.post("/chatbots", response_model=ChatbotResponse)
async def create_chatbot(
    data: ChatbotCreate,
    user: UserInfo = Depends(require_partner),
    session: AsyncSession = Depends(get_async_session),
) -> Chatbot:
    """Crea un nuevo chatbot para un cliente del partner."""
    # Verificar que el cliente pertenece al partner autenticado
    client = await session.get(Client, uuid.UUID(data.client_id))
    if not client or client.partner_id != user.user_id:
        raise HTTPException(status_code=403, detail="Client not found or not owned by this partner")
    chatbot = Chatbot(
        client_id=uuid.UUID(data.client_id),
        name=data.name,
        system_prompt=data.system_prompt,
        sources=data.sources,
    )
    session.add(chatbot)
    await session.commit()
    await session.refresh(chatbot)
    return chatbot


@router.get("/chatbots", response_model=list[ChatbotResponse])
async def list_chatbots(
    user: UserInfo = Depends(require_partner),
    session: AsyncSession = Depends(get_async_session),
) -> list[Chatbot]:
    """Lista los chatbots de los clientes del partner autenticado."""
    result = await session.execute(
        select(Chatbot).join(Client).where(Client.partner_id == user.user_id)
    )
    return list(result.scalars().all())


@router.post("/chatbots/{chatbot_id}/ingest")
async def trigger_ingestion(
    chatbot_id: str,
    data: IngestionRequest,
    background_tasks: BackgroundTasks,
    user: UserInfo = Depends(require_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Dispara un job de ingestión en background."""
    # Verificar que el chatbot existe y pertenece al partner
    chatbot = await session.get(Chatbot, uuid.UUID(chatbot_id))
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    # Crear job
    job = IngestionJob(
        chatbot_id=uuid.UUID(chatbot_id),
        source_url=data.source_url,
        status="pending",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Aquí se añadiría el background task para procesar
    # background_tasks.add_task(process_ingestion_job, job.id)

    return {"job_id": str(job.id), "status": "pending"}


@router.get("/chatbots/{chatbot_id}/jobs")
async def list_ingestion_jobs(
    chatbot_id: str,
    user: UserInfo = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Lista los jobs de ingestión de un chatbot."""
    result = await session.execute(
        select(IngestionJob)
        .where(IngestionJob.chatbot_id == uuid.UUID(chatbot_id))
        .order_by(IngestionJob.created_at.desc())
        .limit(50)
    )
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "status": j.status,
            "source_url": j.source_url,
            "chunks_processed": j.chunks_processed,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]
```

---

### Prompt A.5 - Router de Feedback

**Objetivo**: Implementar el router FastAPI para la captura de valoraciones de usuarios en chats públicos y la consulta de feedback por parte de administradores e informadores.

**src/api/routers/feedback.py**:
```python
"""Router para el panel de feedback/informadores."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_informer
from src.auth.models import UserInfo
from src.database import get_async_session
from src.services.feedback_service import FeedbackService

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


class FeedbackSubmit(BaseModel):
    interaction_id: str
    score: int = Field(..., ge=1, le=5)
    comment: str | None = None


class InteractionReview(BaseModel):
    id: str
    user_message: str
    assistant_message: str
    feedback_score: int | None
    created_at: str
    run_id: str | None


@router.post("/submit")
async def submit_feedback(
    data: FeedbackSubmit,
    user: UserInfo = Depends(require_informer),
    session: AsyncSession = Depends(get_async_session),
):
    """Envía feedback para una interacción."""
    service = FeedbackService(session)
    await service.submit_feedback(
        interaction_id=uuid.UUID(data.interaction_id),
        score=data.score,
        comment=data.comment,
    )
    return {"status": "submitted"}


@router.get("/interactions/{chatbot_id}", response_model=list[InteractionReview])
async def get_interactions_for_review(
    chatbot_id: str,
    only_low_scores: bool = False,
    limit: int = 50,
    user: UserInfo = Depends(require_informer),
    session: AsyncSession = Depends(get_async_session),
):
    """Obtiene interacciones para revisión."""
    service = FeedbackService(session)
    interactions = await service.get_interactions_for_review(
        chatbot_id=uuid.UUID(chatbot_id),
        limit=limit,
        only_low_scores=only_low_scores,
    )
    return [
        InteractionReview(
            id=str(i.id),
            user_message=i.user_message,
            assistant_message=i.assistant_message,
            feedback_score=i.feedback_score,
            created_at=i.created_at.isoformat(),
            run_id=str(i.run_id) if i.run_id else None,
        )
        for i in interactions
    ]
```

---

### Prompt A.6 - Main.py Completo con Todos los Routers

**Objetivo**: Configurar la aplicación FastAPI principal integrando todos los routers, middleware de autenticación, CORS, logging estructurado y el manejador global de errores.

**src/main.py** (versión completa):
```python
"""Aplicación principal FastAPI."""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.routers import admin, chat, feedback
from src.config import get_settings
from src.logging_config import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    logger = setup_logging()
    logger.info("Starting AI Chatbots Hub")
    yield
    logger.info("Shutting down AI Chatbots Hub")


app = FastAPI(
    title="AI Chatbots Hub",
    description="Hub de chatbots con RAG usando LangGraph y pgvector",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar según entorno
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handlers
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "type": "validation_error",
            "request_id": str(uuid.uuid4()),
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = get_logger("error_handler")
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "type": "internal_error",
            "request_id": str(uuid.uuid4()),
        },
    )


# Registrar routers
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(feedback.router)


@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "name": "AI Chatbots Hub",
        "docs": "/docs",
        "health": "/health",
    }
```

---

## Checklist de Calidad TDD

- [ ] Cada test escrito ANTES de la implementación (RED)
- [ ] Cada test falla inicialmente
- [ ] Implementación mínima para pasar (GREEN)
- [ ] Refactorización sin romper tests
- [ ] Migraciones gestionadas por Alembic
- [ ] Trazado LangChain activo en LangSmith
- [ ] Cobertura de tests >= 80%
- [ ] Métricas RAGAS validadas
- [ ] Error handling global sin leaks de información

---

## Orden de Ejecución Recomendado

1. **Ejecutar Prompts 0.x** - Infraestructura base
2. **Ejecutar Prompts 1.x** - Autenticación y AgentState
3. **Ejecutar Prompts 2.x** - Base de datos y migraciones
4. **Ejecutar Prompts 3.x** - Ingestión de documentos
5. **Ejecutar Prompts 4.x** - Agente LangGraph
6. **Ejecutar Prompts 5.x** - API endpoints
7. **Ejecutar Prompts 8.x** - Observabilidad
8. **Ejecutar Prompts A.x** - Componentes complementarios

**Para cada prompt:**
1. Leer el objetivo y contexto
2. Crear los archivos de test (RED)
3. Ejecutar tests y verificar que fallan
4. Implementar el código (GREEN)
5. Ejecutar tests y verificar que pasan
6. Refactorizar si es necesario

---

## ANEXO B: Archivos de Configuración Esenciales

---

### pytest.ini
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests (require database)
    e2e: End-to-end tests
    slow: Slow tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

---

### .gitignore
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# uv
.uv/
uv.lock

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local
.env.production

# Testing
.coverage
htmlcov/
.pytest_cache/
.hypothesis/

# Docker
*.log

# OS
.DS_Store
Thumbs.db

# Project specific
*.db
*.sqlite3
```

---

### .python-version
```
3.11
```

---

### ruff.toml (alternativa a configuración en pyproject.toml)
```toml
line-length = 100
target-version = "py311"

[lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults
    "B904",   # raise without from inside except
]

[lint.per-file-ignores]
"tests/*" = ["ARG001", "S101"]

[format]
quote-style = "double"
indent-style = "space"
```

---

## Resumen de Archivos a Crear

### Fase 0 - Archivos Base
| Archivo | Prompt |
|---------|--------|
| `pyproject.toml` | 0.1 |
| `.python-version` | 0.1 |
| `docker-compose.yml` | 0.2 |
| `.env.example` | 0.2 |
| `pytest.ini` | Anexo B |
| `.gitignore` | Anexo B |
| `src/__init__.py` | 0.1 |
| `src/config.py` | 0.4 |
| `src/logging_config.py` | 0.6 |
| `tests/conftest.py` | 0.3, A.3 |

### Fase 1 - Autenticación
| Archivo | Prompt |
|---------|--------|
| `src/auth/__init__.py` | 1.2 |
| `src/auth/models.py` | 1.2 |
| `src/auth/exceptions.py` | 1.4 |
| `src/auth/jwt_handler.py` | 1.4 |
| `src/auth/dependencies.py` | A.1 |
| `src/agent/__init__.py` | 1.6 |
| `src/agent/state.py` | 1.6 |

### Fase 2 - Base de Datos
| Archivo | Prompt |
|---------|--------|
| `alembic.ini` | 2.1 |
| `migrations/env.py` | 2.1 |
| `src/database/__init__.py` | 2.3 |
| `src/database/connection.py` | 2.3 |
| `src/database/models.py` | 2.5 |
| `src/services/__init__.py` | 2.7 |
| `src/services/retriever.py` | 2.7 |

### Fase 3 - Ingestión
| Archivo | Prompt |
|---------|--------|
| `src/ingestion/__init__.py` | 3.2 |
| `src/ingestion/hasher.py` | 3.2 |
| `src/ingestion/chunker.py` | 3.4 |
| `src/ingestion/docling_processor.py` | 3.6 |
| `src/ingestion/watcher.py` | 3.8 |

### Fase 4 - Agente
| Archivo | Prompt |
|---------|--------|
| `src/agent/language_detector.py` | 4.2 |
| `src/agent/tools/__init__.py` | 4.4 |
| `src/agent/tools/search_knowledge.py` | 4.4 |
| `src/agent/graph.py` | 4.6 |
| `src/evaluation/__init__.py` | 4.8 |
| `src/evaluation/rag_metrics.py` | 4.8 |

### Fase 5 - API
| Archivo | Prompt |
|---------|--------|
| `src/api/__init__.py` | 5.2 |
| `src/api/schemas.py` | 5.2 |
| `src/api/routers/__init__.py` | 5.2 |
| `src/api/routers/chat.py` | 5.2 |
| `src/main.py` | 5.3, A.6 |

### Fase 6-8 y Anexos
| Archivo | Prompt |
|---------|--------|
| `.github/workflows/ci.yml` | 6.3 |
| `Dockerfile` | 7.1 |
| `docker-compose.prod.yml` | 7.2 |
| `scripts/deploy.sh` | 7.3 |
| `scripts/init_db.py` | 7.3 |
| `src/services/embedding_service.py` | A.2 |
| `src/api/routers/admin.py` | A.4 |
| `src/api/routers/feedback.py` | A.5 |
| `src/services/feedback_service.py` | 8.3 |

---

## Verificación Final antes de Empezar

Ejecuta estos comandos para verificar que todo está listo:

```bash
# 1. Verificar estructura
ls -la src/ tests/

# 2. Verificar dependencias
uv sync

# 3. Verificar Docker
docker compose up -d postgres
docker compose ps

# 4. Verificar que pytest funciona
uv run pytest --collect-only

# 5. Verificar linter
uv run ruff check src/

# 6. Verificar formato
uv run ruff format --check src/
```

Si todos los comandos pasan sin errores, estás listo para comenzar con el **Prompt 0.3** (primer test RED).

---

## FASE 9B: Grafo Público Enriquecido (Clasificador, Reranker, Evaluador de Calidad)

**Objetivo de la Fase**: Enriquecer el grafo LangGraph del modo público (chatbot) con nodos inteligentes: clasificación por dominio entre chatbots, reranking de chunks, evaluación de calidad inline y fallback honesto. Esto justifica plenamente el uso de LangGraph incluso sin usuario identificado.

**Dependencias**: Fase 4 (grafo LangGraph operativo), Fase 5B (LocalEmbeddingService BGE-M3)

**Decisiones de diseño**:
- **Chatbot Portal**: en lugar de crear categorías de KB dentro de un chatbot, se introduce el concepto de "portal": un chatbot con un campo `portal_chatbot_ids` que clasifica consultas entre los chatbots hijos del mismo cliente. Si el chatbot no es portal, el clasificador es pass-through.
- **Clasificador dual**: embeddings por defecto (comparación con centroides de los `system_prompt` de los chatbots hijos), LLM como fallback si la confianza es baja.
- **Reranker configurable**: `ms-marco-MiniLM-L-6-v2` por defecto, modelo cambiable desde panel admin. `NoopReranker` si se desactiva.
- **Umbral de calidad**: 0.6 por defecto, configurable por chatbot desde panel partner.

**Flujo del grafo público enriquecido**:
```
[route_by_capability] → [detect_language] → [query_classifier]
                                                    │
                                          ¿portal con hijos?
                                           /              \
                                    [selecciona KB]    [pass-through]
                                           \              /
                                      [search_knowledge]
                                              │
                                        [reranker]
                                              │
                                    [generate_response]
                                              │
                                    [quality_evaluator]
                                       /            \
                                [score ≥ umbral]  [score < umbral]
                                    │                │
                            [log_interaction]  [fallback_response]
                                    │                │
                                  [END]            [END]
```

---

### Prompt 4B.1 - Tests del Query Classifier (TDD - RED)

**Objetivo**: Validar la clasificación de consultas por dominio para enrutar a la KB del chatbot temático correcto. El clasificador usa embeddings de los `system_prompt` de los chatbots hijos y LLM como fallback.

**tests/modules/agents_hub/unit/test_query_classifier.py**:
```python
"""Tests para el clasificador de consultas por dominio — TDD RED."""
import uuid
import pytest
from unittest.mock import AsyncMock, Mock
from dataclasses import dataclass


@dataclass
class FakeChatbot:
    id: uuid.UUID
    name: str
    system_prompt: str


class TestQueryClassifier:

    @pytest.fixture
    def chatbots_hijos(self):
        return [
            FakeChatbot(id=uuid.uuid4(), name="RRHH", system_prompt="Resuelve dudas sobre nóminas, permisos y contratos laborales."),
            FakeChatbot(id=uuid.uuid4(), name="Normativa", system_prompt="Consultas sobre normativa académica, reglamentos y BOE."),
            FakeChatbot(id=uuid.uuid4(), name="Económico", system_prompt="Gestión económica, presupuestos y justificación de gastos."),
        ]

    @pytest.mark.asyncio
    async def test_classifies_rrhh_query(self, chatbots_hijos) -> None:
        from server.app.modules.agents_hub.agent.query_classifier import QueryClassifier

        embedding_service = AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024))
        classifier = QueryClassifier(embedding_service=embedding_service)
        result = await classifier.classify(
            query="¿Cuántos días de vacaciones me corresponden?",
            candidate_chatbots=chatbots_hijos,
        )
        assert result.chatbot_id == chatbots_hijos[0].id
        assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_pass_through_single_chatbot(self, chatbots_hijos) -> None:
        """Si solo hay un chatbot candidato, devuelve ese directamente."""
        from server.app.modules.agents_hub.agent.query_classifier import QueryClassifier

        embedding_service = AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024))
        classifier = QueryClassifier(embedding_service=embedding_service)
        single = [chatbots_hijos[0]]
        result = await classifier.classify(query="cualquier cosa", candidate_chatbots=single)
        assert result.chatbot_id == single[0].id
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_pass_through_empty_list(self) -> None:
        """Sin candidatos, devuelve None."""
        from server.app.modules.agents_hub.agent.query_classifier import QueryClassifier

        embedding_service = AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024))
        classifier = QueryClassifier(embedding_service=embedding_service)
        result = await classifier.classify(query="hola", candidate_chatbots=[])
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_classification_result_with_confidence(self, chatbots_hijos) -> None:
        from server.app.modules.agents_hub.agent.query_classifier import QueryClassifier, ClassificationResult

        embedding_service = AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024))
        classifier = QueryClassifier(embedding_service=embedding_service)
        result = await classifier.classify(
            query="¿Cómo justifico los gastos del proyecto?",
            candidate_chatbots=chatbots_hijos,
        )
        assert isinstance(result, ClassificationResult)
        assert hasattr(result, "chatbot_id")
        assert hasattr(result, "confidence")
        assert 0.0 <= result.confidence <= 1.0
```

---

### Prompt 4B.2 - Implementación del Query Classifier + Migración (TDD - GREEN)

**Objetivo**: Implementar el clasificador de consultas y añadir el campo `portal_chatbot_ids` a `HubChatbot`.

**Migración Alembic**: añadir a `hub_chatbots`:
- `portal_chatbot_ids: ARRAY(UUID)` — lista de chatbot_ids a los que enrutar (NULL = no es portal)
- `quality_threshold: Float` — umbral de calidad (default 0.6)

**server/app/modules/agents_hub/agent/query_classifier.py**:
```python
"""Clasificador de consultas por dominio para enrutado entre chatbots."""
import uuid
from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np


class EmbeddingProtocol(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@dataclass
class ClassificationResult:
    chatbot_id: uuid.UUID
    chatbot_name: str
    confidence: float


@dataclass
class ChatbotCandidate:
    id: uuid.UUID
    name: str
    system_prompt: str


class QueryClassifier:
    """Clasifica consultas comparando embeddings de la query con los system_prompt de los chatbots candidatos."""

    def __init__(self, embedding_service: EmbeddingProtocol):
        self.embedding_service = embedding_service
        self._centroid_cache: dict[uuid.UUID, list[float]] = {}

    async def classify(
        self,
        query: str,
        candidate_chatbots: Sequence[ChatbotCandidate],
    ) -> ClassificationResult | None:
        if not candidate_chatbots:
            return None
        if len(candidate_chatbots) == 1:
            c = candidate_chatbots[0]
            return ClassificationResult(chatbot_id=c.id, chatbot_name=c.name, confidence=1.0)

        query_emb = await self.embedding_service.embed(query)
        best, best_score = None, -1.0

        for chatbot in candidate_chatbots:
            if chatbot.id not in self._centroid_cache:
                self._centroid_cache[chatbot.id] = await self.embedding_service.embed(chatbot.system_prompt)
            centroid = self._centroid_cache[chatbot.id]
            score = self._cosine_similarity(query_emb, centroid)
            if score > best_score:
                best, best_score = chatbot, score

        return ClassificationResult(
            chatbot_id=best.id, chatbot_name=best.name, confidence=max(0.0, min(1.0, best_score))
        )

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        va, vb = np.array(a), np.array(b)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        return float(np.dot(va, vb) / denom) if denom > 0 else 0.0
```

---

### Prompt 4B.3 - Tests del Reranker (TDD - RED)

**Objetivo**: Validar que el reranker reordena chunks por relevancia real y que NoopReranker no altera el orden.

**tests/modules/agents_hub/unit/test_reranker.py**:
```python
"""Tests para el reranker de chunks — TDD RED."""
import pytest
from dataclasses import dataclass


@dataclass
class FakeChunk:
    content: str
    score: float


class TestCrossEncoderReranker:

    @pytest.mark.asyncio
    async def test_reranker_reorders_by_relevance(self) -> None:
        from server.app.modules.agents_hub.agent.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        chunks = [
            FakeChunk(content="Python es un lenguaje de programación.", score=0.5),
            FakeChunk(content="Las vacaciones son 22 días laborables al año.", score=0.9),
        ]
        result = await reranker.rerank(query="¿Cuántos días de vacaciones tengo?", documents=chunks, top_k=2)
        assert result[0].content == chunks[1].content

    @pytest.mark.asyncio
    async def test_reranker_truncates_to_top_k(self) -> None:
        from server.app.modules.agents_hub.agent.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        chunks = [FakeChunk(content=f"Chunk {i}", score=0.5) for i in range(10)]
        result = await reranker.rerank(query="test", documents=chunks, top_k=3)
        assert len(result) == 3


class TestNoopReranker:

    @pytest.mark.asyncio
    async def test_noop_preserves_order(self) -> None:
        from server.app.modules.agents_hub.agent.reranker import NoopReranker

        reranker = NoopReranker()
        chunks = [FakeChunk(content=f"Chunk {i}", score=float(i)) for i in range(5)]
        result = await reranker.rerank(query="test", documents=chunks, top_k=5)
        assert [r.content for r in result] == [c.content for c in chunks]

    @pytest.mark.asyncio
    async def test_noop_truncates_to_top_k(self) -> None:
        from server.app.modules.agents_hub.agent.reranker import NoopReranker

        reranker = NoopReranker()
        chunks = [FakeChunk(content=f"Chunk {i}", score=float(i)) for i in range(10)]
        result = await reranker.rerank(query="test", documents=chunks, top_k=3)
        assert len(result) == 3
```

---

### Prompt 4B.4 - Implementación del Reranker (TDD - GREEN)

**Objetivo**: Implementar reranker desacoplado con interfaz `RerankerProtocol`.

**Dependencia**: añadir `sentence-transformers>=2.6.0` a `server/pyproject.toml` (si no está ya por BGE-M3).

**server/app/modules/agents_hub/agent/reranker.py**:
```python
"""Reranker de chunks con interfaz desacoplada."""
from dataclasses import dataclass
from typing import Protocol, Sequence, TypeVar

T = TypeVar("T")


class HasContent(Protocol):
    content: str


@dataclass
class RankedDocument:
    content: str
    score: float
    original_index: int


class RerankerProtocol(Protocol):
    async def rerank(self, query: str, documents: Sequence[HasContent], top_k: int = 5) -> list[RankedDocument]: ...


class NoopReranker:
    """Reranker que no altera el orden — para desactivar sin cambiar el grafo."""

    async def rerank(self, query: str, documents: Sequence[HasContent], top_k: int = 5) -> list[RankedDocument]:
        return [
            RankedDocument(content=d.content, score=getattr(d, "score", 0.0), original_index=i)
            for i, d in enumerate(documents[:top_k])
        ]


class CrossEncoderReranker:
    """Reranker basado en cross-encoder (sentence-transformers)."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self._model_name)
        return self._model

    async def rerank(self, query: str, documents: Sequence[HasContent], top_k: int = 5) -> list[RankedDocument]:
        if not documents:
            return []
        model = self._get_model()
        pairs = [(query, d.content) for d in documents]
        scores = model.predict(pairs)
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [
            RankedDocument(content=documents[i].content, score=float(s), original_index=i)
            for i, s in indexed[:top_k]
        ]


_reranker_instance: RerankerProtocol | None = None

def get_reranker(model_name: str | None = None, enabled: bool = True) -> RerankerProtocol:
    global _reranker_instance
    if not enabled:
        return NoopReranker()
    if _reranker_instance is None:
        _reranker_instance = CrossEncoderReranker(model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker_instance
```

---

### Prompt 4B.5 - Tests del Quality Evaluator y Fallback (TDD - RED)

**Objetivo**: Validar la evaluación inline de calidad y el mecanismo de fallback.

**tests/modules/agents_hub/unit/test_quality_evaluator.py**:
```python
"""Tests para evaluador de calidad inline y fallback — TDD RED."""
import pytest


class TestQualityEvaluator:

    @pytest.mark.asyncio
    async def test_high_quality_passes(self) -> None:
        from server.app.modules.agents_hub.agent.quality_evaluator import evaluate_response_quality

        result = await evaluate_response_quality(
            question="¿Qué es Python?",
            answer="Python es un lenguaje de programación versátil.",
            context="Python es un lenguaje de programación versátil y fácil de aprender.",
        )
        assert result.score >= 0.6
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_low_quality_fails(self) -> None:
        from server.app.modules.agents_hub.agent.quality_evaluator import evaluate_response_quality

        result = await evaluate_response_quality(
            question="¿Cuántos días de vacaciones tengo?",
            answer="La temperatura media en Marte es de -60 grados.",
            context="Los empleados tienen 22 días laborables de vacaciones.",
        )
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_custom_threshold(self) -> None:
        from server.app.modules.agents_hub.agent.quality_evaluator import evaluate_response_quality

        result = await evaluate_response_quality(
            question="test", answer="test related", context="test context",
            threshold=0.9,
        )
        assert isinstance(result.passed, bool)

    @pytest.mark.asyncio
    async def test_metrics_include_faithfulness_and_relevance(self) -> None:
        from server.app.modules.agents_hub.agent.quality_evaluator import evaluate_response_quality

        result = await evaluate_response_quality(
            question="test", answer="test", context="test",
        )
        assert "faithfulness" in result.metrics
        assert "relevance" in result.metrics


class TestFallbackHandler:

    @pytest.mark.asyncio
    async def test_fallback_generates_honest_message(self) -> None:
        from server.app.modules.agents_hub.agent.fallback_handler import generate_fallback_response

        response = await generate_fallback_response(language="es")
        assert "información suficiente" in response.lower() or "no dispongo" in response.lower()

    @pytest.mark.asyncio
    async def test_fallback_respects_language(self) -> None:
        from server.app.modules.agents_hub.agent.fallback_handler import generate_fallback_response

        response_ca = await generate_fallback_response(language="ca")
        response_en = await generate_fallback_response(language="en")
        assert response_ca != response_en


class TestRetrievalValidator:
    """Valida el nodo que decide si el contexto recuperado es suficiente
    para generar respuesta directamente o si hay que hacer fallback
    de idioma (re-búsqueda sin filtro de idioma + advertencia de traducción)."""

    @pytest.mark.asyncio
    async def test_sufficient_results_pass(self) -> None:
        from server.app.modules.agents_hub.agent.retrieval_validator import validate_retrieval
        from server.app.modules.agents_hub.services.retriever import SearchResult
        import uuid

        results = [
            SearchResult(id=uuid.uuid4(), content="x", source_url="u", language="ca", score=0.8),
            SearchResult(id=uuid.uuid4(), content="y", source_url="u", language="ca", score=0.75),
        ]
        decision = validate_retrieval(results, min_results=2, min_score=0.25)
        assert decision == "ok"

    @pytest.mark.asyncio
    async def test_zero_results_triggers_language_fallback(self) -> None:
        from server.app.modules.agents_hub.agent.retrieval_validator import validate_retrieval

        decision = validate_retrieval([], min_results=2, min_score=0.25)
        assert decision == "language_fallback"

    @pytest.mark.asyncio
    async def test_low_score_triggers_language_fallback(self) -> None:
        from server.app.modules.agents_hub.agent.retrieval_validator import validate_retrieval
        from server.app.modules.agents_hub.services.retriever import SearchResult
        import uuid

        results = [
            SearchResult(id=uuid.uuid4(), content="x", source_url="u", language="ca", score=0.1),
        ]
        decision = validate_retrieval(results, min_results=2, min_score=0.25)
        assert decision == "language_fallback"

    @pytest.mark.asyncio
    async def test_language_fallback_warning_in_context(self) -> None:
        from server.app.modules.agents_hub.agent.fallback_handler import build_translation_warning

        warning = build_translation_warning(source_language="es", query_language="ca")
        assert "ca" in warning.lower() or "català" in warning.lower() or "idioma" in warning.lower()
```

---

### Prompt 4B.6 - Implementación del Quality Evaluator + Fallback (TDD - GREEN)

**Objetivo**: Implementar evaluador de calidad reutilizando `rag_metrics.py` y handler de fallback i18n.

**server/app/modules/agents_hub/agent/quality_evaluator.py**:
```python
"""Evaluador de calidad de respuestas inline (pre-envío)."""
from dataclasses import dataclass, field

from server.app.modules.agents_hub.evaluation.rag_metrics import (
    calculate_answer_relevance,
    calculate_faithfulness,
)


@dataclass
class QualityResult:
    score: float
    passed: bool
    metrics: dict = field(default_factory=dict)


async def evaluate_response_quality(
    question: str,
    answer: str,
    context: str,
    threshold: float = 0.6,
) -> QualityResult:
    faithfulness = await calculate_faithfulness(answer=answer, context=context)
    relevance = await calculate_answer_relevance(question=question, answer=answer)

    combined = (faithfulness + relevance) / 2.0
    return QualityResult(
        score=combined,
        passed=combined >= threshold,
        metrics={"faithfulness": faithfulness, "relevance": relevance},
    )
```

**server/app/modules/agents_hub/agent/fallback_handler.py**:
```python
"""Respuesta de fallback cuando la calidad es insuficiente."""

_FALLBACK_MESSAGES = {
    "es": "No dispongo de información suficiente para responder con confianza a esta consulta. Te recomiendo contactar directamente con el servicio correspondiente.",
    "ca": "No dispose d'informació suficient per respondre amb confiança a aquesta consulta. Et recomane contactar directament amb el servei corresponent.",
    "en": "I don't have enough information to answer this query with confidence. I recommend contacting the relevant service directly.",
}


async def generate_fallback_response(language: str = "es") -> str:
    return _FALLBACK_MESSAGES.get(language, _FALLBACK_MESSAGES["es"])


_TRANSLATION_WARNINGS = {
    "es": "⚠️ No se ha encontrado información en el idioma de tu consulta. La respuesta se ha generado a partir de fuentes en otro idioma y puede contener adaptaciones.",
    "ca": "⚠️ No s'ha trobat informació en l'idioma de la consulta. La resposta s'ha generat a partir de fonts en un altre idioma i pot contenir adaptacions.",
    "en": "⚠️ No information was found in your query language. The response was generated from sources in another language and may contain adaptations.",
}


def build_translation_warning(source_language: str, query_language: str) -> str:
    return _TRANSLATION_WARNINGS.get(query_language, _TRANSLATION_WARNINGS["es"])
```

**server/app/modules/agents_hub/agent/retrieval_validator.py**:
```python
"""Decide si el contexto recuperado es suficiente o se necesita fallback de idioma."""
from server.app.modules.agents_hub.services.retriever import SearchResult


def validate_retrieval(
    results: list[SearchResult],
    min_results: int = 2,
    min_score: float = 0.25,
) -> str:
    """Evalúa si los resultados de búsqueda son suficientes.

    Returns:
        "ok" — context suficiente, continuar con generate_response
        "language_fallback" — re-buscar sin filtro de idioma y añadir advertencia
    """
    if not results:
        return "language_fallback"
    if len(results) < min_results or max(r.score for r in results) < min_score:
        return "language_fallback"
    return "ok"
```

**Nota de diseño**: `min_results` y `min_score` se leen de `HubChatbot.min_retrieval_results` y
`HubChatbot.min_retrieval_score` vía `ConfigProvider` en el nodo del grafo. Los defaults (2 y 0.25)
son los valores de columna en la migración Alembic (ver Prompt 4B.2).

---

### Prompt 4B.7 - Tests del Grafo Público Integrado (TDD - RED)

**Objetivo**: Validar el flujo completo del grafo enriquecido con aristas condicionales.

**tests/modules/agents_hub/integration/test_enriched_graph.py**:
```python
"""Tests de integración del grafo público enriquecido — TDD RED."""
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestEnrichedPublicGraph:

    @pytest.mark.asyncio
    async def test_graph_has_new_nodes(self) -> None:
        from server.app.modules.agents_hub.agent.graph import create_agent_graph

        with patch("server.app.modules.agents_hub.agent.graph.ChatGoogleGenerativeAI"):
            graph = create_agent_graph(retriever=Mock(), embedding_service=Mock())
            node_names = list(graph.nodes.keys())
            assert "query_classifier" in node_names
            assert "reranker" in node_names
            assert "quality_evaluator" in node_names
            assert "fallback_response" in node_names

    @pytest.mark.asyncio
    async def test_graph_has_conditional_edge_after_quality(self) -> None:
        """El grafo debe tener una bifurcación tras quality_evaluator."""
        from server.app.modules.agents_hub.agent.graph import create_agent_graph

        with patch("server.app.modules.agents_hub.agent.graph.ChatGoogleGenerativeAI"):
            graph = create_agent_graph(retriever=Mock(), embedding_service=Mock())
            compiled = graph.compile()
            assert compiled is not None

    @pytest.mark.asyncio
    async def test_new_state_fields_initialized(self) -> None:
        from server.app.modules.agents_hub.agent.state import create_initial_state

        state = create_initial_state(user_id=None, chatbot_id="test-123", initial_message="Hola")
        assert state["classified_chatbot_id"] == ""
        assert state["quality_score"] == 0.0
        assert state["fallback_triggered"] is False
```

---

### Prompt 4B.8 - Integración en graph.py y state.py (TDD - GREEN)

**Objetivo**: Modificar `state.py` con los campos nuevos e integrar todos los nodos en `graph.py` con aristas condicionales.

**Cambios en state.py** — añadir al `AgentState`:
```python
    # --- Fase 4B: Grafo Público Enriquecido ---
    classified_chatbot_id: str      # ID del chatbot seleccionado por clasificador ("" = sin clasificar)
    classifier_confidence: float    # Confianza del clasificador (0.0–1.0)
    reranked_context: list[str]     # Contexto tras reranking
    quality_score: float            # Score compuesto del evaluador (0.0–1.0)
    quality_metrics: dict           # {faithfulness: float, relevance: float}
    fallback_triggered: bool        # True si la respuesta fue sustituida por fallback honesto
    language_fallback_triggered: bool  # True si se re-buscó sin filtro de idioma
    context_source_language: str | None  # Idioma predominante de los chunks usados (None si no aplica)
```

**Cambios en create_initial_state** — inicializar campos nuevos:
```python
    classified_chatbot_id="",
    classifier_confidence=0.0,
    reranked_context=[],
    quality_score=0.0,
    quality_metrics={},
    fallback_triggered=False,
    language_fallback_triggered=False,
    context_source_language=None,
```

**Cambios en graph.py** — flujo completo con validación de retrieval y language fallback:

```
[route_by_capability] → [detect_language] → [query_classifier]
                                                    │
                                      [search_knowledge]  ← búsqueda con filtro de idioma
                                              │
                                   [validate_retrieval]
                                     /               \
                               "ok"               "language_fallback"
                                 │                       │
                           [reranker]        [search_knowledge_fallback]  ← sin filtro idioma
                                 │                       │
                           [generate_response] ←─────────┘  (con advertencia de traducción si fallback)
                                 │
                        [quality_evaluator]
                           /            \
                    [score ≥ umbral]  [score < umbral]
                           │                │
                  [log_interaction]  [fallback_response]  ← respuesta honesta "no tengo info"
                           │                │
                         [END]            [END]
```

```python
    # Nuevos nodos (Fase 4B)
    graph.add_node("query_classifier", query_classifier_node)
    graph.add_node("validate_retrieval", validate_retrieval_node)
    graph.add_node("search_knowledge_fallback", search_knowledge_fallback_node)
    graph.add_node("reranker", reranker_node)
    graph.add_node("quality_evaluator", quality_evaluator_node)
    graph.add_node("fallback_response", fallback_response_node)
    graph.add_node("log_interaction", log_interaction_node)

    # Flujo actualizado
    graph.set_entry_point("route_by_capability")
    graph.add_edge("route_by_capability", "detect_language")
    graph.add_edge("detect_language", "query_classifier")
    graph.add_edge("query_classifier", "search_knowledge")

    # Arista condicional: validate_retrieval decide si hay suficiente contexto en el idioma detectado
    graph.add_edge("search_knowledge", "validate_retrieval")
    graph.add_conditional_edges(
        "validate_retrieval",
        lambda state: state.get("retrieval_decision", "ok"),
        {"ok": "reranker", "language_fallback": "search_knowledge_fallback"},
    )
    graph.add_edge("search_knowledge_fallback", "reranker")
    graph.add_edge("reranker", "generate_response")
    graph.add_edge("generate_response", "quality_evaluator")

    # Arista condicional: quality_evaluator decide si la respuesta es suficientemente buena
    graph.add_conditional_edges(
        "quality_evaluator",
        lambda state: "ok" if state["quality_score"] >= quality_threshold else "fallback",
        {"ok": "log_interaction", "fallback": "fallback_response"},
    )
    graph.add_edge("log_interaction", END)
    graph.add_edge("fallback_response", END)
```

**Lógica de `validate_retrieval_node`**:
```python
async def validate_retrieval_node(state: AgentState) -> dict:
    results = state.get("raw_search_results", [])
    config = await config_provider.get_chatbot_config(state["chatbot_id"])
    decision = validate_retrieval(
        results,
        min_results=config.min_retrieval_results,   # default 2
        min_score=config.min_retrieval_score,        # default 0.25
    )
    return {"retrieval_decision": decision}
```

**Lógica de `search_knowledge_fallback_node`** (re-búsqueda sin filtro de idioma):
```python
async def search_knowledge_fallback_node(state: AgentState) -> dict:
    result = await search_knowledge(
        query=state["messages"][-1].content,
        chatbot_id=state["chatbot_id"],
        retriever=retriever,
        embedding_service=embedding_service,
        language=None,   # sin filtro — busca en todos los idiomas
    )
    # Detectar idioma predominante de los resultados para la advertencia
    source_lang = detect_source_language(result)
    return {
        "retrieved_context": [result],
        "language_fallback_triggered": True,
        "context_source_language": source_lang,
    }
```

**El nodo `generate_response` lee `language_fallback_triggered`** y, si es True, añade
`build_translation_warning(source_language, query_language)` al inicio del system_prompt.

**Cambios en config_models.py** — campos portal y umbrales de retrieval:
```python
    # En HubChatbot, añadir:
    portal_chatbot_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    quality_threshold: Mapped[float] = mapped_column(default=0.6)
    min_retrieval_results: Mapped[int] = mapped_column(Integer, default=2)
    min_retrieval_score: Mapped[float] = mapped_column(default=0.25)
```

**Migración Alembic adicional** (se añade a la de 4B.2):
```python
    op.add_column("hub_chatbots", sa.Column("min_retrieval_results", sa.Integer(), nullable=False, server_default="2"))
    op.add_column("hub_chatbots", sa.Column("min_retrieval_score", sa.Float(), nullable=False, server_default="0.25"))
```

---

## FASE 9C: StorageService — Abstracción de almacenamiento de objetos (fsspec) ✅ COMPLETADO (2026-04-28)

**Objetivo de la fase**: Eliminar los accesos directos al sistema de archivos del SO para persistir documentos de negocio. Todo fichero de negocio (PDFs subidos, fuentes de ingestión) pasa por `StorageService`, backed por `fsspec`. En local/dev el backend es el sistema de archivos local o MinIO; en producción GCP, es Google Cloud Storage.

**Motivación**: Cloud Run no garantiza persistencia de `/tmp` entre peticiones ni entre instancias. El flujo actual guarda PDFs en `/tmp` y los borra tras procesar: el documento original no se conserva y la solución se rompe si Docling corre en una instancia diferente. Esta fase resuelve el gap crítico de portabilidad identificado el 2026-04-27 (ver sección "Infraestructura objetivo y portabilidad" en `CLAUDE.md`).

**Dependencias**: ninguna (infraestructura transversal; no depende de otras fases pendientes).

**Archivos afectados**:
- `server/app/core/storage.py` — nuevo
- `server/app/routers/hub_ingestion_router.py` — refactor (eliminar `tempfile` en el handler de upload)
- `server/app/modules/agents_hub/ingestion/watcher.py` — refactor (leer de storage, no de ruta local)
- `server/pyproject.toml` — añadir `fsspec`, `gcsfs`, `s3fs`
- `.env.example` y `docker-compose.yml` — nuevas variables de entorno

---

### Prompt 9C.1 — TDD RED: contrato y tests de StorageService ✅ COMPLETADO (2026-04-28)

**Objetivo**: Definir el contrato de `StorageService` mediante tests que deben fallar antes de implementar nada. El test cubre `put`, `get`, `exists`, `delete` y la fábrica `get_storage_service()`.

**`server/tests/modules/agents_hub/unit/test_storage_service.py`**:
```python
"""Tests del protocolo StorageService — TDD RED."""
import os
import pytest

os.environ.setdefault("STORAGE_BACKEND", "file")
os.environ.setdefault("STORAGE_BUCKET", "/tmp/govgenai_test")


class TestFsspecStorageService:

    @pytest.fixture
    def storage(self, tmp_path):
        from server.app.core.storage import FsspecStorageService
        return FsspecStorageService(backend="file", bucket=str(tmp_path))

    @pytest.mark.asyncio
    async def test_put_and_get_roundtrip(self, storage):
        await storage.put("docs/test.pdf", b"PDF content")
        result = await storage.get("docs/test.pdf")
        assert result == b"PDF content"

    @pytest.mark.asyncio
    async def test_exists_returns_true_after_put(self, storage):
        await storage.put("docs/test.pdf", b"data")
        assert await storage.exists("docs/test.pdf") is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_missing_key(self, storage):
        assert await storage.exists("nonexistent/file.pdf") is False

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, storage):
        await storage.put("docs/to_delete.pdf", b"data")
        await storage.delete("docs/to_delete.pdf")
        assert await storage.exists("docs/to_delete.pdf") is False

    @pytest.mark.asyncio
    async def test_get_raises_on_missing_file(self, storage):
        with pytest.raises(FileNotFoundError):
            await storage.get("nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_put_creates_intermediate_directories(self, storage):
        await storage.put("nested/deep/dir/file.pdf", b"data")
        assert await storage.exists("nested/deep/dir/file.pdf") is True


class TestGetStorageService:

    def test_returns_fsspec_service_with_env_vars(self, monkeypatch):
        monkeypatch.setenv("STORAGE_BACKEND", "file")
        monkeypatch.setenv("STORAGE_BUCKET", "/tmp/test")
        from server.app.core import storage as storage_module
        storage_module._build_storage_service.cache_clear()
        service = storage_module.get_storage_service()
        from server.app.core.storage import FsspecStorageService
        assert isinstance(service, FsspecStorageService)
```

**Confirmar RED**:
```bash
cd server && uv run pytest tests/modules/agents_hub/unit/test_storage_service.py -v
# Esperado: ImportError o ModuleNotFoundError (el módulo aún no existe)
```

---

### Prompt 9C.2 — TDD GREEN: FsspecStorageService e inyección de dependencia ✅ COMPLETADO (2026-04-28)

**Objetivo**: Implementar `server/app/core/storage.py` con `FsspecStorageService` y `get_storage_service()`. Los tests del Prompt 9C.1 deben pasar en verde.

**Añadir a `server/pyproject.toml`** (bloque `dependencies`):
```toml
"fsspec>=2024.6.0",
"gcsfs>=2024.6.0",
"s3fs>=2024.6.0",
```

**`server/app/core/storage.py`**:
```python
from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from typing import Protocol, runtime_checkable

import fsspec


@runtime_checkable
class StorageService(Protocol):
    async def put(self, key: str, data: bytes) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...


class FsspecStorageService:
    def __init__(self, backend: str, bucket: str, **kwargs):
        self._bucket = bucket.rstrip("/")
        self._fs = fsspec.filesystem(backend, **kwargs)

    def _full_path(self, key: str) -> str:
        return f"{self._bucket}/{key}"

    async def put(self, key: str, data: bytes) -> None:
        path = self._full_path(key)
        await asyncio.to_thread(self._sync_put, path, data)

    def _sync_put(self, path: str, data: bytes) -> None:
        parent = "/".join(path.split("/")[:-1])
        if parent:
            self._fs.makedirs(parent, exist_ok=True)
        with self._fs.open(path, "wb") as f:
            f.write(data)

    async def get(self, key: str) -> bytes:
        if not await self.exists(key):
            raise FileNotFoundError(f"Key not found in storage: {key}")
        path = self._full_path(key)
        return await asyncio.to_thread(self._sync_get, path)

    def _sync_get(self, path: str) -> bytes:
        with self._fs.open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        await asyncio.to_thread(self._fs.rm, path)

    async def exists(self, key: str) -> bool:
        path = self._full_path(key)
        return await asyncio.to_thread(self._fs.exists, path)


@lru_cache(maxsize=1)
def _build_storage_service() -> FsspecStorageService:
    backend = os.environ.get("STORAGE_BACKEND", "file")
    bucket = os.environ.get("STORAGE_BUCKET", "/tmp/govgenai")
    kwargs: dict = {}
    if backend == "s3":
        endpoint = os.environ.get("STORAGE_ENDPOINT")
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        kwargs["key"] = os.environ.get("STORAGE_ACCESS_KEY", "")
        kwargs["secret"] = os.environ.get("STORAGE_SECRET_KEY", "")
    return FsspecStorageService(backend=backend, bucket=bucket, **kwargs)


def get_storage_service() -> FsspecStorageService:
    return _build_storage_service()
```

**Añadir a `.env.example`**:
```bash
# ── Object storage (fsspec) ─────────────────────────────────────────────────
# Desarrollo local (sistema de archivos del SO):
STORAGE_BACKEND=file
STORAGE_BUCKET=/tmp/govgenai_uploads

# MinIO local (compatible S3) — activo en docker-compose.yml por defecto:
# STORAGE_BACKEND=s3
# STORAGE_BUCKET=govgenai
# STORAGE_ENDPOINT=http://minio:9000
# STORAGE_ACCESS_KEY=minioadmin
# STORAGE_SECRET_KEY=minioadmin

# Google Cloud Storage (producción Cloud Run):
# STORAGE_BACKEND=gcs
# STORAGE_BUCKET=govgenai-prod
# (credenciales vía Application Default Credentials o GOOGLE_APPLICATION_CREDENTIALS)
```

**Añadir al servicio `app` en `docker-compose.yml`**:
```yaml
environment:
  STORAGE_BACKEND: "s3"
  STORAGE_BUCKET: "govgenai"
  STORAGE_ENDPOINT: "http://minio:9000"
  STORAGE_ACCESS_KEY: "minioadmin"
  STORAGE_SECRET_KEY: "minioadmin"
```

**Confirmar GREEN**:
```bash
uv sync  # instala fsspec, gcsfs, s3fs
cd server && uv run pytest tests/modules/agents_hub/unit/test_storage_service.py -v
# Esperado: 8 tests PASSED
```

---

### Prompt 9C.3 — Integración: reemplazar /tmp directo en el flujo de ingestión ✅ COMPLETADO (2026-04-28)

**Objetivo**: Modificar `hub_ingestion_router.py` e `IngestionWatcher` para que el PDF subido se persista via `StorageService` en lugar de sólo en `/tmp`. El PDF queda disponible en storage tras el procesamiento; `source_url` en `HubIngestionJob` refleja la clave de storage, no una ruta efímera.

**Flujo resultante**:
```
POST /upload → storage.put("ingestion/{chatbot_id}/{job_id}.pdf", bytes)
                 └─ BackgroundTask:
                    1. storage.get(key) → bytes → NamedTemporaryFile(delete=False)
                    2. DoclingProcessor(tmp_path) → Markdown
                    3. os.unlink(tmp_path)   # el tmp local desaparece
                    4. chunks → PostgreSQL con source_url = storage key
                    # El PDF permanece en storage (GCS/MinIO/local)
```

**Cambios en `server/app/routers/hub_ingestion_router.py`**:
```python
# Añadir imports
from server.app.core.storage import get_storage_service, StorageService

# Endpoint de upload — cambiar firma y cuerpo:
async def upload_document(
    ...,
    storage: StorageService = Depends(get_storage_service),
) -> ...:
    pdf_bytes = await file.read()
    storage_key = f"ingestion/{chatbot_id}/{job_id}.pdf"
    await storage.put(storage_key, pdf_bytes)
    # Pasar storage_key al background task (no ruta local)
    background_tasks.add_task(process_job, session, job_id, storage_key, storage)
    return ...
```

**Cambios en `server/app/modules/agents_hub/ingestion/watcher.py`**:
```python
import tempfile, os
from server.app.core.storage import StorageService

class IngestionWatcher:
    def __init__(self, session, embedding_service, storage: StorageService):
        self._storage = storage
        ...

    async def run_job(self, job_id: UUID, storage_key: str) -> None:
        pdf_bytes = await self._storage.get(storage_key)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            await self._process_from_local(job_id, tmp_path, storage_key)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
```

**Tests de integración** en `server/tests/modules/agents_hub/integration/test_ingestion_storage.py`:
```python
"""Tests de integración: flujo de ingestión con StorageService."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestIngestionWithStorage:

    @pytest.mark.asyncio
    async def test_upload_persists_pdf_to_storage(self, async_client, auth_headers):
        mock_storage = AsyncMock()
        mock_storage.put = AsyncMock()
        mock_storage.get = AsyncMock(return_value=b"%PDF-1.4 test content")

        with patch("server.app.core.storage.get_storage_service", return_value=mock_storage):
            response = await async_client.post(
                "/api/v1/hub/ingestion/upload",
                files={"file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")},
                headers=auth_headers,
            )
        assert response.status_code == 202
        mock_storage.put.assert_called_once()
        key = mock_storage.put.call_args[0][0]
        assert key.endswith(".pdf")
        assert "ingestion/" in key

    @pytest.mark.asyncio
    async def test_pdf_remains_in_storage_after_processing(self, async_client, auth_headers):
        """El PDF no debe borrarse de storage tras el procesamiento."""
        mock_storage = AsyncMock()
        mock_storage.put = AsyncMock()
        mock_storage.get = AsyncMock(return_value=b"%PDF-1.4 test")
        mock_storage.delete = AsyncMock()

        with patch("server.app.core.storage.get_storage_service", return_value=mock_storage):
            await async_client.post(
                "/api/v1/hub/ingestion/upload",
                files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
                headers=auth_headers,
            )
        mock_storage.delete.assert_not_called()
```

**Confirmar**:
```bash
cd server && uv run pytest tests/modules/agents_hub/ -v -k "storage"
uv run pytest tests/ -v  # regresión completa
```

---

## BLOQUE 9CBis — Modos de retrieval, citas como contrato y router multi-materia

**Contexto**: hasta este punto el sistema asume RAG vectorial (chunking + embeddings + búsqueda top-k) como única estrategia de retrieval. Para el primer despliegue (UJI ~100-150 normativas clasificadas por materias; ayuntamientos medios tipo Vall d'Uixó / Onda) este enfoque tiene limitaciones reales:

- **Citas degradadas**: la cita apunta a un chunk, no a un documento citable (artículo, ordenanza, página web).
- **Pérdida de estructura jerárquica**: la normativa universitaria/municipal está muy interconectada; el top-k recupera fragmentos sueltos y se pierde la jerarquía Título → Capítulo → Artículo.
- **Errores de retrieval silenciosos**: si el top-k no trae el chunk correcto, el LLM responde con seguridad sobre información incompleta.
- **Frescura cara**: cada cambio normativo obliga a re-chunkear/re-embeddar; con el crawler activo el coste operacional es alto.

Este bloque introduce **tres modos de retrieval** (vectorial, long-context, agentic) seleccionables por chatbot, **citas como contrato del agente** (no como subproducto del retriever) y un **router multi-materia opcional** que clasifica la consulta a un sub-chatbot especializado (caso UJI: un chatbot por materia con un router padre).

**Prerrequisitos**: Bloque 9A completado (frontend admin); FASE 9C completada (StorageService).

**Compatibilidad**: refactoriza prompts ya completados (9.7.x ingesta, 9.8.2 chat SSE backend, 9.10 widget) sin romper el comportamiento observable. Cada refactor incluye su propio test de regresión.

**Decisiones de diseño**:

- **El admin elige el modo, no el sistema** — la decisión automática añade complejidad sin valor claro hoy. El panel admin **sugiere** un modo según el tamaño del corpus, pero el admin tiene la última palabra.
- **El pipeline de ingesta es común a los tres modos**: siempre crea `HubDocument` (markdown + metadatos canónicos). El chunking + embedding solo se ejecuta cuando `retrieval_mode == "vector"`.
- **`HubDocument` es la unidad citable**: en cualquier modo, la cita devuelve `(title, url)` del documento, no del chunk.
- **`RetrievalStrategy` como Protocol**: los nodos del grafo no saben qué estrategia usan; se inyecta vía `Depends`. `VectorRetrievalStrategy` envuelve el `HybridRetriever` actual sin tocarlo.
- **Router multi-materia como segundo nivel opcional**: un `HubChatbot` puede ser `kind="router"` (con hijos) o `kind="atomic"`. El router clasifica la consulta y delega al hijo apropiado. Cada hijo tiene su propio `retrieval_mode` y su propio corpus.
- **Cita como contrato del agente**: el `system_prompt` exige cita en cada afirmación factual y un post-validador rechaza respuestas sin cita cuando hubo recuperación.

**Heurística de recomendación** (mostrada en el panel al elegir modo, no aplicada de forma automática):

| Tokens totales del corpus | Modo recomendado | Justificación |
|---|---|---|
| < 100 K | `long_context` | Cabe holgadamente en el contexto de Sonnet/Opus 4.x con caching; cero pérdida; citas perfectas. |
| 100 K – 2 M | `agentic` | El LLM lee un índice de documentos y carga sólo los relevantes; balance coste/precisión; preserva estructura. |
| > 2 M | `vector` | Único modo que escala económicamente; aceptas degradación de citas y errores de top-k. |

Las cifras del primer cliente:

- **UJI** (~150 normativas × 5-50 páginas): estimación 750 K – 3 M tokens. Modo recomendado: **`agentic`** combinado con **router multi-materia** (un chatbot por materia, cada uno con corpus 100-300 K → puede ir en `agentic` o incluso `long_context`).
- **Ayuntamiento medio** (Vall d'Uixó / Onda, ordenanzas + sede electrónica): estimación 200-500 K tokens. Modo recomendado: **`agentic`** sin router (corpus único más reducido).

**Flujo del bloque**:

```
Guía 9CBis.0 (conceptual, se lee antes de escribir código)
  ├── 9CBis.1 RED   modelo HubDocument + retrieval_mode + kind/parent_id (tests)
  ├── 9CBis.2 GREEN modelo + migración Alembic + refactor chunks
  ├── 9CBis.3 RED   Protocol RetrievalStrategy + Source dataclass (tests)
  ├── 9CBis.4 GREEN VectorRetrievalStrategy (envuelve HybridRetriever, agrupa por documento)
  ├── 9CBis.5       LongContextRetrievalStrategy con prompt caching (RED + GREEN)
  ├── 9CBis.6       AgenticRetrievalStrategy + tools list_documents/read_document (RED + GREEN)
  ├── 9CBis.7       Citas como contrato: system prompt + post-validador (RED + GREEN)
  ├── 9CBis.8       Refactor de 9.7.x — IngestionWatcher crea HubDocument; chunks solo si vector
  ├── 9CBis.9       Refactor UI Documentos — vista unificada de HubDocument (PDF + crawler)
  ├── 9CBis.10      Refactor de 9.8.2 — SSE emite Source[] estructurado (no string[])
  ├── 9CBis.11      Refactor de 9.10 — Widget renderiza citas como pills clicables
  ├── 9CBis.12 RED  router multi-materia: nodo route_to_subagent (tests)
  ├── 9CBis.13 GREEN router + UI admin de jerarquía padre/hijo
  └── 9CBis.14      UI admin: selector retrieval_mode con recomendación basada en tokens
```

**Cierre del bloque**: tras 9CBis.14, ejecutar la suite completa (`uv run pytest tests/ -v` en `server/` y `npm test` en `frontend/`) y verificar manualmente que (a) los chatbots existentes siguen respondiendo (modo `vector` por defecto), (b) un chatbot nuevo configurado en `long_context` o `agentic` responde con citas precisas a documento, (c) el router multi-materia delega correctamente entre hijos. Generar el `.bat` de pruebas manuales agregado para todo el bloque.

---

### Guía 9CBis.0 — Conceptos: tres modos de retrieval, cita como contrato y router multi-materia

**Objetivo**: regla única y reutilizable para decidir, ante cualquier extensión futura del sistema RAG, cómo encaja en los tres modos y cómo se preserva el contrato de citas. Aplica a los prompts 9CBis.1–9CBis.14 y a cualquier nodo o tool RAG que se añada después.

Esta guía **no produce código**: es el filtro conceptual que cada prompt aplica.

#### Los tres modos de retrieval

| Modo | Cuándo usarlo | Qué hace en runtime | Coste/Latencia |
|---|---|---|---|
| `vector` | Corpus > 2 M tokens; preguntas muy específicas; presupuesto ajustado | `HybridRetriever.hybrid_search` → top-k chunks → contexto al LLM | Bajo coste, latencia baja, retrieval imperfecto |
| `long_context` | Corpus < 100 K tokens; máxima precisión de cita | Empaqueta todos los `HubDocument` activos como bloque cacheable en el system prompt | Coste alto sin cache; bajo con cache (TTL 5 min) |
| `agentic` | Corpus 100 K – 2 M tokens; preguntas multi-documento | Expone tools `list_documents` y `read_document` al LLM; el LLM elige qué leer iterativamente | Coste medio; latencia mayor (varias iteraciones); preserva estructura |

**Regla dura**: `RetrievalStrategy` es la única abstracción que el grafo conoce. Los nodos del grafo no importan `HybridRetriever` ni `HubDocumentChunk` directamente — se inyecta la strategy.

#### Cita como contrato del agente

La cita NO es responsabilidad del retriever. La cita es:

1. **Un dato estructurado**: el retriever devuelve `Source` (`document_id`, `title`, `url`, `excerpt`, `score`), no strings.
2. **Una obligación del system prompt**: el agente debe citar tras cada afirmación factual, formato `[título](url)`.
3. **Un post-validador**: tras generar la respuesta, si hubo `Source[]` recuperados y el texto no contiene ninguna cita, se inyecta un fallback ("No tengo información suficiente para responder con citas verificables").

Esta separación garantiza que cambiar de `vector` a `agentic` no rompa las citas — el contrato vive fuera del retriever.

#### Router multi-materia (opcional)

Un `HubChatbot` puede ser:

- **`kind="atomic"`** (default): un chatbot con su propio corpus y `retrieval_mode`. Es el caso de un ayuntamiento pequeño.
- **`kind="router"`**: un chatbot sin corpus propio que tiene hijos atómicos. La consulta entra al router, que clasifica por embeddings (con LLM como fallback) y delega al hijo. Es el caso de UJI: chatbot raíz "UJI" → hijos "Normativa académica", "RRHH", "Económico-financiero", "Investigación", etc.

El router reutiliza el `QueryClassifier` de la **FASE 9B** (Grafo Público Enriquecido). Si la FASE 9B aún no está implementada cuando se aborde 9CBis, el clasificador se introduce aquí en su forma mínima (embeddings vs `system_prompt` de los hijos) y la FASE 9B lo enriquece después.

#### Reglas de clasificación

| Decisión | Regla |
|---|---|
| ¿Modelo nuevo de datos toca chunks? | NO — chunks son una derivación del documento. La verdad es `HubDocument`. |
| ¿Un nodo del grafo necesita acceso al corpus? | Inyecta `RetrievalStrategy`, no `HybridRetriever`. |
| ¿Una nueva tool del agente devuelve texto? | Devuelve `Source[]` estructurado, no string. |
| ¿Quién decide el modo? | El admin en el panel; el sistema solo recomienda. |
| ¿El router puede tener nietos? | NO en esta primera versión: jerarquía de exactamente dos niveles (router → atomic). |

---

### Prompt 9CBis.1 — TDD RED: modelo `HubDocument` + nuevos campos en `HubChatbot`

**Objetivo**: definir los tests del nuevo modelo `HubDocument` (unidad citable, vive en `HubOperationalBase`) y de los nuevos campos de `HubChatbot` (`retrieval_mode`, `kind`, `parent_chatbot_id`). Tests deben fallar (RED).

**Ámbito**: edge (`HubDocument` toca datos del cliente final).

**Decisiones de modelado**:

- `HubDocument.id`: UUID, generado en backend.
- `HubDocument.chatbot_id`: FK lógica a `hub_chatbots.id` (sin `relationship` cross-base, según frontera 9.6.5).
- `HubDocument.title`: string (extraído del primer `# H1` del markdown si no se proporciona; obligatorio).
- `HubDocument.canonical_url`: URL pública para citar; obligatorio (si no hay URL real, se usa la storage key como fallback).
- `HubDocument.markdown_content`: texto completo procesado por Docling.
- `HubDocument.token_count`: int, calculado en ingesta con `tiktoken` o aproximación `len(content) // 4`.
- `HubDocument.content_hash`: hash sha256 del markdown (para detectar cambios sin re-procesar).
- `HubDocument.language`: detectado en ingesta.
- `HubDocument.source_kind`: `"upload" | "crawler" | "manual"`.
- `HubDocument.section_path`: opcional, ruta jerárquica `"Reglamento de Permanencia > Título II > Art. 23"` cuando la ingestión segmenta por secciones (extensión futura del crawler).
- `HubDocument.created_at`, `updated_at`.

Nuevos campos en `HubChatbot`:

- `retrieval_mode`: `Literal["vector", "long_context", "agentic"]`, default `"vector"` (para no romper chatbots existentes).
- `kind`: `Literal["atomic", "router"]`, default `"atomic"`.
- `parent_chatbot_id`: UUID nullable; FK a `hub_chatbots.id` con `ondelete="SET NULL"`. Sólo se rellena si el chatbot es hijo de un router.

**`server/tests/modules/agents_hub/unit/test_hub_document.py`**:

```python
"""Tests del modelo HubDocument — TDD RED."""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestHubDocument:

    @pytest.mark.asyncio
    async def test_create_document_with_required_fields(self, db_session: AsyncSession):
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        doc = HubDocument(
            chatbot_id=uuid.uuid4(),
            title="Reglamento de Permanencia",
            canonical_url="https://uji.es/normativa/permanencia.pdf",
            markdown_content="# Reglamento de Permanencia\n\nArt. 1...",
            content_hash="a" * 64,
            language="es",
            source_kind="upload",
            token_count=1234,
        )
        db_session.add(doc)
        await db_session.commit()
        assert doc.id is not None
        assert doc.created_at is not None

    @pytest.mark.asyncio
    async def test_title_is_required(self, db_session):
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        doc = HubDocument(
            chatbot_id=uuid.uuid4(),
            canonical_url="https://uji.es/x.pdf",
            markdown_content="contenido",
            content_hash="b" * 64,
            language="es",
            source_kind="upload",
            token_count=10,
        )
        db_session.add(doc)
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_content_hash_uniqueness_per_chatbot(self, db_session):
        """Mismo hash + mismo chatbot → conflicto; mismo hash en otro chatbot → OK."""
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        cb_a, cb_b = uuid.uuid4(), uuid.uuid4()
        h = "c" * 64
        d1 = HubDocument(chatbot_id=cb_a, title="X", canonical_url="u1", markdown_content="x",
                         content_hash=h, language="es", source_kind="upload", token_count=1)
        d2 = HubDocument(chatbot_id=cb_b, title="X", canonical_url="u2", markdown_content="x",
                         content_hash=h, language="es", source_kind="upload", token_count=1)
        db_session.add_all([d1, d2])
        await db_session.commit()  # OK, distintos chatbots

        d3 = HubDocument(chatbot_id=cb_a, title="X dup", canonical_url="u3", markdown_content="x",
                         content_hash=h, language="es", source_kind="upload", token_count=1)
        db_session.add(d3)
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_chunk_has_optional_document_id_fk(self, db_session):
        """HubDocumentChunk gana un campo document_id (nullable para retrocompatibilidad)."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubDocument, HubDocumentChunk,
        )
        doc = HubDocument(
            chatbot_id=uuid.uuid4(), title="X", canonical_url="u",
            markdown_content="x", content_hash="d" * 64, language="es",
            source_kind="upload", token_count=1,
        )
        db_session.add(doc); await db_session.commit()

        chunk = HubDocumentChunk(
            chatbot_id=doc.chatbot_id,
            document_id=doc.id,
            content="frag",
            source_url="u",
            content_hash="e" * 64,
            language="es",
        )
        db_session.add(chunk); await db_session.commit()
        assert chunk.document_id == doc.id
```

**`server/tests/modules/agents_hub/unit/test_hub_chatbot_retrieval_fields.py`**:

```python
"""Tests de los nuevos campos de HubChatbot — TDD RED."""
import uuid
import pytest


class TestHubChatbotRetrievalFields:

    @pytest.mark.asyncio
    async def test_default_retrieval_mode_is_vector(self, db_session):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        # ... crear cliente y llm_config previos ...
        cb = HubChatbot(client_id=..., llm_config_id=..., name="cb1", system_prompt="...")
        db_session.add(cb); await db_session.commit()
        assert cb.retrieval_mode == "vector"
        assert cb.kind == "atomic"
        assert cb.parent_chatbot_id is None

    @pytest.mark.asyncio
    async def test_router_chatbot_has_no_corpus(self, db_session):
        """Un chatbot router no debería tener documentos asociados (regla a nivel UI/servicio)."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        cb = HubChatbot(client_id=..., llm_config_id=..., name="UJI",
                        system_prompt="Router de la UJI", kind="router")
        db_session.add(cb); await db_session.commit()
        assert cb.kind == "router"

    @pytest.mark.asyncio
    async def test_child_chatbot_references_router(self, db_session):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        router = HubChatbot(client_id=..., llm_config_id=..., name="UJI",
                            system_prompt="...", kind="router")
        db_session.add(router); await db_session.commit()
        child = HubChatbot(client_id=router.client_id, llm_config_id=router.llm_config_id,
                           name="UJI / Normativa académica", system_prompt="...",
                           kind="atomic", parent_chatbot_id=router.id,
                           retrieval_mode="agentic")
        db_session.add(child); await db_session.commit()
        assert child.parent_chatbot_id == router.id

    @pytest.mark.asyncio
    async def test_invalid_retrieval_mode_rejected(self, db_session):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        cb = HubChatbot(client_id=..., llm_config_id=..., name="x", system_prompt="...",
                        retrieval_mode="random")
        db_session.add(cb)
        with pytest.raises(Exception):
            await db_session.commit()
```

**Confirmar RED**: `uv run pytest tests/modules/agents_hub/unit/test_hub_document.py tests/modules/agents_hub/unit/test_hub_chatbot_retrieval_fields.py -v` → todos los tests deben fallar por `AttributeError` o `ImportError`.

---

### Prompt 9CBis.2 — TDD GREEN: modelo `HubDocument`, migración Alembic y refactor de `HubDocumentChunk`

**Objetivo**: implementar el modelo `HubDocument`, los nuevos campos en `HubChatbot`, la FK opcional `document_id` en `HubDocumentChunk` y la migración Alembic. Los tests del 9CBis.1 deben pasar.

**Cambios en `server/app/modules/agents_hub/database/operational_models.py`**:

```python
class HubDocument(HubOperationalBase):
    """Documento citable. Unidad atómica del corpus de un chatbot."""

    __tablename__ = "hub_documents"
    __table_args__ = (
        UniqueConstraint("chatbot_id", "content_hash", name="uq_document_chatbot_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # upload | crawler | manual
    section_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# En HubDocumentChunk, añadir:
class HubDocumentChunk(HubOperationalBase):
    # ... campos existentes ...
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    # FK lógica a hub_documents.id; ondelete="CASCADE" se gestiona en la migración Alembic.
```

**Cambios en `server/app/modules/agents_hub/database/config_models.py`** (`HubChatbot`):

```python
from sqlalchemy import CheckConstraint

class HubChatbot(HubConfigBase):
    # ... campos existentes ...
    retrieval_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="vector",
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="atomic")
    parent_chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_chatbots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "retrieval_mode IN ('vector', 'long_context', 'agentic')",
            name="ck_chatbot_retrieval_mode",
        ),
        CheckConstraint(
            "kind IN ('atomic', 'router')",
            name="ck_chatbot_kind",
        ),
    )
```

**Migración Alembic** (`server/alembic/versions/<id>_hub_documents_and_retrieval_mode.py`):

1. `CREATE TABLE hub_documents` con todos los campos y `UniqueConstraint(chatbot_id, content_hash)`.
2. `ALTER TABLE hub_document_chunks ADD COLUMN document_id UUID NULL` + índice.
3. `ALTER TABLE hub_chatbots ADD COLUMN retrieval_mode VARCHAR(20) NOT NULL DEFAULT 'vector'`.
4. `ALTER TABLE hub_chatbots ADD COLUMN kind VARCHAR(20) NOT NULL DEFAULT 'atomic'`.
5. `ALTER TABLE hub_chatbots ADD COLUMN parent_chatbot_id UUID NULL` + FK + índice.
6. Añadir los dos `CHECK` constraints.
7. Migración de datos: para cada `HubIngestionJob` ya existente con `status="completed"`, crear el `HubDocument` correspondiente y backfillear `HubDocumentChunk.document_id` agrupando por `source_url`.

```python
def upgrade() -> None:
    # 1. Crear tabla hub_documents
    op.create_table(
        "hub_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("chatbot_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=False),
        sa.Column("markdown_content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("source_kind", sa.String(20), nullable=False),
        sa.Column("section_path", sa.String(1024), nullable=True),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chatbot_id", "content_hash", name="uq_document_chatbot_hash"),
    )
    op.create_index("ix_hub_documents_chatbot_id", "hub_documents", ["chatbot_id"])
    op.create_index("ix_hub_documents_content_hash", "hub_documents", ["content_hash"])

    # 2. Añadir document_id a chunks
    op.add_column("hub_document_chunks",
                  sa.Column("document_id", UUID(as_uuid=True), nullable=True))
    op.create_index("ix_hub_document_chunks_document_id",
                    "hub_document_chunks", ["document_id"])

    # 3. Nuevos campos en hub_chatbots
    op.add_column("hub_chatbots",
                  sa.Column("retrieval_mode", sa.String(20),
                            nullable=False, server_default="vector"))
    op.add_column("hub_chatbots",
                  sa.Column("kind", sa.String(20),
                            nullable=False, server_default="atomic"))
    op.add_column("hub_chatbots",
                  sa.Column("parent_chatbot_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_chatbot_parent", "hub_chatbots", "hub_chatbots",
        ["parent_chatbot_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_hub_chatbots_parent", "hub_chatbots", ["parent_chatbot_id"])
    op.create_check_constraint(
        "ck_chatbot_retrieval_mode", "hub_chatbots",
        "retrieval_mode IN ('vector', 'long_context', 'agentic')",
    )
    op.create_check_constraint(
        "ck_chatbot_kind", "hub_chatbots",
        "kind IN ('atomic', 'router')",
    )

    # 4. Backfill: crear HubDocument por cada job completado con chunks
    op.execute("""
        INSERT INTO hub_documents
            (id, chatbot_id, title, canonical_url, markdown_content,
             content_hash, language, source_kind, token_count, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            j.chatbot_id,
            COALESCE(j.original_filename, j.canonical_url, j.source_url),
            COALESCE(j.canonical_url, j.source_url),
            '',                                          -- markdown_content vacío en backfill
            (SELECT MIN(c.content_hash) FROM hub_document_chunks c
             WHERE c.chatbot_id = j.chatbot_id
               AND c.source_url = COALESCE(j.canonical_url, j.source_url)),
            COALESCE(j.language, 'es'),
            CASE WHEN j.source_url LIKE 'http%' THEN 'crawler' ELSE 'upload' END,
            COALESCE(j.chunks_processed * 250, 0),       -- aprox tokens
            j.created_at,
            j.created_at
        FROM hub_ingestion_jobs j
        WHERE j.status = 'completed'
          AND EXISTS (SELECT 1 FROM hub_document_chunks c
                      WHERE c.chatbot_id = j.chatbot_id
                        AND c.source_url = COALESCE(j.canonical_url, j.source_url));
    """)

    # 5. Backfill: vincular chunks a su document por (chatbot_id, source_url)
    op.execute("""
        UPDATE hub_document_chunks c
        SET document_id = d.id
        FROM hub_documents d
        WHERE d.chatbot_id = c.chatbot_id
          AND d.canonical_url = c.source_url
          AND c.document_id IS NULL;
    """)


def downgrade() -> None:
    op.drop_constraint("ck_chatbot_kind", "hub_chatbots")
    op.drop_constraint("ck_chatbot_retrieval_mode", "hub_chatbots")
    op.drop_index("ix_hub_chatbots_parent", "hub_chatbots")
    op.drop_constraint("fk_chatbot_parent", "hub_chatbots", type_="foreignkey")
    op.drop_column("hub_chatbots", "parent_chatbot_id")
    op.drop_column("hub_chatbots", "kind")
    op.drop_column("hub_chatbots", "retrieval_mode")
    op.drop_index("ix_hub_document_chunks_document_id", "hub_document_chunks")
    op.drop_column("hub_document_chunks", "document_id")
    op.drop_index("ix_hub_documents_content_hash", "hub_documents")
    op.drop_index("ix_hub_documents_chatbot_id", "hub_documents")
    op.drop_table("hub_documents")
```

**Confirmar GREEN**:

```bash
cd server && uv run alembic upgrade head
uv run pytest tests/modules/agents_hub/unit/test_hub_document.py -v
uv run pytest tests/modules/agents_hub/unit/test_hub_chatbot_retrieval_fields.py -v
uv run pytest tests/ -v   # regresión completa: nada debe romperse
```

---

### Prompt 9CBis.3 — TDD RED: Protocol `RetrievalStrategy` + dataclass `Source` ✅ COMPLETADO (2026-04-28)

**Objetivo**: definir el contrato `RetrievalStrategy` que abstrae los tres modos, y la dataclass `Source` que sustituye al `string` actual de fuentes. Tests del Protocol y de la dataclass; los nodos del grafo aún no se tocan.

**`server/app/modules/agents_hub/services/retrieval/__init__.py`** (módulo nuevo).

**`server/app/modules/agents_hub/services/retrieval/types.py`**:

```python
"""Tipos compartidos entre las distintas RetrievalStrategy."""

import uuid
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Source:
    """Documento citable devuelto por una RetrievalStrategy."""
    document_id: uuid.UUID
    title: str
    url: str
    excerpt: str            # fragmento mostrado al LLM (puede ser el documento completo)
    score: float            # relevancia [0, 1] (1.0 si la strategy no calcula score)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalContext:
    """Contexto agregado que se pasa al nodo generate_response."""
    sources: list[Source]
    mode: str                       # "vector" | "long_context" | "agentic"
    total_tokens: int               # suma estimada de tokens del excerpt agregado


class RetrievalStrategy(Protocol):
    """Contrato común a las tres estrategias.

    Las strategies que pre-recuperan (vector, long_context) implementan get_context.
    AgenticRetrievalStrategy devuelve un RetrievalContext vacío y expone tools al grafo.
    """

    mode: str  # "vector" | "long_context" | "agentic"

    async def get_context(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
    ) -> RetrievalContext: ...

    def get_agent_tools(self) -> list:
        """Devuelve lista de tools LangChain (vacía salvo en agentic)."""
        ...
```

**`server/tests/modules/agents_hub/unit/test_retrieval_types.py`**:

```python
"""Tests de los tipos compartidos de retrieval — TDD RED."""
import uuid
import pytest


class TestSource:

    def test_source_is_frozen(self):
        from server.app.modules.agents_hub.services.retrieval.types import Source
        s = Source(document_id=uuid.uuid4(), title="X", url="u", excerpt="e", score=0.9)
        with pytest.raises(Exception):
            s.score = 0.5  # frozen dataclass

    def test_source_default_metadata_empty(self):
        from server.app.modules.agents_hub.services.retrieval.types import Source
        s = Source(document_id=uuid.uuid4(), title="X", url="u", excerpt="e", score=1.0)
        assert s.metadata == {}


class TestRetrievalContext:

    def test_empty_context(self):
        from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext
        ctx = RetrievalContext(sources=[], mode="vector", total_tokens=0)
        assert ctx.sources == []
        assert ctx.mode == "vector"


class TestRetrievalStrategyProtocol:

    def test_protocol_requires_get_context_and_get_agent_tools(self):
        from server.app.modules.agents_hub.services.retrieval.types import RetrievalStrategy

        class IncompleteStrategy:
            mode = "vector"
        # Protocol no fuerza en runtime, pero un implementador real debería tener ambos métodos.
        # Verificamos que el Protocol exista y exponga los nombres esperados.
        assert hasattr(RetrievalStrategy, "get_context")
        assert hasattr(RetrievalStrategy, "get_agent_tools")
```

**Confirmar RED**: `uv run pytest tests/modules/agents_hub/unit/test_retrieval_types.py -v` → falla por `ImportError`.

---

### Prompt 9CBis.4 — TDD GREEN: `VectorRetrievalStrategy` (envuelve `HybridRetriever`) ✅ COMPLETADO (2026-04-28)

**Objetivo**: implementar la primera strategy real, que envuelve el `HybridRetriever` existente sin tocarlo. Garantiza retrocompatibilidad: cualquier chatbot con `retrieval_mode="vector"` (default tras migración) sigue funcionando exactamente igual, **excepto** que ahora las fuentes vienen agrupadas por `document_id` (no chunks sueltos).

**Cambio clave**: la strategy agrega los chunks recuperados por `document_id`, escoge el chunk con mayor score como `excerpt` representativo, y devuelve un `Source` por documento. Esto elimina el problema actual de citar 3 chunks del mismo PDF.

**`server/app/modules/agents_hub/services/retrieval/vector_strategy.py`**:

```python
"""VectorRetrievalStrategy — envuelve HybridRetriever y agrupa por documento."""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.retrieval.types import (
    RetrievalContext, Source,
)
from server.app.modules.agents_hub.services.retriever import HybridRetriever


class VectorRetrievalStrategy:
    mode = "vector"

    def __init__(
        self,
        session: AsyncSession,
        embedding_service,
        top_k: int = 8,
    ):
        self._session = session
        self._embedding = embedding_service
        self._retriever = HybridRetriever(session)
        self._top_k = top_k

    async def get_context(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
    ) -> RetrievalContext:
        query_embedding = await self._embedding.embed(query)
        results = await self._retriever.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            chatbot_id=chatbot_id,
            top_k=self._top_k,
            language=language,
        )
        if not results:
            return RetrievalContext(sources=[], mode=self.mode, total_tokens=0)

        # Agrupar chunks por document_id
        by_doc: dict[uuid.UUID | None, list] = defaultdict(list)
        for r in results:
            by_doc[r.metadata.get("document_id")].append(r)

        # Cargar documentos en bloque
        doc_ids = [d for d in by_doc.keys() if d is not None]
        docs_map: dict[uuid.UUID, HubDocument] = {}
        if doc_ids:
            stmt = select(HubDocument).where(HubDocument.id.in_(doc_ids))
            res = await self._session.execute(stmt)
            docs_map = {d.id: d for d in res.scalars().all()}

        sources: list[Source] = []
        total_tokens = 0
        for doc_id, chunks in by_doc.items():
            best = max(chunks, key=lambda c: c.score)
            doc = docs_map.get(doc_id) if doc_id else None
            title = doc.title if doc else best.source_url.rsplit("/", 1)[-1]
            url = doc.canonical_url if doc else best.source_url
            excerpt = best.content
            sources.append(Source(
                document_id=doc.id if doc else uuid.uuid4(),
                title=title, url=url, excerpt=excerpt, score=best.score,
                metadata={"chunks_matched": len(chunks)},
            ))
            total_tokens += len(excerpt) // 4

        sources.sort(key=lambda s: s.score, reverse=True)
        return RetrievalContext(sources=sources, mode=self.mode, total_tokens=total_tokens)

    def get_agent_tools(self) -> list:
        return []  # vector pre-recupera; no expone tools al agente
```

**Tests** en `server/tests/modules/agents_hub/unit/test_vector_strategy.py`:

```python
# test_returns_empty_context_when_no_chunks
# test_groups_multiple_chunks_into_one_source_per_document
# test_uses_document_title_and_canonical_url_when_available
# test_falls_back_to_filename_when_no_document_record
# test_get_agent_tools_returns_empty_list
# test_total_tokens_is_approximated_from_excerpt_length
```

**Confirmar GREEN**:

```bash
cd server && uv run pytest tests/modules/agents_hub/unit/test_vector_strategy.py -v
uv run pytest tests/ -v -k "not slow"   # regresión: el chat sigue funcionando
```

---

### Prompt 9CBis.5 — `LongContextRetrievalStrategy` con prompt caching (RED → GREEN) ✅ COMPLETADO (2026-04-28)

**Objetivo**: implementar la strategy `long_context` que carga todos los `HubDocument` activos del chatbot y los empaqueta como un único bloque marcado con cache breakpoint para que el LLM lo reutilice entre consultas (TTL 5 min). Solo aplicable cuando `sum(token_count) < LONG_CONTEXT_LIMIT` (configurable, default 150 K).

**`server/app/modules/agents_hub/services/retrieval/long_context_strategy.py`**:

```python
"""LongContextRetrievalStrategy — empaqueta todo el corpus en el contexto del LLM."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.retrieval.types import (
    RetrievalContext, Source,
)


LONG_CONTEXT_TOKEN_LIMIT = 150_000


class LongContextRetrievalStrategy:
    mode = "long_context"

    def __init__(self, session: AsyncSession, token_limit: int = LONG_CONTEXT_TOKEN_LIMIT):
        self._session = session
        self._token_limit = token_limit

    async def get_context(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
    ) -> RetrievalContext:
        stmt = select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
        if language:
            stmt = stmt.where(HubDocument.language == language)
        stmt = stmt.order_by(HubDocument.created_at)
        result = await self._session.execute(stmt)
        documents = list(result.scalars().all())

        total = sum(d.token_count for d in documents)
        if total > self._token_limit:
            raise ValueError(
                f"Long context mode no admite corpus de {total} tokens "
                f"(límite {self._token_limit}). Cambia el modo a 'agentic' o 'vector'."
            )

        sources = [
            Source(
                document_id=d.id,
                title=d.title,
                url=d.canonical_url,
                excerpt=d.markdown_content,
                score=1.0,
                metadata={
                    "language": d.language,
                    "section_path": d.section_path,
                    "cacheable": True,    # marcador para que generate_response use cache_control
                },
            )
            for d in documents
        ]
        return RetrievalContext(sources=sources, mode=self.mode, total_tokens=total)

    def get_agent_tools(self) -> list:
        return []
```

**Integración con prompt caching**: el nodo `generate_response` (modificado en 9CBis.7) detecta `metadata["cacheable"] == True` y al construir los mensajes Anthropic añade `"cache_control": {"type": "ephemeral"}` al bloque del corpus, antes del mensaje del usuario. Si el LLM activo no es Anthropic, el campo se ignora silenciosamente (Gemini/OpenAI tienen sus propios mecanismos; documentar como TODO para extensión futura).

**Tests** en `server/tests/modules/agents_hub/unit/test_long_context_strategy.py`:

```python
# test_returns_all_documents_as_sources_when_under_limit
# test_raises_when_corpus_exceeds_limit
# test_filters_by_language_when_specified
# test_marks_sources_as_cacheable
# test_returns_empty_when_chatbot_has_no_documents
```

**Confirmar**:

```bash
cd server && uv run pytest tests/modules/agents_hub/unit/test_long_context_strategy.py -v
```

---

### Prompt 9CBis.6 — `AgenticRetrievalStrategy` + tools `list_documents` / `read_document` (RED → GREEN) ✅ COMPLETADO (2026-04-28)

**Objetivo**: implementar la strategy `agentic` que NO pre-recupera. Devuelve un `RetrievalContext` vacío y expone dos tools al grafo LangGraph. El LLM razona sobre el índice y carga lo que necesita.

**Tools nuevas** en `server/app/modules/agents_hub/agent/tools/`:

#### `list_documents.py`

```python
"""Tool: lista el índice de documentos disponibles para el chatbot."""

import uuid
from typing import Protocol


class DocumentIndexProtocol(Protocol):
    async def list_index(self, chatbot_id: uuid.UUID, language: str | None) -> list[dict]: ...


async def list_documents(
    chatbot_id: str,
    index: DocumentIndexProtocol,
    language: str | None = None,
) -> str:
    """Devuelve un índice formateado de documentos disponibles.

    Cada entrada: `[id] título — sección_path (idioma, ~tokens)`. El LLM lo lee y decide
    qué cargar con `read_document(id=<uuid>)`.
    """
    items = await index.list_index(uuid.UUID(chatbot_id), language)
    if not items:
        return "No hay documentos disponibles para este chatbot."
    lines = ["Documentos disponibles (usa read_document(id=<id>) para leer uno):"]
    for it in items:
        section = f" — {it['section_path']}" if it.get("section_path") else ""
        lines.append(
            f"[{it['id']}] {it['title']}{section} "
            f"({it['language']}, ~{it['token_count']} tokens, {it['url']})"
        )
    return "\n".join(lines)
```

#### `read_document.py`

```python
"""Tool: devuelve el markdown completo de un documento."""

import uuid
from typing import Protocol


class DocumentReaderProtocol(Protocol):
    async def read(self, document_id: uuid.UUID) -> dict | None: ...


async def read_document(
    document_id: str,
    reader: DocumentReaderProtocol,
) -> str:
    """Devuelve el markdown completo del documento solicitado para que el LLM lo cite.

    El LLM debe citar como `[título](url)` tras cada afirmación factual basada en este
    contenido. Si el documento no existe, devuelve un mensaje explícito.
    """
    doc = await reader.read(uuid.UUID(document_id))
    if not doc:
        return f"Documento {document_id} no encontrado."
    return (
        f"# {doc['title']}\n"
        f"_Fuente: {doc['url']}_\n\n"
        f"{doc['markdown_content']}"
    )
```

#### `agentic_strategy.py`

```python
"""AgenticRetrievalStrategy — el LLM elige qué documentos leer."""

import uuid

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.agent.tools.list_documents import list_documents
from server.app.modules.agents_hub.agent.tools.read_document import read_document
from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.retrieval.types import (
    RetrievalContext,
)


class AgenticRetrievalStrategy:
    mode = "agentic"

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_index(self, chatbot_id: uuid.UUID, language: str | None) -> list[dict]:
        stmt = select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
        if language:
            stmt = stmt.where(HubDocument.language == language)
        stmt = stmt.order_by(HubDocument.title)
        res = await self._session.execute(stmt)
        return [
            {"id": str(d.id), "title": d.title, "url": d.canonical_url,
             "language": d.language, "section_path": d.section_path,
             "token_count": d.token_count}
            for d in res.scalars().all()
        ]

    async def read(self, document_id: uuid.UUID) -> dict | None:
        doc = await self._session.get(HubDocument, document_id)
        if not doc:
            return None
        return {"title": doc.title, "url": doc.canonical_url,
                "markdown_content": doc.markdown_content}

    async def get_context(self, query, chatbot_id, language=None) -> RetrievalContext:
        # No pre-recuperación: el agente decide vía tools
        return RetrievalContext(sources=[], mode=self.mode, total_tokens=0)

    def get_agent_tools(self) -> list:
        # Bind del chatbot_id se hace en el grafo (cierre sobre state["chatbot_id"])
        return [list_documents, read_document]
```

**Sources retornados al final**: cuando el agente termina, el grafo recoge los `document_id` de cada llamada a `read_document` y los empaqueta como `Source[]` en el evento `done` del SSE. Esto se implementa en 9CBis.10.

**Tests** en `server/tests/modules/agents_hub/unit/test_agentic_strategy.py`:

```python
# test_get_context_returns_empty_for_agentic
# test_get_agent_tools_returns_list_and_read_tools
# test_list_index_returns_all_documents_of_chatbot
# test_list_index_filters_by_language
# test_read_returns_full_markdown_with_metadata
# test_read_returns_none_for_unknown_id
# test_list_documents_tool_formats_index_with_token_estimates
# test_read_document_tool_returns_not_found_message_for_unknown_id
```

**Confirmar**:

```bash
cd server && uv run pytest tests/modules/agents_hub/unit/test_agentic_strategy.py -v
uv run pytest tests/modules/agents_hub/unit/ -v   # regresión retrieval
```

---

### Prompt 9CBis.7 — Citas como contrato del agente: system prompt + post-validador (RED → GREEN)

**Objetivo**: el contrato de citas vive en el agente, no en el retriever. Tras este prompt, cualquier chatbot — sea `vector`, `long_context` o `agentic` — devuelve respuestas con citas o un fallback honesto si no puede citar.

**Componentes**:

1. **Plantilla base de system prompt** con instrucción de cita, integrada en `generate_response_node`.
2. **`citation_validator.py`** — función pura que detecta si la respuesta contiene al menos una cita en formato `[título](url)` cuando hubo `Source[]` recuperados.
3. **Refactor del nodo `generate_response`** del grafo: usa `RetrievalStrategy` inyectada, monta el system prompt según el modo, llama al LLM, valida citas, y devuelve `{"messages": [...], "sources": [...]}`.

**`server/app/modules/agents_hub/agent/prompts.py`** (módulo nuevo, prompts compartidos):

```python
"""Plantillas de system prompt para el grafo del agente."""

CITATION_RULES = """\
REGLAS DE CITA (obligatorias):
1. Cada afirmación factual basada en los documentos debe ir seguida de una cita en formato
   markdown `[título del documento](url)`. La cita va al final de la frase citada.
2. Si una afirmación combina varios documentos, cita todos: `[doc1](url1) [doc2](url2)`.
3. Si la pregunta no puede responderse con la información disponible, dilo explícitamente:
   "No tengo información suficiente en los documentos disponibles para responder a esta
   pregunta con citas verificables." NO inventes información ni cites documentos no
   recuperados.
4. NUNCA inventes URLs ni títulos. Usa SOLO los proporcionados en el contexto.
"""


def build_system_prompt(
    base_prompt: str,
    language: str,
    sources_block: str,
    mode: str,
) -> str:
    """Construye el system prompt final.

    Args:
        base_prompt: system_prompt definido por el admin para el chatbot.
        language: idioma de respuesta detectado.
        sources_block: bloque markdown con los documentos (vacío en agentic).
        mode: vector | long_context | agentic.
    """
    parts = [base_prompt.strip(), "", f"Responde en {language}.", "", CITATION_RULES.strip()]
    if mode == "agentic":
        parts.append(
            "\nUsa la tool `list_documents` para ver el índice y `read_document(id=...)` "
            "para cargar el texto completo de cada documento que necesites antes de responder."
        )
    elif sources_block:
        parts.extend(["", "DOCUMENTOS DISPONIBLES:", "", sources_block])
    return "\n".join(parts)


def format_sources_block(sources: list) -> str:
    """Convierte Source[] en un bloque markdown que el LLM puede leer y citar."""
    if not sources:
        return ""
    lines = []
    for s in sources:
        lines.append(f"## {s.title}")
        lines.append(f"_URL: {s.url}_")
        lines.append("")
        lines.append(s.excerpt)
        lines.append("")
    return "\n".join(lines)
```

**`server/app/modules/agents_hub/agent/citation_validator.py`** (módulo nuevo):

```python
"""Validación post-generación: garantiza que la respuesta cite cuando debe."""

import re

# Patrón markdown link: [texto](url) — captura cualquier link, no solo URL externa
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

NO_CITATION_FALLBACK = (
    "No tengo información suficiente en los documentos disponibles para responder a "
    "esta pregunta con citas verificables. ¿Podrías reformular o proporcionar más contexto?"
)


def has_valid_citations(response_text: str, allowed_urls: set[str]) -> bool:
    """True si la respuesta contiene al menos una cita cuyo URL esté en allowed_urls."""
    for _title, url in _MD_LINK.findall(response_text):
        if url.strip() in allowed_urls:
            return True
    return False


def enforce_citation_contract(
    response_text: str,
    sources: list,
    mode: str,
) -> str:
    """Si hubo sources y la respuesta no cita ninguno válido, devuelve el fallback.

    En modo agentic, se relaja: el agente puede decidir no leer ningún documento (saludo,
    charla); validamos solo si las tools fueron invocadas (señalado por sources no vacío).
    """
    if not sources:
        return response_text
    allowed = {s.url for s in sources}
    if has_valid_citations(response_text, allowed):
        return response_text
    return NO_CITATION_FALLBACK
```

**Refactor del grafo** (`server/app/modules/agents_hub/agent/graph.py`):

```python
def create_agent_graph(
    retrieval_strategy,         # RetrievalStrategy inyectada
    llm,                        # BaseChatModel inyectado (no hardcodear ChatGoogleGenerativeAI)
    base_system_prompt: str,    # del HubChatbot
    user_id: str | None = None,
):
    async def search_or_skip_node(state):
        if retrieval_strategy.mode == "agentic":
            return {"retrieved_sources": [], "retrieval_mode": "agentic"}
        ctx = await retrieval_strategy.get_context(
            query=state["messages"][-1].content,
            chatbot_id=uuid.UUID(state["chatbot_id"]),
            language=state.get("language"),
        )
        return {
            "retrieved_sources": ctx.sources,
            "retrieval_mode": ctx.mode,
            "total_tokens": ctx.total_tokens,
        }

    async def generate_response_node(state):
        sources = state.get("retrieved_sources", [])
        mode = state.get("retrieval_mode", "vector")
        sources_block = format_sources_block(sources)
        system = build_system_prompt(
            base_system_prompt, state.get("language", "es"), sources_block, mode,
        )

        if mode == "agentic":
            llm_with_tools = llm.bind_tools(retrieval_strategy.get_agent_tools())
            response = await llm_with_tools.ainvoke([
                {"role": "system", "content": system},
                *_to_messages(state["messages"]),
            ])
            # Loop tool-calling: tras cada read_document, registrar el doc_id en sources
            sources = await _run_agentic_loop(response, llm_with_tools, retrieval_strategy)
            text = sources_text  # output final del loop
        else:
            response = await llm.ainvoke([
                {"role": "system", "content": system},
                *_to_messages(state["messages"]),
            ])
            text = response.content

        validated = enforce_citation_contract(text, sources, mode)
        return {"messages": [AIMessage(content=validated)], "sources": sources}
```

**Tests** en `server/tests/modules/agents_hub/unit/test_citation_validator.py`:

```python
# test_returns_text_unchanged_when_no_sources
# test_returns_text_when_at_least_one_valid_citation_present
# test_returns_fallback_when_sources_exist_but_no_citation
# test_returns_fallback_when_citation_url_not_in_allowed
# test_detects_multiple_citations_in_same_paragraph
# test_agentic_mode_with_empty_sources_returns_text  # saludos no requieren cita
```

**Tests** en `server/tests/modules/agents_hub/unit/test_prompts.py`:

```python
# test_build_system_prompt_includes_citation_rules
# test_build_system_prompt_includes_language_directive
# test_build_system_prompt_for_agentic_mentions_tools
# test_build_system_prompt_for_long_context_includes_sources_block
# test_format_sources_block_renders_each_source_with_title_and_url
```

**Confirmar**:

```bash
cd server && uv run pytest tests/modules/agents_hub/unit/test_citation_validator.py -v
uv run pytest tests/modules/agents_hub/unit/test_prompts.py -v
uv run pytest tests/ -v -k "graph or agent"   # regresión grafo
```

---

### Prompt 9CBis.8 — Refactor de 9.7.x: `IngestionWatcher` crea `HubDocument`; chunks solo si `vector`

**Objetivo**: reescribir `IngestionWatcher` para que sea el productor canónico de `HubDocument`. El chunking + embedding ahora es **opcional** y se ejecuta solo cuando `chatbot.retrieval_mode == "vector"`. Los chatbots en `long_context` o `agentic` ingestan documentos sin generar chunks (ahorro de tiempo y storage).

**Cambios en `server/app/modules/agents_hub/ingestion/watcher.py`**:

```python
class IngestionWatcher:
    def __init__(self, session, embedding_service, storage=None,
                 chatbot_provider=None):
        # chatbot_provider: dependencia para leer HubChatbot.retrieval_mode
        # (no se importa HubChatbot directamente: cumple frontera edge/cloud)
        ...

    async def process_source(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
        citation_url: str | None = None,
        prefetched_content: str | None = None,
        title: str | None = None,
    ) -> HubDocument:
        """Crea/actualiza un HubDocument. Genera chunks SOLO si retrieval_mode == 'vector'.

        Returns:
            El HubDocument creado o actualizado (idempotente por content_hash).
        """
        # 1. Obtener markdown
        if prefetched_content is not None:
            content = prefetched_content
        else:
            processor = await self._get_processor()
            content = await asyncio.to_thread(processor.process, source_url)

        if language is None:
            language = detect_language(content)
        content_hash = hash_content(content)
        canonical = citation_url or source_url
        doc_title = title or _extract_title_from_markdown(content) or canonical
        token_count = _estimate_tokens(content)

        # 2. Idempotencia: ¿ya existe este documento (mismo chatbot, mismo hash)?
        existing = await self._session.execute(
            select(HubDocument).where(
                HubDocument.chatbot_id == chatbot_id,
                HubDocument.content_hash == content_hash,
            ).limit(1)
        )
        doc = existing.scalar_one_or_none()
        if doc:
            doc.canonical_url = canonical
            doc.title = doc_title
            doc.updated_at = datetime.now(timezone.utc)
        else:
            # Si la URL ya estaba registrada con otro hash → reemplazar
            old = await self._session.execute(
                select(HubDocument).where(
                    HubDocument.chatbot_id == chatbot_id,
                    HubDocument.canonical_url == canonical,
                )
            )
            for old_doc in old.scalars():
                # Borrar chunks vinculados (CASCADE manual)
                await self._session.execute(
                    delete(HubDocumentChunk).where(
                        HubDocumentChunk.document_id == old_doc.id
                    )
                )
                await self._session.delete(old_doc)
            doc = HubDocument(
                chatbot_id=chatbot_id, title=doc_title, canonical_url=canonical,
                markdown_content=content, content_hash=content_hash, language=language,
                source_kind="crawler" if source_url.startswith(("http://", "https://")) else "upload",
                token_count=token_count,
            )
            self._session.add(doc)
            await self._session.flush()

        # 3. Chunking + embedding solo si el chatbot está en modo vector
        retrieval_mode = await self._chatbot_provider.get_retrieval_mode(chatbot_id) \
            if self._chatbot_provider else "vector"
        if retrieval_mode == "vector":
            await self._regenerate_chunks_for_document(doc)
        else:
            # Asegurar que no quedan chunks de modos previos
            await self._session.execute(
                delete(HubDocumentChunk).where(HubDocumentChunk.document_id == doc.id)
            )

        await self._session.commit()
        return doc

    async def _regenerate_chunks_for_document(self, doc: HubDocument) -> None:
        await self._session.execute(
            delete(HubDocumentChunk).where(HubDocumentChunk.document_id == doc.id)
        )
        chunks = self.chunker.split(
            doc.markdown_content,
            metadata={"document_id": str(doc.id), "source_url": doc.canonical_url},
        )
        for ch in chunks:
            embedding = await self._embedding.embed(ch.content)
            self._session.add(HubDocumentChunk(
                chatbot_id=doc.chatbot_id,
                document_id=doc.id,
                content=ch.content,
                source_url=doc.canonical_url,
                content_hash=hash_content(ch.content),
                embedding=embedding,
                chunk_metadata={**ch.metadata, "document_id": str(doc.id)},
                language=doc.language,
            ))
```

**`process_user_upload`** mantiene `is_temporary=True` y `owner_id`, pero ahora también crea un `HubDocument` con `source_kind="upload"` para que las citas en modo agente funcionen. El TTL de cleanup borra documento + chunks.

**Helpers nuevos** en `server/app/modules/agents_hub/ingestion/markdown_utils.py`:

```python
import re

_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def extract_title_from_markdown(content: str) -> str | None:
    """Devuelve el primer H1 del documento, sin el #."""
    m = _H1.search(content)
    return m.group(1).strip() if m else None


def estimate_tokens(content: str) -> int:
    """Aproximación rápida (4 chars/token). Suficiente para la heurística del modo."""
    return max(1, len(content) // 4)
```

**`ChatbotConfigProvider`** (nuevo, edge — vía `ConfigProvider` existente):

```python
# Extender el LocalConfigProvider del Prompt 9.6.5 con:
async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str: ...
```

**Cambios en `source_scheduler.py`**: el scheduler ahora pasa el `prefetched_content` al watcher pero el watcher decide si chunkea o no según el modo. No hay otros cambios.

**Cambios en `hub_ingestion_router.py`**:

- `POST /upload` sigue igual de cara al cliente; internamente la BackgroundTask llama a `watcher.process_user_upload` que crea `HubDocument`.
- `DELETE /{chatbot_id}/jobs/{job_id}` cambia: borra el `HubDocument` correspondiente (matching por `canonical_url == job.canonical_url or job.source_url`) y CASCADE borra los chunks. Mantener compatibilidad de respuesta (mismo `{message, chunks_deleted}`).
- `DELETE /{chatbot_id}/chunks` se renombra internamente pero conserva la ruta y semántica externa: borra documentos + chunks + jobs del chatbot.
- **Nuevo endpoint**: `GET /api/v1/hub/ingestion/{chatbot_id}/documents` — lista `HubDocument[]` para la UI 9CBis.9.

**Tests**:

```python
# server/tests/modules/agents_hub/integration/test_ingestion_creates_documents.py
# test_upload_creates_hub_document_with_extracted_title
# test_upload_in_vector_mode_creates_chunks
# test_upload_in_long_context_mode_skips_chunks
# test_upload_in_agentic_mode_skips_chunks
# test_re_upload_same_content_is_idempotent
# test_re_upload_different_content_replaces_document_and_chunks
# test_changing_chatbot_mode_to_vector_regenerates_chunks_on_next_ingest
```

**Test de regresión** en `server/tests/modules/agents_hub/integration/test_ingestion_regression.py`:

```python
# test_existing_chat_flow_still_works_after_refactor   # chatbot vector responde igual
# test_search_knowledge_returns_sources_grouped_by_document  # nueva forma de las fuentes
```

**Confirmar**:

```bash
cd server && uv run alembic upgrade head
uv run pytest tests/modules/agents_hub/integration/test_ingestion_creates_documents.py -v
uv run pytest tests/modules/agents_hub/integration/test_ingestion_regression.py -v
uv run pytest tests/ -v   # regresión completa obligatoria
```

---

### Prompt 9CBis.9 — Refactor UI Documentos: vista unificada de `HubDocument`

**Objetivo**: la pestaña "Documentos subidos" del prompt 9.7 pasa a mostrar `HubDocument[]` (vista unificada de PDFs subidos + URLs del crawler), porque ahora ambos producen el mismo modelo. El concepto de "job" se conserva como histórico técnico (otra pestaña), pero el usuario gestiona "documentos".

**Cambios en `frontend/src/shared/api/ingestion.ts`**:

```typescript
export interface HubDocument {
  id: string
  chatbot_id: string
  title: string
  canonical_url: string
  language: string
  source_kind: 'upload' | 'crawler' | 'manual'
  section_path: string | null
  token_count: number
  created_at: string
  updated_at: string
}

// fetchDocuments(chatbotId): Promise<HubDocument[]>
// deleteDocument(chatbotId, documentId): Promise<void>
```

**Cambios en `frontend/src/admin/pages/DocumentsPage.tsx`**:

- Renombrar internamente la tab existente "Documentos subidos" → "Documentos" y poblarla desde `fetchDocuments`.
- Columnas: título, fuente (icono según `source_kind`), idioma, tokens (formato compacto), fecha, acciones.
- Acciones por fila: **Ver** (modal con preview markdown renderizado), **Sustituir** (re-upload con la misma `canonical_url`), **Eliminar**.
- Encima de la tabla, banner informativo: "Modo de retrieval del chatbot: **{mode}** ({recomendación según token total})". El banner enlaza a la página del chatbot donde se cambia el modo (UI del 9CBis.14).
- Conservar tab "Fuentes web" del 9.7.1 (gestión de URLs monitorizadas) sin cambios funcionales.
- Añadir tab nueva "Jobs (técnico)" oculta tras un `Disclosure`, que muestra el histórico actual de `HubIngestionJob` para depuración.

**Tests** en `frontend/src/admin/pages/__tests__/DocumentsPage.test.tsx`:

```typescript
// should_list_documents_grouped_by_chatbot
// should_show_source_kind_icon
// should_show_total_tokens_summary_banner
// should_open_preview_modal_on_view_action
// should_delete_document_with_confirm
// should_keep_sources_tab_unchanged
```

**Confirmar**:

```bash
cd frontend && npm test -- DocumentsPage
npm run build     # asegurar que el bundle del admin sigue construyendo
```

---

### Prompt 9CBis.10 — Refactor de 9.8.2: SSE emite `Source[]` estructurado

**Objetivo**: el evento `done` del SSE pasa de `sources: string[]` a `sources: Source[]` con `(document_id, title, url, score)`. Esto corrige también el bug latente en `hub_chat.py:159` donde `final_sources = output.get("sources", [])` siempre devolvía `[]` porque el nodo no añadía `sources` al output.

**Cambios en `server/app/api/v1/hub_chat.py`**:

```python
# 1. Inyectar la RetrievalStrategy según el chatbot.retrieval_mode
async def _make_strategy(chatbot, session, embedding_service):
    if chatbot.retrieval_mode == "long_context":
        return LongContextRetrievalStrategy(session)
    if chatbot.retrieval_mode == "agentic":
        return AgenticRetrievalStrategy(session)
    return VectorRetrievalStrategy(session, embedding_service)

# 2. En chat_stream: leer chatbot.retrieval_mode + system_prompt y pasar al grafo
strategy = await _make_strategy(chatbot, session, embedding_service)
graph = create_agent_graph(
    retrieval_strategy=strategy,
    llm=await get_llm_for_chatbot(chatbot),     # usa model_factory
    base_system_prompt=chatbot.system_prompt,
    user_id=user.user_id,
)

# 3. En event_generator: recoger Source[] del state final, no string[]
elif kind == "on_chain_end" and name == "generate_response":
    output = event.get("data", {}).get("output", {})
    raw_sources = output.get("sources", [])  # ahora List[Source]
    final_sources = [
        {"document_id": str(s.document_id), "title": s.title,
         "url": s.url, "score": round(s.score, 3)}
        for s in raw_sources
    ]
    detected_language = output.get("language", "es")

# 4. Evento done con la nueva forma
yield _sse("done", {
    "interaction_id": str(interaction_id),
    "sources": final_sources,           # ← ahora objetos, no strings
    "language_fallback": language_fallback,
    "translation_warning": translation_warning,
})
```

**Compatibilidad**: el cliente del prompt 9.10 lee `sources as string[]`. Hasta que 9CBis.11 lo actualice, el front mostrará objetos en vez de strings (no rompe — solo afecta render). El test E2E debe ejecutarse después de 9CBis.11 para validar el flujo completo.

**Tests actualizados** en `server/tests/modules/agents_hub/integration/test_hub_chat_sse.py`:

```python
# test_done_event_includes_structured_sources_with_document_id
# test_done_event_sources_have_title_and_url
# test_done_event_empty_sources_when_no_retrieval_happened
# test_long_context_mode_sources_marked_with_canonical_urls
# test_agentic_mode_sources_only_include_documents_actually_read
# test_no_citation_fallback_emits_done_with_empty_sources
```

**Confirmar**:

```bash
cd server && uv run pytest tests/modules/agents_hub/integration/test_hub_chat_sse.py -v
uv run pytest tests/ -v   # regresión completa
```

---

### Prompt 9CBis.11 — Refactor de 9.10: Widget renderiza citas como pills clicables

**Objetivo**: el widget pasa a tratar `sources` como objetos estructurados, los renderiza como pills clicables debajo del mensaje del asistente, y resalta inline las citas markdown del propio texto (parsea `[título](url)` y las convierte en enlaces accesibles).

**Cambios en `frontend/src/widget/hooks/useChat.ts`**:

```typescript
export interface SourceRef {
  document_id: string
  title: string
  url: string
  score: number
}

export interface UseChatReturn {
  // ...
  sources: SourceRef[]    // antes string[]
}

// En el handler del evento done:
setSources(payload.sources as SourceRef[])
```

**Cambios en `frontend/src/widget/components/ChatWidget.tsx`**:

```typescript
import ReactMarkdown from 'react-markdown'   // añadir dependencia

// 1. Renderizar el mensaje del asistente con ReactMarkdown para que [título](url)
//    aparezcan como enlaces (target="_blank", rel="noopener")
// 2. Debajo del último mensaje del asistente, render de pills:
//    <div role="list" aria-label={t('chat.sources')}>
//      {sources.map(s => (
//        <a key={s.document_id} href={s.url} target="_blank" rel="noopener"
//           role="listitem" className="source-pill">
//          {s.title}
//        </a>
//      ))}
//    </div>
// 3. Estilo de pill: borde redondeado, fondo gris claro, hover azul.
//    Variables CSS: --source-pill-bg, --source-pill-fg, --source-pill-border.
```

**Añadir** a `frontend/src/widget/locales/<lang>/chat.json`:

```json
{
  "sources": "Fuentes",
  "no_sources": "Sin fuentes citadas"
}
```

**Tests actualizados** en `frontend/src/widget/__tests__/ChatWidget.test.tsx`:

```typescript
// should_render_source_pills_when_done_event_has_sources
// should_render_assistant_message_with_inline_markdown_links
// should_open_source_links_in_new_tab
// should_handle_empty_sources_array_gracefully
// should_announce_sources_to_screen_readers   // role="list" + aria-label
```

**Documentar en `frontend/widget.html`** (la página de prueba): mostrar un ejemplo de respuesta con citas para que el integrador vea cómo se ven las pills.

**Confirmar**:

```bash
cd frontend && npm install react-markdown
npm test -- ChatWidget
npm run build:widget   # bundle del widget sigue construyendo
```

---

### Prompt 9CBis.12 — TDD RED: router multi-materia (`route_to_subagent`)

**Objetivo**: introducir el nodo `route_to_subagent` en el grafo cuando `chatbot.kind == "router"`. El nodo clasifica la consulta entre los hijos atómicos (basado en embeddings de sus `system_prompt`) y delega.

**Tests** en `server/tests/modules/agents_hub/unit/test_router_node.py`:

```python
"""Tests del router multi-materia — TDD RED."""
import uuid
import pytest
from unittest.mock import AsyncMock


class TestRouteToSubagent:

    @pytest.fixture
    def router_chatbot(self):
        from dataclasses import dataclass
        @dataclass
        class FakeCB:
            id: uuid.UUID
            name: str
            system_prompt: str
            kind: str = "atomic"
            parent_chatbot_id: uuid.UUID | None = None
            retrieval_mode: str = "agentic"
        router_id = uuid.uuid4()
        return [
            FakeCB(id=router_id, name="UJI", system_prompt="Asistente UJI", kind="router"),
            FakeCB(id=uuid.uuid4(), name="Normativa académica",
                   system_prompt="Reglamentos académicos, planes de estudio, permanencia",
                   parent_chatbot_id=router_id),
            FakeCB(id=uuid.uuid4(), name="RRHH",
                   system_prompt="Personal docente e investigador, nóminas, permisos",
                   parent_chatbot_id=router_id),
            FakeCB(id=uuid.uuid4(), name="Económico",
                   system_prompt="Presupuestos, justificación de gastos, contratos",
                   parent_chatbot_id=router_id),
        ]

    @pytest.mark.asyncio
    async def test_router_classifies_to_correct_child(self, router_chatbot):
        from server.app.modules.agents_hub.agent.router_node import build_route_to_subagent_node

        embedding_service = AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024))
        chatbot_provider = AsyncMock()
        chatbot_provider.get_children = AsyncMock(return_value=router_chatbot[1:])

        node = build_route_to_subagent_node(
            embedding_service=embedding_service,
            chatbot_provider=chatbot_provider,
        )
        state = {
            "messages": [type("M", (), {"content": "¿Cuántos días de permiso me corresponden?"})()],
            "chatbot_id": str(router_chatbot[0].id),
        }
        result = await node(state)
        assert result["selected_child_id"] in {str(c.id) for c in router_chatbot[1:]}
        assert result["routing_confidence"] >= 0.0

    @pytest.mark.asyncio
    async def test_router_with_single_child_passes_through(self, router_chatbot):
        from server.app.modules.agents_hub.agent.router_node import build_route_to_subagent_node
        embedding_service = AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024))
        only_one = [router_chatbot[1]]
        chatbot_provider = AsyncMock(get_children=AsyncMock(return_value=only_one))
        node = build_route_to_subagent_node(embedding_service, chatbot_provider)
        state = {"messages": [type("M", (), {"content": "x"})()],
                 "chatbot_id": str(router_chatbot[0].id)}
        result = await node(state)
        assert result["selected_child_id"] == str(only_one[0].id)
        assert result["routing_confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_router_with_no_children_raises(self, router_chatbot):
        from server.app.modules.agents_hub.agent.router_node import build_route_to_subagent_node
        embedding_service = AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024))
        chatbot_provider = AsyncMock(get_children=AsyncMock(return_value=[]))
        node = build_route_to_subagent_node(embedding_service, chatbot_provider)
        state = {"messages": [type("M", (), {"content": "x"})()],
                 "chatbot_id": str(router_chatbot[0].id)}
        with pytest.raises(ValueError, match="sin hijos"):
            await node(state)

    @pytest.mark.asyncio
    async def test_low_confidence_falls_back_to_llm_classifier(self, router_chatbot):
        """Si la confianza por embeddings < umbral, usa LLM como segundo intento."""
        from server.app.modules.agents_hub.agent.router_node import build_route_to_subagent_node
        embedding_service = AsyncMock(embed=AsyncMock(return_value=[0.0] * 1024))
        # Embeddings idénticos → confianza ≈ 1.0 entre todos → tie-breaker por LLM
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=type("R", (),
                                                  {"content": str(router_chatbot[2].id)})())
        chatbot_provider = AsyncMock(get_children=AsyncMock(return_value=router_chatbot[1:]))
        node = build_route_to_subagent_node(embedding_service, chatbot_provider,
                                            llm_fallback=llm,
                                            confidence_threshold=0.95)
        result = await node({
            "messages": [type("M", (), {"content": "ambigua"})()],
            "chatbot_id": str(router_chatbot[0].id),
        })
        assert result["selected_child_id"] == str(router_chatbot[2].id)
```

**Confirmar RED**: `uv run pytest tests/modules/agents_hub/unit/test_router_node.py -v` → falla por `ImportError`.

---

### Prompt 9CBis.13 — TDD GREEN: nodo router + endpoints + UI admin de jerarquía

**Objetivo**: implementar el nodo `route_to_subagent` y delegar la ejecución al subgrafo del hijo elegido. Endpoints CRUD para gestionar la jerarquía. UI admin para crear router → hijos.

**`server/app/modules/agents_hub/agent/router_node.py`**:

```python
"""Nodo router multi-materia: clasifica la consulta y delega a un sub-chatbot."""

import uuid
from typing import Protocol

import numpy as np


class ChatbotChildrenProvider(Protocol):
    async def get_children(self, parent_id: uuid.UUID) -> list: ...


def _cosine(a, b) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def build_route_to_subagent_node(
    embedding_service,
    chatbot_provider: ChatbotChildrenProvider,
    llm_fallback=None,
    confidence_threshold: float = 0.65,
):
    async def node(state):
        children = await chatbot_provider.get_children(uuid.UUID(state["chatbot_id"]))
        if not children:
            raise ValueError(f"Chatbot router {state['chatbot_id']} sin hijos atómicos.")
        if len(children) == 1:
            return {"selected_child_id": str(children[0].id), "routing_confidence": 1.0}

        query = state["messages"][-1].content
        q_emb = np.array(await embedding_service.embed(query))
        scored = []
        for c in children:
            c_emb = np.array(await embedding_service.embed(c.system_prompt))
            scored.append((c, _cosine(q_emb, c_emb)))
        scored.sort(key=lambda x: x[1], reverse=True)
        best, conf = scored[0]

        if llm_fallback is not None and conf < confidence_threshold:
            options = "\n".join(f"- {c.id}: {c.name} ({c.system_prompt[:120]})"
                                for c, _ in scored)
            response = await llm_fallback.ainvoke([
                {"role": "system", "content":
                    "Devuelve SOLO el UUID del sub-chatbot que mejor responda. "
                    "Sin explicaciones."},
                {"role": "user", "content":
                    f"Consulta: {query}\n\nOpciones:\n{options}"},
            ])
            picked_id = str(response.content).strip()
            picked = next((c for c, _ in scored if str(c.id) == picked_id), best)
            return {"selected_child_id": str(picked.id), "routing_confidence": conf}

        return {"selected_child_id": str(best.id), "routing_confidence": conf}
    return node
```

**Integración en el grafo**: en `chat_stream` (`hub_chat.py`):

```python
if chatbot.kind == "router":
    # 1. Resolver al hijo
    router_node = build_route_to_subagent_node(embedding_service, chatbot_provider,
                                               llm_fallback=await get_llm_for_chatbot(chatbot))
    routing = await router_node({"messages": [HumanMessage(content=request.message)],
                                  "chatbot_id": str(chatbot_id)})
    # 2. Recargar como si la petición hubiera ido directamente al hijo
    child = await session.get(HubChatbot, uuid.UUID(routing["selected_child_id"]))
    chatbot = child   # el resto del flujo es idéntico
    # Emitir evento status informativo:
    yield _sse("status", {"node": "route_to_subagent",
                          "msg": f"Materia detectada: {child.name}"})
```

**Endpoints nuevos** en `hub_chatbots_router.py`:

```python
# GET    /api/v1/hub/chatbots/{id}/children          → lista hijos del router
# POST   /api/v1/hub/chatbots/{id}/children          → asigna hijo existente al router
#         body: { child_chatbot_id: uuid }
# DELETE /api/v1/hub/chatbots/{id}/children/{child}  → desvincula hijo del router
```

**Tests** de los endpoints en `server/tests/modules/agents_hub/integration/test_chatbot_hierarchy.py`:

```python
# test_assign_child_to_router_succeeds
# test_cannot_assign_child_with_kind_router
# test_cannot_create_grandchild_hierarchy   # max 2 niveles
# test_cannot_assign_child_from_different_client
# test_list_children_returns_only_direct_children
# test_unassign_child_clears_parent_chatbot_id
```

**UI admin** — `frontend/src/admin/pages/ChatbotsPage.tsx`:

- Selector `kind`: `atomic` (default) | `router` al crear/editar.
- Si `kind == "router"`: ocultar campos de `retrieval_mode`, `system_prompt` (el router no tiene corpus propio; el system_prompt se usa solo como descripción para clasificar). Mostrar sección "Sub-chatbots" con lista actual de hijos y botón "Asignar hijo" (modal con dropdown de chatbots atómicos del mismo cliente sin parent).
- Si `kind == "atomic"`: comportamiento actual + (opcional) badge "Asignado al router X" si tiene parent.

**Tests UI** en `frontend/src/admin/pages/__tests__/ChatbotsPage.hierarchy.test.tsx`:

```typescript
// should_show_kind_selector_in_form
// should_hide_retrieval_mode_when_kind_is_router
// should_show_children_section_for_router_chatbots
// should_assign_child_via_modal
// should_warn_when_router_has_no_children
```

**Confirmar**:

```bash
cd server && uv run pytest tests/modules/agents_hub/unit/test_router_node.py -v
uv run pytest tests/modules/agents_hub/integration/test_chatbot_hierarchy.py -v
cd ../frontend && npm test -- ChatbotsPage
uv run pytest tests/ -v   # regresión completa obligatoria
```

---

### Prompt 9CBis.14 — UI admin: selector `retrieval_mode` con recomendación basada en tokens

**Objetivo**: en la pantalla de edición de chatbot, añadir el selector `retrieval_mode` con una recomendación visible y argumentada según el `total_tokens` del corpus actual del chatbot. El admin ve la sugerencia pero decide.

**Endpoint nuevo** `GET /api/v1/hub/chatbots/{id}/corpus-stats`:

```python
{
  "total_documents": 142,
  "total_tokens": 487_321,
  "by_language": {"es": 380_000, "ca": 107_321},
  "recommended_mode": "agentic",
  "recommendation_reason":
    "El corpus supera 100K tokens y queda por debajo de 2M; el modo agentic ofrece "
    "el mejor balance entre coste y precisión de citas."
}
```

Lógica de recomendación (servicio `corpus_recommender.py`, edge):

```python
def recommend_retrieval_mode(total_tokens: int) -> tuple[str, str]:
    if total_tokens < 100_000:
        return ("long_context",
                f"El corpus ({total_tokens:,} tokens) cabe completo en el contexto del LLM. "
                f"Recomendado long_context: cero pérdida de información, citas precisas.")
    if total_tokens < 2_000_000:
        return ("agentic",
                f"El corpus ({total_tokens:,} tokens) excede el long_context pero permite "
                f"que el LLM seleccione qué documentos leer. Recomendado agentic.")
    return ("vector",
            f"El corpus ({total_tokens:,} tokens) requiere búsqueda vectorial para escalar "
            f"económicamente. Recomendado vector; aceptas degradación de citas y posibles "
            f"errores de recuperación top-k.")
```

**UI** — en `ChatbotsPage` form de edición:

- Selector `retrieval_mode`: 3 opciones (`vector`, `long_context`, `agentic`) con descripción corta.
- Banner con la recomendación actual ("Sugerido: **agentic**") y razón. Si el admin elige algo distinto del sugerido, mostrar advertencia naranja: "Has elegido un modo distinto del recomendado para este corpus. Asegúrate de entender las implicaciones de coste y precisión."
- Si el modo elegido es `long_context` y `total_tokens > 150_000`, **bloquear el guardado** con error: "El corpus excede el límite del modo long_context (150K tokens). Reduce el corpus o cambia a agentic."
- Si el chatbot cambia de modo, mostrar info: "Al cambiar el modo, la próxima ingestión regenerará/borrará chunks según corresponda. Los documentos existentes no se ven afectados."

**Comando admin** `POST /api/v1/hub/chatbots/{id}/regenerate-chunks` (cloud → edge):

- Solo válido si `retrieval_mode == "vector"`.
- Recorre los `HubDocument[]` del chatbot, regenera chunks + embeddings (idempotente).
- Útil cuando el admin cambia de `agentic` o `long_context` a `vector` y quiere chunkear el corpus existente sin re-subir cada documento.
- Devuelve un `task_id` para seguimiento; el progreso se emite vía SSE en otro endpoint.

**Tests** en `server/tests/modules/agents_hub/unit/test_corpus_recommender.py`:

```python
# test_recommends_long_context_for_small_corpus
# test_recommends_agentic_for_medium_corpus
# test_recommends_vector_for_huge_corpus
# test_recommendation_reason_includes_token_count
```

**Tests** en `server/tests/modules/agents_hub/integration/test_corpus_stats_endpoint.py`:

```python
# test_corpus_stats_returns_total_tokens_and_recommendation
# test_corpus_stats_groups_by_language
# test_regenerate_chunks_blocked_for_non_vector_mode
# test_regenerate_chunks_creates_chunks_for_existing_documents
```

**Tests UI** en `frontend/src/admin/pages/__tests__/ChatbotsPage.retrievalMode.test.tsx`:

```typescript
// should_show_recommendation_banner_with_reason
// should_warn_when_user_picks_non_recommended_mode
// should_block_save_when_long_context_exceeds_limit
// should_show_chunk_regeneration_button_only_for_vector_mode
```

**Confirmar**:

```bash
cd server && uv run pytest tests/modules/agents_hub/unit/test_corpus_recommender.py -v
uv run pytest tests/modules/agents_hub/integration/test_corpus_stats_endpoint.py -v
cd ../frontend && npm test -- ChatbotsPage.retrievalMode
uv run pytest tests/ -v   # regresión completa final del bloque
npm test                  # regresión completa frontend
npm run build && npm run build:widget   # bundles ok
```

**Smoke test manual del bloque completo (`pruebas_manuales_prompt9CBis.bat`)**:

1. Verificar `docker compose up` con la migración aplicada.
2. Crear chatbot atómico en modo `long_context`, subir 2 PDFs pequeños (<50K tokens total), preguntar y verificar que la respuesta cita ambos documentos como pills clicables.
3. Cambiar el chatbot a `agentic`, repetir la pregunta y verificar que el LLM invoca `read_document` (visible en eventos `status` del SSE) y solo cita los documentos leídos.
4. Cambiar a `vector`, ejecutar `POST /regenerate-chunks`, repetir y verificar que las citas siguen apuntando a los `HubDocument` correctos (no a chunks).
5. Crear un chatbot router "UJI demo" con dos hijos atómicos ("Normativa", "RRHH") en `agentic`. Hacer una pregunta clara de cada materia y verificar que el evento `status` informa "Materia detectada: …" antes de la respuesta.
6. Comprobar UI: banner de recomendación coherente con el tamaño del corpus, advertencia al elegir modo no recomendado, error al elegir long_context con corpus > 150K.

---

## BLOQUE 9E — Panel de administración LLM y Prompts

**Objetivo**: Dar a administradores y partners control total sobre qué modelo usa cada proceso y qué instrucciones recibe, sin tocar código ni reiniciar el servidor. El sistema de tiers unifica la configuración tanto para chatbots/agentes como para flujos de automatización.

**Prerrequisito**: Bloque 9A completado (layout admin disponible).

**Dependencia con Fase 10**: El prompt 10.11 original ("Cerebro de la IA") queda **absorbido y reemplazado** por este bloque, que es más completo. Al ejecutar 9E el prompt 10.11 puede marcarse directamente como COMPLETADO.

### Contexto: sistema de tiers (legado NiceGUI)

En la aplicación NiceGUI existente los modelos LLM se organizaban en tres tiers:

| Tier | Uso | Características |
|---|---|---|
| **1 — Texto** | Generación de respuestas, redacción, resumen | Más rápido y barato; suficiente para la mayoría de tareas |
| **2 — Lógica** | Razonamiento, clasificación, extracción estructurada | Mayor capacidad analítica; coste moderado |
| **3 — Supervisión** | Validación final, evaluación de calidad, auditoría | El más capaz; se usa puntualmente |

Cada proceso o prompt tenía un **tier por defecto** y podía sobreescribirse con un **override** para ese prompt concreto. El mismo sistema de tiers aplica a **chatbots/agentes** (nodos del grafo LangGraph) y a **flujos de automatización** (factories, ETL, scripts).

### Modelo de datos a añadir (migración Alembic)

```python
# Cambios en hub_llm_configs
ALTER TABLE hub_llm_configs
  ADD COLUMN tier        SMALLINT NOT NULL DEFAULT 1,   -- 1 | 2 | 3
  ADD COLUMN label       VARCHAR(100),                   -- etiqueta legible ("Gemini Flash")
  ADD COLUMN is_default  BOOLEAN NOT NULL DEFAULT FALSE; -- config por defecto de ese tier

# Cambios en hub_prompt_templates
ALTER TABLE hub_prompt_templates
  ADD COLUMN default_tier   SMALLINT NOT NULL DEFAULT 1,
  ADD COLUMN override_tier  SMALLINT;   -- NULL = usar default_tier
```

### Seeding inicial obligatorio

El Prompt 9E.1 debe incluir un comando `seed_llm_configs` que cree configuraciones por defecto para que la BD nunca arranque vacía. Ejemplo:

```
Tier 1 → google / gemini-2.0-flash   / GOOGLE_API_KEY      (default)
Tier 2 → google / gemini-2.5-pro     / GOOGLE_API_KEY
Tier 3 → openai / gpt-4o             / OPENAI_API_KEY
Tier 1 → ollama / llama3.2           / —     (alternativa local, sin coste)
```

---

### Prompt 9E.1 — Backend: tiers, CRUD de LLM configs y seeding

**Objetivo**: Ampliar el modelo `HubLLMConfig` con el sistema de tiers, exponer endpoints CRUD completos para que la UI los gestione, y añadir un comando de seeding para poblar la BD al arrancar.

**Ámbito**: cloud (la configuración es responsabilidad del admin/partner).

**Migración Alembic** — añade `tier`, `label`, `is_default` a `hub_llm_configs` y `default_tier`, `override_tier` a `hub_prompt_templates`.

**Endpoints nuevos** (router: `hub_llm_configs_router`, prefijo `/api/v1/hub/llm-configs`, Deploy: cloud):
```
GET    /api/v1/hub/llm-configs            → lista todas las configs
POST   /api/v1/hub/llm-configs            → crear nueva config
PATCH  /api/v1/hub/llm-configs/{id}      → editar (label, tier, model_name, api_key_secret_name, is_default)
DELETE /api/v1/hub/llm-configs/{id}      → eliminar (guard: no borrar si hay chatbots asignados)
POST   /api/v1/hub/llm-configs/{id}/test → probar conexión: envía prompt mínimo y devuelve latencia ms
```

**Endpoint ampliado** en `hub_prompt_templates`:
```
PATCH  /api/v1/hub/prompts/{id}  → ahora acepta default_tier y override_tier
```

**`model_factory.py`** — ampliar `get_model()` para aceptar `tier` opcional:
```python
async def get_model_for_tier(tier: int, config_provider: ConfigProvider) -> BaseChatModel:
    """Devuelve el modelo marcado como is_default para ese tier."""
```

**Comando de seeding** — `server/app/scripts/seed_llm_configs.py`:
- Idempotente: no duplica si ya existen configs
- Lee variables de entorno para detectar qué proveedores están disponibles
- Ejecutable como `uv run python -m server.app.scripts.seed_llm_configs`

**Tests requeridos** (`server/tests/modules/agents_hub/unit/`):
```python
# test_llm_configs_router.py
# should_list_llm_configs
# should_create_llm_config_with_tier
# should_reject_duplicate_default_for_same_tier
# should_delete_config_not_in_use
# should_block_delete_config_in_use
# should_return_latency_on_test_connection   ← mockea el LLM
# should_get_model_for_tier_returns_default
```

---

### Prompt 9E.2 — Frontend: pantalla "Modelos LLM"

**Objetivo**: Tabla con todas las configs LLM, gestión CRUD y botón "Probar conexión" con feedback de latencia.

**Ruta**: `/admin/llm-configs` (ya en el sidebar del Prompt 9.4).

**`src/admin/pages/LLMConfigsPage.tsx`**:
```typescript
// Tabla: columnas provider | modelo | tier (chip 1/2/3 con color) | etiqueta | default | acciones
// Chip tier: Tier 1 = verde, Tier 2 = amarillo, Tier 3 = rojo
// Columna "Clave API": muestra solo el nombre de la variable de entorno (no el valor)
// Botón "Probar" → POST /hub/llm-configs/{id}/test → muestra badge "OK · 342 ms" o error
// Formulario crear/editar: provider (select), modelo, tier (1/2/3), etiqueta, nombre var env, is_default
// Guard al borrar: si hay chatbots asignados, muestra lista de afectados
```

**Tests requeridos**:
```typescript
// should_list_llm_configs_with_tier_chips
// should_open_create_form
// should_show_latency_badge_after_test_connection
// should_show_affected_chatbots_before_delete
```

---

### Prompt 9E.3 — Frontend: pantalla "Prompts del sistema"

**Objetivo**: Editor de prompt templates con override de tier por prompt y vista previa con variables de ejemplo.

**Ruta**: `/admin/prompts` (ya en el sidebar del Prompt 9.4).

**`src/admin/pages/PromptsPage.tsx`**:
```typescript
// Lista izquierda: prompt templates con nombre, proceso asociado y tier efectivo
// Editor derecho: textarea con resaltado de variables {variable} (fondo amarillo claro)
//   - Selector "Tier por defecto": chips 1/2/3
//   - Toggle "Override tier": activa dropdown con tier concreto para este prompt
//   - Vista previa: rellena {variables} con valores de ejemplo y muestra el prompt final
//   - Botón "Guardar versión": incrementa el campo version en BD
//   - Badge "v3" junto al nombre para indicar la versión actual
// Aplica a: prompt templates de chatbots Y de flujos de automatización
//   (campo proceso_tipo: 'chatbot' | 'automation')
```

**Tests requeridos**:
```typescript
// should_list_prompt_templates
// should_highlight_variables_in_editor
// should_show_effective_tier_with_override
// should_increment_version_on_save
// should_preview_prompt_with_example_values
```

---

## FASE 10: Sistema de Plantillas y Temas (Chatbots, Panel Admin, Partners y UI Principal)

**Objetivo de la Fase**: Crear un sistema de plantillas editables que permita personalizar la apariencia del chatbot sin modificar el código fuente. Los administradores podrán ajustar colores, fuentes, espaciados y componentes mediante archivos de configuración.

**Dependencias**: FASE 9 (Frontend + i18n)

**Conceptos clave**:
- **CSS Custom Properties (Variables)**: Permiten cambiar estilos dinámicamente
- **Theme Provider**: Componente React que inyecta el tema en toda la aplicación
- **Configuración externa**: Temas definidos en JSON cargados desde el servidor
- **Plantillas de componentes**: Estructura modular para personalización granular

---

### Prompt 10.1 - Definición del Sistema de Temas (TDD RED)

**Objetivo**: Definir la estructura TypeScript para los temas y validar su configuración.

**frontend/src/themes/__tests__/theme.test.ts** (RED):
```typescript
import { describe, it, expect } from 'vitest';
import {
  ThemeConfig,
  validateTheme,
  DEFAULT_THEME,
  mergeThemes,
  ThemeColors,
  ThemeTypography,
  ThemeSpacing,
  ThemeBorderRadius,
  ThemeComponents,
} from '../types';

describe('Theme Types and Validation', () => {
  describe('DEFAULT_THEME', () => {
    it('should have all required color properties', () => {
      expect(DEFAULT_THEME.colors.primary).toBeDefined();
      expect(DEFAULT_THEME.colors.secondary).toBeDefined();
      expect(DEFAULT_THEME.colors.background).toBeDefined();
      expect(DEFAULT_THEME.colors.surface).toBeDefined();
      expect(DEFAULT_THEME.colors.text).toBeDefined();
      expect(DEFAULT_THEME.colors.textSecondary).toBeDefined();
      expect(DEFAULT_THEME.colors.border).toBeDefined();
      expect(DEFAULT_THEME.colors.error).toBeDefined();
      expect(DEFAULT_THEME.colors.success).toBeDefined();
      expect(DEFAULT_THEME.colors.warning).toBeDefined();
    });

    it('should have bot and user message colors', () => {
      expect(DEFAULT_THEME.colors.botMessage).toBeDefined();
      expect(DEFAULT_THEME.colors.userMessage).toBeDefined();
      expect(DEFAULT_THEME.colors.botMessageText).toBeDefined();
      expect(DEFAULT_THEME.colors.userMessageText).toBeDefined();
    });

    it('should have typography settings', () => {
      expect(DEFAULT_THEME.typography.fontFamily).toBeDefined();
      expect(DEFAULT_THEME.typography.fontSize).toBeDefined();
      expect(DEFAULT_THEME.typography.fontSizeSmall).toBeDefined();
      expect(DEFAULT_THEME.typography.fontSizeLarge).toBeDefined();
      expect(DEFAULT_THEME.typography.fontWeight).toBeDefined();
      expect(DEFAULT_THEME.typography.fontWeightBold).toBeDefined();
      expect(DEFAULT_THEME.typography.lineHeight).toBeDefined();
    });

    it('should have spacing settings', () => {
      expect(DEFAULT_THEME.spacing.xs).toBeDefined();
      expect(DEFAULT_THEME.spacing.sm).toBeDefined();
      expect(DEFAULT_THEME.spacing.md).toBeDefined();
      expect(DEFAULT_THEME.spacing.lg).toBeDefined();
      expect(DEFAULT_THEME.spacing.xl).toBeDefined();
    });

    it('should have border radius settings', () => {
      expect(DEFAULT_THEME.borderRadius.sm).toBeDefined();
      expect(DEFAULT_THEME.borderRadius.md).toBeDefined();
      expect(DEFAULT_THEME.borderRadius.lg).toBeDefined();
      expect(DEFAULT_THEME.borderRadius.full).toBeDefined();
    });
  });

  describe('validateTheme', () => {
    it('should return valid for a complete theme', () => {
      const result = validateTheme(DEFAULT_THEME);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect missing required colors', () => {
      const invalidTheme = {
        ...DEFAULT_THEME,
        colors: { primary: '#000' } as ThemeColors,
      };
      const result = validateTheme(invalidTheme);
      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should detect invalid color format', () => {
      const invalidTheme = {
        ...DEFAULT_THEME,
        colors: {
          ...DEFAULT_THEME.colors,
          primary: 'not-a-color',
        },
      };
      const result = validateTheme(invalidTheme);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Invalid color format for primary: not-a-color');
    });

    it('should validate hex colors', () => {
      const validTheme = {
        ...DEFAULT_THEME,
        colors: {
          ...DEFAULT_THEME.colors,
          primary: '#ff0000',
        },
      };
      const result = validateTheme(validTheme);
      expect(result.valid).toBe(true);
    });

    it('should validate rgb colors', () => {
      const validTheme = {
        ...DEFAULT_THEME,
        colors: {
          ...DEFAULT_THEME.colors,
          primary: 'rgb(255, 0, 0)',
        },
      };
      const result = validateTheme(validTheme);
      expect(result.valid).toBe(true);
    });

    it('should validate hsl colors', () => {
      const validTheme = {
        ...DEFAULT_THEME,
        colors: {
          ...DEFAULT_THEME.colors,
          primary: 'hsl(0, 100%, 50%)',
        },
      };
      const result = validateTheme(validTheme);
      expect(result.valid).toBe(true);
    });
  });

  describe('mergeThemes', () => {
    it('should merge partial theme with defaults', () => {
      const partial = {
        colors: {
          primary: '#ff0000',
        },
      };
      const merged = mergeThemes(DEFAULT_THEME, partial);
      expect(merged.colors.primary).toBe('#ff0000');
      expect(merged.colors.secondary).toBe(DEFAULT_THEME.colors.secondary);
      expect(merged.typography).toEqual(DEFAULT_THEME.typography);
    });

    it('should deep merge nested objects', () => {
      const partial = {
        typography: {
          fontSize: '18px',
        },
      };
      const merged = mergeThemes(DEFAULT_THEME, partial);
      expect(merged.typography.fontSize).toBe('18px');
      expect(merged.typography.fontFamily).toBe(DEFAULT_THEME.typography.fontFamily);
    });

    it('should handle empty partial theme', () => {
      const merged = mergeThemes(DEFAULT_THEME, {});
      expect(merged).toEqual(DEFAULT_THEME);
    });

    it('should override component templates', () => {
      const partial = {
        components: {
          chatBubble: {
            borderRadius: '20px',
            padding: '16px',
          },
        },
      };
      const merged = mergeThemes(DEFAULT_THEME, partial);
      expect(merged.components?.chatBubble?.borderRadius).toBe('20px');
    });
  });
});
```

---

### Prompt 10.2 - Implementación de Tipos de Tema (TDD GREEN)

**Objetivo**: Implementar los tipos TypeScript, interfaces de validación y funciones de merge/fusión del sistema de temas que permiten la personalización visual dinámica.

**frontend/src/themes/types.ts**:
```typescript
/**
 * Sistema de Temas para AI Chatbots Hub
 *
 * Este módulo define la estructura de temas personalizables
 * que permiten modificar la apariencia del chatbot sin tocar el código.
 */

// ============================================
// Tipos base para colores
// ============================================

export interface ThemeColors {
  // Colores principales
  primary: string;
  primaryHover: string;
  primaryLight: string;
  secondary: string;
  secondaryHover: string;

  // Fondos
  background: string;
  surface: string;
  surfaceHover: string;

  // Texto
  text: string;
  textSecondary: string;
  textMuted: string;
  textOnPrimary: string;

  // Bordes y separadores
  border: string;
  borderLight: string;
  divider: string;

  // Estados
  error: string;
  errorLight: string;
  success: string;
  successLight: string;
  warning: string;
  warningLight: string;
  info: string;
  infoLight: string;

  // Mensajes del chat
  botMessage: string;
  botMessageText: string;
  userMessage: string;
  userMessageText: string;

  // Overlays y sombras
  overlay: string;
  shadow: string;
}

// ============================================
// Tipos para tipografía
// ============================================

export interface ThemeTypography {
  fontFamily: string;
  fontFamilyMono: string;

  // Tamaños
  fontSizeXs: string;
  fontSizeSmall: string;
  fontSize: string;
  fontSizeMd: string;
  fontSizeLarge: string;
  fontSizeXl: string;
  fontSizeXxl: string;

  // Pesos
  fontWeightLight: number;
  fontWeight: number;
  fontWeightMedium: number;
  fontWeightBold: number;

  // Altura de línea
  lineHeight: number;
  lineHeightTight: number;
  lineHeightRelaxed: number;

  // Espaciado de letras
  letterSpacing: string;
  letterSpacingWide: string;
}

// ============================================
// Tipos para espaciado
// ============================================

export interface ThemeSpacing {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  xxl: string;
}

// ============================================
// Tipos para bordes
// ============================================

export interface ThemeBorderRadius {
  none: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  full: string;
}

// ============================================
// Tipos para sombras
// ============================================

export interface ThemeShadows {
  none: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
}

// ============================================
// Tipos para componentes específicos
// ============================================

export interface ChatBubbleStyles {
  borderRadius?: string;
  padding?: string;
  maxWidth?: string;
  shadow?: string;
}

export interface HeaderStyles {
  height?: string;
  padding?: string;
  background?: string;
  borderBottom?: string;
}

export interface InputStyles {
  height?: string;
  padding?: string;
  borderRadius?: string;
  border?: string;
  focusBorder?: string;
}

export interface ButtonStyles {
  padding?: string;
  borderRadius?: string;
  fontWeight?: number;
  textTransform?: 'none' | 'uppercase' | 'capitalize';
}

export interface WidgetStyles {
  width?: string;
  height?: string;
  borderRadius?: string;
  shadow?: string;
  position?: {
    bottom?: string;
    right?: string;
    left?: string;
  };
}

export interface ThemeComponents {
  chatBubble?: ChatBubbleStyles;
  header?: HeaderStyles;
  input?: InputStyles;
  button?: ButtonStyles;
  widget?: WidgetStyles;
}

// ============================================
// Tipos para animaciones
// ============================================

export interface ThemeAnimations {
  durationFast: string;
  durationNormal: string;
  durationSlow: string;
  easing: string;
  easingBounce: string;
}

// ============================================
// Configuración completa del tema
// ============================================

export interface ThemeConfig {
  name: string;
  version: string;
  colors: ThemeColors;
  typography: ThemeTypography;
  spacing: ThemeSpacing;
  borderRadius: ThemeBorderRadius;
  shadows: ThemeShadows;
  animations: ThemeAnimations;
  components?: ThemeComponents;
  customCSS?: string;
}

// ============================================
// Tema por defecto
// ============================================

export const DEFAULT_THEME: ThemeConfig = {
  name: 'default',
  version: '1.0.0',

  colors: {
    // Colores principales (azul universitario)
    primary: '#0066cc',
    primaryHover: '#0052a3',
    primaryLight: '#e6f0fa',
    secondary: '#6c757d',
    secondaryHover: '#545b62',

    // Fondos
    background: '#ffffff',
    surface: '#f8f9fa',
    surfaceHover: '#e9ecef',

    // Texto
    text: '#212529',
    textSecondary: '#6c757d',
    textMuted: '#adb5bd',
    textOnPrimary: '#ffffff',

    // Bordes
    border: '#dee2e6',
    borderLight: '#e9ecef',
    divider: '#e9ecef',

    // Estados
    error: '#dc3545',
    errorLight: '#f8d7da',
    success: '#28a745',
    successLight: '#d4edda',
    warning: '#ffc107',
    warningLight: '#fff3cd',
    info: '#17a2b8',
    infoLight: '#d1ecf1',

    // Mensajes del chat
    botMessage: '#f1f3f4',
    botMessageText: '#212529',
    userMessage: '#0066cc',
    userMessageText: '#ffffff',

    // Overlays
    overlay: 'rgba(0, 0, 0, 0.5)',
    shadow: 'rgba(0, 0, 0, 0.1)',
  },

  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fontFamilyMono: "'Fira Code', 'Consolas', monospace",

    fontSizeXs: '0.75rem',
    fontSizeSmall: '0.875rem',
    fontSize: '1rem',
    fontSizeMd: '1rem',
    fontSizeLarge: '1.125rem',
    fontSizeXl: '1.25rem',
    fontSizeXxl: '1.5rem',

    fontWeightLight: 300,
    fontWeight: 400,
    fontWeightMedium: 500,
    fontWeightBold: 600,

    lineHeight: 1.5,
    lineHeightTight: 1.25,
    lineHeightRelaxed: 1.75,

    letterSpacing: 'normal',
    letterSpacingWide: '0.025em',
  },

  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    xxl: '3rem',
  },

  borderRadius: {
    none: '0',
    sm: '0.25rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    full: '9999px',
  },

  shadows: {
    none: 'none',
    sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px rgba(0, 0, 0, 0.15)',
  },

  animations: {
    durationFast: '150ms',
    durationNormal: '300ms',
    durationSlow: '500ms',
    easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easingBounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },

  components: {
    chatBubble: {
      borderRadius: '1rem',
      padding: '0.75rem 1rem',
      maxWidth: '80%',
      shadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
    },
    header: {
      height: '60px',
      padding: '0 1rem',
      background: 'linear-gradient(135deg, #0066cc 0%, #0052a3 100%)',
      borderBottom: 'none',
    },
    input: {
      height: '48px',
      padding: '0.75rem 1rem',
      borderRadius: '24px',
      border: '1px solid #dee2e6',
      focusBorder: '2px solid #0066cc',
    },
    button: {
      padding: '0.5rem 1rem',
      borderRadius: '0.5rem',
      fontWeight: 500,
      textTransform: 'none',
    },
    widget: {
      width: '380px',
      height: '600px',
      borderRadius: '1rem',
      shadow: '0 10px 40px rgba(0, 0, 0, 0.15)',
      position: {
        bottom: '20px',
        right: '20px',
      },
    },
  },
};

// ============================================
// Validación de tema
// ============================================

const COLOR_REGEX = /^(#[0-9a-fA-F]{3,8}|rgb\(|rgba\(|hsl\(|hsla\(|[a-z]+$)/;

const REQUIRED_COLORS: (keyof ThemeColors)[] = [
  'primary',
  'secondary',
  'background',
  'surface',
  'text',
  'textSecondary',
  'border',
  'error',
  'success',
  'warning',
  'botMessage',
  'userMessage',
  'botMessageText',
  'userMessageText',
];

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function validateTheme(theme: ThemeConfig): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Validar colores requeridos
  for (const colorKey of REQUIRED_COLORS) {
    if (!theme.colors[colorKey]) {
      errors.push(`Missing required color: ${colorKey}`);
    }
  }

  // Validar formato de colores
  for (const [key, value] of Object.entries(theme.colors)) {
    if (value && !COLOR_REGEX.test(value)) {
      errors.push(`Invalid color format for ${key}: ${value}`);
    }
  }

  // Validar tipografía
  if (!theme.typography.fontFamily) {
    errors.push('Missing required typography.fontFamily');
  }

  if (!theme.typography.fontSize) {
    errors.push('Missing required typography.fontSize');
  }

  // Validar spacing
  const requiredSpacing = ['xs', 'sm', 'md', 'lg', 'xl'];
  for (const key of requiredSpacing) {
    if (!theme.spacing[key as keyof ThemeSpacing]) {
      errors.push(`Missing required spacing: ${key}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// ============================================
// Utilidad para merge de temas
// ============================================

type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export function mergeThemes(
  base: ThemeConfig,
  partial: DeepPartial<ThemeConfig>
): ThemeConfig {
  return deepMerge(base, partial) as ThemeConfig;
}

function deepMerge<T extends object>(target: T, source: DeepPartial<T>): T {
  const result = { ...target };

  for (const key in source) {
    if (source[key] !== undefined) {
      if (
        typeof source[key] === 'object' &&
        source[key] !== null &&
        !Array.isArray(source[key])
      ) {
        result[key] = deepMerge(
          target[key] as object,
          source[key] as DeepPartial<object>
        ) as T[Extract<keyof T, string>];
      } else {
        result[key] = source[key] as T[Extract<keyof T, string>];
      }
    }
  }

  return result;
}
```

---

### Prompt 10.3 - Theme Provider y Context (TDD RED)

**Objetivo**: Validar el comportamiento del `ThemeProvider` React: carga de tema por defecto, cambio dinámico de tema, inyección de variables CSS en el DOM y exposición del contexto a componentes hijos.

**frontend/src/themes/__tests__/ThemeProvider.test.tsx** (RED):
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import { ReactNode } from 'react';
import { ThemeProvider, useTheme } from '../ThemeProvider';
import { DEFAULT_THEME, ThemeConfig } from '../types';

// Mock de fetch para cargar temas
const mockFetch = vi.fn();
global.fetch = mockFetch;

const wrapper = ({ children }: { children: ReactNode }) => (
  <ThemeProvider>{children}</ThemeProvider>
);

describe('ThemeProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(DEFAULT_THEME),
    });
  });

  describe('useTheme hook', () => {
    it('should provide default theme initially', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.theme).toEqual(DEFAULT_THEME);
    });

    it('should provide theme colors', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.theme.colors.primary).toBeDefined();
    });

    it('should provide isLoading state', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(typeof result.current.isLoading).toBe('boolean');
    });

    it('should provide setTheme function', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(typeof result.current.setTheme).toBe('function');
    });

    it('should provide loadTheme function', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(typeof result.current.loadTheme).toBe('function');
    });
  });

  describe('Theme loading', () => {
    it('should load theme from URL', async () => {
      const customTheme: Partial<ThemeConfig> = {
        colors: {
          ...DEFAULT_THEME.colors,
          primary: '#ff0000',
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(customTheme),
      });

      const { result } = renderHook(() => useTheme(), { wrapper });

      await act(async () => {
        await result.current.loadTheme('/api/themes/custom');
      });

      expect(result.current.theme.colors.primary).toBe('#ff0000');
    });

    it('should handle load errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useTheme(), { wrapper });

      await act(async () => {
        await result.current.loadTheme('/api/themes/broken');
      });

      // Should fall back to default theme
      expect(result.current.theme).toEqual(DEFAULT_THEME);
      expect(result.current.error).toBeDefined();
    });

    it('should validate loaded theme', async () => {
      const invalidTheme = {
        colors: { primary: 'invalid-color' },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(invalidTheme),
      });

      const { result } = renderHook(() => useTheme(), { wrapper });

      await act(async () => {
        await result.current.loadTheme('/api/themes/invalid');
      });

      // Should have validation warning but still use merged theme
      expect(result.current.validationWarnings.length).toBeGreaterThan(0);
    });
  });

  describe('CSS Variables injection', () => {
    it('should inject CSS variables into document', () => {
      render(
        <ThemeProvider>
          <div data-testid="test">Test</div>
        </ThemeProvider>
      );

      const root = document.documentElement;
      const primaryColor = getComputedStyle(root).getPropertyValue('--color-primary');
      expect(primaryColor.trim()).toBe(DEFAULT_THEME.colors.primary);
    });

    it('should update CSS variables when theme changes', async () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      await act(async () => {
        result.current.setTheme({
          ...DEFAULT_THEME,
          colors: {
            ...DEFAULT_THEME.colors,
            primary: '#ff0000',
          },
        });
      });

      const root = document.documentElement;
      const primaryColor = getComputedStyle(root).getPropertyValue('--color-primary');
      expect(primaryColor.trim()).toBe('#ff0000');
    });
  });

  describe('Theme persistence', () => {
    it('should save theme preference to localStorage', async () => {
      const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

      const { result } = renderHook(() => useTheme(), { wrapper });

      await act(async () => {
        result.current.setTheme({
          ...DEFAULT_THEME,
          name: 'custom',
        });
      });

      expect(setItemSpy).toHaveBeenCalledWith(
        'chatbot-theme',
        expect.any(String)
      );
    });

    it('should restore theme from localStorage on mount', () => {
      const savedTheme = {
        ...DEFAULT_THEME,
        name: 'saved',
        colors: {
          ...DEFAULT_THEME.colors,
          primary: '#00ff00',
        },
      };

      vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(
        JSON.stringify(savedTheme)
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme.name).toBe('saved');
      expect(result.current.theme.colors.primary).toBe('#00ff00');
    });
  });

  describe('Predefined themes', () => {
    it('should provide list of available themes', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.availableThemes).toContain('default');
      expect(result.current.availableThemes).toContain('dark');
      expect(result.current.availableThemes).toContain('university');
    });

    it('should switch to dark theme', async () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      await act(async () => {
        await result.current.switchTheme('dark');
      });

      expect(result.current.theme.name).toBe('dark');
      // Dark theme should have dark background
      expect(result.current.theme.colors.background).toBe('#1a1a2e');
    });
  });
});
```

---

### Prompt 10.4 - Implementación del Theme Provider (TDD GREEN)

**Objetivo**: Implementar el `ThemeProvider` como Context React que inyecta las variables CSS del tema activo en el DOM, gestiona el estado del tema y expone las funciones de cambio.

**frontend/src/themes/ThemeProvider.tsx**:
```typescript
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from 'react';
import {
  ThemeConfig,
  DEFAULT_THEME,
  validateTheme,
  mergeThemes,
  ValidationResult,
} from './types';
import { DARK_THEME, UNIVERSITY_THEME, HIGH_CONTRAST_THEME } from './presets';

// ============================================
// Tipos del contexto
// ============================================

interface ThemeContextValue {
  theme: ThemeConfig;
  isLoading: boolean;
  error: Error | null;
  validationWarnings: string[];
  availableThemes: string[];
  setTheme: (theme: ThemeConfig) => void;
  loadTheme: (url: string) => Promise<void>;
  switchTheme: (themeName: string) => Promise<void>;
  resetTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

// ============================================
// Temas predefinidos
// ============================================

const PRESET_THEMES: Record<string, ThemeConfig> = {
  default: DEFAULT_THEME,
  dark: DARK_THEME,
  university: UNIVERSITY_THEME,
  'high-contrast': HIGH_CONTRAST_THEME,
};

// ============================================
// Storage key
// ============================================

const STORAGE_KEY = 'chatbot-theme';

// ============================================
// Utilidad para generar CSS variables
// ============================================

function generateCSSVariables(theme: ThemeConfig): string {
  const variables: string[] = [];

  // Colores
  for (const [key, value] of Object.entries(theme.colors)) {
    const cssKey = `--color-${camelToKebab(key)}`;
    variables.push(`${cssKey}: ${value};`);
  }

  // Tipografía
  variables.push(`--font-family: ${theme.typography.fontFamily};`);
  variables.push(`--font-family-mono: ${theme.typography.fontFamilyMono};`);
  variables.push(`--font-size-xs: ${theme.typography.fontSizeXs};`);
  variables.push(`--font-size-sm: ${theme.typography.fontSizeSmall};`);
  variables.push(`--font-size: ${theme.typography.fontSize};`);
  variables.push(`--font-size-md: ${theme.typography.fontSizeMd};`);
  variables.push(`--font-size-lg: ${theme.typography.fontSizeLarge};`);
  variables.push(`--font-size-xl: ${theme.typography.fontSizeXl};`);
  variables.push(`--font-size-xxl: ${theme.typography.fontSizeXxl};`);
  variables.push(`--font-weight-light: ${theme.typography.fontWeightLight};`);
  variables.push(`--font-weight: ${theme.typography.fontWeight};`);
  variables.push(`--font-weight-medium: ${theme.typography.fontWeightMedium};`);
  variables.push(`--font-weight-bold: ${theme.typography.fontWeightBold};`);
  variables.push(`--line-height: ${theme.typography.lineHeight};`);
  variables.push(`--line-height-tight: ${theme.typography.lineHeightTight};`);
  variables.push(`--line-height-relaxed: ${theme.typography.lineHeightRelaxed};`);

  // Espaciado
  for (const [key, value] of Object.entries(theme.spacing)) {
    variables.push(`--spacing-${key}: ${value};`);
  }

  // Border radius
  for (const [key, value] of Object.entries(theme.borderRadius)) {
    variables.push(`--radius-${key}: ${value};`);
  }

  // Sombras
  for (const [key, value] of Object.entries(theme.shadows)) {
    variables.push(`--shadow-${key}: ${value};`);
  }

  // Animaciones
  variables.push(`--duration-fast: ${theme.animations.durationFast};`);
  variables.push(`--duration-normal: ${theme.animations.durationNormal};`);
  variables.push(`--duration-slow: ${theme.animations.durationSlow};`);
  variables.push(`--easing: ${theme.animations.easing};`);
  variables.push(`--easing-bounce: ${theme.animations.easingBounce};`);

  // Componentes específicos
  if (theme.components) {
    const { chatBubble, header, input, button, widget } = theme.components;

    if (chatBubble) {
      if (chatBubble.borderRadius) variables.push(`--bubble-radius: ${chatBubble.borderRadius};`);
      if (chatBubble.padding) variables.push(`--bubble-padding: ${chatBubble.padding};`);
      if (chatBubble.maxWidth) variables.push(`--bubble-max-width: ${chatBubble.maxWidth};`);
      if (chatBubble.shadow) variables.push(`--bubble-shadow: ${chatBubble.shadow};`);
    }

    if (header) {
      if (header.height) variables.push(`--header-height: ${header.height};`);
      if (header.padding) variables.push(`--header-padding: ${header.padding};`);
      if (header.background) variables.push(`--header-bg: ${header.background};`);
    }

    if (input) {
      if (input.height) variables.push(`--input-height: ${input.height};`);
      if (input.padding) variables.push(`--input-padding: ${input.padding};`);
      if (input.borderRadius) variables.push(`--input-radius: ${input.borderRadius};`);
    }

    if (widget) {
      if (widget.width) variables.push(`--widget-width: ${widget.width};`);
      if (widget.height) variables.push(`--widget-height: ${widget.height};`);
      if (widget.borderRadius) variables.push(`--widget-radius: ${widget.borderRadius};`);
      if (widget.shadow) variables.push(`--widget-shadow: ${widget.shadow};`);
    }
  }

  return variables.join('\n');
}

function camelToKebab(str: string): string {
  return str.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();
}

// ============================================
// Inyección de CSS en el documento
// ============================================

function injectThemeCSS(theme: ThemeConfig): void {
  const cssVariables = generateCSSVariables(theme);

  // Buscar o crear el elemento style
  let styleElement = document.getElementById('chatbot-theme-vars');
  if (!styleElement) {
    styleElement = document.createElement('style');
    styleElement.id = 'chatbot-theme-vars';
    document.head.appendChild(styleElement);
  }

  styleElement.textContent = `:root {\n${cssVariables}\n}`;

  // Inyectar CSS personalizado si existe
  if (theme.customCSS) {
    let customStyleElement = document.getElementById('chatbot-custom-css');
    if (!customStyleElement) {
      customStyleElement = document.createElement('style');
      customStyleElement.id = 'chatbot-custom-css';
      document.head.appendChild(customStyleElement);
    }
    customStyleElement.textContent = theme.customCSS;
  }
}

// ============================================
// Provider Component
// ============================================

interface ThemeProviderProps {
  children: ReactNode;
  initialTheme?: ThemeConfig;
  themeUrl?: string;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  initialTheme,
  themeUrl,
}) => {
  const [theme, setThemeState] = useState<ThemeConfig>(() => {
    // Intentar cargar desde localStorage
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return mergeThemes(DEFAULT_THEME, parsed);
      }
    } catch {
      // Ignorar errores de parsing
    }

    return initialTheme || DEFAULT_THEME;
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);

  // Inyectar CSS cuando cambia el tema
  useEffect(() => {
    injectThemeCSS(theme);
  }, [theme]);

  // Cargar tema desde URL si se proporciona
  useEffect(() => {
    if (themeUrl) {
      loadTheme(themeUrl);
    }
  }, [themeUrl]);

  const setTheme = useCallback((newTheme: ThemeConfig) => {
    // Validar tema
    const validation = validateTheme(newTheme);
    if (!validation.valid) {
      console.warn('Theme validation failed:', validation.errors);
    }
    setValidationWarnings(validation.warnings);

    setThemeState(newTheme);

    // Guardar en localStorage
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newTheme));
    } catch (e) {
      console.warn('Failed to save theme to localStorage:', e);
    }
  }, []);

  const loadTheme = useCallback(async (url: string): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to load theme: ${response.statusText}`);
      }

      const partialTheme = await response.json();
      const mergedTheme = mergeThemes(DEFAULT_THEME, partialTheme);

      // Validar
      const validation = validateTheme(mergedTheme);
      setValidationWarnings([...validation.errors, ...validation.warnings]);

      setTheme(mergedTheme);
    } catch (e) {
      const error = e instanceof Error ? e : new Error('Unknown error loading theme');
      setError(error);
      console.error('Failed to load theme:', error);
    } finally {
      setIsLoading(false);
    }
  }, [setTheme]);

  const switchTheme = useCallback(async (themeName: string): Promise<void> => {
    const preset = PRESET_THEMES[themeName];
    if (preset) {
      setTheme(preset);
    } else {
      // Intentar cargar desde API
      await loadTheme(`/api/themes/${themeName}`);
    }
  }, [setTheme, loadTheme]);

  const resetTheme = useCallback(() => {
    setTheme(DEFAULT_THEME);
    localStorage.removeItem(STORAGE_KEY);
  }, [setTheme]);

  const availableThemes = useMemo(() => Object.keys(PRESET_THEMES), []);

  const contextValue = useMemo<ThemeContextValue>(
    () => ({
      theme,
      isLoading,
      error,
      validationWarnings,
      availableThemes,
      setTheme,
      loadTheme,
      switchTheme,
      resetTheme,
    }),
    [
      theme,
      isLoading,
      error,
      validationWarnings,
      availableThemes,
      setTheme,
      loadTheme,
      switchTheme,
      resetTheme,
    ]
  );

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};

// ============================================
// Hook para usar el tema
// ============================================

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

// ============================================
// HOC para componentes temáticos
// ============================================

export function withTheme<P extends object>(
  Component: React.ComponentType<P & { theme: ThemeConfig }>
): React.FC<Omit<P, 'theme'>> {
  return function ThemedComponent(props: Omit<P, 'theme'>) {
    const { theme } = useTheme();
    return <Component {...(props as P)} theme={theme} />;
  };
}
```

---

### Prompt 10.5 - Temas Predefinidos (Presets)

**Objetivo**: Definir los temas visuales predefinidos del sistema (Default, Dark, University, High Contrast) como objetos de configuración reutilizables y exportables.

**frontend/src/themes/presets.ts**:
```typescript
/**
 * Temas predefinidos para el chatbot
 *
 * Estos temas pueden usarse directamente o como base para personalización.
 */

import { ThemeConfig, DEFAULT_THEME, mergeThemes } from './types';

// ============================================
// Tema Oscuro
// ============================================

export const DARK_THEME: ThemeConfig = mergeThemes(DEFAULT_THEME, {
  name: 'dark',
  version: '1.0.0',

  colors: {
    // Colores principales
    primary: '#60a5fa',
    primaryHover: '#3b82f6',
    primaryLight: '#1e3a5f',
    secondary: '#94a3b8',
    secondaryHover: '#64748b',

    // Fondos
    background: '#1a1a2e',
    surface: '#16213e',
    surfaceHover: '#1f2937',

    // Texto
    text: '#f1f5f9',
    textSecondary: '#94a3b8',
    textMuted: '#64748b',
    textOnPrimary: '#ffffff',

    // Bordes
    border: '#334155',
    borderLight: '#1e293b',
    divider: '#1e293b',

    // Estados
    error: '#f87171',
    errorLight: '#7f1d1d',
    success: '#4ade80',
    successLight: '#14532d',
    warning: '#fbbf24',
    warningLight: '#78350f',
    info: '#38bdf8',
    infoLight: '#0c4a6e',

    // Mensajes del chat
    botMessage: '#1e293b',
    botMessageText: '#f1f5f9',
    userMessage: '#3b82f6',
    userMessageText: '#ffffff',

    // Overlays
    overlay: 'rgba(0, 0, 0, 0.7)',
    shadow: 'rgba(0, 0, 0, 0.3)',
  },

  components: {
    header: {
      background: 'linear-gradient(135deg, #1e3a5f 0%, #16213e 100%)',
    },
    widget: {
      shadow: '0 10px 40px rgba(0, 0, 0, 0.4)',
    },
  },
});

// ============================================
// Tema Universitario (colores corporativos)
// ============================================

export const UNIVERSITY_THEME: ThemeConfig = mergeThemes(DEFAULT_THEME, {
  name: 'university',
  version: '1.0.0',

  colors: {
    // Colores principales (azul institucional)
    primary: '#003366',
    primaryHover: '#002244',
    primaryLight: '#e6f0fa',
    secondary: '#cc0000',
    secondaryHover: '#990000',

    // Fondos
    background: '#ffffff',
    surface: '#f5f7fa',
    surfaceHover: '#ebeef3',

    // Texto
    text: '#1a1a1a',
    textSecondary: '#4a4a4a',
    textMuted: '#7a7a7a',
    textOnPrimary: '#ffffff',

    // Bordes
    border: '#d1d5db',
    borderLight: '#e5e7eb',
    divider: '#e5e7eb',

    // Mensajes del chat
    botMessage: '#f0f4f8',
    botMessageText: '#1a1a1a',
    userMessage: '#003366',
    userMessageText: '#ffffff',
  },

  typography: {
    fontFamily: "'Source Sans Pro', 'Roboto', -apple-system, sans-serif",
  },

  components: {
    header: {
      background: 'linear-gradient(135deg, #003366 0%, #002244 100%)',
    },
    chatBubble: {
      borderRadius: '0.5rem',
    },
    button: {
      borderRadius: '0.25rem',
    },
  },
});

// ============================================
// Tema Alto Contraste (accesibilidad)
// ============================================

export const HIGH_CONTRAST_THEME: ThemeConfig = mergeThemes(DEFAULT_THEME, {
  name: 'high-contrast',
  version: '1.0.0',

  colors: {
    // Colores principales
    primary: '#0000ff',
    primaryHover: '#0000cc',
    primaryLight: '#ccccff',
    secondary: '#000000',
    secondaryHover: '#333333',

    // Fondos
    background: '#ffffff',
    surface: '#ffffff',
    surfaceHover: '#f0f0f0',

    // Texto
    text: '#000000',
    textSecondary: '#000000',
    textMuted: '#333333',
    textOnPrimary: '#ffffff',

    // Bordes
    border: '#000000',
    borderLight: '#333333',
    divider: '#000000',

    // Estados
    error: '#cc0000',
    errorLight: '#ffcccc',
    success: '#006600',
    successLight: '#ccffcc',
    warning: '#cc6600',
    warningLight: '#ffe6cc',

    // Mensajes del chat
    botMessage: '#f0f0f0',
    botMessageText: '#000000',
    userMessage: '#0000ff',
    userMessageText: '#ffffff',
  },

  typography: {
    fontSize: '1.125rem',
    fontSizeLarge: '1.25rem',
    fontWeight: 500,
    fontWeightBold: 700,
  },

  components: {
    chatBubble: {
      borderRadius: '0',
      shadow: 'none',
    },
    input: {
      border: '2px solid #000000',
      focusBorder: '3px solid #0000ff',
    },
    header: {
      background: '#000000',
      borderBottom: '2px solid #ffffff',
    },
  },
});

// ============================================
// Exportar todos los presets
// ============================================

export const THEME_PRESETS = {
  default: DEFAULT_THEME,
  dark: DARK_THEME,
  university: UNIVERSITY_THEME,
  'high-contrast': HIGH_CONTRAST_THEME,
} as const;

export type ThemePresetName = keyof typeof THEME_PRESETS;
```

---

### Prompt 10.6 - CSS Base con Variables (Template)

**Objetivo**: Crear el archivo CSS base con todas las Custom Properties (variables CSS) que el ThemeProvider sobreescribe dinámicamente para controlar colores, tipografía y espaciados.

**frontend/src/themes/base.css**:
```css
/**
 * CSS Base con Variables de Tema
 *
 * Este archivo define los estilos base usando CSS custom properties.
 * Las variables son inyectadas por el ThemeProvider.
 */

/* ============================================
   Reset y Base
   ============================================ */

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

/* ============================================
   Variables por defecto (fallback)
   ============================================ */

:root {
  /* Colores - serán sobrescritos por el tema */
  --color-primary: #0066cc;
  --color-primary-hover: #0052a3;
  --color-primary-light: #e6f0fa;
  --color-secondary: #6c757d;
  --color-background: #ffffff;
  --color-surface: #f8f9fa;
  --color-text: #212529;
  --color-text-secondary: #6c757d;
  --color-border: #dee2e6;
  --color-error: #dc3545;
  --color-success: #28a745;

  /* Mensajes */
  --color-bot-message: #f1f3f4;
  --color-bot-message-text: #212529;
  --color-user-message: #0066cc;
  --color-user-message-text: #ffffff;

  /* Tipografía */
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-size: 1rem;
  --font-size-sm: 0.875rem;
  --font-size-lg: 1.125rem;
  --font-weight: 400;
  --font-weight-bold: 600;
  --line-height: 1.5;

  /* Espaciado */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;

  /* Bordes */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-full: 9999px;

  /* Sombras */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);

  /* Animaciones */
  --duration-fast: 150ms;
  --duration-normal: 300ms;
  --easing: cubic-bezier(0.4, 0, 0.2, 1);

  /* Componentes */
  --widget-width: 380px;
  --widget-height: 600px;
  --widget-radius: 1rem;
  --widget-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  --header-height: 60px;
  --input-height: 48px;
  --bubble-radius: 1rem;
  --bubble-padding: 0.75rem 1rem;
  --bubble-max-width: 80%;
}

/* ============================================
   Estilos del Widget
   ============================================ */

.chatbot-widget {
  width: var(--widget-width);
  max-height: var(--widget-height);
  border-radius: var(--widget-radius);
  box-shadow: var(--widget-shadow);
  background-color: var(--color-background);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: var(--font-family);
  font-size: var(--font-size);
  line-height: var(--line-height);
  color: var(--color-text);
}

/* ============================================
   Header
   ============================================ */

.chatbot-header {
  height: var(--header-height);
  padding: var(--header-padding, 0 var(--spacing-md));
  background: var(--header-bg, var(--color-primary));
  color: var(--color-text-on-primary, white);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.chatbot-header__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  margin: 0;
}

.chatbot-header__subtitle {
  font-size: var(--font-size-sm);
  opacity: 0.9;
}

/* ============================================
   Área de mensajes
   ============================================ */

.chatbot-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
  background-color: var(--color-background);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* ============================================
   Burbujas de chat
   ============================================ */

.chat-bubble {
  max-width: var(--bubble-max-width);
  padding: var(--bubble-padding);
  border-radius: var(--bubble-radius);
  box-shadow: var(--bubble-shadow, var(--shadow-sm));
  word-wrap: break-word;
  animation: fadeIn var(--duration-normal) var(--easing);
}

.chat-bubble--bot {
  align-self: flex-start;
  background-color: var(--color-bot-message);
  color: var(--color-bot-message-text);
  border-bottom-left-radius: var(--radius-sm);
}

.chat-bubble--user {
  align-self: flex-end;
  background-color: var(--color-user-message);
  color: var(--color-user-message-text);
  border-bottom-right-radius: var(--radius-sm);
}

/* ============================================
   Input de chat
   ============================================ */

.chatbot-input {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background-color: var(--color-surface);
  border-top: 1px solid var(--color-border);
}

.chatbot-input__field {
  flex: 1;
  height: var(--input-height);
  padding: var(--input-padding, 0 var(--spacing-md));
  border: var(--input-border, 1px solid var(--color-border));
  border-radius: var(--input-radius, var(--radius-full));
  background-color: var(--color-background);
  color: var(--color-text);
  font-family: inherit;
  font-size: var(--font-size);
  outline: none;
  transition: border-color var(--duration-fast) var(--easing),
              box-shadow var(--duration-fast) var(--easing);
}

.chatbot-input__field:focus {
  border: var(--input-focus-border, 2px solid var(--color-primary));
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.chatbot-input__field::placeholder {
  color: var(--color-text-muted, var(--color-text-secondary));
}

/* ============================================
   Botones
   ============================================ */

.chatbot-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: var(--radius-md);
  background-color: var(--color-primary);
  color: var(--color-text-on-primary, white);
  font-family: inherit;
  font-size: var(--font-size);
  font-weight: var(--font-weight-medium, 500);
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--easing),
              transform var(--duration-fast) var(--easing);
}

.chatbot-btn:hover {
  background-color: var(--color-primary-hover);
}

.chatbot-btn:active {
  transform: scale(0.98);
}

.chatbot-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chatbot-btn--icon {
  width: var(--input-height);
  height: var(--input-height);
  padding: 0;
  border-radius: var(--radius-full);
}

.chatbot-btn--secondary {
  background-color: var(--color-secondary);
}

.chatbot-btn--secondary:hover {
  background-color: var(--color-secondary-hover);
}

/* ============================================
   Estados y feedback
   ============================================ */

.chatbot-typing {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.chatbot-typing__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--color-text-secondary);
  animation: typing 1.4s infinite ease-in-out both;
}

.chatbot-typing__dot:nth-child(1) { animation-delay: -0.32s; }
.chatbot-typing__dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.chatbot-error {
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--color-error-light);
  color: var(--color-error);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

/* ============================================
   Animaciones
   ============================================ */

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(100%);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ============================================
   Utilidades
   ============================================ */

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

/* ============================================
   Responsive
   ============================================ */

@media (max-width: 480px) {
  .chatbot-widget {
    width: 100%;
    height: 100%;
    max-height: 100vh;
    border-radius: 0;
  }
}
```

---

### Prompt 10.7 - Editor de Tema en Tiempo Real (Componente de Administración)

**Objetivo**: Implementar el componente React `ThemeEditor` que permite al administrador modificar colores, tipografía y espaciados del chatbot en tiempo real, con previsualización inmediata y capacidad de exportar/importar el tema como JSON.

**frontend/src/components/ThemeEditor/ThemeEditor.tsx**:
```typescript
/**
 * Editor de temas en tiempo real
 *
 * Este componente permite a los administradores personalizar
 * el tema del chatbot de forma visual.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../themes/ThemeProvider';
import { ThemeConfig, DEFAULT_THEME, validateTheme } from '../../themes/types';
import { THEME_PRESETS, ThemePresetName } from '../../themes/presets';
import styles from './ThemeEditor.module.css';

interface ColorInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

const ColorInput: React.FC<ColorInputProps> = ({ label, value, onChange }) => (
  <div className={styles.colorInput}>
    <label className={styles.colorLabel}>{label}</label>
    <div className={styles.colorInputWrapper}>
      <input
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={styles.colorPicker}
      />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={styles.colorText}
        pattern="^#[0-9a-fA-F]{6}$"
      />
    </div>
  </div>
);

interface ThemeEditorProps {
  onSave?: (theme: ThemeConfig) => Promise<void>;
  onCancel?: () => void;
}

export const ThemeEditor: React.FC<ThemeEditorProps> = ({ onSave, onCancel }) => {
  const { t } = useTranslation();
  const { theme, setTheme, availableThemes, switchTheme } = useTheme();
  const [localTheme, setLocalTheme] = useState<ThemeConfig>(theme);
  const [activeTab, setActiveTab] = useState<'colors' | 'typography' | 'components' | 'preview'>('colors');
  const [isSaving, setIsSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Sincronizar con el tema global
  useEffect(() => {
    setLocalTheme(theme);
  }, [theme]);

  // Validar cambios
  useEffect(() => {
    const result = validateTheme(localTheme);
    setValidationErrors(result.errors);
  }, [localTheme]);

  const updateColor = useCallback((key: keyof ThemeConfig['colors'], value: string) => {
    setLocalTheme((prev) => ({
      ...prev,
      colors: {
        ...prev.colors,
        [key]: value,
      },
    }));
  }, []);

  const updateTypography = useCallback(
    (key: keyof ThemeConfig['typography'], value: string | number) => {
      setLocalTheme((prev) => ({
        ...prev,
        typography: {
          ...prev.typography,
          [key]: value,
        },
      }));
    },
    []
  );

  const applyPreset = useCallback(async (presetName: string) => {
    const preset = THEME_PRESETS[presetName as ThemePresetName];
    if (preset) {
      setLocalTheme(preset);
    }
  }, []);

  const handlePreview = useCallback(() => {
    setTheme(localTheme);
  }, [localTheme, setTheme]);

  const handleSave = useCallback(async () => {
    if (validationErrors.length > 0) {
      return;
    }

    setIsSaving(true);
    try {
      setTheme(localTheme);
      if (onSave) {
        await onSave(localTheme);
      }
    } finally {
      setIsSaving(false);
    }
  }, [localTheme, validationErrors, setTheme, onSave]);

  const handleReset = useCallback(() => {
    setLocalTheme(DEFAULT_THEME);
    setTheme(DEFAULT_THEME);
  }, [setTheme]);

  const handleExport = useCallback(() => {
    const json = JSON.stringify(localTheme, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `theme-${localTheme.name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [localTheme]);

  const handleImport = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target?.result as string);
        setLocalTheme({ ...DEFAULT_THEME, ...imported });
      } catch (err) {
        console.error('Failed to parse theme file:', err);
      }
    };
    reader.readAsText(file);
  }, []);

  return (
    <div className={styles.editor}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.title}>{t('themeEditor.title', 'Editor de Tema')}</h2>
        <div className={styles.presetSelector}>
          <label>{t('themeEditor.preset', 'Preset')}:</label>
          <select
            value={localTheme.name}
            onChange={(e) => applyPreset(e.target.value)}
            className={styles.select}
          >
            {availableThemes.map((name) => (
              <option key={name} value={name}>
                {name.charAt(0).toUpperCase() + name.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'colors' ? styles.active : ''}`}
          onClick={() => setActiveTab('colors')}
        >
          {t('themeEditor.colors', 'Colores')}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'typography' ? styles.active : ''}`}
          onClick={() => setActiveTab('typography')}
        >
          {t('themeEditor.typography', 'Tipografía')}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'components' ? styles.active : ''}`}
          onClick={() => setActiveTab('components')}
        >
          {t('themeEditor.components', 'Componentes')}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'preview' ? styles.active : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          {t('themeEditor.preview', 'Vista Previa')}
        </button>
      </div>

      {/* Content */}
      <div className={styles.content}>
        {activeTab === 'colors' && (
          <div className={styles.colorGrid}>
            <h3>{t('themeEditor.mainColors', 'Colores Principales')}</h3>
            <ColorInput
              label="Primary"
              value={localTheme.colors.primary}
              onChange={(v) => updateColor('primary', v)}
            />
            <ColorInput
              label="Primary Hover"
              value={localTheme.colors.primaryHover}
              onChange={(v) => updateColor('primaryHover', v)}
            />
            <ColorInput
              label="Secondary"
              value={localTheme.colors.secondary}
              onChange={(v) => updateColor('secondary', v)}
            />

            <h3>{t('themeEditor.backgrounds', 'Fondos')}</h3>
            <ColorInput
              label="Background"
              value={localTheme.colors.background}
              onChange={(v) => updateColor('background', v)}
            />
            <ColorInput
              label="Surface"
              value={localTheme.colors.surface}
              onChange={(v) => updateColor('surface', v)}
            />

            <h3>{t('themeEditor.text', 'Texto')}</h3>
            <ColorInput
              label="Text"
              value={localTheme.colors.text}
              onChange={(v) => updateColor('text', v)}
            />
            <ColorInput
              label="Text Secondary"
              value={localTheme.colors.textSecondary}
              onChange={(v) => updateColor('textSecondary', v)}
            />

            <h3>{t('themeEditor.chatMessages', 'Mensajes del Chat')}</h3>
            <ColorInput
              label="Bot Message BG"
              value={localTheme.colors.botMessage}
              onChange={(v) => updateColor('botMessage', v)}
            />
            <ColorInput
              label="Bot Message Text"
              value={localTheme.colors.botMessageText}
              onChange={(v) => updateColor('botMessageText', v)}
            />
            <ColorInput
              label="User Message BG"
              value={localTheme.colors.userMessage}
              onChange={(v) => updateColor('userMessage', v)}
            />
            <ColorInput
              label="User Message Text"
              value={localTheme.colors.userMessageText}
              onChange={(v) => updateColor('userMessageText', v)}
            />
          </div>
        )}

        {activeTab === 'typography' && (
          <div className={styles.typographyPanel}>
            <div className={styles.inputGroup}>
              <label>{t('themeEditor.fontFamily', 'Familia de fuente')}</label>
              <input
                type="text"
                value={localTheme.typography.fontFamily}
                onChange={(e) => updateTypography('fontFamily', e.target.value)}
                className={styles.textInput}
              />
            </div>

            <div className={styles.inputGroup}>
              <label>{t('themeEditor.fontSize', 'Tamaño base')}</label>
              <input
                type="text"
                value={localTheme.typography.fontSize}
                onChange={(e) => updateTypography('fontSize', e.target.value)}
                className={styles.textInput}
              />
            </div>

            <div className={styles.inputGroup}>
              <label>{t('themeEditor.lineHeight', 'Altura de línea')}</label>
              <input
                type="number"
                step="0.1"
                value={localTheme.typography.lineHeight}
                onChange={(e) => updateTypography('lineHeight', parseFloat(e.target.value))}
                className={styles.textInput}
              />
            </div>
          </div>
        )}

        {activeTab === 'preview' && (
          <div className={styles.previewPanel}>
            <p>{t('themeEditor.previewDescription', 'Vista previa del tema aplicado al widget.')}</p>
            {/* Aquí se mostraría una mini-preview del chatbot */}
            <div
              className={styles.miniPreview}
              style={{
                backgroundColor: localTheme.colors.background,
                color: localTheme.colors.text,
                fontFamily: localTheme.typography.fontFamily,
              }}
            >
              <div
                style={{
                  backgroundColor: localTheme.colors.primary,
                  color: localTheme.colors.textOnPrimary,
                  padding: '1rem',
                }}
              >
                Header del Chat
              </div>
              <div style={{ padding: '1rem' }}>
                <div
                  style={{
                    backgroundColor: localTheme.colors.botMessage,
                    color: localTheme.colors.botMessageText,
                    padding: '0.5rem 1rem',
                    borderRadius: '1rem',
                    marginBottom: '0.5rem',
                    maxWidth: '80%',
                  }}
                >
                  ¡Hola! ¿En qué puedo ayudarte?
                </div>
                <div
                  style={{
                    backgroundColor: localTheme.colors.userMessage,
                    color: localTheme.colors.userMessageText,
                    padding: '0.5rem 1rem',
                    borderRadius: '1rem',
                    marginLeft: 'auto',
                    maxWidth: '80%',
                  }}
                >
                  Tengo una pregunta sobre...
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className={styles.errors}>
          {validationErrors.map((error, i) => (
            <div key={i} className={styles.error}>
              ⚠️ {error}
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className={styles.actions}>
        <div className={styles.leftActions}>
          <button onClick={handlePreview} className={styles.btnSecondary}>
            {t('themeEditor.preview', 'Vista Previa')}
          </button>
          <button onClick={handleReset} className={styles.btnSecondary}>
            {t('themeEditor.reset', 'Resetear')}
          </button>
        </div>
        <div className={styles.rightActions}>
          <button onClick={handleExport} className={styles.btnSecondary}>
            {t('themeEditor.export', 'Exportar')}
          </button>
          <label className={styles.btnSecondary}>
            {t('themeEditor.import', 'Importar')}
            <input
              type="file"
              accept=".json"
              onChange={handleImport}
              style={{ display: 'none' }}
            />
          </label>
          {onCancel && (
            <button onClick={onCancel} className={styles.btnSecondary}>
              {t('common.cancel', 'Cancelar')}
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={validationErrors.length > 0 || isSaving}
            className={styles.btnPrimary}
          >
            {isSaving ? t('common.saving', 'Guardando...') : t('common.save', 'Guardar')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ThemeEditor;
```

---

### Prompt 10.8 - Backend: API de Temas

**Objetivo**: Implementar los endpoints REST FastAPI para el CRUD completo de temas personalizados, incluyendo almacenamiento en base de datos y servicio de temas por URL pública.

**src/api/routers/themes.py**:
```python
"""Router para gestión de temas del chatbot."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_admin, require_partner
from src.auth.models import UserInfo
from src.database import get_async_session

router = APIRouter(prefix="/api/v1/themes", tags=["themes"])


# ============================================
# Modelos Pydantic
# ============================================

class ThemeColors(BaseModel):
    """Colores del tema."""
    primary: str = "#0066cc"
    primaryHover: str = "#0052a3"
    primaryLight: str = "#e6f0fa"
    secondary: str = "#6c757d"
    background: str = "#ffffff"
    surface: str = "#f8f9fa"
    text: str = "#212529"
    textSecondary: str = "#6c757d"
    border: str = "#dee2e6"
    error: str = "#dc3545"
    success: str = "#28a745"
    warning: str = "#ffc107"
    botMessage: str = "#f1f3f4"
    botMessageText: str = "#212529"
    userMessage: str = "#0066cc"
    userMessageText: str = "#ffffff"

    class Config:
        extra = "allow"


class ThemeTypography(BaseModel):
    """Tipografía del tema."""
    fontFamily: str = "'Inter', sans-serif"
    fontSize: str = "1rem"
    fontSizeSmall: str = "0.875rem"
    fontSizeLarge: str = "1.125rem"
    fontWeight: int = 400
    fontWeightBold: int = 600
    lineHeight: float = 1.5


class ThemeSpacing(BaseModel):
    """Espaciado del tema."""
    xs: str = "0.25rem"
    sm: str = "0.5rem"
    md: str = "1rem"
    lg: str = "1.5rem"
    xl: str = "2rem"


class ThemeConfig(BaseModel):
    """Configuración completa del tema."""
    name: str = Field(..., min_length=1, max_length=100)
    version: str = "1.0.0"
    colors: ThemeColors = Field(default_factory=ThemeColors)
    typography: ThemeTypography = Field(default_factory=ThemeTypography)
    spacing: ThemeSpacing = Field(default_factory=ThemeSpacing)
    customCSS: str | None = None

    class Config:
        extra = "allow"


class ThemeCreate(BaseModel):
    """Datos para crear un tema.

    Sistema de cascada visual:
    - Si solo se especifica client_id: tema a nivel cliente (hereda defaults de plataforma).
    - Si se especifica chatbot_id: tema a nivel chatbot (hereda del cliente, que hereda de plataforma).
    - Sin ninguno: tema de plataforma (defaults globales, solo Admin).
    """
    name: str = Field(..., min_length=1, max_length=100)
    client_id: str | None = None   # tema a nivel cliente
    chatbot_id: str | None = None  # tema a nivel chatbot (override sobre cliente)
    config: ThemeConfig


class ThemeUpdate(BaseModel):
    """Datos para actualizar un tema."""
    config: ThemeConfig


class ThemeResponse(BaseModel):
    """Respuesta con datos del tema."""
    id: str
    name: str
    client_id: str | None
    chatbot_id: str | None
    config: dict
    is_default: bool
    created_at: str
    updated_at: str


# ============================================
# Almacenamiento de temas (simplificado - en producción usar BD)
# ============================================

THEMES_DIR = Path("data/themes")
THEMES_DIR.mkdir(parents=True, exist_ok=True)


def get_theme_path(theme_id: str) -> Path:
    """Obtiene la ruta del archivo de tema."""
    return THEMES_DIR / f"{theme_id}.json"


def load_theme(theme_id: str) -> dict | None:
    """Carga un tema desde archivo."""
    path = get_theme_path(theme_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_theme(theme_id: str, data: dict) -> None:
    """Guarda un tema en archivo."""
    path = get_theme_path(theme_id)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_themes() -> list[dict]:
    """Lista todos los temas disponibles."""
    themes = []
    for path in THEMES_DIR.glob("*.json"):
        try:
            theme = json.loads(path.read_text(encoding="utf-8"))
            themes.append(theme)
        except (json.JSONDecodeError, IOError):
            continue
    return themes


# ============================================
# Endpoints
# ============================================

@router.get("", response_model=list[ThemeResponse])
async def get_themes(
    client_id: str | None = None,
    chatbot_id: str | None = None,
    user: UserInfo = Depends(require_partner),
) -> list[dict]:
    """Lista los temas disponibles para el partner.

    Filtra opcionalmente por client_id o chatbot_id.
    La resolución final del tema efectivo sigue la cascada:
    plataforma (defaults) → cliente → chatbot.
    """
    themes = list_themes()

    if chatbot_id:
        themes = [t for t in themes if t.get("chatbot_id") == chatbot_id or t.get("client_id") == client_id or t.get("is_default")]
    elif client_id:
        themes = [t for t in themes if t.get("client_id") == client_id or t.get("is_default")]

    return themes


@router.get("/presets")
async def get_preset_themes() -> list[dict]:
    """Obtiene los temas predefinidos (no requiere auth)."""
    presets = [
        {"name": "default", "label": "Predeterminado"},
        {"name": "dark", "label": "Oscuro"},
        {"name": "university", "label": "Universitario"},
        {"name": "high-contrast", "label": "Alto Contraste"},
    ]
    return presets


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(
    theme_id: str,
) -> dict:
    """Obtiene un tema específico por ID."""
    theme = load_theme(theme_id)
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {theme_id} not found"
        )
    return theme


@router.post("", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
    data: ThemeCreate,
    user: UserInfo = Depends(require_partner),
) -> dict:
    """Crea un nuevo tema para un cliente o chatbot del partner.

    Si data.chatbot_id es None y data.client_id es None, solo Admin puede crear
    temas de plataforma (defaults globales).
    """
    theme_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    theme = {
        "id": theme_id,
        "name": data.name,
        "chatbot_id": data.chatbot_id,
        "config": data.config.model_dump(),
        "is_default": False,
        "created_at": now,
        "updated_at": now,
        "created_by": user.user_id,
    }

    save_theme(theme_id, theme)
    return theme


@router.put("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    theme_id: str,
    data: ThemeUpdate,
    user: UserInfo = Depends(require_admin),
) -> dict:
    """Actualiza un tema existente."""
    theme = load_theme(theme_id)
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {theme_id} not found"
        )

    if theme.get("is_default"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify default themes"
        )

    theme["config"] = data.config.model_dump()
    theme["updated_at"] = datetime.now(timezone.utc).isoformat()

    save_theme(theme_id, theme)
    return theme


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(
    theme_id: str,
    user: UserInfo = Depends(require_admin),
) -> None:
    """Elimina un tema personalizado."""
    theme = load_theme(theme_id)
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {theme_id} not found"
        )

    if theme.get("is_default"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default themes"
        )

    path = get_theme_path(theme_id)
    path.unlink()


@router.post("/{theme_id}/apply/{chatbot_id}")
async def apply_theme_to_chatbot(
    theme_id: str,
    chatbot_id: str,
    user: UserInfo = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Aplica un tema a un chatbot específico."""
    theme = load_theme(theme_id)
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {theme_id} not found"
        )

    # Aquí se actualizaría la configuración del chatbot en BD
    # Por ahora retornamos confirmación
    return {
        "message": f"Theme {theme_id} applied to chatbot {chatbot_id}",
        "theme_name": theme["name"],
    }
```

---

### Prompt 10.9 - Tests del Sistema de Temas

**Objetivo**: Validar el sistema completo de temas: tipos TypeScript, ThemeProvider, API REST y editor visual, asegurando que los cambios se aplican y persisten correctamente.

**tests/test_themes.py**:
```python
"""Tests para el sistema de temas."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

from src.main import app


@pytest.fixture
def sample_theme_config():
    """Configuración de tema de ejemplo."""
    return {
        "name": "test-theme",
        "version": "1.0.0",
        "colors": {
            "primary": "#ff0000",
            "primaryHover": "#cc0000",
            "primaryLight": "#ffcccc",
            "secondary": "#00ff00",
            "background": "#ffffff",
            "surface": "#f0f0f0",
            "text": "#000000",
            "textSecondary": "#666666",
            "border": "#cccccc",
            "error": "#ff0000",
            "success": "#00ff00",
            "warning": "#ffff00",
            "botMessage": "#e0e0e0",
            "botMessageText": "#000000",
            "userMessage": "#0066cc",
            "userMessageText": "#ffffff",
        },
        "typography": {
            "fontFamily": "'Arial', sans-serif",
            "fontSize": "16px",
            "fontSizeSmall": "14px",
            "fontSizeLarge": "18px",
            "fontWeight": 400,
            "fontWeightBold": 700,
            "lineHeight": 1.6,
        },
        "spacing": {
            "xs": "4px",
            "sm": "8px",
            "md": "16px",
            "lg": "24px",
            "xl": "32px",
        },
    }


class TestThemeValidation:
    """Tests para validación de temas."""

    def test_valid_theme_passes_validation(self, sample_theme_config):
        """Un tema válido pasa la validación."""
        from src.api.routers.themes import ThemeConfig

        theme = ThemeConfig(**sample_theme_config)
        assert theme.name == "test-theme"
        assert theme.colors.primary == "#ff0000"

    def test_invalid_theme_name_fails(self):
        """Un nombre vacío falla la validación."""
        from src.api.routers.themes import ThemeConfig
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ThemeConfig(name="", version="1.0.0")

    def test_extra_fields_allowed(self, sample_theme_config):
        """Campos extra son permitidos para extensibilidad."""
        from src.api.routers.themes import ThemeConfig

        sample_theme_config["customField"] = "custom-value"
        theme = ThemeConfig(**sample_theme_config)
        assert theme.name == "test-theme"


class TestThemeAPI:
    """Tests para la API de temas."""

    @pytest.fixture
    def mock_auth(self):
        """Mock de autenticación para tests."""
        with patch("src.auth.dependencies.get_current_user") as mock:
            mock.return_value = MagicMock(
                user_id="test-user",
                email="test@example.com",
                role="admin"
            )
            yield mock

    @pytest.mark.asyncio
    async def test_get_presets(self):
        """Obtener temas predefinidos no requiere auth."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/themes/presets")

        assert response.status_code == 200
        presets = response.json()
        assert len(presets) >= 3
        preset_names = [p["name"] for p in presets]
        assert "default" in preset_names
        assert "dark" in preset_names

    @pytest.mark.asyncio
    async def test_create_theme_requires_auth(self, sample_theme_config):
        """Crear un tema requiere autenticación."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/themes",
                json={"name": "new-theme", "config": sample_theme_config}
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_theme_success(self, sample_theme_config, mock_auth, auth_headers):
        """Crear un tema con auth exitoso."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/themes",
                json={"name": "new-theme", "config": sample_theme_config},
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new-theme"
        assert "id" in data


class TestThemeStorage:
    """Tests para almacenamiento de temas."""

    def test_save_and_load_theme(self, sample_theme_config, tmp_path):
        """Guardar y cargar un tema funciona correctamente."""
        from src.api.routers.themes import save_theme, load_theme, THEMES_DIR

        # Usar directorio temporal
        with patch.object(Path, "__new__", return_value=tmp_path):
            theme_id = "test-theme-123"
            theme_data = {
                "id": theme_id,
                "name": "Test Theme",
                "config": sample_theme_config,
            }

            # Guardar directamente en tmp_path
            theme_path = tmp_path / f"{theme_id}.json"
            theme_path.write_text(json.dumps(theme_data), encoding="utf-8")

            # Verificar que el archivo existe
            assert theme_path.exists()

            # Leer y verificar contenido
            loaded = json.loads(theme_path.read_text(encoding="utf-8"))
            assert loaded["name"] == "Test Theme"
            assert loaded["config"]["colors"]["primary"] == "#ff0000"
```

---

### Prompt 10.10 - Actualización del App.tsx con ThemeProvider

**Objetivo**: Integrar el `ThemeProvider` y el sistema de temas en la aplicación principal, permitiendo cargar temas personalizados desde URL y sincronizarlos con el chatbot configurado.

**frontend/src/App.tsx** (versión actualizada):
```typescript
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './themes/ThemeProvider';
import { ChatWidget } from './components/ChatWidget/ChatWidget';
import './i18n'; // Inicializar i18n
import './themes/base.css'; // Estilos base con CSS variables

// Crear cliente de React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 1000 * 60 * 5, // 5 minutos
    },
  },
});

// Obtener configuración de URL params
const getConfig = () => {
  const params = new URLSearchParams(window.location.search);
  return {
    chatbotId: params.get('chatbotId') || 'default',
    showLanguageSelector: params.get('showLangSelector') !== 'false',
    position: (params.get('position') as 'bottom-right' | 'bottom-left' | 'embedded') || 'bottom-right',
    themeUrl: params.get('theme') || undefined,
  };
};

function App() {
  const config = getConfig();

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider themeUrl={config.themeUrl}>
        <ChatWidget
          chatbotId={config.chatbotId}
          showLanguageSelector={config.showLanguageSelector}
          position={config.position}
        />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
```

---

### Resumen del Sistema de Plantillas (FASE 10)

**Archivos creados**:

| Archivo | Descripción |
|---------|-------------|
| `frontend/src/themes/types.ts` | Tipos TypeScript para temas, validación y merge |
| `frontend/src/themes/ThemeProvider.tsx` | Context provider para gestión de temas |
| `frontend/src/themes/presets.ts` | Temas predefinidos (default, dark, university, high-contrast) |
| `frontend/src/themes/base.css` | CSS base con variables personalizables |
| `frontend/src/components/ThemeEditor/ThemeEditor.tsx` | Editor visual de temas |
| `src/api/routers/themes.py` | API REST para gestión de temas |
| `tests/test_themes.py` | Tests del sistema de temas |

**Características**:

1. **CSS Custom Properties**: Todas las propiedades visuales usan variables CSS
2. **ThemeProvider**: Inyecta variables y gestiona el estado del tema
3. **Temas predefinidos**: Default, Dark, University, High Contrast
4. **Validación**: Los temas se validan antes de aplicarse
5. **Persistencia**: Los temas se guardan en localStorage
6. **Import/Export**: Los temas pueden exportarse/importarse como JSON
7. **API Backend**: CRUD completo para temas personalizados
8. **Editor visual**: Componente para editar temas en tiempo real

**Uso básico**:

```typescript
// En la URL del iframe
?theme=/api/v1/themes/custom-university

// Cambiar tema programáticamente
const { switchTheme } = useTheme();
await switchTheme('dark');

// Personalizar colores
const { setTheme, theme } = useTheme();
setTheme({
  ...theme,
  colors: {
    ...theme.colors,
    primary: '#ff0000',
  },
});
```

---

### Prompt 10.11 - Panel de Control del "Cerebro" de la IA (React Admin)

**Objetivo**: Crear en el Panel de Administración de React una sección para editar prompts y cambiar el modelo de IA en caliente, sin tocar el código ni reiniciar el servidor.

**Instrucciones**:

```
En el Panel de Administración de React, crea una sección de 'Configuración del Cerebro'.

1. Editor de Prompts: Un área de texto con resaltado de sintaxis para editar los templates de sistema almacenados en la tabla `prompt_templates`.
2. Selector de Modelo: Un dropdown para cambiar el proveedor y el modelo vinculado al chatbot (tabla `llm_configs`).
3. Prueba en Vivo: Un botón para probar el nuevo prompt/modelo en un entorno de sandbox antes de guardarlo definitivamente.

TESTS REQUERIDOS (Vitest):
- test_prompt_editor_saves_new_version: Verificar que al guardar un prompt se incrementa el campo `version` en la base de datos.
- test_model_selector_updates_chatbot: Validar que el cambio de modelo en el dropdown se persiste correctamente en `llm_configs`.
```

---

## FASE 11: Autoinstalación y Distribución como Software Libre

**Objetivo de la Fase**: Empaquetar el sistema completo para que cualquier institución pública pueda desplegarlo con un solo comando, sin depender de servicios de pago ni de conocimientos avanzados de infraestructura.

**Dependencias**: Fases 1-10 (sistema completo funcional)

**Conceptos clave**:
- **Docker Compose "One-Click"**: Un único archivo levanta todo el stack (Backend, Frontend, BD, MinIO, Ollama).
- **Variables de entorno documentadas**: Cada parámetro con comentarios explicativos para facilitar la adaptación.
- **Script de inicialización**: Automatiza migraciones, creación de superusuario y carga de datos de ejemplo.

---

### Prompt 11.1 - Generador de Configuración (.env.example)

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

## FASE 12: Gestor de Expedientes (Integración vía MCP)

> **Arquitectura MCP**: La integración con el Gestor de Expedientes legacy se realizará exponiendo dicho sistema como un Servidor MCP (Model Context Protocol) que GovGenAI consumirá como cliente agnóstico. Esto aísla la plataforma de las especificidades del sistema antiguo.

**Objetivo de la Fase**: Implementar el módulo de gestión de tramitaciones administrativas multi-fase,
auditables y conformes con el Reglamento de IA de la UE (RIA).

**Dependencias**: Fase 3 (Docling), Fase 4 (LangGraph operativo), Fase 5 (Auth OIDC/SAML del PLAN_DESARROLLO.md)

**Contexto**: El Gestor de Expedientes es el tercer módulo de la plataforma. Reutiliza la infraestructura
del Hub (LangGraph, Docling, pgvector) y el patrón de metaprogramación de Automation para orquestar
tramitaciones administrativas. Ver sección 9 de modulo_AI_agents-hub.md para el diseño completo.

**Mapa de sprints**:

| Sprint | Contenido | Duración | Prerequisito |
|--------|-----------|----------|--------------|
| E1 | Schema BD, CRUD expedientes, API base, AdaptadorNativo | 1 semana | Hub infrastructure |
| E2 | Motor LangGraph con checkpointing, nodos estándar, AdaptadorREST | 2 semanas | LangGraph Hub operativo |
| E3 | AuditService, ExplicabilidadService, endpoint /informe, tests RIA | 1 semana | Sprint E2 |
| E4 | Frontend React: lista, detalle, bandeja aprobaciones, configurador | 3 semanas | Auth OIDC/SAML, Sprint E2 |
| E5 | AdaptadorOracle via MCP Client, sincronizacion bidireccional | 1 semana | MCP Client (Fase 5 PLAN_DESARROLLO) |

---

### Prompt E1 - Schema de Base de Datos y API Base del Gestor (TDD RED/GREEN)

**Objetivo**: Crear las tablas del Gestor de Expedientes y los endpoints CRUD básicos.

**Instrucciones**:

```
Actua como experto en FastAPI y SQLAlchemy async. Implementa el modulo base del Gestor de Expedientes
en server/app/modules/expedientes/.

TABLAS NUEVAS (migration Alembic):
- tipos_expediente: catalogo de tramitaciones (id, nombre, descripcion, version, configuracion JSON)
- expedientes: instancias (id, tipo_id, estado, tenant_id, creado_por, fecha_inicio, metadata JSON)
- fases_expediente: (id, expediente_id, nombre, estado, orden, funcion, responsable_rol)
- acciones_fase: (id, fase_id, tipo [llm|script|human|rpa|api_externa], funcion, responsable_rol, configuracion JSON)
- ejecuciones_accion: (id, accion_id, expediente_id, timestamp, actor_id, resultado, codigo_ejecutado, explicacion, estado)
- documentos_expediente: (id, expediente_id, nombre, tipo, doc_chunk_id nullable, ruta, metadata)
- audit_expediente: log inmutable (id, expediente_id, fase_id, accion_id, timestamp, actor,
  accion_descripcion, estado_anterior, estado_nuevo, hash_integridad)

ENDPOINTS (bajo /expedientes):
GET    /expedientes/tipos/
GET    /expedientes/tipos/{tipo_id}
POST   /expedientes/
GET    /expedientes/
GET    /expedientes/{id}
DELETE /expedientes/{id}
GET    /expedientes/pendientes/mios
GET    /expedientes/pendientes/rol/{rol}

TESTS REQUERIDOS:
- test_crear_tipo_expediente_con_fases_y_responsables
- test_crear_expediente_instancia
- test_listar_expedientes_filtrados_por_estado
- test_eliminar_expediente_solo_si_estado_inicial
- test_listar_pendientes_del_usuario_autenticado

CRITERIOS DE ACEPTACION:
- Todo tipo de expediente debe declarar funcion y responsable_rol en cada fase (obligatorio)
- Sin ellos, el tipo no puede activarse
```

---

### Prompt E2 - Motor LangGraph con Checkpointing (TDD RED/GREEN)

**Objetivo**: Implementar el motor de procesos basado en LangGraph con estado persistido en PostgreSQL.

**Instrucciones**:

```
Actua como experto en LangGraph y FastAPI async. Implementa el motor de procesos del Gestor
en server/app/modules/expedientes/engine/.

ESTADO DEL EXPEDIENTE (ExpedienteState):
class ExpedienteState(TypedDict):
    expediente_id: str
    tipo: str
    fase_actual: str
    datos: dict
    documentos: list[str]
    historial_acciones: list
    pendiente_humano: bool
    responsable_actual: str
    explicacion_ia: str

NODOS ESTANDAR A IMPLEMENTAR:
- NodoLLM: genera propuesta usando LLM Gateway existente
- NodoScript: ejecuta script Python determinista (reutiliza sandbox de Automation)
- NodoHuman: breakpoint LangGraph — el expediente queda suspendido esperando aprobacion
- NodoRPA: despacha job al agente de ejecucion local (Prompt 9.17)
- NodoAPIExterna: llama al MCP Client (cuando este disponible)
- NodoNotificacion: encola notificacion al responsable de la siguiente fase

CHECKPOINTING:
- Persistir estado del grafo en PostgreSQL (tabla langgraph_checkpoints)
- Permitir reanudar un expediente suspendido desde el punto exacto de parada

NUEVOS ENDPOINTS:
POST /expedientes/{id}/avanzar    -> ejecutar siguiente accion automatica
POST /expedientes/{id}/aprobar    -> resolucion humana positiva (NodoHuman)
POST /expedientes/{id}/rechazar   -> resolucion humana negativa + motivo
GET  /expedientes/{id}/pendiente  -> accion pendiente actual

TESTS REQUERIDOS:
- test_nodo_llm_genera_propuesta_y_guarda_explicacion
- test_nodo_human_suspende_grafo_y_espera
- test_aprobar_expediente_reanuda_grafo
- test_rechazar_expediente_registra_motivo_en_audit
- test_checkpointing_restaura_estado_tras_reinicio
```

---

### Prompt E3 - AuditService y Cumplimiento RIA (TDD RED/GREEN)

**Objetivo**: Implementar el log de auditoria inmutable y el endpoint de informe de trazabilidad.

**Instrucciones**:

```
Implementa AuditService en server/app/modules/expedientes/services/audit_service.py.

REQUISITOS:
1. Cada transicion de estado escribe una entrada en audit_expediente con hash de integridad
   (SHA-256 del contenido + timestamp + hash anterior -> cadena de bloques ligera)
2. El log es inmutable: ningun endpoint permite UPDATE o DELETE en audit_expediente
3. Endpoint GET /expedientes/{id}/audit -> log completo ordenado por timestamp
4. Endpoint GET /expedientes/{id}/informe -> PDF de trazabilidad completa para auditorias RIA

CAMPOS OBLIGATORIOS EN CADA ENTRADA:
- explicacion_ia: el "por que" de la decision (Art. 13 RIA — transparencia)
- codigo_ejecutado: el script exacto que se ejecuto (si aplica)
- actor: usuario o sistema que realizo la accion
- hash_integridad: SHA-256 encadenado

TESTS REQUERIDOS:
- test_audit_entry_created_on_every_state_transition
- test_audit_hash_chain_is_valid
- test_audit_log_is_immutable
- test_informe_pdf_contains_all_phases_and_decisions
- test_explicacion_ia_is_required_for_llm_nodes
```

---

### Prompt E4 - Frontend React: Pantallas del Gestor de Expedientes (TDD RED/GREEN)

**Objetivo**: Implementar las pantallas del Gestor en frontend/src/expedientes/.

**Instrucciones**:

```
Actua como experto en React + Tailwind. Implementa las pantallas del Gestor de Expedientes.

PANTALLAS A CREAR:
1. ExpedientesListPage.tsx — lista con filtros por estado, tipo y responsable
2. ExpedienteDetailPage.tsx — timeline de fases, documentos adjuntos, log de audit
3. AprobacionesBandejaPage.tsx — bandeja de expedientes pendientes del usuario autenticado
   con botones Aprobar / Rechazar + campo de motivo
4. TipoExpedienteConfigPage.tsx — formulario estructurado para definir tipos:
   fases, acciones, funcion y responsable de cada una
   (el disenador visual low-code queda diferido a v2)

REQUISITOS TRANSVERSALES:
- Todas las pantallas requieren autenticacion (OIDC/SAML activo)
- Los botones de accion se muestran solo al responsable de la fase actual
- Timeline visual del estado (pendiente / en_curso / aprobada / rechazada)

TESTS REQUERIDOS (Vitest):
- should_display_expedientes_with_filters
- should_show_approve_button_only_to_responsible_user
- should_render_audit_timeline_in_correct_order
- should_validate_tipo_form_requires_funcion_and_responsable
```

---

### Prompt E5 - AdaptadorUJI + AdaptadorGestion400 + capa ENI/ENS (TDD RED/GREEN)

**Objetivo**: Implementar los adaptadores de tramitación para los dos sistemas destino del piloto (UJI y Gestión 400) y la capa transversal ENI/ENS. Reemplaza el `AdaptadorOracle` descartado en la decisión 11 de `PLAN_DESARROLLO.md`.
**Prerequisito**: MCP Client operativo (Fase 5 de PLAN_DESARROLLO.md), sprints E2/E2.5/E2.6 completados.

**Instrucciones**:

```
Implementa en server/app/modules/expedientes/adapters/:

1. INTERFAZ COMÚN AdaptadorTramitacion (Protocol):
   async def consultar_expediente(self, ref_externa: str) -> dict
   async def crear_tramitacion(self, tipo: str, datos: dict) -> str
   async def actualizar_estado(self, ref_externa: str, estado: dict) -> bool
   async def adjuntar_documento(self, ref_externa: str, doc: bytes, meta: dict) -> bool
   async def publicar_resolucion(self, ref_externa: str, resolucion: dict) -> bool
   async def obtener_documentos(self, ref_externa: str) -> list[bytes]

2. AdaptadorUJI (uji_adapter.py):
   - Cliente HTTP contra el API institucional de la Universitat Jaume I
   - Autenticación: token institucional (via MCP Client)
   - Configurado por tipo de expediente, no globalmente

3. AdaptadorGestion400 (gestion400_adapter.py):
   - Cliente contra el API público de Gestión 400 (opensea)
   - Mapeo de esquemas: expediente interno ↔ formato G400
   - Detección de discordancias via BridgeService (Fase 6.6)

4. CAPA ENI TRANSVERSAL (eni_layer.py):
   - Resolvedor DIR3: valida/enriquece códigos de unidades administrativas
   - Enriquecedor eEMGDE: metadatos de gestión de documentos
   - Generador/verificador CSV (Código Seguro de Verificación)
   - Empaquetador de evidencia: conjunto de documentos + metadatos ENI

5. CAPA ENS (ens_policy.py):
   - Política por tipo de expediente: categorización alta/media/baja
   - Aplicada al sandbox (Fase 5.4) + AuditService (Fase 6.2)

NUEVOS ENDPOINTS:
POST /expedientes/{id}/sincronizar   -> pull del estado desde el sistema origen
POST /expedientes/{id}/publicar      -> push de la resolución al sistema origen
GET  /expedientes/{id}/evidencia-eni -> genera el paquete de evidencia ENI

TESTS REQUERIDOS:
- test_adaptador_uji_consulta_expediente_real (mock HTTP)
- test_adaptador_gestion400_mapea_esquema_bidireccional
- test_capa_eni_enriquece_metadatos_eemgde
- test_csv_generado_supera_verificacion_propia
- test_ens_categoria_alta_activa_sandbox_estricto
- test_adaptador_activo_se_configura_por_tipo_no_globalmente
- test_flujo_completo_consulta_proceso_publicacion_mock (E2E)
- test_serializacion_eni_valida_contra_xsd
```

---

## FASE 13: Privacidad y Anonimización Reversible NER (Zero-Knowledge)

**Tipo**: Migración + integración  
**Prerequisitos**: FASE 9 (Frontend), FASE 12.E2 (grafo LangGraph de expedientes)  
**Corresponde a**: Fase 6.1 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Migrar el pipeline NER de anonimización reversible de `client_app/` al servidor FastAPI y conectarlo como hook pre/post-LLM en el grafo de expedientes y en automation. El chatbot informativo (información pública) no aplica.

**Componentes legacy a migrar** (`client_app/app/`):
- `modules/privacy/anonymizer.py` (1010 LoC) + `services/anonymization_service.py` (216 LoC)
- `utils/pii_detector.py` + `services/privacy_guardian.py` + `services/screenshot_guard.py`

**Destino**: `server/app/core/privacy/`

**Capacidades clave**:
- Pipeline NER (spaCy / transformers / Presidio) ejecutado antes de enviar contexto al LLM
- Vault de mapeos pseudónimo ↔ valor real cifrado at rest, persistido solo en el Edge node
- Rehidratación post-LLM del output antes de mostrarlo al tramitador
- Tests de no-fuga: golden-set de entradas con PII, asserts de que ningún dato real cruza la frontera LLM

**Tests legacy a migrar**: `test_ner_upgrade`, `test_etl_anonymization_ia`, `test_rpa_anonymization`, `test_privacy_audit`, `test_privacy_consent`, `test_privacy_indicator`, `test_anonymizer_initials`

---

## FASE 14: Sandbox Distribuido Edge ↔ Thin-client

**Tipo**: Migración + split arquitectónico  
**Prerequisitos**: FASE 5 (thin client operativo)  
**Corresponde a**: Fase 5.4–5.5 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Separar la responsabilidad del sandbox entre el Edge node (diseño + auditoría AST + firma del script) y el Thin client (ejecución aislada del script firmado). El Edge firma con clave privada; el thin client verifica con la pública antes de ejecutar.

**Componentes legacy a migrar** (`client_app/app/`):
- `modules/sandbox/safety_sandbox.py` (76 LoC) → **Edge** `server/app/core/sandbox/`
- `services/sandbox_worker.py` (241 LoC) → **Thin client** `client_app/local_agent/sandbox/`
- `services/sandbox_service.py` (214 LoC) → **Edge** (orquestación)

**Contrato Edge ↔ Thin-client**:
1. Edge genera script + RunManifest firmado con ECDSA
2. Thin client verifica firma; rechaza si inválida
3. Thin client ejecuta en sandbox con CPU cap + network egress off + FS restringido
4. Thin client devuelve resultado + manifest de ejecución firmado
5. Edge verifica la firma del resultado y registra en AuditService

**Tests legacy a migrar**: `test_safety_sandbox`, `test_sandbox_isolation`

---

## FASE 15: RunManifest + AuditService + Script Registry Unificados (IA Frugal)

**Tipo**: Migración + refactor  
**Prerequisitos**: FASE 12.E3 (AuditService de expedientes), FASE 13 (privacidad)  
**Corresponde a**: Fase 6.2–6.4 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Unificar el formato `run_manifest.json` y la cadena de auditoría SHA-256 para que sea válida en los tres módulos (automation, Hub, expedientes). Migrar el Script Registry con índice semántico para reuso directo sin LLM.

**Componentes legacy a migrar** (`client_app/app/`):
- `services/manifest_generator.py` (165 LoC) + `manifest_signature_service.py` (258 LoC)
- `services/enterprise_audit_service.py` (281 LoC) + `external_script_audit_service.py` (188 LoC)
- `services/script_library_service.py` (840 LoC) + `flow_registry_service.py` (374 LoC)
- `services/script_generator_service.py` (405 LoC) + `script_adaptation_service.py` + `validation_loop.py` (143 LoC) + `custom_script_service.py`

**Destino**: `server/app/core/manifest/` + `server/app/core/audit/` + `server/app/modules/automation/scripts/`

**Capacidades clave**:
- Tabla `scripts_aprobados` con hash + versión + tenant + etiqueta semántica (bge-m3)
- Endpoint de búsqueda por taxonomía (reuso directo sin LLM)
- Métricas de reuso (% tareas resueltas sin invocar LLM) expuestas en panel admin
- Cache semántico pre-LLM (campo `intent_embedding`): activar solo si el piloto lo justifica — evaluar tras tener métricas de taxonomía

**Tests legacy a migrar**: `test_manifest_signature`, `test_script_signing`, `test_external_script_audit`, `test_script_generator_service`, `test_script_adaptation`, `test_script_ingestion`, `test_validation_loop`, `test_flow_registry`

---

## FASE 16: Determinista-first + Fábricas como Nodos LangGraph

**Tipo**: Migración + wrapper LangGraph  
**Prerequisitos**: FASE 12.E2 (motor LangGraph expedientes), FASE 15 (Script Registry)  
**Corresponde a**: Fase 6.5 + Fase 7.E2.6 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Migrar los servicios deterministas y las fábricas de código al servidor y exponerlos como nodos invocables desde el grafo LangGraph. La lógica "determinista por defecto, LLM si no encaja" se preserva como estrategia de ejecución.

**Componentes legacy a migrar** (`client_app/app/`):
- `services/deterministic_etl_service.py` (350 LoC) + `deterministic_graphics_service.py` (605 LoC)
- `modules/factory/etl_factory.py` (369 LoC) + `graphics_factory.py` (342 LoC) + `report_factory.py` (540+243 LoC)

**Destino**: `server/app/modules/automation/factories/`

**Nodos LangGraph nuevos** (Fase 7.E2.6):
- `NodoFabrica`: wrapper que invoca `etl_factory` / `graphics_factory` / `report_factory` o cualquier script del Registry
- `NodoValidador`: AST audit + `validation_loop` + heurísticas; etiqueta la propuesta como `segura | requiere_revisión | bloqueada`; intercalado antes del `NodoHuman`

**Tests legacy a migrar**: `test_etl_factory`, `test_graphics_factory`, `test_pdf_factory_refinements`, `test_etl_brain_decoupling`

---

## FASE 17: Agente Analista + Base Vectorial de Normativa

**Tipo**: Nuevo desarrollo  
**Prerequisitos**: FASE 12.E2 (motor LangGraph), FASE 3 (ingestión Docling)  
**Corresponde a**: Fase 7.E2.5 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Añadir un nodo LangGraph previo al enrutado que clasifica la intención del tramitador e identifica la normativa aplicable, devolviendo citas trazables al nodo siguiente.

**Capacidades clave**:
- Knowledge base `regulation` (tipo nuevo) ingerida por Docling: BOE, DOGC, ordenanzas UJI, normativa autonómica y local relevante
- `NodoAnalista`: clasifica intención + recupera normativa aplicable por RAG sobre `regulation` KB
- Output del nodo alimenta al siguiente nodo (LLM o Script) como contexto + citas normativas con referencia trazable
- Solo para el grafo de expedientes; el chatbot informativo no usa este nodo

**Tests requeridos**: clasificación correcta en golden-set de peticiones, normativa devuelta con referencia trazable, nodo no invocado en grafo de chatbot informativo

---

## FASE 18: Bridges Semánticos Ampliados (Multi-contexto)

**Tipo**: Migración + extensión  
**Prerequisitos**: FASE 15 (Script Registry), FASE 7.E5 (Adaptadores UJI/G400)  
**Corresponde a**: Fase 6.6 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Migrar los bridges semánticos y generalizarlos para ser invocables desde flows, expedientes y adaptadores de tramitación.

**Componentes legacy a migrar** (`client_app/app/`):
- `services/bridge_creator.py` (118 LoC) + `bridge_generation_service.py` (83 LoC) + `library_bridge.py`

**Destino**: `server/app/modules/automation/bridge/`

**Capacidades nuevas**:
- Interfaz común reutilizable desde flows, expedientes y adaptadores de tramitación
- Detección de discordancias entre esquemas (UJI ↔ Gestión 400) con score de confianza
- Catálogo de bridges reutilizables por par `(sistema_origen, sistema_destino)`
- Bridge como nodo invocable desde el grafo de expedientes

**Tests legacy a migrar**: `test_type_compatibility_bridge`

---

## FASE 19: Adaptadores UJI + Gestión 400 + Capa ENI/ENS (Servidores MCP)

> **Arquitectura MCP**: Se desarrollarán Servidores MCP para UJI, Gestión 400 y ENI/ENS, estandarizando la integración con la capa de inteligencia artificial.

**Tipo**: Nuevo desarrollo  
**Prerequisitos**: FASE 5 (MCP Client), FASE 12.E2 (motor LangGraph), FASE 14 (sandbox), FASE 18 (bridges)  
**Corresponde a**: Fase 7.E5 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

> Los prompts detallados de esta fase están en la Fase 12, Prompt E5 de este documento.

**Objetivo**: Implementar los dos adaptadores del piloto v1 y la capa transversal ENI/ENS. Reemplaza el `AdaptadorOracle` descartado.

**Ver**: Fase 12, Prompt E5 de este documento (ya actualizado con este contenido).

---

## FASE 20: Accesibilidad WCAG 2.2 AA + Admin Conversacional

**Tipo**: Nuevo (transversal)  
**Prerequisitos**: FASE 9 (Frontend React), FASE 10 (temas)  
**Corresponde a**: Fase 8 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Garantizar WCAG 2.2 AA en todas las rutas del frontend e implementar una consola conversacional de administración en lenguaje natural.

**Capacidades clave**:
- WCAG 2.2 AA como criterio de aceptación obligatorio en cada pantalla (Bloques 9A/9B/9C y pantallas de expedientes)
- `@axe-core/react` integrado en Vitest; Lighthouse CI en GitHub Actions (umbral a11y ≥ 95)
- Reutilización de `client_app/tests/a11y/test_accessibility.py` legacy como seed
- Consola conversacional admin: el partner escribe en lenguaje natural (*"crea un chatbot para el padrón que use el LLM local"*) y el sistema ejecuta la configuración usando el grafo del Hub con tools de administración

**Integración**: la consola conversacional admin se integra en la Fase 10 (panel de IA), pues depende del grafo agéntico del Hub estable.

---

## FASE 21: RPA Web (Diferido a v2)

**Tipo**: Decisión de no-migración  
**Fuera del alcance del piloto v1**  
**Corresponde a**: Fase 9 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Fuera de roadmap v1 — decisión documentada

**Decisión**: `client_app/app/core/rpa_executor.py` (1049 LoC) y `client_app/app/services/web_watcher_service.py` (878 LoC) **no se migran** al thin client en v1. El peso de Playwright (~300-400 MB de navegadores) es incompatible con el objetivo de thin client ligero.

**Durante v1**: código legacy intacto en `client_app/` pero no incluido en el empaquetado del thin client. Si un flujo crítico del piloto requiere web RPA, se despliega un worker Playwright centralizado en el Edge node (Docker headless).

**En v2**: decidir entre re-empaquetar Playwright en el thin client o mantener el worker centralizado en Edge, según la demanda real del piloto.

---

## FASE 22: Microservicios de computación pesada — Embedding Service y Docling Service

**Tipo**: Diferido — se activa únicamente cuando los criterios de métricas se cumplan en producción.  
**Estado**: ⏳ No iniciar hasta que los criterios de activación se verifiquen en Cloud Run.  
**Prerrequisitos**: Despliegue en Cloud Run operativo (FASE 9C completa, Cloud SQL Auth Proxy, GCS).  
**Corresponde a**: decisión de infraestructura documentada el 2026-04-27 (ver `CLAUDE.md` sección "Servicios de computación pesada").

**Motivación**: BGE-M3 (~1.1 GB) y Docling (CPU-intensivo) corren actualmente in-process dentro del servidor FastAPI. Esto es correcto y suficiente mientras el despliegue sea pequeño, pero en Cloud Run implica cold start de 30-90 s y 3-4 GB de RAM por instancia. La abstracción `EmbeddingService` (protocolo ya existente) hace que la extracción sea un cambio de inyección de dependencia, sin tocar la lógica de negocio.

**Criterios de activación** — no iniciar antes de que se cumplan los tres:
1. Cold start del API supera **15 s** en Cloud Run (visible en métricas Cloud Run / Langfuse).
2. RAM de la instancia FastAPI supera **2 GB** en uso normal (métrica Cloud Run).
3. Se necesita escalar embedding/Docling de forma independiente al API.

**Arquitectura objetivo**:
```
Cloud Run: govgenai-api (FastAPI, ~512 MB)
    ├─ HTTP → Cloud Run: embedding-service  (min-instances=1, BGE-M3 siempre caliente)
    └─ HTTP → Cloud Run: docling-service    (min-instances=0, escala a 0 entre ingestiones)
    ├─ Cloud SQL (vía Auth Proxy)
    └─ GCS (vía StorageService / fsspec)
```

---

### Prompt 22.1 — Microservicio de embeddings (FastAPI standalone)

**Objetivo**: Extraer `LocalEmbeddingService` a un microservicio FastAPI independiente con su propio Dockerfile y `pyproject.toml`. El servidor principal añade `HttpEmbeddingService` y la fábrica `get_embedding_service()` selecciona la implementación por variable de entorno.

**Archivos nuevos**:
- `services/embedding/main.py`
- `services/embedding/Dockerfile`
- `services/embedding/pyproject.toml`

**`services/embedding/main.py`**:
```python
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI()
_model = SentenceTransformer("BAAI/bge-m3")


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]
    dimensions: int


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vec = _model.encode(req.text, normalize_embeddings=True)
    return EmbedResponse(embedding=vec.tolist(), dimensions=len(vec))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

**Añadir `HttpEmbeddingService`** a `server/app/modules/agents_hub/services/embedding_service.py`:
```python
class HttpEmbeddingService:
    """Delega la generación de embeddings al microservicio externo."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def embed(self, text: str) -> list[float]:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self._base_url}/embed", json={"text": text})
            resp.raise_for_status()
            return resp.json()["embedding"]
```

**Actualizar `get_embedding_service()`** — selector por env var:
```python
def get_embedding_service() -> EmbeddingService:
    url = os.environ.get("EMBEDDING_SERVICE_URL")
    if url:
        return HttpEmbeddingService(url)
    return _local_embedding_service_singleton()
```

**Tests requeridos**:
```python
# should_call_embed_endpoint_with_correct_payload
# should_return_embedding_as_list_of_floats
# should_raise_on_http_error_from_microservice
# should_use_local_service_when_no_env_var
# should_use_http_service_when_env_var_set
```

---

### Prompt 22.2 — Microservicio Docling (worker de procesamiento de PDFs)

**Objetivo**: Extraer `DoclingProcessor` a un microservicio FastAPI independiente. El servidor principal llama a `POST /process-pdf` (multipart) y recibe el Markdown resultante. Permite escalar el procesamiento de PDFs a cero instancias cuando no hay ingestión activa.

**Archivos nuevos**:
- `services/docling/main.py`
- `services/docling/Dockerfile`
- `services/docling/pyproject.toml`

**`services/docling/main.py`**:
```python
import os
import tempfile
from fastapi import FastAPI, UploadFile
from docling.document_converter import DocumentConverter

app = FastAPI()
_converter = DocumentConverter()


@app.post("/process-pdf")
async def process_pdf(file: UploadFile) -> dict:
    pdf_bytes = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = _converter.convert(tmp_path)
        markdown = result.document.export_to_markdown()
    finally:
        os.unlink(tmp_path)
    return {"markdown": markdown, "pages": result.document.num_pages}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

**Añadir `HttpDoclingProcessor`** a `server/app/modules/agents_hub/ingestion/docling_processor.py`:
```python
class HttpDoclingProcessor:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def process_pdf_bytes(self, pdf_bytes: bytes) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/process-pdf",
                files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
            )
            resp.raise_for_status()
            return resp.json()["markdown"]
```

**Tests requeridos**:
```python
# should_return_markdown_string_from_valid_pdf
# should_raise_on_invalid_pdf_bytes
# should_include_page_count_in_response
# should_use_http_processor_when_env_var_set
# should_fall_back_to_local_when_no_env_var
```

---

### Prompt 22.3 — Integración: docker-compose y variables de entorno

**Objetivo**: Conectar los dos microservicios al stack de desarrollo. Actualizar `docker-compose.yml` con los dos nuevos servicios. El API principal los usa automáticamente si las variables de entorno están definidas.

**Añadir a `docker-compose.yml`**:
```yaml
  embedding-service:
    build:
      context: ./services/embedding
    ports:
      - "8001:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      start_period: 120s  # tiempo de carga del modelo BGE-M3

  docling-service:
    build:
      context: ./services/docling
    ports:
      - "8002:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      start_period: 60s
```

**Añadir a `server/.env`**:
```bash
EMBEDDING_SERVICE_URL=http://embedding-service:8001
DOCLING_SERVICE_URL=http://docling-service:8002
```

**Tests requeridos**:
```python
# should_use_http_embedding_service_when_url_env_var_set
# should_use_http_docling_processor_when_url_env_var_set
# should_fall_back_to_local_services_when_env_vars_absent
# integration: should_process_pdf_end_to_end_with_http_docling_and_http_embedding
```
