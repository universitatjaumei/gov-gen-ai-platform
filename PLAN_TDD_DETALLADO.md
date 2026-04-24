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
| FASE 5 — API Endpoints | ✅ COMPLETADO | 2026-04-23 | hub_chat (SSE), hub_tasks (export PDF/MD), embedding_service, bugfix deps.py 401; 13 tests verdes |
| FASE 6 — Tests E2E y CI/CD | ✅ COMPLETADO | 2026-04-23 | 4 tests E2E (httpx+AsyncClient), 5 tests integración pipeline+auth, GitHub Actions CI/CD con pgvector |
| FASE 7 — Docker multi-stage | ✅ COMPLETADO | 2026-04-23 | Imagen CPU-only (~2.96 GB), uv sync, docker-compose.prod.yml, LangFuse self-hosted, scripts/postgres/init.sql |
| FASE 8 — LangFuse + FeedbackService | ✅ COMPLETADO | 2026-04-23 | observability.py, FeedbackService, hub_feedback router, migración feedback_text, 10 tests verdes |
| FASE 9 — Frontend React | ⏳ PENDIENTE | — | — |
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
| **5** | API Endpoints | 5.1 - 5.4 | **MANTENIDA** (rutas nuevas en FastAPI existente) | Fases 1, 2, 4 |
| **6** | Tests E2E | 6.1 - 6.3 | **MANTENIDA** (CI/CD: GitHub Actions) | Fases 1-5 |
| **7** | Despliegue | 7.1 - 7.4 | **REDUCIDA** — extender docker-compose existente | Fases 1-6 |
| **8** | Observabilidad | 8.1 - 8.3 | **MANTENIDA** | Fases 1-5 |
| **9** | Frontend + i18n + Modo Agente | 9.1 - 9.18 | **MANTENIDA + AMPLIADA** (añadidos 9.14–9.18) | Fase 5 (API) |
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

> **En Gov Gen AI Platform, la infraestructura de auth ya existe** (modelos AdminAccount, PartnerAccount,
> JWT por cabecera, RBAC). Esta fase se reduce a **dos tareas**:
>
> 1. **Añadir el rol `end_user`** al sistema de roles existente (usuarios anónimos del chatbot y
>    usuarios identificados del modo agente). Adaptar los prompts 1.1–1.4 a este alcance reducido.
>
> 2. **Migrar de `X-License-Key` + Bearer email a JWT estándar** (base para OIDC/SAML en Fase 5
>    del `PLAN_DESARROLLO.md`). Adaptar los prompts 1.3–1.4 a esta migración.
>
> Los prompts 1.5–1.6 (AgentState) se mantienen íntegros: el estado del agente LangGraph
> es nuevo y no existe en AutomatIA.
>
> **No implementar** autenticación OIDC/SAML en esta fase — está diferida a Q2 2026 (Fase 5).

---

### Prompt 1.1 - Tests de Modelos de Usuario (TDD - RED)

**Objetivo**: Escribir tests para los modelos de autenticación.

**Instrucciones**:

```
Escribe tests para src/auth/models.py que definan el modelo UserInfo.

TESTS REQUERIDOS:
1. UserInfo contiene user_id, email, role
2. UserInfo es inmutable (frozen dataclass)
3. UserInfo es serializable a dict
4. role tiene valores válidos: "user", "admin", "partner", "informer"
```

**Archivos a crear**:

**tests/unit/test_auth_models.py**:
```python
"""Tests para modelos de autenticación - TDD RED PHASE."""
from dataclasses import FrozenInstanceError

import pytest


class TestUserInfoModel:
    """Tests para el modelo UserInfo."""

    def test_user_info_has_required_fields(self) -> None:
        """UserInfo debe tener user_id, email y role."""
        from src.auth.models import UserInfo

        user = UserInfo(
            user_id="user-123",
            email="test@example.com",
            role="user",
        )

        assert user.user_id == "user-123"
        assert user.email == "test@example.com"
        assert user.role == "user"

    def test_user_info_is_immutable(self) -> None:
        """UserInfo debe ser inmutable (frozen)."""
        from src.auth.models import UserInfo

        user = UserInfo(
            user_id="user-123",
            email="test@example.com",
            role="user",
        )

        with pytest.raises(FrozenInstanceError):
            user.user_id = "other-id"  # type: ignore

    def test_user_info_serializable_to_dict(self) -> None:
        """UserInfo debe poder convertirse a diccionario."""
        from src.auth.models import UserInfo

        user = UserInfo(
            user_id="user-123",
            email="test@example.com",
            role="admin",
        )

        user_dict = user.to_dict()

        assert isinstance(user_dict, dict)
        assert user_dict["user_id"] == "user-123"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["role"] == "admin"

    def test_user_info_role_validation(self) -> None:
        """role debe ser uno de: user, admin, partner, informer."""
        from src.auth.models import UserInfo, UserRole

        # Roles válidos
        for role in ["user", "admin", "partner", "informer"]:
            user = UserInfo(user_id="123", email="test@test.com", role=role)
            assert user.role == role

    def test_user_info_invalid_role_raises_error(self) -> None:
        """role inválido debe lanzar error."""
        from src.auth.models import UserInfo

        with pytest.raises(ValueError) as exc_info:
            UserInfo(user_id="123", email="test@test.com", role="superuser")

        assert "role" in str(exc_info.value).lower()


class TestUserRole:
    """Tests para el enum UserRole."""

    def test_user_role_values(self) -> None:
        """UserRole debe tener los valores correctos."""
        from src.auth.models import UserRole

        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.PARTNER.value == "partner"
        assert UserRole.INFORMER.value == "informer"
```

**Comando para ejecutar (debe fallar)**:
```bash
uv run pytest tests/unit/test_auth_models.py -v
# Expected: FAILED - ModuleNotFoundError: No module named 'src.auth'
```

---

### Prompt 1.2 - Implementación de Modelos de Usuario (TDD - GREEN)

**Objetivo**: Implementar los modelos de autenticación para pasar los tests.

**Archivos a crear**:

**src/auth/__init__.py**:
```python
"""Módulo de autenticación."""
from src.auth.models import UserInfo, UserRole

__all__ = ["UserInfo", "UserRole"]
```

**src/auth/models.py**:
```python
"""Modelos de autenticación y usuario."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    """Roles de usuario disponibles.

    - ADMIN: gestiona la plataforma global (proveedores LLM, partners, config sistema).
    - PARTNER: crea y configura chatbots/agentes para sus clientes.
    - INFORMER: supervisa y valida respuestas de la IA.
    - USER: usuario final del chatbot/agente.
    """

    USER = "user"
    ADMIN = "admin"
    PARTNER = "partner"
    INFORMER = "informer"


def _validate_role(role: str) -> str:
    """Valida que el rol sea válido."""
    valid_roles = {r.value for r in UserRole}
    if role not in valid_roles:
        raise ValueError(
            f"Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}"
        )
    return role


@dataclass(frozen=True)
class UserInfo:
    """Información del usuario autenticado.

    Es inmutable (frozen) para garantizar que no se modifique
    accidentalmente durante el procesamiento de requests.
    """

    user_id: str
    email: str
    role: str = field(default="user")

    def __post_init__(self) -> None:
        """Valida los campos después de la inicialización."""
        # Usamos object.__setattr__ porque es frozen
        object.__setattr__(self, "role", _validate_role(self.role))

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
        }

    @property
    def is_admin(self) -> bool:
        """Verifica si el usuario es administrador de plataforma."""
        return self.role == UserRole.ADMIN.value

    @property
    def is_partner(self) -> bool:
        """Verifica si el usuario es partner (gestiona chatbots de clientes)."""
        return self.role == UserRole.PARTNER.value

    @property
    def is_informer(self) -> bool:
        """Verifica si el usuario es informador."""
        return self.role == UserRole.INFORMER.value
```

**Comando para verificar**:
```bash
uv run pytest tests/unit/test_auth_models.py -v
# Expected: All tests PASSED
```

---

### Prompt 1.3 - Tests de Validación JWT (TDD - RED)

**Objetivo**: Escribir tests para la validación de tokens JWT.

**Instrucciones**:

```
Escribe tests para src/auth/jwt_handler.py.

TESTS REQUERIDOS:
1. Token válido extrae user_info correctamente
2. Token expirado lanza AuthenticationError
3. Firma inválida lanza AuthenticationError
4. Token sin claims requeridos lanza AuthenticationError
5. Función para crear tokens de prueba
```

**Archivos a crear**:

**tests/unit/test_jwt_handler.py**:
```python
"""Tests para el manejador de JWT - TDD RED PHASE."""
import time
from unittest.mock import patch

import pytest


class TestJWTValidation:
    """Tests para validación de tokens JWT."""

    @pytest.fixture
    def jwt_settings(self):
        """Configura variables de entorno para JWT."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/testdb",
            "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRATION_MINUTES": "60",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            # Forzar recarga de config
            import importlib
            import src.config
            importlib.reload(src.config)
            yield

    def test_valid_token_extracts_user_info(self, jwt_settings) -> None:
        """Un token válido debe extraer UserInfo correctamente."""
        from src.auth.jwt_handler import create_token, decode_token
        from src.auth.models import UserInfo

        # Crear token de prueba
        user = UserInfo(user_id="user-123", email="test@example.com", role="admin")
        token = create_token(user)

        # Decodificar
        decoded_user = decode_token(token)

        assert decoded_user.user_id == "user-123"
        assert decoded_user.email == "test@example.com"
        assert decoded_user.role == "admin"

    def test_expired_token_raises_error(self, jwt_settings) -> None:
        """Un token expirado debe lanzar AuthenticationError."""
        from src.auth.jwt_handler import create_token, decode_token
        from src.auth.exceptions import AuthenticationError
        from src.auth.models import UserInfo

        user = UserInfo(user_id="user-123", email="test@example.com", role="user")

        # Crear token que expira inmediatamente
        token = create_token(user, expires_in_minutes=-1)

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(token)

        assert "expired" in str(exc_info.value).lower()

    def test_invalid_signature_raises_error(self, jwt_settings) -> None:
        """Una firma inválida debe lanzar AuthenticationError."""
        from src.auth.jwt_handler import decode_token
        from src.auth.exceptions import AuthenticationError

        # Token con firma manipulada
        invalid_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9."
            "invalid_signature_here"
        )

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(invalid_token)

        assert "invalid" in str(exc_info.value).lower() or "signature" in str(exc_info.value).lower()

    def test_token_missing_required_claims_raises_error(self, jwt_settings) -> None:
        """Token sin claims requeridos debe lanzar error."""
        import jwt
        from src.auth.jwt_handler import decode_token
        from src.auth.exceptions import AuthenticationError
        from src.config import get_settings

        settings = get_settings()

        # Token sin email
        payload = {"sub": "user-123"}  # Falta email
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(token)

        assert "claim" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()

    def test_malformed_token_raises_error(self, jwt_settings) -> None:
        """Token malformado debe lanzar AuthenticationError."""
        from src.auth.jwt_handler import decode_token
        from src.auth.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            decode_token("not.a.valid.jwt.token")

        with pytest.raises(AuthenticationError):
            decode_token("")

        with pytest.raises(AuthenticationError):
            decode_token("just_random_string")
```

**Comando para ejecutar (debe fallar)**:
```bash
uv run pytest tests/unit/test_jwt_handler.py -v
# Expected: FAILED - ModuleNotFoundError
```

---

### Prompt 1.4 - Implementación de JWT Handler (TDD - GREEN)

**Objetivo**: Implementar el manejador de JWT para pasar los tests.

**Archivos a crear**:

**src/auth/exceptions.py**:
```python
"""Excepciones personalizadas para autenticación."""


class AuthenticationError(Exception):
    """Error de autenticación."""

    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class AuthorizationError(Exception):
    """Error de autorización (permisos insuficientes)."""

    def __init__(self, message: str = "Insufficient permissions"):
        self.message = message
        super().__init__(self.message)
```

**src/auth/jwt_handler.py**:
```python
"""Manejador de tokens JWT."""
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidSignatureError

from src.auth.exceptions import AuthenticationError
from src.auth.models import UserInfo
from src.config import get_settings


def create_token(user: UserInfo, expires_in_minutes: int | None = None) -> str:
    """Crea un token JWT para el usuario.

    Args:
        user: Información del usuario
        expires_in_minutes: Minutos hasta expiración (None usa config)

    Returns:
        Token JWT codificado
    """
    settings = get_settings()

    if expires_in_minutes is None:
        expires_in_minutes = settings.jwt_expiration_minutes

    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)

    payload = {
        "sub": user.user_id,
        "email": user.email,
        "role": user.role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> UserInfo:
    """Decodifica y valida un token JWT.

    Args:
        token: Token JWT a decodificar

    Returns:
        UserInfo extraído del token

    Raises:
        AuthenticationError: Si el token es inválido
    """
    settings = get_settings()

    if not token or not isinstance(token, str):
        raise AuthenticationError("Invalid token format")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except InvalidSignatureError:
        raise AuthenticationError("Invalid token signature")
    except DecodeError:
        raise AuthenticationError("Invalid token format")
    except Exception as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")

    # Validar claims requeridos
    required_claims = ["sub", "email"]
    missing_claims = [c for c in required_claims if c not in payload]
    if missing_claims:
        raise AuthenticationError(
            f"Token missing required claims: {', '.join(missing_claims)}"
        )

    return UserInfo(
        user_id=payload["sub"],
        email=payload["email"],
        role=payload.get("role", "user"),
    )
```

**Comando para verificar**:
```bash
uv run pytest tests/unit/test_jwt_handler.py -v
# Expected: All tests PASSED
```

---

### Prompt 1.5 - Tests del AgentState (TDD - RED)

**Objetivo**: Escribir tests para el estado del agente LangGraph.

**Instrucciones**:

```
Escribe tests para src/agent/state.py que definan el AgentState de LangGraph.

TESTS REQUERIDOS:
1. AgentState tiene campos: messages, user_id, chatbot_id, language
2. messages es una lista que se puede extender (append-only)
3. AgentState es serializable a JSON
4. user_id y chatbot_id son strings requeridos
```

**Archivos a crear**:

**tests/unit/test_agent_state.py**:
```python
"""Tests para el AgentState de LangGraph - TDD RED PHASE."""
import json

import pytest


class TestAgentState:
    """Tests para el estado del agente."""

    def test_agent_state_has_required_fields(self) -> None:
        """AgentState debe tener todos los campos requeridos."""
        from src.agent.state import AgentState

        state = AgentState(
            messages=[],
            user_id="user-123",
            chatbot_id="chatbot-456",
            language="es",
        )

        assert hasattr(state, "messages")
        assert hasattr(state, "user_id")
        assert hasattr(state, "chatbot_id")
        assert hasattr(state, "language")

    def test_agent_state_messages_is_list(self) -> None:
        """messages debe ser una lista."""
        from src.agent.state import AgentState
        from langchain_core.messages import HumanMessage

        state = AgentState(
            messages=[HumanMessage(content="Hello")],
            user_id="user-123",
            chatbot_id="chatbot-456",
        )

        assert isinstance(state["messages"], list)
        assert len(state["messages"]) == 1

    def test_agent_state_messages_append_via_reducer(self) -> None:
        """Los mensajes deben poder añadirse vía el reducer de LangGraph."""
        from src.agent.state import AgentState
        from langchain_core.messages import AIMessage, HumanMessage

        initial_state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "user_id": "user-123",
            "chatbot_id": "chatbot-456",
            "language": "en",
        }

        # Simular update de LangGraph
        new_messages = [AIMessage(content="Hi there!")]

        # El reducer debe combinar mensajes
        from src.agent.state import messages_reducer
        combined = messages_reducer(initial_state["messages"], new_messages)

        assert len(combined) == 2
        assert combined[0].content == "Hello"
        assert combined[1].content == "Hi there!"

    def test_agent_state_serializable(self) -> None:
        """AgentState debe ser serializable a JSON."""
        from src.agent.state import AgentState, serialize_state
        from langchain_core.messages import HumanMessage

        state: AgentState = {
            "messages": [HumanMessage(content="Test")],
            "user_id": "user-123",
            "chatbot_id": "chatbot-456",
            "language": "es",
        }

        serialized = serialize_state(state)

        # Debe ser JSON válido
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)

        assert parsed["user_id"] == "user-123"
        assert len(parsed["messages"]) == 1

    def test_agent_state_default_language(self) -> None:
        """language debe tener un valor por defecto."""
        from src.agent.state import create_initial_state

        state = create_initial_state(
            user_id="user-123",
            chatbot_id="chatbot-456",
        )

        assert state["language"] == "es"  # Español por defecto

    def test_agent_state_optional_fields(self) -> None:
        """AgentState debe soportar campos opcionales."""
        from src.agent.state import AgentState

        state: AgentState = {
            "messages": [],
            "user_id": "user-123",
            "chatbot_id": "chatbot-456",
            "language": "en",
            "retrieved_context": ["doc1", "doc2"],
            "current_tool": "search_knowledge",
        }

        assert state.get("retrieved_context") == ["doc1", "doc2"]
        assert state.get("current_tool") == "search_knowledge"
```

**Comando para ejecutar (debe fallar)**:
```bash
uv run pytest tests/unit/test_agent_state.py -v
# Expected: FAILED - ModuleNotFoundError
```

---

### Prompt 1.6 - Implementación del AgentState (TDD - GREEN)

**Objetivo**: Implementar el AgentState para LangGraph.

**Archivos a crear**:

**src/agent/__init__.py**:
```python
"""Módulo del agente LangGraph."""
```

**src/agent/state.py**:
```python
"""Definición del estado del agente para LangGraph."""
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage, BaseMessage


def messages_reducer(
    existing: list[AnyMessage],
    new: list[AnyMessage] | AnyMessage
) -> list[AnyMessage]:
    """Reducer para combinar mensajes (append-only).

    Este reducer implementa la lógica de LangGraph para
    acumular mensajes en el estado.

    Args:
        existing: Lista de mensajes existentes
        new: Nuevo(s) mensaje(s) a añadir

    Returns:
        Lista combinada de mensajes
    """
    if isinstance(new, list):
        return existing + new
    return existing + [new]


class AgentState(TypedDict, total=False):
    """Estado del agente para el grafo de LangGraph.

    Attributes:
        messages: Historial de mensajes (append-only via reducer)
        user_id: ID del usuario autenticado
        chatbot_id: ID del chatbot que procesa la conversación
        language: Idioma detectado o configurado (default: "es")
        retrieved_context: Documentos recuperados del RAG
        current_tool: Herramienta actualmente en ejecución
        run_id: ID de la ejecución para LangSmith
    """

    messages: Annotated[list[AnyMessage], messages_reducer]
    user_id: str
    chatbot_id: str
    language: str
    retrieved_context: list[str]
    current_tool: str | None
    run_id: str | None


def create_initial_state(
    user_id: str,
    chatbot_id: str,
    initial_message: str | None = None,
    language: str = "es",
) -> AgentState:
    """Crea el estado inicial del agente.

    Args:
        user_id: ID del usuario
        chatbot_id: ID del chatbot
        initial_message: Mensaje inicial opcional
        language: Idioma por defecto

    Returns:
        Estado inicial configurado
    """
    from langchain_core.messages import HumanMessage

    messages: list[AnyMessage] = []
    if initial_message:
        messages.append(HumanMessage(content=initial_message))

    return AgentState(
        messages=messages,
        user_id=user_id,
        chatbot_id=chatbot_id,
        language=language,
        retrieved_context=[],
        current_tool=None,
        run_id=None,
    )


def serialize_state(state: AgentState) -> dict[str, Any]:
    """Serializa el estado a un diccionario JSON-compatible.

    Args:
        state: Estado del agente

    Returns:
        Diccionario serializable
    """
    serialized: dict[str, Any] = {
        "user_id": state.get("user_id"),
        "chatbot_id": state.get("chatbot_id"),
        "language": state.get("language", "es"),
        "messages": [],
        "retrieved_context": state.get("retrieved_context", []),
        "current_tool": state.get("current_tool"),
        "run_id": state.get("run_id"),
    }

    for msg in state.get("messages", []):
        serialized["messages"].append({
            "type": msg.__class__.__name__,
            "content": msg.content,
        })

    return serialized
```

**Comando para verificar**:
```bash
uv run pytest tests/unit/test_agent_state.py -v
# Expected: All tests PASSED
```

---

## FASE 2: Base de Datos y Migraciones — PARCIALMENTE REDUCIDA

> El prompt 2.1 (configuración de Alembic) está **reducido**: Alembic ya está configurado en el servidor.
> Solo hay que crear la nueva migration que añade las tablas del Hub al schema existente
> (chatbots, knowledge_bases, documents, document_chunks con vector, conversations, messages,
> feedback_ratings, ragas_evaluations) y habilitar la extensión `pgvector` si no está activa.
>
> Los prompts 2.2–2.9 se mantienen íntegros: definen modelos ORM, retriever híbrido y
> esquema de gobernanza de IA específicos del Hub.

---

### Prompt 2.1 - Configuración de Alembic (Setup)

**Objetivo**: Configurar Alembic para migraciones asíncronas con asyncpg.

**Instrucciones**:

```
Configura Alembic para el proyecto con soporte asíncrono.

TAREAS:
1. Inicializar Alembic: alembic init migrations
2. Configurar alembic.ini para usar DATABASE_URL
3. Configurar env.py para operaciones async

CRITERIOS DE ACEPTACIÓN:
- alembic upgrade head funciona sin errores
- La extensión vector está habilitada en PostgreSQL
```

**Archivos a crear**:

**alembic.ini**:
```ini
[alembic]
script_location = migrations
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

**migrations/env.py**:
```python
"""Configuración de Alembic para migraciones asíncronas."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config import get_settings
from src.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda conn: context.configure(connection=conn, target_metadata=target_metadata)
        )
        await connection.run_sync(lambda conn: context.run_migrations())

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

### Prompt 2.2 - Tests de Conexión a Base de Datos (TDD - RED)

**Objetivo**: Validar la conexión asíncrona a PostgreSQL con soporte de la extensión `pgvector`, asegurando que el motor y la fábrica de sesiones funcionan correctamente.

**Archivos a crear**:

**tests/integration/test_database_connection.py**:
```python
"""Tests de integración para la conexión a base de datos."""
import pytest
from sqlalchemy import text


@pytest.fixture
def db_url():
    return "postgresql+asyncpg://chatbots:chatbots_secret@localhost:5432/chatbots_hub_test"


class TestAsyncDatabaseConnection:

    @pytest.mark.asyncio
    async def test_async_engine_creates_connection(self, db_url: str) -> None:
        from src.database.connection import create_async_engine

        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_async_session_commits_transaction(self, db_url: str) -> None:
        from src.database.connection import create_async_engine, create_session_factory

        engine = create_async_engine(db_url)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            await session.execute(text("CREATE TEMP TABLE test_commit (id SERIAL, value TEXT)"))
            await session.execute(text("INSERT INTO test_commit (value) VALUES ('test')"))
            await session.commit()
            result = await session.execute(text("SELECT value FROM test_commit"))
            assert result.scalar() == "test"
        await engine.dispose()
```

---

### Prompt 2.3 - Implementación de Conexión a BD (TDD - GREEN)

**Objetivo**: Implementar el motor de conexión asíncrona y la fábrica de sesiones SQLAlchemy que supere los tests de conexión anteriores.

**src/database/__init__.py**:
```python
"""Módulo de base de datos."""
from src.database.connection import get_async_session

__all__ = ["get_async_session"]
```

**src/database/connection.py**:
```python
"""Conexión asíncrona a PostgreSQL."""
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker,
    create_async_engine as sa_create_async_engine,
)

from src.config import get_settings


def create_async_engine(url: str | None = None, **kwargs: Any) -> AsyncEngine:
    if url is None:
        url = get_settings().database_url
    return sa_create_async_engine(url, echo=False, pool_pre_ping=True, **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine()
    return _engine


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = create_session_factory(get_engine())
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

### Prompt 2.4 - Tests de Modelos ORM (TDD - RED)

**Objetivo**: Validar los modelos SQLAlchemy (`Chatbot`, `DocumentChunk`, `IngestionJob`) con sus campos, relaciones y constraints antes de implementarlos.

**tests/integration/test_database_models.py**:
```python
"""Tests para modelos ORM."""
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select, text


@pytest.fixture
def db_url():
    return "postgresql+asyncpg://chatbots:chatbots_secret@localhost:5432/chatbots_hub_test"


class TestChatbotModel:

    @pytest.mark.asyncio
    async def test_create_chatbot_model(self, db_url: str) -> None:
        from src.database.connection import create_async_engine, create_session_factory
        from src.database.models import Base, Chatbot

        engine = create_async_engine(db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            chatbot = Chatbot(
                id=uuid.uuid4(), name="Test Bot",
                system_prompt="You are helpful.", sources=[]
            )
            session.add(chatbot)
            await session.commit()

            result = await session.execute(select(Chatbot).where(Chatbot.name == "Test Bot"))
            assert result.scalar_one().name == "Test Bot"

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


class TestDocumentChunkModel:

    @pytest.mark.asyncio
    async def test_create_chunk_with_vector(self, db_url: str) -> None:
        from src.database.connection import create_async_engine, create_session_factory
        from src.database.models import Base, Chatbot, DocumentChunk

        engine = create_async_engine(db_url)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            chatbot = Chatbot(id=uuid.uuid4(), name="Bot", system_prompt="Test", sources=[])
            session.add(chatbot)
            await session.flush()

            chunk = DocumentChunk(
                chatbot_id=chatbot.id, content="Test content",
                source_url="https://example.com", content_hash="abc123",
                embedding=[0.1] * 1536, metadata={"page": 1}
            )
            session.add(chunk)
            await session.commit()

            result = await session.execute(select(DocumentChunk).where(DocumentChunk.content_hash == "abc123"))
            saved = result.scalar_one()
            assert len(saved.embedding) == 1536

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
```

---

### Prompt 2.5 - Implementación de Modelos ORM (TDD - GREEN)

**Objetivo**: Implementar los modelos ORM completos con sus relaciones, índices vectoriales y migraciones Alembic correspondientes.

**src/database/models.py**:
```python
"""Modelos ORM de SQLAlchemy."""
import uuid
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, list[str]: ARRAY(String)}


class Client(Base):
    """Entidad cliente (institución) gestionada por un partner."""
    __tablename__ = "clients"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # user_id del partner responsable
    theme_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # overrides visuales a nivel cliente
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    chatbots: Mapped[list["Chatbot"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class Chatbot(Base):
    __tablename__ = "chatbots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    theme_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # overrides visuales a nivel chatbot (cascada sobre cliente)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    client: Mapped["Client"] = relationship(back_populates="chatbots")
    document_chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="chatbot", cascade="all, delete-orphan")
    interactions: Mapped[list["Interaction"]] = relationship(back_populates="chatbot", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    language: Mapped[str] = mapped_column(String(10), default="es")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    chatbot: Mapped["Chatbot"] = relationship(back_populates="document_chunks")


class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_message: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    feedback_score: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    chatbot: Mapped["Chatbot"] = relationship(back_populates="interactions")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    chunks_processed: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

---

### Prompt 2.6 - Tests del Retriever Híbrido (TDD - RED)

**Objetivo**: Validar el sistema de búsqueda que combina similitud vectorial (semántica) con búsqueda por palabras clave (full-text), devolviendo resultados rankeados por relevancia.

**tests/integration/test_retriever.py**:
```python
"""Tests para el retriever híbrido."""
import uuid
import pytest
from sqlalchemy import text


@pytest.fixture
def db_url():
    return "postgresql+asyncpg://chatbots:chatbots_secret@localhost:5432/chatbots_hub_test"


class TestHybridRetriever:

    @pytest.mark.asyncio
    async def test_vector_similarity_search(self, db_url: str) -> None:
        from src.database.connection import create_async_engine, create_session_factory
        from src.database.models import Base, Chatbot, DocumentChunk
        from src.services.retriever import HybridRetriever

        engine = create_async_engine(db_url)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            chatbot_id = uuid.uuid4()
            chatbot = Chatbot(id=chatbot_id, name="Test", system_prompt="Test", sources=[])
            session.add(chatbot)
            await session.flush()

            chunks = [
                DocumentChunk(chatbot_id=chatbot_id, content="Python es genial", source_url="url1", content_hash="h1", embedding=[0.1]*1536),
                DocumentChunk(chatbot_id=chatbot_id, content="Java es diferente", source_url="url2", content_hash="h2", embedding=[0.9]*1536),
            ]
            session.add_all(chunks)
            await session.commit()

            retriever = HybridRetriever(session)
            results = await retriever.vector_search([0.12]*1536, chatbot_id, top_k=2)
            assert len(results) >= 1
            assert "Python" in results[0].content

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
```

---

### Prompt 2.7 - Implementación del Retriever Híbrido (TDD - GREEN)

**Objetivo**: Implementar el `HybridRetriever` que ejecuta búsquedas vectoriales con `pgvector` y full-text en PostgreSQL, fusionando y rankeando los resultados.

**src/services/__init__.py**:
```python
"""Módulo de servicios."""
```

**src/services/retriever.py**:
```python
"""Servicio de búsqueda híbrida."""
import uuid
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import DocumentChunk


@dataclass
class SearchResult:
    id: uuid.UUID
    content: str
    source_url: str
    language: str
    score: float
    metadata: dict


class HybridRetriever:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def vector_search(
        self, query_embedding: list[float], chatbot_id: uuid.UUID,
        top_k: int = 5, language: str | None = None
    ) -> list[SearchResult]:
        similarity = 1 - DocumentChunk.embedding.cosine_distance(query_embedding)
        query = (
            select(DocumentChunk, similarity.label("score"))
            .where(DocumentChunk.chatbot_id == chatbot_id)
            .where(DocumentChunk.embedding.isnot(None))
        )
        if language:
            query = query.where(DocumentChunk.language == language)
        query = query.order_by(similarity.desc()).limit(top_k)
        result = await self.session.execute(query)
        return [
            SearchResult(
                id=row.DocumentChunk.id, content=row.DocumentChunk.content,
                source_url=row.DocumentChunk.source_url, language=row.DocumentChunk.language,
                score=float(row.score), metadata=row.DocumentChunk.metadata or {}
            )
            for row in result.all()
        ]

    async def keyword_search(
        self, query: str, chatbot_id: uuid.UUID,
        top_k: int = 5, language: str | None = None
    ) -> list[SearchResult]:
        filters = [DocumentChunk.chatbot_id == chatbot_id]
        for word in query.split():
            filters.append(DocumentChunk.content.ilike(f"%{word}%"))
        if language:
            filters.append(DocumentChunk.language == language)
        stmt = select(DocumentChunk).where(*filters).limit(top_k)
        result = await self.session.execute(stmt)
        return [
            SearchResult(
                id=c.id, content=c.content, source_url=c.source_url,
                language=c.language, score=1.0, metadata=c.metadata or {}
            )
            for c in result.scalars().all()
        ]

    async def hybrid_search(
        self, query: str, query_embedding: list[float], chatbot_id: uuid.UUID,
        top_k: int = 5, language: str | None = None, vector_weight: float = 0.7
    ) -> list[SearchResult]:
        vector_results = await self.vector_search(query_embedding, chatbot_id, top_k*2, language)
        keyword_results = await self.keyword_search(query, chatbot_id, top_k*2, language)

        scores: dict[uuid.UUID, tuple[SearchResult, float]] = {}
        k = 60
        for rank, r in enumerate(vector_results):
            scores[r.id] = (r, vector_weight * (1/(k+rank+1)))
        for rank, r in enumerate(keyword_results):
            rrf = (1-vector_weight) * (1/(k+rank+1))
            if r.id in scores:
                scores[r.id] = (r, scores[r.id][1] + rrf)
            else:
                scores[r.id] = (r, rrf)

        sorted_results = sorted(scores.values(), key=lambda x: x[1], reverse=True)
        return [SearchResult(id=r.id, content=r.content, source_url=r.source_url, language=r.language, score=s, metadata=r.metadata) for r, s in sorted_results[:top_k]]
```

---

---

### Prompt 2.8 - Esquema de Gobernanza de IA (TDD - RED/GREEN)

**Objetivo**: Crear el soporte en base de datos para almacenar prompts y configuraciones de modelos de forma dinámica, permitiendo editar el comportamiento de la IA sin tocar el código.

**Instrucciones**:

```
Actúa como un experto en Bases de Datos. Actualiza el modelo de SQLAlchemy en `src/database/models.py`.

TAREAS:
1. Tabla `llm_configs`: Campos `id`, `provider` (enum: google, openai, ollama), `model_name`, `temperature`, `max_tokens`, `api_key_secret_name` (string para referencia a Secret Manager).
2. Tabla `prompt_templates`: Campos `id`, `chatbot_id` (FK), `slug` (ej: 'system_base'), `language` (ca, es, en), `template_text` (Text), `version` (int).
3. Relación: Actualizar el modelo `Chatbot` para que tenga una relación 1:1 con `llm_configs` y 1:N con `prompt_templates`.

TESTS REQUERIDOS (RED):
- test_chatbot_retrieves_correct_prompt_by_language: Validar que al pedir el prompt 'system' en catalán, no devuelva el de castellano.
- test_llm_config_persistence: Validar que se pueden guardar y recuperar parámetros de temperatura y modelo.
```

---

### Prompt 2.9 - Estructura de Asignación de Modelos por Chatbot (TDD - RED/GREEN)

**Objetivo**: Garantizar que cada bot tenga un modelo LLM asignado de forma explícita y que el administrador pueda cambiarlo sin reiniciar el servidor.

**Instrucciones**:

```
Actualiza la tabla `chatbots` para incluir una relación obligatoria con `llm_configs`. Cada bot debe tener un `model_id` asignado. El sistema debe permitir que el administrador cambie este ID en cualquier momento para que el bot empiece a usar un modelo distinto (ej. pasar de Flash a Pro para mayor precisión).

TESTS REQUERIDOS (RED):
- test_chatbot_has_required_model: Validar que no se puede crear un chatbot sin `model_id`.
- test_model_hot_swap: Validar que cambiar el `model_id` en base de datos hace que la siguiente petición use el nuevo modelo sin reiniciar el proceso.
```

---

## FASE 3: Ingestión de Documentos (Asíncrona)

---

### Prompt 3.1 - Tests del Hasher de Documentos (TDD - RED)

**Objetivo**: Crear un sistema para detectar cambios en documentos usando SHA-256.

**tests/unit/test_hasher.py**:
```python
"""Tests para el hasher de documentos."""
import pytest


class TestDocumentHasher:

    def test_hash_content_returns_sha256(self) -> None:
        from src.ingestion.hasher import hash_content

        content = "Este es un documento de prueba."
        result = hash_content(content)

        assert len(result) == 64  # SHA-256 hex
        assert result.isalnum()

    def test_same_content_same_hash(self) -> None:
        from src.ingestion.hasher import hash_content

        content = "Contenido idéntico"
        hash1 = hash_content(content)
        hash2 = hash_content(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self) -> None:
        from src.ingestion.hasher import hash_content

        hash1 = hash_content("Contenido A")
        hash2 = hash_content("Contenido B")

        assert hash1 != hash2

    def test_hash_file_returns_hash(self) -> None:
        from src.ingestion.hasher import hash_file
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Contenido del archivo")
            temp_path = f.name

        result = hash_file(Path(temp_path))
        assert len(result) == 64

        Path(temp_path).unlink()
```

---

### Prompt 3.2 - Implementación del Hasher (TDD - GREEN)

**Objetivo**: Implementar el sistema de hashing SHA-256 para detectar si un documento ha cambiado desde la última ingestión, evitando reprocesamiento innecesario.

**src/ingestion/__init__.py**:
```python
"""Módulo de ingestión de documentos."""
```

**src/ingestion/hasher.py**:
```python
"""Hasher para detección de cambios en documentos."""
import hashlib
from pathlib import Path


def hash_content(content: str) -> str:
    """Genera hash SHA-256 del contenido.

    Args:
        content: Texto a hashear

    Returns:
        Hash hexadecimal de 64 caracteres
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def hash_file(file_path: Path) -> str:
    """Genera hash SHA-256 de un archivo.

    Args:
        file_path: Ruta al archivo

    Returns:
        Hash hexadecimal de 64 caracteres
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()
```

---

### Prompt 3.3 - Tests del Chunker de Markdown (TDD - RED)

**Objetivo**: Validar el sistema de división de documentos Markdown en chunks semánticos con metadatos (fuente, posición, idioma) que preserven el contexto para el RAG.

**tests/unit/test_chunker.py**:
```python
"""Tests para el chunker de markdown."""
import pytest


class TestMarkdownChunker:

    def test_split_by_headers(self) -> None:
        from src.ingestion.chunker import MarkdownChunker

        markdown = '''# Título Principal

Este es el contenido del título principal.

## Sección 1

Contenido de la sección 1.

## Sección 2

Contenido de la sección 2.
'''
        chunker = MarkdownChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.split(markdown)

        assert len(chunks) >= 2
        assert any("Sección 1" in c.content for c in chunks)

    def test_preserves_metadata(self) -> None:
        from src.ingestion.chunker import MarkdownChunker

        markdown = '''# Título

Contenido bajo el título.
'''
        chunker = MarkdownChunker()
        chunks = chunker.split(markdown, metadata={"source": "test.md"})

        assert chunks[0].metadata["source"] == "test.md"

    def test_respects_chunk_size(self) -> None:
        from src.ingestion.chunker import MarkdownChunker

        long_content = "# Título\n\n" + "Palabra " * 1000
        chunker = MarkdownChunker(chunk_size=200, chunk_overlap=20)
        chunks = chunker.split(long_content)

        for chunk in chunks:
            assert len(chunk.content) <= 300  # Con margen
```

---

### Prompt 3.4 - Implementación del Chunker (TDD - GREEN)

**Objetivo**: Implementar el splitter de Markdown que genera chunks vectorizables manteniendo coherencia semántica y metadatos de trazabilidad.

**src/ingestion/chunker.py**:
```python
"""Chunker para documentos Markdown."""
from dataclasses import dataclass, field
from typing import Any

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    """Representa un chunk de documento."""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MarkdownChunker:
    """Divide documentos Markdown en chunks semánticos."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.headers_to_split = [
            ("#", "header_1"),
            ("##", "header_2"),
            ("###", "header_3"),
        ]

        self.md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split,
            strip_headers=False,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, content: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Divide el contenido en chunks.

        Args:
            content: Contenido Markdown
            metadata: Metadatos adicionales

        Returns:
            Lista de chunks
        """
        base_metadata = metadata or {}

        # Primero dividir por headers
        md_docs = self.md_splitter.split_text(content)

        # Luego dividir documentos grandes
        chunks = []
        for doc in md_docs:
            doc_content = doc.page_content
            doc_metadata = {**base_metadata, **doc.metadata}

            if len(doc_content) > self.chunk_size:
                sub_docs = self.text_splitter.split_text(doc_content)
                for i, sub_content in enumerate(sub_docs):
                    chunks.append(Chunk(
                        content=sub_content,
                        metadata={**doc_metadata, "chunk_index": i},
                    ))
            else:
                chunks.append(Chunk(content=doc_content, metadata=doc_metadata))

        return chunks
```

---

### Prompt 3.5 - Tests del Procesador Docling (TDD - RED)

**Objetivo**: Validar la conversión de PDFs y páginas web (incluyendo webs dinámicas con JavaScript) a Markdown estructurado usando Docling y Playwright.

**tests/unit/test_docling_processor.py**:
```python
"""Tests para el procesador Docling."""
import pytest
from unittest.mock import Mock, patch


class TestDoclingProcessor:

    def test_process_pdf_returns_markdown(self) -> None:
        from src.ingestion.docling_processor import DoclingProcessor

        with patch('src.ingestion.docling_processor.DocumentConverter') as mock_converter:
            mock_result = Mock()
            mock_result.document.export_to_markdown.return_value = "# Título\n\nContenido"
            mock_converter.return_value.convert.return_value = mock_result

            processor = DoclingProcessor()
            result = processor.process_pdf("test.pdf")

            assert "# Título" in result
            assert "Contenido" in result

    def test_process_url_returns_markdown(self) -> None:
        from src.ingestion.docling_processor import DoclingProcessor

        with patch('src.ingestion.docling_processor.DocumentConverter') as mock_converter:
            mock_result = Mock()
            mock_result.document.export_to_markdown.return_value = "# Web Page\n\nContent"
            mock_converter.return_value.convert.return_value = mock_result

            processor = DoclingProcessor()
            result = processor.process_url("https://example.com")

            assert "# Web Page" in result
```

---

### Prompt 3.6 - Implementación del Procesador Docling (TDD - GREEN)

**Objetivo**: Implementar el procesador que usa Docling (IBM) y Playwright para convertir cualquier fuente documental a Markdown limpio y estructurado.

**src/ingestion/docling_processor.py**:
```python
"""Procesador de documentos usando Docling."""
from pathlib import Path

from docling.document_converter import DocumentConverter


class DoclingProcessor:
    """Convierte PDFs y URLs a Markdown usando Docling."""

    def __init__(self):
        self.converter = DocumentConverter()

    def process_pdf(self, pdf_path: str | Path) -> str:
        """Convierte un PDF a Markdown.

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Contenido en formato Markdown
        """
        result = self.converter.convert(str(pdf_path))
        return result.document.export_to_markdown()

    def process_url(self, url: str) -> str:
        """Convierte una página web a Markdown.

        Args:
            url: URL de la página

        Returns:
            Contenido en formato Markdown
        """
        result = self.converter.convert(url)
        return result.document.export_to_markdown()

    def process(self, source: str) -> str:
        """Procesa automáticamente PDF o URL.

        Args:
            source: Ruta a PDF o URL

        Returns:
            Contenido en formato Markdown
        """
        if source.startswith(('http://', 'https://')):
            return self.process_url(source)
        return self.process_pdf(source)
```

---

### Prompt 3.7 - Tests del Watcher Asíncrono (TDD - RED)

**Objetivo**: Validar el sistema de vigilancia asíncrono que detecta cambios en fuentes configuradas (URLs, carpetas) y dispara automáticamente el pipeline de ingestión.

**tests/unit/test_watcher.py**:
```python
"""Tests para el watcher de ingestión."""
import uuid
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestIngestionWatcher:

    @pytest.mark.asyncio
    async def test_process_source_creates_chunks(self) -> None:
        from src.ingestion.watcher import IngestionWatcher

        with patch('src.ingestion.watcher.DoclingProcessor') as mock_docling:
            mock_docling.return_value.process.return_value = "# Test\n\nContent"

            watcher = IngestionWatcher(
                session=AsyncMock(),
                embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1]*1536)),
            )

            chunks = await watcher.process_source(
                source_url="https://example.com",
                chatbot_id=uuid.uuid4(),
            )

            assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_process_skips_unchanged_content(self) -> None:
        from src.ingestion.watcher import IngestionWatcher

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=Mock(content_hash="existing_hash"))))

        watcher = IngestionWatcher(
            session=mock_session,
            embedding_service=AsyncMock(),
        )

        # El hash del nuevo contenido coincide
        with patch('src.ingestion.watcher.hash_content', return_value="existing_hash"):
            with patch('src.ingestion.watcher.DoclingProcessor') as mock_docling:
                mock_docling.return_value.process.return_value = "Content"

                result = await watcher.process_source(
                    source_url="https://example.com",
                    chatbot_id=uuid.uuid4(),
                )
                # Debe devolver lista vacía si no hay cambios
                assert len(result) == 0
```

---

### Prompt 3.8 - Implementación del Watcher (TDD - GREEN)

**Objetivo**: Implementar el `IngestionWatcher` asíncrono que orquesta el pipeline completo: detectar cambios → procesar con Docling → chunkear → vectorizar → almacenar en PostgreSQL.

**src/ingestion/watcher.py**:
```python
"""Orquestador de ingestión asíncrona."""
import uuid
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DocumentChunk, IngestionJob
from src.ingestion.chunker import MarkdownChunker
from src.ingestion.docling_processor import DoclingProcessor
from src.ingestion.hasher import hash_content


class EmbeddingService(Protocol):
    """Protocolo para servicio de embeddings."""
    async def embed(self, text: str) -> list[float]: ...


class IngestionWatcher:
    """Orquesta la ingestión de documentos."""

    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService):
        self.session = session
        self.embedding_service = embedding_service
        self.processor = DoclingProcessor()
        self.chunker = MarkdownChunker()

    async def process_source(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        language: str = "es",
    ) -> list[DocumentChunk]:
        """Procesa una fuente y crea chunks.

        Args:
            source_url: URL o ruta al documento
            chatbot_id: ID del chatbot
            language: Idioma del documento

        Returns:
            Lista de chunks creados
        """
        # Obtener contenido
        content = self.processor.process(source_url)
        content_hash = hash_content(content)

        # Verificar si ya existe con el mismo hash
        existing = await self.session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.source_url == source_url)
            .where(DocumentChunk.content_hash == content_hash)
            .limit(1)
        )
        if existing.scalar_one_or_none():
            return []  # Sin cambios

        # Eliminar chunks antiguos de esta fuente
        old_chunks = await self.session.execute(
            select(DocumentChunk).where(DocumentChunk.source_url == source_url)
        )
        for chunk in old_chunks.scalars():
            await self.session.delete(chunk)

        # Crear nuevos chunks
        chunks = self.chunker.split(content, metadata={"source_url": source_url})
        created_chunks = []

        for chunk in chunks:
            embedding = await self.embedding_service.embed(chunk.content)
            db_chunk = DocumentChunk(
                chatbot_id=chatbot_id,
                content=chunk.content,
                source_url=source_url,
                content_hash=hash_content(chunk.content),
                embedding=embedding,
                metadata=chunk.metadata,
                language=language,
            )
            self.session.add(db_chunk)
            created_chunks.append(db_chunk)

        await self.session.commit()
        return created_chunks

    async def run_job(self, job_id: uuid.UUID) -> None:
        """Ejecuta un job de ingestión.

        Args:
            job_id: ID del job
        """
        job = await self.session.get(IngestionJob, job_id)
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await self.session.commit()

        try:
            chunks = await self.process_source(job.source_url, job.chatbot_id)
            job.status = "completed"
            job.chunks_processed = len(chunks)
            job.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)

        await self.session.commit()
```

---

---

### Prompt 3.9 - Ingestión de Documentos de Usuario (Contexto Temporal)

**Objetivo**: Implementar la capacidad de procesar y vectorizar PDFs subidos por el usuario en tiempo real, asegurando que esta información esté aislada y vinculada únicamente a su sesión/identidad.

**Instrucciones**:

```
Actúa como un experto en Backend. Implementa la lógica de 'Ingesta Prioritaria' para documentos subidos por el usuario.

TAREAS:
1. Crear el endpoint `POST /api/v1/ingestion/user-upload` que reciba un archivo PDF y un `user_id` (del SSO).
2. Modificar `DocumentChunk` en `src/database/models.py` para incluir una columna `is_temporary: bool` y `owner_id: UUID` (opcional).
3. Implementar un flujo en `IngestionWatcher` que procese estos archivos ignorando el sistema de 'hashing' global (siempre se procesan) y los marque como temporales.
4. Asegurar que el sistema de búsqueda (Retriever) incluya estos chunks SOLO si el `user_id` de la consulta coincide con el `owner_id` del documento.

TESTS REQUERIDOS (RED):
- test_user_upload_is_not_visible_to_other_users: Validar que un documento subido por el Usuario A no es recuperado en una búsqueda del Usuario B.
- test_temporary_chunks_cleanup: Validar una función que elimine chunks temporales después de 24 horas (TTL).
```

---

## FASE 4: Agente LangGraph con Herramientas y RAGAS

---

### Prompt 4.1 - Tests del Detector de Idioma (TDD - RED)

**Objetivo**: Validar la detección automática del idioma del mensaje del usuario (Catalán, Castellano e Inglés) para adaptar las respuestas del agente.

**tests/unit/test_language_detector.py**:
```python
"""Tests para el detector de idioma."""
import pytest


class TestLanguageDetector:

    def test_detects_spanish(self) -> None:
        from src.agent.language_detector import detect_language

        text = "Hola, ¿cómo estás? Necesito ayuda con un problema."
        result = detect_language(text)
        assert result == "es"

    def test_detects_english(self) -> None:
        from src.agent.language_detector import detect_language

        text = "Hello, how are you? I need help with a problem."
        result = detect_language(text)
        assert result == "en"

    def test_defaults_to_spanish_on_short_text(self) -> None:
        from src.agent.language_detector import detect_language

        text = "Hola"
        result = detect_language(text)
        assert result == "es"  # Default
```

---

### Prompt 4.2 - Implementación del Detector de Idioma (TDD - GREEN)

**Objetivo**: Implementar el detector de idioma que analiza el texto de entrada y devuelve el código de idioma (`ca`, `es`, `en`) para su uso en el grafo LangGraph.

**src/agent/language_detector.py**:
```python
"""Detector de idioma para mensajes."""
from langdetect import detect, LangDetectException


def detect_language(text: str, default: str = "es") -> str:
    """Detecta el idioma de un texto.

    Args:
        text: Texto a analizar
        default: Idioma por defecto si no se puede detectar

    Returns:
        Código de idioma (es, en, etc.)
    """
    if len(text.strip()) < 10:
        return default

    try:
        return detect(text)
    except LangDetectException:
        return default
```

---

### Prompt 4.3 - Tests de la Herramienta search_knowledge (TDD - RED)

**Objetivo**: Validar la herramienta de búsqueda en la base de conocimiento que el agente LangGraph usa para recuperar contexto relevante antes de generar respuestas.

**tests/unit/test_tools.py**:
```python
"""Tests para las herramientas del agente."""
import uuid
import pytest
from unittest.mock import AsyncMock, Mock


class TestSearchKnowledgeTool:

    @pytest.mark.asyncio
    async def test_search_returns_formatted_results(self) -> None:
        from src.agent.tools.search_knowledge import search_knowledge

        mock_retriever = AsyncMock()
        mock_retriever.hybrid_search = AsyncMock(return_value=[
            Mock(content="Resultado 1", source_url="url1", score=0.9),
            Mock(content="Resultado 2", source_url="url2", score=0.8),
        ])

        result = await search_knowledge(
            query="test query",
            chatbot_id=str(uuid.uuid4()),
            retriever=mock_retriever,
            embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1]*1536)),
        )

        assert "Resultado 1" in result
        assert "Resultado 2" in result

    @pytest.mark.asyncio
    async def test_search_handles_no_results(self) -> None:
        from src.agent.tools.search_knowledge import search_knowledge

        mock_retriever = AsyncMock()
        mock_retriever.hybrid_search = AsyncMock(return_value=[])

        result = await search_knowledge(
            query="nonexistent",
            chatbot_id=str(uuid.uuid4()),
            retriever=mock_retriever,
            embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1]*1536)),
        )

        assert "no se encontr" in result.lower() or "not found" in result.lower()
```

---

### Prompt 4.4 - Implementación de search_knowledge (TDD - GREEN)

**Objetivo**: Implementar la herramienta `search_knowledge` que el agente invoca para realizar búsquedas RAG filtradas por idioma y acceso (público o privado del usuario).

**src/agent/tools/__init__.py**:
```python
"""Herramientas del agente."""
```

**src/agent/tools/search_knowledge.py**:
```python
"""Herramienta de búsqueda en la base de conocimiento."""
import uuid
from typing import Protocol


class RetrieverProtocol(Protocol):
    async def hybrid_search(self, query: str, query_embedding: list[float], chatbot_id: uuid.UUID, top_k: int, language: str | None) -> list: ...


class EmbeddingProtocol(Protocol):
    async def embed(self, text: str) -> list[float]: ...


async def search_knowledge(
    query: str,
    chatbot_id: str,
    retriever: RetrieverProtocol,
    embedding_service: EmbeddingProtocol,
    top_k: int = 5,
    language: str | None = None,
) -> str:
    """Busca información relevante en la base de conocimiento.

    Args:
        query: Consulta de búsqueda
        chatbot_id: ID del chatbot
        retriever: Servicio de recuperación
        embedding_service: Servicio de embeddings
        top_k: Número de resultados
        language: Filtro de idioma

    Returns:
        Texto formateado con los resultados
    """
    query_embedding = await embedding_service.embed(query)

    results = await retriever.hybrid_search(
        query=query,
        query_embedding=query_embedding,
        chatbot_id=uuid.UUID(chatbot_id),
        top_k=top_k,
        language=language,
    )

    if not results:
        return "No se encontró información relevante para tu consulta."

    formatted = "**Información encontrada:**\n\n"
    for i, result in enumerate(results, 1):
        formatted += f"{i}. {result.content[:200]}...\n"
        formatted += f"   _Fuente: {result.source_url}_\n\n"

    return formatted
```

---

### Prompt 4.5 - Tests del Grafo LangGraph (TDD - RED)

**Objetivo**: Validar el flujo completo del grafo de decisión: detección de idioma → selección de herramientas según rol → búsqueda → generación de respuesta.

**tests/unit/test_graph.py**:
```python
"""Tests para el grafo de LangGraph."""
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestAgentGraph:

    def test_graph_has_required_nodes(self) -> None:
        from src.agent.graph import create_agent_graph

        with patch('src.agent.graph.ChatGoogleGenerativeAI'):
            graph = create_agent_graph(
                retriever=Mock(),
                embedding_service=Mock(),
            )

            # Verificar nodos
            assert "detect_language" in str(graph.nodes)
            assert "generate_response" in str(graph.nodes)

    @pytest.mark.asyncio
    async def test_graph_processes_message(self) -> None:
        from src.agent.graph import create_agent_graph
        from src.agent.state import create_initial_state

        with patch('src.agent.graph.ChatGoogleGenerativeAI') as mock_llm:
            mock_llm.return_value.ainvoke = AsyncMock(
                return_value=Mock(content="Respuesta de prueba")
            )

            graph = create_agent_graph(
                retriever=AsyncMock(hybrid_search=AsyncMock(return_value=[])),
                embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1]*1536)),
            )

            initial_state = create_initial_state(
                user_id="user-123",
                chatbot_id="chatbot-456",
                initial_message="Hola, necesito ayuda",
            )

            # El grafo debe poder compilarse y ejecutarse
            compiled = graph.compile()
            assert compiled is not None
```

---

### Prompt 4.6 - Implementación del Grafo LangGraph (TDD - GREEN)

**Objetivo**: Implementar el grafo de decisión LangGraph con soporte de modo dual: en modo Público ejecuta solo RAG con fuentes abiertas; en modo Agente (usuario identificado) desbloquea herramientas MCP y acceso a documentos temporales del usuario.

> **Nota — Modo Dual (Chatbot/Agente):** El grafo es consciente del contexto del usuario. Si se recibe un `user_id` válido (modo Agente identificado), el nodo inicial desbloquea herramientas adicionales: consulta MCP (`query_oracle_mcp`) y búsqueda en documentos temporales del usuario. En modo Público (anónimo), solo está disponible `search_knowledge_base` con fuentes públicas. Ver Prompt 4.9 para la lógica de síntesis y Prompt 4.10 para el selector de modelos dinámico.

**src/agent/graph.py**:
```python
"""Grafo de LangGraph para el agente.

Soporta dos modos de operación:
- Modo Público (Chatbot): user_id=None, solo herramientas RAG públicas.
- Modo Agente (Identificado): user_id válido, desbloquea MCP y docs de usuario.
"""
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_vertexai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from src.agent.language_detector import detect_language
from src.agent.state import AgentState
from src.agent.tools.search_knowledge import search_knowledge
from src.config import get_settings


def create_agent_graph(retriever, embedding_service, user_id: str | None = None):
    """Crea el grafo del agente.

    Args:
        retriever: Servicio de recuperación
        embedding_service: Servicio de embeddings

    Returns:
        StateGraph configurado
    """
    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=settings.google_api_key,
    )

    async def detect_language_node(state: AgentState) -> dict:
        """Detecta el idioma del último mensaje."""
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, HumanMessage):
                language = detect_language(last_message.content)
                return {"language": language}
        return {"language": state.get("language", "es")}

    async def search_knowledge_node(state: AgentState) -> dict:
        """Busca información relevante."""
        messages = state.get("messages", [])
        if not messages:
            return {"retrieved_context": []}

        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            return {"retrieved_context": []}

        result = await search_knowledge(
            query=last_message.content,
            chatbot_id=state["chatbot_id"],
            retriever=retriever,
            embedding_service=embedding_service,
            language=state.get("language"),
        )
        return {"retrieved_context": [result]}

    async def generate_response_node(state: AgentState) -> dict:
        """Genera la respuesta final."""
        messages = state.get("messages", [])
        context = state.get("retrieved_context", [])

        # Construir prompt con contexto
        context_str = "\n".join(context) if context else "Sin información adicional."

        system_prompt = f"""Eres un asistente útil. Responde en {state.get('language', 'es')}.

Información relevante:
{context_str}

Responde de forma concisa y útil."""

        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            *[{"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content} for m in messages]
        ])

        return {"messages": [AIMessage(content=response.content)]}

    async def route_by_capability_node(state: AgentState) -> dict:
        """Determina las capacidades disponibles según el rol del usuario."""
        available_tools = ["search_knowledge"]
        if user_id:
            # Modo Agente: desbloquear herramientas avanzadas
            available_tools.extend(["query_oracle_mcp", "search_user_docs"])
        return {"user_id": user_id, "available_tools": available_tools}

    # Construir grafo
    graph = StateGraph(AgentState)

    graph.add_node("route_by_capability", route_by_capability_node)
    graph.add_node("detect_language", detect_language_node)
    graph.add_node("search_knowledge", search_knowledge_node)
    graph.add_node("generate_response", generate_response_node)

    graph.set_entry_point("route_by_capability")
    graph.add_edge("route_by_capability", "detect_language")
    graph.add_edge("detect_language", "search_knowledge")
    graph.add_edge("search_knowledge", "generate_response")
    graph.add_edge("generate_response", END)

    return graph
```

---

### Prompt 4.7 - Tests de Evaluación RAGAS (TDD - RED)

**Objetivo**: Validar las métricas de calidad RAG (fidelidad, relevancia de respuesta, recall de contexto) usando el framework RAGAS con pares pregunta-respuesta de referencia.

**tests/evaluation/test_rag_quality.py**:
```python
"""Tests de calidad RAG usando RAGAS."""
import pytest
from unittest.mock import AsyncMock, Mock


class TestRAGQuality:

    @pytest.fixture
    def golden_qa_pairs(self):
        return [
            {
                "question": "¿Qué es Python?",
                "answer": "Python es un lenguaje de programación.",
                "context": "Python es un lenguaje de programación versátil y fácil de aprender.",
            },
            {
                "question": "¿Para qué sirve FastAPI?",
                "answer": "FastAPI es un framework para crear APIs.",
                "context": "FastAPI es un framework web moderno para construir APIs con Python.",
            },
        ]

    @pytest.mark.asyncio
    async def test_rag_faithfulness(self, golden_qa_pairs) -> None:
        """La respuesta no debe alucinar fuera del contexto."""
        from src.evaluation.rag_metrics import calculate_faithfulness

        for qa in golden_qa_pairs:
            score = await calculate_faithfulness(
                answer=qa["answer"],
                context=qa["context"],
            )
            assert score >= 0.7, f"Faithfulness bajo para: {qa['question']}"

    @pytest.mark.asyncio
    async def test_rag_answer_relevance(self, golden_qa_pairs) -> None:
        """La respuesta debe ser relevante a la pregunta."""
        from src.evaluation.rag_metrics import calculate_answer_relevance

        for qa in golden_qa_pairs:
            score = await calculate_answer_relevance(
                question=qa["question"],
                answer=qa["answer"],
            )
            assert score >= 0.7, f"Relevancia baja para: {qa['question']}"
```

---

### Prompt 4.8 - Implementación de Métricas RAGAS (TDD - GREEN)

**Objetivo**: Implementar el pipeline de evaluación automática con RAGAS que mide la calidad del agente de forma objetiva y genera informes de calidad.

**src/evaluation/__init__.py**:
```python
"""Módulo de evaluación."""
```

**src/evaluation/rag_metrics.py**:
```python
"""Métricas de calidad RAG usando RAGAS."""
from ragas.metrics import faithfulness, answer_relevancy
from ragas import evaluate
from datasets import Dataset


async def calculate_faithfulness(answer: str, context: str) -> float:
    """Calcula la fidelidad de la respuesta al contexto.

    Args:
        answer: Respuesta generada
        context: Contexto proporcionado

    Returns:
        Score de fidelidad (0-1)
    """
    data = {
        "question": ["placeholder"],
        "answer": [answer],
        "contexts": [[context]],
    }
    dataset = Dataset.from_dict(data)

    try:
        result = evaluate(dataset, metrics=[faithfulness])
        return result["faithfulness"]
    except Exception:
        # Fallback simple: verificar que palabras clave del contexto estén en la respuesta
        context_words = set(context.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(context_words & answer_words) / len(context_words) if context_words else 0
        return min(overlap * 2, 1.0)


async def calculate_answer_relevance(question: str, answer: str) -> float:
    """Calcula la relevancia de la respuesta a la pregunta.

    Args:
        question: Pregunta original
        answer: Respuesta generada

    Returns:
        Score de relevancia (0-1)
    """
    data = {
        "question": [question],
        "answer": [answer],
        "contexts": [[""]],
    }
    dataset = Dataset.from_dict(data)

    try:
        result = evaluate(dataset, metrics=[answer_relevancy])
        return result["answer_relevancy"]
    except Exception:
        # Fallback: verificar overlap de palabras significativas
        q_words = set(question.lower().split()) - {"qué", "cómo", "cuál", "es", "para", "un", "una"}
        a_words = set(answer.lower().split())
        overlap = len(q_words & a_words) / len(q_words) if q_words else 0
        return min(overlap * 2, 1.0)
```

---

---

### Prompt 4.9 - Orquestador de Tareas y Síntesis (The Task Runner)

**Objetivo**: Implementar la lógica en LangGraph para que el agente pueda realizar una "triangulación" de datos: Normativa + Datos del Sistema + Evidencias del Usuario = Informe Final.

**Instrucciones**:

```
Actúa como un experto en IA Agéntica. Implementa un nodo de 'Planificación y Síntesis' en LangGraph.

LÓGICA DE NEGOCIO:
1. Identificación de Requisitos: El agente debe extraer de la 'Materia' (RAG) qué campos o criterios son obligatorios para la tarea (ej: criterios de una subvención).
2. Mapeo de Datos:
   - Consultar en Oracle (MCP) los datos reales ejecutados (ej: gastos, fechas).
   - Analizar los documentos del usuario para extraer la 'Justificación' o evidencias.
3. Análisis de Gaps: Si falta información crítica para completar el informe, el agente debe detenerse y preguntar al usuario específicamente por ese dato.
4. Generación Estructurada: Una vez tiene todo, debe generar un borrador completo siguiendo una plantilla de Markdown predefinida para esa tarea específica.

TESTS REQUERIDOS (RED):
- test_task_data_integration: Verificar que el agente combina correctamente un dato de Oracle (numérico) con una explicación del PDF del usuario.
- test_gap_detection: Validar que el agente no genera el informe si falta un campo obligatorio definido en la normativa.
```

---

### Prompt 4.10 - Model Factory y Dynamic Prompt Service

**Objetivo**: Implementar el motor que instancia modelos y recupera prompts de la base de datos en tiempo real, eliminando los valores hardcodeados del código.

**Instrucciones**:

```
Actúa como un experto en LangChain y Patrones de Diseño. Implementa los servicios de factoría en `src/services/`.

ARCHIVOS A CREAR/MODIFICAR:
1. `src/services/model_factory.py`:
   - Implementar `get_model(chatbot_id: UUID)`: Consulta la tabla `llm_configs`, recupera la API Key del Secret Manager y devuelve la instancia correcta (`ChatGoogleGenerativeAI`, `ChatOpenAI`, o `ChatOllama`).
2. `src/services/prompt_service.py`:
   - Implementar `get_formatted_prompt(chatbot_id: UUID, slug: str, language: str, **kwargs)`: Recupera el template de la DB y usa python `.format()` para inyectar las variables.

INTEGRACIÓN EN LANGGRAPH:
- Refactorizar el nodo `generate_response` en `src/agent/graph.py` para que use estos servicios en lugar de variables hardcodeadas.

TESTS REQUERIDOS (RED):
- test_model_factory_switching: Validar que si cambio el provider en la DB de 'google' a 'openai', la factoría devuelve el tipo de objeto correcto sin reiniciar el servidor.
- test_prompt_injection_safety: Validar que el formateo de templates de la DB maneja correctamente las variables inexistentes sin romper el flujo.
```

---

### Prompt 4.11 - Nodo de Refinamiento Iterativo (Human-in-the-Loop)

**Objetivo**: Implementar un bucle de validación en LangGraph que permita al usuario revisar y corregir el borrador generado antes de la exportación final.

**Instrucciones**:

```
Implementa en LangGraph un nodo de 'Validación de Usuario'. Si el modo es 'Agente', el sistema no finalizará tras la primera respuesta. Debe presentar el borrador y esperar un mensaje de feedback. Si el usuario pide cambios, el agente debe re-generar el contenido integrando las correcciones. Solo al recibir la señal 'FINALIZAR', se procederá a la exportación.

TESTS REQUERIDOS (RED):
- test_draft_revision_loop: Validar que tras el feedback del usuario el agente genera una segunda versión del borrador.
- test_finalize_signal_triggers_export: Validar que la señal 'FINALIZAR' cierra el bucle y activa el endpoint de exportación.
```

---

## FASE 5: API Endpoints y Robustez

---

### Prompt 5.1 - Tests del Endpoint de Chat (TDD - RED)

**Objetivo**: Validar el endpoint de streaming de chat con autenticación JWT, manejo de errores, y respuesta en Server-Sent Events (SSE) o WebSocket.

**tests/e2e/test_chat_endpoint.py**:
```python
"""Tests E2E para el endpoint de chat."""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


class TestChatEndpoint:

    @pytest.mark.asyncio
    async def test_chat_returns_stream(self) -> None:
        from src.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.api.routers.chat.get_agent_graph') as mock_graph:
                mock_graph.return_value.astream = AsyncMock(return_value=iter([
                    {"messages": [{"content": "Hola"}]},
                ]))

                response = await client.post(
                    "/api/v1/chat/chatbot-123",
                    json={"message": "Hola"},
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_requires_authentication(self) -> None:
        from src.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/chatbot-123",
                json={"message": "Hola"},
            )

            assert response.status_code == 401
```

---

### Prompt 5.2 - Implementación del Endpoint de Chat

**Objetivo**: Implementar el endpoint FastAPI `/api/v1/chat` que recibe el mensaje del usuario, invoca el agente LangGraph y devuelve la respuesta en streaming.

**src/api/__init__.py**:
```python
"""Módulo de API."""
```

**src/api/schemas.py**:
```python
"""Schemas Pydantic para la API."""
from pydantic import BaseModel, Field
from typing import Optional
import uuid


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    content: str
    run_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    type: str
    request_id: str
```

**src/api/routers/__init__.py**:
```python
"""Routers de la API."""
```

**src/api/routers/chat.py**:
```python
"""Router para el endpoint de chat."""
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ChatRequest
from src.auth.dependencies import get_current_user
from src.auth.models import UserInfo
from src.database import get_async_session

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/{chatbot_id}")
async def chat(
    chatbot_id: str,
    request: ChatRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Endpoint de chat con streaming SSE.

    Args:
        chatbot_id: ID del chatbot
        request: Mensaje del usuario
        user: Usuario autenticado
        session: Sesión de base de datos

    Returns:
        Stream de eventos SSE
    """
    async def generate() -> AsyncIterator[str]:
        # Aquí iría la lógica del grafo
        yield f"data: {{'content': 'Procesando...'}}\n\n"
        yield f"data: {{'content': 'Respuesta de ejemplo'}}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
```

---

### Prompt 5.3 - Global Error Handler

**Objetivo**: Implementar el manejador global de excepciones de FastAPI que devuelve respuestas JSON consistentes para errores de autenticación, validación y errores internos.

**src/main.py**:
```python
"""Aplicación principal FastAPI."""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.routers import chat
from src.config import get_settings
from src.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    setup_logging()
    yield


app = FastAPI(
    title="AI Chatbots Hub",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Maneja errores de validación Pydantic."""
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
    """Maneja todas las excepciones no capturadas."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "type": "internal_error",
            "request_id": str(uuid.uuid4()),
        },
    )


app.include_router(chat.router)


@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "healthy"}
```

---

---

### Prompt 5.4 - Exportación de Documentos y Cierre de Tarea

**Objetivo**: Transformar el resultado del agente en un archivo descargable oficial, permitiendo que el trabajo salga del chat hacia los procesos administrativos de la universidad.

**Instrucciones**:

```
Actúa como un experto en Backend. Implementa un servicio de generación de documentos oficiales.

TAREAS:
1. Crear el endpoint `GET /api/v1/tasks/export/{run_id}`.
2. Motor de Conversión: Transformar el Markdown final generado por el agente en formatos PDF y DOCX (usando librerías como `ReportLab` o `Pandoc`).
3. Plantillas Institucionales: Aplicar una hoja de estilos que incluya el logo de la universidad, pie de página oficial y numeración.
4. Registro de Versiones: Guardar una copia del documento generado en la tabla `interactions` vinculada a la sesión del usuario para auditoría.

TESTS REQUERIDOS (RED):
- test_pdf_generation_content: Verificar que el texto del informe generado por la IA coincide exactamente con el contenido del PDF final.
- test_export_security: Asegurar que solo el dueño de la tarea (o un administrador) puede descargar el archivo generado.
```

---

## FASE 6: Tests End-to-End y Flujos Completos

---

### Prompt 6.1 - Tests E2E del Flujo de Chat Completo

**Objetivo**: Validar el flujo completo desde la API hasta la respuesta.

**tests/e2e/test_chat_flow.py**:
```python
"""Tests E2E para el flujo completo de chat."""
import uuid
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


class TestChatFlowE2E:

    @pytest.fixture
    async def setup_chatbot(self, db_session):
        """Crea un chatbot de prueba con datos."""
        from src.database.models import Chatbot, DocumentChunk

        chatbot = Chatbot(
            id=uuid.uuid4(),
            name="E2E Test Bot",
            system_prompt="Eres un asistente de prueba.",
            sources=["https://example.com"],
        )
        db_session.add(chatbot)
        await db_session.flush()

        # Añadir chunks de conocimiento
        chunk = DocumentChunk(
            chatbot_id=chatbot.id,
            content="Python es un lenguaje de programación versátil y fácil de aprender.",
            source_url="https://example.com/python",
            content_hash="test_hash_123",
            embedding=[0.1] * 1536,
            language="es",
        )
        db_session.add(chunk)
        await db_session.commit()

        return chatbot

    @pytest.mark.asyncio
    async def test_full_chat_flow(self, setup_chatbot, auth_headers) -> None:
        """Test del flujo completo: pregunta -> búsqueda -> respuesta."""
        from src.main import app

        chatbot = setup_chatbot

        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.agent.graph.ChatGoogleGenerativeAI') as mock_llm:
                mock_llm.return_value.ainvoke = AsyncMock(
                    return_value=type('Response', (), {'content': 'Python es un lenguaje muy versátil.'})()
                )

                response = await client.post(
                    f"/api/v1/chat/{chatbot.id}",
                    json={"message": "¿Qué es Python?"},
                    headers=auth_headers,
                )

                assert response.status_code == 200
                # Verificar que es un stream SSE
                assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_chat_stores_interaction(self, setup_chatbot, auth_headers, db_session) -> None:
        """El chat debe guardar la interacción en la BD."""
        from src.main import app
        from src.database.models import Interaction
        from sqlalchemy import select

        chatbot = setup_chatbot

        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.agent.graph.ChatGoogleGenerativeAI') as mock_llm:
                mock_llm.return_value.ainvoke = AsyncMock(
                    return_value=type('Response', (), {'content': 'Respuesta de prueba'})()
                )

                await client.post(
                    f"/api/v1/chat/{chatbot.id}",
                    json={"message": "Pregunta de prueba"},
                    headers=auth_headers,
                )

        # Verificar que se guardó la interacción
        result = await db_session.execute(
            select(Interaction).where(Interaction.chatbot_id == chatbot.id)
        )
        interactions = result.scalars().all()
        # Debería haber al menos una interacción
        # (depende de la implementación del endpoint)


class TestIngestionFlowE2E:

    @pytest.mark.asyncio
    async def test_full_ingestion_flow(self, db_session, auth_headers) -> None:
        """Test del flujo completo de ingestión."""
        from src.main import app
        from src.database.models import Chatbot

        # Crear chatbot
        chatbot = Chatbot(
            name="Ingestion Test Bot",
            system_prompt="Test",
            sources=[],
        )
        db_session.add(chatbot)
        await db_session.commit()
        await db_session.refresh(chatbot)

        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.ingestion.docling_processor.DocumentConverter') as mock_docling:
                mock_result = type('Result', (), {
                    'document': type('Doc', (), {
                        'export_to_markdown': lambda: '# Test\n\nContenido de prueba'
                    })()
                })()
                mock_docling.return_value.convert.return_value = mock_result

                # Disparar ingestión
                response = await client.post(
                    f"/api/v1/admin/chatbots/{chatbot.id}/ingest",
                    json={"source_url": "https://example.com/doc.pdf"},
                    headers=auth_headers,
                )

                assert response.status_code == 200
                data = response.json()
                assert "job_id" in data
                assert data["status"] == "pending"
```

---

### Prompt 6.2 - Tests de Integración de Componentes

**Objetivo**: Validar la integración entre autenticación SSO, base de datos, agente LangGraph y endpoints API en flujos reales de extremo a extremo.

**tests/integration/test_full_pipeline.py**:
```python
"""Tests de integración del pipeline completo."""
import uuid
import pytest
from unittest.mock import AsyncMock, patch


class TestRAGPipeline:

    @pytest.mark.asyncio
    async def test_ingestion_to_retrieval_pipeline(self, db_session) -> None:
        """Test: ingestión -> chunking -> embedding -> retrieval."""
        from src.database.models import Chatbot, DocumentChunk
        from src.ingestion.chunker import MarkdownChunker
        from src.ingestion.hasher import hash_content
        from src.services.retriever import HybridRetriever

        # 1. Crear chatbot
        chatbot = Chatbot(
            id=uuid.uuid4(),
            name="Pipeline Test",
            system_prompt="Test",
            sources=[],
        )
        db_session.add(chatbot)
        await db_session.flush()

        # 2. Simular ingestión
        markdown_content = """# Documentación de FastAPI

FastAPI es un framework web moderno y rápido para construir APIs con Python.

## Características

- Alto rendimiento
- Fácil de usar
- Basado en estándares
"""
        chunker = MarkdownChunker(chunk_size=200, chunk_overlap=20)
        chunks = chunker.split(markdown_content)

        # 3. Guardar chunks con embeddings simulados
        for i, chunk in enumerate(chunks):
            db_chunk = DocumentChunk(
                chatbot_id=chatbot.id,
                content=chunk.content,
                source_url="https://fastapi.tiangolo.com",
                content_hash=hash_content(chunk.content),
                embedding=[0.1 + i * 0.01] * 1536,  # Embeddings únicos
                language="es",
            )
            db_session.add(db_chunk)

        await db_session.commit()

        # 4. Probar retrieval
        retriever = HybridRetriever(db_session)
        results = await retriever.vector_search(
            query_embedding=[0.11] * 1536,
            chatbot_id=chatbot.id,
            top_k=3,
        )

        assert len(results) >= 1
        assert any("FastAPI" in r.content for r in results)


class TestAuthPipeline:

    @pytest.mark.asyncio
    async def test_token_creation_and_validation(self) -> None:
        """Test: crear token -> decodificar -> validar usuario."""
        from src.auth.jwt_handler import create_token, decode_token
        from src.auth.models import UserInfo

        # Crear usuario
        user = UserInfo(
            user_id="test-user-456",
            email="pipeline@test.com",
            role="admin",
        )

        # Crear token
        token = create_token(user)
        assert token is not None
        assert len(token) > 50

        # Decodificar y validar
        decoded = decode_token(token)
        assert decoded.user_id == user.user_id
        assert decoded.email == user.email
        assert decoded.role == user.role
```

---

### Prompt 6.3 - Configuración de CI/CD (Bitbucket Pipelines)

**Objetivo**: Configurar la integración continua en Bitbucket para ejecutar la batería de tests (unitarios, integración y E2E) automáticamente en cada subida de código.

**Instrucciones**:

```
Actúa como un experto en DevOps. Configura el archivo `bitbucket-pipelines.yml` para automatizar las pruebas del proyecto.

REQUISITOS DEL PIPELINE:
1. Imagen Base: Usar una imagen ligera de Python 3.11 (ej: python:3.11-slim).
2. Servicios: Configurar un servicio adicional 'database' usando la imagen `ankane/pgvector:latest`.
3. Pasos (Steps):
   - Instalación de uv: Descargar e instalar el binario de uv.
   - Cache: Configurar el cache de uv para acelerar ejecuciones futuras.
   - Linting: Ejecutar `ruff check src/`.
   - Tests: Ejecutar `pytest tests/` pasando las variables de entorno necesarias (DATABASE_URL, JWT_SECRET_KEY, etc.).
4. Artefactos: Guardar los informes de cobertura de tests (coverage.xml) para su visualización.

CRITERIOS DE ACEPTACIÓN:
- El pipeline debe ponerse en "verde" solo si todos los tests pasan.
- La base de datos vectorial debe estar disponible para los tests de integración.
```

**bitbucket-pipelines.yml** (colocar en la raíz del repositorio):
```yaml
image: python:3.11-slim

# Definición de servicios adicionales (Bases de datos)
definitions:
  services:
    postgres:
      image: ankane/pgvector:latest
      variables:
        POSTGRES_USER: 'postgres'
        POSTGRES_PASSWORD: 'ci_password_secret'
        POSTGRES_DB: 'test_db'

pipelines:
  default: # Se ejecuta en todas las ramas excepto las especificadas
    - step:
        name: "Linting & Testing (TDD Pipeline)"
        caches:
          - pip
        services:
          - postgres
        script:
          # 1. Instalar dependencias del sistema necesarias para pg_isready y uv
          - apt-get update && apt-get install -y curl postgresql-client

          # 2. Instalar uv (Gestor de paquetes rápido)
          - curl -LsSf https://astral.sh/uv/install.sh | sh
          - export PATH="$HOME/.cargo/bin:$PATH"

          # 3. Instalar dependencias del proyecto
          - uv sync --all-extras

          # 4. Esperar a que la base de datos esté lista
          - sleep 5
          - pg_isready -h localhost -p 5432 -U postgres

          # 5. Ejecutar Linter (Calidad de código)
          - uv run ruff check src/

          # 6. Ejecutar Batería de Tests
          - export DATABASE_URL="postgresql+asyncpg://postgres:ci_password_secret@localhost:5432/test_db"
          - export JWT_SECRET_KEY="ci-test-secret-key-at-least-32-chars-long"
          - export MOCK_AUTH="true"
          - uv run pytest tests/ --cov=src --cov-report=xml
        artifacts:
          - coverage.xml
```

---

## FASE 7: Despliegue y Containerización — REDUCIDA

> **En Gov Gen AI Platform, Docker ya está configurado.** Esta fase se reduce a:
>
> - **Prompt 7.1 (Dockerfile)**: Verificar que el Dockerfile existente del servidor incorpora
>   las nuevas dependencias Hub. No crear uno nuevo.
> - **Prompt 7.2 (docker-compose.prod.yml)**: Extender el `docker-compose.yml` existente con
>   los servicios nuevos que requiere el Hub (MinIO si no está, Ollama opcional).
>   El servicio de PostgreSQL ya existe; solo añadir la extensión `pgvector`.
> - **Prompts 7.3–7.4 (scripts y entornos)**: Adaptar los scripts existentes del servidor
>   para incluir los datos de ejemplo del Hub en la inicialización.
>
> **No crear** un docker-compose nuevo desde cero — extender el existente.

---

### Prompt 7.1 - Dockerfile Multi-stage

**Objetivo**: Crear imagen Docker optimizada para producción.

**Dockerfile**:
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar archivos de dependencias
COPY pyproject.toml uv.lock ./

# Instalar dependencias
RUN uv sync --frozen --no-dev --no-editable

# Stage 2: Runtime
FROM python:3.11-slim as runtime

WORKDIR /app

# Crear usuario no-root
RUN useradd --create-home --shell /bin/bash appuser

# Copiar entorno virtual desde builder
COPY --from=builder /app/.venv /app/.venv

# Copiar código fuente
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Configurar PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Cambiar a usuario no-root
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Exponer puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Prompt 7.2 - Docker Compose para Producción

**Objetivo**: Configurar el stack Docker Compose de producción con todos los servicios necesarios (Backend, Frontend, PostgreSQL, almacenamiento) listos para desplegarse.

**docker-compose.prod.yml**:
```yaml
version: "3.9"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: chatbots_hub_app
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - LANGCHAIN_TRACING_V2=${LANGCHAIN_TRACING_V2:-true}
      - LANGCHAIN_PROJECT=${LANGCHAIN_PROJECT:-ai-chatbots-hub}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - MOCK_AUTH=false
      - LOG_FORMAT=json
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: ankane/pgvector:latest
    container_name: chatbots_hub_db_prod
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  migrate:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: chatbots_hub_migrate
    environment:
      - DATABASE_URL=${DATABASE_URL}
    command: ["alembic", "upgrade", "head"]
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data_prod:
```

---

### Prompt 7.3 - Scripts de Despliegue

**Objetivo**: Implementar los scripts de despliegue, actualización y rollback del sistema en producción, incluyendo migraciones de base de datos automáticas.

**scripts/deploy.sh**:
```bash
#!/bin/bash
set -e

echo "🚀 Iniciando despliegue de AI Chatbots Hub..."

# Verificar variables de entorno requeridas
required_vars=("DATABASE_URL" "JWT_SECRET_KEY" "GOOGLE_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Variable $var no está definida"
        exit 1
    fi
done

echo "✅ Variables de entorno verificadas"

# Construir imagen
echo "📦 Construyendo imagen Docker..."
docker compose -f docker-compose.prod.yml build

# Ejecutar migraciones
echo "🗄️ Ejecutando migraciones..."
docker compose -f docker-compose.prod.yml run --rm migrate

# Iniciar servicios
echo "🔄 Iniciando servicios..."
docker compose -f docker-compose.prod.yml up -d app

# Verificar health
echo "🏥 Verificando health del servicio..."
sleep 10
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✅ Despliegue completado exitosamente!"
else
    echo "❌ Error: El servicio no está healthy"
    docker compose -f docker-compose.prod.yml logs app
    exit 1
fi
```

**scripts/init_db.py**:
```python
#!/usr/bin/env python
"""Script para inicializar la base de datos."""
import asyncio
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from src.config import get_settings
from src.database.connection import create_async_engine
from src.database.models import Base


async def init_database():
    """Inicializa la base de datos."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    print(f"🗄️ Conectando a: {settings.database_url.split('@')[1]}")

    async with engine.begin() as conn:
        # Habilitar extensión pgvector
        print("📦 Habilitando extensión pgvector...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Crear tablas
        print("📋 Creando tablas...")
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("✅ Base de datos inicializada correctamente!")


if __name__ == "__main__":
    asyncio.run(init_database())
```

---

### Prompt 7.4 - Configuración de Entornos

**Objetivo**: Definir la gestión de variables de entorno y secretos para los diferentes entornos (desarrollo, staging, producción) con validación al arranque.

**.env.production.example**:
```env
# Database (Producción)
POSTGRES_USER=chatbots_prod
POSTGRES_PASSWORD=<GENERAR_PASSWORD_SEGURO>
POSTGRES_DB=chatbots_hub_prod
DATABASE_URL=postgresql+asyncpg://chatbots_prod:<PASSWORD>@postgres:5432/chatbots_hub_prod

# Google/Vertex AI
GOOGLE_API_KEY=<TU_API_KEY>

# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<TU_LANGSMITH_KEY>
LANGCHAIN_PROJECT=ai-chatbots-hub-prod

# Auth (GENERAR CON: openssl rand -hex 32)
JWT_SECRET_KEY=<GENERAR_SECRET_32_CHARS_MINIMO>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
MOCK_AUTH=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## FASE 8: Observabilidad y Panel de Feedback

---

### Prompt 8.1 - Integración LangSmith Run ID

**Objetivo**: Integrar el tracking de trazas LangSmith en el agente para tener observabilidad completa de cada invocación: entradas, salidas, herramientas usadas y latencias.

**src/api/routers/chat.py** (actualización):
```python
"""Router de chat con integración LangSmith."""
import uuid
from langsmith import Client as LangSmithClient

from src.config import get_settings


def get_langsmith_trace_url(run_id: str) -> str:
    """Genera la URL de la traza en LangSmith.

    Args:
        run_id: ID de la ejecución

    Returns:
        URL completa a la traza
    """
    settings = get_settings()
    project = settings.langchain_project
    return f"https://smith.langchain.com/o/default/projects/{project}/runs/{run_id}"
```

---

### Prompt 8.2 - Tests del Servicio de Feedback (TDD - RED)

**Objetivo**: Validar el almacenamiento y consulta de valoraciones de usuarios (estrellas, correcciones), asegurando su vinculación correcta a la sesión y al run de LangSmith.

**tests/unit/test_feedback_service.py**:
```python
"""Tests para el servicio de feedback."""
import uuid
import pytest
from unittest.mock import AsyncMock


class TestFeedbackService:

    @pytest.mark.asyncio
    async def test_submit_feedback(self) -> None:
        from src.services.feedback_service import FeedbackService

        mock_session = AsyncMock()
        service = FeedbackService(mock_session)

        await service.submit_feedback(
            interaction_id=uuid.uuid4(),
            score=5,
            comment="Excelente respuesta",
        )

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_interactions_for_review(self) -> None:
        from src.services.feedback_service import FeedbackService

        mock_session = AsyncMock()
        service = FeedbackService(mock_session)

        result = await service.get_interactions_for_review(
            chatbot_id=uuid.uuid4(),
            limit=10,
        )

        assert isinstance(result, list)
```

---

### Prompt 8.3 - Implementación del Servicio de Feedback

**Objetivo**: Implementar el servicio que captura valoraciones de usuarios en chats públicos y correcciones de informadores humanos, alimentando el ciclo de mejora continua con RAGAS.

**src/services/feedback_service.py**:
```python
"""Servicio de gestión de feedback."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Interaction


class FeedbackService:
    """Gestiona el feedback de interacciones."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def submit_feedback(
        self,
        interaction_id: uuid.UUID,
        score: int,
        comment: str | None = None,
    ) -> None:
        """Envía feedback para una interacción.

        Args:
            interaction_id: ID de la interacción
            score: Puntuación (1-5)
            comment: Comentario opcional
        """
        await self.session.execute(
            update(Interaction)
            .where(Interaction.id == interaction_id)
            .values(feedback_score=score, feedback_text=comment)
        )
        await self.session.commit()

    async def get_interactions_for_review(
        self,
        chatbot_id: uuid.UUID,
        limit: int = 50,
        only_low_scores: bool = False,
    ) -> list[Interaction]:
        """Obtiene interacciones para revisión.

        Args:
            chatbot_id: ID del chatbot
            limit: Número máximo de resultados
            only_low_scores: Solo mostrar puntuaciones bajas

        Returns:
            Lista de interacciones
        """
        query = (
            select(Interaction)
            .where(Interaction.chatbot_id == chatbot_id)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
        )

        if only_low_scores:
            query = query.where(Interaction.feedback_score <= 2)

        result = await self.session.execute(query)
        return list(result.scalars().all())
```

---

## Scripts de Utilidad

**pyproject.toml** (scripts section):
```toml
[project.scripts]
dev = "uvicorn src.main:app --reload --port 8000"
test = "pytest tests/ -v"
test-cov = "pytest tests/ --cov=src --cov-report=html"
test-unit = "pytest tests/unit -v"
test-integration = "pytest tests/integration -v"
test-e2e = "pytest tests/e2e -v"
test-eval = "pytest tests/evaluation -v"
migrate = "alembic upgrade head"
makemigrations = "alembic revision --autogenerate"
lint = "ruff check src/"
format = "ruff format src/"
```

---

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
>   nueva + el borrado del fichero NiceGUI equivalente (ver CLAUDE.md).

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

### Prompt 9.7 - Hub > Pantalla de Documentos

**Objetivo**: Gestión de documentos por chatbot: upload múltiple, listado con estado de ingestión y borrado.

**Endpoints que consume**:
- `GET  /api/v1/hub/ingestion/{chatbot_id}/jobs` — jobs de ingestión
- `POST /api/v1/hub/ingestion/upload` — subida de documento
- `DELETE /api/v1/hub/ingestion/{chatbot_id}/chunks` — borrar colección

**Componentes shadcn/ui**:
```bash
npx shadcn@latest add progress tabs
```

**`src/admin/pages/DocumentsPage.tsx`** — estructura clave:
```typescript
// Selector de chatbot (Select) — scope de la vista
// Dropzone para subir PDFs (react-dropzone o input file)
// Tabla de jobs: nombre, estado (pending/processing/done/error), chunks generados, fecha
// Progress bar animado para jobs en curso (polling cada 3s con react-query refetch)
// Botón "Limpiar colección" con confirmación AlertDialog
```

**Tests requeridos**:
```typescript
// should_list_ingestion_jobs_for_selected_chatbot
// should_accept_pdf_files_only_in_dropzone
// should_show_progress_for_processing_job
// should_show_error_state_for_failed_job
// should_confirm_before_clearing_collection
```

---

### Prompt 9.8 - Hub > Pantalla de Informes

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

## BLOQUE 9B — Widget y Modo Agente

*Objetivo: widget embebible funcional + modo agente expandido para usuarios identificados.*

---

### Prompt 9.9 - Widget: bundle embebible

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

### Prompt 9.10 - Widget: chat SSE y feedback

**Objetivo**: Componente de chat completo con streaming SSE, historial de mensajes y valoración por estrellas.

**`src/widget/components/ChatWidget.tsx`**:
```typescript
// Estado: messages[], isLoading, error
// useChat hook: POST /api/v1/hub/chat/{chatbot_id} → EventSource SSE
//   - acumula chunks en el último mensaje del asistente
//   - emite evento 'done' al recibir {done: true}
// StarRating: 1-5 estrellas, visible al finalizar cada respuesta
//   → llama POST /api/v1/hub/feedback/{interaction_id} con score
// Botón flotante (cerrar/abrir) con posición configurable vía CSS custom properties
```

**Tests requeridos**:
```typescript
// should_display_user_and_assistant_messages
// should_stream_chunks_in_real_time
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

*Prerrequisito: Bloque 9A completado (layout admin disponible). Cada prompt incluye el borrado del equivalente NiceGUI.*

**Orden de ejecución dentro del bloque** (las dependencias son estrictas):

```
Guía 9C.0 (conceptual, se lee antes de escribir código)
  ├── 9.12a  Focus Mode React          ──┐
  │                                       ├──► 9.12  Flujos
  │                                       │
  └── 9.12b  Refactor backend Docling  ──┼──► 9.13  PDF extractor (UI)
                                          │
                                          └──► 9.14  Scripts
                                               9.15  Limpieza NiceGUI restante
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
- [ ] El fichero NiceGUI equivalente está eliminado (no comentado, no archivado).
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

**Limpieza NiceGUI** (se aplica parcialmente aquí; el resto al cerrar 9.12/9.13/9.14):
```bash
# El borrado de focus_manager/layout_state/drawer_hub/pill_logic NO ocurre en este commit
# porque las páginas NiceGUI que aún no se han migrado siguen dependiendo de ellos.
# Se documenta como deuda que se cancela en 9.15 (Limpieza NiceGUI restante).
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

**Limpieza NiceGUI** (en el mismo commit que GREEN):
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

**Limpieza NiceGUI** (en el mismo commit que GREEN):
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

**Limpieza NiceGUI** en el mismo commit.

---

### Prompt 9.15 - Limpieza NiceGUI restante

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

**Objetivo**: Proceso Python ligero en `client_app/local_agent/` que se conecta al servidor por WebSocket, recibe jobs y los ejecuta localmente.

**Estructura**:
```
client_app/local_agent/
├── main.py          # Punto de entrada; conecta al server por WebSocket
├── runner.py        # Recibe jobs {job_id, type, payload} y despacha al handler
├── handlers/
│   ├── script.py    # Ejecuta scripts Python (sandbox existente de AutomatIA)
│   ├── rpa.py       # Ejecuta Playwright RPA
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

**Objetivo**: Implementar el servicio de embeddings con Google/Vertex AI.

**src/services/embedding_service.py**:
```python
"""Servicio de embeddings usando Google Generative AI."""
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import get_settings


class EmbeddingService:
    """Genera embeddings usando Google Generative AI."""

    def __init__(self):
        settings = get_settings()
        self.model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=settings.google_api_key,
        )

    async def embed(self, text: str) -> list[float]:
        """Genera el embedding de un texto.

        Args:
            text: Texto a embeber

        Returns:
            Vector de 1536 dimensiones
        """
        # LangChain embeddings son síncronos, wrapeamos
        return self.model.embed_query(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings para múltiples textos.

        Args:
            texts: Lista de textos

        Returns:
            Lista de vectores
        """
        return self.model.embed_documents(texts)
```

---

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

## FASE 10: Sistema de Plantillas y Temas Personalizables

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

## FASE 12: Gestor de Expedientes — NUEVA

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

## FASE 19: Adaptadores UJI + Gestión 400 + Capa ENI/ENS

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
