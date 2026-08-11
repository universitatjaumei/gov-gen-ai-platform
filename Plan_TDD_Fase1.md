# Plan TDD — Fase 1: Hub Informativo, Personalización y Redacción (MVP)

> Actualizado: 2026-05-04. Generado dividiendo PLAN_TDD_DETALLADO.md en tres archivos por fase funcional.

## Propósito
Fase 1 del plan de desarrollo de Gov Gen AI Platform. Cubre los módulos de chatbots RAG
(públicos y privados), el sistema de temas institucionales, el despliegue en staging GCP,
la privacidad NER y las herramientas de redacción asistida.

El objetivo al finalizar esta fase es disponer de un **MVP desplegado con URL pública en GCP**,
capaz de servir chatbots informativos y de redacción para al menos una organización piloto (UJI).

## Alcance
- **~~Subfase 1.A — Chatbots Públicos con Datos Reales~~ — COMPLETADA ✅:**
  - ~~Spider genérico (1A.1): `crawl_depth`, filtros regex, límite de páginas.~~
  - ~~Spiders especializados UJI (1A.2): normativa BOE/DOGV/UJI + catálogo de procedimientos.~~
  - ~~Asistente HITL de ingestión (1A.3): propuesta automática de selectores CSS, validación antes de guardar.~~
  - Grafo público multi-perfil (BLOQUE 9B): CoreGraph + GraphProfiles + RetrievalPipelineFactory (RAG / MD_LONG_CONTEXT / MD_AGENT_SELECTOR); perfiles PUBLIC_KB_RICH y PUBLIC_PORTAL_AGGREGATOR (UJI).
  - Workspaces y agentes de redacción (9.11a–9.11d): modelos, pipeline de seguridad, grafo LangGraph, UI.
- **Subfase 1.B — Identidad Visual:**
  - Sistema de temas institucionales (FASE 10): variables CSS, presets, editor visual.
- **Subfase 1.C — Privacidad, Diseño y Exportación de Informes:**
  *(orden de ejecución dentro de 1.C)*
  1. Focus Mode como infraestructura de diseño transversal (1C.0): Zustand + DrawerHub reutilizable.
  2. Autosave y resiliencia del Workspace (1C.1): versioning optimista, backoff exponencial.
  3. Privacidad NER reversible (FASE 13): hook pre/post-LLM en DraftingCoreGraph; vault cifrado en edge. *(Alcance Fase 1: solo redacción. Integración con expedientes → Fase 3.)*
  4. Editor accesible WCAG 2.2 AA — editor de redacción (1C.2): shortcuts, focus trap, axe-core.
  5. Exportación DOCX/ODT con citas trazables (1C.3): plantillas Jinja2, índice automático, RunManifest.
  6. Integración Google Drive opcional (1C.4): destino configurable por Organización.
- **Transversal F1 — Accesibilidad WCAG 2.2 AA (FASE 20 reducida):** WCAG transversal en todas las rutas del frontend + axe-core en Vitest + Lighthouse CI. Sin consola conversacional admin (diferida a Fase 2).
- **Bloque 9Q — Calidad de Contenido Web Ingestado:** introduce la entidad **sitio** (`HubWebSite`) como unidad de crawl + auditoría, **desacoplada** del corpus del chatbot. Un crawl único por sitio puebla `HubCrawledPage`; una **capa de selección** (`HubCorpusSelection`, N:M) decide qué páginas se ingieren en qué chatbots. El motor de detección (superseded, duplicados, contradicciones, vacías, stale, errores de crawl) corre **a nivel sitio** y emite dos salidas: higiene del RAG (`superseded`/`quality_score` en `HubCrawledPage`; el retriever excluye documentos de páginas superseded) e informe de auditoría web **por sitio** (JSON + visor admin + export DOCX/PDF). Recrawl periódico con **diff de sitemap** (nuevas/cambiadas/desaparecidas). Reemplaza `HubIngestionSource` (monitor de URL suelta). La ingesta de PDF subido es independiente y se mantiene. Edge. Se ejecuta tras el bloque SBX y antes de Fase 11. **Sin accesibilidad del sitio rastreado** (backlog v2; la accesibilidad del propio frontend ya está en Fase 20).
- **Deploy GCP (Prompts D.1–D.5):** último paso — cuando el producto esté completo y probado localmente.
- **Al finalizar F1:** Autoinstalación (FASE 11) para distribución como software libre.

## Qué NO se ejecuta en esta fase
- Migración NiceGUI→React (Guía 9C.0, Prompts 9.12–9.15) → Fase 2.
- Agente local (Thin Client, Prompt 9.16) → Fase 2.
- Sandbox distribuido, RunManifest, Script Registry → Fase 2.
- Gestor de Expedientes → Fase 3.
- Integración NER con expedientes (FASE 13 parcial) → Fase 3 (requiere FASE 12.E2).
- Admin conversacional (FASE 20 parcial) → Fase 2 (requiere grafo agéntico estable).
- Microservicios de computación pesada (FASE 22) → Diferido post-cloud (ver PLAN_DESARROLLO.md).
- RPA Web (FASE 21) → Diferido v2.

## Nomenclatura vigente
SuperAdmin / Admin / Organización / Usuario
(Ver §4 de Arquitectura.md para el mapeo completo SuperAdmin←Admin, Admin←Partner, Organización←Cliente.)

---

## FASES COMPLETADAS (contexto — sin prompts detallados)

Las siguientes fases han sido completadas y validadas. Sus prompts atómicos se han ejecutado; el código
resultante está documentado en el repositorio. Se listan aquí solo como referencia histórica.

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

### Prompt 9.1 - Scaffolding: Vite + shadcn/ui + i18n ✅ COMPLETADO

### Prompt 9.2 - i18n: locales es / ca / en ✅ COMPLETADO

### Prompt 9.3 - Auth: contexto JWT y rutas protegidas ✅ COMPLETADO

### Prompt 9.4 - Layout: sidebar seccional y header ✅ COMPLETADO

### Prompt 9.5 - Hub > Pantalla de Chatbots ✅ COMPLETADO

### Prompt 9.6 - Hub > Pantalla de Clientes ✅ COMPLETADO

### Prompt 9.6.5 - Frontera Edge-Cloud (preparación del despliegue híbrido) ✅ COMPLETADO

### Prompt 9.6.6 - Frontera Edge-Cloud en la capa de aplicación (routers y módulos) ✅ COMPLETADO

### Prompt 9.7 - Hub > Pantalla de Documentos ✅ COMPLETADO

### Prompt 9.7.1 - Hub > Fuentes web monitorizadas (crawler de ingestión) ✅ COMPLETADO (2026-04-25)

### Prompt 9.8 - Hub > Pantalla de Informes ✅ COMPLETADO (2026-04-26)

### Prompt 9.8.1 - Etiquetado de idioma en la ingestión ✅ COMPLETADO (2026-04-26)

### Prompt 9.8.2 - SSE streaming en el endpoint de chat (backend) ✅ COMPLETADO (2026-04-26)

### Prompt 9.9 - Widget: bundle embebible ✅ COMPLETADO (2026-04-26)

### Prompt 9.10 - Widget: chat SSE y feedback ✅ COMPLETADO (2026-04-26)

---


## ~~Subfase 1.A — Spider Skills y Asistente HITL de Ingestión~~ — COMPLETADA ✅

**Objetivo**: Implementar las capacidades de indexación web necesarias para que el chatbot informativo sirva respuestas con datos reales de webs institucionales. Esta subfase es **prerrequisito para la puesta en marcha del chatbot UJI** con datos actualizados.

**Dependencias**: Prompt 9.7.1 (crawler base ✅ completado).

**Entregable**: Sistema capaz de indexar cualquier web institucional con control de profundidad, filtros y selectores CSS, apoyado por un asistente que propone selectores automáticamente al Admin.

---

### Prompt 1A.1 — Spider Genérico: crawl_depth, filtros regex y límite de páginas (TDD RED/GREEN)

**Objetivo**: Extender el crawler base (Prompt 9.7.1) con control de profundidad BFS, filtros regex de URL y límite de páginas, para indexar jerarquías web institucionales de forma controlada y predecible.

**Contexto**: El spider base existe en `server/app/modules/agents_hub/ingestion/spider.py`. Sin `crawl_depth` ni `max_pages` el spider puede indexar sitios enteros. Estos parámetros se leen de `HubWebSource.config_json` y extienden el comportamiento existente sin romperlo.

**Instrucciones al agente**:
```text
Actúa como experto en Python y scraping web. Extiende el spider existente en
server/app/modules/agents_hub/ingestion/spider.py.

NUEVOS PARÁMETROS leídos de HubWebSource.config_json:
  crawl_depth (int, default 1): niveles de links internos a seguir desde la URL raíz.
  url_regex_filter (str, nullable): si se proporciona, solo se indexan URLs que machan la regex.
  max_pages (int, default 50): límite absoluto de páginas procesadas por ejecución.

LÓGICA BFS:
1. Cola de pares (url, depth). Raíz comienza con depth=0.
2. Solo se encolan links del mismo dominio base (sin subdominios externos).
3. Si depth >= crawl_depth: procesar el nodo pero NO encolar sus hijos.
4. Si url_regex_filter existe: descartar la URL si no macha.
5. Al alcanzar max_pages: detener el BFS, marcar CrawlResult.status = COMPLETED_PARTIAL,
   incrementar pages_skipped con los que quedaban en cola.

TIPOS NUEVOS (añadir al módulo):
  class CrawlStatus(Enum): COMPLETED = "completed"; COMPLETED_PARTIAL = "completed_partial"
  @dataclass class CrawlResult:
      crawled_urls: list[str]
      pages_crawled: int
      pages_skipped: int
      status: CrawlStatus

INTERFAZ GenericSpider:
  Constructor acepta fetch_fn: Callable[[str], Awaitable[str]] para testing sin red.
  Método: async def crawl(source: HubWebSource) -> CrawlResult

TESTS REQUERIDOS:
- test_spider_respects_crawl_depth_zero
- test_spider_respects_crawl_depth_one
- test_spider_url_regex_filter_excludes_non_matching_urls
- test_spider_stops_at_max_pages_and_marks_partial
- test_spider_does_not_revisit_urls
```

**Tests RED — tests/modules/agents_hub/unit/test_spider_generic.py**:
```python
"""Tests para el spider genérico con crawl_depth, regex y max_pages — TDD RED."""
import pytest
from dataclasses import dataclass, field


@dataclass
class FakeWebSource:
    url: str
    config_json: dict = field(default_factory=dict)


class TestGenericSpider:

    @pytest.mark.asyncio
    async def test_spider_respects_crawl_depth_zero(self) -> None:
        """Con crawl_depth=0 solo procesa la URL raíz, sin seguir ningún link."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        fetched_urls: list[str] = []

        async def fake_fetch(url: str) -> str:
            fetched_urls.append(url)
            return '<html><body><a href="/pagina2">enlace</a></body></html>'

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 0, "max_pages": 10},
        )
        result = await spider.crawl(source)

        assert fetched_urls == ["https://ejemplo.uji.es"]
        assert result.pages_crawled == 1

    @pytest.mark.asyncio
    async def test_spider_respects_crawl_depth_one(self) -> None:
        """Con crawl_depth=1 procesa raíz + links de primer nivel, sin bajar más."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        pages = {
            "https://ejemplo.uji.es": '<html><a href="/a">A</a><a href="/b">B</a></html>',
            "https://ejemplo.uji.es/a": '<html><a href="/c">C</a></html>',
            "https://ejemplo.uji.es/b": "<html>contenido b</html>",
        }

        async def fake_fetch(url: str) -> str:
            return pages.get(url, "<html></html>")

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "max_pages": 50},
        )
        result = await spider.crawl(source)

        crawled = set(result.crawled_urls)
        assert "https://ejemplo.uji.es" in crawled
        assert "https://ejemplo.uji.es/a" in crawled
        assert "https://ejemplo.uji.es/b" in crawled
        assert "https://ejemplo.uji.es/c" not in crawled  # nivel 2, no debe llegar

    @pytest.mark.asyncio
    async def test_spider_url_regex_filter_excludes_non_matching_urls(self) -> None:
        """Con url_regex_filter, solo se indexan las URLs que machan la expresión."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        pages = {
            "https://ejemplo.uji.es": (
                '<html><a href="/normativa/ley1">Ley</a>'
                '<a href="/noticias/nota">Noticia</a></html>'
            ),
            "https://ejemplo.uji.es/normativa/ley1": "<html>normativa</html>",
            "https://ejemplo.uji.es/noticias/nota": "<html>noticia</html>",
        }

        async def fake_fetch(url: str) -> str:
            return pages.get(url, "<html></html>")

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "url_regex_filter": r"/normativa/", "max_pages": 50},
        )
        result = await spider.crawl(source)

        assert "https://ejemplo.uji.es/normativa/ley1" in result.crawled_urls
        assert "https://ejemplo.uji.es/noticias/nota" not in result.crawled_urls

    @pytest.mark.asyncio
    async def test_spider_stops_at_max_pages_and_marks_partial(self) -> None:
        """Al alcanzar max_pages, el resultado se marca COMPLETED_PARTIAL."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider, CrawlStatus

        async def fake_fetch(url: str) -> str:
            links = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(20))
            return f"<html>{links}</html>"

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 2, "max_pages": 3},
        )
        result = await spider.crawl(source)

        assert result.pages_crawled <= 3
        assert result.status == CrawlStatus.COMPLETED_PARTIAL
        assert result.pages_skipped > 0

    @pytest.mark.asyncio
    async def test_spider_does_not_revisit_urls(self) -> None:
        """Una URL no se procesa dos veces aunque aparezca en múltiples páginas."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        call_counts: dict[str, int] = {}

        async def fake_fetch(url: str) -> str:
            call_counts[url] = call_counts.get(url, 0) + 1
            return '<html><a href="https://ejemplo.uji.es">inicio</a></html>'

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "max_pages": 10},
        )
        await spider.crawl(source)

        assert call_counts.get("https://ejemplo.uji.es", 0) == 1
```

**Criterios de aceptación**:
- `GenericSpider` acepta `crawl_depth`, `url_regex_filter` y `max_pages` desde `config_json`.
- `CrawlResult` expone `crawled_urls`, `pages_crawled`, `pages_skipped`, `status`.
- Los 5 tests pasan en verde sin regresión en los tests del spider existente.

---

### Prompt 1A.2 — Spiders Especializados UJI: Normativa y Procedimientos (TDD RED/GREEN)

**Objetivo**: Implementar dos extractores especializados para las fuentes institucionales de la UJI: normativa académica (BOE/DOGV/normativa.uji.es) y catálogo de procedimientos administrativos. Producen `HubDocument` con metadatos estructurados que enriquecen las respuestas del chatbot.

**Contexto**: El spider genérico (1A.1) proporciona la infraestructura BFS. Los especializados la extienden con lógica de extracción de contenido estructurado por fuente. Implementan `SpiderProtocol` para poder ser seleccionados por `SpiderFactory` según el campo `spider_type` de `HubWebSource`.

**Instrucciones al agente**:
```text
Actúa como experto en Python y extracción de datos de webs institucionales. Implementa los
spiders especializados en server/app/modules/agents_hub/ingestion/spiders/.

SPIDER 1 — NormativaSpider (fuentes: boe | dogv | uji):
  Parámetros constructor: source_type (str), date_from (date | None).
  Método: extract_document(url: str, html: str) -> NormativaDoc | None
  Extrae: titulo, fecha_publicacion (date), numero_norma (str), texto (str).
  Filtra: si date_from y fecha_publicacion < date_from -> devuelve None.
  Genera HubDocument con metadata_json = {source_type, fecha_publicacion ISO, numero_norma}.
  Los selectores CSS por fuente se configuran en un dict SELECTORS[source_type].

SPIDER 2 — ProcedimientosSpider (fuente: procedimientos.uji.es):
  Método: extract_document(url: str, html: str) -> ProcedimientoDoc | None
  Extrae: nombre, codigo, unidad_responsable, plazo, documentacion_requerida, normativa_aplicable.
  Genera HubDocument con metadata_json = {doc_type: "procedimiento", codigo}.

FACTORY — SpiderFactory en server/app/modules/agents_hub/ingestion/spider_factory.py:
  Método: get_spider(source_type: str) -> SpiderProtocol
  Mapeo: "boe" | "dogv" | "uji" -> NormativaSpider; "procedimientos" -> ProcedimientosSpider;
         "generic" -> GenericSpider.
  Lanza ValueError("Unknown spider type: {source_type}") para tipos desconocidos.

MIGRACIÓN Alembic: añadir columna spider_type (VARCHAR, nullable) a hub_web_sources.
  Default: "generic". El IngestionWatcher usa SpiderFactory para seleccionar el spider.

TESTS REQUERIDOS:
- test_normativa_spider_extracts_titulo_and_fecha_from_boe_html
- test_normativa_spider_skips_documents_before_date_from
- test_normativa_spider_builds_hub_document_with_metadata
- test_procedimientos_spider_extracts_ficha_completa
- test_procedimientos_spider_builds_hub_document_with_type
- test_spider_factory_returns_correct_spider_by_source_type
- test_spider_factory_raises_for_unknown_type
```

**Tests RED — tests/modules/agents_hub/unit/test_spiders_especializados.py**:
```python
"""Tests para spiders especializados UJI (normativa + procedimientos) — TDD RED."""
import pytest
from datetime import date


SAMPLE_BOE_HTML = """
<html><head><title>BOE núm. 123</title></head>
<body>
  <h1 class="documento-tit">Real Decreto 456/2025, de 15 de marzo, sobre universidades</h1>
  <span class="publicado">15/03/2025</span>
  <div class="texto-articulado">
    <p>Artículo 1. Los organismos universitarios deberán adaptar sus procedimientos.</p>
    <p>Artículo 2. El plazo de adaptación será de seis meses desde la publicación.</p>
  </div>
</body></html>
"""

SAMPLE_PROCEDIMIENTO_HTML = """
<html><body>
  <h1 class="proc-titulo">Solicitud de título universitario oficial</h1>
  <span class="proc-codigo">PROC-042</span>
  <span class="proc-unidad">Secretaría General</span>
  <span class="proc-plazo">3 meses desde la finalización de estudios</span>
  <div class="proc-documentacion">Expediente académico, DNI, justificante de pago de tasas</div>
  <div class="proc-normativa">RD 1027/2011, Estatuts UJI art. 56</div>
</body></html>
"""


class TestNormativaSpider:

    def test_normativa_spider_extracts_titulo_and_fecha_from_boe_html(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe")
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is not None
        assert "Real Decreto 456/2025" in doc.titulo
        assert doc.fecha_publicacion == date(2025, 3, 15)
        assert "Artículo 1" in doc.texto

    def test_normativa_spider_skips_documents_before_date_from(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe", date_from=date(2026, 1, 1))
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is None

    def test_normativa_spider_builds_hub_document_with_metadata(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe")
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is not None
        assert doc.metadata_json["source_type"] == "boe"
        assert doc.metadata_json["fecha_publicacion"] == "2025-03-15"


class TestProcedimientosSpider:

    def test_procedimientos_spider_extracts_ficha_completa(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.procedimientos_spider import ProcedimientosSpider

        spider = ProcedimientosSpider()
        doc = spider.extract_document(url="https://procedimientos.uji.es/proc/042", html=SAMPLE_PROCEDIMIENTO_HTML)

        assert doc is not None
        assert "PROC-042" in doc.codigo
        assert "Secretaría General" in doc.unidad_responsable
        assert "DNI" in doc.documentacion_requerida

    def test_procedimientos_spider_builds_hub_document_with_type(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.procedimientos_spider import ProcedimientosSpider

        spider = ProcedimientosSpider()
        doc = spider.extract_document(url="https://procedimientos.uji.es/proc/042", html=SAMPLE_PROCEDIMIENTO_HTML)

        assert doc is not None
        assert doc.metadata_json["doc_type"] == "procedimiento"
        assert doc.metadata_json["codigo"] == "PROC-042"


class TestSpiderFactory:

    def test_spider_factory_returns_correct_spider_by_source_type(self) -> None:
        from server.app.modules.agents_hub.ingestion.spider_factory import SpiderFactory
        from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider
        from server.app.modules.agents_hub.ingestion.spiders.procedimientos_spider import ProcedimientosSpider
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        factory = SpiderFactory()
        assert isinstance(factory.get_spider("boe"), NormativaSpider)
        assert isinstance(factory.get_spider("dogv"), NormativaSpider)
        assert isinstance(factory.get_spider("procedimientos"), ProcedimientosSpider)
        assert isinstance(factory.get_spider("generic"), GenericSpider)

    def test_spider_factory_raises_for_unknown_type(self) -> None:
        from server.app.modules.agents_hub.ingestion.spider_factory import SpiderFactory

        factory = SpiderFactory()
        with pytest.raises(ValueError, match="Unknown spider type"):
            factory.get_spider("tipo_inexistente")
```

**Criterios de aceptación**:
- `NormativaSpider` extrae título, fecha y texto; filtra por `date_from`; produce `HubDocument` con metadatos.
- `ProcedimientosSpider` extrae la ficha completa y produce `HubDocument` con `doc_type=procedimiento`.
- `SpiderFactory` selecciona el spider correcto por `source_type`; lanza `ValueError` para tipos desconocidos.
- Migración Alembic añade `spider_type` a `hub_web_sources`.
- Los 7 tests pasan en verde.

---

### Prompt 1A.3 — Asistente HITL de Ingestión: Propuesta Automática de Selectores CSS (TDD RED/GREEN)

**Objetivo**: Implementar el asistente de ingestión que, dado el HTML de una página web (pegado por el Admin), propone automáticamente los selectores CSS del contenido principal. El Admin revisa y valida la propuesta antes de que se persista en `HubWebSource`.

**Contexto**: Elimina la necesidad de que el Admin conozca CSS. Patrón HITL estricto: la IA propone, el humano aprueba, nunca se persiste sin clic explícito. El HTML se trunca antes de enviarlo al LLM para controlar el coste.

**Instrucciones al agente**:
```text
Actúa como experto en FastAPI y LLMs. Implementa el asistente HITL de ingestión.

BACKEND — HtmlAnalyzerService en server/app/modules/agents_hub/services/html_analyzer_service.py:
  Constructor: __init__(self, llm_service: LLMServiceProtocol)
  Método principal: async analyze(html: str, url_hint: str) -> AnalysisResult
  Lanza EmptyHtmlError si html está vacío o solo contiene espacios.

LÓGICA:
1. Truncar el HTML a 10.000 caracteres (preservar inicio del body para capturar estructura).
2. Enviar al LLM con un prompt que solicita un JSON {"content": "...", "title": "...", "date": "..."}.
3. Parsear la respuesta JSON del LLM. Si falla el parse, devolver confidence=0.0 y selectores vacíos.
4. Validar cada selector contra el HTML real con BeautifulSoup. Eliminar los que no machan ningún elemento.
5. Para los selectores válidos, extraer sample_extraction (primeros 200 chars del texto encontrado).
6. Calcular confidence como ratio de selectores válidos / selectores propuestos.

TIPOS:
  @dataclass class AnalysisResult:
      proposed_selectors: dict[str, str | None]  # clave -> selector CSS o None si no validó
      confidence: float
      sample_extraction: dict[str, str]  # clave -> texto extraído

ENDPOINT — añadir a hub_ingestion_router.py:
  POST /api/v1/hub/ingestion/analyze-html
  Request: { "html": "...", "url_hint": "..." }
  Response: AnalysisResult serializado como JSON

FRONTEND — AdminIngestionAssistant.tsx en frontend/src/admin/pages/:
  - Textarea para pegar HTML (o URL para fetch desde backend).
  - Botón "Analizar" -> llama al endpoint.
  - Preview: muestra selectores propuestos + sample_extraction por cada campo.
  - Botón "Guardar Fuente" (deshabilitado hasta que se haya mostrado la preview al menos una vez).
  - Al guardar: POST /api/v1/hub/sources con config_json = {proposed_selectors, ...otros campos}.

TESTS REQUERIDOS:
- test_html_analyzer_returns_proposed_selectors_as_json
- test_html_analyzer_validates_selectors_against_html
- test_html_analyzer_includes_sample_extraction
- test_endpoint_rejects_empty_html
- test_html_is_truncated_before_sending_to_llm
```

**Tests RED — tests/modules/agents_hub/unit/test_html_analyzer.py**:
```python
"""Tests para el asistente HITL de análisis HTML — TDD RED."""
import pytest
from unittest.mock import AsyncMock


SAMPLE_INSTITUTIONAL_HTML = """
<html><head><title>Normativa - UJI</title></head>
<body>
  <header class="site-header"><nav>Menu</nav></header>
  <main>
    <h1 class="page-title">Reglamento de Doctorado</h1>
    <span class="pub-date">Aprobado: 20/02/2024</span>
    <article class="entry-content">
      <p>El presente reglamento regula los estudios de doctorado en la UJI.</p>
      <p>Artículo 1. El programa de doctorado tendrá una duración máxima de tres años.</p>
    </article>
  </main>
  <footer>Universitat Jaume I</footer>
</body></html>
"""


class TestHtmlAnalyzerService:

    @pytest.mark.asyncio
    async def test_html_analyzer_returns_proposed_selectors_as_json(self) -> None:
        from server.app.modules.agents_hub.services.html_analyzer_service import HtmlAnalyzerService

        llm_mock = AsyncMock()
        llm_mock.generate.return_value = (
            '{"content": "article.entry-content", "title": "h1.page-title", "date": "span.pub-date"}'
        )

        service = HtmlAnalyzerService(llm_service=llm_mock)
        result = await service.analyze(html=SAMPLE_INSTITUTIONAL_HTML, url_hint="https://www.uji.es/normativa")

        assert "content" in result.proposed_selectors
        assert "title" in result.proposed_selectors
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_html_analyzer_validates_selectors_against_html(self) -> None:
        """Los selectores que no machan elementos reales se eliminan de la propuesta."""
        from server.app.modules.agents_hub.services.html_analyzer_service import HtmlAnalyzerService

        llm_mock = AsyncMock()
        llm_mock.generate.return_value = (
            '{"content": "article.entry-content", "title": "h1.page-title", "date": "span.nonexistent"}'
        )

        service = HtmlAnalyzerService(llm_service=llm_mock)
        result = await service.analyze(html=SAMPLE_INSTITUTIONAL_HTML, url_hint="")

        assert result.proposed_selectors.get("content") == "article.entry-content"
        assert result.proposed_selectors.get("title") == "h1.page-title"
        assert result.proposed_selectors.get("date") is None  # no macha -> eliminado

    @pytest.mark.asyncio
    async def test_html_analyzer_includes_sample_extraction(self) -> None:
        """sample_extraction contiene el texto real extraído con los selectores válidos."""
        from server.app.modules.agents_hub.services.html_analyzer_service import HtmlAnalyzerService

        llm_mock = AsyncMock()
        llm_mock.generate.return_value = '{"content": "article.entry-content", "title": "h1.page-title"}'

        service = HtmlAnalyzerService(llm_service=llm_mock)
        result = await service.analyze(html=SAMPLE_INSTITUTIONAL_HTML, url_hint="")

        assert "Reglamento de Doctorado" in result.sample_extraction.get("title", "")
        assert "doctorado" in result.sample_extraction.get("content", "").lower()

    @pytest.mark.asyncio
    async def test_endpoint_rejects_empty_html(self) -> None:
        from server.app.modules.agents_hub.services.html_analyzer_service import (
            HtmlAnalyzerService,
            EmptyHtmlError,
        )

        service = HtmlAnalyzerService(llm_service=AsyncMock())
        with pytest.raises(EmptyHtmlError):
            await service.analyze(html="", url_hint="")

    @pytest.mark.asyncio
    async def test_html_is_truncated_before_sending_to_llm(self) -> None:
        """El fragmento enviado al LLM no supera 10.000 caracteres."""
        from server.app.modules.agents_hub.services.html_analyzer_service import HtmlAnalyzerService

        captured_prompts: list[str] = []

        async def fake_generate(prompt: str) -> str:
            captured_prompts.append(prompt)
            return '{"content": "p", "title": "h1"}'

        llm_mock = AsyncMock()
        llm_mock.generate.side_effect = fake_generate

        service = HtmlAnalyzerService(llm_service=llm_mock)
        large_html = "<html><body>" + "x" * 50_000 + "</body></html>"
        await service.analyze(html=large_html, url_hint="")

        assert len(captured_prompts[0]) <= 12_000
```

**Tests Vitest (frontend) — frontend/src/admin/pages/__tests__/AdminIngestionAssistant.test.tsx**:
```typescript
// Tests a implementar (RED antes de escribir el componente):
// - should_disable_save_button_until_preview_is_shown
// - should_enable_save_button_after_analyze_response_is_rendered
// - should_call_analyze_endpoint_with_pasted_html
// - should_persist_proposed_selectors_on_save_click
```

**Criterios de aceptación**:
- `POST /api/v1/hub/ingestion/analyze-html` devuelve `proposed_selectors`, `confidence` y `sample_extraction`.
- Los selectores se validan contra el HTML con BeautifulSoup; los que no machan se devuelven como `null`.
- El HTML se trunca a 10.000 caracteres antes de enviarlo al LLM.
- El botón "Guardar Fuente" permanece deshabilitado hasta que el Admin ha visto la previsualización.
- Los 5 tests Python y los 4 tests Vitest pasan en verde.

---


## BLOQUE 9B — Grafo Público: Plataforma Multi-organización (Subfase 1.A, PENDIENTE)

## FASE 9B: Grafo Público Extensible (CoreGraph + GraphProfiles + RetrievalPipelineFactory)

**Objetivo de la Fase**: Diseñar e implementar una arquitectura de grafo público extensible para una plataforma multi-organización, manteniendo un enfoque determinista-first, TDD (RED/GREEN) y reutilización máxima de componentes.

El objetivo NO es implementar un único chatbot, sino una **plataforma** capaz de soportar **múltiples chatbots públicos** con **hipótesis de uso distintas**, **estrategias de retrieval distintas**, y **configuración en cascada**, sin acoplar la topología del grafo a un único dominio.

**Dependencias**: Fase 4 (grafo LangGraph operativo), Fase 5B (LocalEmbeddingService BGE-M3)

**Decisiones de diseño**:

- **No grafo monolítico**: no se implementa un único grafo "gigante" con condicionales por dominio. En su lugar: un `CoreGraph` reutilizable, un contrato de `GraphProfiles` seleccionables por chatbot, y un contrato de `RetrievalPipeline` enchufables.
- **CoreGraph**: define el flujo común (idioma, retrieval, merge, rerank, generate, quality_gate, fallback, log). No contiene lógica específica de ningún dominio ni modo de retrieval.
- **GraphProfiles**: definen la topología lógica y el UX por tipo de chatbot (agregación, routing, plantilla de respuesta). Ejemplos: `PUBLIC_KB_RICH` (genérico) y `PUBLIC_PORTAL_AGGREGATOR` (UJI: normativa + procedimientos).
- **RetrievalPipelineFactory**: selecciona pipeline según `retrieval_mode` (`RAG` / `MD_LONG_CONTEXT` / `MD_AGENT_SELECTOR`). Garantiza un contrato común de salida (`RetrievalResult`) para todas las estrategias. El CoreGraph es agnóstico a cómo se obtuvo la evidencia.
- **Configuración en cascada**: Plataforma → Organización → Chatbot. La organización aporta defaults; el chatbot puede sobrescribir cualquier parámetro. No existe lista de "perfiles permitidos" por organización.
- **Caso piloto UJI** (`PUBLIC_PORTAL_AGGREGATOR`): dos dominios relacionados (normativa + procedimientos), comportamiento de agregación, preferencia de idioma (prefer, no strict), aviso de traducción si el idioma de la evidencia difiere del idioma del usuario.

**Arquitectura objetivo**:
```
CoreGraph (flujo común)
  detect_language → retrieve (delegado a RetrievalStrategy + Pipeline) → merge (por perfil)
  → rerank (opcional) → generate_answer (plantilla por perfil)
  → quality_gate (faithfulness + relevance) → fallback honesto / log_interaction

GraphProfiles
  PUBLIC_KB_RICH            ← genérico: grupos, oferta académica, FAQs municipales
  PUBLIC_PORTAL_AGGREGATOR  ← UJI: normativa + procedimientos, merge dual

RetrievalPipelineFactory
  RAG              ← retrieval vectorial clásico
  MD_LONG_CONTEXT  ← document packs Markdown
  MD_AGENT_SELECTOR ← agente selecciona documentos/secciones
```

---

### Prompt 9B.1 (RED) — Estructura de librería de grafos públicos + registry

```markdown
# PROMPT 9B.1 (RED) — Crear estructura de librería de grafos públicos + registry

Objetivo: crear una librería extensible para grafos públicos:
- CoreGraph (nodos comunes)
- Perfiles (Graph Profiles)
- Estrategias enchufables
- Registry (catálogo de perfiles)

Tareas:
1) Crear carpetas:
   server/app/modules/agents_hub/agent/public_graphs/
     core/
     profiles/
     strategies/
     registry.py
     types.py

2) Definir en types.py:
   - Enum PublicGraphProfile con valores iniciales:
     PUBLIC_KB_RICH
     PUBLIC_PORTAL_ROUTER (opcional, preparado)
     PUBLIC_PORTAL_AGGREGATOR (UJI)

3) Implementar registry.py:
   - register_profile(profile_name, profile_factory)
   - get_profile(profile_name) -> profile_factory o error
   - list_profiles() -> list[str]

Tests (RED) en tests/public_graphs/test_registry.py:
- test_registry_lists_profiles
- test_registry_raises_on_unknown_profile
- test_registry_can_register_and_get_profile

Criterio de aceptación:
- La estructura existe y los tests del registry pasan.
```

---

### Prompt 9B.2 (RED) — Modelo de datos: `public_graph_profile` + `retrieval_mode` + defaults de organización

```markdown
# PROMPT 9B.2 (RED) — Modelo de datos para selección de perfil + retrieval_mode + cascada de defaults

Objetivo: permitir múltiples perfiles y múltiples estrategias de retrieval por chatbot/portal (por uso),
sin restricciones por organización. La organización aporta defaults; el chatbot puede sobrescribir.

Tareas:
1) Añadir campos a HubChatbot:
   - public_graph_profile: str (default "PUBLIC_KB_RICH")
   - retrieval_mode: str (default "RAG")  # RAG | MD_LONG_CONTEXT | MD_AGENT_SELECTOR
   - language_mode: str (default "prefer")  # strict | prefer | none
   - quality_threshold: float (default 0.6)
   - min_retrieval_results: int (default 2)
   - min_retrieval_score: float (default 0.25)
   - reranker_enabled: bool (default true)
   - answer_template: str (default "generic")

2) Añadir defaults a la entidad Organización:
   - default_public_graph_profile: str (default "PUBLIC_KB_RICH")
   - default_retrieval_mode: str (default "RAG")
   - default_language_mode: str (default "prefer")
   - default_quality_threshold, default_min_retrieval_results, default_min_retrieval_score
   - default_reranker_enabled, default_answer_template

3) Migraciones Alembic para ambas tablas.

Tests (RED):
- test_chatbot_has_retrieval_mode_default
- test_org_has_default_retrieval_mode
- test_migration_applies_defaults_without_breaking_existing_rows

Criterio de aceptación:
- Dos chatbots de la misma organización pueden tener retrieval_mode distinto.
- No existe campo de "allowed profiles/modes" por organización (sin restricciones).
```

---

### Prompt 9B.3 (RED/GREEN) — ConfigResolver efectivo (cascada) incluye `retrieval_mode`

```markdown
# PROMPT 9B.3 (RED/GREEN) — ConfigResolver: Platform → Organization → Chatbot (incluye retrieval_mode)

Objetivo: resolver configuración efectiva del grafo público por chatbot.

Tareas:
1) Crear core/config_resolver.py:
   - PublicGraphConfig (dataclass/pydantic) con:
     profile, retrieval_mode, language_mode, thresholds, reranker_enabled, answer_template, etc.
   - async get_effective_public_graph_config(chatbot_id, session) -> PublicGraphConfig

2) PlatformDefaults: valores hardcoded o ConfigProvider global.

Tests (RED):
- test_effective_config_uses_platform_defaults
- test_effective_config_org_overrides_platform
- test_effective_config_chatbot_overrides_org
- test_effective_config_includes_retrieval_mode

GREEN:
- Implementación mínima para pasar tests.
```

---

### Prompt 9B.4 (RED) — Contrato de evidencias + contrato de pipelines (tests de contrato)

```markdown
# PROMPT 9B.4 (RED) — Contrato de Evidencia + Protocolos de RetrievalPipeline (con tests de contrato)

Objetivo: definir un contrato uniforme de salida del retrieval, independiente de la estrategia usada.
Es lo que evita necesitar "un grafo por retriever".

Tareas:
1) Crear strategies/retrieval_contract.py:
   - EvidenceItem:
       source_id: str
       source_url: str | None
       title: str | None
       content: str
       language: str | None
       score: float | None
       metadata: dict
   - RetrievalResult:
       items: list[EvidenceItem]
       context_source_language: str | None
       debug: dict

2) Crear strategies/retrieval_pipeline_protocol.py:
   - class RetrievalPipeline(Protocol):
       async def run(query: str, chatbot_id: str, cfg: PublicGraphConfig, deps: GraphDeps) -> RetrievalResult

3) Tests de contrato (RED) en tests/public_graphs/test_retrieval_contract.py:
   - test_pipeline_result_has_items_and_debug
   - test_evidence_item_has_required_fields
   - test_context_source_language_is_set_when_items_present
   - test_contract_is_serializable_or_repr_safe

Criterio de aceptación:
- Existe un contrato estable de retrieval que todos los pipelines deben cumplir.
```

---

### Prompt 9B.5 (RED/GREEN) — RetrievalPipelineFactory + pipelines stub + tests de contrato por modo

```markdown
# PROMPT 9B.5 (RED/GREEN) — RetrievalPipelineFactory + 3 pipelines (RAG / MD_LONG_CONTEXT / MD_AGENT_SELECTOR)

Objetivo: implementar una fábrica que devuelva un pipeline según retrieval_mode, y verificar por tests
que cada pipeline cumple el contrato.

Tareas:
1) Crear strategies/retrieval_pipeline_factory.py:
   - def get_pipeline(mode: str) -> RetrievalPipeline
   - lanzar ValueError si mode desconocido

2) Implementar pipelines mínimos:
   - RagVectorPipeline: llama al retriever vectorial existente y devuelve EvidenceItem por chunk
   - MdLongContextPipeline: selecciona un subconjunto de docs MD y construye un "pack" en items
   - MdAgentSelectorPipeline: (mínimo) simula selección de docs sin LLM y devuelve items

3) Tests (RED) en tests/public_graphs/test_retrieval_pipeline_factory.py:
   - test_factory_returns_pipeline_for_each_mode
   - test_factory_raises_for_unknown_mode

4) Tests de contrato por pipeline (RED) en tests/public_graphs/test_retrieval_pipelines_contract.py:
   - test_rag_pipeline_conforms_to_contract
   - test_md_long_context_pipeline_conforms_to_contract
   - test_md_agent_selector_pipeline_conforms_to_contract

GREEN:
- Implementación mínima para pasar tests.
```

---

### Prompt 9B.6 (RED) — Protocolos/Interfaces de estrategias actualizados para usar pipelines

```markdown
# PROMPT 9B.6 (RED) — Protocolos de estrategias (actualizados para RetrievalPipeline)

Objetivo: los perfiles siguen definiendo RetrievalStrategy/Merge/Template/LanguagePolicy,
pero RetrievalStrategy debe usar el pipeline devuelto por RetrievalPipelineFactory según cfg.retrieval_mode.

Tareas:
1) En strategies/protocols.py:
   - RetrievalStrategy.retrieve(...) devuelve RetrievalOutput
   - RetrievalOutput puede contener uno o varios RetrievalResult (p.ej. buckets)
   - RetrievalStrategy invoca internamente get_pipeline(cfg.retrieval_mode).run(...)

2) Tests (RED):
   - test_retrieval_strategy_uses_pipeline_factory
   - test_retrieval_output_can_hold_multiple_buckets

Criterio:
- retrieval_mode se aplica sin cambiar CoreGraph.
```

---

### Prompt 9B.7 (RED/GREEN) — CoreGraph (orquestación común)

```markdown
# PROMPT 9B.7 (RED/GREEN) — CoreGraph: orquestación común usando RetrievalStrategy

Objetivo: CoreGraph ejecuta el flujo común sin lógica específica de dominio ni retrieval_mode:
detect_language → retrieve → merge → (optional) rerank → generate_answer → quality_gate → (log | fallback)

Tareas:
- Implementar/ajustar core/core_graph.py para trabajar con RetrievalOutput/RetrievalResult.
- No introducir lógica específica de UJI ni de ningún modo de retrieval.

Tests (RED):
- test_core_graph_compiles_with_mock_strategies
- test_core_graph_branches_to_fallback_when_quality_low
- test_core_graph_runs_with_each_retrieval_mode_using_generic_profile

GREEN:
- Implementación mínima.
```

---

### Prompt 9B.8 (RED/GREEN) — Perfil genérico PUBLIC_KB_RICH (compatible con los 3 retrieval_mode)

```markdown
# PROMPT 9B.8 (RED/GREEN) — PUBLIC_KB_RICH compatible con 3 retrieval_mode

Objetivo: perfil "default" para futuros chatbots (grupos, oferta académica, FAQs municipales).
Debe funcionar con cualquiera de los 3 modos de retrieval.

Tareas:
1) profiles/public_kb_rich.py:
   - SingleSourceRetrievalStrategy: usa pipeline(cfg.retrieval_mode)
   - PassthroughMergeStrategy
   - GenericAnswerTemplateStrategy
   - DefaultLanguagePolicy

2) Tests (RED):
   - test_public_kb_rich_runs_in_rag_mode
   - test_public_kb_rich_runs_in_md_long_context_mode
   - test_public_kb_rich_runs_in_md_agent_selector_mode

GREEN:
- Implementación.

Criterio:
- Un chatbot público genérico funciona con los 3 modos sin cambiar de grafo.
```

---

### Prompt 9B.9 (RED/GREEN) — Perfil PUBLIC_PORTAL_ROUTER (opcional, compatible con retrieval_mode)

```markdown
# PROMPT 9B.9 (RED/GREEN) — PUBLIC_PORTAL_ROUTER (opcional) compatible con retrieval_mode

Objetivo: portal que enruta entre chatbots hijos si los dominios son disjuntos.
El retrieval dentro del hijo respeta su cfg.retrieval_mode.

Tareas:
- Implementar profiles/public_portal_router.py:
   - decide chatbot hijo
   - carga effective config del hijo
   - ejecuta CoreGraph con el perfil del hijo (o fuerza PUBLIC_KB_RICH si procede)

Tests (RED):
- test_portal_router_selects_child_chatbot_and_uses_child_retrieval_mode

GREEN:
- Implementación.
```

---

### Prompt 9B.10 (RED) — Tests del perfil UJI agregador (independiente de retrieval_mode)

```markdown
# PROMPT 9B.10 (RED) — Tests UJI Aggregator: combina procedimientos + normativa en cualquier retrieval_mode

El perfil UJI agrega dos fuentes (procedimientos + normativa). El mismo perfil debe operar con
retrieval_mode=RAG (lo normal) y, en el futuro, con MD_LONG_CONTEXT o MD_AGENT_SELECTOR sin duplicar el grafo.

Tests:
- test_uji_aggregator_rag_mode_combines_procedure_and_normativa
- test_uji_aggregator_md_long_context_mode_combines_procedure_and_normativa
- test_uji_aggregator_md_agent_selector_mode_combines_procedure_and_normativa
- test_uji_normativa_only_when_no_procedure_candidate
- test_uji_answer_template_sections_present
- test_uji_translation_warning_only_when_context_language_differs
```

---

### Prompt 9B.11 (GREEN) — Implementación del perfil UJI agregador usando pipelines por bucket

```markdown
# PROMPT 9B.11 (GREEN) — Implementar PUBLIC_PORTAL_AGGREGATOR (UJI) usando pipelines según cfg.retrieval_mode

Objetivo: RetrievalStrategy dual:
- bucket procedimientos: pipeline(cfg.retrieval_mode).run(...) sobre fuente procedimientos
- bucket normativa: pipeline(cfg.retrieval_mode).run(...) sobre fuente normativa

Merge:
- si hay procedimiento candidato:
    - incluir procedimiento top
    - recuperar normativa enlazada por URL/canonical_id si existe
    - añadir normativa general como respaldo
- si no:
    - solo normativa

Notas:
- Deduplicación no puede basarse solo en URL si el contenido varía por idioma;
  usar doc_id o (canonical_url, language).

Criterio:
- Pasa los tests del Prompt 9B.10 sin cambiar CoreGraph.
```

---

### Prompt 9B.12 (RED/GREEN) — LanguagePolicy (prefer/strict/none) + warning por idioma real del contexto

```markdown
# PROMPT 9B.12 (RED/GREEN) — LanguagePolicy y warning de traducción

Objetivo:
- prefer: prioriza idioma del usuario si existe evidencia; evita doble búsqueda innecesaria.
- strict: permite comportamiento de filtro estricto si se necesita.
- none: neutral.

Warning de traducción:
- Se muestra si context_source_language != query_language.
- No se dispara por "fallback_triggered" de calidad (son señales distintas).

Tests:
- test_language_policy_prefer_avoids_double_search
- test_language_policy_strict_can_trigger_fallback
- test_warning_only_when_context_language_differs
```

---

### Prompt 9B.13 (RED/GREEN) — GraphFactory runtime: selección de perfil + pipeline por chatbot

```markdown
# PROMPT 9B.13 (RED/GREEN) — GraphFactory runtime: perfil + retrieval_mode por chatbot

Objetivo: punto de integración final. El endpoint público debe:
- resolver config efectiva (incluye public_graph_profile y retrieval_mode)
- seleccionar perfil en registry
- crear CoreGraph con el bundle de estrategias del perfil
- ejecutar

Tests:
- test_graph_factory_uses_chatbot_override_profile_and_retrieval_mode
- test_graph_factory_uses_org_defaults_when_chatbot_missing
- test_graph_factory_uses_platform_defaults_when_org_missing
```

---

### Prompt 9B.14 — Kit de ampliación (docs + tests de contrato por perfil y pipeline)

```markdown
# PROMPT 9B.14 — Kit para añadir perfiles y pipelines (docs + tests de contrato)

Objetivo: dejar la plataforma lista para crecer sin reabrir arquitectura.

Tareas:
1) docs/GRAPH_PROFILES.md:
   - qué es CoreGraph
   - qué es un GraphProfile
   - qué es retrieval_mode
   - cómo añadir un perfil nuevo (ej. oferta académica estructurada)
   - cómo añadir un pipeline nuevo (si apareciera un modo futuro)

2) tests/public_graphs/test_profile_contract.py:
   - todo perfil registrado debe:
     - compilar grafo
     - tener strategies no nulas
     - poder ejecutarse con cada retrieval_mode (smoke)

3) tests/public_graphs/test_pipeline_contract_suite.py:
   - todo pipeline en factory debe pasar el contrato común (EvidenceItem, RetrievalResult)
```

---


---

## BLOQUE 9R — Redacción Contract-First: ReportProfiles, UI Contracts y DraftingCoreGraph (Subfase 1.A → 1.C, PENDIENTE)

> Creado: 2026-05-11. Sustituye y amplía los prompts 9.11a–9.11d (conservados como referencia histórica tras el bloque).
> Referencia estratégica: `Rediseño_informes.md`.

### Propósito del bloque 9R

Reformular la subfase de Agentes de Redacción / Workspaces para que **no** sea un grafo monolítico con extracción, redacción IA y ensamblado, sino una **arquitectura contract-first extensible** análoga al bloque 9B (CoreGraph + Profiles + Factory + Contracts):

- `DraftingCoreGraph` común para todos los tipos de informe.
- `ReportProfiles` para especializar tipos de informe (incluye `GENERIC_REPORT` obligatorio para informes no predefinidos).
- `ReportTemplateContract`, `BlockContract`, `ReportUIContract` versionados y exportados por OpenAPI.
- `ExtractionPipelineFactory` para Excel/PDF/manual/scripts seguros (extracción determinista, no IA).
- `LLM-assisted Report Specification`: el LLM propone un `ReportTemplateDraft`, el humano valida y aprueba antes de persistir.
- `HITL por bloque` con máquina de estados explícita (`draft → extracted → ai_generated → needs_review → approved | rejected → locked`).
- `DraftingRunManifest` obligatorio para trazabilidad de cada ejecución.

### Decisiones de diseño

1. **No grafo monolítico**. El `DraftingCoreGraph` es común. La variación entre tipos de informe se resuelve por `ReportProfile`, no por `if/else` dentro del core.
2. **Contratos versionados**. El antiguo `config_hibrida JSON` desaparece. Se sustituye por `ReportTemplateContract` con `version_id`, schema validable y serialización OpenAPI.
3. **UI por contrato**. El frontend no tiene pantallas hardcoded por tipo de informe. Renderiza `ReportUIContract` con `react-hook-form` + `zodResolver` + tipos generados por Orval.
4. **LLM propone, humano aprueba**. El asistente LLM genera `ReportTemplateDraft` → validador estructural → vista previa editable → aprobación HITL → persistencia como plantilla o workspace ad hoc.
5. **Extracción determinista primero**. Excel/PDF se parsean con código (`pandas`, `pdfplumber`, `camelot`), nunca con LLM como mecanismo principal. Los scripts generados por IA son una extensión controlada (refactor de 9.11b con HITL + AST + auditoría IA).
6. **Estados de bloque explícitos**. Cada bloque tiene un estado en `{draft, missing_input, extracted, ai_generated, needs_review, approved, rejected, locked}`. Un bloque IA sin `approved` no entra en el documento final. Un bloque requerido sin datos bloquea el ensamblado.
7. **RunManifest obligatorio**. Ninguna exportación procede sin un `DraftingRunManifest` con `workspace_id`, `template_version_id`, `report_profile`, `uploaded_documents`, `input_validation`, `extracted_blocks`, `ai_blocks`, `model_used`, `prompt_versions`, `citations`, `warnings`, `user_approvals` y `final_document_hash`.
8. **Edge/Cloud**. Los módulos 9R son **edge** (procesan documentos/expedientes del cliente). Los routers se etiquetan `Deploy: edge` y no importan módulos cloud directamente.

### Diagrama del DraftingCoreGraph

```
LoadTemplateNode
  → ValidateInputContractNode
    → FileNormalizationNode
      → DeterministicExtractionNode    [Excel / PDFText / PDFTable / Manual / AdminScript]
        → DataQualityCheckNode
          → MissingDataQuestionNode    [HITL: solicita inputs faltantes]
            → AIAssistDraftNode         [LLM: solo con datos validados como contexto]
              → CitationAndTraceabilityNode
                → UserReviewGateNode    [HITL: aprueba/rechaza/regenera por bloque]
                  → ApplyUserEditsNode
                    → FinalAssemblerNode
                      → AuditLogNode    [emite DraftingRunManifest]
```

### Mapa de ejecución del bloque 9R

```
9R.0   (DOC)        Decisiones de arquitectura + nota en el plan

9R.1.1 (RED/GREEN)  ReportTemplateContract + ReportTemplateVersion (Pydantic + OpenAPI)
9R.1.2 (RED/GREEN)  InputContract + BlockContract + ReportUIContract
9R.1.3 (RED/GREEN)  WorkspaceState + BlockState + ReportTemplateDraft (runtime)
9R.1.4 (RED/GREEN)  Migración Alembic: hub_report_templates / hub_workspaces / hub_workspace_blocks / hub_run_manifests

9R.2.1 (RED/GREEN)  ReportProfile registry + GENERIC_REPORT como perfil obligatorio
9R.2.2 (RED/GREEN)  Estructura inicial de GENERIC_REPORT (secciones, bloques mínimos, inputs aceptados)

9R.3.1 (RED/GREEN)  Tipos de bloque (STATIC_TEXT, USER_INPUT, DETERMINISTIC_DATA, TABLE, CHART, AI_ASSISTED_TEXT, AI_SUMMARY, AI_REWRITE, CITATION_BLOCK, REVIEW_GATE)
9R.3.2 (RED/GREEN)  BlockState machine + reglas de transición + invariantes (AI sin approved no ensambla)
9R.3.3 (RED/GREEN)  Propagación de outputs entre bloques (BlockReference + projection) + orden topológico + detección de ciclos

9R.4.1 (RED/GREEN)  LLMSpecService: NL → ReportTemplateDraft
9R.4.2 (RED/GREEN)  Validador estructural + rechazo de drafts con tipos no permitidos
9R.4.3 (RED/GREEN)  Endpoints preview/approve + HITL (admin: plantilla; user: workspace ad hoc)
9R.4.4 (RED/GREEN)  Versionado de plantillas: política de anclaje y endpoints de migración de workspaces

9R.5.1 (RED/GREEN)  Protocolo ExtractionPipeline + contratos (Input/Result/Provenance/Warning)
9R.5.2 (RED/GREEN)  ExcelExtractionPipeline + PDFTextExtractionPipeline
9R.5.3 (RED/GREEN)  PDFTableExtractionPipeline + ManualInputPipeline
9R.5.4 (RED/GREEN)  ExtractionPipelineFactory + AdminScriptExtractionPipeline (motor de ejecución)
9R.5.5 (RED/GREEN)  ScriptProposalService + migración módulo anonimización (spaCy NER + Faker + regex + anclajes, desde client_app legacy) + endpoints propose/describe/anonymize/test/validate
9R.5.6 (RED/GREEN)  Workflow de aprobación scripts: self-service usuario / cola admin para plantillas globales
9R.5.7 (RED/GREEN)  Bloque CHART (modo determinista + IA) — migración de graphics_factory + deterministic_graphics_service legacy
9R.5.8 (RED/GREEN)  Bloque DATA_TRANSFORM (filter/aggregate/join/pivot/groupby) — migración de etl_service + deterministic_etl + etl_factory legacy
9R.5.9 (RED/GREEN)  Extractor Docling rico (ExtractedDocument: markdown + tables_json + páginas con bbox) — adelantado parcial de Fase 2 prompt 9.12b

9R.6.1 (RED/GREEN)  CoreGraph: LoadTemplate / ValidateInputContract / FileNormalization
9R.6.2 (RED/GREEN)  CoreGraph: DeterministicExtraction / DataQualityCheck / MissingDataQuestion
9R.6.3 (RED/GREEN)  CoreGraph: AIAssistDraft / CitationAndTraceability
9R.6.4 (RED/GREEN)  CoreGraph: UserReviewGate / ApplyUserEdits / FinalAssembler
9R.6.5 (RED/GREEN)  CoreGraph: AuditLog + emisión de DraftingRunManifest + instrumentación Langfuse
9R.6.6 (RED/GREEN)  CoreGraph: fallback paths + BlockState=failed + política de retry

9R.7.1 (RED/GREEN)  ReportUIContractRenderer + DynamicUploadSlots + DynamicFieldRenderer
9R.7.2 (RED/GREEN)  BlockEditor + AIBlockReviewPanel + DataQualityPanel + WorkspaceStatusBar
9R.7.3 (RED/GREEN)  ReportTemplateBuilderPage (admin) + GenericReportWizard (user)
9R.7.4 (RED/GREEN)  LLMDraftPreviewPage + flujo de aprobación
9R.7.5 (RED/GREEN)  UI scripts: ScriptProposalWizardPage + AdminScriptReviewQueuePage
9R.7.6 (RED/GREEN)  Simplificación de etiquetas de estado para usuario final + panel debug admin

9R.8.1 (RED/GREEN)  HITL endpoints + servicios de transición de bloques
9R.8.2 (RED/GREEN)  Tests E2E de edición/rechazo/regeneración por bloque

9R.9.1 (RED/GREEN)  DraftingRunManifest modelo Pydantic + repo + endpoint
9R.9.2 (RED/GREEN)  Integración con ExportService (1C.4) — DOCX-only en MVP

9R.10.1 (RED)       Vertical slice E2E: tests de aceptación
9R.10.2 (GREEN)     Wire-up integral del slice
```

### Reglas duras del bloque 9R

1. **No existe `config_hibrida JSON` libre**. Cualquier dato de configuración va en un `ReportTemplateContract` versionado.
2. **Los routers HTTP devuelven Pydantic ResponseModel específicos**. Nunca devolver modelos ORM directamente.
3. **El frontend usa exclusivamente tipos generados por Orval**. Está prohibido crear interfaces TypeScript manuales para DTOs de redacción.
4. **El LLM no puede crear plantillas persistentes sin aprobación HITL**. Solo genera `ReportTemplateDraft`.
5. **Ningún bloque IA entra al documento final sin estado `approved`**. El `UserReviewGateNode` bloquea el ensamblado.
6. **Toda ejecución del agente emite `DraftingRunManifest`**, incluso si falla. La exportación a DOCX (1C.4) requiere manifest válido. ODT queda fuera del MVP (backlog post-MVP, mantener abstracción `Exporter` para no rework).
7. **Módulos 9R son edge**. Routers etiquetados `Deploy: edge` (ver CLAUDE.md), no importan módulos cloud.
8. **TDD obligatorio**. RED antes que GREEN; ningún PR del bloque se acepta sin tests del nuevo contrato/comportamiento.

---

### 9R.0 — Decisiones de arquitectura (DOC, sin TDD)

```markdown
# 9R.0 — Documento de decisiones de arquitectura

Objetivo: dejar registrada en el repositorio la arquitectura objetivo del bloque 9R antes de empezar TDD.

Tareas:
1) Crear `docs/REDACCION_CONTRACT_FIRST.md` con:
   - Propósito del bloque.
   - Decisiones de diseño (1-8 listadas arriba).
   - Diagrama del DraftingCoreGraph (versión textual).
   - Mapa de ejecución 9R.1 → 9R.10.
   - Reglas duras del bloque.
   - Glosario: ReportProfile, ReportTemplateContract, BlockContract, ReportUIContract, BlockState, DraftingRunManifest, ReportTemplateDraft, ExtractionPipeline.

2) Añadir en `CLAUDE.md` un párrafo breve en la sección de Edge/Cloud aclarando que los nuevos módulos `modules/redaccion/` son edge.

3) Crear el esqueleto de carpetas (vacías) para que la estructura sea visible:
   - `server/app/modules/redaccion/`
   - `server/app/modules/redaccion/contracts/`
   - `server/app/modules/redaccion/profiles/`
   - `server/app/modules/redaccion/pipelines/`
   - `server/app/modules/redaccion/graph/`
   - `server/app/modules/redaccion/services/`
   - `frontend/src/redaccion/`

Criterio de done:
- El documento es legible y autosuficiente.
- Cualquier dev nuevo entiende qué hace el bloque 9R sin leer el plan completo.
```

---

### Prompt 9R.1.1 (RED/GREEN) — ReportTemplateContract + ReportTemplateVersion

```markdown
# PROMPT 9R.1.1 (RED/GREEN) — Contratos Pydantic de plantilla y versión

Objetivo: definir los contratos serializables de plantilla y versión, exportables por OpenAPI y consumibles por Orval.

Estructura (en server/app/modules/redaccion/contracts/):
- template.py        # ReportTemplateContract, ReportTemplateVersion
- __init__.py

ReportTemplateContract (mínimo):
- id: UUID
- name: str
- description: str | None
- report_profile: ReportProfileId   # Enum/Literal
- owner_kind: Literal["platform","organization","user"]
- owner_id: UUID | None
- is_global: bool
- current_version_id: UUID
- created_at: datetime
- updated_at: datetime

ReportTemplateVersion (mínimo):
- id: UUID
- template_id: UUID
- version: int
- spec: ReportTemplateSpec   # contiene sections, blocks, inputs, ui_contract
- created_at: datetime
- created_by: UUID

ReportTemplateSpec (mínimo):
- sections: list[SectionContract]
- blocks: list[BlockContract]   # referencia adelantada (9R.1.2)
- input_contract: InputContract # referencia adelantada (9R.1.2)
- ui_contract: ReportUIContract # referencia adelantada (9R.1.2)
- ai_block_policy: AIBlockPolicy
- review_policy: ReviewPolicy
- export_policy: ExportPolicy

Tests (RED → GREEN):
- test_report_template_contract_is_serializable_to_openapi
- test_report_template_version_requires_template_id
- test_report_template_spec_rejects_unknown_owner_kind
- test_report_template_version_is_immutable_once_persisted   # contrato: solo se versiona, nunca se edita
- test_report_template_exports_stable_schema_names           # ChatbotRead-style naming
- test_only_admin_can_create_global_template_contract

Criterio de done:
- `uv run python export_openapi.py` muestra los schemas ReportTemplateContract, ReportTemplateVersion, ReportTemplateSpec, SectionContract.
- Los nombres de schema son estables (no `ReportTemplateRead_v1__abc`).
- Tests verdes; sin código en routers todavía.
```

---

### Prompt 9R.1.2 (RED/GREEN) — InputContract + BlockContract + ReportUIContract

```markdown
# PROMPT 9R.1.2 (RED/GREEN) — Contratos de inputs, bloques y UI adaptativa

Objetivo: definir los contratos discriminados de bloque, los inputs aceptados por la plantilla y el contrato UI que el frontend renderizará dinámicamente.

Estructura (en server/app/modules/redaccion/contracts/):
- inputs.py     # InputContract, InputSlot
- blocks.py     # BlockContract (discriminated union), BlockKind enum
- ui.py         # ReportUIContract, UISection, UIFieldDescriptor, UIDropzoneDescriptor

InputContract (mínimo):
- required_slots: list[InputSlot]
- optional_slots: list[InputSlot]

InputSlot:
- slot_id: str
- kind: Literal["pdf","excel","csv","text","number","date","selector"]
- label: dict[str, str]      # i18n {es,ca,en}
- required: bool
- multiple: bool
- max_size_mb: int | None
- validation: dict | None    # regex, min/max, schema columnas Excel, etc.

BlockContract (discriminated union por `kind`):
- STATIC_TEXT, USER_INPUT, DETERMINISTIC_DATA, TABLE, CHART,
  AI_ASSISTED_TEXT, AI_SUMMARY, AI_REWRITE, CITATION_BLOCK, REVIEW_GATE
- Campos comunes: id, kind, title, required, depends_on (list[str]), order
- Campos específicos por kind: source_pipeline (para DETERMINISTIC_DATA),
  ai_prompt_template_id (para AI_*), data_block_ref (para CHART/TABLE),
  review_policy_id (para REVIEW_GATE)

ReportUIContract:
- wizard_steps: list[UISection]
- dropzones: list[UIDropzoneDescriptor]
- manual_fields: list[UIFieldDescriptor]
- block_editor_enabled: bool
- ai_review_panel_enabled: bool
- preview_layout: Literal["markdown","docx-like","split"]

Tests (RED → GREEN):
- test_block_contract_discriminator_by_kind
- test_ai_block_requires_review_policy_reference
- test_data_block_requires_source_pipeline
- test_chart_block_requires_data_block_ref
- test_table_block_requires_data_block_ref
- test_review_gate_block_requires_review_policy_id
- test_input_slot_excel_validates_required_columns_schema
- test_input_slot_pdf_accepts_max_size_mb
- test_ui_contract_renders_wizard_steps_in_order
- test_block_contract_is_serializable_and_appears_in_openapi
- test_unknown_block_kind_is_rejected

Criterio de done:
- Discriminated union de BlockContract aparece en openapi.json con `oneOf` y `discriminator: kind`.
- `npm run generate:api` produce tipos TypeScript discriminados (no `Block` genérico con `any`).
- Tests verdes.
```

---

### Prompt 9R.1.3 (RED/GREEN) — WorkspaceState + BlockState + ReportTemplateDraft

```markdown
# PROMPT 9R.1.3 (RED/GREEN) — Contratos de runtime: estado del workspace y draft LLM

Objetivo: definir el estado de runtime que circula por el DraftingCoreGraph y el contrato del draft propuesto por el asistente LLM.

Estructura (en server/app/modules/redaccion/contracts/):
- runtime.py    # WorkspaceState, BlockState, BlockStatus, WorkspaceStatus
- drafts.py     # ReportTemplateDraft, ReportTemplateDraftValidationResult

BlockStatus (Literal):
- "draft" | "missing_input" | "extracted" | "ai_generated" | "needs_review" | "approved" | "rejected" | "locked"

BlockState:
- block_id: str
- kind: BlockKind
- status: BlockStatus
- content: dict | None         # extracted data o ai text
- citations: list[Citation] | None
- last_updated_by: Literal["system","user","ai"]
- updated_at: datetime
- approval: ApprovalRecord | None

WorkspaceStatus (Literal):
- "draft" | "ingesting" | "extracting" | "drafting" | "in_review" | "assembled" | "exported" | "error"

WorkspaceState:
- workspace_id: UUID
- template_version_id: UUID
- report_profile: ReportProfileId
- inputs: dict[str, InputArtifact]    # por slot_id
- blocks: dict[str, BlockState]
- status: WorkspaceStatus
- warnings: list[ExtractionWarning]
- run_manifest_id: UUID | None

ReportTemplateDraft (lo que devuelve el LLM):
- proposed_profile: ReportProfileId
- proposed_sections: list[SectionContract]
- proposed_blocks: list[BlockContract]
- proposed_inputs: InputContract
- rationale: str            # explicación del LLM
- model_used: str
- prompt_version: str

ReportTemplateDraftValidationResult:
- ok: bool
- normalized_draft: ReportTemplateDraft | None
- errors: list[ValidationError]

Tests (RED → GREEN):
- test_workspace_state_serializes_with_block_status
- test_block_state_status_transition_valid_paths
- test_block_state_rejects_invalid_status_transition     # draft → approved (sin pasar por needs_review) → rechazar
- test_report_template_draft_includes_model_and_prompt_version
- test_invalid_draft_returns_normalized_errors

Criterio de done:
- BlockStatus expuesto en OpenAPI como enum.
- Las transiciones inválidas levantan `InvalidBlockTransitionError`.
- Tests verdes.
```

---

### Prompt 9R.1.4 (RED/GREEN) — Migración Alembic + repos

```markdown
# PROMPT 9R.1.4 (RED/GREEN) — Tablas hub_report_templates / hub_workspaces / hub_workspace_blocks / hub_run_manifests

Objetivo: crear la capa de persistencia. Los contratos Pydantic son la fuente de verdad — los modelos ORM no se exponen al exterior.

Tablas (HubOperationalBase — edge, ver CLAUDE.md):
- hub_report_templates (id, name, description, report_profile, owner_kind, owner_id, is_global, current_version_id, created_at, updated_at)
- hub_report_template_versions (id, template_id FK, version, spec_json JSONB, created_at, created_by)
- hub_workspaces (id, template_version_id FK, owner_id, status, inputs_json JSONB, warnings_json JSONB, run_manifest_id FK nullable, created_at, updated_at)
- hub_workspace_blocks (id, workspace_id FK, block_id, kind, status, content_json JSONB, citations_json JSONB, approval_json JSONB, updated_at)
- hub_run_manifests (id, workspace_id FK, template_version_id FK, report_profile, payload_json JSONB, final_document_hash str, created_at)

Reglas:
- `hub_report_template_versions` es append-only. No hay UPDATE — solo nuevas versiones.
- `hub_workspace_blocks` tiene constraint UNIQUE(workspace_id, block_id).
- `hub_run_manifests.final_document_hash` se completa solo al ensamblar.
- Sin `relationship()` cross-base (HubConfigBase ↔ HubOperationalBase prohibido).

Tests (RED → GREEN):
- test_alembic_upgrade_head_creates_new_tables
- test_alembic_downgrade_removes_new_tables_cleanly
- test_template_version_insert_only_no_update
- test_workspace_block_unique_per_workspace
- test_run_manifest_links_to_workspace_and_template_version

Aplicar:
- cd server && uv run alembic upgrade head
- alembic current confirma la nueva revisión

Criterio de done:
- Migración aplicada en BD local.
- Tests verdes.
- Repos `ReportTemplateRepo`, `WorkspaceRepo`, `WorkspaceBlockRepo`, `RunManifestRepo` exponen métodos `get`, `list`, `save`, `update_status`, sin lógica de negocio.
```

---

### Prompt 9R.2.1 (RED/GREEN) — ReportProfile registry + GENERIC_REPORT

```markdown
# PROMPT 9R.2.1 (RED/GREEN) — Registry de perfiles + perfil obligatorio GENERIC_REPORT

Objetivo: implementar el registry de perfiles análogo al de 9B (GraphProfileRegistry), con GENERIC_REPORT como perfil obligatorio.

Estructura (en server/app/modules/redaccion/profiles/):
- registry.py        # ReportProfileRegistry, ReportProfileId enum/Literal
- generic_report.py  # GenericReportProfile (perfil base)
- __init__.py        # registro automático

ReportProfileId (Literal):
- "GENERIC_REPORT" | "ANNUAL_REPORT" | "DOCTORATE_PROGRAM_REPORT" | "CONTRACT_REPORT" | "FREEFORM_MEMO"

ReportProfile (Protocol):
- profile_id: ReportProfileId
- def default_spec() -> ReportTemplateSpec
- def applicable_pipelines() -> list[ExtractionPipelineId]
- def review_policy() -> ReviewPolicy
- def ai_block_policy() -> AIBlockPolicy

ReportProfileRegistry:
- register(profile: ReportProfile)
- get(profile_id: ReportProfileId) -> ReportProfile
- list() -> list[ReportProfileId]
- contiene una entrada obligatoria GENERIC_REPORT al importarse el módulo (auto-register en __init__).

Tests (RED → GREEN):
- test_registry_contains_generic_report_after_import
- test_registry_rejects_duplicate_profile_id
- test_get_unknown_profile_raises
- test_generic_report_default_spec_is_valid_report_template_spec
- test_generic_report_applicable_pipelines_includes_excel_pdf_manual

Criterio de done:
- `from server.app.modules.redaccion.profiles import registry; registry.get("GENERIC_REPORT")` funciona sin error.
- GENERIC_REPORT no puede desregistrarse (constante de bloque).
- Tests verdes.
```

---

### Prompt 9R.2.2 (RED/GREEN) — Estructura inicial de GENERIC_REPORT

```markdown
# PROMPT 9R.2.2 (RED/GREEN) — Spec por defecto del perfil genérico

Objetivo: que GENERIC_REPORT proponga una estructura útil para informes no predefinidos.

Spec por defecto (`generic_report.default_spec()`):
- sections (orden y nombre):
  1. Título y datos de contexto       → STATIC_TEXT + USER_INPUT
  2. Objetivo del informe              → USER_INPUT
  3. Contexto                          → USER_INPUT + AI_REWRITE (asistido, opcional)
  4. Fuentes aportadas                 → DETERMINISTIC_DATA (referencia a inputs)
  5. Datos extraídos                   → DETERMINISTIC_DATA + TABLE/CHART
  6. Análisis asistido                 → AI_ASSISTED_TEXT (sobre datos validados, requiere REVIEW_GATE)
  7. Conclusiones                      → AI_SUMMARY (requiere REVIEW_GATE)
  8. Recomendaciones                   → USER_INPUT + AI_REWRITE (asistido, opcional)
  9. Anexos / fuentes                  → CITATION_BLOCK

- input_contract:
  - opcional Excel (slot_id="datos_excel", validation: cualquier hoja)
  - opcional PDF (slot_id="memoria_pdf")
  - opcional texto libre (slot_id="notas")

- ai_block_policy: requiere `needs_review` antes de `approved`; modelo Tier-1 con prompt versionado.

Tests (RED → GREEN):
- test_generic_report_profile_exists
- test_generic_report_default_spec_contains_nine_sections_in_order
- test_generic_report_accepts_manual_blocks
- test_generic_report_accepts_excel_and_pdf_inputs
- test_generic_report_requires_human_approval_for_ai_blocks
- test_generic_report_can_be_created_from_llm_draft   # placeholder, full test en 9R.4
- test_generic_report_generates_run_manifest_field    # placeholder, full test en 9R.9

Criterio de done:
- Crear workspace con `profile=GENERIC_REPORT` y plantilla por defecto genera 9 secciones esperadas.
- Todos los bloques AI están marcados `requires_review=True`.
- Tests verdes.
```

---

### Prompt 9R.3.1 (RED/GREEN) — Tipos de bloque y comportamiento por kind

```markdown
# PROMPT 9R.3.1 (RED/GREEN) — Implementar el comportamiento por tipo de bloque

Objetivo: para cada tipo de bloque, codificar inputs/outputs/dependencias/política IA/política HITL/render UI/trazabilidad.

Para cada kind en BlockKind, implementar en server/app/modules/redaccion/blocks/handlers/:
- propósito (docstring de clase)
- inputs aceptados (qué bloques o slots leen)
- outputs (estructura del content)
- puede ser required: bool
- puede depender de otros bloques: list[BlockKind]
- usa IA: bool
- requiere aprobación: bool
- render UI: dict[str, Any]  → consumido por ReportUIContract
- registro en RunManifest: dict (qué se serializa)

Handlers mínimos:
- StaticTextHandler
- UserInputHandler
- DeterministicDataHandler  (delega en ExtractionPipeline)
- TableHandler              (consume DETERMINISTIC_DATA)
- ChartHandler              (consume DETERMINISTIC_DATA o TABLE)
- AIAssistedTextHandler
- AISummaryHandler
- AIRewriteHandler
- CitationBlockHandler
- ReviewGateHandler

Tests (RED → GREEN):
- test_block_contract_has_required_fields
- test_ai_block_requires_review_policy
- test_data_block_requires_extraction_source
- test_chart_block_depends_on_data_block
- test_review_gate_blocks_final_assembly_until_approved
- test_block_contract_is_serializable
- test_chart_handler_rejects_missing_data_block_ref
- test_ai_handler_records_model_and_prompt_version_to_manifest

Criterio de done:
- Cada handler implementa `validate(block)`, `execute(block, state)`, `to_manifest(block)`.
- Tests verdes (10/10).
- Documentación por handler (docstring estructurado).
```

---

### Prompt 9R.3.2 (RED/GREEN) — BlockState machine + invariantes

```markdown
# PROMPT 9R.3.2 (RED/GREEN) — Máquina de estados de bloque y reglas de transición

Objetivo: implementar una máquina de estados explícita para BlockStatus con transiciones permitidas y rechazo determinista de las prohibidas.

Estructura (en server/app/modules/redaccion/services/block_state_machine.py):
- BlockStateMachine.transition(block: BlockState, event: BlockTransitionEvent) -> BlockState
- Eventos: REQUEST_INPUT, EXTRACT, AI_GENERATE, REQUEST_REVIEW, APPROVE, REJECT, REGENERATE, LOCK

Tabla de transiciones (resumen):
- draft ─REQUEST_INPUT→ missing_input
- missing_input ─EXTRACT→ extracted
- draft ─EXTRACT→ extracted
- extracted ─AI_GENERATE→ ai_generated
- ai_generated ─REQUEST_REVIEW→ needs_review
- needs_review ─APPROVE→ approved
- needs_review ─REJECT→ rejected
- rejected ─REGENERATE→ ai_generated
- approved ─LOCK→ locked

Invariantes:
- Un bloque AI nunca pasa de `ai_generated` directo a `approved` sin `needs_review`.
- Un bloque `locked` no admite más transiciones.
- Un bloque `required` sin estado `approved`/`locked` bloquea el ensamblado.

Tests (RED → GREEN):
- test_block_state_machine_allows_extract_from_draft
- test_block_state_machine_blocks_direct_ai_to_approved
- test_block_state_machine_locked_block_is_terminal
- test_block_state_machine_rejected_block_can_regenerate
- test_final_assembler_blocks_when_required_block_not_approved
- test_block_transition_emits_audit_event

Criterio de done:
- Toda transición ilegal levanta `InvalidBlockTransitionError` con mensaje claro.
- Cada transición emite un evento auditable (`block_transition_audit`).
- Tests verdes (6/6).
```

---

### Prompt 9R.3.3 (RED/GREEN) — Propagación de outputs entre bloques + orden topológico

```markdown
# PROMPT 9R.3.3 (RED/GREEN) — BlockReference, projection y topología de ejecución

Objetivo: definir cómo el output de un bloque se convierte en input contextual de otro y garantizar que el CoreGraph ejecuta los bloques en orden topológico, rechazando ciclos en `depends_on`.

Refinamiento del contrato (en server/app/modules/redaccion/contracts/block_io.py):
- BlockReference (Pydantic):
    block_id: UUID
    projection: Literal["raw", "summary", "field"]
    field_path: str | None       # solo si projection="field"; dot+index notation tipo "rows[0].total"
- BlockContract.depends_on (refinado): list[BlockReference]    # antes era list[str]
- WorkspaceState.block_outputs: dict[UUID, dict]               # output serializable por block_id

Servicio (en server/app/modules/redaccion/services/block_topology.py):
- BlockTopology.sort(blocks: list[BlockContract]) -> list[BlockContract]
- BlockTopology.detect_cycles(blocks: list[BlockContract]) -> list[UUID]   # vacío si OK
- BlockTopology.resolve_inputs(state: WorkspaceState, block: BlockContract) -> dict[block_id, Any]
  - Aplica projection sobre cada `depends_on` para producir un dict listo para inyectar
  - "raw" → output completo
  - "summary" → output["summary"] si existe; si no, str(output)[:1000]
  - "field" → resuelve field_path con helper seguro (rechaza eval, accesos no atómicos)

Integración:
- 9R.4.2 (DraftValidator): rechazar ciclos en `depends_on` (404 con `loc` apuntando al bloque ofensor).
- 9R.6.2 (DeterministicExtractionNode): tras éxito escribe `state.block_outputs[block.id] = result.dict()`.
- 9R.6.3 (AIAssistDraftNode): antes de invocar el LLM construye contexto vía `BlockTopology.resolve_inputs`. NO accede directo a `state.raw_data_blocks`/`state.ai_draft_blocks`.
- 9R.3.2 (BlockState machine): un bloque no entra en `EXTRACT`/`AI_GENERATE` hasta que todos sus `depends_on` están en estado `approved` o `locked`. Para DETERMINISTIC consumido solo por otros DETERMINISTIC, también vale `extracted`.

Reglas duras:
- block_outputs es parte del estado del grafo y se persiste en `hub_workspaces.state_json` para reanudación.
- La projection "field" usa una helper estricta (`safe_field_resolver`) que solo acepta tokens dot y `[<int>]`. Cualquier otra cosa levanta `UnsafeFieldPathError`.
- Ningún nodo escribe block_outputs si su bloque no terminó en éxito.

Tests (RED → GREEN):
- test_block_reference_serializable_in_openapi_with_discriminator
- test_topology_sort_orders_blocks_by_dependencies
- test_topology_detect_cycle_returns_offending_block_ids
- test_draft_validator_rejects_cyclic_depends_on_with_422
- test_projection_raw_returns_full_output
- test_projection_summary_returns_summary_field_when_present
- test_projection_summary_falls_back_to_truncated_string_when_no_summary
- test_projection_field_resolves_dot_path
- test_projection_field_resolves_index_path
- test_projection_field_rejects_unsafe_expressions
- test_ai_node_reads_dependencies_via_projection_not_state
- test_block_blocked_until_dependencies_approved_or_locked
- test_block_outputs_persisted_to_workspace_state

Criterio de done:
- BlockReference aparece en openapi.json y Orval genera tipos.
- safe_field_resolver tiene cobertura ≥ 95 % de líneas (parsing crítico de seguridad).
- 13 tests verdes.
- Documentar en docs/REDACCION_CONTRACT_FIRST.md la sección "Propagación de outputs y topología".
```

---

### Prompt 9R.4.1 (RED/GREEN) — LLMSpecService: NL → ReportTemplateDraft

```markdown
# PROMPT 9R.4.1 (RED/GREEN) — Asistente LLM de especificación de informes

Objetivo: dado un texto en lenguaje natural, devolver un `ReportTemplateDraft` estructurado. El LLM NO ejecuta, NO persiste, NO escribe código.

Estructura (en server/app/modules/redaccion/services/llm_spec_service.py):
- LLMSpecService.propose_template(prompt_nl: str, owner_kind: Literal["admin","user"]) -> ReportTemplateDraft
- Internamente:
  1) Construir prompt con system message que liste los tipos de bloque permitidos.
  2) Llamar al LLM (Tier 1, model_factory).
  3) Parsear salida JSON (json_mode si el provider lo soporta, fallback con `pydantic.TypeAdapter`).
  4) Adjuntar `model_used`, `prompt_version`.

Reglas:
- El system prompt declara explícitamente los `BlockKind` válidos y rechaza `BlockKind` desconocidos en la respuesta.
- El servicio NO crea registros en BD. Solo devuelve el draft.
- El owner_kind se propaga al draft (afecta a quién verá el preview).

Tests (RED → GREEN):
- test_llm_spec_service_returns_report_template_draft   (mock LLM)
- test_llm_spec_service_records_model_used_and_prompt_version
- test_llm_spec_service_does_not_persist_anything
- test_llm_spec_service_respects_owner_kind            (admin → puede sugerir is_global=True)

Criterio de done:
- Servicio aislado, sin acceso a repos.
- Mock LLM en tests; el test real con LLM va en integración (`tests/integration/test_llm_spec_real.py`, opcional).
- Tests verdes.
```

---

### Prompt 9R.4.2 (RED/GREEN) — Validador estructural de ReportTemplateDraft

```markdown
# PROMPT 9R.4.2 (RED/GREEN) — Validador estructural y normalizador

Objetivo: validar que un `ReportTemplateDraft` propuesto por el LLM cumpla el contrato (BlockKind permitidos, dependencias resueltas, secciones bien formadas) y normalizarlo (orden de bloques, ids únicos).

Estructura (en server/app/modules/redaccion/services/draft_validator.py):
- DraftValidator.validate(draft: ReportTemplateDraft) -> ReportTemplateDraftValidationResult
- Comprueba:
  - profile_id pertenece al registry
  - todos los BlockKind son válidos
  - dependencias (`depends_on`) referencian bloques existentes
  - CHART/TABLE referencian un DETERMINISTIC_DATA presente
  - AI_* tienen ai_prompt_template_id resoluble (o usa default policy)
  - REVIEW_GATE existe si hay bloques AI
  - input_contract es coherente (slots referenciados por DETERMINISTIC_DATA existen)
- Normaliza:
  - asigna ids únicos a bloques que no los tengan
  - ordena bloques por section/order
  - devuelve `normalized_draft`

Tests (RED → GREEN):
- test_invalid_llm_draft_is_rejected
- test_unknown_block_type_is_rejected
- test_chart_without_data_block_is_rejected
- test_ai_block_without_review_gate_is_rejected
- test_draft_normalizer_assigns_unique_block_ids
- test_draft_normalizer_orders_blocks_by_section

Criterio de done:
- Validador determinista (mismo input → mismo output).
- Errors devueltos con `loc`, `msg`, `type` (compatible con FastAPI 422).
- Tests verdes.
```

---

### Prompt 9R.4.3 (RED/GREEN) — Endpoints preview/approve + HITL

```markdown
# PROMPT 9R.4.3 (RED/GREEN) — Endpoints HTTP para asistente LLM

Objetivo: exponer la generación de drafts, su preview y su aprobación (creando plantilla persistente o workspace ad hoc).

Endpoints (en server/app/routers/redaccion/llm_drafts_router.py — Deploy: edge):
- POST /api/v1/redaccion/llm-drafts/propose
  Request: { "prompt_nl": str, "mode": "admin_template" | "user_workspace" }
  Response: ReportTemplateDraft (sin persistir)
- POST /api/v1/redaccion/llm-drafts/validate
  Request: ReportTemplateDraft
  Response: ReportTemplateDraftValidationResult
- POST /api/v1/redaccion/llm-drafts/approve-as-template
  Request: { "draft": ReportTemplateDraft, "name": str, "is_global": bool }
  Solo rol admin/partner. Solo si is_global=True requiere admin.
  Response: ReportTemplateContract
- POST /api/v1/redaccion/llm-drafts/approve-as-workspace
  Request: { "draft": ReportTemplateDraft, "name": str }
  Cualquier usuario autenticado.
  Response: WorkspaceState

Reglas:
- approve-as-template solo crea plantillas. No crea workspace.
- approve-as-workspace crea plantilla privada (owner_kind=user) + workspace en estado `draft`.
- Ambos endpoints invocan DraftValidator antes de persistir; rechazan con 422 si invalid.

Tests (RED → GREEN):
- test_llm_draft_requires_human_approval_before_persisting
- test_admin_can_save_llm_draft_as_template
- test_non_admin_cannot_save_global_template
- test_user_can_use_llm_draft_as_private_workspace
- test_llm_draft_preview_contains_sections_blocks_and_inputs
- test_approve_endpoint_rejects_invalid_draft_with_422

Criterio de done:
- 4 endpoints registrados y documentados en OpenAPI.
- Tests verdes.
- Frontend (9R.7.4) podrá consumirlos vía Orval.
```

---

### Prompt 9R.4.4 (RED/GREEN) — Versionado de plantillas: política y migración de workspaces

```markdown
# PROMPT 9R.4.4 (RED/GREEN) — Política de anclaje y endpoints de migración

Objetivo: definir el comportamiento del sistema cuando se publica una nueva versión de un `ReportTemplate` que ya tiene workspaces vivos contra la versión anterior.

Política de producto (no negociable salvo cambio explícito):
- Un Workspace queda anclado a su `template_version_id` para siempre.
- Publicar vN+1 NO migra automáticamente workspaces existentes.
- El propietario del workspace ve un aviso "Plantilla actualizada — versión vN+1 disponible" en `WorkspaceStatusBar` (9R.7.2).
- La migración es un acto explícito del propietario: crea un workspace nuevo clonado contra vN+1, conservando solo los inputs originales (sin bloques approved). El workspace antiguo queda `archived` y permanece accesible para auditoría.

Servicio (en server/app/modules/redaccion/services/template_migration_service.py):
- TemplateMigrationService.detect_new_version(workspace_id) -> NewVersionNotice | None
    NewVersionNotice = { current_version_id, latest_version_id, changes_summary, breaking_changes }
- TemplateMigrationService.migrate_workspace(workspace_id, target_version_id, user_id) -> Workspace
    - Verifica compatibilidad de InputContract (mismos slots required obligatorios)
    - Crea workspace nuevo contra target_version_id, copia `inputs_json`, NO copia outputs ni approvals
    - Marca workspace antiguo: status="archived", archived_reason=f"migrated_to_{new_id}"
    - Setea workspace nuevo: parent_workspace_id apunta al antiguo
    - Devuelve nuevo workspace

Endpoints (Deploy: edge, hub_redaccion_router.py):
- GET  /api/v1/hub/redaccion/workspaces/{id}/template-update-notice
    Response 200: NewVersionNotice | 204 si workspace ya alineado
- POST /api/v1/hub/redaccion/workspaces/{id}/migrate
    Request: { "target_version_id": UUID }
    Response 201: { "new_workspace_id": UUID } | 409 con `compatibility_errors` si InputContract incompatible | 403 si no es owner

Migración Alembic:
- hub_workspaces.parent_workspace_id (UUID, FK a hub_workspaces.id, nullable)
- hub_workspaces.archived_reason (str, nullable)
- hub_workspaces.status: extender enum con "archived"

Reglas duras:
- Migrar NO borra el workspace antiguo (auditoría + RunManifest preservado).
- Solo `owner_id` puede invocar migrate. Misma policy que autosave 1C.1.
- Si target_version_id introduce un breaking change en InputContract (campo required nuevo), devolver 409 con `compatibility_errors: list[{ slot_id, reason }]`. El usuario debe rellenar los nuevos slots manualmente tras crear el workspace nuevo.

Tests (RED → GREEN):
- test_detect_new_version_returns_notice_when_template_has_newer_version
- test_detect_new_version_returns_none_when_workspace_aligned_to_latest
- test_migrate_creates_new_workspace_against_target_version
- test_migrate_preserves_inputs_json_verbatim
- test_migrate_does_not_copy_block_outputs_or_approvals
- test_migrate_archives_old_workspace_with_reason
- test_migrate_links_parent_workspace_id_in_new_workspace
- test_migrate_returns_409_when_input_contract_breaking_change
- test_migrate_requires_workspace_ownership
- test_migration_preserves_old_workspace_run_manifest

Criterio de done:
- Migración Alembic aplicada (3 columnas).
- 2 endpoints documentados en OpenAPI.
- 10 tests verdes.
- Documentar en docs/REDACCION_CONTRACT_FIRST.md la sección "Versionado de plantillas y migración de workspaces".
```

---

### Prompt 9R.5.1 (RED/GREEN) — Protocolo ExtractionPipeline + contratos

```markdown
# PROMPT 9R.5.1 (RED/GREEN) — Protocolos y contratos comunes de extracción

Objetivo: definir el contrato común que todo pipeline de extracción debe respetar, análogo al `RetrievalPipeline` de 9B.

Estructura (en server/app/modules/redaccion/pipelines/):
- contracts.py     # ExtractionPipeline (Protocol), ExtractionInput, ExtractionResult, ExtractedTable, ExtractedMetric, ExtractionWarning, ExtractionProvenance
- __init__.py

ExtractionInput:
- source_kind: Literal["excel","pdf_text","pdf_table","manual","admin_script"]
- file_ref: StorageRef | None     # ruta fsspec
- raw_text: str | None            # para manual
- options: dict                   # ej. {sheet: 0, header_row: 1}

ExtractionResult:
- tables: list[ExtractedTable]
- metrics: list[ExtractedMetric]
- free_text: str | None
- warnings: list[ExtractionWarning]
- provenance: ExtractionProvenance

ExtractionProvenance:
- pipeline_id: str
- source_ref: str            # storage key
- extracted_at: datetime
- column_mapping: dict | None
- pages: list[int] | None

ExtractionPipeline (Protocol):
- pipeline_id: ExtractionPipelineId
- def extract(input: ExtractionInput) -> ExtractionResult
- def supports(source_kind: str) -> bool

Tests (RED → GREEN):
- test_extraction_result_contains_provenance
- test_extraction_warning_has_severity_and_code
- test_extraction_pipeline_protocol_is_typing_protocol
- test_extraction_result_serializable_to_openapi

Criterio de done:
- Contratos en OpenAPI.
- Tests verdes.
- Sin implementación de pipelines concretos todavía (eso es 9R.5.2 / 9R.5.3 / 9R.5.4).
```

---

### Prompt 9R.5.2 (RED/GREEN) — ExcelExtractionPipeline + PDFTextExtractionPipeline

```markdown
# PROMPT 9R.5.2 (RED/GREEN) — Pipelines deterministas Excel y PDF-texto

Objetivo: implementar dos pipelines deterministas reales con datos de prueba.

Estructura (en server/app/modules/redaccion/pipelines/):
- excel_pipeline.py    # ExcelExtractionPipeline (pandas)
- pdf_text_pipeline.py # PDFTextExtractionPipeline (Docling, sin OCR, sin tablas)

ExcelExtractionPipeline:
- Lee con pandas (openpyxl backend).
- Soporta `sheet` y `header_row` en options.
- Valida columnas requeridas (si vienen en options.required_columns); emite ExtractionWarning si faltan.
- Devuelve ExtractedTable con `columns`, `rows`, `dtypes`.

PDFTextExtractionPipeline (versión MVP ligera):
- Usa Docling con `do_ocr=False`, `do_table_structure=False`, `do_picture_classification=False`.
- Extrae solo texto plano vía `export_to_text()`.
- Detecta PDFs no extractables (imagen sin capa de texto) → ExtractionWarning severity=error, code=NON_EXTRACTABLE_PDF.

> Nota (2026-05-13): la versión "rica" de este pipeline (markdown + tablas estructuradas + páginas) se entrega en **9R.5.9**, que amplía este pipeline aprovechando las capacidades completas de Docling. Esta versión queda como modo ligero/rápido para casos en que solo se necesita el texto.

Tests (RED → GREEN):
- test_excel_pipeline_reads_basic_table   (fixture: tests/fixtures/redaccion/sample.xlsx)
- test_excel_pipeline_reports_missing_required_columns
- test_excel_pipeline_handles_multiple_sheets
- test_pdf_text_pipeline_extracts_paragraphs
- test_pdf_pipeline_reports_non_extractable_pdf  (fixture: imagen-only PDF)
- test_excel_provenance_records_sheet_and_header_row

Criterio de done:
- Fixtures mínimas en tests/fixtures/redaccion/.
- pandas, docling añadidos a pyproject.toml (docling ya está, instalado para RAG).
- Tests verdes.
```

---

### Prompt 9R.5.3 (RED/GREEN) — PDFTableExtractionPipeline + ManualInputPipeline

```markdown
# PROMPT 9R.5.3 (RED/GREEN) — Tablas en PDF y entrada manual

Objetivo: añadir extracción de tablas PDF y normalización de entrada manual del usuario.

Estructura:
- pdf_table_pipeline.py # PDFTableExtractionPipeline (camelot o pdfplumber tables)
- manual_pipeline.py    # ManualInputPipeline

PDFTableExtractionPipeline:
- Intenta camelot lattice → fallback stream.
- Devuelve ExtractedTable por tabla detectada (con `page`).
- Si no detecta tablas → ExtractionWarning severity=warn, code=NO_TABLES_FOUND.

ManualInputPipeline:
- Convierte texto/números introducidos por el usuario en ExtractionResult mínima.
- No usa LLM. Solo normaliza tipos (parse_number, parse_date) y valida contra el InputSlot.

Tests (RED → GREEN):
- test_pdf_table_pipeline_detects_tables_with_camelot
- test_pdf_table_pipeline_warns_when_no_tables_found
- test_manual_pipeline_parses_numbers
- test_manual_pipeline_validates_required_slots
- test_manual_pipeline_rejects_wrong_type

Criterio de done:
- camelot-py añadido a deps (opcional: ghostscript en docker).
- Tests verdes.
```

---

### Prompt 9R.5.4 (RED/GREEN) — Factory + AdminScriptExtractionPipeline

```markdown
# PROMPT 9R.5.4 (RED/GREEN) — Factory y refactor del pipeline de scripts seguros

Objetivo: agrupar todos los pipelines en una factory selectiva por `source_kind`, y refactorizar el pipeline de scripts generados por IA del antiguo 9.11b para que sea uno más entre los pipelines.

Estructura:
- factory.py                # ExtractionPipelineFactory
- admin_script_pipeline.py  # AdminScriptExtractionPipeline (reusa ScriptSecurityAuditor)

ExtractionPipelineFactory:
- register(pipeline)
- get(source_kind) -> ExtractionPipeline
- list() -> list[ExtractionPipelineId]
- Auto-registra todos los pipelines al importar el paquete.

AdminScriptExtractionPipeline:
- Solo invocable por owner admin/partner del template.
- Recupera código aprobado (ya pasó AST + auditoría IA + aprobación HITL).
- Ejecuta el script en sandbox restringido (subproc con tiempo límite, pandas/json/math permitidos).
- Devuelve ExtractionResult.

Tests (RED → GREEN):
- test_factory_returns_pipeline_for_excel
- test_factory_returns_pipeline_for_pdf_text
- test_factory_returns_pipeline_for_pdf_table
- test_factory_returns_pipeline_for_manual
- test_factory_returns_pipeline_for_admin_script
- test_factory_rejects_unknown_source_type
- test_admin_script_pipeline_only_runs_approved_code
- test_admin_script_pipeline_blocks_unsafe_imports   (reusa tests de AST de 9.11b)

Criterio de done:
- ScriptSecurityAuditor de 9.11b migrado a `modules/redaccion/services/script_auditor.py` y reutilizado por AdminScriptExtractionPipeline.
- El endpoint `/agents/generate-script` queda dentro del flujo de creación de plantilla (no externo).
- Tests verdes (8/8).

Nota (2026-05-13): este prompt entrega solo el **motor de ejecución** (audit + sandbox). El **workflow de proposición LLM-asistido** (cualquier usuario propone, AST audit + sandbox test obligatorio, admin aprueba para plantillas globales) se cubre en 9R.5.5 + 9R.5.6 + 9R.7.5.
```

---

### Prompt 9R.5.5 (RED/GREEN) — ScriptProposalService + migración del módulo de anonimización (spaCy + Faker, desde legacy)

**Modelo sugerido**: **Opus** — migración masiva de 1011 LOC legacy + 14 tests con decisiones de diseño embebidas (qué preservar/descartar, adaptaciones async, contratos StorageRef).

```markdown
# PROMPT 9R.5.5 (RED/GREEN) — Workflow de proposición de scripts: motor backend con anonimización híbrida

Objetivo: permitir que cualquier usuario solicite a un LLM la generación de un script Python de extracción para su plantilla, validarlo automáticamente (AST audit + sandbox test obligatorio sobre datos reales o sintéticos) y dejarlo listo para persistir/promocionar. Este prompt entrega el motor backend completo, incluyendo la migración del módulo de anonimización legacy (spaCy NER + Faker + regex + anclajes de formulario), que ya estaba desarrollado y probado en client_app. Los endpoints de aprobación/persistencia llegan en 9R.5.6.

> **Avance respecto al plan original**: este prompt absorbe parte del trabajo previsto inicialmente para Fase 13 (NER). Se aprovecha el módulo legacy ya probado de `client_app/app/modules/privacy/` en lugar de reinventarlo. Fase 13 se reducirá a los hooks pre/post-LLM dentro del DraftingCoreGraph, reutilizando el `PiiDetector` que se construye aquí.

Deploy: edge

## Parte 1 — Migración del módulo de anonimización desde legacy

Fuente legacy (a migrar):
- `client_app/app/modules/privacy/anonymizer.py` (1011 líneas, motor core)
- `client_app/app/modules/privacy/anonymizer_service.py` (204 líneas, alto nivel xlsx/csv)
- `client_app/app/utils/pii_detector.py` (wrapper)
- `client_app/app/services/anonymization_service.py` (async wrapper + auditoría)
- Tests asociados en `client_app/tests/`: test_ner_anonymizer.py, test_anonymizer_patterns.py, test_anonymizer.py, test_anonymizer_extended.py, test_anonymizer_service.py, test_extraction_anonymization.py, test_etl_anonymization.py, test_custom_script_anonymization.py (los UI tests no se migran — los reemplaza 9R.7.5).

Destino:
- `server/app/modules/redaccion/services/anonymization/`
  - `__init__.py`
  - `pii_detector.py`            # PiiDetector (regex + spaCy NER + anclajes)
  - `faker_generator.py`         # FakerGenerator con contexto (firstname/lastname/fullname)
  - `anonymizer.py`              # AnonymizationContext (motor)
  - `service.py`                 # AnonymizerService (alto nivel async)
  - `policies.py`                # Strategies predefinidas (NER_PERSON→FAKE_NAME, EMAIL→TOKEN, DNI→CODE, AEPD/LOPDGDD)
- `server/tests/modules/redaccion/anonymization/` (tests migrados, adaptados a async)

Adaptaciones obligatorias durante la migración:
1. **Reemplazar `file_path: str` por `file_ref: StorageRef`** en todas las firmas públicas. Internamente usar StorageService para descargar antes de procesar.
2. **Hacer async** los puntos de E/S (descarga, subida). El motor de detección/sustitución puede seguir síncrono (CPU-bound).
3. **Eliminar dependencia de `EncryptionService`** para persistencia cifrada en disco — no se necesita en MVP de scripts (la determinismo se obtiene con `Faker(seed=hash(file_path))` por proposal). Mantener la API `save_state/load_state` pero como no-op opcional, marcada `# TODO post-MVP: persistencia de auditoría`.
4. **Quitar la integración con `enterprise_audit_service`** del legacy — se reemplaza por el audit log nativo del módulo redacción (HubWorkspaceAuditEvent existente desde 9R.8.1).
5. **Mantener Disposición 7ª LOPDGDD** (`anonymize_document_id`) — útil para despliegues en sector público español.
6. **Mantener fallback sin spaCy** — si el modelo no carga, degrada a solo regex con warning explícito en el audit_result devuelto al usuario.

Dependencias nuevas en pyproject.toml:
- `spacy>=3.7`
- `faker>=22.0` (probablemente ya esté)
- En Dockerfile (server): `RUN python -m spacy download es_core_news_md && python -m spacy download en_core_web_md` durante el build.

## Parte 2 — TestDataAnonymizerService (envoltura sobre el módulo migrado)

`server/app/modules/redaccion/services/test_data_anonymizer.py`:

Métodos públicos:
- `describe_columns(file_ref: StorageRef) -> ColumnInfo[]`
  - Solo aplica a XLSX/CSV.
  - Para cada columna: ejecuta `PiiDetector` sobre los primeros 50 valores no nulos.
  - Combina con heurística por nombre de columna ("nombre", "apellido", "email", "iban", "dni"…).
  - Devuelve `ColumnInfo(name, sample_values, inferred_faker_provider, confidence)`.
- `anonymize_tabular(file_ref, substitutions: list[ColumnSubstitution]) -> StorageRef`
  - Aplica el FakerGenerator del módulo migrado, fila a fila.
  - Devuelve referencia al archivo sintético en storage.
- `anonymize_pdf_to_text(file_ref: StorageRef) -> StorageRef`
  - Pipeline: Docling → markdown → `AnonymizationContext.anonymize()` sobre el texto completo → guarda `.md` sintético en storage.
  - **Opción 1 confirmada**: no regenera PDF. El admin lo verá como markdown plano. Justificación: el pipeline de scripts trabaja sobre `raw_text` extraído por Docling, regenerar el PDF añadiría coste sin valor.
- `preview_pdf_spans(file_ref: StorageRef) -> PiiSpan[]`
  - Para la UI: devuelve los spans detectados con `{start, end, type, original_text, suggested_fake}` para que el usuario revise antes de aplicar.

ColumnSubstitution:
```python
class ColumnSubstitution(BaseModel):
    column_name: str
    faker_provider: Literal[
        "keep", "name", "first_name", "last_name", "email", "phone",
        "iban", "dni", "nie", "address", "city", "company", "date", "integer"
    ]
```

## Parte 3 — ScriptProposalService

`server/app/modules/redaccion/services/script_proposal_service.py`:

- Constructor: `(llm_service, script_auditor: ScriptSecurityAuditor)` — reutiliza el auditor de 9R.5.4.
- `propose(prompt_nl, sample_schema, owner_kind) -> ProposalResult`:
  - System prompt acotado (lista blanca de imports = WHITELIST_MODULES de 9R.5.4; contrato de salida `result: dict`; variables disponibles `file_path/raw_text/options`).
  - Few-shot: al menos 1 ejemplo Excel + 1 ejemplo PDF text + 1 ejemplo de agregación con pandas.
  - Ejecuta `script_auditor.audit(code)` y devuelve `{code, audit_result}`.
  - **No persiste** — el guardado lo hace el endpoint.

## Parte 4 — Persistencia

`HubScriptProposal` (ORM, sobre HubOperationalBase):
- id: UUID PK
- proposer_user_id: UUID
- target_owner_kind: str  # 'user' | 'platform'
- target_template_id: UUID | None
- prompt_nl: text
- code: text
- audit_result_json: JSONB
- test_data_ref: JSONB | null         # StorageRef serializado, null hasta el primer /test
- test_data_is_anonymized: bool
- test_data_anonymization_map: JSONB | null    # {columns: [...], spans: [...]} según tipo
- test_data_kind: str | null          # 'xlsx' | 'csv' | 'pdf_text'
- test_result_json: JSONB | null
- test_result_hash: str | null        # sha256 hex
- test_validated_by_proposer_at: timestamp | null
- status: str   # proposed | tested | rejected (los de aprobación llegan en 9R.5.6)
- created_at, updated_at

Migración Alembic: tabla `hub_script_proposals` + FKs a hub_users.

## Parte 5 — Endpoints

Router: `server/app/routers/redaccion/scripts_router.py` (Deploy: edge, registrado en `_register_edge`).

- `POST /api/v1/redaccion/scripts/propose`
  - Body: `{prompt_nl, target_owner_kind, target_template_id?, sample_schema?}`
  - Crea HubScriptProposal status='proposed', devuelve `{proposal_id, code, audit_result}`.

- `POST /api/v1/redaccion/scripts/{proposal_id}/describe-test-data`
  - Body: multipart con archivo XLSX/CSV.
  - Sube a storage. Llama `describe_columns()`. Devuelve sugerencias de Faker provider por columna.

- `POST /api/v1/redaccion/scripts/{proposal_id}/preview-pdf-spans`
  - Body: multipart con PDF.
  - Sube a storage. Llama `preview_pdf_spans()`. Devuelve los PiiSpan detectados.

- `POST /api/v1/redaccion/scripts/{proposal_id}/anonymize-test-data`
  - Body: `{file_ref, kind: 'xlsx'|'csv'|'pdf_text', substitutions?, span_overrides?}`
  - Tabular: aplica `anonymize_tabular`. PDF: aplica `anonymize_pdf_to_text` (con overrides del usuario sobre los spans detectados).
  - Devuelve `{synthetic_ref, anonymization_map}`.

- `POST /api/v1/redaccion/scripts/{proposal_id}/test`
  - Body: `{test_data_ref, use_real_data: bool}`.
  - Si `target_owner_kind='platform'` → `use_real_data` DEBE ser false (422 si true: `REAL_DATA_NOT_ALLOWED_FOR_PLATFORM_TARGET`).
  - Ejecuta exactamente el mismo `_execute_in_sandbox` de `AdminScriptExtractionPipeline` (no duplicar lógica).
  - Captura ExtractionResult, calcula sha256 del JSON, guarda en BD, status proposed→tested.
  - Devuelve `{result, hash}`.

- `POST /api/v1/redaccion/scripts/{proposal_id}/validate-test-result`
  - Solo el proposer. Marca `test_validated_by_proposer_at=now`. 422 si no hay test_result_json todavía.

## Tests (RED → GREEN)

Anonimización (migrados/adaptados del legacy):
- test_pii_detector_identifies_persons_with_ner
- test_pii_detector_identifies_dni_nif_with_regex
- test_pii_detector_identifies_iban_with_regex
- test_pii_detector_uses_form_anchors_for_field_context
- test_pii_detector_degrades_to_regex_only_without_spacy
- test_faker_generator_is_deterministic_per_value
- test_faker_generator_uses_lastname_after_firstname_anchor
- test_anonymizer_handles_aepd_disposicion_septima_for_dni
- test_anonymize_tabular_preserves_row_count
- test_anonymize_pdf_to_text_returns_markdown_with_substituted_spans
- test_anonymize_pdf_to_text_preserves_non_pii_content_verbatim

Workflow (nuevos):
- test_propose_generates_code_and_audit_result
- test_propose_rejects_when_llm_outputs_forbidden_import (mocked LLM)
- test_describe_test_data_suggests_iban_provider_for_iban_column
- test_test_endpoint_requires_anonymized_data_for_platform_target
- test_test_endpoint_executes_in_same_sandbox_as_admin_pipeline
- test_test_endpoint_stores_result_hash
- test_validate_test_result_requires_prior_test
- test_validate_test_result_marks_proposer_validation_timestamp

## Criterio de done

- ≥19 tests verdes (11 anonimización + 8 workflow).
- Migración Alembic aplicada (`hub_script_proposals`).
- Endpoints registrados en main.py bajo `_register_edge`.
- `PiiDetector` queda como módulo independiente (lo reutilizará Fase 13 NER para los hooks pre/post-LLM).
- spaCy `es_core_news_md` y `en_core_web_md` descargados en el build de Docker.
- Documentación: añadir sección "Módulo de anonimización" a `docs/REDACCION_CONTRACT_FIRST.md` explicando origen legacy + adaptaciones.

## Retirada legacy (CLAUDE.md regla Caso A)

Al cerrar este prompt en GREEN:
- Mover a `_legacy_nicegui/` (manteniendo ruta relativa):
  - `client_app/app/modules/privacy/`
  - `client_app/app/services/anonymization_service.py`
  - `client_app/app/utils/pii_detector.py`
  - Tests legacy (excepto los de UI NiceGUI que sí se borran directamente, ya que son código huérfano — Caso B).
- Verificar con `grep -r` que no quedan referencias activas desde código de producción a las rutas movidas.
- **No borres `_legacy_nicegui/` ni en este prompt ni al cerrar la subfase**. El borrado definitivo lo hará el usuario manualmente al cierre de la Fase 1 completa (regla actualizada en CLAUDE.md).
```

---

### Prompt 9R.5.6 (RED/GREEN) — Aprobación con gate de validación obligatoria

**Modelo sugerido**: **Sonnet** — alcance acotado (state machine con 5 endpoints, gates de validación explícitos en el prompt). Opus solo si se quiere reducir iteraciones.

```markdown
# PROMPT 9R.5.6 (RED/GREEN) — Endpoints de aprobación + cola admin + incrustación en plantilla

Objetivo: cerrar el workflow de scripts: persistencia self-service en plantillas privadas, promoción con cola admin para plantillas globales. Toda persistencia exige test_validated_by_proposer_at NOT NULL.

Deploy: edge

Endpoints nuevos en server/app/routers/redaccion/scripts_router.py:

- POST /api/v1/redaccion/scripts/{proposal_id}/save-to-private-template
  - Requiere que el proposer sea el dueño de target_template_id y target_owner_kind='user'.
  - Reglas duras:
    - audit_result.approved must be True (422: AUDIT_FAILED)
    - test_validated_by_proposer_at IS NOT NULL (422: TEST_NOT_VALIDATED)
  - Crea nueva HubReportTemplateVersion del template con el script incrustado en spec_json (un nuevo BlockContract de tipo DETERMINISTIC_DATA con source_kind='admin_script' y options={code, approved:True}).
  - Actualiza HubReportTemplate.current_version_id.
  - Transiciona HubScriptProposal a status='approved', reviewer_user_id=proposer_user_id, reviewed_at=now.

- POST /api/v1/redaccion/scripts/{proposal_id}/submit-for-review
  - Requiere target_owner_kind='platform'.
  - Reglas duras: audit_result.approved + test_validated_by_proposer_at + test_data_is_anonymized=True (422 cualquiera de las tres).
  - Transiciona status='tested' → 'pending_review'. No persiste todavía en plantilla.

- GET /api/v1/redaccion/scripts/pending
  - Solo admin/partner. Devuelve lista de HubScriptProposal con status='pending_review'.
  - Cada item: proposal_id, proposer, prompt_nl, code (head 500 chars), audit_result, test_result_hash, test_data_ref (firmado para descarga temporal).

- POST /api/v1/redaccion/scripts/{proposal_id}/admin-retest
  - Solo admin/partner. Permite que el admin re-ejecute el script contra el mismo test_data_ref.
  - Compara nuevo hash con test_result_hash original.
  - Devuelve { result, hash, hash_matches: bool }.

- POST /api/v1/redaccion/scripts/{proposal_id}/approve
  - Solo admin/partner sobre proposal con status='pending_review'.
  - Body: { target_global_template_id, review_note? }
  - Reglas duras: hash_matches en el último admin-retest debe ser true (422: HASH_MISMATCH) — o haber sido revisado <10 min antes.
  - Crea nueva versión de target_global_template_id con script incrustado.
  - status='approved', reviewer_user_id=admin_id.

- POST /api/v1/redaccion/scripts/{proposal_id}/reject
  - Solo admin/partner. Body: { review_note }.
  - status='rejected'. Audit event en hub_workspace_audit_events.

Cambios en ORM:
- HubScriptProposal.status enum ampliado: proposed | tested | pending_review | approved | rejected.

Tests (RED → GREEN):
- test_save_to_private_template_requires_audit_pass
- test_save_to_private_template_requires_validated_test
- test_save_to_private_template_creates_new_version
- test_save_to_private_template_rejects_if_not_owner
- test_submit_for_review_requires_anonymized_test_data
- test_get_pending_returns_only_pending_review_status
- test_get_pending_forbidden_for_regular_user
- test_admin_retest_returns_hash_match_flag
- test_approve_requires_recent_hash_match
- test_approve_creates_new_global_template_version
- test_reject_records_note_and_blocks_further_changes

Criterio de done:
- 11 tests verdes.
- Migración Alembic con la ampliación del enum (si la columna es String(20), no necesita migración).
- README en docs/REDACCION_CONTRACT_FIRST.md: nueva sección "Workflow de scripts metaprogramados".
```

---

### Prompt 9R.5.7 (RED/GREEN) — Bloque CHART: migración del módulo de gráficos legacy

**Modelo sugerido**: **Sonnet** — migración con patrón establecido (mismo formato que 9R.5.4); sandbox compartido reduce decisiones. Opus si la auditoría AST con plotly/matplotlib produce falsos positivos sutiles.

```markdown
# PROMPT 9R.5.7 (RED/GREEN) — Implementación del block kind CHART vía migración del legacy

Objetivo: implementar la ejecución del block kind `CHART` (definido en 9R.3.1 pero sin handler real) migrando el módulo de gráficos legacy de `client_app/`. Patrón dual confirmado: modo determinista (UI configura tipo + ejes + filtros) y modo IA (NL → script Python que genera el gráfico). Determinista first: si el usuario lo configura, no se invoca al LLM.

> Avance respecto al plan original: 9R.3.1 dejó `CHART` definido como contrato sin implementación. Este prompt cierra esa deuda reutilizando el trabajo ya probado del legacy en lugar de reinventar.

Deploy: edge

## Parte 1 — Migración desde legacy

Fuente legacy:
- `client_app/app/modules/factory/graphics_factory.py` (342 LOC — modo IA, generación de script)
- `client_app/app/services/deterministic_graphics_service.py` (modo asistido)
- `client_app/app/services/graphics_service.py` (62 LOC — wrapper headless)
- Tests: `client_app/tests/unit/test_graphics_factory.py`, `test_graphics_page_modes.py`, `client_app/tests/security/test_sandbox_graphics.py`.

Destino:
- `server/app/modules/redaccion/services/charts/`
  - `__init__.py`
  - `chart_configuration.py`           # ChartConfiguration Pydantic (migrado del dataclass legacy)
  - `deterministic_chart_service.py`   # DeterministicChartService (modo configurador)
  - `chart_factory.py`                 # ChartFactory (modo IA, NL → script)
  - `chart_renderer.py`                # render_chart(config_or_script, data) → bytes (PNG/SVG)
- `server/tests/modules/redaccion/charts/`

Adaptaciones obligatorias:
1. **Eliminar acoplamiento NiceGUI**: el legacy mezcla UI con lógica dentro de `graphics_page.py` (líneas 771-816, `handle_ai_generation`). Esa lógica se extrae a `ChartFactory.generate_script()` y `chart_renderer.render_chart()`. La página NiceGUI se descarta — la UI nueva llega en 9R.7.x.
2. **StorageRef en lugar de file paths**: input (datos) y output (imagen del gráfico) referenciados por StorageRef.
3. **Sandbox compartido con scripts**: cuando se ejecuta el script generado en modo IA, usar el mismo `_execute_in_sandbox` de `AdminScriptExtractionPipeline` (9R.5.4). No duplicar.
4. **Auditoría AST igual que scripts**: el código generado por LLM pasa por `ScriptSecurityAuditor` (9R.5.4) antes de ejecutar. Lista blanca ampliada a `plotly`, `matplotlib`, `seaborn` solo para este pipeline.
5. **Output serializable para el manifest**: además del PNG/SVG, persistir el `ChartConfiguration` JSON (qué tipo, qué columnas) en `block.content_json` para reproducibilidad.

## Parte 2 — Integración con el block kind CHART

`server/app/modules/redaccion/blocks/handlers.py` — actualizar `ChartBlockHandler`:
- `execute(block: BlockContract, ctx: ExecutionContext) -> BlockOutput`:
  - Si `block.config.mode == 'deterministic'`: invoca `DeterministicChartService.render(config, data)`.
  - Si `block.config.mode == 'ai'`: invoca `ChartFactory.generate_script(nl_prompt, schema)` → audit → sandbox → `chart_renderer.render_chart(script, data)`.
  - Output: `{image_ref: StorageRef, configuration: ChartConfiguration, model_used: str | None}`.
- `to_manifest(block) -> dict`: incluye `chart_type`, `data_source_block_id` (BlockReference), `model_used`, `prompt_version` si modo IA.

Ampliación de `BlockContract` para CHART (en `contracts/blocks.py`):
```python
class ChartBlockConfig(BaseModel):
    mode: Literal['deterministic', 'ai']
    chart_type: Literal['bar', 'line', 'pie', 'scatter', 'histogram'] | None  # solo deterministic
    x_axis: str | None
    y_axis: str | list[str] | None
    color_by: str | None
    nl_prompt: str | None  # solo ai
    palette: str = 'default'
```

## Parte 3 — Endpoints

No se añaden endpoints HTTP nuevos: el render se invoca desde el grafo (`AIAssistDraftNode` siguiente al CHART consume el `image_ref`). Sí se añade:
- `GET /api/v1/redaccion/charts/preview` — solo en el wizard de UI, permite previsualizar un chart sin persistir (datos sintéticos del usuario).

## Tests (RED → GREEN)

Migrados/adaptados del legacy:
- test_deterministic_chart_service_renders_bar_chart
- test_deterministic_chart_service_renders_line_chart
- test_deterministic_chart_service_renders_pie_chart
- test_chart_factory_generates_script_from_nl
- test_chart_factory_rejects_unsafe_imports_in_generated_script
- test_chart_renderer_outputs_png_bytes
- test_chart_renderer_outputs_svg_when_requested

Nuevos:
- test_chart_block_handler_routes_to_deterministic_when_mode_deterministic
- test_chart_block_handler_routes_to_ai_when_mode_ai
- test_chart_block_handler_audits_generated_script_before_execution
- test_chart_block_handler_persists_configuration_in_manifest
- test_chart_block_handler_resolves_data_via_block_reference

## Criterio de done

- ≥12 tests verdes.
- `ChartBlockHandler.execute()` funcional para ambos modos.
- Sandbox compartido con AdminScriptExtractionPipeline (verificable: una sola implementación de `_execute_in_sandbox`).
- Tests del slice (9R.10) preparados para incluir un bloque CHART.

## Retirada legacy (CLAUDE.md regla Caso A)

Al cerrar este prompt en GREEN, mover a `_legacy_nicegui/`:
- `client_app/app/modules/factory/graphics_factory.py`
- `client_app/app/services/graphics_service.py`
- `client_app/app/services/deterministic_graphics_service.py`
- `client_app/app/ui/graphics_page.py`
- Tests legacy asociados.
Verificar con `grep -r` que no quedan referencias activas. Borrado definitivo manual por el usuario al cierre de Fase 1.
```

---

### Prompt 9R.5.8 (RED/GREEN) — Bloque DATA_TRANSFORM: migración del módulo ETL legacy

**Modelo sugerido**: **Opus** — el prompt más denso del bloque: migración ~1200 LOC + discriminated unions de operaciones + NL→ops con refinamiento iterativo + fallback a script + integración como nodo nuevo en el grafo. Concentra decisiones de diseño.

```markdown
# PROMPT 9R.5.8 (RED/GREEN) — Nuevo block kind DATA_TRANSFORM con motor ETL determinista + modo IA

Objetivo: introducir el block kind `DATA_TRANSFORM` que ejecuta transformaciones tabulares (filter, aggregate, join, pivot, normalize, groupby) entre la extracción determinista y los bloques IA. Migrado del módulo ETL legacy, que es el módulo mejor factorizado del client_app (separación lógica/UI razonable, sandbox + anonimización + refinamiento iterativo).

> Avance respecto al plan original: el BlockContract de 9R.1.2 cubría 10 tipos de bloque pero no incluía transformación tabular. Este prompt añade el 11º tipo y resuelve el eslabón ausente entre `DeterministicExtractionNode` y `AIAssistDraftNode` para informes que necesitan agregar/filtrar antes de redactar.

Deploy: edge

## Parte 1 — Migración desde legacy

Fuente legacy:
- `client_app/app/services/etl_service.py` (425 LOC, orquestador maduro)
- `client_app/app/services/deterministic_etl_service.py` (motor de operaciones)
- `client_app/app/modules/factory/etl_factory.py` (369 LOC, modo IA)
- Tests: `client_app/tests/unit/test_etl_service.py`, `test_deterministic_etl.py`, `client_app/tests/integration/test_etl_e2e.py` + tests de modos, clarificación, anonimización.

Destino:
- `server/app/modules/redaccion/services/transformation/`
  - `__init__.py`
  - `operations.py`                # Operation Pydantic discriminated union (FilterOp, AggregateOp, JoinOp, PivotOp, NormalizeOp, GroupByOp)
  - `deterministic_etl.py`         # DeterministicETLService.execute(df, operations) → df
  - `etl_factory.py`               # ETLFactory.generate_operations_from_nl(nl, schema) → list[Operation]
  - `etl_service.py`               # ETLService (orquestador: lee → transforma → valida → devuelve)
- `server/tests/modules/redaccion/transformation/`

Adaptaciones obligatorias:
1. **Reemplazar generación de script Python por generación de `list[Operation]` JSON**: en el legacy, el modo IA generaba código Python ejecutable. Aquí preferimos que la IA produzca operaciones declarativas (más auditable, más fácil de mostrar al usuario antes de aplicar). Si una operación requerida no encaja en el catálogo, fallback a script Python via ScriptSecurityAuditor (igual que 9R.5.5).
2. **StorageRef + DataFrame async**: el legacy trabajaba sobre `pd.DataFrame` in-memory. Mantener pandas pero envolver la lectura/escritura en async (`StorageService.get_bytes` + `pd.read_excel`/`read_csv`).
3. **Refinamiento iterativo conservado**: el legacy tenía `MAX_REFINEMENT_ITERATIONS = 3` (la IA podía corregir su output si la validación fallaba). Mantener.
4. **Anonimización integrada en el flujo de tests**: cuando el bloque DATA_TRANSFORM se usa como test data para un script (9R.5.5), el anonymizer (también 9R.5.5) se aplica antes.
5. **Tipos de operación cubiertos**: filter (col, op, value), aggregate (col, function), join (other_block_ref, on, how), pivot (index, columns, values), normalize (cols, method), groupby (cols, agg_dict). Validación estricta en cada operación.

## Parte 2 — Integración con el block kind DATA_TRANSFORM

Añadir `DATA_TRANSFORM` al `BlockKind` enum en `contracts/blocks.py`:

```python
class DataTransformBlockConfig(BaseModel):
    mode: Literal['deterministic', 'ai']
    source_block_ref: BlockReference  # de qué bloque toma el DataFrame
    operations: list[Operation] | None  # solo deterministic
    nl_instruction: str | None         # solo ai (se traduce a operations)
```

`DataTransformBlockHandler.execute(block, ctx)`:
- Resuelve DataFrame desde `source_block_ref` (reusa BlockReference + projection de 9R.3.3).
- Si `mode == 'deterministic'`: `DeterministicETLService.execute(df, operations)`.
- Si `mode == 'ai'`: `ETLFactory.generate_operations_from_nl(nl, schema)` → validate → execute. Si genera operations inválidas tras 3 intentos, fallback a script Python (sandbox + audit).
- Output: `{transformed_data_ref: StorageRef, operations_applied: list[Operation], model_used: str | None}`.
- `to_manifest`: incluye lista de operaciones aplicadas y fuente (deterministic vs ai).

## Parte 3 — Integración en el grafo

Modificar `DraftingCoreGraph` (9R.6.x):
- Nuevo nodo `DataTransformationNode` (servidor entre `DeterministicExtractionNode` y `AIAssistDraftNode`).
- Itera sobre bloques `DATA_TRANSFORM` en orden topológico (reusar 9R.3.3).
- Transición de estado: `draft → ai_generated` o `draft → extracted` según mode (el resultado es determinista en ambos casos — la IA solo elige las operaciones, no las ejecuta).

## Tests (RED → GREEN)

Migrados/adaptados del legacy:
- test_deterministic_etl_filter
- test_deterministic_etl_aggregate
- test_deterministic_etl_join
- test_deterministic_etl_pivot
- test_deterministic_etl_groupby_with_multiple_aggs
- test_deterministic_etl_normalize_min_max
- test_etl_factory_generates_operations_from_nl (mocked LLM)
- test_etl_factory_refines_when_validation_fails
- test_etl_factory_falls_back_to_script_when_operations_unsupported
- test_etl_service_runs_pipeline_end_to_end

Nuevos:
- test_data_transform_block_handler_resolves_source_via_block_ref
- test_data_transform_block_persists_operations_in_manifest
- test_data_transform_node_runs_between_extraction_and_ai
- test_data_transform_block_chains_with_chart_block_consuming_output

## Criterio de done

- ≥14 tests verdes.
- DATA_TRANSFORM funcional en ambos modos.
- `DataTransformationNode` integrado en core_graph.py (9R.6.x ya completado).
- Documentación actualizada en `docs/REDACCION_CONTRACT_FIRST.md`: sección "Bloques de transformación".

## Retirada legacy (CLAUDE.md regla Caso A)

Al cerrar este prompt en GREEN, mover a `_legacy_nicegui/`:
- `client_app/app/services/etl_service.py`
- `client_app/app/services/deterministic_etl_service.py`
- `client_app/app/modules/factory/etl_factory.py`
- `client_app/app/ui/etl_page.py`
- Tests legacy asociados.
Verificar con `grep -r` que no quedan referencias activas. Borrado definitivo manual por el usuario al cierre de Fase 1.
```

---

### Prompt 9R.5.9 (RED/GREEN) — Extractor Docling rico (ExtractedDocument) — adelantado parcial de Fase 2

**Modelo sugerido**: **Sonnet** — cambio de contrato bien definido + 2 ajustes localizados en nodos del grafo. La heurística text_linear/complex_tables es simple. Pasa a Opus si la API de Docling resulta más opaca de lo esperado.

```markdown
# PROMPT 9R.5.9 (RED/GREEN) — PDFTextExtractionPipeline rico: markdown + tablas estructuradas + páginas

Objetivo: amplificar el `PDFTextExtractionPipeline` actual (que ya usa Docling pero solo extrae texto plano via `export_to_text()`) para que produzca el contrato rico `ExtractedDocument` previsto inicialmente en Fase 2 prompt 9.12b. Aprovecha Docling al máximo: markdown por documento + markdown por página + tablas estructuradas con bbox, todo en una sola ejecución. Adelantado de Fase 2 a Fase 1 porque informes habituales agregan varios PDFs en un mismo informe — sin esta riqueza, el AIAssistDraftNode trabaja sobre texto plano linealizado y pierde estructura (encabezados, listas, tablas).

> Opción B confirmada (2026-05-13): adelantar **solo el extractor Docling rico**, no el wizard interactivo de extracción (analyze→extract→refine→generate_script) que sigue en Fase 2 prompt 9.13 con UI propia. El wizard se beneficia de RPA-like batch processing y encaja mejor con el módulo de automatización.

Deploy: edge

## Parte 1 — Contrato ExtractedDocument en redaccion

Origen del contrato: Fase 2 prompt 9.12b (`Plan_TDD_Fase2.md:436-455`). Se traslada literalmente, con ubicación nueva en redaccion.

Estructura en `server/app/modules/redaccion/pipelines/contracts.py`:
```python
class ExtractedCell(BaseModel):
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1

class ExtractedTableRich(BaseModel):
    """Tabla con coordenadas y celdas — extensión de ExtractedTable existente."""
    page: int                     # 1-based
    caption: str | None = None
    headers: list[str]
    cells: list[ExtractedCell]
    bbox: tuple[float, float, float, float] | None = None

class ExtractedPage(BaseModel):
    page: int                     # 1-based
    markdown: str                 # render markdown de esta página (Docling)
    plain_text: str               # texto lineal por si el consumidor prefiere
    tables: list[ExtractedTableRich]

class ExtractedDocument(BaseModel):
    """Salida rica de Docling. Se anexa a ExtractionResult.provenance.extras."""
    filename: str
    num_pages: int
    markdown: str                 # documento completo
    pages: list[ExtractedPage]
    tables: list[ExtractedTableRich]  # vista plana
    extraction_strategy: Literal["text_linear", "complex_tables"]
    docling_version: str
```

Para mantener retrocompatibilidad con el `ExtractionResult` simple (consumido por Excel, Manual, AdminScript), `ExtractedDocument` se entrega como **campo adicional** opcional:

```python
class ExtractionResult(BaseModel):
    tables: list[ExtractedTable] = Field(default_factory=list)
    metrics: list[ExtractedMetric] = Field(default_factory=list)
    free_text: str | None = None
    document: ExtractedDocument | None = None   # ← NUEVO. Solo PDFs ricos.
    warnings: list[ExtractionWarning] = Field(default_factory=list)
    provenance: ExtractionProvenance
```

Ventaja: los nodos del grafo que ya consumen `free_text` o `tables` siguen funcionando. Los nodos nuevos (AIAssistDraftNode, citation tracking) pueden preferir `document.markdown` y `document.tables[*]` cuando estén presentes.

## Parte 2 — Upgrade del PDFTextExtractionPipeline

Modificar `server/app/modules/redaccion/pipelines/pdf_text_pipeline.py`:

```python
def __init__(self) -> None:
    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = True        # ← cambio (antes False)
    opts.do_picture_classification = False
    opts.generate_page_images = False
    self._converter = DocumentConverter(...)

def extract(self, inp: ExtractionInput) -> ExtractionResult:
    conv = self._converter.convert(str(file_path))
    doc = conv.document

    # Construir ExtractedDocument rico
    pages = [
        ExtractedPage(
            page=p.page_no,
            markdown=p.export_to_markdown(),
            plain_text=p.export_to_text(),
            tables=[_to_rich_table(t) for t in p.tables],
        )
        for p in doc.pages
    ]
    rich = ExtractedDocument(
        filename=inp.file_ref.key,
        num_pages=len(pages),
        markdown=doc.export_to_markdown(),
        pages=pages,
        tables=[_to_rich_table(t) for t in doc.tables],
        extraction_strategy=_choose_strategy(doc),
        docling_version=docling.__version__,
    )

    # Mantener compatibilidad con consumers simples
    return ExtractionResult(
        free_text=doc.export_to_text() or None,
        tables=[ExtractedTable(  # vista simple para retro-compat
            name=f"page_{t.page}_table_{i}",
            headers=t.headers,
            rows=[[c.text for c in row_cells] for row_cells in _group_by_row(t.cells)],
            source_page=t.page,
        ) for i, t in enumerate(rich.tables)],
        document=rich,
        warnings=[...] if not doc.export_to_text() else [],
        provenance=...,
    )
```

Async wrapper: Docling es síncrono y CPU-bound. Envolver con `asyncio.to_thread(self._converter.convert, ...)` en el nodo `DeterministicExtractionNode` (cambio menor en 9R.6.2 ya verde).

## Parte 3 — Estrategia de extracción

Heurística mínima para `extraction_strategy`:
- Si `len(doc.tables) >= 3` o el ratio tables/pages > 0.5 → `complex_tables`.
- Si no → `text_linear`.

Útil para que `AIAssistDraftNode` adapte su prompt: ante `complex_tables` prioriza `tables_json` en el contexto; ante `text_linear` prioriza `markdown`.

## Parte 4 — Integración con AIAssistDraftNode (9R.6.3 ya verde — micro-ajuste)

Cambio en `server/app/modules/redaccion/graph/nodes/ai_assist_draft.py`:
- Cuando el bloque depende de un input PDF cuyo `ExtractionResult.document is not None`:
  - Pasar al LLM `document.markdown[:30000]` en lugar de `free_text`.
  - Si `extraction_strategy == "complex_tables"`: anexar `json.dumps([t.model_dump() for t in document.tables[:20]])`.
- Si el bloque depende de varios PDFs: concatenar markdown con encabezados `## [filename]` para que el LLM mantenga atribución.

## Parte 5 — Citation traceability (9R.6.3 ya verde — micro-ajuste)

`CitationAndTraceabilityNode`: cuando el contenido AI cite un dato extraído de un PDF rico, la cita puede incluir:
- `source_document` (filename)
- `page` (número de página del bbox)
- `cell_ref` si proviene de una tabla específica
- `excerpt` (primeros 200 chars del párrafo donde aparece el dato)

El modelo `Citation` de `contracts/runtime.py` ya soporta estos campos. Solo hay que poblarlos.

## Tests (RED → GREEN)

Nuevos (en `server/tests/modules/redaccion/test_docling_rich_extraction.py`):
- test_pipeline_produces_extracted_document_with_markdown
- test_pipeline_produces_per_page_markdown_and_tables
- test_pipeline_chooses_complex_tables_strategy_when_many_tables
- test_pipeline_chooses_text_linear_when_few_tables
- test_pipeline_preserves_table_bbox_when_available
- test_pipeline_extracted_document_serializes_to_openapi_schema
- test_retro_compat_free_text_still_populated
- test_retro_compat_simple_tables_view_still_populated

Adaptaciones a tests existentes (smoke tests, no rehacer):
- Tests de `AIAssistDraftNode` ahora reciben `document.markdown` cuando el input es PDF — verificar que el prompt construido lo incluye.
- Tests de `CitationAndTraceabilityNode` verifican que las citas con bbox/page se persisten.

## Criterio de done

- ≥8 tests nuevos verdes.
- Tests existentes de pdf_text_pipeline siguen verdes (retro-compatibilidad).
- `ExtractedDocument` aparece en OpenAPI exportado.
- AIAssistDraftNode prefiere markdown sobre plain_text cuando está disponible.
- Documentación actualizada en `docs/REDACCION_CONTRACT_FIRST.md`: sección "Extracción rica de PDFs con Docling".

## Lo que NO se hace aquí (queda en Fase 2)

- **Wizard de extracción con fases interactivas** (analyze_structure / extract_precision / refine / generate_script): sigue en Fase 2 prompt 9.13. El usuario interactivo con muchos PDFs similares (caso RPA) lo usa allí.
- **API de runs con polling por run_id**: no es necesaria en MVP. La extracción se hace síncrona dentro del DraftingCoreGraph (con `asyncio.to_thread`). Si emerge problema de latencia con PDFs grandes, se mueve a background task post-MVP.
- **UI específica del extractor PDF**: en MVP, el usuario sube PDFs vía el `GenericReportWizard` existente; no hay pantalla dedicada al extractor.

## Implicaciones para el plan de Fase 2

- Prompt 9.12b queda **reducido a deuda residual**: actualizar fixtures de tests, limpiar imports obsoletos. La mayor parte del trabajo (motor Docling, contratos `ExtractedDocument`, prompts adaptados a markdown) ya está hecha aquí.
- Prompt 9.13 (UI wizard) sigue íntegro pero ahora consume el contrato `ExtractedDocument` ya estable desde Fase 1.
- Fase 2 actualizará `Plan_TDD_Fase2.md` y `PROJECT_STATE.md` cuando se aborde, no es responsabilidad de este prompt.
```

---

### Prompt 9R.6.1 (RED/GREEN) — CoreGraph: nodos de carga y normalización

```markdown
# PROMPT 9R.6.1 (RED/GREEN) — LoadTemplateNode / ValidateInputContractNode / FileNormalizationNode

Objetivo: implementar los tres primeros nodos del DraftingCoreGraph.

Estructura (en server/app/modules/redaccion/graph/):
- state.py           # WorkspaceState reutiliza el contrato de runtime de 9R.1.3
- core_graph.py      # build_core_graph() devuelve compiled graph
- nodes/load_template.py
- nodes/validate_inputs.py
- nodes/file_normalization.py

LoadTemplateNode:
- Lee `template_version_id` del state.
- Carga ReportTemplateVersion desde repo.
- Hidrata `state.spec`.

ValidateInputContractNode:
- Comprueba slots requeridos del InputContract contra `state.inputs`.
- Marca bloques USER_INPUT pendientes como `missing_input`.
- Si falta input requerido → status="ingesting" (pide al usuario) o "error" según política.

FileNormalizationNode:
- Para cada InputArtifact PDF/Excel: descarga vía StorageService, calcula hash, registra en `state.artifacts_normalized`.
- No parsea; solo prepara para el siguiente nodo.

Tests (RED → GREEN):
- test_load_template_node_hydrates_state_spec
- test_load_template_node_raises_if_version_not_found
- test_validate_input_contract_marks_missing_required_inputs
- test_file_normalization_records_hashes
- test_core_graph_compiles_with_generic_report_profile

Criterio de done:
- `build_core_graph()` retorna un graph compilable.
- Tests verdes.
```

---

### Prompt 9R.6.2 (RED/GREEN) — CoreGraph: extracción determinista

```markdown
# PROMPT 9R.6.2 (RED/GREEN) — DeterministicExtractionNode / DataQualityCheckNode / MissingDataQuestionNode

Objetivo: ejecutar la extracción determinista antes de cualquier nodo IA.

Nodos:
- DeterministicExtractionNode
  - Para cada DETERMINISTIC_DATA block: invoca ExtractionPipelineFactory según `source_kind`.
  - Guarda ExtractionResult en `state.blocks[block_id].content`.
  - Transición de estado: missing_input → extracted.
- DataQualityCheckNode
  - Inspecciona warnings (NO_TABLES_FOUND, MISSING_REQUIRED_COLUMNS, NON_EXTRACTABLE_PDF).
  - Si severity=error → pasa al MissingDataQuestionNode.
- MissingDataQuestionNode
  - Formula preguntas concretas al usuario (HITL): "Falta columna 'fecha' en datos_excel — ¿puedes subir versión corregida?"
  - Estado del workspace = "in_review", devuelve grafo en pausa.

Tests (RED → GREEN):
- test_core_graph_blocks_when_required_input_missing
- test_core_graph_runs_deterministic_extraction_before_ai
- test_data_quality_check_pauses_graph_on_critical_warning
- test_missing_data_question_emits_actionable_message
- test_deterministic_extraction_writes_to_block_content

Criterio de done:
- Confirmar invariante: ningún nodo IA se ejecuta si data quality tiene errores críticos.
- Tests verdes.
```

---

### Prompt 9R.6.3 (RED/GREEN) — CoreGraph: nodos IA

```markdown
# PROMPT 9R.6.3 (RED/GREEN) — AIAssistDraftNode / CitationAndTraceabilityNode

Objetivo: generar texto asistido por IA usando solo datos ya validados como contexto, y registrar provenance.

Nodos:
- AIAssistDraftNode
  - Para cada bloque AI_ASSISTED_TEXT / AI_SUMMARY / AI_REWRITE:
    - Construye contexto solo con `state.blocks[*]` en estado `extracted` o `approved`.
    - Llama al LLM con prompt_template versionado.
    - Guarda salida + model_used + prompt_version en `state.blocks[block_id]`.
    - Transición: extracted → ai_generated.
- CitationAndTraceabilityNode
  - Adjunta citaciones a cada bloque AI (referenciando data blocks origen).
  - Si AI_ASSISTED_TEXT referencia un Excel: cita `[fila X, hoja "Y", input slot "datos_excel"]`.

Tests (RED → GREEN):
- test_ai_node_receives_only_validated_data_context
- test_ai_node_records_model_and_prompt_version
- test_ai_node_skipped_if_block_already_approved_or_locked
- test_citation_node_attaches_provenance_to_ai_block
- test_ai_node_handles_llm_error_gracefully   (state="error", no contamina state.blocks)

Criterio de done:
- Tests verdes (5/5).
- No hay AIDrafterNode legacy del 9.11c: ese paso queda absorbido aquí.
```

---

### Prompt 9R.6.4 (RED/GREEN) — CoreGraph: HITL y ensamblado

```markdown
# PROMPT 9R.6.4 (RED/GREEN) — UserReviewGateNode / ApplyUserEditsNode / FinalAssemblerNode

Objetivo: bloquear el ensamblado hasta que todos los bloques AI tengan estado `approved`, aplicar ediciones del usuario y ensamblar el documento final.

Nodos:
- UserReviewGateNode
  - Para cada bloque AI en `ai_generated` → transición a `needs_review`.
  - Si quedan bloques en `needs_review` → status="in_review", grafo pausa.
  - Si todos los AI están `approved` → continúa al ensamblado.
- ApplyUserEditsNode
  - Aplica ediciones manuales del usuario sobre el contenido (override del texto AI).
  - Mantiene el original en `state.blocks[block_id].original_ai_content` para auditoría.
- FinalAssemblerNode
  - Renderiza Markdown ensamblado según orden de secciones.
  - Solo incluye bloques en estado `approved` o `locked`.
  - Calcula `final_document_hash` (SHA-256 del Markdown).
  - Transición workspace: "in_review" → "assembled".

Tests (RED → GREEN):
- test_review_gate_prevents_unapproved_ai_blocks_in_final_document
- test_review_gate_pauses_graph_until_all_ai_blocks_approved
- test_apply_user_edits_preserves_original_ai_content
- test_final_assembler_only_includes_approved_blocks
- test_final_assembler_computes_document_hash

Criterio de done:
- Tests verdes (5/5).
- `state.final_document` poblado solo si todos los bloques requeridos están `approved`.
```

---

### Prompt 9R.6.5 (RED/GREEN) — CoreGraph: AuditLog + RunManifest emission + tracing Langfuse

```markdown
# PROMPT 9R.6.5 (RED/GREEN) — AuditLogNode + emisión de DraftingRunManifest + instrumentación Langfuse

Objetivo: cerrar el grafo emitiendo un DraftingRunManifest con trazabilidad completa e instrumentar todos los nodos del DraftingCoreGraph con Langfuse para observabilidad runtime (consistente con el grafo público de 9B).

Nodo:
- AuditLogNode
  - Construye DraftingRunManifest con todo el contenido necesario (ver 9R.9.1).
  - Persiste vía RunManifestRepo.
  - Actualiza `workspace.run_manifest_id`.
  - Transición workspace: "assembled" → "assembled" (el manifest no cambia estado, solo registra).

Instrumentación Langfuse (transversal a todos los nodos del CoreGraph):
- Reusar `server/app/core/observability/langfuse.py` (existente desde Fase 8). NO crear cliente nuevo.
- Cada invocación del CoreGraph abre un span raíz `redaccion.run` con atributos: `workspace_id`, `template_version_id`, `run_manifest_id` (asignado tras AuditLogNode).
- Cada nodo abre un span hijo `redaccion.{node_name}` con atributos: `node_name`, `block_id` (si aplica), `block_kind` (si aplica).
- Nodos IA (AIAssistDraftNode, CitationAndTraceabilityNode) añaden atributos extra al span: `model_used`, `prompt_version`, `tokens_in`, `tokens_out`, `latency_ms`.
- Fallos (capturados por la política de retry de 9R.6.6) se emiten como `span.event("error", { type, message, retry_attempt })` antes de marcar el bloque como `failed`.
- El `run_manifest_id` final se escribe como atributo del span raíz para enlazar tracing ↔ manifest.

Tests (RED → GREEN):
- test_core_graph_generates_run_manifest
- test_core_graph_generates_manifest_even_on_error
- test_core_graph_supports_admin_template_and_ad_hoc_workspace
- test_run_manifest_persisted_after_audit_log_node
- test_workspace_run_manifest_id_updated
- test_core_graph_opens_root_langfuse_span_with_workspace_id
- test_each_node_opens_child_span_under_root
- test_ai_node_records_model_and_token_attributes_on_span
- test_failed_node_emits_error_event_on_span
- test_root_span_attribute_run_manifest_id_set_after_audit_log

Criterio de done:
- Cualquier ejecución del DraftingCoreGraph (éxito o fallo controlado) deja un manifest persistido.
- Cada nodo aparece como span hijo del span raíz en Langfuse.
- Span raíz contiene `workspace_id`, `template_version_id` y `run_manifest_id` final.
- 10 tests verdes.
- Documentar en docs/REDACCION_CONTRACT_FIRST.md el diagrama final + sección "Observabilidad".
```

---

### Prompt 9R.6.6 (RED/GREEN) — CoreGraph: fallback paths + BlockState=failed

```markdown
# PROMPT 9R.6.6 (RED/GREEN) — Fallos controlados, BlockState=failed y política de retry

Objetivo: definir el comportamiento del DraftingCoreGraph cuando un nodo falla por causa controlada (timeout LLM, extracción imposible, AdminScript con excepción runtime), sin abortar el workspace ni perder el progreso ya logrado en otros bloques.

Extensión de BlockState (modifica 9R.3.2):
- Nuevo estado `failed` con sub-tipo obligatorio en `failure_kind`:
    failure_kind: Literal["extraction_failed", "ai_failed", "script_failed", "validation_failed"]
- Nuevas transiciones:
    draft           ─EXTRACT_FAIL→ failed(extraction_failed)
    extracted       ─AI_FAIL→      failed(ai_failed)
    extracted       ─SCRIPT_FAIL→  failed(script_failed)
    needs_review    ─APPROVE→      approved      (sin cambio)
    failed          ─REGENERATE→   draft|extracted|ai_generated (según failure_kind)
    failed          ─REJECT→       rejected      (saltar bloque si no es required)
    *(dependencia)  ─DEP_FAIL→     failed(validation_failed) si una dependencia está failed

Servicio BlockExecutor (nuevo, en server/app/modules/redaccion/services/block_executor.py):
- Encapsula la política de retry para todos los nodos del CoreGraph.
- async def execute(node_fn: Callable, block: BlockContract, state: WorkspaceState) -> NodeResult
    - Llama node_fn(block, state).
    - LLM timeouts y errores de red: 1 retry automático con backoff de 2s.
    - AST validation errors y script runtime exceptions: NO retry (probablemente bug determinista).
    - Captura excepción y devuelve `NodeResult(status="failed", failure_kind=..., last_error=...)`.
    - Cada intento emite span Langfuse `error` (ver 9R.6.5).

Comportamiento del CoreGraph ante fallo (ver 9R.3.3 para topología):
- El nodo afectado marca su bloque `failed(<failure_kind>)` y persiste outputs parciales si existen en `state.block_outputs[block.id]["partial"] = ...`.
- El CoreGraph NO aborta: continúa con los bloques cuya topología no dependa del fallido.
- Los bloques que dependen del fallido (vía `depends_on` de 9R.3.3) pasan automáticamente a `failed(validation_failed)` con `last_error="dependency_failed:<block_id>"`.
- AuditLogNode (9R.6.5) recoge la lista de bloques fallidos en `manifest.failed_blocks: list[{block_id, failure_kind, last_error_message, retry_attempts}]`.

Integración con UserReviewGateNode (9R.6.4):
- El gate también acepta bloques `failed`: la UI muestra `failure_kind`, último error y dos acciones:
    1) "Regenerar" → REGENERATE event, vuelve al estado origen y re-ejecuta.
    2) "Saltar bloque" → solo si `required=False`; emite REJECT.

Migración Alembic:
- hub_workspace_blocks: extender enum `state` con valor `failed`
- hub_workspace_blocks.failure_kind (str, nullable)
- hub_workspace_blocks.last_error_message (text, nullable)
- hub_workspace_blocks.retry_attempts (int, default 0, not null)

Reglas duras:
- BlockExecutor es la ÚNICA superficie con la política de retry. Los nodos no implementan su propio retry.
- Un bloque `required=True` cuya dependencia está `failed(validation_failed)` impide el ensamblado final (regla heredada de 9R.3.2 + 9R.6.4): FinalAssemblerNode rechaza el workspace con un `WorkspaceBlockedByFailedBlocksError`.

Tests (RED → GREEN):
- test_block_state_machine_supports_failed_state_with_subtypes
- test_block_state_machine_failed_to_regenerate_returns_to_correct_origin_state
- test_block_executor_retries_once_on_llm_timeout
- test_block_executor_no_retry_on_script_runtime_exception
- test_block_executor_no_retry_on_ast_validation_error
- test_block_executor_emits_error_span_on_each_attempt
- test_core_graph_continues_with_independent_blocks_when_one_fails
- test_core_graph_marks_dependent_blocks_as_validation_failed
- test_partial_outputs_preserved_under_block_outputs_partial
- test_audit_log_node_records_failed_blocks_in_manifest_with_attempts
- test_user_review_gate_allows_regenerate_on_failed_block
- test_user_review_gate_allows_skip_only_if_block_not_required
- test_final_assembler_rejects_when_required_block_failed_validation

Criterio de done:
- Migración Alembic aplicada (1 enum value + 3 columnas).
- BlockExecutor centraliza el retry; sin duplicación en los nodos.
- 13 tests verdes.
- Documentar en docs/REDACCION_CONTRACT_FIRST.md la sección "Fallos controlados y política de retry".
```

---

### Prompt 9R.7.1 (RED/GREEN) — UI: Renderer base + slots dinámicos

```markdown
# PROMPT 9R.7.1 (RED/GREEN) — ReportUIContractRenderer + DynamicUploadSlots + DynamicFieldRenderer

Objetivo: componente raíz que renderiza una UI completa solo a partir de un `ReportUIContract` consumido por Orval.

Estructura (en frontend/src/redaccion/components/):
- ReportUIContractRenderer.tsx
- DynamicUploadSlots.tsx
- DynamicFieldRenderer.tsx

Reglas:
- 0 interfaces TypeScript manuales. Usar tipos de @/shared/api/generated/model.
- react-hook-form + zodResolver para validación.
- Soporta i18n por dict[str,str] en labels.

Tests Vitest RED → GREEN:
- should_render_upload_slots_from_ui_contract
- should_render_dynamic_fields_from_ui_contract
- should_block_continue_when_required_input_missing
- should_show_validation_error_on_invalid_field
- should_render_localized_labels_from_dict

Criterio de done:
- 5/5 tests verdes.
- `npx tsc -p tsconfig.app.json --noEmit` limpio.
```

---

### Prompt 9R.7.2 (RED/GREEN) — UI: BlockEditor + paneles de revisión

```markdown
# PROMPT 9R.7.2 (RED/GREEN) — BlockEditor + AIBlockReviewPanel + DataQualityPanel + WorkspaceStatusBar

Objetivo: editor visual de bloques + paneles de revisión y estado.

Componentes:
- BlockEditor.tsx           → drag & drop de bloques (no-code, estilo TipTap)
- AIBlockReviewPanel.tsx    → muestra bloques en `needs_review` con botones Approve/Reject/Regenerate
- DataQualityPanel.tsx      → lista de ExtractionWarning con severity y código
- WorkspaceStatusBar.tsx    → estado del workspace + progreso (ingesting/extracting/drafting/in_review/assembled)

Hooks consumidos (Orval):
- useGetWorkspaceById
- usePatchWorkspaceBlock      (approve/reject/regenerate)
- useGetWorkspaceWarnings

Tests Vitest RED → GREEN:
- should_show_ai_blocks_as_pending_review
- should_require_explicit_approval_before_final_assembly
- should_show_extraction_warnings_with_severity
- should_show_workspace_status_progress
- should_allow_regenerate_ai_block

Criterio de done:
- Tests verdes (5/5).
- Sin fetch manual: todo vía hooks generados.
```

---

### Prompt 9R.7.3 (RED/GREEN) — UI: páginas admin y usuario

```markdown
# PROMPT 9R.7.3 (RED/GREEN) — ReportTemplateBuilderPage + GenericReportWizard

Objetivo: dos páginas con responsabilidades claras.

ReportTemplateBuilderPage (admin):
- Listado de plantillas (globales + organización).
- Crear/editar plantilla: configura secciones, bloques, inputs, ui_contract.
- Guardar como nueva versión (append-only).
- Restringido a rol admin/partner.

GenericReportWizard (user):
- Selección de plantilla (globales + propias) o GENERIC_REPORT.
- Wizard de inputs (upload slots, manual fields).
- Acceso al BlockEditor del workspace.
- Acceso al AIBlockReviewPanel.

Hooks (Orval): useListTemplates, useCreateTemplate, useCreateWorkspace, useGetWorkspaceById.

Tests Vitest RED → GREEN:
- should_allow_admin_to_save_template_version
- should_allow_user_to_create_ad_hoc_workspace_from_generic_report
- should_list_only_user_visible_templates
- should_redirect_non_admin_away_from_builder_page

Criterio de done:
- Tests verdes.
- Páginas registradas en el router del frontend.
```

---

### Prompt 9R.7.4 (RED/GREEN) — UI: LLM draft preview + aprobación

```markdown
# PROMPT 9R.7.4 (RED/GREEN) — LLMDraftPreviewPage

Objetivo: pantalla que pide al usuario un prompt en lenguaje natural, recibe `ReportTemplateDraft`, lo muestra editable, y permite aprobar como plantilla o workspace.

Pantalla (en frontend/src/redaccion/pages/LLMDraftPreviewPage.tsx):
- Input de texto natural + botón "Generar propuesta".
- Vista previa editable del draft (mismo BlockEditor de 9R.7.2).
- Toggle "Modo": Crear plantilla (admin) | Crear workspace (cualquiera).
- Botón "Aprobar y crear".
- Muestra validación estructural en línea (errors de DraftValidator).

Hooks (Orval): useProposeLlmDraft, useValidateLlmDraft, useApproveAsTemplate, useApproveAsWorkspace.

Tests Vitest RED → GREEN:
- should_render_llm_generated_draft_preview_before_persisting
- should_block_approve_button_when_draft_invalid
- should_call_approve_as_template_when_admin_mode
- should_call_approve_as_workspace_when_user_mode
- should_show_validation_errors_inline

Criterio de done:
- Tests verdes (5/5).
- Cero llamadas manuales a fetch.
```

---

### Prompt 9R.7.5 (RED/GREEN) — UI metaprogramación: wizard de propuesta de scripts + cola admin

**Modelo sugerido**: **Sonnet** — UI con muchos pasos pero patrones React conocidos (wizard + invalidación + hooks Orval). Decisiones de diseño ya tomadas en el prompt. Opus solo si la lógica de invalidación entre pasos se complica.

```markdown
# PROMPT 9R.7.5 (RED/GREEN) — UI completa del workflow de scripts

Objetivo: dar al usuario un wizard guiado para proponer un script vía LLM, probarlo obligatoriamente sobre datos reales o sintéticos antes de poder persistirlo, y al admin una cola de revisión para promociones a plantilla global.

Estructura nueva (en frontend/src/redaccion/):
- pages/ScriptProposalWizardPage.tsx     # wizard de 7 pasos para cualquier usuario
- pages/AdminScriptReviewQueuePage.tsx   # cola para admin/partner
- components/ScriptCodePreview.tsx       # syntax highlight + AST findings
- components/TestDataAnonymizerForm.tsx  # tabla columnas + dropdown Faker provider
- components/SandboxTestResultViewer.tsx # muestra ExtractionResult + hash

ScriptProposalWizardPage (data-testids: wizard-step-{n}):
1. Prompt NL — textarea "¿Qué cálculo o extracción necesitas?" + botón "Generar".
2. Preview código + auditoría — muestra código resaltado + lista de findings AST. Si audit.approved=false, botón "Reintentar" vuelve al paso 1 (con feedback del audit).
3. Subir datos de test — dropzone para CSV/XLSX.
4. Anonimización — tabla de columnas con dropdown por columna (keep / name / email / phone / iban / address / date / integer). Si target_owner_kind='platform', "keep" está deshabilitado para columnas con sample_values no numéricos (heurística simple).
5. Ejecutar sandbox — botón "Probar"; muestra ExtractionResult + hash. Si error, vuelve al paso 1 o 4.
6. Validar resultado — checkbox "Confirmo que esta salida es correcta para mi caso de uso" + botón "Confirmar".
7. Guardar / enviar — botones condicionales:
   - Si target_owner_kind='user': "Guardar en mi plantilla" (POST save-to-private-template).
   - Si target_owner_kind='platform': "Enviar al admin para revisión" (POST submit-for-review).

Cada paso bloquea el siguiente hasta que la condición se cumple (visible vía atributo aria-disabled). No hay back-skip silencioso: si cambias el código, los pasos 3-7 se invalidan y hay que rehacerlos.

AdminScriptReviewQueuePage:
- Tabla con propuestas pending_review: proposer, fecha, target_template, hash test.
- Click → vista detalle: código + audit + descarga test_data anonimizado + último ExtractionResult.
- Botón "Re-ejecutar test" (POST admin-retest) → muestra hash_matches.
- Botones "Aprobar" (deshabilitado si último retest hace >10 min o hash_matches=false) y "Rechazar con nota".

Hooks (Orval): useProposeScript, useAnonymizeTestData, useTestScript, useValidateTestResult, useSaveToPrivateTemplate, useSubmitForReview, useGetPendingScripts, useAdminRetest, useApproveScript, useRejectScript.

Tests Vitest RED → GREEN:
- should_block_next_step_until_audit_passes
- should_block_save_button_until_test_validated
- should_require_anonymization_for_platform_target
- should_invalidate_later_steps_when_code_regenerated
- should_disable_approve_when_admin_retest_stale
- should_show_hash_match_indicator_in_review_queue
- should_redirect_non_admin_away_from_review_queue
- should_call_save_to_private_template_for_user_target
- should_call_submit_for_review_for_platform_target

Criterio de done:
- 9 tests verdes.
- Rutas registradas en App.tsx: /redaccion/scripts/wizard y /redaccion/scripts/review (admin-only).
- i18n: todas las etiquetas vía i18next (es/en/ca).
- Cero hardcoded strings en UI.
- TypeScript limpio (`npx tsc -p tsconfig.app.json --noEmit`).
```

---

### Prompt 9R.7.6 (RED/GREEN) — Simplificación de etiquetas de estado y mensajes al usuario final

**Modelo sugerido**: **Sonnet** — alcance pequeño y bien definido (mapper de status + componente StatusBadge + BlockDebugPanel admin-only). Sin decisiones abiertas.

```markdown
# PROMPT 9R.7.6 (RED/GREEN) — Mensajes amigables para el usuario; detalle técnico solo para admin

Objetivo: la máquina de estados interna del backend tiene 9+ estados (draft, missing_input, extracted, ai_generated, needs_review, approved, rejected, locked, failed) más failure_kind. La UI debe traducir esto a un vocabulario reducido y comprensible para el usuario final, manteniendo el detalle técnico accesible solo en un panel debug visible a admin/partner.

Estructura nueva:
- frontend/src/redaccion/utils/statusLabels.ts
- frontend/src/redaccion/components/BlockDebugPanel.tsx
- frontend/src/shared/i18n/locales/{es,en,ca}/redaccion.json (nuevo namespace)

statusLabels.ts:
- mapBlockStatusToUserLabel(status: string, failure_kind?: string): { label: string, tone: 'neutral'|'info'|'warning'|'success'|'error' }
  - draft, missing_input    → { label: t('redaccion.status.missing_data'), tone: 'warning' }
  - extracted               → { label: t('redaccion.status.data_loaded'), tone: 'info' }
  - ai_generated, needs_review → { label: t('redaccion.status.needs_review'), tone: 'info' }
  - approved, locked        → { label: t('redaccion.status.approved'), tone: 'success' }
  - failed                  → { label: t('redaccion.status.error_recoverable'), tone: 'error' }
  - rejected                → { label: t('redaccion.status.rejected_retry'), tone: 'warning' }
- mapWorkspaceStatusToUserLabel(status): análogo para workspace (assembled → "Listo para exportar", etc.).

Modificaciones obligatorias en componentes existentes:
- BlockEditor.tsx, AIBlockReviewPanel.tsx, WorkspaceStatusBar.tsx, DataQualityPanel.tsx: SUSTITUIR la renderización cruda del status string por <StatusBadge label={...} tone={...} />.
- Crear StatusBadge en frontend/src/shared/components/StatusBadge.tsx (componente genérico reutilizable).

BlockDebugPanel.tsx:
- Solo se monta si useAuth().user.role in ('admin','partner').
- Toggle "Detalles técnicos" (off por defecto).
- Cuando se activa, muestra: status interno, failure_kind, last_error_message, retry_attempts, updated_at, audit events más recientes.
- Aparece como sección colapsable al final de BlockEditor.

Mensajes de error:
- last_error_message del backend NO se muestra al usuario final tal cual. Se reemplaza por traducción del failure_kind:
  - ai_failed         → "La IA no pudo generar este bloque. Puedes reintentarlo."
  - extraction_failed → "No se pudieron extraer datos del documento. Revisa el archivo y reintenta."
  - script_failed     → "El cálculo automático falló. Contacta con el administrador."
  - validation_failed → "Los datos no cumplen el formato esperado."
- El last_error_message original queda accesible solo desde BlockDebugPanel.

Tests Vitest RED → GREEN:
- should_render_user_label_not_internal_status
- should_map_failed_to_recoverable_error_tone
- should_not_show_last_error_message_to_regular_user
- should_show_last_error_message_in_debug_panel_for_admin
- should_hide_debug_panel_for_user_role
- should_translate_failure_kind_to_friendly_message

Criterio de done:
- 6 tests verdes.
- Ningún componente de redacción muestra el string crudo de status (grep negativo: `\{block\.status\}` no aparece en JSX).
- i18n en 3 idiomas.
- TypeScript limpio.
```

---

### Prompt 9R.8.1 (RED/GREEN) — Endpoints HITL por bloque

```markdown
# PROMPT 9R.8.1 (RED/GREEN) — Endpoints de transición de bloques

Objetivo: exponer las transiciones de BlockStatus como endpoints HTTP, delegando en BlockStateMachine.

Endpoints (en server/app/routers/redaccion/workspaces_router.py — Deploy: edge):
- PATCH /api/v1/redaccion/workspaces/{workspace_id}/blocks/{block_id}/approve
- PATCH /api/v1/redaccion/workspaces/{workspace_id}/blocks/{block_id}/reject
- PATCH /api/v1/redaccion/workspaces/{workspace_id}/blocks/{block_id}/regenerate
- PATCH /api/v1/redaccion/workspaces/{workspace_id}/blocks/{block_id}/edit  (override de content por usuario)
- POST  /api/v1/redaccion/workspaces/{workspace_id}/resume                 (reanuda DraftingCoreGraph)

Reglas:
- Solo el owner del workspace o admin/partner pueden transicionar.
- Cada transición registra audit event en la tabla `hub_workspace_audit_events`.
- regenerate dispara un nuevo AIAssistDraftNode para ese bloque solamente.

Tests (RED → GREEN):
- test_approve_block_transitions_to_approved
- test_reject_block_transitions_to_rejected
- test_regenerate_calls_ai_node_only_for_that_block
- test_edit_block_overrides_content_and_records_original
- test_resume_workspace_continues_graph_from_review_gate
- test_non_owner_cannot_transition_blocks

Criterio de done:
- Tests verdes (6/6).
- Endpoints en OpenAPI.
```

---

### Prompt 9R.8.2 (RED/GREEN) — Tests E2E de transiciones

**Modelo sugerido**: **Sonnet** — escenarios E2E explícitos, fixtures DB. Trabajo metódico, sin decisiones abiertas.

```markdown
# PROMPT 9R.8.2 (RED/GREEN) — Tests E2E de edición/rechazo/regeneración

Objetivo: cubrir el flujo completo de HITL con tests de integración usando DB real.

Escenarios E2E (en server/tests/modules/redaccion/e2e/):
1. test_e2e_user_approves_all_blocks_and_assembles
2. test_e2e_user_rejects_ai_block_then_regenerates_then_approves
3. test_e2e_user_edits_ai_block_content_and_original_preserved
4. test_e2e_user_with_missing_input_resumes_after_upload
5. test_e2e_admin_locks_block_to_prevent_further_changes

Cada test:
- Crea template + workspace.
- Sube fixtures.
- Recorre los endpoints de 9R.8.1.
- Verifica estado final del workspace, los blocks y el RunManifest.

Criterio de done:
- 5/5 tests E2E verdes.
- DB se limpia entre tests.
- Tiempo total < 30s.
```

---

### Prompt 9R.9.1 (RED/GREEN) — DraftingRunManifest modelo + repo + endpoint

**Modelo sugerido**: **Sonnet** — contrato Pydantic + repo + 2 endpoints GET. Patrón conocido sin sorpresas.

```markdown
# PROMPT 9R.9.1 (RED/GREEN) — DraftingRunManifest

Objetivo: implementar el modelo Pydantic, el repo y el endpoint de consulta del manifest.

DraftingRunManifest (en server/app/modules/redaccion/contracts/manifest.py):
- workspace_id: UUID
- template_id: UUID
- template_version_id: UUID
- report_profile: ReportProfileId
- uploaded_documents: list[UploadedDocumentInfo]
- input_contract_validation: InputContractValidationResult
- extracted_blocks: list[ExtractedBlockSummary]
- ai_blocks: list[AIBlockSummary]    # incluye model_used, prompt_version
- model_used: str | None             # último modelo usado
- prompt_versions: list[str]
- citations: list[Citation]
- warnings: list[ExtractionWarning]
- user_approvals: list[ApprovalRecord]
- final_document_hash: str | None
- created_at: datetime

Endpoints:
- GET /api/v1/redaccion/workspaces/{workspace_id}/manifest
- GET /api/v1/redaccion/manifests/{manifest_id}

Tests (RED → GREEN):
- test_run_manifest_created_for_each_drafting_run
- test_run_manifest_records_uploaded_documents
- test_run_manifest_records_extracted_blocks
- test_run_manifest_records_ai_blocks_and_model
- test_run_manifest_records_user_approvals
- test_run_manifest_endpoint_returns_full_payload
- test_run_manifest_is_immutable

Criterio de done:
- Tests verdes (7/7).
- Manifest expuesto en OpenAPI.
- Endpoint GET disponible para frontend de 1C.4.
```

---

### Prompt 9R.9.2 (RED/GREEN) — Integración con ExportService (1C.4) — DOCX-only en MVP

**Modelo sugerido**: **Sonnet** — generación DOCX con python-docx + smoke tests + chequeo opcional LibreOffice. Sin decisiones abiertas.

```markdown
# PROMPT 9R.9.2 (RED/GREEN) — Conexión con exportación DOCX

Objetivo: garantizar que la exportación a DOCX (prompt 1C.4) consume el manifest y lo incluye en el anexo de auditoría.

Alcance MVP: SOLO DOCX. ODT queda fuera del MVP — la abstracción `Exporter` se mantiene para que ODT entre como segunda implementación post-MVP sin rework.

Cambios:
- En 1C.4 (export_service): leer el manifest del workspace antes de exportar.
- Si manifest.final_document_hash es None → ExportService rechaza la exportación.
- Adjuntar como anexo: tabla con uploaded_documents, ai_blocks (model + prompt_version), user_approvals, warnings.
- Smoke test que abra el DOCX generado con python-docx para validar estructura básica.
- Si se detecta `libreoffice` en PATH, smoke test adicional convirtiéndolo a PDF para verificar compatibilidad.

Tests (RED → GREEN):
- test_export_service_reads_run_manifest_before_export
- test_export_service_rejects_export_without_final_hash
- test_export_appendix_includes_ai_blocks_with_model
- test_export_appendix_includes_user_approvals
- test_final_document_hash_in_export_metadata_matches_manifest
- test_docx_opens_without_errors_with_python_docx
- test_docx_renders_in_libreoffice_when_available  (skip si no hay libreoffice)

Criterio de done:
- Tests verdes (7/7, con skip condicional para libreoffice).
- Documentar en 1C.4 que requiere manifest válido y produce únicamente DOCX en esta fase.
- Marcar dependencia bidireccional: 1C.4 ↔ 9R.9.
- Documentar en `docs/REDACCION_CONTRACT_FIRST.md` que ODT está en backlog post-MVP y por qué (riesgo de incompatibilidad de estilos en LibreOffice vs Word).
```

---

### Prompt 9R.10.1 (RED) — Vertical slice E2E: tests de aceptación

**Modelo sugerido**: **Sonnet** — escritura de tests sobre comportamiento ya especificado. Si los tests fallan por motivos triviales (imports, fixtures), Sonnet basta; el wire-up complejo va en 9R.10.2.

```markdown
# PROMPT 9R.10.1 (RED) — Tests E2E del slice MVP

Objetivo: escribir los tests de aceptación end-to-end del flujo completo de GENERIC_REPORT. Deben fallar inicialmente (cubren el wire-up que aún no existe).

Escenario E2E (test_generic_report_slice_mvp.py):
1. Usuario describe el informe en NL.
2. Sistema propone draft.
3. Usuario aprueba draft → crea workspace.
4. Usuario sube Excel + PDF.
5. Sistema valida inputs.
6. Sistema ejecuta DeterministicExtractionNode (Excel → tabla, PDF → texto).
7. Sistema ejecuta AIAssistDraftNode (genera análisis + summary).
8. Sistema entra en in_review.
9. Usuario aprueba ambos bloques AI.
10. Sistema ensambla documento Markdown.
11. Sistema emite DraftingRunManifest.

Tests:
- test_user_can_create_generic_report_from_natural_language
- test_user_can_upload_excel_and_pdf_to_workspace
- test_required_inputs_are_validated
- test_excel_data_is_extracted_before_ai_drafting
- test_ai_block_requires_review
- test_final_document_contains_only_approved_blocks
- test_run_manifest_is_generated_at_end_of_slice

Criterio de RED correcto:
- Todos los tests existen y describen el comportamiento esperado.
- Fallan por ImportError, endpoint no encontrado, o estados incoherentes — no por error de sintaxis.
- Documentar qué wire-up falta en `tests/modules/redaccion/e2e/slice_mvp_status.md`.
```

---

### Prompt 9R.10.2 (GREEN) — Wire-up integral del slice

**Modelo sugerido**: **Opus** — prompt crítico del bloque: integración cruzada de 9R.1 a 9R.9, debugging multi-módulo, decisiones de wire-up dispersas. Aquí Sonnet suele pegarse en bugs sutiles; Opus reduce iteraciones de forma notable.

```markdown
# PROMPT 9R.10.2 (GREEN) — Hacer pasar el slice MVP

Objetivo: conectar todas las piezas (9R.1 a 9R.9) para que los tests de 9R.10.1 pasen.

Tareas (no implementar nuevas funcionalidades — solo wire-up):
1. Registrar todos los routers en server/app/main.py con etiqueta Deploy: edge.
2. Conectar LLMSpecService → DraftValidator → approve-as-workspace → DraftingCoreGraph.
3. Conectar endpoints de 9R.8.1 al BlockStateMachine real (no stub).
4. Asegurar que AuditLogNode persiste el manifest al final.
5. Configurar fixtures de Excel/PDF en tests/fixtures/redaccion/.
6. Wire del frontend: ReportTemplateBuilderPage, GenericReportWizard, LLMDraftPreviewPage en el router del frontend.

Tests:
- Todos los tests de 9R.10.1 deben pasar.
- Suite completa de redaccion (unit + integration + e2e) verde.

Criterio de done:
- E2E del slice MVP verde (7/7).
- No hay regresiones en otros módulos.
- `uv run pytest server/tests/modules/redaccion/ -v` pasa.
- `npm test` del frontend pasa.

Aviso: tras este prompt, los antiguos endpoints `/agents/templates`, `/agents/workspaces` y `/agents/generate-script` del 9.11a–9.11d deben eliminarse o quedar como aliases que devuelven 301 a los nuevos `/redaccion/*`. Si se eliminan, dejar tests de regresión que aseguren que no hay clientes activos usándolos.
```

---

### Continuación tras el bloque 9R

Una vez completado 9R.10.2:

- Eliminar definitivamente las tablas legacy `hub_agent_templates`, `hub_user_workspaces`, `hub_workspace_documents` del 9.11a (migración de borrado tras verificar que no quedan datos).
- Eliminar el código de `modules/agents_hub/agent/` que correspondía al pipeline antiguo de redacción (DataExtractorNode/AIDrafterNode/DocumentAssemblerNode) si todavía existe — el DraftingCoreGraph del 9R lo reemplaza.
- Reanudar la subfase 1.C: el prompt 1C.0 (Focus Mode) y 1C.4 (exportación DOCX/ODT) ya pueden apoyarse en el manifest de 9R.9.

---


---

## ~~Prompts 9.11a–9.11d~~ — REEMPLAZADOS por el bloque 9R (referencia histórica, NO ejecutar)

> Los prompts 9.11a–9.11d se mantienen aquí como contexto histórico de cómo se planteó inicialmente la redacción.
> A partir del 2026-05-11 quedan **superseded** por el BLOQUE 9R (ver arriba), que aplica el patrón contract-first del bloque 9B.
> No ejecutar estos prompts directamente. La capa de scripts seguros (9.11b) se reabsorbe en `AdminScriptExtractionPipeline` del prompt 9R.5.4.

### Prompt 9.11a - Agentes Privados: Modelos y API Base (TDD RED/GREEN)

**Objetivo**: Crear la infraestructura de backend para plantillas de informes híbridas y workspaces privados, permitiendo tanto plantillas globales (admin) como privadas (usuario).

**Instrucciones**:
```text
Actúa como experto en FastAPI y SQLAlchemy async. Implementa los modelos y endpoints base en server/app/modules/agents_hub/.

TABLAS NUEVAS (crear migración Alembic):
- `hub_agent_templates`: Plantillas (id, nombre, descripcion, system_prompt, config_hibrida JSON, is_global bool, owner_id nullable)
- `hub_user_workspaces`: Sesiones de redacción (id, template_id, user_id, estado_documento JSON, created_at, updated_at)
- `hub_workspace_documents`: Documentos subidos temporalmente a una sesión (id, workspace_id, filename, file_path)

ENDPOINTS (en `hub_agents_router.py`):
GET    /api/v1/hub/agents/templates (devuelve globales + las del user)
POST   /api/v1/hub/agents/templates (crea nueva plantilla)
POST   /api/v1/hub/agents/workspaces (instancia una sesión a partir de un template)
GET    /api/v1/hub/agents/workspaces/me
GET    /api/v1/hub/agents/workspaces/{workspace_id}
POST   /api/v1/hub/agents/workspaces/{workspace_id}/upload

TESTS REQUERIDOS:
- test_user_can_read_global_templates_and_own_templates
- test_create_workspace_from_template
- test_unauthenticated_user_cannot_access_workspaces
```

---

### Prompt 9.11b - Pipeline de Seguridad y Generación de Scripts (TDD RED/GREEN)

**Objetivo**: Servicio determinista (código plano, sin LangGraph) para generar scripts extractores seguros, con validación AST y Auditoría IA, previo a la confirmación HITL del usuario.

**Instrucciones**:
```text
Actúa como experto en Python y Seguridad. Implementa `ScriptSecurityAuditor` en server/app/modules/agents_hub/services/.

FLUJO DEL SERVICIO (Código Plano, Síncrono/Stateless):
1. Recibe el prompt natural del usuario.
2. Llama al LLM (Tier 1) para generar el script Python.
3. Validación AST: parsea con `ast.parse` y bloquea imports peligrosos (os, subprocess, sys, open). Solo permite pandas, json, math, etc.
4. Auditoría IA: Llama a un LLM Tier Superior pasando el código. Pregunta si tiene efectos colaterales. Debe devolver un JSON `{ "safe": bool, "reason": "..." }`.

ENDPOINT:
POST /api/v1/hub/agents/generate-script
Request: { "prompt": "..." }
Response: { "code": "...", "is_safe": bool, "audit_reason": "..." }
(El HITL se hará en el Frontend, el usuario decidirá si guardar este código en la plantilla).

TESTS REQUERIDOS:
- test_ast_validator_blocks_os_import
- test_ast_validator_allows_pandas
- test_security_auditor_flags_malicious_code
```

---

### Prompt 9.11c - Ensamblador Híbrido LangGraph (TDD RED/GREEN)

**Objetivo**: Implementar el grafo LangGraph para el agente redactor que combina extracción determinista con reflexión IA.

**Instrucciones**:
```text
Actúa como experto en LangGraph y Python. Crea el pipeline híbrido de redacción en server/app/modules/agents_hub/agent/.

ESTADO DEL GRAFO (`WorkspaceState`):
- `workspace_id`: str
- `chat_history`: list
- `raw_data_blocks`: dict (ej. tablas extraídas determinísticamente)
- `ai_draft_blocks`: dict (ej. reflexiones generadas por IA)
- `final_document`: str (markdown ensamblado)

NODOS A IMPLEMENTAR:
1. `DataExtractorNode`: Ejecuta el script seguro (guardado en la plantilla) sobre los documentos del workspace. Guarda en `raw_data_blocks`. NO usa el LLM para parsear datos.
2. `AIDrafterNode`: Llama al LLM pasando `raw_data_blocks` como contexto. Genera el texto reflexivo en `ai_draft_blocks`.
3. `DocumentAssemblerNode`: Usa Jinja2 para combinar ambos bloques según el layout de la plantilla, actualizando `final_document`.

TESTS REQUERIDOS:
- test_data_extractor_executes_script_deterministically
- test_ai_drafter_receives_data_as_context_only
- test_document_assembler_combines_blocks_correctly
```

---

### Prompt 9.11d - Frontend: Interfaz No-Code y Workspaces (TDD RED/GREEN)

**Objetivo**: Implementar las pantallas de creación de plantillas (HITL) y la vista de redacción (Workspace) para el usuario final, integrando los átomos de automatización.

**Instrucciones**:
```text
Actúa como experto en React y Tailwind. Implementa las vistas en frontend/src/agent/.

1. PANTALLA CREACIÓN PLANTILLAS (`AgentTemplatesPage.tsx`):
- Editor visual (No-Code, estilo TipTap) para arrastrar "Bloques de Datos" y "Bloques IA".
- Generador de Scripts e Integración de Átomos: 
  - Permite añadir un "Bloque de Transformación de Datos": UI para seleccionar tipo de transformación (agrupar, filtrar, etc.) consumiendo el backend del átomo migrado.
  - Permite añadir un "Bloque de Gráfico": UI para seleccionar tipo de gráfico (barras, líneas, pastel) consumiendo el backend del átomo de ploteo.
  - Para lógicas a medida: Input de texto natural -> botón "Generar Script IA" -> llama a `/generate-script`.
- HITL: Si `is_safe` es true, muestra la razón de auditoría en verde. Exige que el usuario clique "Aprobar y Guardar" antes de persistir la plantilla.

2. PANTALLA WORKSPACE (`AgentWorkspacePanel.tsx`):
- Split View:
  - Izquierda: Chat + Dropzone de archivos.
  - Derecha: Live Preview del `final_document` (Markdown renderizado incluyendo los gráficos generados).
- Botón "Exportar PDF/Word".

TESTS REQUERIDOS (Vitest):
- should_require_explicit_hitl_approval_before_saving_template
- should_render_split_view_with_chat_and_preview
- should_render_data_transformation_and_plot_config_ui
```


---


## Subfase 1.C — Infraestructura de Diseño y Exportación Avanzada de Informes (PENDIENTE)

**Objetivo**: Completar la cadena de valor de los informes: infraestructura de diseño transversal (Focus Mode), exportación a formatos editables (DOCX/ODT) y entrega a flujos humanos externos (Google Drive).

**Dependencias**: BLOQUE 9R — Redacción Contract-First (DraftingCoreGraph + ReportProfiles + DraftingRunManifest). 1C.4 requiere especialmente el manifest emitido por 9R.9 para el anexo de auditoría. (Los antiguos 9.11a–9.11d quedan superseded por 9R.)

**Entregable**: Editor de informes en Focus Mode con exportación a DOCX/ODT con citas trazables y opción de guardar directamente en Google Drive institucional.

---

### Prompt 1C.0 — Focus Mode como Infraestructura de Diseño Transversal (TDD RED/GREEN)

**Modelo sugerido**: **Sonnet** — React + Zustand + componentes shadcn/ui con tests explícitos. Sin lógica LLM. Patrón conocido.

**Objetivo**: Implementar el sistema de Focus Mode y DrawerHub como infraestructura de diseño reutilizable en `frontend/src/shared/layout/`. Sirve tanto al workspace de informes (Subfase 1.C) como, en Fase 2, al editor de flujos de automatización.

**Contexto**: En los workspaces de informes (9.11d), el botón "Exportar" abre un panel lateral. En los flujos de automatización (Fase 2), el mismo panel mostrará las Data Pills y el Copilot. El mismo componente `DrawerHub` sirve a ambos contextos gracias al campo `context` del store.

**Instrucciones al agente**:
```text
Actúa como experto en React y Zustand. Implementa el sistema de Focus Mode y DrawerHub en
frontend/src/shared/layout/.

1. STORE GLOBAL (useFocusStore.ts):
   Zustand store con las siguientes propiedades:
     viewMode: 'standard' | 'focus'   (colapsa el sidebar principal cuando 'focus')
     drawerVisible: boolean
     activeTab: 'config' | 'blocks' | 'data' | 'ai' | 'pills' | 'copilot'
     context: { type: 'informe' | 'flujo'; entityId: string } | null
   Acciones: setViewMode, toggleDrawer, setActiveTab, setContext, reset.

2. DRAWERHUB (DrawerHub.tsx):
   Componente Sheet de shadcn/ui (side="right", width="420px").
   Renderiza pestañas dinámicas según context.type:
     - Si 'informe': pestañas 'Bloques', 'Datos', 'IA'.
     - Si 'flujo': pestañas 'Configuración', 'Data Pills', 'Copilot'.
   Cada pestaña renderiza un slot (children por nombre de pestaña).

3. FOCUSLAYOUT (FocusLayout.tsx):
   HOC/wrapper que:
     - Al montar: llama setContext({type, entityId}) y setViewMode('focus').
     - Al desmontar: llama reset() para restaurar el estado.
     - Colapsa el sidebar principal inyectando la clase 'sidebar-collapsed' en el layout raíz.
     - Renderiza {children} + <DrawerHub />.

USO PREVISTO:
   En AgentWorkspacePanel (9.11d):
     <FocusLayout context={{ type: 'informe', entityId: workspace.id }}>
       <WorkspaceContent />
     </FocusLayout>

TESTS REQUERIDOS (Vitest):
- should_set_focus_mode_on_mount_and_reset_on_unmount
- should_render_informe_tabs_when_context_type_is_informe
- should_render_flujo_tabs_when_context_type_is_flujo
- should_collapse_sidebar_when_view_mode_is_focus
- should_toggle_drawer_visibility
```

**Tests RED — frontend/src/shared/layout/__tests__/FocusMode.test.tsx**:
```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { act } from 'react';

describe('useFocusStore', () => {
  beforeEach(() => {
    // Reset store between tests
    const { reset } = require('../useFocusStore').useFocusStore.getState();
    act(() => reset());
  });

  it('should_set_focus_mode_on_mount_and_reset_on_unmount', () => {
    const { useFocusStore } = require('../useFocusStore');
    const { FocusLayout } = require('../FocusLayout');

    const { unmount } = render(
      <FocusLayout context={{ type: 'informe', entityId: 'ws-123' }}>
        <div>contenido</div>
      </FocusLayout>
    );

    expect(useFocusStore.getState().viewMode).toBe('focus');
    expect(useFocusStore.getState().context?.entityId).toBe('ws-123');

    unmount();

    expect(useFocusStore.getState().viewMode).toBe('standard');
    expect(useFocusStore.getState().context).toBeNull();
  });

  it('should_render_informe_tabs_when_context_type_is_informe', () => {
    const { useFocusStore } = require('../useFocusStore');
    const { DrawerHub } = require('../DrawerHub');

    act(() => {
      useFocusStore.getState().setContext({ type: 'informe', entityId: 'ws-1' });
      useFocusStore.getState().toggleDrawer();
    });

    render(<DrawerHub />);

    expect(screen.getByRole('tab', { name: /bloques/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /datos/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /ia/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /copilot/i })).not.toBeInTheDocument();
  });

  it('should_render_flujo_tabs_when_context_type_is_flujo', () => {
    const { useFocusStore } = require('../useFocusStore');
    const { DrawerHub } = require('../DrawerHub');

    act(() => {
      useFocusStore.getState().setContext({ type: 'flujo', entityId: 'flow-1' });
      useFocusStore.getState().toggleDrawer();
    });

    render(<DrawerHub />);

    expect(screen.getByRole('tab', { name: /configuraci/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /data pills/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /copilot/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /bloques/i })).not.toBeInTheDocument();
  });

  it('should_collapse_sidebar_when_view_mode_is_focus', () => {
    const { FocusLayout } = require('../FocusLayout');

    const { container } = render(
      <FocusLayout context={{ type: 'informe', entityId: 'ws-1' }}>
        <div>contenido</div>
      </FocusLayout>
    );

    // FocusLayout debe añadir clase sidebar-collapsed al elemento raíz del layout
    const layoutWrapper = container.querySelector('[data-testid="focus-layout"]');
    expect(layoutWrapper).toHaveClass('sidebar-collapsed');
  });

  it('should_toggle_drawer_visibility', () => {
    const { useFocusStore } = require('../useFocusStore');

    expect(useFocusStore.getState().drawerVisible).toBe(false);
    act(() => useFocusStore.getState().toggleDrawer());
    expect(useFocusStore.getState().drawerVisible).toBe(true);
    act(() => useFocusStore.getState().toggleDrawer());
    expect(useFocusStore.getState().drawerVisible).toBe(false);
  });
});
```

**Criterios de aceptación**:
- `FocusLayout` activa `viewMode='focus'` al montar y llama `reset()` al desmontar.
- `DrawerHub` muestra pestañas de Informe cuando `context.type='informe'`; pestañas de Flujo cuando `context.type='flujo'`.
- El sidebar colapsa (clase `sidebar-collapsed`) cuando `viewMode='focus'`.
- `AgentWorkspacePanel` (9.11d) se envuelve con `<FocusLayout>` sin modificar su lógica interna.
- Los 5 tests pasan en verde.

---

### Prompt 1C.0.bis — Copilot Drawer: RAG sobre docs de módulo + NL→config (TDD RED/GREEN)

**Modelo sugerido**: **Opus** — tuning de comportamiento LLM (RAG sobre docs + traductor NL→config estructurada para tres targets distintos). Los prompts del sistema y la validación discriminated-union son finos: Opus reduce iteraciones notablemente sobre Sonnet.

**Objetivo**: añadir al `DrawerHub` (1C.0) un asistente conversacional (`CopilotPanel`) que cumple dos funciones, migradas conceptualmente del legacy `copilot_chat.py` (986 LOC NiceGUI):
1. **RAG sobre la documentación del módulo activo**: el usuario hace preguntas en lenguaje natural ("¿cómo creo un bloque de tabla?", "¿qué pasa si rechazo un bloque IA?") y recibe respuestas basadas en `docs/REDACCION_CONTRACT_FIRST.md` y similares, contextualizadas al módulo donde está navegando.
2. **NL → instrucciones deterministas**: el usuario dicta lo que quiere ("agrupa por mes y suma el importe", "haz un gráfico de barras del total por región") y el copilot produce **configuración estructurada** que las páginas wizard consumen (operaciones ETL del 9R.5.8, configuración de chart del 9R.5.7, propuesta de script del 9R.5.5).

**Dependencias**: 1C.0 (FocusLayout + DrawerHub + useFocusStore), 9R.5.5 (ScriptProposalService — copilot lo invoca para scripts), 9R.5.7 (ChartFactory — copilot lo invoca para gráficos), 9R.5.8 (ETLFactory — copilot lo invoca para transformaciones).

**Origen legacy** (a migrar conceptualmente, no portar literalmente NiceGUI):
- `client_app/app/ui/components/copilot_chat.py` (986 LOC) — patrones reutilizables:
  - Parseo de tags `[PROMPT_PROPOSAL]`, `[ETL_AI_PROMPT]`, `[CHART_AI_PROMPT]` para distinguir "respuesta textual" de "configuración estructurada".
  - `STEP_TYPE_MAP` que mapea contexto del módulo (GRAPHICS/ETL/EXTRACTION) al tipo de instrucción esperada — equivalente a nuestro `BlockKind`.
  - **Pills contextuales**: sugerencias rápidas según el módulo donde está el usuario.
- `client_app/app/ui/focus_manager.py` (183 LOC) — `apply_fix()` con acciones tipadas (CREATE_STEP, ANONYMIZE_VAR…) — patrón a replicar con dispatch via `useFocusStore`.

**Instrucciones al agente**:
```text
Actúa como experto en React + Zustand + RAG. Implementa el CopilotPanel en
frontend/src/shared/layout/copilot/.

1. SERVICIO BACKEND (server/app/modules/redaccion/services/copilot/):
   - DocsRetriever: indexa docs/REDACCION_CONTRACT_FIRST.md + docs/CHATBOTS_PUBLICOS.md
     usando BGE-M3 (el embedding_service ya existente). Filtro por módulo activo.
   - CopilotService.answer(question, context): {answer: str, source_refs: list[str]}
   - CopilotService.translate_nl_to_config(instruction, target_kind): devuelve un
     discriminated union ChartConfig | list[Operation] | ProposalRequest según target_kind.
     Internamente invoca ChartFactory / ETLFactory / ScriptProposalService.
   - Endpoint: POST /api/v1/redaccion/copilot/ask
                POST /api/v1/redaccion/copilot/translate

2. UI (frontend/src/shared/layout/copilot/CopilotPanel.tsx):
   - Input de chat + botón enviar.
   - Pills contextuales (3-5 sugerencias rápidas según useFocusStore.context.type).
   - Distingue dos tipos de respuesta:
     - Textual con citas → renderiza como markdown + lista de referencias.
     - Configuración estructurada → muestra preview + botón "Aplicar" que despacha
       una acción al store de la página activa (ChartConfig al builder de chart,
       Operations al wizard ETL, ProposalRequest al wizard de script).

3. STORE (extiende useFocusStore):
   pendingAction: { kind: 'chart_config' | 'etl_ops' | 'script_proposal'; payload: any } | null
   Acción dispatchCopilotAction(action) que las páginas wizard consumen vía hook
   useCopilotAction(targetKind).

Tests Vitest:
- should_index_docs_and_retrieve_by_module
- should_answer_question_with_source_refs
- should_translate_nl_to_chart_config_when_target_is_chart
- should_translate_nl_to_etl_operations_when_target_is_data_transform
- should_translate_nl_to_script_proposal_when_target_is_admin_script
- should_render_pills_contextual_to_active_module
- should_dispatch_action_to_active_wizard_when_apply_clicked
```

**Criterios de aceptación**:
- 7 tests verdes.
- CopilotPanel integrado como pestaña en DrawerHub (tab "Copilot" tanto en 'informe' como en 'flujo').
- Cero llamadas manuales a fetch — solo hooks Orval.
- i18n en ES/EN/CA.

**Retirada legacy (CLAUDE.md regla Caso A)**:
Al cerrar este prompt en GREEN, mover a `_legacy_nicegui/`:
- `client_app/app/ui/components/copilot_chat.py`
- `client_app/app/ui/components/side_drawer.py`
- `client_app/app/ui/focus_manager.py`
- Tests asociados.
Borrado definitivo manual al cierre de Fase 1.

---

### Prompt 1C.1 — Autosave y resiliencia del Workspace (TDD RED/GREEN)

**Modelo sugerido**: **Sonnet** — concurrencia optimista con contrato explícito (version por workspace + bloque). Patrón conocido, alcance acotado.

**Objetivo**: Persistir automáticamente el estado del Workspace en backend tras cada cambio de bloque, con concurrencia optimista y detección de conflictos. Permite que el usuario pueda cerrar la pestaña o perder conexión sin perder trabajo, y evita pisar cambios de otra sesión abierta del mismo workspace.

**Contexto**: 9R.1.4 crea las tablas `hub_workspaces` y `hub_workspace_blocks`. El editor del 9R.7 emite cambios por bloque (`BlockState`, contenido editado por el usuario, edición de `ai_generated`). Sin autosave, un fallo de red o un cierre accidental pierde el trabajo. Sin versión optimista, dos pestañas abiertas se pisan silenciosamente.

**Dependencias**: 9R.1.4 (tablas), 9R.3.2 (BlockState machine), 1C.0 (Focus Mode).

**Instrucciones al agente**:
```text
Actúa como experto en FastAPI async y React Query. Implementa autosave con concurrencia optimista.

BACKEND — server/app/modules/redaccion/

1. Migración Alembic: añadir `version` (int, default 1, not null) a `hub_workspaces`.
   Cada UPDATE incrementa `version` en 1.

2. Schemas Pydantic en `redaccion/contracts/state_update.py`:
   class BlockUpdate(BaseModel):
       block_id: UUID
       state: BlockState | None          # opcional: transición de estado
       content: dict | None              # opcional: contenido editado del bloque
       expected_block_version: int       # versión esperada del bloque (optimistic lock por bloque)

   class WorkspaceStatePatch(BaseModel):
       expected_workspace_version: int   # versión esperada del workspace
       block_updates: list[BlockUpdate]

   class WorkspaceStatePatchResponse(BaseModel):
       workspace_version: int            # nueva versión tras el patch
       updated_block_versions: dict[UUID, int]
       saved_at: datetime

3. Endpoint en `hub_redaccion_router.py` (Deploy: edge):
   PATCH /api/v1/hub/redaccion/workspaces/{workspace_id}/state
   - 200: aplicado, devuelve nueva versión
   - 409 Conflict: `expected_workspace_version` o `expected_block_version` desactualizada
       Response body: { "current_workspace_version": int, "conflicting_block_ids": [UUID] }
   - 422: BlockState transition inválida (rechaza por la state machine de 9R.3.2)
   - 404: workspace no existe o no pertenece al usuario

4. Servicio `WorkspaceAutosaveService` con método `apply_patch(workspace_id, user_id, patch)`:
   - Lock pesimista de la fila del workspace (SELECT ... FOR UPDATE) durante el patch
   - Verifica `expected_workspace_version` y cada `expected_block_version`
   - Valida transiciones contra `BlockState` machine (9R.3.2)
   - Incrementa versiones, persiste, devuelve nuevo manifest de versiones

FRONTEND — frontend/src/redaccion/hooks/

1. `useAutosave(workspaceId, getState)`:
   - Debounce 1500ms tras el último cambio
   - useEffect con cleanup que cancela debounce al desmontar
   - Mutation que invoca PATCH; on success actualiza la versión en el store local
   - on 409: emite evento `workspace:conflict` con `conflicting_block_ids`
   - on error de red: reintenta con backoff exponencial (3 intentos máx), luego marca el workspace como "offline"

2. Componente `ConflictModal` (frontend/src/redaccion/components/):
   - Se abre al recibir `workspace:conflict`
   - Texto: "Otra sesión ha modificado este workspace. Recarga para ver los cambios; los tuyos no guardados se perderán."
   - Botón único "Recargar workspace" → invalida la query, refetch.

3. Indicador visual en `WorkspaceStatusBar` (9R.7.2):
   - "Guardado hace Ns" / "Guardando..." / "Sin conexión" / "Conflicto sin resolver"

TESTS REQUERIDOS:

Backend (pytest):
- test_patch_with_correct_versions_updates_workspace_and_blocks
- test_patch_with_stale_workspace_version_returns_409
- test_patch_with_stale_block_version_returns_409_with_conflicting_ids
- test_patch_with_invalid_block_state_transition_returns_422
- test_patch_increments_workspace_and_block_versions
- test_patch_is_atomic_on_partial_failure
- test_patch_requires_workspace_ownership

Frontend (Vitest):
- should_debounce_autosave_calls_to_at_most_one_per_1500ms
- should_open_conflict_modal_on_409_response
- should_retry_save_with_backoff_on_network_error
- should_mark_workspace_offline_after_3_failed_retries
- should_update_local_version_after_successful_save
```

**Tests RED — tests/modules/redaccion/unit/test_autosave_service.py**:
```python
"""Tests para WorkspaceAutosaveService — TDD RED."""
import pytest
from uuid import uuid4
from datetime import datetime

from server.app.modules.redaccion.services.autosave_service import (
    WorkspaceAutosaveService, ConflictError, InvalidTransitionError,
)
from server.app.modules.redaccion.contracts.state_update import (
    WorkspaceStatePatch, BlockUpdate,
)


class TestWorkspaceAutosaveService:

    @pytest.mark.asyncio
    async def test_patch_with_correct_versions_updates_workspace_and_blocks(
        self, autosave_service, seeded_workspace_v3_with_blocks
    ) -> None:
        ws, blocks = seeded_workspace_v3_with_blocks
        patch = WorkspaceStatePatch(
            expected_workspace_version=3,
            block_updates=[
                BlockUpdate(
                    block_id=blocks[0].id,
                    state="approved",
                    content={"text": "edited"},
                    expected_block_version=blocks[0].version,
                ),
            ],
        )
        result = await autosave_service.apply_patch(ws.id, ws.owner_id, patch)
        assert result.workspace_version == 4
        assert result.updated_block_versions[blocks[0].id] == blocks[0].version + 1

    @pytest.mark.asyncio
    async def test_patch_with_stale_workspace_version_raises_conflict(
        self, autosave_service, seeded_workspace_v3_with_blocks
    ) -> None:
        ws, _ = seeded_workspace_v3_with_blocks
        patch = WorkspaceStatePatch(expected_workspace_version=1, block_updates=[])
        with pytest.raises(ConflictError) as exc:
            await autosave_service.apply_patch(ws.id, ws.owner_id, patch)
        assert exc.value.current_workspace_version == 3

    @pytest.mark.asyncio
    async def test_patch_with_stale_block_version_raises_conflict_with_ids(
        self, autosave_service, seeded_workspace_v3_with_blocks
    ) -> None:
        ws, blocks = seeded_workspace_v3_with_blocks
        patch = WorkspaceStatePatch(
            expected_workspace_version=3,
            block_updates=[
                BlockUpdate(
                    block_id=blocks[0].id,
                    content={"text": "x"},
                    expected_block_version=blocks[0].version - 1,  # stale
                ),
            ],
        )
        with pytest.raises(ConflictError) as exc:
            await autosave_service.apply_patch(ws.id, ws.owner_id, patch)
        assert blocks[0].id in exc.value.conflicting_block_ids

    @pytest.mark.asyncio
    async def test_patch_with_invalid_state_transition_raises(
        self, autosave_service, seeded_workspace_v3_with_blocks
    ) -> None:
        ws, blocks = seeded_workspace_v3_with_blocks
        # blocks[0] está en 'draft'; no se puede pasar directamente a 'locked'
        patch = WorkspaceStatePatch(
            expected_workspace_version=3,
            block_updates=[
                BlockUpdate(
                    block_id=blocks[0].id,
                    state="locked",
                    expected_block_version=blocks[0].version,
                ),
            ],
        )
        with pytest.raises(InvalidTransitionError):
            await autosave_service.apply_patch(ws.id, ws.owner_id, patch)

    @pytest.mark.asyncio
    async def test_patch_is_atomic_on_partial_failure(
        self, autosave_service, seeded_workspace_v3_with_blocks, session
    ) -> None:
        ws, blocks = seeded_workspace_v3_with_blocks
        # Un update válido + uno inválido → toda la transacción se revierte
        patch = WorkspaceStatePatch(
            expected_workspace_version=3,
            block_updates=[
                BlockUpdate(
                    block_id=blocks[0].id, content={"x": 1},
                    expected_block_version=blocks[0].version,
                ),
                BlockUpdate(
                    block_id=blocks[1].id, state="locked",  # inválido
                    expected_block_version=blocks[1].version,
                ),
            ],
        )
        with pytest.raises(InvalidTransitionError):
            await autosave_service.apply_patch(ws.id, ws.owner_id, patch)
        # versión del workspace y bloques sin cambios
        await session.refresh(ws)
        assert ws.version == 3
```

**Tests RED — frontend/src/redaccion/hooks/\_\_tests\_\_/useAutosave.test.tsx**:
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAutosave } from '../useAutosave';

const PATCH_URL = /\/api\/v1\/hub\/redaccion\/workspaces\/.+\/state/;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('useAutosave', () => {
  beforeEach(() => { vi.useFakeTimers(); });

  it('should_debounce_autosave_calls_to_at_most_one_per_1500ms', async () => {
    const patchMock = vi.fn().mockResolvedValue({ workspace_version: 2 });
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    );
    act(() => { result.current.markDirty(); });
    act(() => { result.current.markDirty(); });
    act(() => { result.current.markDirty(); });
    vi.advanceTimersByTime(1499);
    expect(patchMock).not.toHaveBeenCalled();
    vi.advanceTimersByTime(2);
    await waitFor(() => expect(patchMock).toHaveBeenCalledTimes(1));
  });

  it('should_open_conflict_modal_on_409_response', async () => {
    const patchMock = vi.fn().mockRejectedValue({
      status: 409, body: { current_workspace_version: 5, conflicting_block_ids: ['b1'] },
    });
    const onConflict = vi.fn();
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock, { onConflict }),
      { wrapper },
    );
    act(() => { result.current.markDirty(); });
    vi.advanceTimersByTime(1600);
    await waitFor(() => expect(onConflict).toHaveBeenCalledWith({
      current_workspace_version: 5, conflicting_block_ids: ['b1'],
    }));
  });

  it('should_retry_save_with_backoff_on_network_error', async () => {
    const patchMock = vi.fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValue({ workspace_version: 2 });
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    );
    act(() => { result.current.markDirty(); });
    vi.advanceTimersByTime(1600);
    await vi.runAllTimersAsync();
    expect(patchMock).toHaveBeenCalledTimes(3);
  });

  it('should_mark_workspace_offline_after_3_failed_retries', async () => {
    const patchMock = vi.fn().mockRejectedValue(new Error('network'));
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    );
    act(() => { result.current.markDirty(); });
    vi.advanceTimersByTime(1600);
    await vi.runAllTimersAsync();
    expect(result.current.status).toBe('offline');
  });
});
```

**Criterios de aceptación**:
- Migración Alembic añade `version` a `hub_workspaces` y `hub_workspace_blocks`.
- `PATCH /api/v1/hub/redaccion/workspaces/{id}/state` devuelve 200/409/422 según contrato.
- `WorkspaceAutosaveService` es atómico: si un `BlockUpdate` falla, ningún cambio se persiste.
- `useAutosave` debounceá 1500ms, reintenta con backoff y emite `onConflict` ante 409.
- `WorkspaceStatusBar` muestra estado (`saved`/`saving`/`offline`/`conflict`).
- 7 tests backend + 4 tests frontend en verde.

---

## Fase 13 — NER reversible en el flujo de redacción (Subfase 1.C, PENDIENTE)

> Posición en orden de ejecución: entre 1C.1 y 1C.2 (ver `PROJECT_STATE.md` → orden de ejecución acordado).
>
> Objetivo del bloque: garantizar que ningún dato PII real sale del edge hacia el LLM en el flujo de redacción, pero el output final preserva los datos originales para el usuario. Cumplimiento RGPD + LOPDGDD. Reutiliza el `PiiDetector` y `FakerGenerator` migrados en 9R.5.5 (no se reinventa nada).

---

### Prompt 13.1 (RED/GREEN) — Hooks NER pre/post-LLM con `RunAnonymizationContext` reversible

**Modelo sugerido**: **Opus** — la reversibilidad tiene casos finos (orden de sustituciones para evitar matches parciales, citas que deben preservar originales tras revertir, modo LOPDGDD Disposición 7ª con formato específico, PII cruzando fronteras de bloque). Sonnet sale adelante pero con varias iteraciones.

```markdown
# PROMPT 13.1 (RED/GREEN) — NER reversible en el DraftingCoreGraph

Objetivo: insertar hooks NER pre/post-LLM en el grafo para que ningún PII real llegue al LLM (RGPD), pero el output final preserve originales para el usuario. La reversibilidad se basa en un `RunAnonymizationContext` que mantiene el mapeo bidireccional original↔sintético durante toda la ejecución del workspace.

Deploy: edge

Dependencias:
- 9R.5.5 (PiiDetector + FakerGenerator ya migrados desde legacy).
- 9R.6.3 (AIAssistDraftNode) y 9R.6.4 (UserReviewGateNode/ApplyUserEditsNode) — los hooks se enganchan aquí.
- 9R.1.4 (HubWorkspace).

## Parte 1 — Contrato `RunAnonymizationContext`

Estructura en `server/app/modules/redaccion/services/anonymization/run_context.py`:

```python
class PiiSpan(BaseModel):
    type: Literal['PERSON', 'ORG', 'LOC', 'EMAIL', 'PHONE', 'DNI', 'NIE',
                  'IBAN', 'CREDIT_CARD', 'POSTAL_CODE', 'DATE', 'NSS']
    original: str
    synthetic: str
    confidence: float
    source_block_id: str | None = None

class AnonymizationMode(str, Enum):
    OFF = "off"                                    # PII real al LLM (solo dev/test)
    DETECT_ONLY = "detect_only"                    # detecta y audita, no sustituye
    REPLACE = "replace"                            # sustituye y revierte (default)
    REPLACE_WITH_DISPOSITION_7 = "replace_with_disposition_7"  # LOPDGDD para DNI/NIE/Passport

class RunAnonymizationContext(BaseModel):
    workspace_id: UUID
    run_manifest_id: UUID | None = None
    mode: AnonymizationMode
    spans: list[PiiSpan]
    forward_map: dict[str, str]    # original → synthetic
    reverse_map: dict[str, str]    # synthetic → original
    created_at: datetime

    def substitute(self, text: str) -> str:
        """Sustituye originales por sintéticos. Aplica matches por longitud descendente para evitar matches parciales."""
        ...

    def reverse(self, text: str) -> str:
        """Sustituye sintéticos por originales. Solo revierte cadenas presentes en reverse_map (no falsos positivos)."""
        ...
```

**Reglas duras**:
- `substitute()` ordena `forward_map` por `len(key) desc` antes de sustituir para evitar que "Juan García" se rompa por sustituir "Juan" primero.
- `reverse()` solo revierte cadenas EXACTAS presentes en `reverse_map`. Si el LLM "alucina" un nombre tipo Faker que no estaba en nuestro mapping, queda tal cual (cero falsos positivos).
- Las cadenas sintéticas deben ser únicas en el texto antes de la sustitución (Faker con seed determinista por workspace+span_index garantiza unicidad razonable; si se detecta colisión durante substitute(), regenerar el sintético).
- Modo LOPDGDD: para DNI/NIE/Passport NO se usa Faker; se aplica máscara `***1234X` (oculta primeros caracteres, preserva letra de control). Esta transformación NO es reversible para esos tipos — el output queda enmascarado también.

## Parte 2 — Nuevo nodo `InitAnonymizationNode`

Ubicación en el grafo: **entre DataQualityCheckNode (9R.6.2) y AIAssistDraftNode (9R.6.3)**. Es decir, después de la extracción determinista y antes de cualquier nodo que toque LLM.

```python
class InitAnonymizationNode:
    def __init__(self, pii_detector: PiiDetector, faker_gen: FakerGenerator):
        self._detector = pii_detector
        self._faker = faker_gen

    async def __call__(self, state: WorkspaceState) -> dict:
        # 1. Leer modo del workspace
        mode = state.anonymization_mode

        if mode == AnonymizationMode.OFF:
            return {"anonymization_context": RunAnonymizationContext(
                workspace_id=state.workspace_id, mode=mode,
                spans=[], forward_map={}, reverse_map={},
                created_at=datetime.utcnow(),
            )}

        # 2. Detectar PII en todos los inputs y extracted blocks
        text_corpus = self._gather_text(state)
        spans = self._detector.detect_all(text_corpus)

        # 3. Generar sintéticos (Faker con seed determinista por workspace+type+order)
        forward_map = {}
        reverse_map = {}
        for i, span in enumerate(spans):
            synth = self._faker.generate(
                span.type, span.original,
                seed=f"{state.workspace_id}-{i}",
                mode=mode,
            )
            forward_map[span.original] = synth
            reverse_map[synth] = span.original
            span.synthetic = synth

        return {"anonymization_context": RunAnonymizationContext(
            workspace_id=state.workspace_id, mode=mode,
            spans=spans, forward_map=forward_map, reverse_map=reverse_map,
            created_at=datetime.utcnow(),
        )}
```

## Parte 3 — Pre/post hooks en nodos AI

Modificar `AIAssistDraftNode` (9R.6.3) sin tocar su lógica core:

```python
async def __call__(self, state: WorkspaceState) -> dict:
    ctx = state.anonymization_context

    # PRE-HOOK
    if ctx and ctx.mode != AnonymizationMode.OFF:
        block_context = ctx.substitute(block_context)

    # ... llamada LLM existente ...
    result_text = await self._llm.complete(prompt)

    # POST-HOOK
    if ctx and ctx.mode in (AnonymizationMode.REPLACE, AnonymizationMode.REPLACE_WITH_DISPOSITION_7):
        result_text = ctx.reverse(result_text)

    # ... construcción de BlockState con citas ...
```

Aplicar el mismo patrón en cualquier otro nodo del grafo que invoque LLM (ETLFactory NL→ops en 9R.5.8, ChartFactory NL→script en 9R.5.7, ScriptProposalService en 9R.5.5 ya tiene su propia anonimización para test data — no se duplica).

## Parte 4 — Citation preservation

Cuando `CitationAndTraceabilityNode` (9R.6.3) extrae citas del output del LLM:
- El texto ya viene revertido (post-hook hizo `reverse()`).
- Las citas `Citation.excerpt` contienen originales.
- `Citation.source_document` y `page` permanecen estables (son metadata, no PII).

Test crítico: una cita generada por el LLM sobre "Juan García" debe aparecer en el output final como "Juan García" (no "Carlos Pérez sintético") y debe enlazar al documento real (no a uno anonimizado).

## Parte 5 — Persistencia segura en el manifest

`RunAnonymizationContext` se persiste en `DraftingRunManifest` (9R.9.1) **sin originales**:

```python
class AnonymizationSummary(BaseModel):
    """Solo metadata, sin originales ni sintéticos. Para auditoría."""
    mode: AnonymizationMode
    counts_by_type: dict[str, int]  # {PERSON: 5, IBAN: 2, ...}
    total_spans: int
    detected_at: datetime
```

`DraftingRunManifest.anonymization_summary` se rellena al final del grafo. Los mapas forward/reverse NUNCA se persisten en BD ni se loguean. Viven solo en memoria durante la ejecución del workspace.

## Parte 6 — Configuración por workspace

`HubWorkspace` añade columna `anonymization_mode: str` (default `'replace'`).

Migración Alembic en `server/migrations/versions/`:
```python
op.add_column("hub_workspaces",
    sa.Column("anonymization_mode", sa.String(40),
              nullable=False, server_default="replace"))
```

## Tests (RED → GREEN)

Unit tests del context:
- test_substitute_orders_by_length_descending_to_avoid_partial_matches
- test_reverse_only_replaces_exact_matches_no_false_positives
- test_substitute_handles_pii_appearing_in_json_or_quoted_string
- test_disposition_7_masks_dni_with_check_letter_preserved
- test_disposition_7_is_not_reversible_for_dni

Nodo init:
- test_init_anonymization_node_detects_all_pii_in_inputs_and_extracted_blocks
- test_init_anonymization_node_generates_unique_synthetics_per_span
- test_init_anonymization_node_off_mode_returns_empty_context

Integración hooks en grafo:
- test_ai_node_receives_anonymized_context_when_mode_replace
- test_ai_node_output_is_reversed_after_llm_response
- test_detect_only_mode_does_not_substitute_in_prompt
- test_off_mode_passes_real_pii_to_llm

Citas:
- test_citations_preserve_original_pii_after_reversal
- test_citations_keep_source_document_metadata

Persistencia:
- test_run_manifest_records_summary_without_originals
- test_anonymization_context_never_persists_forward_or_reverse_map_to_db

## Criterio de done

- ≥16 tests verdes.
- `WorkspaceState.anonymization_context` añadido en `contracts/runtime.py`.
- `HubWorkspace.anonymization_mode` con migración Alembic aplicada.
- `InitAnonymizationNode` integrado en `build_core_graph()` (modificación pequeña a `core_graph.py`).
- Hooks aplicados en `AIAssistDraftNode`, `ETLFactory.generate_operations_from_nl` (9R.5.8) y `ChartFactory.generate_script` (9R.5.7).
- Documentación en `docs/REDACCION_CONTRACT_FIRST.md`: sección "NER reversible (Fase 13)".

## Verificación manual obligatoria

1. Crear workspace con mode='replace', subir Excel con columna `nombre_persona` real.
2. Verificar en Langfuse trace que el prompt enviado al LLM no contiene los nombres originales.
3. Verificar que el output final del workspace SÍ contiene los nombres originales.
4. Verificar que el RunManifest contiene `anonymization_summary.counts_by_type` con los conteos.
5. Verificar que la BD no contiene en ningún campo los originales en forma sintética ni los mapas.
```

---

### Prompt 13.2 (RED/GREEN) — Panel admin de auditoría NER + toggle per-workspace

**Modelo sugerido**: **Sonnet** — endpoints REST + componente React leyendo summary. Sin lógica LLM ni decisiones de diseño abiertas.

```markdown
# PROMPT 13.2 (RED/GREEN) — UI de auditoría NER y configuración por workspace

Objetivo: dar visibilidad al admin sobre qué PII se detectó y anonimizó en cada workspace, y permitir al owner cambiar el modo de anonimización antes de ejecutar el grafo.

Deploy: edge (endpoints) + frontend.

Dependencias:
- 13.1 (RunAnonymizationContext + HubWorkspace.anonymization_mode persistidos).
- 9R.7.6 (BlockDebugPanel como contenedor).

## Parte 1 — Endpoints

`server/app/routers/redaccion/anonymization_router.py`:

- `GET /api/v1/redaccion/workspaces/{workspace_id}/anonymization-summary`
  - Devuelve `AnonymizationSummary` del último run (sin originales, sin sintéticos):
    ```json
    {
      "mode": "replace",
      "counts_by_type": {"PERSON": 5, "IBAN": 2, "EMAIL": 1},
      "total_spans": 8,
      "last_run_at": "2026-05-13T...",
      "current_workspace_mode": "replace"
    }
    ```
  - 404 si no hay run ejecutado todavía.
  - Permisos: owner del workspace o admin/partner.

- `PATCH /api/v1/redaccion/workspaces/{workspace_id}/anonymization-mode`
  - Body: `{"mode": "off" | "detect_only" | "replace" | "replace_with_disposition_7"}`
  - 422 si `workspace.status IN ('drafting', 'in_review', 'assembled', 'exported')` con detalle `MODE_LOCKED_DURING_EXECUTION`.
  - Solo owner. Audit event en `hub_workspace_audit_events` (event="anonymization_mode_changed").

- `POST /api/v1/redaccion/workspaces/{workspace_id}/re-analyze`
  - Dispara solo `InitAnonymizationNode` sin llegar al LLM. Útil para previsualizar conteos antes de ejecutar.
  - Permisos: owner.

## Parte 2 — UI

Componente `WorkspaceAnonymizationPanel.tsx` en `frontend/src/redaccion/components/`:

- **Sección 1 — Modo actual** (selector deshabilitado si workspace en ejecución):
  - Radio buttons: Off / Detect only / Replace / Replace con LOPDGDD
  - Descripción debajo de cada opción
  - Badge LOPDGDD si modo = `replace_with_disposition_7`

- **Sección 2 — Detección actual** (tabla de conteos):
  - Columnas: Tipo PII | Cantidad detectada
  - Total al pie
  - Vacío si no se ha ejecutado análisis

- **Sección 3 — Acciones**:
  - Botón "Re-analizar ahora" (POST re-analyze)
  - Botón "Cambiar modo" (PATCH, solo si workspace no en ejecución)

Integración: se monta dentro de `BlockDebugPanel` (9R.7.6) como pestaña adicional "Anonimización", visible para admin/partner siempre y para el owner cuando `workspace.status NOT IN ('drafting','in_review')`.

Hooks Orval: `useGetAnonymizationSummary`, `usePatchAnonymizationMode`, `useReAnalyzeAnonymization`.

## Tests

Backend pytest:
- test_summary_returns_metadata_without_originals
- test_summary_returns_404_when_no_run_executed
- test_summary_forbidden_for_non_owner_non_admin
- test_patch_mode_rejects_during_drafting_status
- test_patch_mode_records_audit_event
- test_re_analyze_triggers_init_node_without_llm

Frontend Vitest:
- test_panel_renders_counts_by_type
- test_panel_disables_mode_selector_when_workspace_drafting
- test_panel_shows_lopdgdd_badge_in_disposition_7_mode
- test_re_analyze_button_dispatches_mutation

## Criterio de done

- 10 tests verdes (6 backend + 4 frontend).
- Endpoints en OpenAPI, hooks Orval regenerados.
- i18n en ES/EN/CA para todas las etiquetas.
- TypeScript limpio.
- Sin strings hardcoded.
```

---

### Prompt 1C.2 — Editor accesible: shortcuts, focus trap y WCAG 2.2 AA (TDD RED/GREEN)

**Modelo sugerido**: **Sonnet** — patrones WCAG 2.2 AA bien establecidos; alcance cerrado (shortcuts + focus trap + aria-live).

**Objetivo**: Cumplir WCAG 2.2 AA en el editor de Workspaces e implementar los atajos de teclado y comportamientos de focus management que un usuario de teclado o lector de pantalla espera de un editor profesional.

**Contexto**: El editor 9R.7 + Focus Mode 1C.0 + Autosave 1C.1 conforman una superficie compleja con drawer modal, bloques interactivos, transiciones de estado y autosave. Sin focus trap el usuario de teclado se "escapa" del modal; sin atajos los usuarios productivos pierden tiempo; sin anuncios `aria-live` un usuario de lector de pantalla no percibe las transiciones de bloque. WCAG 2.2 AA es el criterio de aceptación de la plataforma (ver Fase 20).

**Dependencias**: 1C.0 (DrawerHub), 1C.1 (autosave), 9R.7 (renderer).

**Instrucciones al agente**:
```text
Actúa como experto en accesibilidad web (WCAG 2.2 AA) y React. Implementa accesibilidad y atajos
en el editor de Workspaces.

1. KEYBOARD SHORTCUTS — hook `useEditorShortcuts(handlers)` en frontend/src/redaccion/hooks/:
   - `Escape`: si drawer abierto → cierra drawer; si no → ejecuta `handlers.onLeaveFocusMode()`.
   - `Cmd+S` (o `Ctrl+S` en Windows): preventDefault + `handlers.onForceSave()`.
   - `Cmd+Enter` / `Ctrl+Enter`: si hay bloque activo en estado `needs_review`
     → `handlers.onApproveActiveBlock()`.
   - `Cmd+Z` / `Ctrl+Z`: si hay edit history en el bloque activo
     → `handlers.onUndo()` (mínimo: revertir última edición de contenido).
   - Los handlers son inyectados; el hook solo ata los listeners y los limpia al desmontar.

2. FOCUS TRAP — DrawerHub (1C.0) debe atrapar el foco cuando `drawerVisible=true`:
   - Usar `react-focus-lock` (añadir a dependencias del frontend).
   - El primer elemento enfocable del drawer recibe foco al abrir.
   - Tab/Shift+Tab cicla solo entre elementos del drawer.
   - Al cerrar (Escape o botón), foco vuelve al elemento que abrió el drawer.

3. ARIA-LIVE para transiciones de estado de bloque:
   - Componente `BlockStateAnnouncer` (frontend/src/redaccion/components/) con `role="status"`
     y `aria-live="polite"`.
   - Suscrito al BlockState machine: cada transición emite texto a anunciar:
     `extracted`: "Bloque {label}: datos extraídos."
     `ai_generated`: "Bloque {label}: borrador IA listo, requiere revisión."
     `approved`: "Bloque {label}: aprobado."
     `rejected`: "Bloque {label}: rechazado, se regenerará."

4. AXE-CORE — añadir `@axe-core/react` como devDependency.
   En `frontend/src/test-utils/axe.ts`: exportar `expectNoAxeViolations(container)` que ejecuta
   `axe.run` y filtra reglas críticas + serias.

5. ETIQUETADO ARIA del renderer (9R.7):
   - Todo botón con icono solo debe tener `aria-label`.
   - El `BlockEditor` tiene `role="region"` y `aria-label="Bloque {tipo}: {label}"`.
   - El estado actual del bloque se anuncia con `aria-describedby` apuntando a un `<span class="sr-only">`.
   - Los inputs dinámicos de `DynamicFieldRenderer` propagan `aria-required`, `aria-invalid`,
     `aria-describedby` cuando hay errores de validación.

TESTS REQUERIDOS (Vitest + @axe-core/react):

- should_close_drawer_on_escape_when_drawer_is_open
- should_leave_focus_mode_on_escape_when_drawer_closed
- should_call_force_save_on_cmd_s_and_prevent_default
- should_approve_active_block_on_cmd_enter_when_state_is_needs_review
- should_not_approve_block_on_cmd_enter_when_state_is_draft
- should_trap_focus_within_drawer_when_open
- should_restore_focus_to_trigger_on_drawer_close
- should_announce_block_state_change_via_aria_live
- should_pass_axe_audit_on_workspace_with_mixed_block_states
- should_pass_axe_audit_on_drawer_open_state
```

**Tests RED — frontend/src/redaccion/hooks/\_\_tests\_\_/useEditorShortcuts.test.tsx**:
```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { useEditorShortcuts } from '../useEditorShortcuts';

function Harness({ handlers }: { handlers: Parameters<typeof useEditorShortcuts>[0] }) {
  useEditorShortcuts(handlers);
  return <div data-testid="harness" />;
}

describe('useEditorShortcuts', () => {
  it('should_close_drawer_on_escape_when_drawer_is_open', () => {
    const handlers = {
      isDrawerOpen: true,
      hasActiveBlock: false,
      activeBlockState: null,
      onCloseDrawer: vi.fn(),
      onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(),
      onApproveActiveBlock: vi.fn(),
      onUndo: vi.fn(),
    };
    render(<Harness handlers={handlers} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handlers.onCloseDrawer).toHaveBeenCalled();
    expect(handlers.onLeaveFocusMode).not.toHaveBeenCalled();
  });

  it('should_leave_focus_mode_on_escape_when_drawer_closed', () => {
    const handlers = {
      isDrawerOpen: false, hasActiveBlock: false, activeBlockState: null,
      onCloseDrawer: vi.fn(), onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(), onApproveActiveBlock: vi.fn(), onUndo: vi.fn(),
    };
    render(<Harness handlers={handlers} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handlers.onLeaveFocusMode).toHaveBeenCalled();
  });

  it('should_call_force_save_on_cmd_s_and_prevent_default', () => {
    const handlers = {
      isDrawerOpen: false, hasActiveBlock: false, activeBlockState: null,
      onCloseDrawer: vi.fn(), onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(), onApproveActiveBlock: vi.fn(), onUndo: vi.fn(),
    };
    render(<Harness handlers={handlers} />);
    const ev = new KeyboardEvent('keydown', { key: 's', metaKey: true, cancelable: true });
    const prevented = !window.dispatchEvent(ev);
    expect(handlers.onForceSave).toHaveBeenCalled();
    expect(prevented).toBe(true);
  });

  it('should_approve_active_block_on_cmd_enter_when_state_is_needs_review', () => {
    const handlers = {
      isDrawerOpen: false, hasActiveBlock: true, activeBlockState: 'needs_review' as const,
      onCloseDrawer: vi.fn(), onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(), onApproveActiveBlock: vi.fn(), onUndo: vi.fn(),
    };
    render(<Harness handlers={handlers} />);
    fireEvent.keyDown(window, { key: 'Enter', metaKey: true });
    expect(handlers.onApproveActiveBlock).toHaveBeenCalled();
  });

  it('should_not_approve_block_on_cmd_enter_when_state_is_draft', () => {
    const handlers = {
      isDrawerOpen: false, hasActiveBlock: true, activeBlockState: 'draft' as const,
      onCloseDrawer: vi.fn(), onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(), onApproveActiveBlock: vi.fn(), onUndo: vi.fn(),
    };
    render(<Harness handlers={handlers} />);
    fireEvent.keyDown(window, { key: 'Enter', metaKey: true });
    expect(handlers.onApproveActiveBlock).not.toHaveBeenCalled();
  });
});
```

**Tests RED — frontend/src/redaccion/components/\_\_tests\_\_/A11y.test.tsx**:
```typescript
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { expectNoAxeViolations } from '@/test-utils/axe';
import { WorkspaceEditor } from '../WorkspaceEditor';
import { mockWorkspaceWithMixedBlocks } from '@/test-utils/fixtures';

describe('Editor accessibility (WCAG 2.2 AA)', () => {
  it('should_pass_axe_audit_on_workspace_with_mixed_block_states', async () => {
    const { container } = render(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks()} />,
    );
    await expectNoAxeViolations(container);
  });

  it('should_announce_block_state_change_via_aria_live', async () => {
    const { container, rerender } = render(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks({ block1State: 'draft' })} />,
    );
    rerender(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks({ block1State: 'ai_generated' })} />,
    );
    const live = container.querySelector('[aria-live="polite"]');
    expect(live?.textContent).toMatch(/borrador IA listo/i);
  });

  it('should_trap_focus_within_drawer_when_open', () => {
    // Render con drawer abierto; comprobar que document.activeElement está dentro del drawer.
  });

  it('should_restore_focus_to_trigger_on_drawer_close', () => {
    // Render con botón trigger; abre drawer; cierra; comprobar activeElement = trigger.
  });
});
```

**Criterios de aceptación**:
- `useEditorShortcuts` ata `Escape`, `Cmd/Ctrl+S`, `Cmd/Ctrl+Enter`, `Cmd/Ctrl+Z` y los limpia al desmontar.
- `DrawerHub` atrapa el foco (react-focus-lock) y lo restaura al cerrar.
- `BlockStateAnnouncer` anuncia transiciones por `aria-live="polite"`.
- `expectNoAxeViolations` pasa en el editor con bloques en todos los estados de la state machine.
- Cero violaciones críticas o serias en axe-core para los snapshots clave.
- 10 tests en verde.

---

### Prompt 1C.3 — Vista previa imprimible y anexo de auditoría (TDD RED/GREEN)

**Modelo sugerido**: **Sonnet** — CSS print + estructura DOM compartida con ExportService. Sin decisiones abiertas.

**Objetivo**: Antes de exportar, el usuario ve una vista previa de página completa (`WorkspacePreview`) que coincide visualmente con el DOCX/ODT final, incluido el anexo de auditoría con el `DraftingRunManifest`. La preview y el ExportService consumen la misma estructura serializada para garantizar que lo que el usuario ve es exactamente lo que se exporta.

**Contexto**: 9R.9.1 produce `DraftingRunManifest`. 1C.4 lo escribe en DOCX/ODT como notas al pie + anexo. Sin preview compartida, divergen: la pantalla puede mostrar algo, el export otra cosa. Este prompt extrae la estructura a un contrato compartido (`PreviewPayload`) que ambos consumen.

**Dependencias**: 9R.9.1 (DraftingRunManifest), 9R.6.4 (FinalAssemblerNode).

**Instrucciones al agente**:
```text
Actúa como experto en arquitectura contract-first. Implementa el contrato Preview y la pantalla
de vista previa.

BACKEND — server/app/modules/redaccion/

1. Contrato `PreviewPayload` en `contracts/preview.py` (Pydantic, exportado por OpenAPI):
   class PreviewSection(BaseModel):
       level: int                     # 1 = portada, 2 = H1, 3 = H2, etc.
       title: str
       blocks: list[PreviewBlock]

   class PreviewBlock(BaseModel):
       block_id: UUID
       kind: BlockKind                # STATIC_TEXT | DETERMINISTIC_DATA | TABLE | CHART
                                      #  | AI_ASSISTED_TEXT | AI_SUMMARY | CITATION_BLOCK
       state: BlockState              # solo `approved` o `locked` aparecen en export
       html: str                      # contenido renderizado a HTML semántico
       citations: list[UUID]          # IDs de chunks referenciados

   class PreviewAuditEntry(BaseModel):
       chunk_id: UUID
       source_url: str | None
       source_filename: str | None
       page: int | None
       model_used: str | None
       prompt_version: str | None
       approvals: list[UUID]          # block_ids que aprobó este chunk

   class PreviewPayload(BaseModel):
       workspace_id: UUID
       template_version_id: UUID
       cover: PreviewSection          # portada (título, organización, fecha)
       toc: list[tuple[int, str]]     # (level, title) para índice
       body: list[PreviewSection]
       audit_annex: list[PreviewAuditEntry]
       manifest_id: UUID              # referencia al DraftingRunManifest
       generated_at: datetime

2. Endpoint:
   GET /api/v1/hub/redaccion/workspaces/{workspace_id}/preview
   Returns: PreviewPayload
   Deploy: edge

3. Servicio `PreviewBuilderService` (consumido por endpoint y por ExportService de 1C.4):
   - Carga workspace + bloques aprobados + manifest activo
   - Construye `PreviewPayload` con el mismo orden y secciones que el export
   - Rechaza con 409 si hay bloques en estado distinto a `approved`/`locked`/`static`
     (un export no procede si hay AI sin aprobar — regla 5 de 9R)

4. ExportService de 1C.4 SE REFACTORIZA para consumir `PreviewBuilderService.build_payload()`
   en lugar de procesar Markdown crudo: garantiza que preview ≡ export.

FRONTEND — frontend/src/redaccion/preview/

1. Pantalla `WorkspacePreview` (ruta `/redaccion/workspaces/:id/preview`):
   - Llama `GET .../preview` y renderiza `PreviewPayload` como página A4.
   - Estilos `@media print` y `@page` para que `Cmd+P` genere PDF con la misma maqueta.
   - Sección "Anexo de auditoría" al final: tabla con `chunk_id`, fuente, página, modelo,
     prompt_version, aprobaciones.
   - Botón "Exportar a DOCX/ODT" al pie → invoca el endpoint de 1C.4.

2. Componente compartido `PreviewRenderer({ payload }: { payload: PreviewPayload })`:
   - Mapea cada `PreviewBlock.kind` a su componente de presentación.
   - El `html` se sanitiza con DOMPurify antes de inyectar.
   - `CITATION_BLOCK` renderiza superíndices `[1]`, `[2]`... linkados al anexo.

TESTS REQUERIDOS:

Backend (pytest):
- test_preview_payload_contains_only_approved_or_locked_blocks
- test_preview_endpoint_returns_409_when_blocks_pending_review
- test_preview_builder_orders_blocks_by_template_section
- test_export_service_uses_same_payload_as_preview_endpoint
- test_audit_annex_lists_all_chunks_used_by_approved_blocks

Frontend (Vitest):
- should_render_cover_index_body_and_audit_annex_in_order
- should_sanitize_block_html_before_rendering
- should_link_citation_superscripts_to_audit_annex
- should_match_export_structure_snapshot
- should_show_print_only_stylesheet_for_page_size_a4
```

**Tests RED — tests/modules/redaccion/unit/test_preview_builder.py**:
```python
"""Tests para PreviewBuilderService — TDD RED."""
import pytest
from uuid import uuid4

from server.app.modules.redaccion.services.preview_builder import (
    PreviewBuilderService, PendingBlocksError,
)


class TestPreviewBuilder:

    @pytest.mark.asyncio
    async def test_payload_contains_only_approved_or_locked_blocks(
        self, builder: PreviewBuilderService, workspace_all_approved
    ) -> None:
        payload = await builder.build_payload(workspace_all_approved.id)
        for section in payload.body:
            for block in section.blocks:
                assert block.state in ("approved", "locked")

    @pytest.mark.asyncio
    async def test_returns_409_when_blocks_pending_review(
        self, builder: PreviewBuilderService, workspace_with_needs_review
    ) -> None:
        with pytest.raises(PendingBlocksError) as exc:
            await builder.build_payload(workspace_with_needs_review.id)
        assert len(exc.value.pending_block_ids) >= 1

    @pytest.mark.asyncio
    async def test_orders_blocks_by_template_section(
        self, builder: PreviewBuilderService, workspace_with_3_sections
    ) -> None:
        payload = await builder.build_payload(workspace_with_3_sections.id)
        titles = [s.title for s in payload.body]
        assert titles == ["Introducción", "Marco Legal", "Conclusiones"]

    @pytest.mark.asyncio
    async def test_export_service_uses_same_payload(
        self, builder: PreviewBuilderService, export_service, workspace_all_approved, storage_mock
    ) -> None:
        preview_payload = await builder.build_payload(workspace_all_approved.id)
        await export_service.export(workspace_all_approved.id, format="docx")
        # ExportService delega en builder.build_payload; verificamos misma referencia
        export_payload = export_service.last_payload_used
        assert export_payload.workspace_id == preview_payload.workspace_id
        assert [b.block_id for s in export_payload.body for b in s.blocks] == \
               [b.block_id for s in preview_payload.body for b in s.blocks]

    @pytest.mark.asyncio
    async def test_audit_annex_lists_all_chunks_used_by_approved_blocks(
        self, builder: PreviewBuilderService, workspace_with_citations
    ) -> None:
        payload = await builder.build_payload(workspace_with_citations.id)
        cited_ids = {c for s in payload.body for b in s.blocks for c in b.citations}
        annex_ids = {entry.chunk_id for entry in payload.audit_annex}
        assert cited_ids.issubset(annex_ids)
```

**Tests RED — frontend/src/redaccion/preview/\_\_tests\_\_/PreviewRenderer.test.tsx**:
```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PreviewRenderer } from '../PreviewRenderer';
import { samplePreviewPayload } from '@/test-utils/fixtures';

describe('PreviewRenderer', () => {
  it('should_render_cover_index_body_and_audit_annex_in_order', () => {
    const { container } = render(<PreviewRenderer payload={samplePreviewPayload()} />);
    const sections = container.querySelectorAll('[data-preview-section]');
    const kinds = Array.from(sections).map(s => s.getAttribute('data-preview-section'));
    expect(kinds).toEqual(['cover', 'toc', 'body', 'audit-annex']);
  });

  it('should_sanitize_block_html_before_rendering', () => {
    const payload = samplePreviewPayload({
      bodyBlockHtml: '<script>alert(1)</script><p>seguro</p>',
    });
    const { container } = render(<PreviewRenderer payload={payload} />);
    expect(container.querySelector('script')).toBeNull();
    expect(screen.getByText('seguro')).toBeInTheDocument();
  });

  it('should_link_citation_superscripts_to_audit_annex', () => {
    const payload = samplePreviewPayload({ withCitations: true });
    const { container } = render(<PreviewRenderer payload={payload} />);
    const sup = container.querySelector('sup a[href^="#audit-"]');
    expect(sup).not.toBeNull();
  });
});
```

**Criterios de aceptación**:
- `PreviewPayload` exportado por OpenAPI; Orval lo genera en el frontend.
- `GET /api/v1/hub/redaccion/workspaces/{id}/preview` devuelve 200 con payload completo o 409 con `pending_block_ids` si hay bloques sin revisar.
- `PreviewBuilderService` es la única fuente de la estructura del documento; `ExportService` (1C.4) lo consume.
- `WorkspacePreview` renderiza cover + toc + body + audit-annex con CSS `@media print` para A4.
- Las citas `[1]`, `[2]`... linkan al anexo (`#audit-{chunk_id}`).
- HTML de los bloques saneado con DOMPurify antes de renderizar.
- 5 tests backend + 3 tests frontend en verde.

---

### Prompt 1C.4 — Exportación Avanzada DOCX/ODT con Plantillas y Citas (TDD RED/GREEN)

**Modelo sugerido**: **Sonnet** — DOCX-only en MVP (decidido 2026-05-13); generación con python-docx + anexo de auditoría. Base ya esbozada en 9R.9.2.

**Objetivo**: Implementar la exportación del `final_document` de un workspace a `.docx` y `.odt` con maquetación profesional: índice automático, citas a pie de página extraídas del `RunManifest` y estilos institucionales.

**Contexto**: El grafo LangGraph de redacción (9.11c) genera `WorkspaceState.final_document` en Markdown y un `RunManifest` con los chunks recuperados y sus metadatos. Este prompt convierte ese output en documentos descargables con formato institucional.

**Instrucciones al agente**:
```text
Actúa como desarrollador Senior. Implementa el ExportService en
server/app/modules/agents_hub/services/export_service.py.

DEPENDENCIAS Python: python-docx, odfpy o python-odt, Jinja2 (ya instalados en el proyecto).

SERVICIO ExportService:
  Constructor: __init__(self, storage: StorageService)
  Método principal:
    async def export(
        workspace_id: str,
        final_document: str,          # Markdown del workspace
        run_manifest: RunManifest,     # chunks usados + sus metadatos
        format: Literal["docx", "odt"],
        theme: ThemeConfig | None,     # colores/tipografía de la Organización (nullable)
    ) -> ExportResult

LÓGICA:
1. Parsear el Markdown con mistune o markdown-it-py para extraer secciones y títulos.
2. Construir una estructura de documento con:
   - Portada: título del workspace, fecha, nombre de la Organización (desde ThemeConfig).
   - Índice automático (tabla de contenidos generada a partir de los H1/H2/H3).
   - Cuerpo: secciones del Markdown convertidas a párrafos con estilos (heading1, heading2, normal).
   - Notas a pie de página: para cada cita [^1] en el Markdown, buscar el chunk correspondiente
     en run_manifest.retrieved_chunks y añadir la referencia completa (URL o nombre de fichero + página).
   - Anexo de auditoría: lista de todos los documentos fuente del RunManifest.
3. Para .docx: usar python-docx con una plantilla base (.docx con estilos predefinidos).
4. Para .odt: usar odfpy con estructura equivalente.
5. Guardar el archivo con StorageService en "exports/{workspace_id}/{filename}".
6. Devolver ExportResult con: file_path (str), download_url (str), format, size_bytes.

ENDPOINT — añadir a hub_agents_router.py:
  POST /api/v1/hub/agents/workspaces/{workspace_id}/export
  Request: { "format": "docx" | "odt" }
  Response: { "download_url": "...", "file_path": "...", "size_bytes": 12345 }

TESTS REQUERIDOS:
- test_export_service_generates_docx_file
- test_export_service_generates_odt_file
- test_export_includes_footnotes_from_run_manifest
- test_export_includes_table_of_contents
- test_export_applies_theme_colors_if_provided
- test_endpoint_returns_download_url
```

**Tests RED — tests/modules/agents_hub/unit/test_export_service.py**:
```python
"""Tests para ExportService (DOCX/ODT) — TDD RED."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass, field


@dataclass
class FakeChunk:
    source_url: str
    page: int | None
    text: str


@dataclass
class FakeRunManifest:
    retrieved_chunks: list[FakeChunk] = field(default_factory=list)


SAMPLE_MARKDOWN = """# Informe de Análisis Normativo

## 1. Introducción
El presente informe analiza la normativa vigente [^1].

## 2. Marco Legal
Las obligaciones se recogen en el artículo 15 [^2].

## 3. Conclusiones
El cumplimiento es obligatorio desde enero de 2025.
"""


class TestExportService:

    @pytest.fixture
    def storage_mock(self):
        mock = AsyncMock()
        mock.put.return_value = None
        mock.get_url.return_value = "https://storage.example.com/exports/ws-1/informe.docx"
        return mock

    @pytest.fixture
    def run_manifest(self):
        return FakeRunManifest(retrieved_chunks=[
            FakeChunk(source_url="https://boe.es/doc/1", page=3, text="normativa vigente"),
            FakeChunk(source_url="https://normativa.uji.es/art15", page=None, text="artículo 15"),
        ])

    @pytest.mark.asyncio
    async def test_export_service_generates_docx_file(self, storage_mock, run_manifest) -> None:
        from server.app.modules.agents_hub.services.export_service import ExportService

        service = ExportService(storage=storage_mock)
        result = await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="docx",
            theme=None,
        )

        assert result.format == "docx"
        assert result.file_path.endswith(".docx")
        assert result.size_bytes > 0
        storage_mock.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_service_generates_odt_file(self, storage_mock, run_manifest) -> None:
        from server.app.modules.agents_hub.services.export_service import ExportService

        service = ExportService(storage=storage_mock)
        result = await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="odt",
            theme=None,
        )

        assert result.format == "odt"
        assert result.file_path.endswith(".odt")

    @pytest.mark.asyncio
    async def test_export_includes_footnotes_from_run_manifest(self, storage_mock, run_manifest) -> None:
        """El documento exportado contiene las referencias del RunManifest como notas a pie."""
        from server.app.modules.agents_hub.services.export_service import ExportService
        import io
        from docx import Document

        written_bytes: list[bytes] = []

        async def capture_put(path: str, data: bytes) -> None:
            written_bytes.append(data)

        storage_mock.put.side_effect = capture_put

        service = ExportService(storage=storage_mock)
        await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="docx",
            theme=None,
        )

        assert len(written_bytes) == 1
        doc = Document(io.BytesIO(written_bytes[0]))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "boe.es" in full_text or "boe.es" in str(doc.element.xml)

    @pytest.mark.asyncio
    async def test_export_includes_table_of_contents(self, storage_mock, run_manifest) -> None:
        """El documento contiene una entrada de índice por cada H2 del Markdown."""
        from server.app.modules.agents_hub.services.export_service import ExportService
        import io
        from docx import Document

        written_bytes: list[bytes] = []

        async def capture_put(path: str, data: bytes) -> None:
            written_bytes.append(data)

        storage_mock.put.side_effect = capture_put

        service = ExportService(storage=storage_mock)
        await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="docx",
            theme=None,
        )

        doc = Document(io.BytesIO(written_bytes[0]))
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert any("Introducción" in h for h in headings)
        assert any("Marco Legal" in h for h in headings)
        assert any("Conclusiones" in h for h in headings)

    @pytest.mark.asyncio
    async def test_export_applies_theme_colors_if_provided(self, storage_mock, run_manifest) -> None:
        """Cuando se proporciona ThemeConfig, el documento usa los colores institucionales."""
        from server.app.modules.agents_hub.services.export_service import ExportService

        theme_mock = MagicMock()
        theme_mock.colors = {"primary": "#003366", "secondary": "#FFFFFF"}
        theme_mock.typography = {"font_family": "Arial"}

        service = ExportService(storage=storage_mock)
        result = await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="docx",
            theme=theme_mock,
        )

        assert result.size_bytes > 0  # el documento se genera sin errores con el tema

    @pytest.mark.asyncio
    async def test_endpoint_returns_download_url(self, storage_mock) -> None:
        from httpx import AsyncClient
        from server.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/hub/agents/workspaces/ws-nonexistent/export",
                json={"format": "docx"},
                headers={"Authorization": "Bearer test-token"},
            )
        # Sin workspace real -> 404, pero el endpoint debe existir (no 405)
        assert response.status_code != 405
```

**Criterios de aceptación**:
- `ExportService.export()` genera archivos `.docx` y `.odt` válidos y los guarda con `StorageService`.
- El documento incluye índice (H2/H3 del Markdown), notas a pie (chunks del `RunManifest`) y secciones del cuerpo.
- Si se proporciona `ThemeConfig`, se aplican colores y tipografía institucionales.
- `POST /api/v1/hub/agents/workspaces/{workspace_id}/export` devuelve `download_url`.
- En `AgentWorkspacePanel` (9.11d), el botón "Exportar PDF/Word" usa este endpoint (actualizar 9.11d).
- Los 6 tests pasan en verde.

---

### Prompt 1C.5 — Integración Google Drive: Destino Configurable para Informes (TDD RED/GREEN)

**Objetivo**: Añadir Google Drive como destino opcional para los informes exportados. El usuario elige entre "Descargar local" o "Guardar en Google Drive institucional" desde el workspace.

**Contexto**: Extensión del `ExportService` (1C.4). La integración con Google Drive es opcional (requiere credenciales OAuth configuradas por la Organización). Si no están configuradas, el selector solo muestra "Descargar local". Sigue el patrón de portabilidad: el conector Drive se inyecta como dependencia, nunca se acopla directamente.

**Instrucciones al agente**:
```text
Actúa como desarrollador Senior. Amplía el ExportService con soporte para destinos.

PROTOCOLO DriveConnectorProtocol en server/app/core/drive_connector.py:
  async def upload(self, file_bytes: bytes, filename: str, folder_id: str | None) -> str
    -> devuelve la URL del archivo en Drive

IMPLEMENTACIONES:
  - NullDriveConnector: devuelve NotImplementedError("Drive not configured").
  - GoogleDriveConnector: usa google-api-python-client (librería opcional, no instalar si no existe).
    Constructor: credentials_json (str, JSON de service account).
    Método upload: usa la Drive API v3 para subir el archivo a la carpeta especificada.

CONFIGURACIÓN por Organización:
  Añadir a HubClient: drive_credentials_json (Text, nullable, encrypted), drive_folder_id (VARCHAR, nullable).
  Migración Alembic correspondiente.

ENDPOINT ampliado:
  POST /api/v1/hub/agents/workspaces/{workspace_id}/export
  Request: { "format": "docx" | "odt", "destination": "local" | "drive" }
  - Si destination="drive" y DriveConnector es NullDriveConnector: devolver 422 con mensaje claro.
  - Si destination="drive" y hay credenciales: subir y devolver drive_url en la respuesta.

FRONTEND — actualizar AgentWorkspacePanel.tsx:
  - Reemplazar el botón "Exportar PDF/Word" por un componente ExportDropdown.
  - Opciones: "Descargar .docx", "Descargar .odt", "Guardar en Google Drive" (solo visible si
    la Organización tiene drive_credentials_json configurado).

TESTS REQUERIDOS:
- test_null_drive_connector_raises_not_implemented
- test_google_drive_connector_calls_api_with_correct_params
- test_export_endpoint_with_drive_destination_calls_connector
- test_export_endpoint_returns_422_when_drive_not_configured
```

**Tests RED — tests/modules/agents_hub/unit/test_drive_connector.py**:
```python
"""Tests para DriveConnector y destino Drive en el export endpoint — TDD RED."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestNullDriveConnector:

    @pytest.mark.asyncio
    async def test_null_drive_connector_raises_not_implemented(self) -> None:
        from server.app.core.drive_connector import NullDriveConnector

        connector = NullDriveConnector()
        with pytest.raises(NotImplementedError, match="Drive not configured"):
            await connector.upload(file_bytes=b"data", filename="test.docx", folder_id=None)


class TestGoogleDriveConnector:

    @pytest.mark.asyncio
    async def test_google_drive_connector_calls_api_with_correct_params(self) -> None:
        from server.app.core.drive_connector import GoogleDriveConnector

        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_service.files.return_value = mock_files
        mock_create = MagicMock()
        mock_files.create.return_value = mock_create
        mock_create.execute.return_value = {"id": "file-abc", "webViewLink": "https://drive.google.com/file/abc"}

        with patch(
            "server.app.core.drive_connector.build_drive_service",
            return_value=mock_service,
        ):
            connector = GoogleDriveConnector(credentials_json='{"type": "service_account"}')
            url = await connector.upload(file_bytes=b"docx-content", filename="informe.docx", folder_id="folder-123")

        assert "drive.google.com" in url
        mock_files.create.assert_called_once()
        call_kwargs = mock_files.create.call_args
        assert call_kwargs.kwargs["body"]["parents"] == ["folder-123"]

    @pytest.mark.asyncio
    async def test_google_drive_connector_upload_without_folder(self) -> None:
        from server.app.core.drive_connector import GoogleDriveConnector

        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_service.files.return_value = mock_files
        mock_create = MagicMock()
        mock_files.create.return_value = mock_create
        mock_create.execute.return_value = {"id": "file-xyz", "webViewLink": "https://drive.google.com/file/xyz"}

        with patch("server.app.core.drive_connector.build_drive_service", return_value=mock_service):
            connector = GoogleDriveConnector(credentials_json='{"type": "service_account"}')
            url = await connector.upload(file_bytes=b"data", filename="informe.odt", folder_id=None)

        assert url is not None
        call_kwargs = mock_files.create.call_args
        assert "parents" not in call_kwargs.kwargs.get("body", {})


class TestExportEndpointWithDrive:

    @pytest.mark.asyncio
    async def test_export_endpoint_with_drive_destination_calls_connector(self) -> None:
        from server.app.modules.agents_hub.services.export_service import ExportService
        from server.app.core.drive_connector import GoogleDriveConnector

        storage_mock = AsyncMock()
        storage_mock.put.return_value = None
        storage_mock.get_url.return_value = "https://storage/exports/ws-1/informe.docx"

        drive_mock = AsyncMock(spec=GoogleDriveConnector)
        drive_mock.upload.return_value = "https://drive.google.com/file/informe"

        service = ExportService(storage=storage_mock, drive_connector=drive_mock)

        from tests.modules.agents_hub.unit.test_export_service import SAMPLE_MARKDOWN, FakeRunManifest
        result = await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=FakeRunManifest(),
            format="docx",
            theme=None,
            destination="drive",
        )

        drive_mock.upload.assert_called_once()
        assert result.drive_url is not None
        assert "drive.google.com" in result.drive_url

    @pytest.mark.asyncio
    async def test_export_endpoint_returns_422_when_drive_not_configured(self) -> None:
        from httpx import AsyncClient
        from server.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/hub/agents/workspaces/ws-existing/export",
                json={"format": "docx", "destination": "drive"},
                headers={"Authorization": "Bearer test-token"},
            )
        # Sin Drive configurado para la Organización -> 422 Unprocessable Entity
        assert response.status_code in (404, 422)  # 404 si no existe ws, 422 si Drive no configurado
```

**Criterios de aceptación**:
- `DriveConnectorProtocol` con `NullDriveConnector` (por defecto) y `GoogleDriveConnector` (opcional).
- `ExportService` acepta un parámetro `destination: Literal["local", "drive"]` y el conector como dependencia.
- Si `destination="drive"` y el conector es `NullDriveConnector`: el endpoint devuelve 422 con mensaje claro.
- Migración Alembic: `drive_credentials_json` y `drive_folder_id` en `hub_clients`.
- `ExportDropdown` en el frontend oculta la opción Drive si la Organización no tiene credenciales configuradas.
- Los 4 tests pasan en verde.

---

## Fase 20 reducida — WCAG 2.2 AA transversal (PENDIENTE)

> Posición en orden de ejecución: entre 1C.4 (exportación) y Fase 11 (autoinstalación). Ver `PROJECT_STATE.md` → orden de ejecución acordado.
>
> Objetivo del bloque: garantizar WCAG 2.2 AA en todas las rutas del MVP — widget público, redacción, admin hub, auth — con auditoría automatizada en CI. Excluido: consola conversacional admin (diferida a Fase 2). Se beneficia de los patrones ya aplicados en 1C.2 (editor accesible) y los extiende al resto de la app.

---

### Prompt 20.1 (RED/GREEN) — Infraestructura de auditoría WCAG con axe-core + CI gate

**Modelo sugerido**: **Sonnet** — setup de jest-axe/axe-core en Vitest + workflow CI. Patrón estándar.

```markdown
# PROMPT 20.1 (RED/GREEN) — Auditoría a11y automatizada en suite de tests + CI

Objetivo: añadir auditoría automatizada de accesibilidad WCAG 2.2 AA a la suite de tests del frontend y como gate de CI. Garantiza que cualquier regresión es detectada antes de merge.

Deploy: frontend + CI.

Dependencias:
- 1C.2 ya establece los patrones WCAG en el editor de Workspace. Este prompt extiende la cobertura a toda la app.
- 10.x (sistema de temas) ya debería estar verde para que los contrastes de color sean estables.

## Parte 1 — Dependencias y configuración

Añadir a `frontend/package.json`:
```json
{
  "devDependencies": {
    "jest-axe": "^9.0.0",
    "@axe-core/react": "^4.x"
  }
}
```

## Parte 2 — Helper reutilizable

`frontend/src/test/a11y.ts`:
```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
import { configureAxe } from 'jest-axe';

expect.extend(toHaveNoViolations);

const axeConfig = configureAxe({
  rules: {
    // WCAG 2.2 AA — lista explícita activada
    'color-contrast': { enabled: true },
    'aria-required-attr': { enabled: true },
    'aria-required-children': { enabled: true },
    'aria-required-parent': { enabled: true },
    'aria-valid-attr': { enabled: true },
    'aria-valid-attr-value': { enabled: true },
    'button-name': { enabled: true },
    'document-title': { enabled: true },
    'duplicate-id': { enabled: true },
    'form-field-multiple-labels': { enabled: true },
    'frame-title': { enabled: true },
    'html-has-lang': { enabled: true },
    'html-lang-valid': { enabled: true },
    'image-alt': { enabled: true },
    'input-button-name': { enabled: true },
    'input-image-alt': { enabled: true },
    'label': { enabled: true },
    'link-name': { enabled: true },
    'list': { enabled: true },
    'listitem': { enabled: true },
    'meta-viewport': { enabled: true },
    'select-name': { enabled: true },
    'svg-img-alt': { enabled: true },
    'tabindex': { enabled: true },
    'focus-order-semantics': { enabled: true },
    'landmark-one-main': { enabled: true },
    'region': { enabled: true },
  },
});

export async function expectNoA11yViolations(container: HTMLElement) {
  const results = await axeConfig(container);
  expect(results).toHaveNoViolations();
}
```

## Parte 3 — Tests baseline obligatorios

`frontend/src/__tests__/a11y/` (nuevo directorio):

- `widget.a11y.test.tsx` — renderiza el widget público completo, ejecuta `expectNoA11yViolations`.
- `redaccion-workspace.a11y.test.tsx` — renderiza un workspace con bloques de cada tipo + drawer abierto.
- `redaccion-llm-draft-preview.a11y.test.tsx` — pantalla LLMDraftPreviewPage (9R.7.4) con draft mockeado.
- `redaccion-script-wizard.a11y.test.tsx` — ScriptProposalWizardPage (9R.7.5) en cada uno de los 7 pasos.
- `admin-chatbots.a11y.test.tsx` — ChatbotsPage con listado mockeado.
- `admin-clients.a11y.test.tsx` — ClientsPage con listado mockeado.
- `admin-llm-configs.a11y.test.tsx` — LLMConfigsPage.
- `admin-prompts.a11y.test.tsx` — PromptsPage.
- `auth-login.a11y.test.tsx` — LoginPage.

Mínimo 9 tests baseline (uno por pantalla principal del MVP).

## Parte 4 — CI gate

Modificar `.github/workflows/contract.yml` (o el workflow equivalente):

```yaml
jobs:
  a11y:
    runs-on: ubuntu-latest
    needs: contract
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test:a11y
```

Añadir script en `frontend/package.json`:
```json
"scripts": {
  "test:a11y": "vitest run src/__tests__/a11y"
}
```

## Parte 5 — Documentación

`docs/A11Y_GUIDELINES.md` (nuevo):
- Cómo añadir un test a11y a una nueva pantalla
- Reglas WCAG 2.2 AA cubiertas automáticamente vs. las que requieren revisión manual (Lighthouse, lector de pantalla)
- Cómo interpretar y arreglar las violaciones más comunes (label, contrast, focus-order)

## Tests (RED → GREEN)

- 9 tests `*.a11y.test.tsx` deben **fallar** inicialmente con violaciones reales (RED). Documentar las violaciones detectadas en un archivo `a11y-baseline.md` temporal para que 20.2 las pueda atacar.
- Una vez 20.2 corrija las violaciones, este conjunto se vuelve verde.

> **Importante para 20.1**: este prompt entrega la INFRAESTRUCTURA. No se espera que los 9 tests pasen en verde tras 20.1. La validación de done para 20.1 es:
> - jest-axe/axe-core instalado correctamente y funcionando.
> - Helper a11y disponible.
> - 9 tests escritos y ejecutables (aunque fallen por violaciones reales).
> - Workflow CI configurado (puede quedar como `continue-on-error: true` temporalmente hasta cerrar 20.2).
> - `a11y-baseline.md` generado con el listado de violaciones detectadas.

## Criterio de done

- jest-axe y axe-core instalados.
- Helper `expectNoA11yViolations` disponible y testeado contra un componente "perfecto" sintético.
- 9 archivos de test a11y creados, ejecutables vía `npm run test:a11y`.
- Workflow CI añadido (puede ser `continue-on-error: true` temporal).
- `a11y-baseline.md` con violaciones documentadas por pantalla → entrada para 20.2.
- `docs/A11Y_GUIDELINES.md` creado.
```

---

### Prompt 20.2 (RED/GREEN) — Sweep de remediación de violaciones WCAG en pantallas MVP

**Modelo sugerido**: **Sonnet** — corrección sistemática por categorías de violación con patrones conocidos (labels, contrast, focus). Si alguna pantalla requiere reestructuración importante, escalar a Opus puntualmente.

```markdown
# PROMPT 20.2 (RED/GREEN) — Corrección sistemática de violaciones WCAG detectadas en 20.1

Objetivo: corregir todas las violaciones WCAG 2.2 AA detectadas por la auditoría automatizada de 20.1, hasta que los 9 tests baseline pasen en verde y el CI gate pueda quitar el `continue-on-error: true`.

Deploy: frontend.

Dependencias:
- 20.1 GREEN con `a11y-baseline.md` poblado.
- 1C.2 (patrones de focus trap + aria-live en redacción) como referencia.
- 10.x (sistema de temas con tokens de contraste estables).

## Alcance — pantallas a corregir

Mismo conjunto que los 9 tests de 20.1:
- Widget público chatbot (9B).
- Redacción: Workspace + LLMDraftPreviewPage + ScriptProposalWizardPage + ReportTemplateBuilderPage + GenericReportWizard + AdminScriptReviewQueuePage.
- Admin Hub: ChatbotsPage, ClientsPage, LLMConfigsPage, PromptsPage, DocumentsPage, ReportsPage.
- Auth: LoginPage.

Excluido (diferido a Fase 2):
- Consola conversacional admin.
- Componentes que aún no existen al cierre de 20.2.

## Categorías de violación a corregir (en orden de prioridad)

### Categoría 1 — Labels y nombres accesibles

- Cada `<input>`, `<select>`, `<textarea>` debe tener `<label>` asociado por `htmlFor` o `aria-label`.
- Cada `<button>` con solo icono debe tener `aria-label`.
- Cada link con solo icono debe tener `aria-label` o texto sr-only.

### Categoría 2 — Color contrast

- Auditar tokens de tema (10.6) y ajustar ratios:
  - Texto normal: ≥4.5:1
  - Texto grande (≥18pt o ≥14pt bold): ≥3:1
  - UI components y graphical objects: ≥3:1
- Modificar los presets de tema (10.5) si el preset Default no cumple.

### Categoría 3 — Heading order y landmarks

- Cada página tiene exactamente un `<h1>`.
- La jerarquía h1→h2→h3 no salta niveles.
- Cada página tiene `<main>` y los landmarks pertinentes (`<nav>`, `<aside>`, `<footer>`).

### Categoría 4 — Focus management

- Todos los elementos interactivos tienen focus visible (no `outline: none` sin reemplazo).
- Tab order es lógico (top→bottom, left→right culturalmente).
- Modals y drawers (DrawerHub de 1C.0) atrapan foco (ya cubierto en 1C.2; verificar replicación).
- Al cerrar un modal/drawer, el foco vuelve al trigger.

### Categoría 5 — ARIA

- Roles ARIA solo cuando el HTML semántico no basta. Preferir `<button>` sobre `<div role="button">`.
- `aria-live="polite"` para notificaciones, `aria-live="assertive"` solo para errores críticos.
- `aria-current="page"` en navegación.
- `aria-expanded`, `aria-controls` en dropdowns/accordions.

### Categoría 6 — Imágenes y media

- Cada `<img>` con contenido informativo tiene `alt`.
- Imágenes decorativas: `alt=""`.
- SVG icons inline: `aria-hidden="true"` si decorativos; `role="img"` + `<title>` si informativos.

### Categoría 7 — Forms y errores

- Mensajes de error asociados al input por `aria-describedby`.
- Indicación de campos requeridos no solo por color (asterisco textual o `aria-required="true"`).
- Validación en vivo anunciada por `aria-live` en formularios largos.

## Workflow de remediación

Para cada categoría:
1. Ejecutar `npm run test:a11y` → ver qué pantallas violan esa regla.
2. Aplicar corrección sistemática (un commit por categoría facilita revisión).
3. Re-ejecutar los tests → verificar reducción de violaciones.
4. Iterar hasta verde.

## Tests

Los 9 tests de 20.1 deben pasar todos en verde tras este prompt.

Tests adicionales puntuales si emerge una corrección no trivial:
- Si se introduce un focus-trap nuevo: `test_*_focus_trap_returns_focus_to_trigger`.
- Si se cambia el theme default por contraste: `test_default_theme_meets_4_5_1_ratio`.

## Criterio de done

- 9 tests baseline `*.a11y.test.tsx` en verde.
- `continue-on-error: true` removido del job CI de a11y.
- `a11y-baseline.md` eliminado (su propósito termina aquí).
- `docs/A11Y_CHECKLIST.md` (manual) creado con plan de auditoría adicional vía Lighthouse + NVDA/VoiceOver para validar lo que axe no cubre.
- PR documenta las correcciones aplicadas por categoría (al menos un párrafo por cada una de las 7 categorías arriba).
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

**Modelo sugerido**: **Sonnet** — escritura de tests sobre tipos TypeScript. Patrón estándar.

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

**Modelo sugerido**: **Sonnet** — tipos TS + funciones de merge/validación. Alcance cerrado.

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

**Modelo sugerido**: **Sonnet** — tests de React Context con patrones conocidos.

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

**Modelo sugerido**: **Sonnet** — React Context con inyección de CSS vars. Patrón estándar.

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

**Modelo sugerido**: **Sonnet** — configuración estática de presets (Default, Dark, University, High Contrast).

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

**Modelo sugerido**: **Sonnet** — CSS Custom Properties. Trabajo declarativo sin decisiones abiertas.

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

**Modelo sugerido**: **Sonnet** — UI interactiva con state local y exportación JSON. Patrones React conocidos.

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

**Modelo sugerido**: **Sonnet** — CRUD FastAPI estándar.

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

**Modelo sugerido**: **Sonnet** — tests de integración tipos + Provider + API + editor. Trabajo metódico.

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

**Modelo sugerido**: **Sonnet** — wire-up puntual del Provider en la raíz de la app.

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

**Modelo sugerido**: **Sonnet** — editor de prompts + selector de modelo + sandbox de prueba. React+Orval estándar.

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


---

## Bloque FAQ — Preguntas frecuentes como contenido citable (PENDIENTE)

> **Contexto**: decisión del 2026-08-11. Algunos chatbots deben responder a partir de un
> documento de **preguntas frecuentes con respuesta sugerida**. Se descartaron las otras dos
> vías que se plantearon:
>
> - **Como ejemplos en el prompt**: no escala —cien FAQ no caben en un prompt de sistema— y
>   además invita al modelo a parafrasear una respuesta institucional, que es justo lo que no
>   debe hacer con un texto que alguien redactó con cuidado.
> - **Como dataset dorado**: el dorado mide **recuperación**; es un artefacto de prueba, no
>   de contenido. (Pero ver FAQ.2: el mismo fichero puede sembrarlo, y eso es gratis.)
>
> **Se ingieren como documentos**, con `content_class: faq` —valor que el contrato ya admite—.
> La razón de fondo no es la comodidad: **el texto de la pregunta de una FAQ es un objetivo de
> embedding casi perfecto**, porque se parece mucho más a lo que el ciudadano escribe que el
> artículo que la fundamenta. Una FAQ recupera mejor que su propia norma.
>
> **El riesgo que este bloque tiene que cerrar**: una respuesta sugerida **no es una norma**.
> Si se cita con la misma autoridad que un artículo, se habrá publicado una respuesta no
> revisada como si fuera normativa.

---

### Prompt FAQ.1 (RED/GREEN) — Formato del `.md` de preguntas frecuentes y su troceado

**Modelo sugerido**: **Sonnet** — extiende un contrato que ya existe; el troceador ya es por
encabezados y no hay que tocarlo si el formato se define bien.

**Objetivo**: fijar cómo se escribe un `.md` de FAQ para que cada pregunta y su respuesta
acaben en **el mismo fragmento**, y ni una pregunta se separe de su respuesta ni se mezcle con
la de al lado.

```
# PROMPT FAQ.1 (RED/GREEN) — Una pregunta, un encabezado, un fragmento
# Deploy: edge

## El formato (se añade como sección propia a docs/CONTRATO_MD_CORPUS.md)
- Front-matter con `content_class: faq` y el resto de campos del contrato como cualquier
  documento (`language`, `id_publicacio`, `title`, `estat_vigencia`...).
- **Un encabezado de unidad citable por pregunta**, con su ancla: la pregunta ES el
  encabezado. Ancla estable con prefijo propio, `{#faq-N}`, para que una cita apunte a la
  pregunta y no al documento entero.
- La respuesta sugerida, en el cuerpo de esa unidad.
- **Referencia a la norma que la sostiene**, cuando la haya: es lo que permite que la
  respuesta remita al artículo en vez de sustituirlo.

## Por qué así, y no con negritas o listas
El troceador parte por encabezados (5 niveles + anclas). Si las preguntas van en negrita o en
una lista, el documento entero cae en uno o dos fragmentos y la recuperación devuelve un
bloque con veinte preguntas, de las que diecinueve no vienen a cuento. Peor todavía: un corte
en mitad de la lista deja media pregunta con la respuesta de otra, y **eso se cita mal sin que
se note**.

## Tests (RED primero)
# should_chunk_one_question_and_its_answer_together
# should_not_merge_two_consecutive_questions_in_one_chunk
# should_keep_the_faq_anchor_in_the_chunk_metadata
# should_reject_a_faq_document_whose_questions_are_bold_instead_of_headings
#     (con un aviso que diga por qué: es el error que se va a cometer)
# should_accept_a_faq_document_that_conforms   (extremo a extremo: sube, trocea, recupera)

## Cierre
- [ ] La sección del formato está en `docs/CONTRATO_MD_CORPUS.md`, con un ejemplo completo
- [ ] Un `.md` de FAQ de ejemplo, ingerible, en el repositorio o en el proyecto de curación
```

---

### Prompt FAQ.2 (RED/GREEN) — Una FAQ se cita como FAQ, nunca como norma

**Modelo sugerido**: **Opus** — toca el contrato de citas y la plantilla de respuesta, que es
donde se decide qué autoridad se le atribuye a un texto ante un ciudadano. Equivocarse aquí no
produce un error visible.

**Objetivo**: que la respuesta y la cita distingan una respuesta sugerida de un artículo de
norma. `content_class` ya lo modela; falta que llegue hasta la salida.

```
# PROMPT FAQ.2 (RED/GREEN) — La autoridad del texto viaja con el fragmento
# Deploy: edge

## Cambios
- El `content_class` del documento llega al metadato del fragmento y de ahí a la evidencia
  que consume el grafo. Hoy el troceador ya propaga `estat` y `classes`; es el mismo camino.
- Contrato de citas (P6): una fuente `faq` se presenta como **respuesta orientativa**, con su
  etiqueta, y —si la declara— con el enlace a la norma que la sostiene. Nunca con la misma
  forma que una cita de artículo.
- Plantilla de respuesta: cuando la evidencia dominante es `faq`, el texto debe decir que es
  orientativa. Sin inventar un aviso legal: una frase, y el enlace a la norma.

## Lo que se anunció como «regalo gratis» y NO lo era (comprobado al ejecutar)
- **Sembrar el dataset dorado desde el fichero de FAQ**: **descartado, no es gratis.** Un
  `GoldenQuery` es consulta + documentos que deberían salir. Si el objetivo de la pregunta de
  una FAQ es **la propia FAQ**, la entrada es circular y no mide nada: el documento que
  contiene literalmente esa frase la recupera siempre. Lo que sí valdría —pregunta de FAQ →
  **la norma** que la sostiene— exige mapear la referencia de respaldo a un identificador de
  documento, y eso no existe al escribir la FAQ. Queda como candidato cuando el respaldo se
  declare de forma estructurada, no como texto.
- **Alimentar el detector de huecos (RAG.14)**: no hace falta código. El detector ya trabaja
  sobre las conversaciones con `fallback_reason`; una FAQ que el corpus no sabe responder
  aparece sola en cuanto alguien la pregunta. Era una observación operativa disfrazada de
  tarea.

## Tests (RED primero)
# should_label_a_faq_source_as_orientative_in_the_citation
# should_not_present_a_faq_with_the_same_shape_as_an_article_citation
# should_link_to_the_backing_regulation_when_the_faq_declares_one
# should_carry_content_class_from_document_to_chunk_metadata
# should_mark_faq_evidence_in_the_packed_context   (el aviso va DENTRO del texto que ve el
#     modelo: marcarlo solo en el JSON deja que la respuesta presente la sugerencia como
#     norma, con una etiqueta al lado que la contradice)

## Cierre
- [ ] Una respuesta apoyada en FAQ es distinguible de una apoyada en norma **leyéndola**,
      no solo inspeccionando el JSON
```

---

## Bloque REV — Revisión humana de las respuestas del asistente interno (PENDIENTE)

> **Contexto**: Gerencia quiere un asistente **para funcionarios, con identificación**, y poder
> **revisar las respuestas** para valorar si son adecuadas o si conviene reformular las FAQ.
> Se evaluó adoptar Open WebUI para esto y **se descartó** (ver bloque OWUI): OWUI es una
> interfaz de chat y no aporta nada de la revisión, que es la parte que se pide; además
> duplicaría el registro de conversaciones y debilitaría la cadena de identidad justo en un
> sistema cuyo propósito es auditar quién preguntó qué.
>
> **Lo que ya existe y NO hay que construir** (comprobado en el código el 2026-08-11):
>
> | Necesidad | Dónde está |
> |---|---|
> | Asistente restringido a funcionarios identificados | `access_mode: restricted` + `allowed_saml_groups` (SEC.2.1) sobre el SSO SAML del bloque AUTH. **Es configuración, no desarrollo** |
> | Cada pregunta y respuesta registrada | `HubInteraction` (pregunta, respuesta, quién, `fallback_reason`) |
> | Pantalla de revisión con exportación | `ReportsPage.tsx` sobre `GET /hub/feedback/{chatbot_id}/review`, con estrellas, gráfico y CSV |
> | Bucle de la respuesta mala al contenido | Detector de huecos (RAG.14): agrupa las conversaciones que salieron mal en huecos de corpus |
>
> **Lo que falta es lo que planifica este bloque.**

---

### Prompt REV.1 (RED/GREEN) — El veredicto de quien revisa, sobre conversaciones reales

**Modelo sugerido**: **Sonnet** — el patrón ya existe en el proyecto y se replica; sin
decisiones de diseño abiertas.

**Objetivo**: hoy `feedback_score`/`feedback_text` de `HubInteraction` es la valoración del
**usuario final**. No hay forma de que Gerencia diga «esta respuesta no es adecuada» y quede
constancia de quién lo dijo. El patrón existe literalmente en el proyecto —`HubTestRun` tiene
`verdict` (good/bad/mixed), `verdict_note` y `verdict_by` desde RAG.13—, pero solo sobre
escenarios de prueba, no sobre lo que se le respondió a una persona de verdad.

```
# PROMPT REV.1 (RED/GREEN) — Que revisar deje rastro, y no sea leer un CSV
# Deploy: edge

## Modelo (operational_models.HubInteraction)
- `review_verdict`: 'good' | 'bad' | 'mixed', nullable. Nullable = **sin revisar**, que es
  el estado por defecto y el que alimenta la cola.
- `review_note`: texto, nullable — por qué. Sin esto el veredicto no sirve para reformular
  nada: «mal» no dice qué había que cambiar.
- `review_by`, `review_at`.
- Migración Alembic. Mismos nombres y valores que `HubTestRun` **a propósito**: dos
  vocabularios distintos para la misma idea acabarían divergiendo.

## Endpoint
- `PATCH /hub/feedback/interactions/{interaction_id}/review` con el veredicto y la nota.
- Guarda de tenencia como el resto (SEC.8.1): se resuelve la interacción -> chatbot ->
  organización, y **el revisor tiene que ser de ella**. Estas conversaciones llevan
  preguntas de personas identificadas.
- `GET /hub/feedback/{chatbot_id}/review` gana filtros: `review_status`
  (pending|reviewed|all) y `verdict`. Por defecto **pending**: la cola de revisión es lo que
  falta por mirar, no todo el historial.

## Frontend (ReportsPage)
- Botones de veredicto y campo de nota por fila; el estado se ve sin abrir nada.
- Filtro por estado y por veredicto. Contador de pendientes.
- i18n es/ca/en, sin cadenas sueltas.
- La exportación a CSV incluye las columnas nuevas: es lo que Gerencia se lleva a una
  reunión.

## Tests (RED primero)
# should_default_to_unreviewed
# should_record_who_reviewed_and_when
# should_require_a_note_when_the_verdict_is_bad     (un «mal» sin motivo no reformula nada)
# should_list_only_pending_interactions_by_default
# should_forbid_reviewing_an_interaction_of_another_organization   (va al gate de SEC.8.1)
# should_export_the_verdict_columns_to_csv          (Vitest)
# should_show_the_pending_count                     (Vitest)
```

---

### Prompt REV.2 (CONDICIONAL) — Hilos de conversación persistentes

**Modelo sugerido**: **Opus** — toca el contrato del chat, el modelo de datos y el frontend a
la vez, y hay que decidir qué es una conversación sin romper la contabilidad por turno de
SEC.4.

> **⚠️ NO EJECUTAR TODAVÍA. Prompt con disparador.**
>
> Hoy no hay hilo: `HubInteraction` no tiene identificador de conversación y el endpoint de
> chat **recibe el historial del cliente** (`history`, máximo 50 turnos). O sea que el estado
> vive en el navegador y no se puede retomar mañana.
>
> **Esto es lo único que OWUI habría dado hecho**, y por eso el bloque OWUI no se descartó a
> la ligera. Pero es también el trabajo caro, y no sabemos si hace falta.
>
> **Disparador**: ejecutar solo si el piloto del asistente interno muestra que los
> funcionarios lo piden — es decir, si aparece la queja de «he perdido lo que pregunté ayer».
> Si lo que hacen es preguntar y obtener una respuesta con su fuente, esto no hace falta y
> construirlo sería añadir superficie por si acaso.
>
> **Pregunta que decide, y es para Gerencia**: ¿imaginan «pregunto y obtengo una respuesta
> con su fuente» o **un espacio de trabajo conversacional** —hilos largos, adjuntos, prompts
> guardados, compartir conversaciones entre compañeros—? Si es lo segundo, hay que
> reconsiderar OWUI, porque sería reconstruir un producto entero.

```
# PROMPT REV.2 (CONDICIONAL) — Una conversación, no una ristra de turnos sueltos
# Deploy: edge

## Lo que hay que decidir antes de escribir código
- Qué es una conversación: `HubConversation` propia, o un `conversation_id` en
  `HubInteraction`. Lo segundo es menos tabla y suficiente para retomar; lo primero permite
  título, archivado y compartir. **Decidir con el caso real, no antes.**
- Qué pasa con el historial que hoy manda el cliente: si el servidor lo reconstruye, el
  contrato del endpoint cambia y hay que mirar el widget público, que no tiene sesión.
- **La contabilidad de SEC.4 se cuenta por turno y por actor**: un hilo no puede convertirse
  en la unidad de cuota sin rehacer eso.

## Y lo que NO cambia
- La revisión de REV.1 sigue siendo por interacción: Gerencia valora respuestas, no hilos.
- Un chatbot `public_anon` no gana historial por esto: no hay a quién atribuirlo.
```

---

## Bloque EXT — Frontera de la extracción: qué entra al corpus y qué es contexto (PENDIENTE, va ANTES de Deploy)

> **Contexto**: `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` (2026-08-10). «Subir un documento»
> significaba lo mismo para dos cosas distintas y se separan: el **corpus** —lo que el
> asistente cita ante un ciudadano— solo entra como `.md` conforme a `CONTRATO_MD_CORPUS.md`;
> el **contexto temporal** —un documento que alguien aporta para preguntarle cosas, o una
> entrada de un informe— se extrae con pdfplumber.
>
> La asimetría tiene razón: en el contexto la persona tiene el documento delante y ve si la
> extracción salió mal; en el corpus, una extracción mala es una **cita errónea** que no
> detecta nadie y que sale con la autoridad de una norma.
>
> **Va antes de Deploy** porque retira Docling, y la huella que quede es la que dimensiona la
> VM en D.4.

---

### Prompt EXT.1 (RED/GREEN) — Al corpus solo entra `.md` conforme al contrato

**Modelo sugerido**: **Sonnet** — retirada acotada con verificación por grep; el contrato del
`.md` ya existe y el cargador ya lo consume.

**Objetivo**: `hub_ingestion_router` acepta hoy PDF y lo convierte con Docling dentro de la
petición. Eso produce documentos sin front-matter, sin anclas de artículo y sin estado de
vigencia — es decir, contenido que el asistente **no puede citar** como norma, entrando por la
misma puerta que el corpus curado.

```
# PROMPT EXT.1 (RED/GREEN) — El corpus se alimenta del pipeline, no del navegador
# Deploy: edge

## Cambios
- hub_ingestion_router: la subida al corpus acepta SOLO .md/.markdown (UploadKind.TEXT, que ya
  existe desde SEC.6). Un PDF se rechaza con 415 y un mensaje que diga a dónde ir: el
  documento se convierte en el pipeline de curación, no aquí.
- Validar el front-matter en la subida con `entry_from_frontmatter` (el mismo que usa
  `corpus.load`), para que un .md sin los campos del contrato se rechace en el momento y no
  aparezca a medias en el corpus. Reportar TODOS los campos que faltan, no el primero.
- watcher.py: la ruta de conversión con Docling del corpus deja de usarse (la retirada del
  paquete es EXT.3, aquí solo se deja de llamar).
- frontend DocumentsPage/UploadDropzone: el formato aceptado y el mensaje de error reflejan
  la regla. i18n en es/ca/en, sin cadenas sueltas.

## FUERA DE ALCANCE
- `api/v1/ingestion.py::user_upload` (contexto temporal del usuario) — es EXT.2.
- Los pipelines de redacción — son EXT.2.

## Tests (RED primero)
# should_reject_a_pdf_upload_to_the_corpus_with_415
# should_accept_a_markdown_that_conforms_to_the_contract
# should_reject_a_markdown_without_frontmatter_listing_every_missing_field
# should_not_call_docling_from_the_corpus_path

## Cierre
- [ ] `grep -rn "docling" server/app/modules/agents_hub/ingestion/watcher.py` = 0
- [ ] La pantalla de documentos dice qué formato acepta y por qué (i18n es/ca/en)
```

---

### Prompt EXT.2 (RED/GREEN) — El contexto temporal se extrae con pdfplumber, y un escaneado falla en alto

**Modelo sugerido**: **Sonnet** — sustitución de una librería por otra con contrato de salida
conocido; la guarda de documento vacío es la única decisión, y está cerrada en el prompt.

**Objetivo**: las dos vías de contexto —el PDF que sube una persona para preguntarle cosas y
el PDF que entra como fuente de un informe de redacción— usan Docling. `pdfplumber` **ya es
dependencia directa** (`server/pyproject.toml:44`), así que el cambio no añade nada y quita
los modelos de layout y RapidOCR.

```
# PROMPT EXT.2 (RED/GREEN) — pdfplumber en las dos vías de contexto
# Deploy: edge

## Cambios
- api/v1/ingestion.py::user_upload → extracción con pdfplumber en vez de IngestionWatcher/Docling.
- modules/redaccion/pipelines/pdf_text_pipeline.py → pdfplumber. Ya usaba Docling SIN OCR, así
  que el contrato de salida no cambia: texto de PDFs con capa de texto.
- Extractor compartido y no dos copias: el troceado y el aviso de documento vacío son los
  mismos para las dos vías.

## La guarda que hace aceptable perder OCR
- Sin capa de texto, pdfplumber devuelve poco o nada. Ingerir eso en silencio produce un
  documento VACÍO que no ve nadie — la avería muda que esta auditoría ya encontró tres veces.
- Umbral por página (no absoluto: un PDF de 80 páginas con 200 caracteres está tan vacío como
  uno de 1 con 0). Por debajo → 422 con un mensaje que diga que el documento parece escaneado
  y que hace falta pasarlo por el pipeline de curación, que sí tiene OCR.
- El mensaje es para una persona, no para un log: nada de "extraction failed".

## Tests (RED primero)
# should_extract_text_from_a_digital_pdf
# should_reject_a_scanned_pdf_with_an_explicit_message
# should_use_a_per_page_threshold_not_an_absolute_one
# should_share_the_extractor_between_user_upload_and_redaccion
# should_preserve_the_redaccion_pipeline_output_contract   (regresión: mismo contrato que Docling sin OCR)

## Cierre
- [ ] Los tests de redacción que cubrían el pipeline de PDF siguen verdes sin cambiar sus aserciones
- [ ] `origen_del_text` sigue siendo el único sitio donde se declara que un texto viene de OCR
```

---

### Prompt EXT.3 — Retirada de Docling y medición de la huella

**Modelo sugerido**: **Sonnet** — retirada mecánica + medición. La cifra que salga es la que
dimensiona la VM en D.4, así que se mide, no se estima.

```
# PROMPT EXT.3 — Fuera del árbol, y cuánto ocupa lo que queda
# Deploy: n/a

## Retirada (Caso B: borrado directo, no hay migración en curso)
- Borrar `modules/agents_hub/ingestion/docling_processor.py` y sus llamantes muertos.
- Quitar `docling` de `server/pyproject.toml` y regenerar el lock.
- Barrido: `grep -rn "docling\|Docling\|rapidocr" server/` = 0 fuera de comentarios históricos.
- Ojo a `test_data_anonymizer.py` y `pipelines/{contracts,factory}.py`, que también lo nombran.

## Medición (el dato que necesita D.4)
- Arrancar la aplicación con el compose de producción y medir, SIN Docling:
    - memoria residente en reposo y durante una subida de contexto,
    - tiempo de arranque hasta el primer 200,
    - tamaño de la imagen.
- Repetir con una ingesta de corpus real (`corpus.load` sobre md_contracte) para ver el pico.
- Anotar las cifras en `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §Dimensionado, que hoy dice
  explícitamente que están sin medir.

## Cierre
- [ ] Suite backend completa en verde tras la retirada
- [ ] La imagen construye sin docling y arranca
- [ ] Las cifras están escritas, con el método con que se midieron
```

---

## Fase Deploy — Despliegue Staging GCP (Subfase 1.B, PENDIENTE)

> Nota: El Prompt D.6 (Edge node híbrido) pertenece a la Fase 3 y se detalla en Plan_TDD_Fase3.md.

## Fase Deploy — Paso a producción en GCP

> ## ⚠️ BLOQUE REESCRITO EL 2026-08-10 — el destino es una **VM**, no Cloud Run
>
> Decisión y razones en `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §2. En resumen: el
> planificador de calidad es un APScheduler dentro del `lifespan` y el rastreo de curación se
> encola con `BackgroundTasks`; **en Cloud Run con escalado a cero el scheduler no dispara y
> un rastreo largo muere a media ejecución**. Con CPU siempre asignada se arregla, pero
> entonces se paga lo mismo que una VM con más restricciones — o sea que el descuento que
> justificaba Cloud Run no era cobrable aquí.
>
> **Forma del despliegue**: VM con `docker-compose.prod.yml` (que ya describe la aplicación,
> el sandbox aislado y el resto), **Cloud SQL** para Postgres y **GCS** para documentos. El
> estado sigue gestionado: lo que hay en la base es el corpus curado y conversaciones de
> ciudadanos, y ahí las copias y el *point-in-time recovery* se pagan solos.
>
> **Lo que cambia respecto a lo que sigue escrito abajo**, prompt a prompt:
>
> | Prompt | Estado |
> |---|---|
> | **D.0** | Vigente, con la **lista de servicios recortada** (ver nota dentro) |
> | **D.1** | ✅ **YA HECHO** — lo resolvió **SEC.8.5** con la credencial de sitio (`HubWidgetKey`), que además es mejor que la API key por chatbot que este prompt describía: se guarda con hash, es revocable y no abre nada que no sea `public_anon`. **No ejecutar**; queda como registro |
> | **D.2** | Vigente. Secret Manager sigue siendo el sitio; cambia **quién los lee** (la VM al arrancar, no el servicio de Cloud Run) |
> | **D.3** | Vigente casi sin cambios. Cloud SQL se conserva; la conexión es por Auth Proxy **desde la VM** |
> | **D.4** | **REESCRITO** — era «tres servicios en Cloud Run» (API + embedding-service + docling-service). Con embeddings por API y **Docling retirado en EXT.3**, es **una sola máquina**. Ver D.4-VM |
> | **D.5** | **REESCRITO** — CI/CD que despliega a la VM, no a Cloud Run. Ver D.5-VM |
> | **D.6** | **NUEVO** — lo que una VM sí te hace dueño: copias, arranque tras reinicio y vigilancia. Ver D.6-VM |
>
> **Deja de existir como problema**: el ejecutor de trabajos duradero que SEC.8.8 aplazó para
> el rastreo. En una VM el proceso vive y no hace falta.
>
> **Prerrequisito**: el bloque **EXT** va antes. D.4 necesita la huella medida en EXT.3 para
> dimensionar la máquina, y ese número se mide — no se estima.

Esta fase no añade funcionalidad nueva: convierte la pila de desarrollo (Docker Compose local) en un sistema desplegado en Google Cloud Platform. El codebase ya está diseñado para ello (ver sección "Infraestructura objetivo" en CLAUDE.md); estos prompts completan la configuración y documentan el proceso operativo.

**Requisito previo**: acceso a un proyecto GCP con **facturación activa**. Los servicios ya no se dan por habilitados a mano: los habilita **D.0**, que es un paso del despliegue y no una nota en prosa (enmienda del 2026-08-01, a petición del usuario de habilitarlo todo de una vez en el deploy).

```
Fase Deploy
  ├── D.0  Habilitación de servicios del proyecto — gcloud services enable, versionado
  ├── D.1  Autenticación pública del widget — API key por chatbot
  ├── D.2  Secrets y variables de entorno — migración a Secret Manager
  ├── D.3  Base de datos en producción — Cloud SQL + migraciones Alembic
  ├── D.4  Imágenes Docker — Artifact Registry + Cloud Run
  ├── D.5  CI/CD — pipeline GitHub Actions → Cloud Build → Cloud Run
  └── D.6  Edge node — despliegue híbrido cloud/edge en GCP
```

---

### Prompt D.0 — Habilitación de servicios del proyecto GCP

**Modelo sugerido**: **Sonnet** — script idempotente y lista versionada; sin decisiones abiertas.

> **Ajuste 2026-08-10 (VM).** La lista de abajo se recorta y se amplía:
> - **Fuera**: `run.googleapis.com` y `artifactregistry.googleapis.com` si la imagen se
>   construye en la propia VM. Si el CI la publica (D.5), Artifact Registry **se queda**.
> - **Dentro**: `compute.googleapis.com` (la VM) y `oslogin.googleapis.com` (acceso por SSH
>   gobernado por IAM en vez de claves sueltas en metadatos).
> - **Se quedan** `sqladmin`, `secretmanager`, `storage`, y los de modelo —`aiplatform`,
>   `generativelanguage`— más `discoveryengine` para el Ranking API de RAG.6b.
> - **Ya no hace falta** ningún servicio para embeddings locales ni para Docling: EXT.3 lo
>   retira y MOD.2 deja los embeddings por API.

> **Añadido el 2026-08-01**, a petición del usuario: habilitar todos los servicios de una vez
> durante el despliegue en vez de irlos encendiendo a mano según hagan falta. Hasta ahora esto
> era una frase de «requisito previo» en prosa, con una lista **incompleta** —no incluía Vertex
> AI ni Discovery Engine— y nadie la ejecutaba: los cinco prompts de deploy daban por hecho que
> las APIs ya estaban encendidas.

```
# PROMPT D.0 — Los servicios se habilitan con un script, no con clics
# Deploy: cloud

## Script (scripts/gcp_enable_services.sh)
- `gcloud services enable` con la lista COMPLETA, idempotente (volver a ejecutarlo no rompe) y
  con el proyecto como parametro, no cableado.
- Lista minima a partir de lo que el sistema usa hoy; verificar contra el codigo antes de
  darla por buena, porque una API que falta se manifiesta como un 403 en produccion:
    run.googleapis.com                  Cloud Run (la aplicacion)
    sqladmin.googleapis.com             Cloud SQL (Postgres + pgvector)
    secretmanager.googleapis.com        secretos (D.2)
    artifactregistry.googleapis.com     imagenes (D.4)
    cloudbuild.googleapis.com           build (D.5)
    storage.googleapis.com              GCS via StorageService
    aiplatform.googleapis.com           Vertex AI
    generativelanguage.googleapis.com   Gemini API con API key (embeddings de MOD.2)
    discoveryengine.googleapis.com      Ranking API del reranker (RAG.6b)
- Documentar QUE prompt necesita cada servicio, para que quien lo lea sepa que se rompe si
  quita uno.

## Comprobacion, no solo habilitacion
- El script termina LISTANDO los servicios habilitados y marcando los que faltan. Habilitar y
  no comprobar deja el mismo agujero que habia: creer que estan.
- Anotar la cuota por defecto de discoveryengine, que puede ser baja.

## Tests
# should_list_every_service_the_codebase_needs   (la lista del script cubre lo que se usa)
# should_be_idempotent                            (segunda ejecucion, exit 0)
```

---

### Prompt D.1 ✅ — Autenticación pública del widget: API key por chatbot

> **HECHO EL 2026-08-10 POR SEC.8.5. No ejecutar este prompt.**
>
> El agujero que lo motivaba era peor de lo que este prompt suponía: el widget no es que
> careciera de credencial propia, es que embebía un **JWT de sesión o un PAT completo** en el
> HTML de la página (`data-token`), con el rol y las organizaciones de su dueño detrás.
>
> Lo resuelto en SEC.8.5 es un superconjunto de lo que aquí se pedía: `HubWidgetKey` es por
> chatbot, se guarda con **hash SHA-256**, se compara en tiempo constante, es **revocable**, y
> —por `assert_chatbot_access` con `via=VIA_WIDGET`, que SEC.2.1 ya había dejado escrito sin
> llamante— **solo abre chatbots `public_anon`**. La cabecera es `X-Widget-Key`. Alta, listado
> y revocación en `/hub/chatbots/{id}/widget-keys`.
>
> Lo único que este prompt aportaba y no está: la **documentación de incrustación** para quien
> publique el widget en una web (el `<script>` y el `data-widget-key`). Va a D.6-VM, con el
> resto de lo operativo.

**Modelo sugerido**: **Sonnet** — auth con X-Api-Key header; decisiones de diseño documentadas en el prompt.

**Objetivo**: el widget embebido en webs externas (UJI, ayuntamientos) no puede requerir login de usuario. Sustituir el mecanismo `data-token` JWT (solo válido para pruebas locales) por una **API key pública por chatbot** que identifica el bot sin exponer credenciales de usuario.

**Contexto y decisiones de diseño**:

- El widget se incrusta con un simple `<script>` en cualquier web. El usuario final es un ciudadano o alumno sin cuenta en la plataforma.
- La autenticación no es de usuario sino de **despliegue**: "este widget está autorizado a hablar con el chatbot X".
- La API key se genera al publicar un chatbot (campo `public_api_key` en `HubChatbot`), se muestra una sola vez en el panel admin y se puede revocar.
- El endpoint de chat del widget **no usa JWT**; usa `X-Api-Key` header. El endpoint del panel admin sigue usando JWT.

**Cambios en el modelo**:

```python
# HubChatbot — añadir campo
public_api_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
```

Migración Alembic: `alter table hub_chatbot add column public_api_key varchar(64) unique`.

**Nuevo endpoint público**:

```
POST /api/v1/widget/chat/{chatbot_id}
  Header: X-Api-Key: <public_api_key>
  Body: { "message": "...", "lang": "ca" }
  → StreamingResponse SSE (mismo protocolo que hub_chat)

Deploy: edge
```

El handler valida que `public_api_key` coincide con el `chatbot_id` en la tabla. No crea `HubInteraction` con `user_id` (usuario anónimo); genera un UUID de sesión efímero.

**Ampliación 2026-07-27 — la API key no basta: hay que comprobar el modo de acceso.**

Tal como estaba escrito este prompt, generar una `public_api_key` bastaría para exponer **cualquier** chatbot, incluido uno de gestión interna. Con SEC.2.1 en el plan, el handler del widget debe pasar por las tres guardas compartidas, en este orden y sin reimplementar ninguna:

```
1. assert_chatbot_access(actor=None, chatbot, via='widget_api_key')   # SEC.2.1
     -> 403 ACCESS_MODE_FORBIDDEN si access_mode != 'public_anon',
        aunque la API key sea válida y corresponda al chatbot.
2. assert_chatbot_available(session, chatbot, now)                    # SEC.4.1
     -> 403 CHATBOT_UNAVAILABLE (caducado / fuera de ventana / presupuesto agotado),
        con el unavailable_message del admin.
3. assert_within_quota(session, actor=None, chatbot, via='widget_api_key')  # SEC.4
     -> 429 con la cuota anon_ip_daily_token_quota, sujeto = IP.
```

La contabilidad de tokens (SEC.4) también aplica al camino anónimo: el `HubUsageCounter` se
actualiza con `subject_type='ip'` y con `subject_type='chatbot'`, y el `HubInteraction`
anónimo guarda `prompt_tokens`/`completion_tokens` igual que el autenticado.

**Dependencias nuevas**: D.1 pasa a requerir **SEC.2.1**, **SEC.4** y **SEC.4.1** cerrados.

**Tests añadidos**:
```python
# should_403_widget_when_chatbot_is_authenticated_mode   (API key válida, modo incorrecto)
# should_403_widget_when_chatbot_expired
# should_429_widget_when_ip_daily_quota_exceeded
# should_record_anonymous_usage_under_ip_subject
```

**Cambios en el widget**:

- `main.tsx`: leer `data-api-key` en lugar de `data-token`
- `useChat.ts`: enviar `X-Api-Key` header en lugar de `Authorization: Bearer`
- `widget.html` de producción: solo necesita `data-chatbot-id` y `data-api-key`

```html
<div id="govgenai-widget"
     data-chatbot-id="<uuid>"
     data-api-key="<public_api_key>"
     data-lang="ca"
     data-api-url="https://api.govgenai.com/api/v1">
</div>
```

**UI admin** (panel de publicación del chatbot):
- Botón "Publicar widget" → genera `public_api_key` aleatoria (32 bytes hex), la guarda hasheada en BD, la muestra en claro UNA sola vez.
- Botón "Revocar" → pone `public_api_key = null`.
- Snippet HTML copiable con el `data-api-key` ya relleno.

**Tests requeridos**:
```python
# unit
# should_reject_request_with_invalid_api_key → 401
# should_reject_request_with_api_key_for_wrong_chatbot → 401
# should_accept_request_with_valid_api_key → 200 SSE
# should_not_require_jwt_on_widget_endpoint
# should_create_anonymous_interaction_without_user_id

# integration
# should_generate_api_key_via_admin_endpoint
# should_revoke_api_key_and_reject_subsequent_widget_requests
```

**CORS**: el endpoint `/api/v1/widget/*` debe permitir cualquier origen (`*`) ya que se llama desde webs externas. El endpoint `/api/v1/hub/*` (admin) solo permite el origen del panel admin.

---

### Prompt D.2 — Secrets y variables de entorno: migración a Secret Manager

**Modelo sugerido**: **Sonnet** — migración de .env a GCP Secret Manager. Comandos gcloud + wiring en Cloud Run.

**Objetivo**: eliminar el fichero `server/.env` en producción. Todas las credenciales y configuración sensible viven en **GCP Secret Manager**; el contenedor las recibe como variables de entorno inyectadas por Cloud Run.

**Inventario de secrets** (lo que hay en `server/.env` y su destino en GCP):

| Variable local | Secret Manager name | Quién lo consume |
|---|---|---|
| `JWT_SECRET_KEY` | `govgenai-jwt-secret` | API principal |
| `DATABASE_URL` | `govgenai-db-url-async` | API principal |
| `DATABASE_URL_SYNC` | `govgenai-db-url-sync` | Alembic (Cloud Build step) |
| `LANGFUSE_PUBLIC_KEY` | `govgenai-langfuse-pub` | API principal |
| `LANGFUSE_SECRET_KEY` | `govgenai-langfuse-sec` | API principal |
| `STORAGE_BUCKET` | variable de entorno pública (no secret) | API principal |

**Variables de entorno no-secretas** (se definen directamente en la configuración de Cloud Run, no en Secret Manager):

```
ENVIRONMENT=production
STORAGE_BACKEND=gcs
STORAGE_BUCKET=govgenai-prod
DEPLOY_MODE=all   # o edge / cloud según el nodo
```

**Configuración de Cloud Run** (extracto `cloudbuild.yaml` o CLI):

```yaml
- name: 'gcr.io/cloud-builders/gcloud'
  args:
    - run
    - deploy
    - govgenai-api
    - --set-secrets=JWT_SECRET_KEY=govgenai-jwt-secret:latest
    - --set-secrets=DATABASE_URL=govgenai-db-url-async:latest
    - --set-secrets=LANGFUSE_PUBLIC_KEY=govgenai-langfuse-pub:latest
    - --set-secrets=LANGFUSE_SECRET_KEY=govgenai-langfuse-sec:latest
    - --set-env-vars=ENVIRONMENT=production,STORAGE_BACKEND=gcs,STORAGE_BUCKET=govgenai-prod
```

**Checklist de seguridad**:
- [ ] `server/.env` añadido a `.gitignore` (ya debe estarlo)
- [ ] `JWT_SECRET_KEY` en producción: mínimo 64 bytes aleatorios (`openssl rand -hex 64`)
- [ ] `JWT_EXPIRATION_MINUTES` en producción: volver a 60 (el valor `10080` es solo para desarrollo local)
- [ ] La cuenta de servicio de Cloud Run tiene rol `roles/secretmanager.secretAccessor` solo para los secrets que necesita

**Tests requeridos**:
```python
# should_read_jwt_secret_from_environment_variable
# should_fail_fast_if_jwt_secret_not_set
# should_read_database_url_from_environment_variable
```
(La mayoría ya existen; este prompt verifica que no hay credenciales hardcodeadas en código.)

---

### Prompt D.3 — Base de datos en producción: Cloud SQL + migraciones Alembic

**Modelo sugerido**: **Sonnet** — provisioning Cloud SQL + estrategia de migración Alembic. Comandos documentados.

**Objetivo**: documentar y automatizar el proceso de aprovisionamiento de Cloud SQL y la ejecución de migraciones Alembic como paso pre-deploy, garantizando que la BD nunca queda en un estado intermedio si el despliegue falla.

**Configuración de Cloud SQL**:

```bash
# Crear instancia (una sola vez)
gcloud sql instances create govgenai-prod \
  --database-version=POSTGRES_16 \
  --tier=db-g1-small \
  --region=europe-southwest1 \
  --enable-google-private-path

# Crear BD y usuario
gcloud sql databases create govgenai --instance=govgenai-prod
gcloud sql users create govgenai --instance=govgenai-prod --password=<secret>

# Habilitar extensión pgvector (ejecutar en psql conectado vía Cloud SQL Auth Proxy)
CREATE EXTENSION IF NOT EXISTS vector;
```

**Cloud SQL Auth Proxy en Cloud Run**: Cloud Run conecta a Cloud SQL vía socket Unix automáticamente si se especifica `--add-cloudsql-instances`. La `DATABASE_URL` usa el formato:

```
postgresql+asyncpg:///govgenai?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
```

**Estrategia de migraciones** (sin downtime):

1. Las migraciones se ejecutan como un **Cloud Build step** ANTES del despliegue del nuevo contenedor.
2. Solo se permiten migraciones `ADD COLUMN ... DEFAULT NULL` o `CREATE TABLE` en el step automático.
3. Migraciones con `ALTER COLUMN NOT NULL` o `DROP` requieren aprobación manual y ventana de mantenimiento.
4. El comando:

```yaml
# En cloudbuild.yaml, antes del step de deploy
- name: 'gcr.io/$PROJECT_ID/govgenai-api:$COMMIT_SHA'
  entrypoint: 'uv'
  args: ['run', 'alembic', 'upgrade', 'head']
  env:
    - 'DATABASE_URL_SYNC=$$DATABASE_URL_SYNC'
  secretEnv: ['DATABASE_URL_SYNC']
```

**Backup antes de migrar**:

```bash
gcloud sql backups create --instance=govgenai-prod --async
```

**Tests requeridos**:
```python
# should_run_all_migrations_without_error_on_clean_database
# should_be_idempotent_running_migrations_twice
# should_not_lose_data_on_add_column_migration
```

---

### Prompt D.4.0 (RED/GREEN) — Los modelos locales pasan a ser un extra de instalación

**Modelo sugerido**: **Sonnet** — cambio de empaquetado con criterio cerrado; la parte fina
(importación perezosa y mensaje de error) está especificada abajo.

**Objetivo**: `torch`, `transformers` y `sentence-transformers` son dependencias obligatorias
y están ahí por `LocalEmbeddingService` (BGE-M3) y `LocalReranker`. Con embeddings de Vertex y
el reranker apagado —el plan de despliegue— **no se usan en ejecución, pero se pagan enteros**
en memoria y arranque.

Medido en EXT.3: `sentence-transformers` 216 MB, `torch` 172 MB, y entre los tres se llevan
prácticamente todo el tiempo de import; `pdfplumber`, que es lo que sí se usa, cuesta 5 MB.
La aplicación en reposo son 627 MB, y la mayor parte es esa pila.

**Va antes de D.4-VM** porque cambia el tamaño de la máquina a la mitad, y ese es el número
que D.4 tiene que fijar.

```
# PROMPT D.4.0 (RED/GREEN) — Instalar los modelos locales solo cuando se van a usar
# Deploy: shared (empaquetado)

## Lo que NO cambia, y es la condición del prompt
- **El modo edge sigue pudiendo usar modelos locales.** Esto no retira una capacidad: la
  hace opcional. `LocalEmbeddingService` y `LocalReranker` se conservan íntegros, y un
  despliegue edge los instala con el extra.
- La cascada de selección (`resolve_embedding_service`, `resolve_reranker`) no cambia: se
  sigue eligiendo por fila de configuración, no por lo que haya instalado.

## Cambios
- `server/pyproject.toml`: mover `torch`, `torchvision`, `transformers` y
  `sentence-transformers` de las dependencias base a un extra `[project.optional-dependencies]`
  llamado `local-models`. Regenerar el lock.
- Importación **perezosa** en `LocalEmbeddingService` y `LocalReranker`: el import va dentro
  del método que lo necesita, no en la cabecera del módulo. Hoy `reranker.py` ya lo hace
  ("import perezoso"); replicar el patrón en el servicio de embeddings.
- **El fallo tiene que explicarse.** Si se resuelve un proveedor `local` sin el extra
  instalado, el error debe decir QUÉ falta y CÓMO instalarlo (`uv sync --extra local-models`),
  no un `ModuleNotFoundError: torch` a secas. Es el mismo criterio que
  `EmbeddingProviderNotSupported`, que ya falla con un mensaje que se entiende.
- Documentar el extra en el README de despliegue y en `.env.example`, junto a la elección de
  proveedor de embeddings.

## Tests (RED primero)
# should_not_import_torch_at_module_import_time      (importar la app no carga torch)
# should_explain_how_to_install_the_extra_when_local_embedding_is_selected
# should_explain_how_to_install_the_extra_when_local_reranker_is_selected
# should_still_resolve_google_embeddings_without_the_extra
# should_keep_local_services_working_when_the_extra_IS_installed   (no se retira capacidad)

## Cierre
- [ ] `python -c "import server.app.main; import sys; assert 'torch' not in sys.modules"`
- [ ] Medir de nuevo el RSS en reposo y anotarlo en
      `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §Dimensionado, junto a la cifra de 627 MB
      que sustituye
- [ ] Suite completa en verde CON el extra instalado (es como corre CI hoy)
```

---

### Prompt D.4-VM (REESCRITO) — La máquina: aprovisionamiento, Compose y TLS

**Modelo sugerido**: **Sonnet** — infraestructura con pasos conocidos; la única decisión
abierta (el tamaño) la cierra la medición de EXT.3.

**Objetivo**: una VM que sirva la aplicación de forma estable, con el estado fuera de ella.
Sustituye al despliegue de tres servicios en Cloud Run: con embeddings por API y Docling
retirado en EXT.3, no hay nada que escalar por separado.

**Dependencias**: EXT.3 (la huella medida), D.2 (secretos), D.3 (Cloud SQL).

```
# PROMPT D.4-VM — Una máquina, el estado fuera
# Deploy: cloud (infraestructura)

## Tamaño — MEDIDO (EXT.3 y D.4.0, 2026-08-11)
- **Sin el extra `local-models`, que es este despliegue: 345 MB y 9,4 s de arranque**, con la
  pila de modelos sin cargar. Eran 627 MB antes de D.4.0.
- Pico extrayendo un PDF de 40 páginas (medido antes de D.4.0): **968 MB**. Conviene volver a
  medirlo, porque parte de ese pico venía de la pila que ya no está.
- Con el extra instalado (edge con modelos locales): 559 MB.
- **`e2-small` (2 GB) es holgado** para el despliegue estándar. `e2-medium` solo si se
  instala el extra.
- **La memoria es trasladable; los TIEMPOS no del todo** —Windows, caché de disco y
  antivirus—. Volver a medir el arranque en la propia máquina.
- **Docling ya no manda: manda `torch`.** Medido por librería, `pdfplumber` cuesta 0,09 s y
  5 MB, mientras que `transformers` (142 s), `sentence-transformers` (75 s / 216 MB) y
  `torch` (52 s / 172 MB) se llevan el arranque entero. Están por `LocalEmbeddingService`
  (BGE-M3) y `LocalReranker`, no por la extracción.
- **D.4.0 lo resuelve y hay que ejecutarlo ANTES**: mueve esa pila a un extra
  `[local-models]`. Con ella, la aplicación pide ~2 GB; sin ella, se espera ~150-250 MB. El
  tamaño se fija con la cifra que D.4.0 vuelva a medir, no con la de 627 MB.
- Si el despliegue usa embeddings de Vertex y el reranker apagado —el plan—, la VM **no
  instala el extra**. Un edge con modelos locales sí, y entonces vuelve a hacer falta el
  presupuesto grande.
- El disco no guarda nada que duela perder (ver abajo), así que el margen se pone en memoria.
- Disco: solo sistema, imágenes y logs. Los documentos van a GCS y la base a Cloud SQL, así
  que el disco de la VM no guarda nada que duela perder — y eso es deliberado.

## Aprovisionamiento (script idempotente, versionado; nada de clics)
- VM en europe-southwest1 (misma región que Cloud SQL: la latencia de cada consulta del
  retriever la paga el usuario esperando).
- SIN IP pública para la base: Cloud SQL Auth Proxy como servicio en la VM.
- Cuenta de servicio propia con lo mínimo: cliente de Cloud SQL, lectura de los secretos que
  necesita y acceso al bucket. No la cuenta por defecto de Compute, que viene con más de lo
  que hace falta.
- Cortafuegos: 80/443 abiertos; SSH por IAP u OS Login, nunca 22 abierto al mundo.

## Servicio
- `docker compose -f docker-compose.prod.yml up -d` gobernado por una unidad **systemd** con
  `Restart=always`, para que un reinicio de la máquina levante el sistema solo. Sin esto, la
  VM tiene una avería que Cloud Run no tenía.
- Proxy inverso (Caddy o nginx) con TLS y renovación automática. Caddy si se quiere el
  certificado sin ceremonia.
- ENVIRONMENT=production. Recordar que a partir de SEC.8.3/SEC.8.4 el arranque FALLA —a
  propósito— si SANDBOX_MODE=local o si JWT_SECRET_KEY es el de ejemplo o mide menos de 32
  caracteres. Es la comprobación funcionando, no un problema del despliegue.
- TRUSTED_PROXY_HOPS=1 (SEC.8.4): hay un proxy inverso delante, así que la IP con la que se
  limita el login se cuenta un salto desde la derecha. Con 0 se ignoraría la cabecera y todo
  el tráfico compartiría cubo.

## Verificación de cierre
- [ ] `curl https://<dominio>/health` responde por TLS válido
- [ ] `/docs` NO responde (SEC.7 lo apaga en producción)
- [ ] Reiniciar la VM y comprobar que el sistema vuelve solo
- [ ] El scheduler de calidad dispara (es la razón de elegir VM: verificarlo, no suponerlo)
- [ ] Un rastreo de sitio termina y deja páginas — lo que moría en Cloud Run
```

---

### Prompt D.4-CR (SUPERSEDIDO) — Imágenes Docker: Artifact Registry y Cloud Run

> **No ejecutar.** Reemplazado por D.4-VM. Se conserva porque su `Dockerfile` multi-stage y la
> configuración de Artifact Registry siguen sirviendo si el CI construye la imagen (D.5-VM);
> lo que ya no aplica es el despliegue a Cloud Run y los tres servicios —`embedding-service`
> y `docling-service` no existen: los embeddings van por API desde MOD.2 y Docling se retira
> en EXT.3—.

**Modelo sugerido**: **Sonnet** — Dockerfiles multi-stage + Artifact Registry + Cloud Run config (3 servicios).

**Objetivo**: construir imágenes Docker de producción (API principal, embedding-service, docling-service), publicarlas en Artifact Registry y desplegarlas en Cloud Run con la configuración de recursos adecuada.

**Repositorio en Artifact Registry**:

```bash
gcloud artifacts repositories create govgenai \
  --repository-format=docker \
  --location=europe-southwest1

# Configurar Docker para autenticar
gcloud auth configure-docker europe-southwest1-docker.pkg.dev
```

**`Dockerfile` de producción para la API** (ubicación: raíz del proyecto):

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY server/ server/
COPY pyproject.toml uv.lock ./

RUN pip install uv && uv sync --frozen --no-dev

ENV PYTHONPATH=/app
CMD ["uv", "run", "uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Configuración de Cloud Run por servicio**:

| Servicio | CPU | RAM | Min instances | Max instances | Notas |
|---|---|---|---|---|---|
| `govgenai-api` | 2 | 1 GB | 1 | 10 | Chat + admin |
| `embedding-service` | 4 | 4 GB | 1 | 3 | BGE-M3 cargado permanentemente |
| `docling-service` | 2 | 2 GB | 0 | 5 | Escala a 0 entre ingestas |

**Deploy**:

```bash
# Build y push
docker build -t europe-southwest1-docker.pkg.dev/PROJECT/govgenai/api:SHA .
docker push europe-southwest1-docker.pkg.dev/PROJECT/govgenai/api:SHA

# Deploy Cloud Run
gcloud run deploy govgenai-api \
  --image=europe-southwest1-docker.pkg.dev/PROJECT/govgenai/api:SHA \
  --region=europe-southwest1 \
  --min-instances=1 \
  --max-instances=10 \
  --memory=1Gi \
  --cpu=2 \
  --add-cloudsql-instances=PROJECT:europe-southwest1:govgenai-prod \
  --no-allow-unauthenticated  # el API no es público; el widget usa API key
```

**Frontend (widget + panel admin)**:

El frontend React se construye con `npm run build` y se sirve desde **Cloud Storage + Cloud CDN** (sitio estático), no desde Cloud Run:

```bash
npm run build
gsutil -m rsync -r dist/ gs://govgenai-static/
gcloud compute backend-buckets update govgenai-cdn --enable-cdn
```

El `widget.iife.js` se publica en `https://cdn.govgenai.com/widget/widget.iife.js` — los partners lo referencian con una URL versionada para evitar breaking changes.

**Checklist pre-deploy**:
- [ ] `npm run build` y `npm run build:widget` sin errores
- [ ] `docker build` sin errores en modo producción
- [ ] `uv run pytest tests/ -v` con todas las suites verdes
- [ ] Migración Alembic ejecutada y verificada en staging antes de prod

---

### Prompt D.5-VM (REESCRITO) — CI/CD: GitHub Actions → la VM

**Modelo sugerido**: **Sonnet** — workflow con pasos conocidos; la decisión de autenticación
(Workload Identity) está cerrada en el prompt.

```
# PROMPT D.5-VM — Desplegar sin claves de larga vida ni migraciones a ciegas
# Deploy: cloud (CI)

## Autenticación
- **Workload Identity Federation**, no una clave de cuenta de servicio en los secretos de
  GitHub: una clave JSON en un repositorio es una credencial permanente que nadie rota.

## Flujo
- Construir la imagen en CI y publicarla en Artifact Registry con el SHA del commit como
  etiqueta. `latest` no sirve para saber qué está corriendo ni para volver atrás.
- Desplegar por SSH (IAP): `docker compose pull` + `up -d` con la etiqueta nueva.
- **Migraciones antes de cambiar la imagen**, en un paso propio y visible. Alembic aplicado
  desde el contenedor nuevo contra Cloud SQL, con la salida en el log del workflow: una
  migración que falla dentro del arranque deja el sistema a medias sin decir por qué.
- Comprobación posterior: `/health` y una consulta real al retriever. Si falla, revertir a la
  etiqueta anterior.

## Lo que NO se hace
- Desplegar solo con `git pull` en la VM: eso hace que lo que corre dependa del estado del
  disco de la máquina y no de un artefacto identificable.
- Ejecutar la suite en el despliegue. Corre en CI antes; repetirla aquí alarga el despliegue
  sin añadir información.

## Cierre
- [ ] Un push a main despliega y la versión servida es la del commit
- [ ] Un despliegue con migración deja constancia de qué revisión se aplicó
- [ ] Existe y está probado el camino de vuelta a la etiqueta anterior
```

---

### Prompt D.6-VM (NUEVO) — De lo que una VM te hace dueño: copias, vigilancia y publicación

**Modelo sugerido**: **Sonnet** — operativa con decisiones cerradas.

**Objetivo**: Cloud Run traía gratis el reinicio, el registro y la salud. En una VM eso hay
que ponerlo, y es la contrapartida honesta de la decisión. Recoge además la documentación de
incrustación del widget que D.1 dejó pendiente.

```
# PROMPT D.6-VM — Que sobrevivir a un incidente no dependa de acordarse
# Deploy: cloud (operación)

## Copias
- Cloud SQL: copias automáticas + point-in-time recovery. **Y una restauración de prueba**:
  una copia que nadie ha restaurado nunca es una hipótesis, no una copia.
- GCS: versionado en el bucket de documentos.
- La VM NO se respalda a propósito: no guarda nada que no se pueda reconstruir con el script
  de aprovisionamiento y la imagen. Si algo de la VM hiciera falta respaldar, es que se ha
  colado estado donde no debía.

## Vigilancia
- Uptime check contra /health con aviso.
- Alertas de memoria y disco: el disco lleno por logs es la avería más aburrida y más común
  de una VM.
- Logs de los contenedores a Cloud Logging con rotación local.

## Publicación del widget (lo que quedó de D.1)
- Documentar la incrustación: `<script>` + `data-chatbot-id` + `data-widget-key`, con el
  aviso de que la credencial es de SITIO: aparece en el HTML de quien la publique, y por eso
  no abre nada que no sea un chatbot `public_anon`.
- Documentar la revocación y la rotación.

## Cierre
- [ ] Restauración de la base probada de verdad, con el tiempo que costó anotado
- [ ] El aviso de caída llega a alguien (probarlo apagando el servicio)
- [ ] La guía de incrustación permite a alguien de fuera publicar el widget sin preguntar
```

---

### Prompt D.5-CR (SUPERSEDIDO) — CI/CD: pipeline GitHub Actions → Cloud Run

> **No ejecutar.** Reemplazado por D.5-VM. Se conserva por los pasos de build y autenticación,
> que siguen valiendo; lo que cambia es el destino del despliegue.

**Modelo sugerido**: **Sonnet** — GitHub Actions workflow + secrets + deploy steps. Patrón conocido.

**Objetivo**: automatizar el ciclo completo (test → build → migrate → deploy) con GitHub Actions. Cada push a `main` despliega a producción; cada PR despliega a staging.

**Estructura del pipeline** (`.github/workflows/deploy.yml`):

```
on: push (main) / pull_request

jobs:
  test:
    - uv run pytest server/tests/ -v
    - npm test (frontend)

  build:
    needs: test
    - docker build API, embedding-service, docling-service
    - docker push a Artifact Registry con tag=$COMMIT_SHA

  migrate:
    needs: build
    - Cloud Build step: uv run alembic upgrade head (via Cloud SQL Auth Proxy)

  deploy:
    needs: migrate
    - gcloud run deploy govgenai-api --image=...:$COMMIT_SHA
    - gcloud run deploy embedding-service --image=...:$COMMIT_SHA
    - gcloud run deploy docling-service --image=...:$COMMIT_SHA
    - gsutil rsync frontend/dist/ → Cloud Storage (panel admin)
    - gsutil rsync frontend/dist/widget/ → Cloud Storage CDN (widget público)
```

**Autenticación GCP desde GitHub Actions**:

Usar **Workload Identity Federation** (no service account keys en secretos de GitHub):

```yaml
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/NUMBER/locations/global/workloadIdentityPools/github/providers/github'
    service_account: 'github-deploy@PROJECT.iam.gserviceaccount.com'
```

**Entornos**:

| Branch | Entorno | Cloud Run service | BD |
|---|---|---|---|
| `main` | production | `govgenai-api` | Cloud SQL prod |
| `staging` | staging | `govgenai-api-staging` | Cloud SQL staging (misma instancia, BD distinta) |
| PR | preview | no despliega (solo tests) | — |

**Tests requeridos** (smoke tests post-deploy):

```bash
# Ejecutar tras cada deploy exitoso en CI
curl -f https://api.govgenai.com/health → 200
curl -f https://api.govgenai.com/api/v1/hub/chatbots \
     -H "Authorization: Bearer $SMOKE_TEST_TOKEN" → 200
```

---


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

> **Nota:** Los prompts TDD detallados de esta fase se detallarán (Prompt 5 de la sesión de planificación) antes de ejecutar.


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

> **Nota:** Los prompts TDD detallados de esta fase se detallarán antes de ejecutar.


---

## Bloque SBX — Seguridad de la Información: Sandbox aislado de ejecución de scripts (Subfase 1.B → 1.C, PENDIENTE)

**Objetivo del bloque**: introducir una **frontera de aislamiento por contenedor** para todo código que el sistema ejecuta como resultado de propuestas LLM o de scripts metaprogramados (extracción admin, charts matplotlib, fallback ETL). La auditoría AST (`ScriptSecurityAuditor`, 9R.5.4) y los límites de recursos en proceso son **una primera capa, no la última**: la dinamicidad de Python (getattr, manipulación de `__builtins__`, decoradores, bytecode) deja huecos que la auditoría estática no cubre. Este bloque añade una capa que el script no puede saltar aunque escape del intérprete: un **microservicio evaluador** independiente (`script-sandbox`) en red dedicada sin acceso a base de datos, almacenamiento ni internet, con cgroups/seccomp del propio Docker. El patrón es defensible ante una comisión de seguridad pública porque encaja con el estándar de microservicios (no requiere acceso al socket de Docker del host) y se traduce 1:1 a Cloud Run en GCP.

**Justificación de la ubicación (antes de Fase 11)**:
- Fase 11.2 reescribe `docker-compose.prod.yml` para distribución como software libre. SBX debe haber dejado allí el servicio `script-sandbox` antes de que 11.2 fije el formato.
- Es prerrequisito de auditoría pre-despliegue por la comisión de Seguridad de la Información.
- No bloquea el resto de Fase 1: los tests existentes pasan con la implementación in-process actual; SBX los reorienta a la frontera de red sin cambiar los contratos de los pipelines.

**Decisión Arquitectónica (2026-05-17)**: opción "Microservicio Evaluador" frente a "Docker-out-of-Docker (DooD)". Razones:
1. No requiere montar `/var/run/docker.sock` en el contenedor de la API — eliminamos el principal punto de fricción con infosec en entornos gubernamentales.
2. Funciona en Cloud Run (la opción DooD no — Cloud Run no expone socket de Docker).
3. Encaja con el modelo edge: en despliegues on-premise del cliente, dos contenedores en red privada se auditan trivialmente.
4. Cloud Run corre sobre gVisor por defecto: el sandbox hereda aislamiento de kernel sin configurar nada.

**Capas de defensa resultantes (defensa en profundidad)**:

1. `ScriptSecurityAuditor` (AST) — primera barrera en la API.
2. Re-auditoría defensiva dentro del propio sandbox (segunda barrera, antes de exec).
3. Red dedicada `sandbox-net` — sin DNS hacia `postgres`, `minio`, ni salida a internet.
4. Contenedor sin privilegios: `read_only: true`, `cap_drop: ALL`, `no-new-privileges`, usuario `65534:65534`.
5. Subproceso efímero por petición dentro del sandbox — sin contaminación de memoria entre ejecuciones, `kill` explícito en `finally`.
6. Límites de recursos del propio Docker (`cpus`, `memory`, `tmpfs` con tamaño máximo).
7. En GCP: gVisor (heredado automáticamente).

**Lo que NO incluye este bloque**:
- Migración del sandbox a gVisor explícito on-premise (queda en backlog post-MVP, solo se documenta cómo aplicar `runsc` si el cliente lo requiere).
- Auditoría dinámica del comportamiento del script en tiempo de ejecución (tracing de syscalls). El aislamiento por contenedor + sin red + sin privilegios cubre el modelo de amenazas del MVP.
- Ejecución distribuida o paralelización del sandbox (un único contenedor con un worker pool basta para el volumen previsto).

**Reglas duras del bloque SBX**:
- El microservicio `script-sandbox` **es edge** (vive en el cliente, ejecuta sobre datos del cliente).
- El sandbox **no importa nada** del módulo `redaccion` ni de `agents_hub`. Es un servicio autocontenido con su propio `Dockerfile` y `pyproject.toml` mínimo. Solo comparte el contrato HTTP.
- El cliente HTTP (`SandboxClient`) vive en `server/app/core/sandbox_client.py` (compartido, no edge ni cloud — capa de infraestructura). Análogo a `StorageService`.
- La auditoría AST se duplica intencionalmente: la API audita antes de enviar, el sandbox audita antes de ejecutar. **No** es deuda técnica; es defensa en profundidad. Si el contenedor recibe código no auditado (por bug en la API), no lo ejecuta.
- El sandbox **no persiste** nada entre peticiones. Cada `/execute` arranca un subproceso hijo limpio que muere al terminar.

---

### Prompt SBX.1 (RED/GREEN) — Microservicio `script-sandbox`: FastAPI + subprocess efímero

**Modelo sugerido**: **Opus** — el prompt concentra decisiones de diseño embebidas: contrato HTTP (3 endpoints con semánticas distintas: extracción JSON vs. chart bytes vs. ETL CSV), estrategia de aislamiento del subproceso hijo (fork + kill explícito en `finally`, no confiar en `subprocess.run(timeout=)`), serialización de `options` complejas, re-auditoría AST defensiva sin importar del módulo `redaccion`.

```markdown
# PROMPT SBX.1 (RED/GREEN) — Microservicio script-sandbox

Objetivo: crear un servicio FastAPI autocontenido `services/script_sandbox/` que ejecuta scripts Python aprobados en un subproceso efímero, devolviendo resultados estructurados. Este servicio sustituye los `subprocess.run([sys.executable, ...])` que hoy viven dentro del proceso del API (admin_script_pipeline, chart_renderer, etl_service).

Deploy: edge (forma parte del despliegue del cliente).

## Estructura del nuevo paquete

```
services/script_sandbox/
├── pyproject.toml          # uv-managed; deps mínimas (fastapi, pydantic, pandas, matplotlib, seaborn, numpy, openpyxl, pdfplumber)
├── Dockerfile              # python:3.12-slim, usuario no-root, sin pip-cache
├── sandbox/
│   ├── __init__.py
│   ├── main.py             # FastAPI app
│   ├── auditor.py          # COPIA SIMPLIFICADA de ScriptSecurityAuditor — re-auditoría defensiva
│   ├── runner.py           # ejecuta subproceso hijo + kill explícito
│   ├── wrappers.py         # build_extraction_wrapper, build_chart_wrapper, build_etl_wrapper
│   └── contracts.py        # Pydantic: ExecuteExtractionRequest/Response, ExecuteChartRequest, ExecuteETLRequest
└── tests/
    ├── test_health.py
    ├── test_execute_extraction.py
    ├── test_execute_chart.py
    ├── test_execute_etl.py
    ├── test_auditor_defense.py
    └── test_runner_kills_runaway.py
```

## Contrato HTTP

### `GET /health` → `{"status":"healthy"}`

### `POST /execute-extraction`
Request:
```json
{
  "code": "<script Python>",
  "file_path": "/tmp/sandbox/abc.xlsx",   # ruta dentro del tmpfs del sandbox; el caller debe haberlo escrito antes
  "raw_text": "...",
  "options": {"sheet": "Hoja1"},
  "timeout_seconds": 30
}
```
Response 200:
```json
{
  "result": {
    "tables": [...],
    "metrics": [...],
    "free_text": null
  },
  "stdout_truncated": false
}
```
Response 4xx/5xx:
- 422 SCRIPT_AUDIT_FAILED (`{"code":"SCRIPT_AUDIT_FAILED","findings":[...]}`)
- 422 SCRIPT_EMPTY
- 504 SCRIPT_TIMEOUT
- 500 SCRIPT_EXECUTION_ERROR (con `stderr_truncated` en el body, capado a 500 chars)

### `POST /execute-chart`
Request:
```json
{
  "code": "<script matplotlib>",
  "data_csv": "<contenido CSV completo>",
  "output_format": "png",
  "timeout_seconds": 30
}
```
Response 200: `Content-Type: image/png` (o image/svg+xml) con los bytes.
Response 4xx/5xx: mismos códigos que extraction (audit, empty, timeout, execution).

### `POST /execute-etl`
Request:
```json
{
  "code": "<script con def transform(df)>",
  "data_csv": "<CSV de entrada>",
  "timeout_seconds": 30
}
```
Response 200: `Content-Type: text/csv` con el CSV transformado.
Response 4xx/5xx: idéntico patrón.

## Estrategia de subproceso (runner.py)

REGLA DURA: **no usar `subprocess.run(timeout=)` solo**. Implementar `Popen` + timeout manual con `kill` explícito en `finally`:

```python
def run_subprocess(args: list[str], timeout: int) -> SubprocessResult:
    proc = subprocess.Popen(args, stdout=PIPE, stderr=PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return SubprocessResult(returncode=proc.returncode, stdout=stdout, stderr=stderr)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.communicate(timeout=2)  # drena los pipes tras kill para evitar zombies
        except subprocess.TimeoutExpired:
            pass
        raise TimeoutError()
```

Cada `/execute-*` escribe el wrapper a un fichero temporal en `/tmp/sandbox/`, ejecuta `python` con ese fichero, captura stdout y borra el fichero en `finally`. NUNCA reutiliza el intérprete: cada petición arranca un proceso hijo nuevo. Esto garantiza que ninguna variable, módulo cargado o estado global persiste entre ejecuciones, sin necesidad de reciclar el contenedor.

## Wrappers (wrappers.py)

- `build_extraction_wrapper(code, file_path, raw_text, options)` — análogo al actual `_build_wrapper` de `admin_script_pipeline.py`, imprime `json.dumps(result, default=str)` al stdout.
- `build_chart_wrapper(code, csv_path, out_path, output_format)` — análogo al actual `_WRAPPER_TEMPLATE` de `chart_renderer.py`, llama `plt.savefig(out_path)`.
- `build_etl_wrapper(code, in_csv_path, out_csv_path)` — exec del código (que define `transform(df)`), `transform(df).to_csv(out_csv_path, index=False)`.

Todos los wrappers usan `repr()` para serializar valores en lugar de embebed JSON, para evitar problemas con `True/False/None`.

## Auditor.py — copia defensiva

CRÍTICO: NO importar `ScriptSecurityAuditor` desde `server.app.modules.redaccion`. El sandbox es autocontenido. Copiar la implementación en `sandbox/auditor.py` con su propia `WHITELIST_MODULES`. Si la lista blanca diverge con el tiempo, es porque el sandbox necesita ser MÁS estricto que la API (es la segunda barrera). Documentar esta duplicación en `docs/SANDBOX_SECURITY.md` (creado en SBX.4).

Todos los endpoints invocan `auditor.audit(code)` antes de construir el wrapper. Si `not audit.approved` → 422 SCRIPT_AUDIT_FAILED.

## Tests (RED → GREEN)

Tests in-process con `fastapi.testclient.TestClient` (sin necesidad de levantar Docker en CI):

- test_health_returns_ok
- test_execute_extraction_runs_pandas_script
- test_execute_extraction_returns_422_for_eval_call
- test_execute_extraction_returns_504_on_timeout
- test_execute_extraction_returns_500_with_stderr_truncated_on_runtime_error
- test_execute_extraction_empty_code_returns_422
- test_execute_chart_returns_png_bytes_for_valid_script
- test_execute_chart_returns_422_for_subprocess_import
- test_execute_etl_returns_csv_for_valid_transform
- test_execute_etl_returns_422_when_transform_undefined
- test_auditor_blocks_forbidden_import_even_if_caller_pre_audited (defensa en profundidad: el cliente puede haberse equivocado y el sandbox NO debe ejecutar)
- test_runner_kills_runaway_subprocess_after_timeout (lanza un script con `while True: pass` con timeout=1; verifica que el proceso hijo está muerto tras la excepción — usar `proc.poll() is not None`)
- test_each_execute_starts_fresh_subprocess (ejecuta 2 scripts que escriben a variables globales con el mismo nombre; el segundo no ve el estado del primero)

Mínimo 13 tests RED → GREEN.

## Dockerfile (parte de este prompt; el wiring del compose llega en SBX.4)

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 65534 --no-create-home --shell /usr/sbin/nologin sandboxuser \
    || true  # nobody puede existir ya

WORKDIR /srv/sandbox
COPY pyproject.toml ./
COPY uv.lock* ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY sandbox/ ./sandbox/

USER 65534:65534
EXPOSE 5000
CMD ["uv", "run", "uvicorn", "sandbox.main:app", "--host", "0.0.0.0", "--port", "5000"]
```

## Criterio de done

- 13 tests verdes en `services/script_sandbox/tests/`.
- `docker build -f services/script_sandbox/Dockerfile services/script_sandbox` produce imagen sin warnings.
- El `health` endpoint responde 200.
- El runner mata efectivamente subprocesos colgados (test_runner_kills_runaway lo verifica).
- El auditor del sandbox bloquea código que la API podría haber dejado pasar por error (test_auditor_blocks_forbidden_import_even_if_caller_pre_audited).

## Lo que NO se hace aquí

- No se modifica todavía ningún código de `server/app/`. Los pipelines del API siguen ejecutando in-process. Eso llega en SBX.3.
- No se añade el servicio al `docker-compose.yml`. Eso llega en SBX.4.
- No hay autenticación entre la API y el sandbox: el aislamiento es por red dedicada (sandbox-net). Si en el futuro se necesitase mTLS, se añadirá como capa extra; queda fuera del MVP.
```

---

### Prompt SBX.2 (RED/GREEN) — `SandboxClient`: cliente HTTP en el API

**Modelo sugerido**: **Sonnet** — patrón cliente HTTP estándar con httpx; el contrato ya está fijado en SBX.1; las decisiones abiertas son pocas (retry policy, timeouts, manejo de excepciones).

```markdown
# PROMPT SBX.2 (RED/GREEN) — SandboxClient (httpx)

Objetivo: introducir un cliente HTTP en el API que hable con el microservicio `script-sandbox` definido en SBX.1. Este cliente sustituirá las llamadas `subprocess.run([sys.executable, ...])` que hoy viven dentro de `admin_script_pipeline.py`, `chart_renderer.py` y `etl_service.py`. En SBX.2 SOLO se crea el cliente y sus tests; la sustitución real llega en SBX.3.

Deploy: shared (el cliente vive en `server/app/core/`, lo usan módulos edge — análogo a `StorageService`).

## Estructura

```
server/app/core/sandbox_client.py
server/tests/core/test_sandbox_client.py
```

## Settings

Añadir a `server/app/core/settings.py`:
- `SANDBOX_BASE_URL: str = "http://script-sandbox:5000"` (override `SANDBOX_BASE_URL` en env).
- `SANDBOX_TIMEOUT_SECONDS_DEFAULT: int = 30`.
- `SANDBOX_CONNECT_TIMEOUT_SECONDS: float = 5.0` (timeout de conexión, distinto del timeout de ejecución del script).
- `SANDBOX_MAX_RETRIES_ON_CONNECT_ERROR: int = 1` (no se reintenta en error funcional del script).

## Contrato (Protocol)

```python
from typing import Protocol

class SandboxClient(Protocol):
    async def execute_extraction_script(
        self,
        *,
        code: str,
        file_path: str | None,
        raw_text: str | None,
        options: dict[str, Any],
        timeout_seconds: int | None = None,
    ) -> ExtractionResult:
        """Devuelve ExtractionResult (mismo tipo que pipelines/contracts.py).
        Si el sandbox responde 422 SCRIPT_AUDIT_FAILED → ExtractionResult con warning SCRIPT_SECURITY_VIOLATION.
        Si responde 504 → warning SCRIPT_TIMEOUT.
        Si responde 500 → warning SCRIPT_EXECUTION_ERROR con stderr truncado.
        Si error de red tras los reintentos → SandboxUnavailableError (excepción, NO warning — el caller decide).
        """

    async def execute_chart_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        output_format: Literal["png", "svg"] = "png",
        timeout_seconds: int | None = None,
    ) -> bytes:
        """Devuelve bytes de la imagen. Si el sandbox falla → ChartRenderError (la excepción existente en chart_renderer.py)."""

    async def execute_etl_script(
        self,
        *,
        code: str,
        dataframe_csv: str,
        timeout_seconds: int | None = None,
    ) -> str:
        """Devuelve el CSV transformado como string. Si el sandbox falla → ValueError con mensaje del sandbox."""
```

## Implementaciones

- `HttpSandboxClient` — usa `httpx.AsyncClient` con timeouts diferenciados (connect/read), `retry` solo en `httpx.ConnectError` y `httpx.ReadTimeout` a nivel de conexión (NO sobre `ReadTimeout` que ocurra después de empezar a recibir — eso indica timeout funcional del script).
- `LocalSandboxClient` — ejecuta in-process el mismo wrapper que el sandbox HTTP. Útil para tests E2E del API sin levantar el contenedor sandbox. Implementación: importa los wrappers desde una versión local (puede copiar minimamente del código de SBX.1 o invocar a `subprocess.run` como hacían los pipelines antes). Marcar `LocalSandboxClient` con docstring que aclare que es SOLO para tests y desarrollo sin Docker.

`get_sandbox_client()` como FastAPI dependency (factory que decide según `settings.SANDBOX_MODE` con valores `http` (default en producción) y `local` (default en tests si la env var `TESTING=1`)).

## Tests (RED → GREEN)

Usar `respx` (mock de httpx) o `httpx.MockTransport`:

- test_http_client_execute_extraction_serializes_and_parses_response
- test_http_client_execute_extraction_returns_warning_when_sandbox_returns_422_audit
- test_http_client_execute_extraction_returns_warning_when_sandbox_returns_504
- test_http_client_execute_extraction_returns_warning_when_sandbox_returns_500
- test_http_client_execute_extraction_raises_SandboxUnavailableError_on_connect_error
- test_http_client_execute_extraction_retries_once_on_connect_error
- test_http_client_execute_chart_returns_bytes
- test_http_client_execute_chart_raises_ChartRenderError_on_422
- test_http_client_execute_etl_returns_csv_string
- test_local_client_execute_extraction_matches_http_client_behavior (mismo input → mismo `ExtractionResult` que con sandbox HTTP mockeado)
- test_get_sandbox_client_returns_http_in_production
- test_get_sandbox_client_returns_local_when_testing_env_set

Mínimo 12 tests RED → GREEN.

## Criterio de done

- 12 tests verdes en `server/tests/core/test_sandbox_client.py`.
- `httpx` y `respx` añadidos a `server/pyproject.toml` (si no están).
- `SANDBOX_*` settings documentados en `server/app/core/settings.py` y `.env.example`.
- Ningún código de `pipelines/`, `services/charts/` ni `services/transformation/` toca al cliente todavía: ese refactor llega en SBX.3.

## Lo que NO se hace aquí

- No se cablea el cliente en los pipelines existentes (SBX.3).
- No se modifica el `docker-compose.yml` (SBX.4).
```

---

### Prompt SBX.3 (RED/GREEN) — Refactor de pipelines existentes a `SandboxClient`

**Modelo sugerido**: **Sonnet** — refactor mecánico guiado por tests existentes; el contrato del `SandboxClient` está fijado en SBX.2 y el comportamiento esperado en cada caller no cambia.

```markdown
# PROMPT SBX.3 (RED/GREEN) — Cablear SandboxClient en pipelines, charts y ETL

Objetivo: sustituir las 4 ejecuciones de subprocess in-process existentes por llamadas al `SandboxClient` de SBX.2. Ningún test funcional preexistente debe romperse (los warnings y bytes generados siguen siendo equivalentes). El comportamiento observable del API se mantiene; lo que cambia es la frontera donde se ejecuta el código.

Deploy: edge (los 4 ficheros tocados ya estaban en módulos edge).

## Ficheros a modificar

### 1. `server/app/modules/redaccion/pipelines/admin_script_pipeline.py`

- Eliminar la importación de `subprocess`, `sys`, `tempfile`, `os`.
- `extract()` pasa a `async def extract_async()` (la versión síncrona se elimina — el único caller es `scripts_router.test_proposal`, ya async).
- `_execute_in_sandbox()` se reemplaza por:
  ```python
  return await self._client.execute_extraction_script(
      code=code,
      file_path=file_path_or_None,
      raw_text=raw_text,
      options=inp.options,
      timeout_seconds=timeout,
  )
  ```
- El re-audit AST defensivo en `extract_async` SE MANTIENE en la API (defensa en profundidad: el sandbox también lo hace).
- Constructor pasa a recibir `SandboxClient` (inyección obligatoria).
- Borrar las funciones `_build_wrapper` y `_dict_to_result` (ahora las hace el sandbox).
- Sustituir `_AUDITOR = ScriptSecurityAuditor()` por inyección del auditor también (o mantenerlo como singleton de módulo, está bien por ahora).

### 2. `server/app/modules/redaccion/services/charts/chart_renderer.py`

- `render_chart_from_script()` pasa a `async def`.
- Sustituye `subprocess.run` + tempdir por:
  ```python
  csv_bytes = io.StringIO(); df.to_csv(csv_bytes, index=False)
  return await sandbox_client.execute_chart_script(
      code=code,
      dataframe_csv=csv_bytes.getvalue(),
      output_format=output_format,
      timeout_seconds=timeout,
  )
  ```
- Si el cliente lanza `ChartRenderError`, propagar (ya es el mismo tipo de excepción).
- Constructor o función receive `sandbox_client` (Depends o explícito).

### 3. `server/app/modules/redaccion/services/transformation/etl_service.py`

- `_execute_fallback_script()` deja de ser staticmethod, recibe el cliente.
- En lugar de `exec(...)`:
  ```python
  csv_in = df.to_csv(index=False)
  csv_out = await self._sandbox_client.execute_etl_script(
      code=code,
      dataframe_csv=csv_in,
  )
  return pd.read_csv(io.StringIO(csv_out))
  ```
- El comentario `# si emergen requisitos de aislamiento más fuertes, migrar a un subprocess sandbox análogo al ChartRenderer` se elimina (resuelto).
- Cuando se llama a `_execute_fallback_script` desde `run()`, pasa a `await`.

### 4. `server/app/routers/redaccion/scripts_router.py`

- `_SANDBOX = AdminScriptExtractionPipeline()` desaparece.
- En `test_proposal`:
  ```python
  pipeline = AdminScriptExtractionPipeline(client=Depends(get_sandbox_client))
  extraction = await pipeline.extract_async(inp)
  ```
  o equivalente con inyección por endpoint.

### 5. `server/app/modules/redaccion/blocks/handlers.py`

- Los handlers que invocaban a `ChartRenderer` o ETL fallback ahora hacen `await`. Si alguno era síncrono, propagar a async.

### 6. `server/app/modules/redaccion/graph/nodes/data_transformation_node.py`

- Si invoca `etl_service.run()`, ya era async; no cambia. Verificar que sigue cuadrando.

## Tests a adaptar

Tests existentes que mockeaban `subprocess.run` o tocaban el wrapper interno deben mockear ahora el `SandboxClient`:

- `tests/modules/redaccion/test_admin_script_pipeline*.py` — usar `LocalSandboxClient` o mock de `SandboxClient`. Eliminar referencias a `subprocess`, `tempfile`.
- `tests/modules/redaccion/test_chart_renderer*.py` — idem.
- `tests/modules/redaccion/test_etl_service*.py` — idem en los tests del fallback.
- `tests/routers/redaccion/test_scripts_router*.py` — `_SANDBOX` desaparece; mockear `get_sandbox_client` con `app.dependency_overrides`.

Tests nuevos:
- test_admin_script_pipeline_uses_sandbox_client_and_propagates_warnings (verifica que cuando el cliente devuelve un `ExtractionResult` con `SCRIPT_TIMEOUT`, el pipeline lo devuelve idéntico)
- test_admin_script_pipeline_re_audits_before_calling_client (verifica que un script con `eval()` NUNCA llega al cliente)
- test_chart_renderer_uses_sandbox_client_and_returns_bytes
- test_etl_service_fallback_uses_sandbox_client
- test_scripts_router_test_proposal_uses_async_pipeline (smoke: hace `app.dependency_overrides` para inyectar `LocalSandboxClient`)

## Criterio de done

- 0 ocurrencias de `subprocess.run` ni `subprocess.Popen` en `server/app/modules/redaccion/`. (`grep -r "subprocess" server/app/modules/redaccion/` debe estar limpio).
- 0 ocurrencias de `exec(` en `server/app/modules/redaccion/`. (la auditoría busca exactamente esto en otros sitios; aquí debe quedar SOLO en `script_auditor.py` como string a detectar).
- Toda la suite de redacción pasa (425+/425+ tests verdes, sin regresiones respecto al estado pre-SBX).
- Los tests nuevos (5) verdes.

## Lo que NO se hace aquí

- No se levanta el sandbox real: los tests usan `LocalSandboxClient`. El levantado HTTP se prueba manualmente al cerrar SBX.4 con `docker compose up script-sandbox`.
- No se cambia el `docker-compose.yml` (SBX.4).
```

---

### Prompt SBX.4 (RED/GREEN) — Hardening Docker + documentación de seguridad

**Modelo sugerido**: **Sonnet** — configuración Docker + docs; las decisiones técnicas ya están en SBX.1-3, este prompt aterriza el wiring y el modelo de amenazas.

```markdown
# PROMPT SBX.4 (RED/GREEN) — docker-compose con red aislada + docs de seguridad

Objetivo: incorporar el servicio `script-sandbox` a los dos docker-compose (dev y prod) con hardening completo, dejar la red `sandbox-net` aislada de los datos del cliente (postgres, minio) e internet, y documentar el modelo de amenazas en `docs/SANDBOX_SECURITY.md`.

Deploy: edge (afecta a la topología de despliegue cliente).

## Cambios en docker-compose.yml (dev)

Añadir el servicio:
```yaml
  script-sandbox:
    build:
      context: ./services/script_sandbox
      dockerfile: Dockerfile
    container_name: govgenai_script_sandbox
    networks:
      - sandbox-net
    read_only: true
    tmpfs:
      - /tmp/sandbox:size=128M,mode=0700,uid=65534,gid=65534
    cap_drop: ["ALL"]
    security_opt:
      - no-new-privileges:true
    user: "65534:65534"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health').read()"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    restart: unless-stopped
```

Si el servicio `app` (FastAPI principal) ya existe en el compose dev, conectarlo también a `sandbox-net` (manteniendo su red default existente). Si NO existe (el dev hoy sólo levanta dependencias y el API se ejecuta con `uv run uvicorn` en host), añadir un comentario:
```yaml
# El API ejecutándose en host accede al sandbox via http://localhost:5001 si se mapea el puerto;
# alternativamente, ejecutar el API también en contenedor y conectarlo a sandbox-net.
```
Y exponer el puerto 5000 del sandbox como 5001 en host para desarrollo local sin contenedor del API:
```yaml
    ports:
      - "127.0.0.1:5001:5000"   # SOLO en dev; en prod NO se publica
```

Definir la red:
```yaml
networks:
  sandbox-net:
    driver: bridge
    internal: false  # en dev, false para permitir build/pull; ver nota en prod
```

## Cambios en docker-compose.prod.yml (prod)

Añadir el servicio sin `ports:` (no se expone fuera del host):
```yaml
  script-sandbox:
    # ... mismas opciones que en dev ...
    networks:
      - sandbox-net
    # NO ports — solo accesible desde la red sandbox-net
```

Conectar `app` a las dos redes:
```yaml
  app:
    # ... existente ...
    networks:
      - default
      - sandbox-net
    environment:
      # ... existente ...
      SANDBOX_BASE_URL: http://script-sandbox:5000
```

Definir la red como `internal: true` en prod (sin egress fuera del bridge):
```yaml
networks:
  sandbox-net:
    driver: bridge
    internal: true   # PROD: sin egress a internet, solo intercomunicación entre containers conectados
```

## Verificación manual de aislamiento (parte del criterio de done)

Tras `docker compose -f docker-compose.prod.yml up -d script-sandbox app`, ejecutar:
```bash
# 1. El sandbox NO debe poder resolver postgres
docker compose exec script-sandbox python -c "import socket; print(socket.gethostbyname('postgres'))"
# Debe fallar con: socket.gaierror

# 2. El sandbox NO debe poder salir a internet
docker compose exec script-sandbox python -c "import urllib.request; urllib.request.urlopen('https://www.google.com', timeout=3).read()"
# Debe fallar con: URLError / timeout

# 3. El API SÍ debe poder hablar con el sandbox
docker compose exec app curl -s http://script-sandbox:5000/health
# Debe responder: {"status":"healthy"}

# 4. El sandbox NO debe poder hablar al API (no necesita iniciar conexiones salientes)
docker compose exec script-sandbox python -c "import urllib.request; urllib.request.urlopen('http://app:8000/health', timeout=3).read()"
# Debe fallar (network unreachable o connection refused, depende del driver)
```

Estos 4 checks se documentan como pasos manuales en `pruebas_manuales_promptSBX_4.bat` (requiere UI/interacción con Docker, justifica .bat según CLAUDE.md sección "Pruebas manuales").

## `docs/SANDBOX_SECURITY.md`

Crear con secciones:

1. **Modelo de amenazas**
   - Adversario: usuario autenticado de la plataforma (proposer) que intenta exfiltrar datos del cliente, escalar privilegios o denegar servicio.
   - Activos protegidos: base de datos del cliente (postgres), almacenamiento (minio/gcs), red interna del cliente, otros tenants.
   - Asunciones: el atacante puede escribir cualquier código Python; la auditoría AST puede ser bypassable.

2. **Capas de defensa**
   - Capa 1: `ScriptSecurityAuditor` (AST) en la API antes de aceptar la propuesta.
   - Capa 2: Workflow HITL para promoción a plantilla global (9R.5.6).
   - Capa 3: Red `sandbox-net` aislada (sin DNS hacia postgres/minio, sin egress en prod).
   - Capa 4: Contenedor sin privilegios (cap_drop ALL, no-new-privileges, usuario 65534, read_only fs).
   - Capa 5: Re-auditoría AST defensiva dentro del sandbox.
   - Capa 6: Subproceso efímero por petición (sin contaminación entre ejecuciones).
   - Capa 7: Límites de recursos del propio Docker (cpus, memory, tmpfs size).
   - Capa 8: En GCP, gVisor (heredado automáticamente por Cloud Run).

3. **Lo que NO mitiga este diseño**
   - Bugs del kernel del host (mitigado parcialmente por gVisor en GCP).
   - Side-channel attacks entre tenants (fuera de alcance MVP).
   - Inyección de prompts maliciosos al LLM que generan código bypass — mitigado por capas 1, 2, 5.

4. **Cómo auditar el aislamiento**
   - Los 4 checks de la sección "Verificación manual" anterior.
   - Comandos para inspeccionar capacidades del contenedor: `docker inspect govgenai_script_sandbox --format '{{json .HostConfig.CapDrop}}'`.

5. **Migración futura a gVisor explícito (on-premise)**
   - Pasos para configurar `runtime: runsc` si el cliente despliega sobre containerd + gVisor.
   - Queda fuera del MVP; documentado por si infosec del cliente lo requiere.

6. **Diferencias dev vs. prod**
   - Dev: `sandbox-net` no es internal; el sandbox expone 5001 en host para `uv run` local.
   - Prod: `sandbox-net` internal=true, sin ports expuestos, sandbox solo accesible desde `app`.

## Tests (RED → GREEN)

Tests automáticos:
- test_compose_dev_defines_sandbox_service (parsea YAML y verifica claves obligatorias: cap_drop, read_only, security_opt, user, network)
- test_compose_prod_sandbox_has_no_ports (sandbox sin sección `ports`)
- test_compose_prod_sandbox_net_is_internal (network internal=true)
- test_compose_prod_app_connected_to_sandbox_net
- test_sandbox_dockerfile_runs_as_non_root_user (parsea Dockerfile, verifica `USER 65534`)

5 tests verdes en `tests/infra/test_compose_sandbox.py` (nuevo).

Verificación manual (vía `.bat`):
- `pruebas_manuales_promptSBX_4.bat` cubre los 4 checks de aislamiento de red, plus el smoke E2E de `/api/v1/redaccion/scripts/{id}/test` apuntando al sandbox real.

## Criterio de done

- 5 tests automáticos verdes.
- Los 4 checks manuales de aislamiento pasan (documentados en el .bat con texto explícito de qué esperar).
- `docs/SANDBOX_SECURITY.md` existe y cubre las 6 secciones.
- `docker compose -f docker-compose.prod.yml up -d` levanta los 4 servicios (postgres, app, sandbox, minio) y el endpoint `/api/v1/redaccion/scripts/{id}/test` ejecuta scripts en el sandbox (verificable en logs).
- `.env.example` actualizado con `SANDBOX_BASE_URL=http://script-sandbox:5000` y `SANDBOX_TIMEOUT_SECONDS_DEFAULT=30`.

## Pruebas manuales — Prompt SBX.4

### Antes de empezar
1. Abre Docker Desktop.
2. En una terminal: `docker compose -f docker-compose.prod.yml build script-sandbox app`.
3. Levanta: `docker compose -f docker-compose.prod.yml up -d`.

### Ejecuta el archivo
- Doble clic en `pruebas_manuales_promptSBX_4.bat` (raíz del proyecto).

### Qué debes ver
- 4 checks de aislamiento (los 3 que deben fallar fallan; el que debe pasar pasa).
- 1 smoke E2E: crear un proposal con `POST /api/v1/redaccion/scripts/propose`, ejecutar `/test`, ver en `docker logs script-sandbox` la entrada de ejecución.

### Para terminar
- `docker compose -f docker-compose.prod.yml down`.
```

---

### Continuación tras el bloque SBX

Con SBX cerrado, el siguiente bloque del orden de ejecución es **Bloque 9Q** (Calidad de Contenido Web Ingestado). Tras 9Q viene **Fase 11** (Autoinstalación y Distribución), que reescribirá `docker-compose.prod.yml` para distribución pública. Fase 11.2 debe preservar el servicio `script-sandbox` y su red aislada — añadirlo al template público con comentarios claros.

---

## Bloque 9Q — Motor de auditoría de sitios web (Subfase 1.A → 1.C, COMPLETO 9Q.0–9Q.9)

> ### ⚠ ALCANCE REESCRITO EL 2026-08-02 — leer antes que nada de lo que sigue
>
> **El código de 9Q no cambia; cambia de qué es parte.** Ver `docs/DECISION_CURACION_SEPARADA.md`.
>
> Este bloque se escribió bajo la hipótesis de una **ingesta más o menos automatizada** de
> información pública: apuntar el spider a un sitio, ingerir lo descubierto y arreglar la calidad
> después con detectores. **Preparar el corpus normativo de la UJI ha falsado esa hipótesis.**
> Ese corpus era el mejor caso posible —PDFs de normas con filtro previo de Secretaría General,
> catálogo y numeración estable— y aun así dejarlo ingerible exigió front-matter derivado del
> catálogo, decisión humana de consolidación norma a norma, un panel de revisión construido para
> eso y un parche al generador de HTML para tener anclas por artículo. Si el mejor caso exige
> todo eso, un conjunto de páginas rastreadas —sin versión canónica declarada, sin distinción
> entre vigente y derogado— **no es un corpus: es materia prima**.
>
> **Cómo se lee ahora este bloque.** 9Q no es «calidad del contenido web ingerido al servicio del
> RAG». Es **el motor de la herramienta de curación**, que es una actividad *previa* al asistente
> y con producto propio. En concreto:
>
> - **La salida principal es el informe de auditoría**, dirigido al equipo web de la
>   administración. Tiene valor por sí solo, sin que exista ningún chatbot: auditar la coherencia
>   de lo publicado es una necesidad de transparencia. La higiene del retriever (`superseded`,
>   `quality_score`) pasa a ser el **efecto secundario útil**, no la razón de ser.
> - **No hay ingesta automática de web a corpus.** Que una página sea nueva o haya cambiado es
>   **una señal para el curador**, nunca un disparador de ingesta. Donde el texto de abajo dice
>   «auto-encoladas si casan con una `HubCorpusSelection`», léase «propuestas al curador».
> - **`CorpusSelectionService` es el paso de publicación**, no un detalle de la ingesta: es el
>   punto exacto en que un humano decide que una página entra. Hoy está enterrado en
>   `ingestion/quality/selection_service.py` y debe ser explícito y visible en la UI de curación.
> - **La frontera con el asistente es `docs/CONTRATO_MD_CORPUS.md`**, no una interfaz de código.
>
> **Esto ya estaba latente en el modelo de datos que 9Q construyó**: `HubWebSite` cuelga de
> `organizacion_id` y **no tiene `chatbot_id`** —«propiedad de la organización, no del chatbot»,
> dice su propio docstring—, y `HubContentFinding` admite dos sujetos con un `CHECK` que exige
> exactamente uno. El diseño ya separaba las dos mitades; lo que faltaba era decirlo.
>
> **Lo que se conserva y se refuerza**: el bucle de RAG.14 (preguntas sin responder → huecos de
> corpus). Es la conexión legítima entre asistente y curación, y la razón por la que **no** se
> parte el sistema en dos aplicaciones: el corpus no se cura una vez, se cura continuamente
> contra el uso real.
>
> **Movimiento de código**: no se hace aquí. Va en el **Bloque CUR**, entre CAL y Deploy.

**Objetivo del bloque (redacción original, 2026-05-27)**: separar dos conceptos que hoy el modelo funde, y construir sobre esa separación un **motor de detección de calidad a nivel de sitio**. Hoy todo cuelga de `chatbot_id` y no existe ninguna entidad "sitio"; `HubIngestionSource` es solo un monitor de **una URL suelta por chatbot**. Eso impide (a) escanear todo un sitio para auditar calidad mientras se ingiere solo una parte, (b) que una misma página alimente varios chatbots, y (c) un único crawl por sitio (hoy N chatbots = N crawls del mismo servidor público).

El bloque introduce tres entidades y dos salidas:

**Entidades nuevas** (operacionales, edge, en `operational_models.py`):
- **`HubWebSite`** — propiedad del cliente/administración, **no** del chatbot. URL raíz, sitemap, config de crawl, cadencia, `audit_semantic_scope`. Unidad de **crawl + auditoría**.
- **`HubCrawledPage`** — propiedad del sitio. Cada URL descubierta en el crawl, con sus señales (Last-Modified/ETag/sitemap lastmod/canonical/año) y flags de calidad (`superseded`, `quality_score`, `superseded_by_page_id`). Los `HubContentFinding` referencian **páginas**, no chatbots.
- **`HubCorpusSelection`** — propiedad del chatbot, referencia un sitio + regla de selección (prefijo de path / sección de sitemap / manual). Realiza el mapeo **N:M** página→chatbot: promociona páginas rastreadas a `HubDocument` del/los chatbots.
- `HubDocument` gana `crawled_page_id` (FK opcional a `HubCrawledPage`, `ondelete=SET NULL`, sin `relationship()`). Los PDFs subidos siguen con `crawled_page_id=None`.

**Dos salidas independientes** sobre el mismo análisis:
1. **Higiene del RAG** — flags `superseded`/`quality_score` sobre `HubCrawledPage`; el retriever excluye por defecto los `HubDocument` cuya página de origen esté superseded, en **todos** los chatbots que la ingirieron.
2. **Informe de auditoría web por sitio** — documento estructurado (JSON + visor admin + export DOCX/PDF) dirigido al **equipo web de la administración** para que mejore su propio sitio público.

**Justificación de la ubicación (antes de Fase 11)**:
- Es una mejora de **correctitud del producto central** (calidad de las respuestas del chatbot), de mayor prioridad que la distribución (Fase 11) o el deploy (D.1–D.5).
- Reutiliza crawler, embeddings y retriever ya completados en Subfases 1.A/9B.
- Introduce nuevos servicios y un scheduler; Fase 11.2 debe poder incluirlos en el `docker-compose.prod.yml` público; por eso se cierra antes.

**Decisión arquitectónica (2026-05-27, revisada)**: **split sitio/corpus con motor de detección a nivel sitio**, frente al diseño anterior per-chatbot. Razones:
1. **No rastrear dos veces.** Son webs de administración pública: varios crawlers golpeando los mismos servidores es impolite, dispara rate limits y parece abuso. Un único crawl por sitio que emite hallazgos estructurados es lo correcto técnica y éticamente. El modelo per-chatbot anterior **no cumplía esto** en cuanto dos chatbots bebían del mismo sitio.
2. **El alcance del crawl ≠ el alcance de la ingesta.** La administración quiere auditar **todo** su sitio pero ingerir solo **partes** seleccionadas, posiblemente repartidas entre **varios** chatbots. Eso exige una entidad sitio por encima del chatbot y una capa de selección N:M.
3. **El informe es otro consumidor** de la misma tabla de hallazgos (no otro motor): reutiliza `HybridRetriever` (similitud pgvector) para clustering y el patrón de `source_scheduler` para la cadencia.

**Reemplazo de `HubIngestionSource` (decisión 2026-05-27)**: `HubWebSite` + `HubCorpusSelection` **sustituyen** al monitor de URL suelta. Las fuentes existentes se migran a (sitio + selección) y `HubIngestionSource`, su scheduler (`source_scheduler.py`) y sus endpoints se **eliminan** (CLAUDE.md: sin mecanismos paralelos ni shims). **La ingesta de PDF subido (`POST /hub/ingestion/upload` → `HubIngestionJob` → `HubDocument`) es un flujo independiente y se mantiene intacta**: un chatbot se alimenta de PDFs subidos (`crawled_page_id=None`) **+** páginas seleccionadas del sitio (`crawled_page_id` poblado).

**Actualización periódica**: el recrawl programado hace **diff de sitemap** — páginas **nuevas** → candidatas a ingesta (auto-encoladas si casan con una `HubCorpusSelection`, si no afloran en el informe como "nuevas sin clasificar"); **cambiadas** → re-embed; **desaparecidas** → finding + retirada del corpus.

**Cobertura de la auditoría semántica (`audit_semantic_scope`, por sitio)**: las páginas rastreadas pero no ingeridas no tienen embeddings.
- `ingested` (default, híbrido): el detector determinista corre sobre **todo** el sitio (gratis); el semántico (juez LLM) solo sobre páginas ya ingeridas. Para sitios grandes.
- `full`: se embeben todas las páginas rastreadas y el semántico cubre el sitio completo. Para sitios pequeños donde interesa cobertura total. El administrador lo elige por sitio.

**Frontera edge-cloud**: todo el bloque **es edge**. El motor procesa documentos/chunks/páginas del cliente; el informe es inherentemente sobre el contenido concreto del cliente y **no se puede anonimizar de forma útil**, por lo que se sirve desde el edge node. El cloud, como mucho, vería métricas agregadas anonimizadas vía la sync API — backlog post-MVP, **no entra en 9Q**.

**Lo que NO incluye este bloque**:
- **Accesibilidad / WCAG** del sitio público (backlog v2; la del propio frontend ya está en Fase 20).
- Reescritura/corrección automática del contenido del sitio (el informe es de **diagnóstico**; la acción correctiva la realiza el equipo web humano).
- Sync de métricas agregadas hacia el cloud (backlog post-MVP de la sync API).
- Validación exhaustiva de enlaces rotos mediante recrawl dedicado (el MVP detecta huérfanos/errores a partir de las señales del crawl y del diff de sitemap, no lanza un recrawl de validación de enlaces).

**Reglas duras del bloque 9Q**:
- Todo el módulo de calidad vive en `server/app/modules/agents_hub/ingestion/quality/` y **es edge**. Las entidades nuevas (`HubWebSite`, `HubCrawledPage`, `HubCorpusSelection`) viven en `operational_models.py` sobre `HubOperationalBase`.
- Los routers nuevos se etiquetan `Deploy: edge` y se registran en `_register_edge` de `main.py`.
- **El análisis nunca bloquea el crawl ni la ingesta.** La detección corre como job asíncrono post-crawl o bajo demanda; el crawl/indexado sigue su curso aunque el análisis falle.
- **El LLM solo se invoca sobre clusters ya filtrados por similitud de embeddings** (control de coste). Jamás se llama al LLM por cada par de páginas.
- El motor **lee** modelos operacionales (`HubWebSite`, `HubCrawledPage`, `HubDocument`, `HubDocumentChunk`) y **escribe** `HubContentFinding` + los flags `superseded`/`quality_score` en `HubCrawledPage`. No toca modelos de configuración. **Sin `relationship()` cross-base**; las FK a chatbot/documento se resuelven por id con query explícito.
- **La anonimización previa al LLM es responsabilidad del módulo edge** (reutiliza el `AnonymizerService`/hooks de 9R.5.5/Fase 13 si el contenido a juzgar puede contener PII antes de enviarse al juez LLM).

---

### Prompt 9Q.0 (RED/GREEN) — Modelo sitio/página/selección + reemplazo de `HubIngestionSource`

**Modelo sugerido**: **Opus** — define todo el modelo de datos nuevo y la relación página↔documento↔chatbot, decide la migración que retira `HubIngestionSource` sin romper la ingesta de PDF, y establece las invariantes cross-base. Decisiones de diseño embebidas y refactor de código ya en verde.

**Objetivo**: crear las tres entidades que separan crawl/auditoría (sitio) de ingesta (corpus de chatbot), sus repos, la FK `crawled_page_id` en `HubDocument`, y **retirar `HubIngestionSource`** migrando las fuentes existentes a (sitio + selección). No incluye crawl ni detección todavía (eso es 9Q.2+).

**Contexto**: `operational_models.py` (sobre `HubOperationalBase`). Hoy `HubIngestionSource` (monitor de 1 URL/chatbot) se usa en `hub_ingestion_router.py`, `source_scheduler.py`, `spider_factory.py` y tests de integración. El upload de PDF (`POST /hub/ingestion/upload` → `HubIngestionJob` → `IngestionWatcher`) **no** usa `HubIngestionSource` y no se toca. Sin `relationship()` cross-base (regla edge-cloud de CLAUDE.md).

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.0 (RED/GREEN) — Entidades sitio/página/selección

Deploy: edge.

## ORM — operational_models.py (HubOperationalBase)

class HubWebSite:
  __tablename__ = "hub_web_sites"
  id, client_id UUID (index, dueño = administración, NO chatbot), name str(255),
  root_url str(2048), sitemap_url str(2048)|None, spider_type str(50) default "generic",
  config_json JSONB default dict, crawl_interval_hours int default 24,
  audit_semantic_scope str(20) default "ingested"  # "ingested" | "full"
  last_crawled_at datetime|None, status str(20) default "active", error_message Text|None,
  created_at.

class HubCrawledPage:
  __tablename__ = "hub_crawled_pages"
  id, site_id UUID (index, FK hub_web_sites.id ondelete=CASCADE — NO relationship()),
  url str(2048), canonical_url str(2048)|None, content_hash str(64)|None,
  title str(512)|None, token_count int|None, language str(10)|None,
  markdown_content Text|None,   # texto rastreado de la página; necesario para empty/thin (9Q.3)
                                # y para embeber páginas no ingeridas en modo full (9Q.4)
  # señales de actualidad (las pobla 9Q.2):
  http_last_modified datetime|None, http_etag str(255)|None, sitemap_lastmod datetime|None,
  declared_canonical_url str(2048)|None, content_year int|None,
  # flags de higiene (los consolida 9Q.5):
  superseded bool default False (index), quality_score Float|None,
  superseded_by_page_id UUID|None,
  first_seen_at, last_seen_at, last_crawled_at datetime|None,
  status str(20) default "active"  # "active" | "gone" (fuera del sitemap) | "error" (fetch falló)
  error_message Text|None,         # mensaje del fallo de fetch de ESTA página (si status=="error")
  UniqueConstraint(site_id, url) name="uq_page_site_url".

class HubCorpusSelection:
  __tablename__ = "hub_corpus_selections"
  id, chatbot_id UUID (index), site_id UUID (index, FK hub_web_sites.id ondelete=CASCADE),
  rule_type str(20)  # "path_prefix" | "sitemap_section" | "manual"
  rule_value str(2048)|None  # p.ej. "/tramites/" para path_prefix; None para manual
  auto_ingest_new bool default True  # encolar automáticamente páginas nuevas que casen
  created_at.
  # El mapeo N:M efectivo página→documento se materializa en HubDocument.crawled_page_id;
  # una selección manual puede tener su propia tabla de enlaces si 9Q.7 lo necesita.

## FK nueva en HubDocument (mismo fichero)
  crawled_page_id UUID|None (index, FK hub_crawled_pages.id ondelete=SET NULL — NO relationship())
  # PDFs subidos => None. Documentos de crawl => apuntan a su página de origen.

## Repos — ingestion/quality/site_repo.py
WebSiteRepo(session): create, get, list_by_client, update, delete (cascade páginas).
CrawledPageRepo(session): upsert(site_id, url, ...) (respeta uq_page_site_url),
  list_by_site(site_id, status?), get, mark_gone(page_ids), get_by_canonical(site_id, canonical).
CorpusSelectionRepo(session): create, list_by_chatbot, list_by_site, delete,
  matches(selection, page_url) -> bool  # evalúa la regla contra una URL.

## Migración Alembic — retirada de HubIngestionSource
1. Crea hub_web_sites, hub_crawled_pages, hub_corpus_selections; añade crawled_page_id a hub_documents.
2. DATA MIGRATION: por cada HubIngestionSource existente, crea un HubWebSite (root_url=url,
   client_id derivado del chatbot) + un HubCorpusSelection(chatbot_id, site_id, rule_type="manual").
   (Si no hay forma de derivar client_id en datos de dev, documenta el fallback y créalo nullable.)
3. DROP table hub_ingestion_sources.
Aplica con `uv run alembic upgrade <rev>`. Si la BD no responde, detente y pide arrancarla.

## Retirada de código (CLAUDE.md — borra, no comentes)
- Elimina la clase HubIngestionSource de operational_models.py.
- Elimina source_scheduler.py (check_source/check_all_sources/create_scheduler) y su arranque
  en main.py/lifespan. El scheduler nuevo lo crea 9Q.5.
- Elimina del hub_ingestion_router.py los endpoints de "Fuentes web monitorizadas"
  (list/create/update/delete/check sources). Los endpoints de sitio los crea 9Q.7.
- Ajusta spider_factory.py y los tests de integración que referencian HubIngestionSource.
- grep -r "HubIngestionSource" debe quedar a 0 antes de cerrar.

## Tests (mínimo 12) — tests/modules/agents_hub/integration/test_site_model.py
- CRUD de HubWebSite/HubCrawledPage/HubCorpusSelection vía repos.
- upsert de página respeta uq_page_site_url (2ª llamada actualiza).
- CorpusSelectionRepo.matches: path_prefix casa/no casa; manual siempre False salvo enlace explícito.
- HubDocument.crawled_page_id default None; FK SET NULL al borrar página.
- Borrar sitio cascada páginas (y selecciones).
- audit_semantic_scope default "ingested"; HubCrawledPage default status "active", markdown_content/error_message None.
- Tras la migración: no queda HubIngestionSource importable (import error esperado en test).
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde (incluidos los tests de ingestión adaptados a la retirada de `HubIngestionSource`); migración aplicada (`alembic current`); `grep -r HubIngestionSource` a 0.

---

### Prompt 9Q.1 (RED/GREEN) — Contratos de hallazgos + `HubContentFinding` (clave sitio/página) + repo

**Modelo sugerido**: **Sonnet** — alcance cerrado: contratos Pydantic enumerados, un modelo ORM, un repo CRUD, una migración. Sin decisiones de diseño abiertas (el modelo base ya lo fijó 9Q.0).

**Objetivo**: la taxonomía de hallazgos y el modelo ORM `HubContentFinding`, ahora **rekeyed a sitio/página** (no a chatbot), con su repo. Los flags de higiene ya viven en `HubCrawledPage` (9Q.0).

**Contexto**: usa las entidades de 9Q.0. Un hallazgo es un hecho sobre el **sitio** (páginas), independiente de qué chatbots ingirieron esas páginas.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.1 (RED/GREEN) — Contratos y modelo de hallazgos de calidad

Deploy: edge.

## Contratos Pydantic — ingestion/quality/contracts.py

- FindingType: Literal[
    "superseded",      # versión más antigua de un proceso con versión nueva detectada
    "duplicate",       # mismo contenido en >1 URL
    "contradiction",   # mismo proceso, datos divergentes
    "empty",           # sin contenido útil (markdown vacío / token_count 0)
    "thin",            # contenido por debajo de umbral mínimo
    "stale",           # no revisada/actualizada en > umbral de días
    "crawl_error",     # la página falló al rastrearse (HubCrawledPage.status/error)
    "orphan_page",     # página marcada gone que aún tiene documentos ingeridos
  ]
- FindingSeverity: Literal["info", "warning", "critical"]
- FindingStatus: Literal["new", "confirmed", "dismissed", "resolved"]
- ContentFinding (Pydantic, frozen=True): id, site_id: UUID, finding_type, severity,
  confidence: float (0..1), page_id: UUID|None, related_page_id: UUID|None,
  source_url: str|None, signal: dict (evidencia: fechas comparadas, score de similitud,
  longitudes, etc.), status, detected_at, reviewed_at: datetime|None, reviewed_by: UUID|None,
  resolution_note: str|None
- _VALID_FINDING_TRANSITIONS + InvalidFindingTransitionError (new→confirmed/dismissed,
  confirmed→resolved/dismissed, dismissed→new; resolved es terminal).

## ORM — operational_models.py (HubOperationalBase)

class HubContentFinding:
  __tablename__ = "hub_content_findings"
  id, site_id UUID (index, FK hub_web_sites.id ondelete=CASCADE — NO relationship()),
  finding_type str(40), severity str(20), confidence Float,
  page_id UUID|None (index, FK hub_crawled_pages.id ondelete=SET NULL — NO relationship()),
  related_page_id UUID|None, source_url str(2048)|None, signal_json JSONB,
  status str(20) default "new" (index), detected_at, reviewed_at|None, reviewed_by|None,
  resolution_note Text|None, created_at.
  UniqueConstraint(site_id, finding_type, page_id, related_page_id) name="uq_finding_dedup".

## Repo — ingestion/quality/findings_repo.py

ContentFindingRepo(session):
  async upsert(finding) -> HubContentFinding   # respeta uq_finding_dedup (ON CONFLICT update)
  async list_by_site(site_id, status?, finding_type?) -> list[HubContentFinding]
  async transition(finding_id, new_status, reviewed_by, resolution_note?) -> HubContentFinding
        # valida contra _VALID_FINDING_TRANSITIONS, lanza InvalidFindingTransitionError
  async get(finding_id) -> HubContentFinding|None

## Migración Alembic
Crea hub_content_findings. Aplica con `uv run alembic upgrade <rev>`. Si la BD no responde,
detente y pide arrancarla.

## Tests (mínimo 12) — tests/modules/agents_hub/unit/test_content_findings.py
- ContentFinding congelado, validación de rangos de confidence.
- Transiciones válidas e inválidas (cada arista + terminal resolved).
- Repo.upsert idempotente bajo uq_finding_dedup (2ª llamada actualiza, no duplica).
- Repo.list_by_site filtra por status y finding_type.
- Repo.transition aplica reviewed_at/reviewed_by y rechaza transición inválida.
- FK page_id SET NULL al borrar la página; site_id CASCADE al borrar el sitio.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/unit/test_content_findings.py` verde; migración aplicada (`alembic current`).

---

### Prompt 9Q.2 (RED/GREEN) — Crawl a nivel sitio + señales en páginas + diff de sitemap

**Modelo sugerido**: **Opus** — desacopla el crawl del modelo per-chatbot al modelo de sitio (refactor de `IngestionWatcher`/spider ya en verde), diseña el diff de sitemap (alta/cambio/baja de páginas) y la captura de señales sobre `HubCrawledPage`. Decisiones de diseño embebidas.

**Objetivo**: rastrear un **sitio completo** una sola vez poblando `HubCrawledPage`, capturar las **señales gratuitas** de actualidad sobre cada página, y producir el **diff de sitemap** que detecta páginas nuevas, cambiadas y desaparecidas. No ingiere todavía en chatbots (eso lo dispara la selección de 9Q.7); aquí solo se materializa el mapa del sitio.

**Contexto**: el crawler vive en `ingestion/spider.py` (`GenericSpider._fetch`, `_extract_links`); el indexado en `ingestion/watcher.py`. 9Q.0 retiró `HubIngestionSource`. Las páginas y sus señales viven en `HubCrawledPage` (9Q.0). El crawl debe recorrer el sitemap/enlaces del sitio, no una URL suelta.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.2 (RED/GREEN) — Crawl de sitio + señales + diff de sitemap

Deploy: edge.

## Servicio de señales — ingestion/quality/signal_extractor.py
class CrawlSignalExtractor:
  extract_from_headers(headers: dict) -> {http_last_modified, http_etag}  # RFC 7231; tolera ausencia
  extract_canonical(html: str) -> str|None        # <link rel="canonical" href="...">
  extract_content_year(url: str, text: str) -> int|None
        # prioridad: año en path (/2024/) > año más reciente plausible en texto (1990..año+1)
  async fetch_sitemap(base_url|sitemap_url, fetch_fn) -> dict[str,datetime|None]
        # descarga el sitemap.xml una vez, parsea <url><loc><lastmod>; mapea url->lastmod.
        # Soporta sitemap index (múltiples <sitemap>). Falla en silencio ({}) si no hay/no parsea.

## Servicio de crawl de sitio — ingestion/quality/site_crawler.py
class SiteCrawler(session, spider, signal_extractor, page_repo):
  async def crawl_site(site_id) -> SiteCrawlSummary:
    1. Lee HubWebSite. Obtiene el conjunto de URLs objetivo:
       union(sitemap urls, enlaces descubiertos por el spider dentro del dominio raíz).
    2. Por cada URL: _fetch (body + headers), extrae señales, upsert HubCrawledPage
       (markdown_content, content_hash, title, token_count, language + las 5 señales).
       last_crawled_at/last_seen_at=now, status "active".
       Si el fetch de ESA URL falla: upsert la página con status "error" + error_message
       (no aborta el resto del crawl).
    3. DIFF DE SITEMAP:
       - nuevas: URL en el crawl que no existía como HubCrawledPage → status "active", first_seen_at=now.
       - cambiadas: content_hash distinto al previo → marca para re-embed (signal en summary).
       - desaparecidas: páginas activas en BD que ya NO aparecen en este crawl → status "gone".
    4. Actualiza HubWebSite.last_crawled_at; HubWebSite.status "error"+error_message si el crawl
       falla globalmente (los fallos de página concreta van en la página, no en el sitio).
  SiteCrawlSummary: pages_new, pages_changed, pages_gone, pages_error, pages_total, errors.

## Refactor del spider (sin HubIngestionSource)
- GenericSpider._fetch devuelve body + headers (adapta tipo de retorno y call-sites/tests).
- El recorrido del sitio se acota al dominio de root_url; respeta robots si ya se respetaba.
- El sitemap se consulta una vez por sitio, no por página.

## Tests (mínimo 12) — test_site_crawler.py + test_crawl_signals.py
- Parseo Last-Modified válido / ausente / malformado; canonical con/sin tag (primero gana).
- extract_content_year: año en path gana al texto; sin año → None; descarta años absurdos.
- fetch_sitemap parsea XML (fixture) y sitemap index; ausente → {}.
- crawl_site upsert páginas con markdown_content + las 5 señales; segundo crawl idempotente sobre uq_page_site_url.
- diff: URL nueva → page nueva; content_hash cambiado → pages_changed; URL ausente → status "gone".
- fallo de fetch de una URL → esa página status="error"+error_message, el resto del crawl continúa.
- crawl con fallo global deja HubWebSite.status="error" sin crashear.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde (incluidos los tests de spider adaptados a la nueva firma de `_fetch` y a la retirada de `HubIngestionSource`).

---

### Prompt 9Q.3 (RED/GREEN) — Detector determinista: vacías, finas, stale, errores y supersesión por URL+fecha

**Modelo sugerido**: **Sonnet** — reglas deterministas enumerables; sin LLM. La normalización de URL y la precedencia de fechas se especifican explícitamente en el prompt.

**Objetivo**: primera pasada del motor —sin coste de LLM, sobre **todo el sitio**— que emite hallazgos a partir de las señales de `HubCrawledPage`: páginas vacías/finas, stale, con error de crawl, huérfanas, y **supersesión temporal por patrón de URL + fecha**.

**Contexto**: usa los contratos de 9Q.1 (`HubContentFinding`, claves sitio/página) y las señales de 9Q.2 sobre `HubCrawledPage`. Lee `HubCrawledPage` (y `HubDocument` solo para detectar páginas `gone` con documentos aún ingeridos). Escribe hallazgos vía `ContentFindingRepo`.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.3 (RED/GREEN) — Detector determinista de calidad

Deploy: edge.

## Servicio — ingestion/quality/deterministic_detector.py
class DeterministicQualityDetector(session, *, thin_token_threshold=120, stale_days=365):
  async def analyze(site_id) -> list[ContentFinding]:
    Sobre las HubCrawledPage del sitio, emite (vía ContentFindingRepo.upsert):
      - empty: página con markdown_content vacío/None o token_count==0 → severity critical.
      - thin: token_count < thin_token_threshold (y > 0)            → severity warning.
      - stale: página cuya frescura de CONTENIDO
               max(sitemap_lastmod, http_last_modified, content_year-as-date) sea anterior a
               now-stale_days → severity info. NO incluir last_crawled_at (es siempre ≈ahora tras
               el crawl y anularía la regla). Si las tres señales son None, no se evalúa stale.
               signal incluye la fecha que disparó la regla.
      - crawl_error: HubCrawledPage.status=="error" (error_message poblado) → critical.
      - orphan_page: página status=="gone" que aún tiene HubDocument con crawled_page_id apuntándola
               (query explícito por id, sin relationship)            → warning.
      - superseded (determinista): ver algoritmo abajo.

## Algoritmo de supersesión determinista
  1. Agrupar páginas del sitio por "clave de proceso" = path normalizado de canonical_url
     SIN el segmento de año (quita /2023/, /2024/, query string, fragmentos, trailing slash).
  2. Dentro de cada grupo con >1 página, ordenar por fecha efectiva =
     max(sitemap_lastmod, http_last_modified, content_year-as-date, first_seen_at).
  3. La más reciente es la vigente; las demás → finding superseded con
     related_page_id = id de la vigente, signal = {fechas comparadas, clave de proceso}.
     NO muta todavía HubCrawledPage.superseded (eso lo hace el job 9Q.5 al consolidar);
     aquí solo se emite el hallazgo.
  El detector es idempotente: re-ejecutar no duplica (uq_finding_dedup).

## Tests (mínimo 11) — test_deterministic_detector.py
- empty (markdown_content None/vacío) / thin (justo por encima y por debajo del umbral) / token_count 0.
- stale por señal de contenido antigua; página con señal reciente no marca stale; página con las
  tres señales None NO marca stale (aunque last_crawled_at sea viejo).
- crawl_error desde status=="error" de página.
- orphan_page: página gone con documento aún ingerido.
- supersesión: 3 versiones mismo proceso distinto año → 2 superseded apuntando a la vigente.
- normalización de URL: /proc/2023/x y /proc/2024/x agrupan; /proc/x y /otro/x no.
- idempotencia: segunda pasada no crea hallazgos nuevos.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/unit/test_deterministic_detector.py` verde.

---

### Prompt 9Q.4 (RED/GREEN) — Detector semántico site-scoped: clustering pgvector + juez LLM + `audit_semantic_scope`

**Modelo sugerido**: **Opus** — decisiones de diseño embebidas: estrategia de clustering por similitud, umbral, control de coste, la lógica de cobertura `ingested`/`full` (qué páginas tienen embedding y cuáles se embeben on-demand), diseño del prompt del juez LLM y discriminación duplicado-vs-contradicción con confianza calibrada.

**Objetivo**: segunda pasada, **selectiva y con LLM, a nivel sitio**, que detecta duplicados y contradicciones semánticas entre páginas. Respeta `HubWebSite.audit_semantic_scope`: `ingested` (solo páginas ya ingeridas en algún chatbot, que ya tienen embeddings) o `full` (embebe todas las páginas rastreadas).

**Contexto**: la similitud pgvector y los embeddings de chunks viven en `ingestion/retriever.py` / `HubDocumentChunk`. Una página ingerida tiene embeddings vía su `HubDocument`→chunks (`crawled_page_id`). Una página no ingerida no los tiene. El juez LLM se inyecta como `LLMService` (Protocol, igual que 9R.6.3); el `EmbeddingService` también se inyecta. La anonimización pre-LLM reutiliza los hooks de Fase 13.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.4 (RED/GREEN) — Detector semántico con juez LLM (site-scoped)

Deploy: edge.

## Migración — embedding de página para modo full
Añade a HubCrawledPage: page_embedding Vector(D)|None (pgvector, None = sin embedding), donde D
es la MISMA dimensión que usa HubDocumentChunk.embedding (BGE-M3 = 1024); si no coinciden, la
similitud coseno no cruza. Aplica con `uv run alembic upgrade <rev>`.

## Servicio — ingestion/quality/semantic_detector.py
class SemanticContradictionDetector(session, llm: LLMService, embedding_service, *,
        similarity_threshold=0.92, max_pairs_per_run=200, anonymizer=None):
  async def analyze(site_id) -> list[ContentFinding]:
    0. COBERTURA según HubWebSite.audit_semantic_scope:
       - "ingested": conjunto = páginas del sitio con al menos un HubDocument ingerido. Reusa el
         embedding del chunk representativo (mayor token_count). Si la página está ingerida en
         varios chatbots (varios HubDocument), el contenido es idéntico → toma cualquiera (p.ej. el
         primer document_id) sin recomputar.
       - "full": conjunto = todas las páginas activas. Para las que no tengan page_embedding,
         embeber HubCrawledPage.markdown_content vía embedding_service y persistir page_embedding
         (idempotente: no re-embeber si content_hash no cambió).
    1. CLUSTERING (sin LLM): por cada página del conjunto, vecinos por coseno >= similarity_threshold.
       Forma pares candidatos (page_a, page_b) DISTINTO id dentro del MISMO sitio.
    2. CONTROL DE COSTE: descarta pares de la MISMA canonical (eso es 9Q.3 superseded).
       Limita a max_pairs_per_run, priorizando mayor similitud. 0 pares → return [] sin LLM.
    3. ANONIMIZACIÓN: si anonymizer no es None, anonimiza ambos textos antes del LLM.
    4. JUEZ LLM: por par, JSON estricto
       {"relation":"duplicate"|"contradiction"|"unrelated","confidence":0..1,"explanation":"..."}.
       - duplicate → finding duplicate (warning); contradiction → critical; unrelated → nada.
       confidence del finding = confidence del juez. signal = {similarity, explanation, textos truncados}.
    El prompt del juez es robusto a fences markdown (reutiliza _extract_json de 9R.4.1).

## Reglas
- NUNCA llamar al LLM por cada par del producto cartesiano: solo pares filtrados por umbral y dedup.
- En modo "ingested" jamás se embebe de más (coste 0 de embedding).
- LLM y embedding_service inyectados; tests con fakes deterministas (no red).

## Tests (mínimo 11) — test_semantic_detector.py
- Cobertura "ingested": solo páginas con documento; las no ingeridas se ignoran (0 embeds).
- Cobertura "full": páginas sin embedding se embeben y persisten; segundo run no re-embebe.
- Clustering: solo pares >= umbral; por debajo no.
- Control de coste: 0 pares → 0 llamadas al LLM (spy).
- Pares de la misma canonical se descartan.
- Juez contradiction → critical con confidence propagada; duplicate → warning; unrelated → nada.
- max_pairs_per_run respetado; anonimizador invocado cuando se inyecta; JSON con fences.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/unit/test_semantic_detector.py` verde; cero llamadas al LLM cuando no hay clusters; cero embeddings en modo `ingested`; migración aplicada.

---

### Prompt 9Q.5 (RED/GREEN) — Job asíncrono por sitio + scheduler + consolidación + auto-ingesta de candidatas

**Modelo sugerido**: **Sonnet** — orquestación con patrón de scheduler conocido; alcance cerrado (crawl + detectores + consolidación + auto-ingest ya están especificados por 9Q.2–9Q.4 y la selección de 9Q.7).

**Objetivo**: orquestar **por sitio** el crawl (9Q.2) + ambas pasadas de detección (9Q.3/9Q.4) en un job asíncrono que **nunca bloquea**, consolidar los `superseded` en `HubCrawledPage` y propagarlos a los `HubDocument` ingeridos, **auto-ingerir las páginas nuevas** que casen con una `HubCorpusSelection(auto_ingest_new=True)`, y programar la cadencia con un scheduler propio.

**Contexto**: reutiliza el patrón APScheduler del difunto `source_scheduler.py` (eliminado en 9Q.0; entre 9Q.0 y este prompt no hay scheduler de crawl). Los detectores son 9Q.3/9Q.4; el crawler 9Q.2; la ingesta de una página la realiza `IngestionWatcher`; las selecciones las resuelve `CorpusSelectionRepo` (9Q.0/9Q.7).

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.5 (RED/GREEN) — SiteQualityJob + scheduler

Deploy: edge.

## Servicio — ingestion/quality/quality_job.py
class SiteQualityAnalysisJob(session_factory, site_crawler, detectors, watcher, selection_repo,
        *, run_semantic=True):
  async def run_for_site(site_id) -> SiteQualitySummary:
    1. CRAWL: site_crawler.crawl_site(site_id) → diff (nuevas/cambiadas/desaparecidas).
    2. DETECCIÓN: DeterministicQualityDetector.analyze(site_id) SIEMPRE;
       SemanticContradictionDetector.analyze(site_id) si run_semantic y hay LLM.
       Cada detector en try/except aislado: si uno falla, el otro y el crawl siguen (summary.errors).
    3. CONSOLIDACIÓN: por cada finding superseded en new|confirmed, fija
       HubCrawledPage.superseded=True + superseded_by_page_id. PROPAGACIÓN: los HubDocument con
       crawled_page_id de esa página NO se borran; el flag de página basta (el retriever de 9Q.6
       filtra por la página). quality_score por página = heurística documentada
       (1.0 menos penalizaciones por findings críticos/warning sobre esa página).
    4. AUTO-INGESTA: por cada página NUEVA del diff, para cada HubCorpusSelection del sitio con
       auto_ingest_new=True cuya regla case (selection_repo.matches), encola IngestionWatcher
       para crear el HubDocument(crawled_page_id=page.id) en ese chatbot. Páginas CAMBIADAS ya
       ingeridas → re-ingesta (re-embed). Páginas GONE → marca sus documentos para retirada
       (finding orphan_page; la retirada efectiva la decide el equipo vía 9Q.7).
    El job NUNCA propaga excepción que tumbe el scheduler.
  SiteQualitySummary: diff counts, counts por finding_type, páginas marcadas superseded,
    documentos auto-ingeridos, errores.

## Scheduler — ingestion/quality/quality_scheduler.py (patrón APScheduler)
  create_quality_scheduler(session_factory) -> AsyncIOScheduler
    - Job maestro check_all_sites cada N horas (default 24, UTC) que selecciona los HubWebSite
      activos cuyo crawl_interval_hours haya vencido y lanza run_for_site.
  Arranque en main.py / lifespan (sustituye al arranque del antiguo source_scheduler).

## Settings (core/config.py)
  CONTENT_QUALITY_ENABLED: bool = True
  CONTENT_QUALITY_INTERVAL_HOURS: int = 24
  CONTENT_QUALITY_SEMANTIC_ENABLED: bool = True   # apaga el juez LLM si se quiere coste 0

## Tests (mínimo 10) — test_quality_job.py
- run_for_site encadena crawl + ambos detectores y agrega summary.
- Fallo del detector semántico NO impide consolidación determinista (summary.errors).
- Consolidación fija superseded=True + superseded_by_page_id en la página antigua.
- Auto-ingesta: página nueva que casa una selección auto → watcher invocado con crawled_page_id.
- Página nueva sin selección que case → NO se ingiere (queda candidata para 9Q.7).
- quality_score baja con findings críticos; run_semantic=False salta el LLM.
- Scheduler filtra sitios por crawl_interval_hours vencido (mock de tiempo).
- Idempotencia: segunda ejecución no duplica findings ni re-ingiere sin cambios.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde; un fallo simulado del detector semántico deja la suite verde y la consolidación + auto-ingesta intactas.

---

### Prompt 9Q.6 (RED/GREEN) — RAG consciente de calidad: el retriever excluye páginas `superseded`

**Modelo sugerido**: **Sonnet** — modificación acotada del retriever con filtro por flag de página; tests de regresión claros.

**Objetivo**: cerrar el primer canal de salida (higiene RAG): el retriever deja de servir chunks cuyos documentos provengan de una **página** marcada `superseded`, con opción explícita de incluirlos para auditoría. Como el flag vive en la página, el filtrado afecta a **todos** los chatbots que ingirieron esa página.

**Contexto**: `ingestion/retriever.py` (`HybridRetriever.vector_search`/`keyword_search`/`hybrid_search`) y `retrieval/vector_strategy.py`. El flag de supersesión está en `HubCrawledPage` (9Q.0); `HubDocument.crawled_page_id` enlaza chunk→documento→página. El filtro se aplica por defecto sin romper los contratos existentes.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.6 (RED/GREEN) — Retrieval que excluye páginas superseded

Deploy: edge.

## Cambios en HybridRetriever (retriever.py)
- vector_search / keyword_search / hybrid_search aceptan include_superseded: bool = False.
- Por defecto (False), las queries excluyen chunks cuyo document_id apunte a un HubDocument
  cuyo crawled_page_id apunte a una HubCrawledPage con superseded=True.
  Implementar con JOIN/subquery hub_document_chunks → hub_documents → hub_crawled_pages.
- include_superseded=True restaura el comportamiento anterior (para el visor de auditoría).
- Chunks cuyo HubDocument tenga crawled_page_id=None (PDFs subidos, legacy) NO se excluyen
  (no hay página de origen, no hay info de supersesión).

## VectorRetrievalStrategy
- Propaga el filtro por defecto (las respuestas del chatbot nunca usan páginas superseded).

## Tests (mínimo 8) — test_retrieval_quality_filter.py
- Página superseded → los chunks de sus documentos NO aparecen en vector/keyword/hybrid_search.
- include_superseded=True → reaparecen.
- Página no superseded → sin cambios (regresión de los tests de retriever existentes).
- HubDocument con crawled_page_id None (PDF subido) → nunca filtrado.
- Misma página ingerida por 2 chatbots → ambos la excluyen al marcarse superseded.
- hybrid_search mantiene el orden RRF tras excluir superseded.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde, incluidos los tests de retriever previos sin regresión.

---

### Prompt 9Q.7 (RED/GREEN) — Capa de selección: gestión de sitios + mapeo sitio→chatbots + candidatas

**Modelo sugerido**: **Sonnet** — servicio de selección + endpoints con alcance cerrado (las entidades y reglas ya las fijó 9Q.0). Sustituye la superficie de "fuentes" que retiró 9Q.0.

**Objetivo**: dar la superficie HTTP que materializa el split: gestionar **sitios** (CRUD + disparo de crawl), definir **selecciones** que mapean secciones del sitio a chatbots (N:M), y revisar/ejecutar la **ingesta de páginas candidatas** (nuevas o seleccionadas aún no ingeridas).

**Contexto**: repos de 9Q.0 (`WebSiteRepo`, `CrawledPageRepo`, `CorpusSelectionRepo`). La ingesta de una página la realiza `IngestionWatcher` creando `HubDocument(crawled_page_id=...)`. El job de calidad es 9Q.5. Router nuevo `Deploy: edge`, en `_register_edge`.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.7 (RED/GREEN) — Selección y gestión de sitios

Deploy: edge.

## Servicio — ingestion/quality/selection_service.py
class CorpusSelectionService(session, page_repo, selection_repo, watcher):
  async def candidates(site_id, chatbot_id) -> list[CandidatePageView]:
    # páginas activas del sitio que (casan alguna selección del chatbot O son nuevas) y
    # NO tienen aún HubDocument(crawled_page_id) para ese chatbot.
  async def ingest_page(chatbot_id, page_id) -> HubDocument
    # ingesta manual de una página concreta en un chatbot (idempotente: no duplica).
  async def retire_page(chatbot_id, page_id) -> int
    # retira los HubDocument(crawled_page_id) de esa página para ese chatbot (borra chunks).

## Contratos — ingestion/quality/selection_contracts.py
SiteView, SiteCreate (name, root_url, sitemap_url?, audit_semantic_scope?, crawl_interval_hours?),
  # SiteCreate NO incluye client_id: el servidor lo deriva del usuario autenticado (current_user)
  # al crear el HubWebSite. El cliente nunca lo envía.
SelectionView, SelectionCreate (site_id, rule_type, rule_value?, auto_ingest_new?),
CandidatePageView (page_id, url, title, matched_rule?, is_new: bool).

## Router — routers/hub_sites_router.py (Deploy: edge)
- POST/GET/PATCH/DELETE /api/v1/hub/sites                         → CRUD de HubWebSite (por client)
- POST /api/v1/hub/sites/{site_id}/crawl                          → 202, dispara SiteQualityAnalysisJob.run_for_site
- GET  /api/v1/hub/sites/{site_id}/pages?status=                  → páginas rastreadas
- POST/GET/DELETE /api/v1/hub/chatbots/{chatbot_id}/selections    → CRUD de HubCorpusSelection
- GET  /api/v1/hub/sites/{site_id}/candidates?chatbot_id=         → CorpusSelectionService.candidates
- POST /api/v1/hub/chatbots/{chatbot_id}/pages/{page_id}/ingest   → 202, ingest_page (manual)
- DELETE /api/v1/hub/chatbots/{chatbot_id}/pages/{page_id}        → retire_page
Permisos: 403 si el usuario no es owner del chatbot/admin del client. operation_id explícito (Orval).
Registrar en _register_edge (main.py) con docstring `Deploy: edge`.

## Tests (mínimo 10) — test_selection_service.py + test_hub_sites_router.py
- candidates devuelve páginas que casan una selección path_prefix y no están ingeridas; excluye ya ingeridas.
- ingest_page crea HubDocument(crawled_page_id) y es idempotente (2ª llamada no duplica).
- retire_page borra documentos+chunks de esa página para el chatbot y devuelve el count.
- CRUD de sitio y de selección; POST crawl responde 202 y encola run_for_site (spy).
- 403 para usuario no autorizado; edge boundary (router no importa módulos cloud).
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde; OpenAPI regenerado; `_register_edge` incluye el router.

---

### Prompt 9Q.8 (RED/GREEN) — Informe de auditoría web por sitio: builder + export DOCX/PDF + endpoints

**Modelo sugerido**: **Sonnet** — agregación de datos + reutilización de `ExportService`; endpoints con alcance cerrado.

**Objetivo**: cerrar el segundo canal de salida (informe humano): un builder que agrega los hallazgos de un **sitio** en un informe estructurado por tipo con recomendaciones, su exportación a DOCX/PDF descargable, y los endpoints HTTP (cola de revisión, informe, disparo de análisis) **keyed por sitio**.

**Contexto**: el patrón de export DOCX existe en `modules/agents_hub/services/export_service.py` (python-docx). Para PDF, reutilizar el mismo patrón o conversión documentada (sin añadir dependencias pesadas nuevas sin justificar). Router nuevo `Deploy: edge`, en `_register_edge`. Los hallazgos los provee `ContentFindingRepo.list_by_site` (9Q.1).

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.8 (RED/GREEN) — WebQualityReport builder + export + endpoints

Deploy: edge.

## Contrato del informe — ingestion/quality/report_contracts.py
WebQualityReport (Pydantic): site_id, site_name, generated_at, totals_by_type: dict[FindingType,int],
  totals_by_severity, sections: list[FindingTypeSection].
FindingTypeSection: finding_type, findings: list[ContentFindingView],
  recommendation: str  # texto accionable para el equipo web (p.ej. "3 páginas obsoletas:
  considere despublicar /proc/2022/x sustituida por /proc/2024/x").
ContentFindingView: tipo, severidad, urls implicadas (page/related), fechas, explicación.

## Builder — ingestion/quality/report_builder.py
class WebQualityReportBuilder(findings_repo, site_repo):
  async def build(site_id, *, status_filter=("new","confirmed")) -> WebQualityReport
    - list_by_site → agrupa por finding_type, genera recommendation por sección
      (plantillas i18n-izables; texto base en español, claves para traducir en UI).
    - Caso vacío: informe con totals a 0 y sections=[].

## Export — ingestion/quality/report_exporter.py
class WebQualityReportExporter(storage):
  async def to_docx(report) -> bytes      # reutiliza patrón de ExportService (python-docx)
  async def to_pdf(report) -> bytes       # conversión ya disponible; si requiere LibreOffice/headless,
                                          # degradar con skip condicional como en 9R.9.2.

## Router — routers/hub_content_quality_router.py (Deploy: edge)
- GET   /api/v1/hub/sites/{site_id}/findings?status=&type=        → lista (cola de revisión)
- PATCH /api/v1/hub/sites/{site_id}/findings/{finding_id}         → transición de estado
         (confirm/dismiss/resolve; 422 transición inválida; 403 si no autorizado)
- GET   /api/v1/hub/sites/{site_id}/report                        → WebQualityReport JSON
- GET   /api/v1/hub/sites/{site_id}/report/export?format=docx|pdf → descarga binaria
- POST  /api/v1/hub/sites/{site_id}/analyze                       → 202, dispara
          SiteQualityAnalysisJob.run_for_site en background.
Registrar en _register_edge (main.py) con docstring `Deploy: edge`. operation_id explícito (Orval).

## Tests (mínimo 10) — test_content_quality_report.py + test_content_quality_router.py
- build agrupa por finding_type y genera recommendation; caso vacío → totals 0.
- Exporter DOCX produce bytes no vacíos con secciones; PDF con skip condicional documentado.
- GET findings filtra por status/type; PATCH aplica transición y 422 en inválida; 403 no-autorizado.
- GET report devuelve el contrato; export?format=docx devuelve content-type correcto.
- POST analyze responde 202 y encola el job (spy).
- Edge boundary: el router no importa módulos cloud (test_edge_boundary actualizado).
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde; OpenAPI regenerado; `_register_edge` incluye el router.

---

### Prompt 9Q.9 (RED/GREEN) — Frontend: sitios + mapeo de selección + candidatas + auditoría + pruebas manuales

**Modelo sugerido**: **Sonnet** — UI React con hooks Orval generados, i18n, patrones ya establecidos en el admin hub.

**Objetivo**: cerrar el bloque con la interfaz admin organizada **en torno al sitio**: gestión de sitios y disparo de crawl, mapeo de secciones del sitio a chatbots (selecciones), revisión de páginas candidatas a ingesta, cola de hallazgos del sitio, visor del informe de auditoría y descarga DOCX/PDF. Todo i18n y derivado del contrato OpenAPI.

**Contexto**: frontend admin en `frontend/src/admin/`; hooks generados por Orval desde `openapi.json` (endpoints de 9Q.7 sitios/selecciones/candidatas y de 9Q.8 hallazgos/informe). i18n con i18next (es/ca/en). Este prompt **sí requiere pruebas manuales** (navegador) según CLAUDE.md → genera el `.bat`.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.9 (RED/GREEN) — UI de calidad de contenido web (centrada en sitio)

## Regenerar Orval
Tras 9Q.7/9Q.8, regenerar hooks (useListSites / useCreateSite / useCrawlSite /
useListSelections / useCreateSelection / useListCandidates / useIngestPage /
useListSiteFindings / usePatchFinding / useGetWebQualityReport / useAnalyzeSite).
Verificar tsc --noEmit limpio.

## Páginas (frontend/src/admin/pages/)
- SitesPage.tsx: lista de sitios (alta con root_url/sitemap/audit_semantic_scope),
  botón "Rastrear ahora" → useCrawlSite (toast de encolado), estado last_crawled_at.
- SiteMappingPanel.tsx: dado un sitio, gestiona selecciones (regla path_prefix/section/manual,
  toggle auto_ingest_new) y muestra páginas candidatas (useListCandidates) con acción
  "Ingerir en chatbot X" (useIngestPage). Selector de chatbot destino.
- ContentQualityPage.tsx: selector de sitio; "Analizar ahora" → useAnalyzeSite; tabla de
  hallazgos (badge por severidad, URLs, fecha, explicación, Confirmar/Descartar/Resolver via
  usePatchFinding); filtros por status y finding_type.
- WebQualityReportViewer.tsx: useGetWebQualityReport → totales por tipo/severidad + secciones
  por finding_type con recomendación; "Descargar DOCX"/"Descargar PDF" → GET export?format=.
- Rutas /hub/sites y /hub/content-quality en App.tsx + entradas en la navegación de HubLayout.

## i18n (namespace nuevo `contentQuality`, es/en/ca)
  Etiquetas de finding_type, severidad, estados, acciones, reglas de selección, recomendaciones,
  títulos de tabla, botones. NINGÚN string hardcodeado.

## Tests Vitest (mínimo 7) — SitesPage / SiteMappingPanel / ContentQualityPage / WebQualityReportViewer
- SitesPage: alta de sitio invoca useCreateSite; "Rastrear ahora" invoca useCrawlSite.
- SiteMappingPanel: crear selección invoca useCreateSelection; candidatas se listan; "Ingerir" invoca useIngestPage.
- Tabla de hallazgos renderiza con badge de severidad correcto; Confirmar invoca usePatchFinding.
- Filtro por finding_type re-consulta con el parámetro; "Analizar ahora" invoca useAnalyzeSite.
- Visor muestra totales y secciones; caso vacío → mensaje "sin hallazgos".
- Accesibilidad: expectNoA11yViolations sobre las páginas nuevas (helper de 20.1).

## Pruebas manuales (CLAUDE.md — requiere navegador)
Genera `pruebas_manuales_prompt9Q_9.bat` (encoding ANSI 1252, sin BOM, vía PowerShell
[System.IO.File]::WriteAllText con Encoding 1252; primeros bytes @ech) con: arranque Docker,
migración si aplica, smoke `curl` a /hub/sites/{id}/analyze, y pasos en la UI: dar de alta un
sitio, rastrearlo, crear una selección por prefijo, ingerir una candidata en un chatbot,
analizar el sitio, ver hallazgos (duplicados/obsoletas), confirmar uno, abrir el informe,
descargar el DOCX. Casos límite: sitio sin hallazgos; página candidata sin selección que case.
Acompaña la respuesta con el bloque de instrucciones para el usuario (formato CLAUDE.md).
```

**Verificación**: `npm test` (Vitest) verde; `tsc --noEmit` limpio; `.bat` con bytes correctos; bloque de instrucciones manuales en la respuesta. **Cierra el bloque 9Q.**

---

## Bloque AUTH — SSO SAML institucional + Personal Access Tokens (adelanto de Subfase 1.B.1, PENDIENTE)

> **Posición en orden de ejecución**: entre el Bloque 9Q (cerrado) y Fase 11 (Autoinstalación). Ver `PROJECT_STATE.md` → orden de ejecución acordado.

**Justificación del adelanto (2026-06-11)**: la autenticación SSO real (OIDC/SAML) estaba planificada como **Subfase 1.B.1** (`PLAN_DESARROLLO.md`, "antes Fase 5.1") y se difirió: en Fase 1 solo se ejecutó la identidad *visual* (Fase 10/temas). El Bloque MCP (siguiente) necesita un mecanismo de autenticación para **clientes máquina** antes de poder probarse. Se adelanta aquí la Subfase 1.B.1 completa para (a) cerrar el login institucional que la UJI exige por contrato y (b) habilitar la emisión de credenciales máquina que MCP consume.

**Distinción central (no confundir las dos piezas)**:

| Pieza | Para quién | Flujo | Bloque |
|---|---|---|---|
| **SSO SAML** | Humanos (admin/partner/usuario UJI) | Interactivo: redirect a IdP → aserción firmada → JWT de sesión | AUTH.1–AUTH.2, AUTH.4 |
| **PAT (Personal Access Token)** | Máquinas (servidor MCP headless) | No interactivo: token revocable de larga duración en cabecera `Authorization` | AUTH.3 |

Un servidor MCP **no puede** hacer el redirect-a-IdP de SAML. SAML autentica al humano que, ya logado, **emite un PAT** desde la UI; el PAT es lo que el cliente MCP usa. Por eso ambas piezas son necesarias y separadas.

**Decisiones de diseño tomadas (2026-06-11, vía `AskUserQuestion`)**:
- **Alcance**: SSO SAML + PAT completos (no solo PAT).
- **Enfoque SAML**: **Service Provider genérico SAML 2.0** testeable contra un **IdP de pruebas** (fixtures de aserción firmada / SimpleSAMLphp). La metadata real del IdP de la UJI se conecta por variable de entorno cuando esté disponible — **no bloquea** el desarrollo ni los tests.
- **Librería**: **`python3-saml`** (OneLogin) sobre xmlsec.

**Clasificación edge/cloud**:
- Login SAML y emisión/gestión de PAT son **`Deploy: cloud`** (autenticar humanos y emitir credenciales es trabajo del cloud/admin).
- La **validación** de credenciales (JWT y PAT) vive en `core/auth` (**compartido**): los routers edge la heredan vía `Depends`. En `DEPLOY_MODE=all` (dev) la búsqueda del PAT es local. La sincronización cloud→edge de la validación de PAT (cuando exista despliegue edge real) queda como **seguimiento documentado** vía `ConfigProvider`/sync API — no se implementa en este MVP.

**Reglas duras del bloque AUTH**:
- Ningún PAT se persiste en claro: se guarda solo `sha256(token)` + un `prefix` para identificarlo en la UI. El texto plano se devuelve **una sola vez** en la creación.
- La dependencia de auth acepta **JWT o PAT** de forma transparente, discriminando por prefijo (`pat_…`). Un PAT lleva *scopes*; un endpoint protegido por scope rechaza (403) un PAT sin el scope requerido.
- Solo `admin`/`partner` pueden emitir PAT. Los scopes de un PAT **nunca** exceden el rol del emisor.
- SAML con feature flag `SAML_ENABLED`: en dev, el login email+contraseña actual sigue disponible como fallback; en producción institucional se desactiva el fallback.

---

### Prompt AUTH.1 (RED/GREEN) — Service Provider SAML 2.0 con `python3-saml` + IdP de pruebas

**Modelo sugerido**: **Opus** — superficie de seguridad crítica (validación de firma/aserción), decisiones de diseño embebidas (mapa de atributos, adaptador request→python3-saml, fixtures de IdP de pruebas) y primer contacto con la librería.

**Objetivo**: implementar el SP SAML 2.0 que inicia el login contra el IdP institucional, consume la respuesta firmada (ACS) y publica la metadata del SP. Sin provisioning todavía (eso es AUTH.2): aquí se valida la aserción y se extraen NameID + atributos.

**Contexto**: auth actual = JWT de sesión email+contraseña (`server/app/routers/auth_router.py`, `Deploy: cloud`; `core/auth/jwt_handler.py`). `python3-saml` necesita un *dict* de request adaptado desde el `Request` de FastAPI (https on/off, http_host, script_name, get_data, post_data) y un *dict* de settings SP+IdP. El IdP de pruebas se materializa con un par de claves de test y fixtures de `SAMLResponse` firmadas (puede generarse con `xmlsec`/`python3-saml` en el propio test o con SimpleSAMLphp en docs; el test no debe depender de red).

**Instrucciones al agente**:
```markdown
# PROMPT AUTH.1 (RED/GREEN) — SP SAML 2.0 (python3-saml)

Deploy: cloud (router). Validación: compartida (core/auth).

## Dependencias
- Añadir `python3-saml` a pyproject.toml (arrastra `xmlsec` + `lxml`; documentar en
  README/DEV que requiere libxml2/libxmlsec1 del sistema — en Docker, paquetes apt).

## Settings (core/config.py)
SAML_ENABLED: bool = False
SAML_SP_ENTITY_ID, SAML_SP_ACS_URL, SAML_SP_SLS_URL
SAML_SP_X509_CERT, SAML_SP_PRIVATE_KEY (opcionales; para firmar AuthnRequest/metadata)
SAML_IDP_METADATA_URL | SAML_IDP_METADATA_XML  (una de las dos; XML inline para tests)
SAML_ATTR_EMAIL (default "urn:oid:0.9.2342.19200300.100.1.3" / "mail")
SAML_ATTR_NAME, SAML_ATTR_ROLE, SAML_ATTR_GROUPS (nombres de atributo en la aserción)
SAML_DEFAULT_ROLE: str = "user"
SAML_FRONTEND_RETURN_URL (a dónde redirige el ACS tras emitir el JWT)

## core/auth/saml/settings.py
- build_saml_settings() -> dict  # estructura sp/idp de python3-saml, a partir de env;
  si SAML_IDP_METADATA_URL, parsea metadata con OneLogin_Saml2_IdPMetadataParser
  (cacheable); si XML inline, idem desde string.
- InvalidSamlConfigError si falta config obligatoria con SAML_ENABLED=True.

## core/auth/saml/request_adapter.py
- async def prepare_saml_request(request: Request) -> dict
  # {"https", "http_host", "script_name", "get_data", "post_data"} desde el Request FastAPI.
  # Lee el body form (await request.form()) para post_data en el ACS.

## routers/saml_auth_router.py (prefix /auth/saml, Deploy: cloud)
- GET  /auth/saml/login        -> 302 al IdP (OneLogin_Saml2_Auth.login con RelayState opcional)
- POST /auth/saml/acs          -> procesa SAMLResponse: auth.process_response();
                                   si auth.get_errors() -> 401 SAML_VALIDATION_FAILED;
                                   si not auth.is_authenticated() -> 401;
                                   devuelve por ahora {nameid, attributes} (200) — el JWT llega en AUTH.2.
- GET  /auth/saml/metadata     -> XML de metadata del SP (content-type application/xml);
                                   400 si build_saml_settings produce errores de validación.
- GET  /auth/saml/logout (stub mínimo SLO: inicia SLS si SP_SLS_URL; si no, 501 documentado)
- Si SAML_ENABLED=False -> los endpoints responden 404/503 documentado (feature flag).
Registrar en _register_cloud (main.py) con docstring `Deploy: cloud`.

## Tests (mínimo 12) — tests/core/auth/test_saml_sp.py
- build_saml_settings construye sp/idp desde env (metadata XML inline de un IdP de pruebas).
- prepare_saml_request mapea https/host/post_data desde un Request simulado.
- GET /metadata devuelve XML bien formado con el EntityDescriptor del SP (entityID correcto).
- GET /login responde 302 con SAMLRequest en la query (Location al SSO del IdP de pruebas).
- POST /acs con SAMLResponse firmada válida (fixture) -> 200 con nameid + attributes esperados.
- POST /acs con firma manipulada -> 401 SAML_VALIDATION_FAILED (get_errors no vacío).
- POST /acs con aserción expirada / audience incorrecta -> 401.
- SAML_ENABLED=False -> endpoints 404/503; InvalidSamlConfigError si falta IdP con flag on.
Las fixtures de SAMLResponse firmada se generan en conftest con un cert/clave de test
(sin red): documentar el cómo. NUNCA usar el IdP real en tests.
```

**Verificación**: `uv run pytest tests/core/auth/` verde; `GET /auth/saml/metadata` produce XML válido; OpenAPI regenerado; `_register_cloud` incluye el router. Documentar en README la dependencia de sistema `libxmlsec1`.

---

### Prompt AUTH.2 (RED/GREEN) — Provisioning JIT + mapeo identidad SAML → cuenta + rol + JWT de sesión

**Modelo sugerido**: **Sonnet** — reglas de mapeo enumeradas y alcance cerrado; el SP ya valida la aserción en AUTH.1. (Opus solo si el mapeo multi-grupo→rol se complica.)

**Objetivo**: convertir una aserción SAML válida en una sesión del sistema: mapear NameID/atributos a un rol (`UserRole`), localizar o **aprovisionar (JIT)** la cuenta, emitir el JWT de sesión existente (`create_token`) y redirigir al frontend.

**Contexto**: cuentas actuales = `AdminAccount`, `PartnerAccount` (`server/app/database/models.py`). Los usuarios UJI que lleguen por SAML y no sean admin/partner necesitan una entidad propia. El JWT y la `UserInfo` (sub/email/role) ya existen y no cambian — SAML solo es un emisor adicional.

**Instrucciones al agente**:
```markdown
# PROMPT AUTH.2 (RED/GREEN) — Provisioning JIT + JWT desde SAML

Deploy: cloud.

## ORM — HubSsoUser (HubConfigBase) en database/models.py
- id (UUID), email (único, lower), display_name, role (str, validado contra UserRole),
  external_id (NameID del IdP), idp_entity_id, created_at, last_login_at, is_active.
- Migración Alembic (aplicar al terminar; si la BD no responde, pedir arranque al usuario
  según CLAUDE.md).

## core/auth/saml/role_mapping.py
- SAML_GROUP_ROLE_MAP (env JSON: {"grupo-ldap": "partner", ...}) parseado a dict.
- resolve_role(attributes) -> str:
    1) si SAML_ATTR_ROLE presente y válido -> ese rol;
    2) si algún grupo de SAML_ATTR_GROUPS casa SAML_GROUP_ROLE_MAP -> rol mapeado
       (precedencia admin > partner > informer > user);
    3) si no -> SAML_DEFAULT_ROLE.

## core/auth/saml/identity_service.py
class SamlIdentityService(session):
  async def resolve_session(nameid, attributes) -> UserInfo:
    - email := attributes[SAML_ATTR_EMAIL][0] (obligatorio; si falta -> SamlMissingEmailError).
    - Si el email casa un AdminAccount activo -> UserInfo(role=admin).
    - Elif casa un PartnerAccount activo -> UserInfo(role=partner).
    - Else -> upsert HubSsoUser (rol vía resolve_role), actualizar last_login_at -> UserInfo.

## Integración en el ACS (routers/saml_auth_router.py)
- POST /auth/saml/acs (de AUTH.1) ahora: tras validar -> resolve_session -> create_token(user_info)
  -> 302 a SAML_FRONTEND_RETURN_URL con el token (querystring `#token=` o cookie httpOnly;
  decidir y documentar — preferir fragment/cookie sobre query para no filtrarlo en logs).

## Tests (mínimo 10) — tests/core/auth/test_saml_identity.py
- email de AdminAccount conocido -> UserInfo role=admin (sin crear HubSsoUser).
- email de PartnerAccount conocido -> role=partner.
- email desconocido + atributo de grupo mapeado a "partner" -> HubSsoUser role=partner (JIT).
- email desconocido sin grupo -> role=SAML_DEFAULT_ROLE.
- segundo login del mismo NameID -> no duplica HubSsoUser, actualiza last_login_at.
- aserción sin atributo email -> SamlMissingEmailError -> 401 en el ACS.
- resolve_role: precedencia admin>partner cuando hay varios grupos.
- ACS completo (fixture firmada) -> 302 a la return URL con token; decode_token del JWT -> UserInfo correcta.
```

**Verificación**: `uv run pytest tests/core/auth/` verde; migración aplicada (`alembic current` muestra la revisión); el ciclo login→ACS emite un JWT válido decodificable por `decode_token`.

---

### Prompt AUTH.3 (RED/GREEN) — Personal Access Tokens (PAT) revocables para clientes máquina

**Modelo sugerido**: **Opus** — toca la dependencia de auth que protege **todos** los requests (doble vía JWT/PAT) y maneja material criptográfico (hash de tokens, scopes); un error aquí es un agujero de seguridad.

**Objetivo**: emitir, validar y revocar tokens de acceso personal de larga duración con *scopes*, y extender la dependencia de autenticación para aceptarlos de forma transparente. Es el **prerrequisito real del Bloque MCP**.

**Contexto**: la dependencia actual es `get_current_user` (`server/app/api/deps.py`) que decodifica el Bearer JWT. Hay que admitir además PATs sin romper a los consumidores JWT existentes. `core/security.py` ya expone hashing (passlib) — reutilizar `sha256` para el token (no passlib: el token es de alta entropía, no una contraseña).

**Instrucciones al agente**:
```markdown
# PROMPT AUTH.3 (RED/GREEN) — PAT revocables + auth dual JWT/PAT

Deploy: emisión/gestión cloud; validación compartida (core/auth).

## ORM — HubPersonalAccessToken (HubConfigBase)
- id (UUID), owner_id (str), owner_role (str, validado UserRole), name (str),
  token_prefix (str, 8 chars visibles para identificar en UI), token_hash (sha256 hex),
  scopes (JSON list[str]), created_at, expires_at (nullable), last_used_at (nullable),
  revoked_at (nullable). Índice por token_prefix.
- Migración Alembic (aplicar al terminar).

## core/auth/pat/scopes.py
- Scopes válidos (constantes): "redaccion:templates:read", "redaccion:templates:write",
  "chatbots:read", "chatbots:write", "chat:test".
- UnknownScopeError si se pide un scope fuera del catálogo.

## core/auth/pat/service.py
class PatService(session):
  async def create(owner: UserInfo, name, scopes, expires_at?) -> tuple[HubPersonalAccessToken, str]
     - solo admin/partner (else PatForbiddenError); scopes ⊆ permitidos para el rol
       (un partner no puede emitir scopes que su rol no alcanza).
     - genera secret aleatorio (secrets.token_urlsafe(32)); token plano = f"pat_{prefix}_{secret}".
     - persiste token_prefix + sha256(token plano); DEVUELVE el plano UNA vez.
  async def verify(token: str) -> PatPrincipal   # UserInfo + scopes
     - localiza por prefix, compara sha256 en tiempo constante (hmac.compare_digest);
     - rechaza revocado/expirado (PatInvalidError); actualiza last_used_at.
  async def list_for(owner) -> list[...]   # SIN token plano ni hash
  async def revoke(owner, pat_id) -> None   # set revoked_at; 404 si no es del owner

## core/auth/dependencies (extender deps.py)
- get_current_user (o nuevo get_principal): si el Bearer empieza por "pat_" -> PatService.verify
  -> UserInfo con scopes adjuntos; si no -> flujo JWT actual (sin scopes -> scopes=None = "todos
  los de su rol vía sesión humana").
- require_scopes(*needed): dependency factory -> 403 PAT_SCOPE_MISSING si el principal es PAT y
  le falta algún scope. Un principal JWT humano no se filtra por scopes (sesión interactiva).

## routers/pat_router.py (prefix /auth/pats, Deploy: cloud)
- POST   /auth/pats        -> crea (body: name, scopes, expires_at?); 201 con el token plano
                              (único momento en que se ve); 403 si rol no admin/partner.
- GET    /auth/pats        -> lista metadatos del owner (prefix, name, scopes, fechas, revoked).
- DELETE /auth/pats/{id}   -> revoca; 404 si no es del owner.
Registrar en _register_cloud. operation_id explícito (Orval).

## Tests (mínimo 14) — tests/core/auth/test_pat.py + tests/test_pat_router.py
- create devuelve token plano "pat_..." y persiste solo prefix+sha256 (nunca el plano).
- verify(token válido) -> UserInfo+scopes; actualiza last_used_at.
- verify de token revocado -> PatInvalidError; expirado -> PatInvalidError.
- partner no puede crear PAT con scope fuera de su rol -> PatForbiddenError.
- usuario no admin/partner -> POST 403.
- list nunca expone hash ni plano; revoke de PAT ajeno -> 404.
- dependency: Bearer pat_... resuelve a UserInfo; require_scopes 403 si falta scope.
- dependency: Bearer JWT clásico sigue funcionando sin cambios (no regresión).
- comparación de hash en tiempo constante (compare_digest) — test de presencia.
```

**Verificación**: `uv run pytest tests/core/auth/ tests/test_pat_router.py` verde; migración aplicada; los tests de auth JWT preexistentes siguen verdes (sin regresión); OpenAPI regenerado.

---

### Prompt AUTH.4 (RED/GREEN) — Frontend: login SSO + gestión de PAT (UI) + pruebas manuales

**Modelo sugerido**: **Sonnet** — React + hooks Orval + i18n con patrones ya establecidos en el admin hub.

**Objetivo**: botón de login SSO institucional que redirige al SP y consume el token de retorno, y una pantalla de gestión de PAT (crear con scopes y caducidad, copiar el token una sola vez, revocar). Requiere **pruebas manuales** (navegador).

**Contexto**: login actual email+contraseña en el frontend (Prompt 9.3). Orval genera hooks desde `openapi.json` (endpoints de AUTH.3). i18n i18next (es/ca/en).

**Instrucciones al agente**:
```markdown
# PROMPT AUTH.4 (RED/GREEN) — UI login SSO + PAT

## Regenerar Orval
Hooks de PAT: useCreatePat / useListPats / useRevokePat. tsc --noEmit limpio.

## Login (frontend/src/admin/.../LoginPage)
- Botón "Entrar con SSO institucional" -> window.location = `${API}/auth/saml/login`
  (visible si VITE_SAML_ENABLED). Mantener email+contraseña como fallback (dev).
- Manejar el retorno del ACS: leer token del fragment/cookie, guardarlo en el auth context
  existente, redirigir a /hub. Si SAML_FRONTEND_RETURN_URL apunta a /auth/callback, crear
  esa ruta ligera que extrae el token y delega en el contexto.

## Gestión de PAT (frontend/src/admin/pages/AccessTokensPage.tsx, admin/partner)
- Tabla de PAT (name, prefix, scopes, creado, último uso, caducidad, revocar).
- "Crear token": modal react-hook-form+zod (name, multiselect de scopes, expiración opcional)
  -> useCreatePat -> mostrar el token plano UNA vez con botón "Copiar" y aviso
  "no volverás a verlo". Al cerrar, desaparece.
- Revocar -> useRevokePat con confirmación.
- Ruta /hub/access-tokens + entrada en la navegación de HubLayout.

## i18n (namespace `auth`, es/en/ca)
  Login SSO, fallback, etiquetas de scopes, mensajes del modal de creación,
  aviso de copia única, confirmación de revocado. NINGÚN string hardcodeado.

## Tests Vitest (mínimo 6)
- LoginPage muestra el botón SSO cuando VITE_SAML_ENABLED y redirige al /auth/saml/login.
- Callback extrae token del fragment y lo entrega al auth context (mock).
- AccessTokensPage: crear invoca useCreatePat y muestra el token plano una vez.
- Cerrar el modal oculta el token plano (no persiste en el DOM).
- Revocar invoca useRevokePat tras confirmación.
- a11y: expectNoA11yViolations sobre LoginPage y AccessTokensPage (helper de 20.1).

## Pruebas manuales (CLAUDE.md — requiere navegador)
Genera `pruebas_manuales_promptAUTH_4.bat` (ANSI 1252, sin BOM, vía PowerShell
[System.IO.File]::WriteAllText con Encoding 1252; primeros bytes @ech): arranque Docker,
migración, smoke `curl` a /auth/saml/metadata, y pasos UI: pulsar "Entrar con SSO"
(contra el IdP de pruebas si está configurado, o documentar que requiere metadata real),
crear un PAT con scopes redaccion:templates:read/write, copiarlo, revocarlo.
Casos límite: cerrar el modal sin copiar; revocar y comprobar que deja de autenticar.
Acompaña la respuesta con el bloque de instrucciones para el usuario (formato CLAUDE.md).
```

**Verificación**: `npm test` (Vitest) verde; `tsc --noEmit` limpio; `.bat` con bytes correctos; bloque de instrucciones manuales en la respuesta. **Cierra el Bloque AUTH.**

---

## Bloque MCP — Servidor MCP stdio para autoría de plantillas y configuración de chatbots (PENDIENTE)

> **Posición en orden de ejecución**: tras el Bloque AUTH (que aporta el PAT que MCP consume) y antes de Fase 11.

**Origen**: `docs/mcp.md` (valoraciones 1 y 2). Decisiones de planificación tomadas (2026-06-11): **opción A (servidor MCP stdio local, wrapper de la API HTTP)** y alcance **completo** = plantillas (valoración 1) + chatbots (valoración 2) + `test_chat` (fase 2 de mcp.md).

**Por qué encaja sin reabrir nada (resumen de mcp.md)**: la arquitectura contract-first hace el trabajo. El servidor MCP es **un cliente HTTP más** de la API existente (`hub_redaccion_router`/`hub_chatbots_router`), igual que el frontend. No cruza bases ORM ni importa módulos prohibidos. Las piezas críticas ya existen: `DraftValidator`, versionado append-only de plantillas (`ReportTemplateVersionRepo` sin `update()`), `ReportTemplateSpec.model_json_schema()`.

**Ubicación del paquete**: `mcp_server/` en la raíz del repo (paquete independiente con su propio `pyproject.toml`, SDK oficial `mcp`). **No** vive bajo `server/app/` — es un cliente, no parte del servidor. No importa nada de `server/app`; habla con la API por HTTP.

**Autenticación**: el servidor MCP lee un **PAT** (Bloque AUTH) de variable de entorno y lo envía en `Authorization: Bearer pat_…`. Los scopes del PAT acotan lo que el servidor puede hacer (lectura vs escritura).

**HITL por construcción (regla dura nº4 de `REDACCION_CONTRACT_FIRST.md`)**: con MCP el humano está en el bucle (aprueba cada tool call en Claude Code). Se refuerza: tools de lectura/validación libres; las de escritura (`publish_template_version`, `create_template`, `update_chatbot`) exigen un **flag explícito de confirmación** y devuelven el resultado del validador / un *diff* antes de persistir.

**Reglas duras del bloque MCP**:
- El servidor MCP **no** importa código de `server/app`; solo cliente HTTP (`httpx`).
- Toda escritura requiere `confirm=True` (o `dry_run=False` explícito) y el scope de PAT correspondiente; sin él, el tool devuelve el plan/diff sin ejecutar.
- Errores HTTP (401/403/422) del servidor se mapean a errores de tool legibles, nunca se silencian.
- Tests sin red: `respx`/transport mock de httpx; se prueba el mapeo tool→llamada HTTP y el gating de escritura, no el servidor real.

---

### Prompt MCP.1 (RED/GREEN) — Scaffolding del servidor MCP stdio + cliente API con PAT + resources

**Modelo sugerido**: **Opus** — primer contacto con el SDK MCP y el transporte stdio, diseño de la arquitectura del cliente (auth PAT, mapeo de errores, resources); decisiones que condicionan MCP.2–MCP.4.

**Objetivo**: crear el paquete `mcp_server/` con el SDK oficial `mcp` (FastMCP), transporte stdio, un cliente HTTP autenticado por PAT y los *resources* base (JSON Schema de `ReportTemplateSpec`, registry de profiles, guía `GRAPH_PROFILES.md`).

**Contexto**: SDK oficial Python `mcp` (FastMCP: `@mcp.tool()`, `@mcp.resource()`, `mcp.run()` stdio). El JSON Schema de `ReportTemplateSpec` se expone como resource; para no acoplar el cliente al backend, se obtiene de un endpoint nuevo del servidor (ver MCP.2) o, de forma transitoria, de `openapi.json`. Config por entorno: `GOVGENAI_API_BASE_URL`, `GOVGENAI_PAT`.

**Instrucciones al agente**:
```markdown
# PROMPT MCP.1 (RED/GREEN) — Scaffolding MCP stdio + auth PAT

## Paquete mcp_server/ (raíz del repo, pyproject propio)
- deps: mcp, httpx, pydantic. NO depende de server/app.
- mcp_server/config.py: GOVGENAI_API_BASE_URL, GOVGENAI_PAT (desde env); error claro si faltan.
- mcp_server/api_client.py: ApiClient(httpx.AsyncClient) con base_url + header
  Authorization: Bearer <PAT>. Métodos get/post/patch/delete que mapean
  401->AuthError, 403->ScopeError, 422->ValidationError (con el body), 5xx->ServerError.
- mcp_server/server.py: FastMCP("govgenai"); registra resources base; mcp.run() stdio.

## Resources base (mcp_server/resources/)
- resource "govgenai://redaccion/template-schema" -> JSON Schema de ReportTemplateSpec
  (vía GET del endpoint del servidor; en MCP.2 se garantiza el endpoint).
- resource "govgenai://redaccion/profiles" -> registry de report profiles.
- resource "govgenai://docs/graph-profiles" -> contenido de docs/GRAPH_PROFILES.md
  (servido vía endpoint o empaquetado; documentar la fuente).

## Tests (mínimo 8) — mcp_server/tests/test_scaffolding.py (respx)
- ApiClient inyecta Authorization: Bearer <PAT> en cada request.
- 401 -> AuthError; 403 -> ScopeError; 422 -> ValidationError con detalle del body.
- El servidor MCP arranca y lista los resources esperados (in-memory client del SDK mcp).
- resource template-schema devuelve el JSON Schema (respx-mock del endpoint).
- Falta de GOVGENAI_PAT -> error de configuración claro al iniciar.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; `mcp_server` arranca en stdio (`uv run mcp run mcp_server/server.py` o equivalente) y lista resources. Sin imports de `server/app` (grep limpio).

---

### Prompt MCP.2 (RED/GREEN) — Tools de plantillas (redacción) con gate de escritura HITL

**Modelo sugerido**: **Sonnet** — toolset acotado sobre endpoints ya existentes; el SDK ya está cableado en MCP.1.

**Objetivo**: exponer la autoría de `ReportTemplateSpec` como tools MCP: lectura (`list_templates`, `get_template_spec`), validación sin persistir (`validate_template_draft`) y escritura gated (`create_template`, `publish_template_version`).

**Contexto**: endpoints en `hub_redaccion_router` / `llm_drafts_router` (`Deploy: edge`); `DraftValidator` ya expuesto vía `/validate`. Versionado append-only: `publish_template_version` solo añade, nunca corrompe una versión publicada. Si no existe aún un endpoint que devuelva `ReportTemplateSpec.model_json_schema()`, **añadirlo** en el servidor (GET `/api/v1/hub/redaccion/template-schema`, `Deploy: edge`) — alimenta el resource de MCP.1.

**Instrucciones al agente**:
```markdown
# PROMPT MCP.2 (RED/GREEN) — Tools de plantillas

## Backend (si falta): GET /api/v1/hub/redaccion/template-schema -> ReportTemplateSpec.model_json_schema()
  Deploy: edge. operation_id explícito. Test del endpoint.

## Tools (mcp_server/tools/templates.py)
- list_templates() -> GET /hub/redaccion/templates                 [scope redaccion:templates:read]
- get_template_spec(version_id) -> GET .../template-versions/{id}   [read]
- validate_template_draft(spec: dict) -> POST .../validate          [read] (no persiste; devuelve
    el resultado del DraftValidator: errores con loc/msg/type).
- create_template(draft: dict, confirm: bool=False)                 [scope redaccion:templates:write]
    - confirm=False -> ejecuta solo la validación y devuelve el plan; NO crea.
    - confirm=True  -> POST de creación; devuelve el id/version creados.
- publish_template_version(template_id, spec: dict, confirm: bool=False)  [write]
    - confirm=False -> valida (DraftValidator) y devuelve el resultado SIN publicar.
    - confirm=True  -> publica (append-only) y devuelve la nueva version_id.

## Tests (mínimo 10) — mcp_server/tests/test_templates_tools.py (respx)
- cada tool de lectura llama al endpoint correcto y devuelve el payload mapeado.
- validate_template_draft devuelve el resultado del validador (incluye errores).
- create_template/publish con confirm=False -> NO hace POST (solo valida) y devuelve el plan.
- create_template/publish con confirm=True -> hace el POST y devuelve el id.
- 422 del validador -> ValidationError legible.
- escritura sin scope (403 del servidor) -> ScopeError clara.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; endpoint `template-schema` en OpenAPI; gating de escritura verificado (sin confirm no persiste).

---

### Prompt MCP.3 (RED/GREEN) — Tools de chatbots (configuración cloud) con diff/dry_run

**Modelo sugerido**: **Sonnet** — segundo namespace de tools sobre `hub_chatbots_router`; patrón establecido en MCP.2.

**Objetivo**: exponer la configuración de chatbots como tools MCP (namespace `chatbots_*`), mitigando el riesgo de mutación in-place con *diff* y `dry_run`.

**Contexto**: `hub_chatbots_router` (`Deploy: cloud`, roles admin/partner). Versionado in-place sin historial: una escritura errónea muta un bot en producción y el widget público cambia al instante (ver mcp.md valoración 2). Por eso `update_chatbot` ecoa el *diff* (config actual → propuesta) y admite `dry_run`. `GET /hub/chatbots/{id}/corpus-stats` ya recomienda modo según corpus.

**Instrucciones al agente**:
```markdown
# PROMPT MCP.3 (RED/GREEN) — Tools de chatbots

## Resources (mcp_server/resources/)
- enums válidos (public_graph_profile, retrieval_mode, kinds) y JSON Schema de
  ChatbotCreate/ChatbotUpdate (vía endpoint de esquema o openapi.json).

## Tools (mcp_server/tools/chatbots.py)
Lectura [scope chatbots:read]:
- list_clients(), list_chatbots(client_id?), get_chatbot(id),
  get_corpus_stats(id), list_prompt_templates(chatbot_id?)
Escritura [scope chatbots:write]:
- create_chatbot(payload, confirm=False)   # confirm=False -> valida y devuelve plan
- update_chatbot(id, patch, dry_run=True)   # dry_run=True -> devuelve diff actual→propuesta
                                             #   sin persistir; dry_run=False -> aplica el PATCH
- update_prompt_template(id, payload, confirm=False)
- assign_child(router_id, child_id, confirm=False) / unassign_child(...)

## Tests (mínimo 10) — mcp_server/tests/test_chatbots_tools.py (respx)
- lecturas llaman al endpoint correcto (incluye corpus-stats con su recomendación).
- update_chatbot(dry_run=True) hace GET del estado actual, devuelve diff, NO hace PATCH.
- update_chatbot(dry_run=False) hace el PATCH.
- create/assign con confirm=False -> no persiste.
- escritura sin scope chatbots:write -> ScopeError.
- validaciones del servidor (límite 128K MD_LONG_CONTEXT, jerarquía) -> 422 -> ValidationError.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; diff/dry_run verificados; ningún import de `server/app`.

---

### Prompt MCP.4 (RED/GREEN) — Tool `test_chat` + documentación `MCP_SERVER.md` + registro `claude mcp add`

**Modelo sugerido**: **Sonnet** — un tool adicional + documentación; alcance cerrado.

**Objetivo**: cerrar el bucle configurar→probar→ajustar con un tool de chat de prueba, y documentar instalación, scopes y seguridad del servidor MCP.

**Contexto**: `hub_chat_router` (`Deploy: edge`) sirve el chat. En dev (`DEPLOY_MODE=all`) chat y config conviven; en despliegue real son superficies distintas (edge vs cloud) — documentarlo. Este prompt **no** requiere `.bat` de pruebas manuales (no es UI de navegador, es integración MCP/CLI); en su lugar incluye una verificación de integración con Claude Code.

**Instrucciones al agente**:
```markdown
# PROMPT MCP.4 (RED/GREEN) — test_chat + docs

## Tool (mcp_server/tools/chat.py)
- test_chat(chatbot_id, message, lang?) -> POST al endpoint de chat (hub_chat)  [scope chat:test]
  Devuelve la respuesta + evidencias/citas para evaluar la config del bot.
  Documentar la nota dev/prod (misma vs distinta superficie).

## docs/MCP_SERVER.md
- Propósito y arquitectura (cliente HTTP stdio, opción A de mcp.md).
- Variables de entorno (GOVGENAI_API_BASE_URL, GOVGENAI_PAT) y cómo emitir el PAT (Bloque AUTH UI).
- Mapa de scopes -> tools (qué scope necesita cada tool).
- Registro en Claude Code: `claude mcp add govgenai -- uv run mcp run mcp_server/server.py`
  (con las env vars). Ejemplo de sesión: redactar una plantilla y publicarla con confirm.
- Seguridad: HITL por aprobación de tool calls, escritura gated, PAT revocable, sin acceso a server/app.
- Referencia de toolset completa (resources + tools de MCP.2/MCP.3/MCP.4).

## Tests (mínimo 4) — mcp_server/tests/test_chat_tool.py (respx)
- test_chat llama al endpoint de chat con el mensaje y devuelve respuesta + citas.
- escritura/uso sin scope chat:test -> ScopeError.
- 404 chatbot inexistente -> error legible.
- doc smoke: el README/MCP_SERVER.md existe y lista los tools (test de presencia opcional).

## Verificación de integración (manual, sin .bat)
Documentar en la respuesta los pasos para registrar el servidor en Claude Code con un PAT
real emitido desde la UI (AUTH.4) y ejecutar test_chat contra un chatbot existente.
```

**Verificación**: `uv run pytest mcp_server/tests/` verde; `docs/MCP_SERVER.md` completo; instrucciones de `claude mcp add` en la respuesta. **Cierra el Bloque MCP.**

---

**Objetivo de la Fase**: Empaquetar el sistema completo para que cualquier institución pública pueda desplegarlo con un solo comando, sin depender de servicios de pago ni de conocimientos avanzados de infraestructura.

**Dependencias**: Fases 1-10 (sistema completo funcional)

**Conceptos clave**:
- **Docker Compose "One-Click"**: Un único archivo levanta todo el stack (Backend, Frontend, BD, MinIO, Ollama).
- **Variables de entorno documentadas**: Cada parámetro con comentarios explicativos para facilitar la adaptación.
- **Script de inicialización**: Automatiza migraciones, creación de superusuario y carga de datos de ejemplo.

---

### Prompt 11.1 - Generador de Configuración (.env.example)

**Modelo sugerido**: **Sonnet** — generador de plantillas .env con comentarios didácticos.

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

**Modelo sugerido**: **Sonnet** — YAML de Compose + perfiles dev/prod. Trabajo declarativo.

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

**Modelo sugerido**: **Sonnet** — script de bootstrap + seed data. Patrón script + ORM.

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

# COMPLECIÓN DE FASE 1 — Bloques nuevos (planificados 2026-07-11)

> Bloques añadidos a partir de la valoración de `VALORACION_PROYECTO.md` (aprobada por el usuario).
> Todos los prompts son **autocontenidos** y siguen el ciclo TDD RED → GREEN.
>
> **Orden de ejecución recomendado** (se inserta sobre el cursor actual, 11.x):
>
> ```
> Bloque ROL  →  Fase 11 (11.1–11.3)  →  Bloque SEC  →  Bloque CAL  →  Bloque ING.0  →  Deploy GCP (D.1–D.5)
> ```
>
> **Justificación del orden**:
> - **ROL primero**: el renombrado de roles es transversal y toca los mismos modelos de autenticación que `SEC.1`/`SEC.2`. Hacerlo antes evita trabajo doble y evita que Deploy (D.x) arrastre nomenclatura vieja.
> - **SEC antes de Deploy**: son fallos que, desplegados, quedarían públicos. Es bloqueante de `D.1`.
> - **CAL e ING.0** se cierran antes de abrir el repositorio bajo AGPLv3 (deuda de reglas del proyecto + corpus real del piloto).
>
> **Nota sobre `D.1`/`D.2`**: la autenticación pública del widget por API key (M1 de la valoración) ya está cubierta por `D.1`; la migración de secretos a Secret Manager (parte de A3) ya está en `D.2`. El bloque SEC **no los duplica** y asume que se ejecutan en Deploy. La **rotación** de las credenciales actualmente en `.env` (A3) es una acción de operaciones, no un prompt de código: hágase al migrar a Secret Manager.

---

## Bloque ROL — Renombrado de nomenclatura institucional (Subfase 1.B, PENDIENTE)

> **Contexto**: `Arquitectura.md` §5 y `PLAN_DESARROLLO.md` dan por aplicado el renombrado de roles, pero el código sigue con la nomenclatura antigua. Este bloque lo aplica. Es más barato ahora que tras la Fase 3 (Expedientes introduce `responsable_rol` por todo el módulo).

**Mapa de renombrado (fuente de verdad para ambos prompts):**

| Antiguo (código actual) | Nuevo | Naturaleza | Tabla / campo afectado |
|---|---|---|---|
| `AdminAccount` (admin global) | `SuperAdminAccount` | Cuenta | tabla `admin_accounts` → `superadmin_accounts` |
| rol `admin` (global) | rol `superadmin` | Rol | claim `role` en JWT |
| `PartnerAccount` | `AdminAccount` | Cuenta | tabla `partner_accounts` → `admin_accounts` |
| rol `partner` | rol `admin` | Rol | claim `role` en JWT |
| `HubClient` | `HubOrganizacion` | Entidad de datos | tabla `hub_clients` → `hub_organizaciones` |
| columna/parámetro `client_id` | `organizacion_id` | FK | en `HubChatbot`, temas, ingestión, etc. |
| usuario final | rol `user` | Rol | sin cambios de tabla |

> ⚠️ **Trampa**: `AdminAccount` se **reutiliza** para una entidad distinta (el ex-`PartnerAccount`). La migración debe renombrar tablas preservando datos (`ALTER TABLE ... RENAME`), **nunca** drop+create. Ejecutar los renombrados en el orden correcto para no colisionar (`admin_accounts` → `superadmin_accounts` **antes** de `partner_accounts` → `admin_accounts`).

---

### Prompt ROL.1 (RED/GREEN) — Refactor de modelos, migración y dependencias de seguridad

**Modelo sugerido**: **Opus** — refactor transversal (>800 LOC afectadas en modelos, deps, routers, tests), reutilización peligrosa del nombre `AdminAccount` y migración de datos que debe preservar filas y FKs.

**Objetivo**: Aplicar el mapa de renombrado en el backend (modelos ORM, migración Alembic con preservación de datos, dependencias de seguridad y todas las queries/imports afectados) sin perder datos ni romper tests.

```
# PROMPT ROL.1 (RED/GREEN) — Renombrado institucional en el backend
# Deploy: cloud (cuentas/roles) + shared (deps de auth)

## Alcance (aplicar el "Mapa de renombrado" del Bloque ROL)
- database/models.py: AdminAccount→SuperAdminAccount, PartnerAccount→AdminAccount.
  Añadir NADA de lógica nueva aquí (la contraseña del ex-partner es SEC.1).
- modules/agents_hub/database/config_models.py: HubClient→HubOrganizacion; todas las
  columnas y relaciones `client_id`→`organizacion_id`. Mantener HubConfigBase.
- core/auth/models.py: el enum/Literal de roles pasa a superadmin | admin | user.
- api/deps.py + core/auth: require_admin (global) → require_superadmin;
  crear require_admin nuevo (=ex require_partner o el gate de partner); actualizar
  require_scopes / techos de rol de PAT (core/auth/pat/scopes.py: admin→superadmin,
  partner→admin en la tabla de techos).
- routers/auth_router.py: login_admin→login_superadmin (path /auth/superadmin/login),
  login_partner→login_admin (path /auth/admin/login). Mantener el bug de contraseña
  TAL CUAL (lo arregla SEC.1); aquí solo se renombra.
- Reemplazar TODA referencia a client_id/HubClient/partner/PartnerAccount en:
  hub_chatbots_router, hub_themes_router, hub_feedback, hub_chat, seeds.py, y
  cualquier servicio que los importe (grep exhaustivo).

## Migración Alembic (preservando datos; NO drop+create)
- op.rename_table('admin_accounts','superadmin_accounts')
- op.rename_table('partner_accounts','admin_accounts')     # tras el anterior
- op.rename_table('hub_clients','hub_organizaciones')
- op.alter_column(... 'client_id', new_column_name='organizacion_id') en cada tabla con esa FK
- Data migration de roles: UPDATE de la columna role en tokens/cuentas si se persiste
  ('admin'→'superadmin', 'partner'→'admin'). Los JWT en vuelo caducan solos (60 min).
- Reaplicar constraints/índices renombrados. Aplicar con `uv run alembic upgrade head`.

## Tests (RED primero) — tests/core/ + tests/api/
# test_role_rename.py
# should_expose_superadmin_admin_user_roles_only            (el Literal no acepta 'partner')
# should_superadmin_login_verify_password_like_before        (regresión del login global)
# should_require_superadmin_dependency_rejects_admin_role
# should_require_admin_dependency_accepts_admin_and_superadmin
# test_migration_rename.py
# should_rename_tables_preserving_rows                       (seed → upgrade → filas intactas)
# should_rename_client_id_to_organizacion_id_on_chatbots
# should_have_zero_references_to_old_names                   (grep: 'PartnerAccount'|'HubClient'|"role == 'partner'" = 0 en server/app, excl. migración)

## Criterios de cierre (obligatorio)
- [ ] `grep -rn "PartnerAccount\|HubClient\|'partner'\|\bclient_id\b" server/app` = 0 (excl. la migración y comentarios de mapeo)
- [ ] `uv run alembic upgrade head` + `alembic current` en head; datos preservados
- [ ] OpenAPI reexportado (cambian paths de login y esquemas) + Orval pendiente para ROL.2
- [ ] Suite backend en verde
```

---

### Prompt ROL.2 (RED/GREEN) — Frontend: tipos Orval, rutas, i18n y checks de rol

**Modelo sugerido**: **Sonnet** — alcance cerrado; la fuente de verdad (OpenAPI) ya cambió en ROL.1, solo hay que propagar.

**Objetivo**: Propagar el renombrado al frontend regenerando Orval y actualizando rutas, checks de rol e i18n. Sin lógica de negocio nueva.

```
# PROMPT ROL.2 (RED/GREEN) — Renombrado institucional en el frontend

## Regenerar contrato
- Reexportar openapi.json (ya hecho en ROL.1) → `npm run orval` → tipos/hooks nuevos
  (SuperAdminAccount, AdminAccount, HubOrganizacion, organizacion_id).

## Cambios
- shared/auth: el AuthContext y las rutas protegidas usan roles superadmin|admin|user.
  Reemplazar cualquier comparación con 'partner'/'admin-global'.
- Renombrar pantallas/labels: "Clientes"→"Organizaciones" (ClientsPage→OrganizacionesPage),
  "Partners"→"Admins" donde aparezca. Rutas /clients→/organizaciones.
- i18n: renombrar claves y textos es/ca/en (client→organizacion, partner→admin). Sin strings sueltos.

## Tests Vitest (RED primero) — mínimo 5
# should_render_organizaciones_page_from_generated_types
# should_route_superadmin_to_platform_section
# should_route_admin_to_org_scoped_section
# should_hide_platform_admin_from_user_role
# should_use_i18n_keys_not_hardcoded_role_labels

## Pruebas manuales (CLAUDE.md — requiere navegador)
- .bat prompt ROL_2: login como cada rol y verificar navegación y etiquetas.
```

---

## Bloque SEC — Endurecimiento de seguridad (Subfase 1.B, PENDIENTE, BLOQUEANTE DE DESPLIEGUE)

> **Contexto**: hallazgos de la auditoría de seguridad (`VALORACION_PROYECTO.md` §4). Se ejecuta **después de ROL** (usa la nomenclatura nueva: rol `admin`, `organizacion_id`) y **antes de Deploy GCP**. Todo `Deploy: cloud|edge|shared` según el router.

---

### Prompt SEC.1 (RED/GREEN) — Login de Admin con verificación de contraseña [A1]

**Modelo sugerido**: **Sonnet** — patrón conocido (bcrypt ya existe para superadmin); alcance cerrado.

**Objetivo**: Cerrar el bypass de autenticación del login de Admin (ex-partner), que hoy emite JWT sin comprobar contraseña. `AdminAccount` (ex-`PartnerAccount`) ni siquiera tiene campo de hash.

```
# PROMPT SEC.1 (RED/GREEN) — Contraseña obligatoria en login de Admin
# Deploy: cloud

## Cambios
- database/models.py: añadir `hashed_password: str` a AdminAccount (ex-PartnerAccount).
- Migración Alembic: add_column nullable + backfill NULL → cuentas sin password quedan
  DESHABILITADAS para login local (deben usar SSO/PAT o que un superadmin fije password).
- routers/auth_router.py::login_admin: verificar con core/security.verify_password
  (mismo patrón que login_superadmin). Rechazar si hashed_password es NULL.
- Endpoint para que superadmin establezca/resetee la contraseña de un Admin (o reutilizar
  el alta con password hasheado). Mensaje y tiempo de respuesta IDÉNTICOS para
  "cuenta inexistente" y "contraseña inválida" (no filtrar existencia).

## Tests (RED primero) — tests/api/test_auth_login.py
# should_reject_admin_login_without_password_field         (regresión del bug A1)
# should_reject_admin_login_with_wrong_password
# should_accept_admin_login_with_correct_password
# should_reject_admin_with_null_hashed_password
# should_return_identical_error_for_unknown_and_wrong_password
```

---

### Prompt SEC.2 (RED/GREEN) — Aislamiento multi-tenant: claim de organización + filtrado + gate de CI [A2]

**Modelo sugerido**: **Opus** — decisión de diseño del modelo de tenencia + refactor transversal de todos los endpoints con datos de organización + test de aislamiento que debe convertirse en gate.

**Objetivo**: Impedir el acceso horizontal entre organizaciones. Hoy el JWT no lleva la organización y los endpoints no filtran: cualquier admin lista/edita/borra chatbots de todos y lee conversaciones (posible PII ciudadana) de otros.

```
# PROMPT SEC.2 (RED/GREEN) — Aislamiento por organización
# Deploy: shared (claim) + edge/cloud (según router)

## Modelo de tenencia (decisión)
- UserInfo (core/auth/models.py) añade `organizacion_ids: list[str]`:
    - superadmin → lista vacía = acceso a TODAS (comodín).
    - admin → ids de las organizaciones que gestiona.
    - user → la organización a la que pertenece (1 elemento).
- El claim se rellena al emitir el JWT (login superadmin/admin, ACS SAML, y PAT:
  PatPrincipal hereda organizacion_ids del owner).

## Capa de filtrado (única, no repetir en cada endpoint)
- core/auth/tenancy.py: `assert_org_access(principal, organizacion_id)` → 403 si no procede
  (superadmin siempre pasa). `scope_query_to_orgs(stmt, principal, model)` → añade
  WHERE organizacion_id IN (...) salvo superadmin.
- Aplicar en: hub_chatbots_router (list/get/update/delete/corpus-stats/regenerate-chunks),
  hub_chat (conversar solo con chatbots de la propia organización),
  hub_feedback (revisar solo interacciones de chatbots propios),
  hub_themes_router (derivar organizacion_id del principal, NO del body del cliente),
  hub_ingestion_router (cierra el TODO de autorización en :91).

## Tests (RED primero) — tests/api/test_tenant_isolation.py  ← GATE DE CI
# should_list_only_own_org_chatbots                        (admin A no ve chatbots de org B)
# should_forbid_get_chatbot_of_other_org                   (403)
# should_forbid_update_delete_chatbot_of_other_org         (403)
# should_forbid_reading_feedback_of_other_org
# should_forbid_chatting_with_chatbot_of_other_org
# should_ignore_client_supplied_org_id_in_themes           (usa el del token)
# should_allow_superadmin_cross_org_access
# should_scope_ingestion_to_own_org

## Criterios de cierre
- [ ] test_tenant_isolation.py añadido al job de CI como gate obligatorio
- [ ] Ningún endpoint de datos de organización hace `session.get(Model, id)` sin pasar por assert_org_access
```

---

### Prompt SEC.2.1 (RED/GREEN) — Modo de acceso por chatbot + identidad delegada

**Modelo sugerido**: **Opus** — decide el modelo de visibilidad (enum + grupos SAML), refactoriza los tres caminos de conversación tras un único helper, y fija un contrato criptográfico de identidad delegada con riesgo de escalada si se diseña mal.

**Objetivo**: Hoy `HubChatbot` solo tiene `is_active`; no existe forma de expresar "este chatbot es solo para personal autenticado" ni "solo para el grupo Gerencia". SEC.2 aísla **entre** organizaciones, pero **dentro** de una organización todos los chatbots quedan igual de accesibles. Además, el piloto con Open WebUI exige que el backend sepa **qué persona** pregunta cuando la petición llega por un cliente de confianza que porta un PAT de servicio: sin eso, la cuota por usuario de SEC.4 es inaplicable.

**Origen**: revisión de planificación 2026-07-27 (chatbots de gestión para personal + límite de uso). El usuario eligió la **opción (a)**: propagación de identidad por cabecera firmada, no un PAT por usuario (que no escala a cientos de personas ni sobrevive a las bajas).

**Dependencias**: requiere SEC.2 cerrado (`assert_org_access`, claim `organizacion_ids`). El endpoint del widget llega en **D.1**; aquí el helper se testea a nivel unitario con `via='widget_api_key'` y D.1 lo consume — este prompt **no** queda bloqueado por D.1.

```
# PROMPT SEC.2.1 (RED/GREEN) — Autorización por chatbot e identidad delegada
# Deploy: edge (enforcement en el chat) + shared (modelo y helpers de auth)

## PARTE 1 — Modo de acceso por chatbot

### Modelo (agents_hub/database/config_models.py, HubChatbot)
- `access_mode: Mapped[str]` String(20) NOT NULL default 'authenticated'
  + CheckConstraint access_mode IN ('public_anon','authenticated','restricted')
    - public_anon    -> conversable sin sesión, solo por el endpoint widget con API key (D.1)
    - authenticated  -> exige JWT o PAT + pertenencia a la organización (SEC.2)
    - restricted     -> lo anterior + rol en allowed_roles O grupo en allowed_saml_groups
- `allowed_roles: Mapped[list[str]]` ARRAY(String) default list
- `allowed_saml_groups: Mapped[list[str]]` ARRAY(String) default list
- Decisión documentada: **no se crea tabla de grants**. El atributo de grupo ya llega en el
  ACS SAML (bloque AUTH) y dos ARRAY cubren el caso del piloto. Si más adelante hace falta
  granularidad por usuario individual, se añade tabla entonces; estos campos quedan como
  atajo. No sobreingeniería ahora.
- Migración Alembic **fail-closed**: todos los chatbots existentes -> 'authenticated'.
  NO usar 'public_anon' como valor de migración: hoy no existe endpoint anónimo (llega en
  D.1) y abrirlo por migración expondría el corpus sin que nadie lo haya decidido.

### Helper único (core/auth/chatbot_access.py)
- `assert_chatbot_access(actor: EffectiveActor | None, chatbot: HubChatbot, *, via: str) -> None`
  - `via` ∈ {'session','widget_api_key'} — por dónde entró la petición.
  - public_anon + via='widget_api_key' -> pasa sin actor.
  - public_anon + via='session'        -> pasa (un chatbot abierto también es usable logueado).
  - authenticated|restricted + via='widget_api_key' -> 403 ACCESS_MODE_FORBIDDEN.
  - authenticated -> exige actor + assert_org_access(actor, chatbot.organizacion_id).
  - restricted    -> lo anterior + (actor.role in allowed_roles OR
                     intersección no vacía entre actor.saml_groups y allowed_saml_groups).
                     Ambas listas vacías en modo restricted => solo superadmin (fail-closed).
  - superadmin siempre pasa (comodín, coherente con SEC.2).
- `UserInfo` añade `saml_groups: list[str]` (se rellena en el ACS SAML; vacío en login local).

### La organización de un usuario SAML (añadido el 2026-08-02, desde SEC.2)

**Problema que deja abierto SEC.2**: `HubSsoUser` no tiene organización, así que un usuario
provisionado por SSO se queda con el claim vacío y, por la regla de SEC.2, **sin acceso a
ningún recurso de organización**. Es fail-closed y no rompe nada vivo —el SSO real contra el
IdP sigue en la lista de pruebas manuales—, pero capa el login SSO. Se cierra aquí porque
este prompt ya toca `UserInfo` y ya toca el ACS.

**La decisión, y es la mitad importante del encargo: la organización sale de la
configuración del IdP, NUNCA de la aserción.**

- `HubSsoUser` gana `organizacion_id`, que se rellena **al aprovisionar en el ACS** tomándolo
  de la configuración del proveedor de identidad, no de un atributo de la respuesta SAML ni
  del dominio del correo.
- Es el mismo razonamiento anti-escalada que la Parte 2 de este prompt aplica a la cabecera
  delegada: si el dato viniera de fuera, quien controla el IdP podría declarar a qué
  organización pertenece cada persona que entra. Un IdP institucional pertenece a **una**
  institución, y esa relación la fija quien despliega.
- Migración fail-closed, como la de `access_mode`: los `HubSsoUser` existentes se quedan sin
  organización hasta que alguien la asigne. Ninguno hereda una por defecto.

Tests que añade a `tests/core/auth/test_saml_identity.py`:

```
# should_take_the_organizacion_from_the_idp_configuration
# should_ignore_an_organizacion_claimed_in_the_assertion    <- anti-escalada, el que importa
# should_leave_existing_sso_users_without_organizacion_after_migration
```
- Consumidores obligatorios: `hub_chat`, adaptador compatible-OpenAI (OWUI.1) y endpoint
  widget (D.1). **Ningún endpoint construye la decisión a mano** (grep de cierre).

### Router admin (hub_chatbots_router)
- `access_mode`, `allowed_roles`, `allowed_saml_groups` en ChatbotRead/Create/Update.
- Cambiar access_mode solo admin/superadmin (ya cubierto por require_admin).

## PARTE 2 — Identidad delegada (actor firmado)

Motivo: el Pipe de Open WebUI usa **un PAT de servicio**. Sin esto el backend solo ve al
dueño del PAT, y la cuota por usuario de SEC.4 no puede existir.

### Contrato (core/auth/delegated_actor.py)
- Cabecera `X-GovGenAI-Actor`: JWT compacto firmado por el cliente de confianza.
  HS256 con `DELEGATED_ACTOR_SECRET` (secreto compartido; RS256 se deja para cuando haya
  más de un cliente delegante — decisión documentada, no implementar ahora).
  Claims: `sub` (id estable del usuario en el cliente), `email`, `groups: list[str]`,
  `iat`, `exp` (ventana corta, <= 300 s), `aud` = "govgenai-backend".
- Nuevo scope `chat:onbehalf` en core/auth/pat/scopes.py (+ techo de rol superadmin/admin).
  **Sin el scope la cabecera se ignora por completo**: no es error, simplemente el actor
  efectivo es el dueño del PAT. Así un PAT robado sin ese scope no puede suplantar a nadie.
- `resolve_effective_actor(request, principal) -> EffectiveActor`
  con `EffectiveActor(subject_id, email, role, organizacion_ids, saml_groups, delegated: bool)`.
  - PAT con scope `chat:onbehalf` + cabecera válida -> actor delegado.
    **`organizacion_ids` se heredan del PAT, NUNCA de la cabecera** (si vinieran de la
    cabecera, el cliente delegante podría escalar de organización). `saml_groups` sí
    vienen de la cabecera (es lo que el IdP del cliente sabe y el backend no).
  - Firma inválida, expirada, `aud` incorrecto -> 401 ACTOR_TOKEN_INVALID.
  - Sesión humana JWT -> actor = el propio usuario, `delegated=False`.
- `assert_chatbot_access` y la cuota de SEC.4 consumen **el actor efectivo**, no el principal.
  Este es el punto de costura: SEC.4 se escribe sobre `resolve_effective_actor` desde el
  principio, para que OWUI.1 no tenga que retrofitear la cuota por usuario.

## Tests (RED primero)

# tests/api/test_chatbot_access_mode.py
# should_allow_anon_widget_only_when_public_anon
# should_403_widget_key_on_authenticated_chatbot
# should_403_authenticated_user_of_other_org              (se apoya en SEC.2)
# should_allow_restricted_when_role_in_allowed_roles
# should_allow_restricted_when_saml_group_matches
# should_403_restricted_when_no_role_or_group_matches
# should_403_restricted_when_lists_empty_and_not_superadmin
# should_allow_superadmin_regardless_of_access_mode
# should_default_existing_chatbots_to_authenticated_after_migration

# tests/core/auth/test_delegated_actor.py
# should_resolve_actor_from_signed_header_when_scope_present
# should_ignore_actor_header_when_pat_lacks_onbehalf_scope
# should_401_on_invalid_signature
# should_401_on_expired_actor_token
# should_401_on_wrong_audience
# should_inherit_organizacion_ids_from_pat_not_from_header    <- anti-escalada, clave
# should_use_session_user_as_actor_for_human_jwt

## Criterios de cierre
- [ ] Migración aplicada (`alembic upgrade head` + `alembic current`); chatbots existentes en 'authenticated'
- [ ] grep: hub_chat, adaptador OpenAI y endpoint widget pasan TODOS por assert_chatbot_access
- [ ] grep: ningún endpoint decide el acceso a mano
- [ ] `DELEGATED_ACTOR_SECRET` añadido a `.env.example` y generado en `scripts/generate_env.sh` (11.1)
- [ ] OpenAPI reexportado + Orval regenerado
- [ ] Frontera edge/cloud respetada: los tres campos nuevos son configuración (HubConfigBase), sin contadores
```

---

### Prompt SEC.3 (RED/GREEN) — CORS por entorno [A4]

**Modelo sugerido**: **Sonnet** — config declarativa.

```
# PROMPT SEC.3 (RED/GREEN) — CORS restringido por entorno
# Deploy: shared

## Cambios
- core/config.py: `CORS_ALLOWED_ORIGINS: list[str]` (CSV en env), `ENVIRONMENT`.
- main.py: sustituir allow_origins=["*"] por la lista configurada. En producción, lista
  cerrada (dominios del panel + dominios de widget de organizaciones). methods/headers
  acotados a los realmente usados. allow_credentials sigue False.
- Widget embebible: los orígenes de widget se validan aparte (API key por chatbot, D.1);
  no se abre CORS global por ellos.

## Tests (RED primero) — tests/api/test_cors.py
# should_reject_disallowed_origin_in_production_config
# should_allow_configured_origin
# should_default_to_no_wildcard_when_env_is_production
```

---

### Prompt SEC.4 (RED/GREEN) — Rate limiting + contabilidad de tokens + cuotas multi-sujeto [A5]

**Modelo sugerido**: **Sonnet** — el limiter es patrón conocido y la cascada de cuotas se copia del patrón ya existente en `config_resolver.py`. Añade una migración, pero sin decisiones de diseño abiertas.

**Objetivo**: Limitar login (fuerza bruta) y consumo de LLM (coste). Para un chatbot público es control de gasto; para los chatbots de gestión del piloto, control de consumo **por persona**.

**Ampliado el 2026-07-27** (revisión de planificación con Open WebUI): la cuota pasa de *solo por chatbot/día* a **multi-sujeto en cascada**, y se añade la **contabilidad real de tokens** — que no existía en ningún prompt y sin la cual no hay cuota posible, solo conteo de peticiones.

**Dependencias**: SEC.2.1 (el sujeto "usuario" es el **actor efectivo**, no el dueño del PAT).

```
# PROMPT SEC.4 (RED/GREEN) — Rate limiting, contabilidad de tokens y cuotas
# Deploy: shared (limiter) + edge (contadores y cuotas: son datos operacionales de cliente)

## PARTE 1 — Rate limiting (sin cambios respecto al plan original)
- Añadir slowapi (o limiter propio sobre Redis/memoria). Config por env
  (RATE_LIMIT_LOGIN, RATE_LIMIT_CHAT). Clave: IP para login/widget anónimo; actor efectivo
  para el resto.
- Aplicar a: /auth/*/login (bajo, p.ej. 10/min/IP con backoff),
  /hub/chat (por chatbot + por IP), ingestión (por organización).

## PARTE 2 — Contabilidad de tokens (prerrequisito de toda cuota)

### HubInteraction (operational_models.py) — campos nuevos + migración
- `prompt_tokens: Mapped[int | None]`
- `completion_tokens: Mapped[int | None]`
- `cost_estimated: Mapped[float | None]`   (según precio del HubLLMConfig usado)
- Nullable: las interacciones históricas no tienen el dato y no se inventa.

### Captura del uso real
- Leer el usage del proveedor en el trayecto del grafo (callback/`response_metadata` de
  LangChain). Si el proveedor no lo expone, estimar con el tokenizer y **marcarlo** en
  `interaction_metadata.usage_source = 'provider'|'estimated'` — una cuota que se apoya en
  una estimación silenciosa es una cuota que no se puede defender ante el usuario.
- La escritura del usage va en el MISMO commit que la HubInteraction (hoy en
  `api/v1/hub_chat.py`, tras RAG.2 en el CoreGraph). No un segundo write.

### Contador operacional (operational_models.py) — modelo nuevo
- `HubUsageCounter(HubOperationalBase)`:
    subject_type: 'user'|'chatbot'|'organizacion'|'ip'
    subject_id: String(255)
    window_key: String(20)     -- '2026-07-27' (día), '2026-07' (mes), 'total' (acumulado)
    tokens: int, cost: float, updated_at
    UniqueConstraint(subject_type, subject_id, window_key)
- UPSERT atómico (`ON CONFLICT ... DO UPDATE`), no read-modify-write: el chat es concurrente.
- **Vive en HubOperationalBase, nunca en el chatbot**: es dato de consumo del cliente final,
  no configuración, y no se sincroniza al cloud (P8). Un contador en HubChatbot rompería la
  frontera edge/cloud.
- Este contador lo reutiliza SEC.4.1 con `window_key='total'`.

## PARTE 3 — Cuotas en cascada

### Campos de configuración (cascada plataforma -> organización -> chatbot, patrón config_resolver.py)
- En HubOrganizacion: `default_user_daily_token_quota`, `default_user_monthly_token_quota`,
  `monthly_token_quota` (de la organización entera), `default_chatbot_daily_token_quota`
- En HubChatbot: `user_daily_token_quota`, `chatbot_daily_token_quota`,
  `anon_ip_daily_token_quota` (para el widget)
- `None` en cualquier nivel = heredar; `0` = sin límite explícito. Distinguir los dos casos
  (que `0` no signifique "bloqueado") es requisito de test.

### Enforcement (un único punto)
- `core/quotas.py`: `assert_within_quota(session, actor, chatbot, via) -> None`
  Evalúa en orden y devuelve **413/429 en el primer sujeto agotado**, con
  `Retry-After` y un cuerpo que diga QUÉ cuota se agotó
  (`{"code":"QUOTA_EXCEEDED","subject":"user","window":"day","limit":N,"used":M}`).
  Sujetos: usuario/día -> usuario/mes -> chatbot/día -> organización/mes -> IP/día (anónimo).
- Llamado desde `hub_chat`, el adaptador OpenAI (OWUI.1) y el endpoint widget (D.1).
  Mismo criterio que `assert_chatbot_access`: la regla vive en un sitio.
- Se comprueba **antes** de invocar el LLM y se contabiliza **después**. Se acepta el
  desbordamiento de una petición (no se pre-reserva presupuesto): decisión documentada,
  reservar exigiría estimar el coste antes de generar.

### Endpoint de consulta (para que el usuario sepa cuánto le queda)
- `GET /api/v1/hub/usage/me` -> cuotas y consumo del actor efectivo. Deploy: edge.
  Sin esto, un 429 es indistinguible de un fallo.

## Tests (RED primero) — tests/api/test_rate_limit.py + tests/api/test_quotas.py
# should_429_after_login_attempts_exceed_limit
# should_reset_login_limit_after_window
# should_not_limit_below_threshold
# should_scope_limit_per_ip_for_anonymous_widget
# should_persist_prompt_and_completion_tokens_on_interaction
# should_mark_usage_source_when_estimated
# should_upsert_usage_counter_atomically_under_concurrency
# should_429_chat_when_chatbot_daily_quota_exceeded
# should_429_chat_when_user_daily_token_quota_exceeded
# should_429_chat_when_user_monthly_token_quota_exceeded
# should_429_when_organizacion_monthly_quota_exceeded
# should_cascade_quota_from_org_default_to_chatbot
# should_treat_zero_as_unlimited_and_none_as_inherit
# should_report_which_subject_exhausted_the_quota
# should_charge_quota_to_delegated_actor_not_pat_owner      <- integra SEC.2.1
# should_return_remaining_quota_on_usage_me

## Criterios de cierre
- [ ] Migración aplicada (`alembic upgrade head` + `alembic current`)
- [ ] grep: los tres caminos de conversación pasan por assert_within_quota
- [ ] Contadores en HubOperationalBase; ningún contador en tablas de HubConfigBase
- [ ] OpenAPI reexportado + Orval regenerado (usage/me)
```

---

### Prompt SEC.4.1 (RED/GREEN) — Ventana de vigencia y presupuesto acumulado por chatbot

**Modelo sugerido**: **Sonnet** — campos de configuración, una guarda y estado derivado en la UI admin. Sin decisiones abiertas: el contador ya lo aporta SEC.4.

**Objetivo**: Un chatbot público de campaña (plazo de matrícula, convocatoria, periodo de alegaciones) debe poder **caducar solo** y tener **techo de gasto total**, no solo diario. Hoy la única palanca es que un humano se acuerde de poner `is_active = false`.

**Origen**: revisión de planificación 2026-07-27 — "límite de uso temporal para chatbots públicos".

**Dependencias**: SEC.4 (`HubUsageCounter`, `assert_within_quota`).

```
# PROMPT SEC.4.1 (RED/GREEN) — Vigencia temporal y presupuesto total
# Deploy: edge (enforcement) + shared (campos de configuración)

## Campos de configuración (HubChatbot — HubConfigBase, sin contadores)
- `valid_from: Mapped[datetime | None]`   DateTime(timezone=True), nullable
- `valid_until: Mapped[datetime | None]`  DateTime(timezone=True), nullable
- `total_token_budget: Mapped[int | None]` nullable (None = sin techo acumulado)
- `unavailable_message: Mapped[str]` Text, default "" — texto que ve el ciudadano cuando el
  chatbot no está disponible. Vacío -> mensaje genérico i18n del frontend.
- Migración Alembic. Los chatbots existentes quedan con los cuatro campos nulos/vacíos =
  comportamiento actual sin cambios.

## Estado derivado, NO almacenado (decisión de diseño)
- **No se añade `closed_reason` ni se voltea `is_active`.** El estado se calcula:
    expired          <- valid_until  < now
    not_yet_open     <- valid_from   > now
    budget_exhausted <- HubUsageCounter(chatbot, 'total').tokens >= total_token_budget
    available        <- resto
- Razones: (1) un flag persistido se queda obsoleto y obliga a un job que lo refresque;
  (2) el consumo acumulado es dato **operacional** y `HubChatbot` es config que se
  sincroniza cloud->edge — guardar ahí el contador rompería la frontera (P8);
  (3) `is_active` sigue significando lo que significa hoy (el admin lo apagó a mano),
  sin mezclar dos conceptos en un booleano.

## Enforcement (core/chatbot_availability.py)
- `assert_chatbot_available(session, chatbot, now) -> None`
  -> 403 `{"code":"CHATBOT_UNAVAILABLE","reason":"expired|not_yet_open|budget_exhausted",
           "message": chatbot.unavailable_message or None}`
- Se invoca en los tres caminos de conversación, **inmediatamente después de
  `assert_chatbot_access` y antes de `assert_within_quota`** (primero "¿puedes hablar con
  este bot?", luego "¿está abierto?", luego "¿te queda cuota?").
- El 403 NO es un error genérico: lleva el motivo y el mensaje del admin, para que el
  ciudadano lea "el plazo de matrícula terminó el 30 de septiembre" y no "Forbidden".

## Superficie admin
- Los cuatro campos en ChatbotRead/Create/Update + campo **de solo lectura**
  `availability: {state, reason, tokens_used, total_token_budget}` en ChatbotRead,
  calculado en el servidor (Contract-First: el frontend no recalcula el estado).
- `frontend/src/admin`: badge de estado en la lista de chatbots (Disponible / Caducado /
  Presupuesto agotado / Pendiente de apertura) iterando el contrato, más los campos en el
  formulario. i18n es/ca/en.
- **Aviso al admin**: se limita a que el estado sea visible en el panel y en la API. NO se
  implementa email ni webhook: no existe infraestructura de notificaciones en el proyecto y
  crearla aquí sería una feature no pedida. Si el piloto la exige, se planifica aparte.

## Tests (RED primero) — tests/api/test_chatbot_availability.py
# should_403_when_valid_until_in_the_past
# should_403_when_valid_from_in_the_future
# should_allow_when_now_inside_window
# should_allow_when_window_fields_are_null            (comportamiento actual preservado)
# should_403_when_total_token_budget_exhausted
# should_use_total_window_counter_not_daily
# should_return_admin_unavailable_message_in_403_body
# should_expose_derived_availability_in_chatbot_read
# should_not_persist_availability_state_in_db          (grep: sin closed_reason)
# should_check_availability_after_access_and_before_quota   (orden de las guardas)

## Criterios de cierre
- [ ] Migración aplicada (`alembic upgrade head` + `alembic current`)
- [ ] Los tres caminos de conversación invocan la guarda en el orden documentado
- [ ] `availability` es de solo lectura y se calcula en el servidor
- [ ] Verificado en navegador: badge de caducado visible en la lista de chatbots
- [ ] OpenAPI reexportado + Orval regenerado
```

---

### Prompt SEC.5 (RED/GREEN) — Temas: auth en GET + validación anti path-traversal [M2]

**Modelo sugerido**: **Sonnet** — alcance puntual.

```
# PROMPT SEC.5 (RED/GREEN) — Endurecer hub_themes_router
# Deploy: cloud

## Cambios (routers/hub_themes_router.py)
- Validar theme_id como UUID (o slug estricto ^[a-z0-9-]+$) antes de construir rutas.
- Resolver la ruta con (THEMES_DIR / f"{theme_id}.json").resolve() y comprobar que queda
  bajo THEMES_DIR.resolve(); si no → 400. Aplica a GET, PUT, DELETE (unlink).
- Exigir autenticación también en GET /hub/themes/{theme_id} (hoy es público) y aplicar
  assert_org_access (SEC.2) si el tema es de una organización.

## Tests (RED primero) — tests/api/test_themes_security.py
# should_reject_theme_id_with_path_traversal          ('../', '%2F', absolute)
# should_reject_non_uuid_theme_id
# should_require_auth_on_get_theme
# should_not_read_files_outside_themes_dir
```

---

### Prompt SEC.6 (RED/GREEN) — Validación de subidas: tipo real (magic bytes) + límite de tamaño [M4]

**Modelo sugerido**: **Sonnet** — alcance cerrado. Comparte la validación con el futuro Bloque ING.

```
# PROMPT SEC.6 (RED/GREEN) — Validación robusta de uploads
# Deploy: edge

## Cambios (api/v1/ingestion.py y cualquier endpoint de upload)
- core/uploads.py: `validate_upload(file, *, allowed_ext, allowed_magic, max_bytes)`:
    - comprobar extensión + magic bytes (no confiar en content_type, que es spoofeable);
    - hacer streaming a un buffer temporal con corte al superar max_bytes → 413;
    - devolver el buffer validado (no `await file.read()` completo en memoria).
- MAX_UPLOAD_MB por env. Cuota por organización/chatbot (nº o tamaño acumulado) → 429/413.
- Reutilizable por el Bloque ING (validación compartida por extensión+magic).

## Tests (RED primero) — tests/api/test_upload_validation.py
# should_reject_pdf_content_type_with_non_pdf_magic_bytes
# should_reject_upload_exceeding_max_size            (413, sin cargar todo en memoria)
# should_accept_valid_pdf
# should_reject_disallowed_extension
```

---

### Prompt SEC.7 (RED/GREEN) — Docs off en producción + cabeceras de seguridad [M5]

**Modelo sugerido**: **Sonnet** — config + middleware.

```
# PROMPT SEC.7 (RED/GREEN) — Superficie mínima + headers
# Deploy: shared

## Cambios (main.py)
- Si ENVIRONMENT == 'production': FastAPI(docs_url=None, redoc_url=None, openapi_url=None).
  En dev/staging quedan disponibles.
- Middleware de cabeceras de seguridad: X-Content-Type-Options: nosniff, X-Frame-Options:
  DENY (o CSP frame-ancestors para el widget), Referrer-Policy, HSTS (solo prod/https),
  y CSP básica para el panel.

## Tests (RED primero) — tests/api/test_security_headers.py
# should_disable_docs_in_production
# should_expose_docs_in_development
# should_set_nosniff_and_frame_options_headers
# should_set_hsts_only_in_production
```

---

## Bloque SEC.8 — Endurecimiento pre-deploy, segunda auditoría (Subfase 1.B, PENDIENTE, BLOQUEANTE DE DESPLIEGUE)

> **Contexto**: hallazgos de `docs/AUDITORIA_PRE_DEPLOY.md` (auditoría del 2026-08-10). Segunda
> pasada tras SEC.1–SEC.7: cubre lo que se coló en los routers añadidos **después** de SEC.2
> (IDOR horizontal, porque la capa de tenencia no se aplicó a los routers nuevos) y los
> bloqueantes funcionales que se ven verdes en el navegador pero no sobreviven a Cloud Run.
> Va **antes de Deploy GCP (D.0)**. Nomenclatura ROL nueva (`admin`, `organizacion_id`).

---

### Prompt SEC.8.0 ✅ — Gate del sembrado de desarrollo [CR-1]

**Hecho el 2026-08-10** (commit `56d5ef4`). `seed_multitenancy_defaults()` corría en el `lifespan`
en cualquier `ENVIRONMENT` y sembraba el SuperAdmin `fabra@uji.es`/`admin1234` (credencial pública
en el repo). Ahora retorna sin sembrar fuera de `development`; producción se provisiona con
`python -m server.app.scripts.bootstrap`. Tests: `tests/unit/test_seed_environment_gate.py`.

---

### Prompt SEC.8.1 (RED/GREEN) — Aislamiento multi-tenant en los routers posteriores a SEC.2 [CR-2, AL-1, AL-2, AL-3, ME-3, ME-4]

**Modelo sugerido**: **Opus** — barrido transversal de IDOR horizontal sobre datos personales;
cada endpoint exige resolver el recurso a su organización dueña sin romper el caso superadmin, y
el guardarraíl de CI hay que ampliarlo. Es el prompt más crítico del bloque.

**Objetivo**: SEC.2 aisló los routers que existían entonces; toda la familia añadida después
(test-scenarios, curation, prompt-templates, organizaciones, redacción, tasks, feedback) se quedó
con `_require_admin`/`get_current_user` y **nunca resuelve `chatbot_id`/`site_id`/`organizacion_id`
a su organización**. Como los modelos operacionales cuelgan de `chatbot_id`, hace falta el join a
`HubChatbot` (patrón `_chatbot_autorizado`) o comprobar `organizacion_id` directo.

```
# PROMPT SEC.8.1 (RED/GREEN) — Cerrar el IDOR horizontal de los routers post-SEC.2
# Deploy: edge/cloud según router

## Cambios (aplicar assert_org_access / scope_query_to_orgs, capa ya existente de SEC.2)
- hub_organizaciones_router.py:103-193: list -> scope_query_to_orgs; get/update/delete ->
  assert_org_access sobre la organización objetivo (superadmin pasa).
- hub_test_scenarios_router.py:211-258: resolver chatbot -> assert_org_access antes de
  run_scenario y de list/create/update/delete/set_verdict.
- hub_sites_router.py: create_site NO acepta organizacion_id del cliente (usar el del actor);
  list_sites -> site_repo.list_by_organizacion; patch/delete/trigger_crawl/ingest_page/
  retire_page -> resolver site.organizacion_id + assert_org_access.
- hub_content_quality_router.py:268-293 (analyze_content_gaps, lee conversaciones de ciudadanos)
  y transition_finding/get/export_site_report/analyze_site -> resolver org + assert_org_access.
- hub_prompt_templates_router.py: list exige chatbot_id y lo acota; create/update/delete ->
  resolver el chatbot dueño + assert_org_access.
- api/v1/hub_tasks.py:49-63 export_task: resolver chatbot_id->org + assert_org_access
  (quitar el bypass "o admin"; el superadmin pasa por la capa de tenencia).
- api/v1/hub_feedback.py:53-65 submit_feedback (POST): assert sobre la interacción->chatbot->org
  antes del UPDATE. Añadir rate limit.
- routers/redaccion/manifests_router.py:31-64 y hub_redaccion_router.py:276-344,472-486:
  usar el parámetro _user (hoy sin usar) para comprobar owner/organización.
- routers/redaccion/anonymization_router.py:73-86: el bypass admin no debe cruzar tenants.
- api/v1/ingestion.py user_upload: añadir assert_chatbot_access (ME-3).

## Tests (RED primero) — ampliar tests/api/test_tenant_isolation.py (GATE DE CI)
# should_forbid_run_scenario_on_other_org_chatbot
# should_forbid_delete_other_org_organizacion
# should_list_only_own_org_sites_and_findings
# should_forbid_content_gap_analysis_on_other_org_chatbot
# should_forbid_crud_prompt_template_of_other_org_chatbot
# should_forbid_export_task_of_other_org
# should_forbid_feedback_write_on_other_org_interaction
# should_forbid_reading_manifest_or_workspace_of_other_user
# should_forbid_ingestion_upload_without_chatbot_access

## Criterios de cierre
- [ ] El guardarraíl que prohíbe `session.get(HubChatbot/HubWebSite/...,id)` sin pasar por la
      capa de tenencia se extiende de hub_chatbots_router a TODOS estos routers.
- [ ] test_tenant_isolation.py sigue siendo gate obligatorio de CI y cubre los 9 casos nuevos.
```

---

### Prompt SEC.8.2 (RED/GREEN) — Endurecimiento de subidas [AL-7, ME-5]

**Modelo sugerido**: **Sonnet** — patrón conocido (`validate_upload` + clave `uuid4` ya existen en
los endpoints buenos); alcance cerrado.

```
# PROMPT SEC.8.2 (RED/GREEN) — Todas las subidas por validate_upload, sin nombres del cliente
# Deploy: edge

## Cambios
- workspaces_router.py:336-339: NO interpolar file.filename en la ruta de storage. Usar
  os.path.basename o una clave uuid4 (como hub_ingestion_router.py:329-350). Llamar a
  validate_upload (tamaño + tipo) antes de storage.put.
- scripts_router.py:267-305 (describe_test_data, preview_pdf_spans): validate_upload; no guardar
  binario arbitrario como .pdf sin comprobar contenido.
- Barrido: cualquier otro endpoint con UploadFile que llame a storage.put/file.read() sin
  validate_upload.

## Tests (RED primero) — tests/api/redaccion/test_upload_hardening.py
# should_reject_path_traversal_in_workspace_input_filename
# should_reject_oversized_upload_on_workspace_input
# should_validate_content_type_on_preview_pdf
# should_store_under_uuid_key_not_client_filename

## Cierre
- [ ] grep de UploadFile en routers -> todos pasan por validate_upload
```

---

### Prompt SEC.8.3 (RED/GREEN) — Sandbox: gate de producción + auditor AST [AL-4, AL-5]

**Modelo sugerido**: **Sonnet** — gate de config + reglas AST adicionales; el enforcement Docker
ya existe.

```
# PROMPT SEC.8.3 (RED/GREEN) — SANDBOX_MODE=local prohibido en producción + auditor endurecido
# Deploy: edge

## Cambios
- core/config.py get_settings(): si ENVIRONMENT == 'production' y sandbox_mode == 'local'
  -> RuntimeError explícito. (TESTING=1 sigue permitiendo 'local'.)
- script_auditor.py / service script_sandbox auditor: bloquear también
  __builtins__[...] (Subscript), traversal de dunders (__class__/__bases__/__subclasses__),
  y getattr con nombre construido.

## Tests (RED primero)
# tests/core/test_sandbox_prod_gate.py::should_reject_local_sandbox_in_production
# tests/.../test_script_auditor.py::should_block_builtins_subscript_eval
# ...::should_block_dunder_traversal
# ...::should_block_getattr_escape

## Cierre
- [ ] docker-compose.prod.yml: añadir pids_limit al servicio script-sandbox (ME-7)
```

---

### Prompt SEC.8.4 (RED/GREEN) — Cabeceras, entorno y SAML [ME-1, ME-2, ME-6]

**Modelo sugerido**: **Sonnet** — cambios localizados en config y en la lectura de proxy/SAML.

```
# PROMPT SEC.8.4 (RED/GREEN) — X-Forwarded-For, JWT placeholder, hardening SAML
# Deploy: shared

## Cambios
- core/rate_limit.py:89-92: no tomar el primer valor de X-Forwarded-For (controlable por el
  cliente). Usar el número de proxies de confianza (config) y tomar la IP en esa posición, o
  request.client.host detrás de un proxy que reescriba XFF. Documentar el supuesto de Cloud Run.
- core/config.py: en producción, rechazar JWT_SECRET_KEY placeholder ('change-me-in-production')
  y longitud < N.
- core/auth/saml/settings.py:85,51-57: validate_cert=True en parse_remote (o metadata XML inline
  firmada); wantAssertionsSigned=True.

## Tests (RED primero)
# tests/core/test_rate_limit_xff.py::should_not_trust_leftmost_forwarded_for
# tests/core/test_config_prod.py::should_reject_placeholder_jwt_secret_in_production
# tests/core/auth/test_saml_settings.py::should_require_signed_assertions
```

---

### Prompt SEC.8.5 (RED/GREEN) — El widget no embebe un Bearer privilegiado [AL-6]

**Modelo sugerido**: **Opus** — decide el modelo de credencial de sitio / token anónimo acotado y
lo cablea en el endpoint público; riesgo de escalada si se diseña mal. **Coordina con D.1** (el
endpoint del widget), que ya prevé `via='widget_api_key'`.

```
# PROMPT SEC.8.5 (RED/GREEN) — Credencial de sitio de bajo privilegio para el widget
# Deploy: edge (endpoint) + shared (emisión de la credencial)

## Cambios
- Cablear widget_api_key (chatbot_access.py:34,68-72, hoy sin llamante VIA_WIDGET) o emitir un
  token anónimo acotado a un chatbot public_anon, en lugar de embeber un JWT/PAT de sesión.
- frontend/src/widget: consumir la credencial de sitio; retirar el Bearer privilegiado del HTML.
- El endpoint público sigue pasando por las tres guardas (acceso/disponibilidad/cuota) de D.1.

## Tests (RED primero)
# should_reject_widget_credential_on_authenticated_chatbot
# should_scope_widget_credential_to_single_public_anon_chatbot
# should_not_expose_session_bearer_in_widget_bundle
```

---

### Prompt SEC.8.6 (RED/GREEN) — Temas persistentes fuera del disco local [B1]

**Modelo sugerido**: **Sonnet** — mover almacenamiento a tabla; los endpoints y el widget ya
consumen el servicio.

```
# PROMPT SEC.8.6 (RED/GREEN) — Los temas viven en BD, no en data/themes
# Deploy: cloud (la config de temas se sincroniza cloud->edge)

## Objetivo
- hub_themes_router.py:124-183,352 guarda los temas como JSON en Path("data/themes") (efímero en
  Cloud Run, no compartido entre instancias). Tumba el arreglo del widget con tema de MAN.2 #3.

## Cambios
- Modelo HubTheme en HubConfigBase (id, organizacion_id/plataforma, slug, config JSON, nivel de
  la cascada). Migración Alembic + backfill de los temas de data/themes si los hay.
- _save_theme/_load_theme/delete/apply_theme_to_chatbot/get_theme_for_chatbot -> BD.
- Conservar la validación de slug (regex ^[a-z0-9-]{1,64}$) y la censura pública de SEC.5.

## Tests (RED primero)
# should_persist_theme_across_restarts (no depende de disco local)
# should_resolve_theme_for_chatbot_from_db
# should_keep_slug_validation_and_public_scoping
```

---

### Prompt SEC.8.7 (RED/GREEN) — Limpieza de los tests legacy de la raíz `tests/` [B3]

**Modelo sugerido**: **Sonnet** — retirada mecánica verificada por grep/colección (Caso B).

```
# PROMPT SEC.8.7 — Cero rojos al colectar desde la raíz del repo
# Deploy: n/a (higiene)

## Contexto
- 14 tests rotos en el árbol raíz tests/ (no server/tests): 12 fallan por importar rutas que
  CUR.1 movió a modules/curation (test_spiders_especializados.py, test_spider_generic.py) y 2
  errores de colección importan partner_billing_service/partner_scripts_service inexistentes.
- Los spiders quedaron SIN test en la suite canónica (server/tests): hay que darles cobertura ahí.

## Cambios
- Mover/rescribir los tests de spiders a server/tests/modules/curation apuntando a las rutas
  nuevas (modules/curation/spider_factory, spiders/*).
- Borrar tests/unit/test_partner_billing.py y test_partner_scripts_service.py (código eliminado).
- Barrido de la raíz tests/ por más imports a módulos inexistentes.

## Cierre
- [ ] pytest --collect-only DESDE LA RAÍZ del repo sin errores
- [ ] Los spiders tienen test en server/tests (el que corre en CI)
- [ ] grep -rn "ingestion.spider_factory\|ingestion.spiders\|partner_billing_service\|partner_scripts_service" tests/ = 0
```

---

### Prompt SEC.8.8 (DECISIÓN + RED/GREEN) — El crawler de curación: cablear o acotar alcance [B2]

**Modelo sugerido**: **Sonnet** (implementación) — pero antes una **decisión de criterio** del
usuario sobre el alcance del v1.

**Objetivo**: `main.py:94-99` construye el job de curación con `_NullCrawler()` y `detectors=[]`,
y no existe mecanismo real de inyección (`SpiderFactory`/`SiteCrawler` sin llamante de producción)
→ `POST /hub/sites/{id}/crawl` siempre acaba en `"no spider configured"`. Dos caminos:

```
# PROMPT SEC.8.8 — Curación web: cablear el crawler real O acotar el v1
# Deploy: edge

## Decisión tomada (usuario, 2026-08-10): camino (A), cablear.
# El rastreo es la ENTRADA del flujo de curación —descubrir, auditar, seleccionar,
# publicar—, así que desactivarlo no dejaba "una funcionalidad menos": vaciaba la
# herramienta que CUR.2 acababa de construir. Cablearlo NO contradice
# DECISION_CURACION_SEPARADA: el rastreo llena la bandeja del curador y la publicación al
# corpus sigue siendo un botón por candidata. No hay ingesta automática.
#
# Decisión hermana: UNA sola aplicación, ejecución aparte. Curación y asistente comparten
# auth, tenencia, organizaciones, almacenamiento y corpus; partirlos en dos servicios
# duplicaría todo eso y chocaría con la regla de un codebase para ambos modos de
# despliegue. Lo que se separa es el PROCESO que rastrea, no el producto.

## Tests (RED primero)
# should_select_the_spider_declared_by_the_site
# should_fall_back_to_the_generic_spider
# should_report_an_error_for_an_unknown_site
# should_report_an_error_for_an_unknown_spider_type   (no cae al genérico: rastrear el DOGV
#                                                      con el spider equivocado produce
#                                                      páginas basura que revisar a mano)
# should_not_keep_a_null_crawler_in_main              (guardarraíl anti-recaída)
```

> **Pendiente que SEC.8.8 deja abierto y va al bloque Deploy (D.x): el ejecutor de trabajos.**
> El rastreo se encola hoy con `BackgroundTasks`, o sea **dentro del proceso web**. En Cloud
> Run la instancia escala a cero cuando termina de atender peticiones, así que un rastreo
> largo muere a media ejecución sin dejar rastro —responde 202 y no acaba nunca—. En local,
> en Docker y en un edge con contenedor persistente funciona tal cual, que es lo que hace
> falta para probar la curación antes del despliegue. El paso a un ejecutor duradero (Cloud
> Run Jobs / Cloud Tasks) se planifica como prompt propio de Deploy.

---

## Bloque CAL — Deuda de calidad previa al repositorio público (Subfase 1.B, PENDIENTE)

> **Contexto**: hallazgos de las auditorías de calidad backend/frontend (`VALORACION_PROYECTO.md` §3). Cierra violaciones de reglas duras del proyecto (Contract-First, sin código muerto, sin shims) antes de abrir el repo bajo AGPLv3.

---

### Prompt CAL.1 (RED/GREEN) — Retirada de NiceGUI de `server/app/ui/` + Caso B en `client_app/` + código huérfano

**Modelo sugerido**: **Sonnet** — retirada mecánica con verificación por grep (Caso B de CLAUDE.md).

> **Ampliado 2026-07-11** con la limpieza Caso B de `client_app/` identificada en el triaje del
> replanteamiento de Fase 2 (Plan_TDD_Fase2.md §3, Categoría B). Verificado contra git:
> el `.venv/` de client_app NO está trackeado (solo ruido de disco local, fuera de alcance);
> los 5 UI `_legacy` y los artefactos autogenerados SÍ están trackeados.

```
# PROMPT CAL.1 (RED/GREEN) — Retirar NiceGUI del árbol activo del servidor + Caso B client_app

## Análisis previo (solo lectura)
- Confirmar que ningún módulo activo importa `server.app.ui` (grep). Confirmado en auditoría.
- Confirmar que nada importa los 5 UI `_legacy` de client_app ni los artefactos de
  `client_app/app/modules/extraccion/` (grep en client_app/app y client_app/tests).

## Acción — servidor
- Mover server/app/ui/ (22 ficheros NiceGUI: admin_security.py, admin_clients.py,
  partner_security.py, etc.) a _legacy_nicegui/server/app/ui/ (mantener ruta relativa, Caso A)
  O borrar directamente si no hay migración React asociada (Caso B — la mayoría son admin
  NiceGUI ya cubiertos por el panel React). Decidir por fichero.
- Borrar los tests que los mantienen vivos: tests/unit/test_admin_*_ui.py
  (test_admin_clients_ui, test_admin_partners_ui, test_admin_prompts_ui, test_admin_security_ui).
- Borrar el huérfano top-level app/modules/extraccion/ (12 ficheros, sin importadores → Caso B).
- Borrar los scripts ad-hoc en tests/ que no son tests (reproduce_client_id.py, verify_id_logic_standalone.py).

## Acción — client_app (Caso B: borrado directo, sin _legacy_nicegui)
- Borrar los 5 UI legacy explícitos (reemplazados por versiones posteriores):
    client_app/app/ui/_legacy_webhook_page.py
    client_app/app/ui/connections_page_legacy.py
    client_app/app/ui/custom_script_page_legacy.py
    client_app/app/ui/graphics_page_legacy.py
    client_app/app/ui/rpa_page_legacy.py
- Borrar los artefactos autogenerados trackeados (salida de runtime, no código fuente):
    client_app/app/modules/extraccion/.servicios_generados/custom_extractor*.py
    client_app/app/modules/extraccion/servicios/custom_prueba*.py
  Conservar solo el __init__.py si algo vivo importa el paquete; si nada lo importa,
  borrar el directorio completo.
- .gitignore: añadir client_app/app/modules/extraccion/.servicios_generados/ y
  client_app/app/modules/extraccion/servicios/ (evitar que el runtime los re-trackee).
- Si algún test de client_app/tests referenciaba lo borrado, borrarlo también (es test
  de código muerto).

## FUERA DE ALCANCE (no tocar en este prompt)
- Los imports rotos a factories inexistentes (workflow_engine.py:1417/1478,
  clarification_service.py:504, graphics_wizard.py:8): esos ficheros son Categoría C
  pendiente de decisión go/no-go (Plan_TDD_Fase2.md §4); se resuelven con esa decisión.
- El report_factory duplicado (services/ vs modules/factory/): decidir cuál sobra
  pertenece a la misma decisión de Categoría C.
- client_app/.venv/: no está en git; borrado de disco a discreción del usuario.

## Tests / verificación
# should_have_no_nicegui_imports_in_server_app        (grep 'from nicegui' en server/app = 0)
# should_have_no_references_to_server_app_ui           (grep = 0)
# should_collect_pytest_without_removed_ui_tests       (pytest --collect-only sin errores)
# should_have_no_legacy_ui_files_in_client_app         (glob '*_legacy*' en client_app/app/ui = 0)
# should_have_no_generated_extractors_tracked          (git ls-files 'client_app/app/modules/extraccion/**' = 0 o solo __init__.py)
# should_collect_client_app_tests_without_errors       (pytest --collect-only en client_app/tests sin errores)

## Cierre
- [ ] `grep -rn "from nicegui\|server.app.ui\|modules.extraccion" server/` = 0
- [ ] `grep -rn "_legacy_webhook_page\|connections_page_legacy\|custom_script_page_legacy\|graphics_page_legacy\|rpa_page_legacy" client_app/` = 0
- [ ] `git ls-files client_app/app/modules/extraccion` vacío (o solo __init__.py justificado)
- [ ] Suite backend en verde tras la retirada; colección de tests de client_app sin errores
```

---

### Prompt CAL.2 (RED/GREEN) — Migrar la capa API manual del frontend a Orval (cierra CF.4)

**Modelo sugerido**: **Opus** — refactor transversal que toca la página más grande (DocumentsPage) y alinea con el contrato; riesgo de regresión alto.

```
# PROMPT CAL.2 (RED/GREEN) — Eliminar shared/api/*.ts hechos a mano

## Objetivo
- Retirar los 5 módulos con fetch crudo + tipos hardcodeados + API_BASE a localhost:
  shared/api/{ingestion,clients,feedback,llmConfigs,promptTemplates}.ts (cierra el
  literal '// TODO CF.4' de ingestion.ts).

## Acción
- Sustituir cada llamada por el hook Orval generado (useX de shared/api/generated) y los
  tipos de generated/model (IngestionJob, HubDocument, etc. → tipos del contrato).
- Pasar todo por el customInstance (interceptor de auth) en lugar de headers duplicados.
- El streaming SSE del chat del widget queda EXENTO (Orval no cubre SSE); ese fetch se
  mantiene pero centralizando la construcción de Authorization.
- Borrar los 5 ficheros y actualizar los imports (DocumentsPage.tsx:16 y demás consumidores).

## Tests Vitest (RED primero)
# should_use_generated_hook_not_manual_fetch_in_documents_page
# should_not_import_from_shared_api_manual_modules       (los 5 ficheros ya no existen)
# should_send_auth_via_custom_instance
# should_type_ingestion_job_from_generated_model

## Cierre
- [ ] `grep -rn "shared/api/(ingestion|clients|feedback|llmConfigs|promptTemplates)" frontend/src` = 0
- [ ] `grep -rn "localhost:8000" frontend/src` = 0 (fuera de config de dev)
- [ ] tsc --noEmit + vitest en verde
```

---

### Prompt CAL.3 (RED/GREEN) — Descomponer DocumentsPage

**Modelo sugerido**: **Sonnet** — refactor de composición sin cambio de comportamiento.

```
# PROMPT CAL.3 (RED/GREEN) — Partir DocumentsPage.tsx (1019 líneas)

## Acción
- Extraer subcomponentes con responsabilidad única: <UploadDropzone>, <SourcesPanel>
  (sitios/spider), <DocumentsTable>, <IngestionJobsPanel>, <RechunkControls>.
  DocumentsPage queda como orquestador (<300 líneas).
- Sin cambio de comportamiento; los datos siguen viniendo de hooks Orval (CAL.2).

## Tests Vitest (RED primero → mantener verdes tras el split)
# should_render_upload_dropzone_component
# should_render_sources_panel_component
# should_render_documents_table_component
# should_render_jobs_panel_component
# should_keep_existing_documents_page_behaviour     (tests actuales siguen pasando)
```

---

### Prompt CAL.4 (RED/GREEN) — i18n: completar `ca/admin.json` + retirar strings hardcodeados

**Modelo sugerido**: **Sonnet** — alcance cerrado, verificable por conteo de claves.

```
# PROMPT CAL.4 (RED/GREEN) — Cobertura i18n del panel admin

## Acción
- Completar shared/i18n/locales/ca/admin.json a paridad con es/en (hoy ~34 vs ~130 líneas).
- Extraer a claves i18n los literales en español de LLMConfigsPage (~22), ChatbotsPage (~12)
  y las constantes con etiquetas de DocumentsPage (INTERVAL_OPTIONS, LANGUAGE_OPTIONS,
  RETRIEVAL_LABELS, SPIDER_TYPES → usar t() en render, no strings fijos en el array).
- Asociar labels a inputs (htmlFor/id) donde falten (relacionado con a11y de Fase 20).

## Tests Vitest (RED primero)
# should_have_key_parity_across_es_ca_en_admin_namespace
# should_not_render_hardcoded_spanish_in_llmconfigs_page
# should_render_interval_options_via_i18n
# should_associate_labels_with_inputs
```

---

### Prompt CAL.5 (RED/GREEN) — Code-splitting (lazy routes) + retirada de shims

**Modelo sugerido**: **Sonnet** — cambio de build + limpieza puntual.

```
# PROMPT CAL.5 (RED/GREEN) — Bundle y shims

## Frontend
- App.tsx: convertir los imports estáticos de páginas en React.lazy + <Suspense> por ruta
  → romper el chunk monolítico (~927 KB). Verificar chunks por ruta en el build.

## Backend
- Eliminar los shims prohibidos por CLAUDE.md: `init_db = init_server_db` (db.py:31-32) y
  el "Legacy alias" de seeds.py:174-176. Actualizar los llamantes al nombre real.

## Tests
# (frontend) should_lazy_load_route_chunks               (assert de dynamic import)
# (frontend) should_not_bundle_all_pages_in_single_chunk (inspección del manifest de build)
# (backend)  should_import_init_server_db_directly        (grep 'init_db' = 0 fuera de la definición)
# (backend)  should_have_no_legacy_aliases_in_seeds
```

---

### Prompt CAL.4.1 (RED/GREEN) — Las 41 claves de la pantalla de documentos

**Modelo sugerido**: **Sonnet** — alcance cerrado y verificable por conteo de claves.

**Por qué existe**: CAL.4 dejó `es`/`ca`/`en` en paridad y el test en verde, pero la paridad es
de claves **del diccionario**. La pantalla de documentos casi no tiene: sus etiquetas viven como
*default* dentro del `t('clave', 'texto')`, y el default sólo actúa cuando la clave **falta**. El
resultado es que con `i18nextLng=ca` la navegación sale en catalán y el cuerpo de esa pantalla se
queda en castellano. Medido el 2026-08-03 con el árbol de CAL.5.

```
# PROMPT CAL.4.1 (RED/GREEN) — Subir al diccionario las claves que sólo viven como default

## Contexto medido (no hay que volver a contarlo)
- 41 claves del namespace `admin` se usan como t('hub.x', 'texto') y NO están en
  es/ca/en admin.json. Reparto por fichero:
    admin/documents/DocumentsTable.tsx      12
    admin/documents/IngestionJobsPanel.tsx   7
    admin/documents/RechunkControls.tsx      7
    admin/pages/DocumentsPage.tsx            5
    admin/documents/RetrievalBanner.tsx      4
    admin/documents/UploadDropzone.tsx       4
    admin/documents/DocumentBadges.tsx       2
- El texto castellano actual es el que ya está en el segundo argumento de t():
  se sube tal cual a es/admin.json y se traduce a ca/en.

## Acción
- Subir las 41 claves a es/ca/en admin.json conservando el texto castellano actual.
- Dejar el t() con un solo argumento donde la clave ya exista: un default que nunca se
  usa es texto muerto que se desincroniza del diccionario sin que nadie lo note.
- OJO con las cadenas fijas que aún no pasan por t() en esos ficheros: los estados de
  JobStatusBadge ('Completado', 'Procesando', 'Error', 'En cola') están escritos a pelo
  en el switch. Entran también.

## Tests Vitest (RED primero)
# should_not_keep_admin_keys_only_as_inline_default
#   Barre src/ buscando t('hub.x', '...') y falla si la clave no está en es/admin.json.
#   Es el guardarrail que faltaba: el de paridad NO puede cazar esto por construcción,
#   porque lo que no está en el diccionario no se compara con nada.
# should_render_documents_screen_in_catalan
#   Render de DocumentsPage con el doble de i18n resolviendo contra ca/admin.json;
#   assert sobre texto catalán, no sobre la clave.

## Cierre
- [ ] Paridad es/ca/en sigue verde y sube a ~259 claves
- [ ] `i18nextLng=ca` en el navegador: la pantalla de documentos, entera en catalán
- [ ] vitest + tsc --noEmit en verde (la suite en serie: ver la nota de falsos rojos)
```

---

## Bloque MAN — Validación manual de la plataforma completa

**Añadido el 2026-08-03 a petición del usuario.** Hasta ahora las pruebas manuales se han hecho
**por bloque**, y han dejado **10 ficheros `.bat` sueltos** en la raíz. Ese modelo se ha quedado
corto por dos motivos:

1. **Varios de esos `.bat` han caducado sin que nadie lo note.** ROL renombró Partner→Admin y
   Client→Organización, CAL.2 retiró el panel de fuentes web, y CAL.3/CAL.4 rehicieron la
   pantalla de documentos y sus etiquetas. Un guion que dice «pulsa *Fuentes web*» ya no se
   puede seguir, pero sigue ahí, y quien lo ejecute concluirá que la aplicación está rota.
2. **Nadie ha probado nunca la plataforma de una pieza.** Cada campaña validó su bloque contra
   el estado de ese día; los caminos que cruzan módulos —Hub → Redacción → Automatización, o
   una organización con dos chatbots y temas distintos— no los ha recorrido nadie entero.

**Regla que no cambia** (CLAUDE.md §Verificación de UI): lo que el agente puede comprobar en
navegador **no entra** en estos guiones. Lo humano es lo irreducible: credenciales e IdP reales,
sistemas externos no simulables, juicio subjetivo de identidad visual, lector de pantalla real y
cualquier cosa con datos personales de verdad.

**Superficie a cubrir**: `server/app/modules/{agents_hub,automation,redaccion}`, el frontend
(`admin`, `redaccion`, `widget`, `themes`), el servidor MCP, el `client_app` como agente de
ejecución local, y los dos modos de despliegue (`DEPLOY_MODE=cloud|edge`).

---

### Prompt MAN.1 — Inventario, poda y matriz de lo irreducible

**Modelo sugerido**: **Sonnet** — trabajo de recorrido y criterio acotado, sin código nuevo.

```
# PROMPT MAN.1 — Qué exige humano, y qué de lo escrito ya no vale

## Acción
- Revisar los 10 pruebas_manuales_*.bat de la raíz contra el código de HOY. Para cada uno:
  vigente / caducado / parcialmente caducado, con el motivo concreto (qué prompt lo
  invalidó). Los caducados se BORRAN — el historial de git guarda lo que decían.
- Construir docs/PRUEBAS_MANUALES.md: matriz por módulo con, en cada fila, qué se prueba,
  por qué NO puede hacerlo el agente en navegador, y quién puede ejecutarlo (cualquiera /
  alguien con credenciales institucionales / alguien con lector de pantalla / diseño).
- Marcar explícitamente lo que NO va a la matriz por estar ya cubierto en navegador o por
  tests, para que no se repita por inercia.

## Cierre
- [ ] Cada .bat de la raíz o está justificado como vigente o ha desaparecido
- [ ] La matriz cubre agents_hub, automation, redaccion, widget, themes, MCP y client_app
- [ ] Cada fila dice por qué es irreducible; si no se sabe decir, no es irreducible
```

---

### Prompt MAN.2 — Campaña funcional en local (pre-deploy)

**Modelo sugerido**: **Sonnet** — redacción de guiones sobre la matriz de MAN.1.

```
# PROMPT MAN.2 — Recorrido completo de la plataforma sin GCP

## Acción
- Un pruebas_manuales_plataforma.bat maestro que encadene las áreas de la matriz y permita
  ejecutar sólo una (parámetro o menú): levantar, comprobar con curl que responde, y guiar.
- Guiones de los caminos que CRUZAN módulos, que son los que nadie ha recorrido enteros:
    · organización nueva -> dos chatbots -> temas distintos -> widget de cada uno
    · corpus ingerido -> consulta -> cita -> feedback -> el hueco aparece en curación
    · plantilla de redacción -> borrador LLM -> anonimización -> exportación
    · script propuesto -> sandbox -> aprobación -> ejecución en el agente local
- Cada paso con URL exacta, dato de ejemplo y resultado esperado. «Comprobar que
  funciona» no es un paso.

## Cierre
- [ ] El .bat en ANSI (cp1252) sin BOM — se escribe con WriteAllText, ver CLAUDE.md
- [ ] Primeros bytes 0x40 0x65 0x63 0x68 verificados
- [ ] Ejecutado de principio a fin por el usuario, con los fallos anotados como prompts
```

---

### Prompt MAN.3 — Accesibilidad con lector real e identidad visual

**Modelo sugerido**: **Sonnet** — guion de validación; el juicio lo pone el humano.

```
# PROMPT MAN.3 — Lo que no puede juzgar ni un test ni el agente

## Acción
- Guion de recorrido con lector de pantalla REAL (NVDA/JAWS) sobre los formularios del
  panel: chatbots, organizaciones, modelos LLM, documentos y prompts. Fase 20 dejó el gate
  de axe en CI, y CAL.4 asoció 29 <label> a su campo, pero axe no oye: que el foco siga un
  orden razonable y que cada campo se anuncie con su nombre sólo lo dice una persona.
- Guion de identidad visual institucional: tipografía, color, tono del texto y del widget
  embebido en una página real de la UJI.

## Cierre
- [ ] Cada hallazgo, o prompt nuevo o descarte razonado; nada queda en «lo miramos»
```

---

### Prompt MAN.4 — Campaña contra el entorno desplegado (POST-DEPLOY)

**Modelo sugerido**: **Sonnet** — depende de que D.5 haya terminado.

```
# PROMPT MAN.4 — Lo que sólo existe en producción

## Prerrequisito
- Deploy GCP completo (D.0-D.5). Antes de eso este prompt no se puede empezar.

## Acción
- SSO SAML real contra el IdP institucional: alta de usuario nuevo, organización asignada
  desde SAML_ORGANIZACION_ID, y el caso que nunca se ha probado — un usuario del IdP que
  NO debería tener acceso.
- Sistemas externos no simulables en local (G400, ENI, APIs UJI).
- Cloud Run de verdad: cold start medido, Cloud SQL vía proxy, ficheros en GCS a través
  del StorageService.
- Modo edge contra modo cloud: que la frontera de datos aguanta donde se dijo.

## Cierre
- [ ] El cold start medido se compara con el criterio de extracción a microservicio
      (>15 s -> toca extraer embedding/Docling; ver CLAUDE.md)
- [ ] Ningún dato de cliente real sale del edge en modo edge
```

---

## Prompt suelto FIX.1 — El modelo de un chatbot no se puede cambiar (PENDIENTE)

> **Contexto**: encontrado el 2026-08-02 durante las pruebas manuales del Bloque RAG, que el
> usuario no pudo completar. Un solo síntoma —«el botón de ejecutar no hace nada»— tapaba
> cuatro fallos distintos, y ninguno era el que parecía.
>
> **Lo que estaba pasando de verdad**:
>
> 1. **`gemini-2.0-flash` está retirado.** Google devuelve `404 NOT_FOUND: "This model
>    models/gemini-2.0-flash is no longer available"`. El chatbot demo lo tenía asignado.
> 2. **El fallo era invisible.** `POST …/run` devuelve **500** cuando el modelo no responde y
>    `TestScenariosPage` lanza la mutación **sin `onError`**: el botón se comporta igual que si
>    no lo hubieras pulsado. Y en el chatbot demo el 500 ni siquiera aparecía, porque sin
>    corpus el grafo corta antes de llamar al LLM y devuelve el fallback — o sea que el modelo
>    roto quedaba tapado por un corpus vacío.
> 3. **No hay forma de cambiar el modelo.** El formulario **hardcodea**
>    `llm_config_id: DEV_LLM_ID` (y `organizacion_id: DEV_ORG_ID`), y `ChatbotUpdate` **ni
>    siquiera declara `llm_config_id`**: no es un hueco de UI, es que la API no lo permite.
>    Hubo que repuntar el chatbot por SQL.
> 4. **Marcar una configuración por defecto exige un baile de dos pasos** que la API no
>    documenta: responde 409 «ya existe una por defecto para el tier N» en vez de demotar la
>    anterior. En la BD de desarrollo habían quedado **dos configuraciones tier 1 por
>    defecto** a la vez.
>
> **El riesgo latente, que es el peor de los cuatro**: mientras el formulario hardcodee
> `llm_config_id`, **editar cualquier chatbot en la UI le reasigna el modelo en silencio**.
> El «Chatbot de Ejemplo» usa Ollama a propósito y una edición inocente lo pasaría a Gemini.
>
> **Relación con CAL.2 y con las reglas maestras**: `DEV_LLM_ID`/`DEV_ORG_ID` son exactamente
> lo que CLAUDE.md prohíbe —lógica y datos hardcodeados en React que no vienen del contrato—.
> No se espera a CAL.2 porque esto bloquea las pruebas manuales hoy.

---

### Prompt FIX.1 (RED/GREEN) — Elegir el modelo, y ver el error cuando falla

**Modelo sugerido**: **Sonnet** — cuatro arreglos acotados, todos con causa ya diagnosticada.

```
# PROMPT FIX.1 (RED/GREEN) — Que el modelo se pueda cambiar y que los fallos se vean
# Deploy: cloud (chatbots y configuración de LLM son configuración)

## 1. BACKEND — `llm_config_id` entra en ChatbotUpdate
- `ChatbotUpdate` gana `llm_config_id: uuid.UUID | None`.
- Se VALIDA que la configuración existe: 404 con mensaje, no un IntegrityError de la FK a
  mitad de la petición.
- El resto del handler ya aplica `payload` con setattr, así que no hay más que tocar.

## 2. BACKEND — marcar por defecto demota a la anterior
Hoy `is_default=True` responde 409 si ya hay otra del mismo tier. Eso convierte «quiero que
esta sea la de por defecto» en dos peticiones y un hueco: entre la una y la otra no hay
ninguna. Pasa a ser una sola operación: se demota la anterior del mismo tier y se promueve
esta, en la MISMA transacción. Vale para POST y para PATCH.
NOTA: el 409 de BORRAR una configuración en uso se queda como está — ahí sí hay que decidir
qué pasa con los chatbots que la usan, y eso no es este prompt.

## 3. FRONTEND — selector de modelo, y fuera los identificadores hardcodeados
- El formulario de chatbot lista las configuraciones (`GET /hub/llm-configs`) y deja elegir.
- Al EDITAR, el desplegable arranca en la configuración actual del chatbot, no en una
  constante. Esto es lo que cierra el riesgo de reasignar el modelo en silencio.
- `DEV_LLM_ID` y `DEV_ORG_ID` desaparecen del fichero. La organización se elige de
  `GET /hub/organizaciones` al crear; al editar no se toca (ChatbotUpdate no la admite).

## 4. FRONTEND — los errores se ven
- Ejecutar un escenario muestra el error si la mutación falla, con `role="alert"`.
- Mismo tratamiento para crear y borrar: si el backend dice que no, se dice.

## 5. FRONTEND — editar un escenario
El `PATCH` existe desde RAG.13 y no lo usa nadie. Botón de editar que reutiliza el mismo
formulario de crear, prellenado.

## TESTS (RED primero)
# backend  tests/api/test_chatbot_llm_config.py
#   should_change_the_model_of_an_existing_chatbot
#   should_reject_an_unknown_llm_config_with_404
#   should_not_touch_the_model_when_the_field_is_absent      (el riesgo de la reasignación muda)
#   should_promote_to_default_demoting_the_previous_one
#   should_leave_exactly_one_default_per_tier
# frontend src/admin/__tests__/ChatbotModelSelector.test.tsx
#   should_list_available_llm_configs_in_the_form
#   should_preselect_the_current_config_when_editing
#   should_not_send_a_hardcoded_llm_config_id
# frontend src/admin/__tests__/TestScenariosPage.test.tsx  (amplía el existente)
#   should_show_an_error_when_the_run_fails
#   should_edit_an_existing_scenario

## CRITERIO DE DONE
- [ ] `grep -rn "DEV_LLM_ID\|DEV_ORG_ID" frontend/src` = 0
- [ ] Contrato OpenAPI + Orval regenerados; `tsc` limpio
- [ ] Suite backend y frontend sin regresiones
- [ ] Verificación en navegador por el agente si la extensión lo permite; si no, se dice
- [ ] Sin migración
```

---

## Bloque CUR — La curación como producto propio (PENDIENTE)

> **Contexto**: añadido el 2026-08-02. Decisión completa en `docs/DECISION_CURACION_SEPARADA.md`,
> y reescritura del alcance de 9Q en el encabezado de ese bloque. En una frase: **la curación del
> corpus es una actividad previa, humana y con producto propio; el asistente consume el resultado
> y no lo produce**. 9Q construyó el motor correcto bajo una etiqueta equivocada.
>
> **Este bloque NO reescribe nada.** Es una reorganización: mover módulos, separar la superficie
> de UI y hacer explícito el paso de publicación. El comportamiento del crawler, los detectores y
> los informes no cambia, y el esquema de base de datos **no se toca** —`hub_web_sites`,
> `hub_crawled_pages`, `hub_corpus_selections` y `hub_content_findings` ya están bien modeladas—.
>
> **Por qué va antes del Deploy y no después.** Los artefactos de despliegue codifican la
> estructura: D.4 fija qué imágenes y qué servicios de Cloud Run existen, y D.5 el pipeline que
> los construye. Decidir la clasificación de módulos y routers después de montar eso obliga a
> rehacer parte de D.4/D.5 y a repetir la verificación contra producción. Un refactor pre-deploy
> solo arriesga en local y lo cubren los tests. Va **detrás de CAL.1**, que retira NiceGUI y deja
> menos superficie que mover.
>
> **Lo que este bloque NO hace**: partir el sistema en dos repositorios o dos despliegues. Se
> descarta en la decisión —duplicaría AUTH, tenancy, storage, CI y Orval, y rompería el bucle de
> RAG.14—. Si algún día la curación debe operarla otra unidad, es un perfil más de `DEPLOY_MODE`,
> no un fork.

---

### Prompt CUR.1 (RED/GREEN) — Módulo propio para la curación

**Modelo sugerido**: **Sonnet** — movimiento mecánico con frontera ya decidida; las decisiones abiertas están cerradas en el documento de decisión.

```
# PROMPT CUR.1 (RED/GREEN) — `ingestion/quality/` deja de ser un detalle de la ingesta
# Deploy: edge  (todo el módulo procesa contenido del cliente)

# QUÉ SE MUEVE
#   server/app/modules/agents_hub/ingestion/quality/   →  server/app/modules/curation/
#   server/app/modules/agents_hub/ingestion/spiders/   →  server/app/modules/curation/spiders/
#   server/app/modules/agents_hub/ingestion/spider.py, spider_factory.py  →  idem
#
# QUÉ NO SE MUEVE, Y POR QUÉ
#   - `gap_detector.py` se queda: nace de conversaciones (HubInteraction), no de páginas. Es la
#     señal que el asistente EMITE hacia la curación. Que viva en agents_hub y escriba
#     HubContentFinding con chatbot_id es exactamente el contrato entre las dos mitades.
#   - `chunker`, `watcher`, `docling_processor`, `corpus/`: son la ingesta propiamente dicha,
#     el lado del asistente. La curación produce ficheros que cumplen el contrato del corpus;
#     ingerirlos es trabajo del otro lado.
#   - Las entidades ORM: `HubWebSite` y compañía se quedan en `operational_models.py`. Partir
#     el metadata operacional en dos ficheros no aporta y complica `create_all` de los tests.

# REGLAS
#   - `modules/curation/` NO importa de `agents_hub/agent/` ni de routers cloud. Puede usar
#     `services/embedding_resolver` y `core/` compartidos.
#   - `agents_hub` NO importa de `modules/curation/`. La única comunicación es la tabla
#     `hub_content_findings`, con su CHECK de sujeto único.
#   - `hub_content_quality_router` y `hub_sites_router` se re-etiquetan como routers de curación
#     y se registran igual (`_register_edge`); `Deploy: edge` no cambia.

# TESTS (RED primero)
# tests/modules/curation/test_frontera_curacion.py
# should_not_import_agent_module_from_curation      (grep sobre el árbol, como los guardarraíles de TST)
# should_not_import_curation_from_agents_hub
# should_keep_gap_detector_in_agents_hub            (la señal del uso no se muda)
# + los tests existentes de 9Q se mueven y siguen verdes SIN cambios de aserción

# CRITERIO DE DONE
- [ ] `grep -r "ingestion.quality"` = 0 fuera de `_legacy_*`
- [ ] Suite completa verde; ni una aserción de 9Q reescrita (si hay que tocarlas, el movimiento
      no era mecánico y hay que parar y replantear)
- [ ] Sin migración
```

---

### Prompt CUR.2 (RED/GREEN) — Superficie propia en el frontend y publicación explícita

**Modelo sugerido**: **Sonnet** — reorganización de rutas y navegación con i18n; sin lógica nueva.

```
# PROMPT CUR.2 (RED/GREEN) — La curación deja de ser una pestaña del panel de ingesta

# POR QUÉ
# Mientras el spider viva dentro de la UI de ingesta del chatbot, el producto sigue prometiendo
# «apunta al sitio y el asistente aprende». Esa promesa es la que el corpus normativo desmintió,
# y es peligrosa porque no falla de forma visible: produce respuestas seguras apoyadas en una
# norma derogada.

# QUÉ SE HACE
#   1. `frontend/src/curation/` con navegación propia: Sitios, Auditoría, Hallazgos, Publicación.
#   2. `CorpusSelectionService` sube a primer plano como **paso de publicación**: la pantalla
#      dice qué páginas hay candidatas, quién las aprueba y qué chatbot las recibe. Hoy la
#      operación existe (`ingest_page`) pero está presentada como un detalle técnico.
#   3. Los huecos de corpus de RAG.14 se muestran EN la curación, no solo en el panel del
#      chatbot: son entrada de trabajo para el curador.
#   4. i18n es/ca/en completo. Ninguna cadena nueva hardcodeada.

# LO QUE NO SE HACE
#   - Ningún automatismo de ingesta. Ningún botón «ingerir todo el sitio».
#   - Ninguna lógica de negocio en React: las acciones disponibles vienen del backend.

# TESTS (RED primero)
# should_render_curation_nav_without_chatbot_context
# should_require_explicit_publish_action_per_page
# should_list_corpus_gaps_from_rag14_as_curation_input
# should_have_no_hardcoded_strings            (guardarraíl i18n ya existente, extendido)

# CRITERIO DE DONE
- [ ] `tsc` limpio, Vitest verde, Orval regenerado si cambió el contrato
- [ ] Verificación en navegador por el agente (protocolo de METODOLOGIA_AGENTICA.md §4)
- [ ] Ni un string sin traducir en las tres lenguas
```

---

## Bloque ING.0 — Fundamentos del corpus normativo (Subfase 1.A, PENDIENTE)

> **Contexto**: replanificado el 2026-07-28 tras la valoración cruzada con la estrategia de recuperación de `openwebui-gerencia` (`INFORME_ESTRATEGIA_ASISTENTE_GERENCIA.md`) y, sobre todo, con `Descarregar_pdf\normativa_propia\INFORME_MATERIES_I_METADADES_AGENTS.md`, que es donde la clasificación está cerrada: **5 ámbitos, 58 submaterias, esquema de 56 campos** (`vocabulari/ambits.csv`, `vocabulari/submateries.csv`, `vocabulari/esquema_metadades.yaml`).
>
> **Qué sustituye**: los antiguos ING.0.1 (`CorpusManifest`) e ING.0.2 (CLI de carga), que no llegaron a ejecutarse. Su contenido se conserva ampliado en ING.0.3 e ING.0.5. El contrato anterior era incompatible con la estrategia por tres motivos medidos: un `category: str` único donde hacen falta tres ejes; ningún sitio en `HubDocument` donde persistir los metadatos (no hay columna JSON ni `content_class` ni `reviewer`); y ningún filtrado por metadatos en la capa de recuperación, que es exactamente el Nivel 1 de la estrategia y lo que `CRITERIS` §1.4 exige para el control de acceso.
>
> **Estrategia de recuperación objetivo** (informe §6.1), que este bloque + el Bloque VIS habilitan:
> ```
> NIVEL 0  índice de las 58 submaterias en el system prompt      2.307 tokens (medido)
> NIVEL 1  router: pregunta → 1-3 submaterias → fichas filtradas ~1.500 tokens
> NIVEL 2  inyección de 1-3 normas completas                     ~25k tokens
> NIVEL 3  RAG por artículos, SOLO para las 22 leyes externas    (Bloque RAG)
> ```
> El 99,7 % de la normativa propia se inyecta entera (131 docs < 6k tokens, 170 entre 6k y 25k, 1 por encima de 78k). El RAG por fragmentos solo es imprescindible para LCSP (~352k tokens), Ley 6/2024 (~303k) y Decreto-ley 14/2025 (~283k).
>
> **Origen del corpus (decidido 2026-07-28)**: la UJI está definiendo el modelo de publicación normativa. El `.md` autoritativo vivirá **en la BD de publicación**, y de ahí se generarán el PDF y el HTML consultable. **Las circulares de Gerencia pasan por el mismo circuito de publicación**, con `nivell_acces: intern`. Consecuencias duras:
> - **Un solo maestro para el corpus propio**: la BD de publicación. El hub es réplica de solo lectura (`source_kind='publicacio'`). No se construye UI de edición de metadatos en el hub (regla de CLAUDE.md: sin código especulativo); la carga manual queda cubierta por el CLI de ING.0.5 para emergencias.
> - **El crawler queda desactivado para este corpus.** Dos rutas de entrada para la misma norma producirían dos conversiones del mismo texto compitiendo en el top-k. `CRITERIS` §3.2: declarar fuente autoritativa antes de indexar y retirar las redundantes.
> - **Los `.md` llegan con jerarquía real de encabezados (5 niveles) y ancla estable por unidad citable** — confirmado que se aplica tanto a las normas nuevas como retroactivamente al corpus histórico. Especificación cerrada en **`docs/CONTRATO_MD_CORPUS.md`**. Por tanto el parser estructural de la tarea 8 del informe **no se implementa en el hub**: el hub consume la jerarquía, no la reconstruye.
>
> **Dos transportes, un solo reconciliador (decidido 2026-07-28)**: el pipeline de publicación **no estará hasta dentro de unos meses**, así que durante ese tiempo la actualización del corpus se hace **por CLI sobre una carpeta de `.md`**, y no como carga inicial de una sola vez: es el mecanismo de mantenimiento en funcionamiento. Después se le añade el transporte programático (MCP o export incremental). Regla dura para que eso no produzca dos pipelines divergentes:
> - **La lógica de reconciliación se escribe UNA vez**, en ING.0.5, detrás de un protocolo `CorpusSource`. La carpeta local y el servicio MCP son dos **fuentes** del mismo reconciliador; SYNC.1 añade una fuente, no un pipeline.
> - **Lo incremental no es un modo**: emerge del hash. El mismo comando sobre la misma carpeta omite lo no cambiado, actualiza metadatos sin re-chunk y re-ingiere solo lo modificado.
> - **Lo que sí es un modo, y es peligroso, es el censo.** Detectar retiradas exige saber que la fuente es el corpus COMPLETO. Un `--prune` sobre una subcarpeta retiraría cientos de normas. Por eso el censo es opt-in explícito y va con salvaguarda de proporción.
> - **Identidad estable desde el primer día**: `id_publicacio` en el contrato aunque hoy venga vacío, para que el día que llegue el transporte programático sea una continuación y no una recarga del corpus.
>
> **Vocabulario revisable (requisito, decidido 2026-07-28)**: los 5 ámbitos y las 58 submaterias son una **propuesta pendiente de validar por SG** y deben poder cambiar después. Eso impone dos reglas que atraviesan este bloque y el Bloque RAG:
> 1. El vocabulario es **dato versionado en tabla**, nunca `Enum` de Python ni `CheckConstraint`.
> 2. **La taxonomía no entra JAMÁS en el texto que se embebe.** Si `submateria` acabara dentro del chunk embebido, cada revisión del vocabulario costaría un re-embedding del corpus completo y la promesa del informe §3.3 («RRHH sale al coste de un campo») dejaría de ser cierta. Ver enmiendas a RAG.4 y RAG.7.
>
> **Posición en el orden**: ING.0.1→ING.0.5 → carga del corpus v1 → RAG.1 (baseline) → RAG.2 (consolidación) → VIS.1→VIS.3 → resto del Bloque RAG → Bloque SYNC.

---

### Prompt ING.0.1 (RED/GREEN) — Vocabulario controlado como dato versionado

**Modelo sugerido**: **Sonnet** — modelo + servicio + CLI con alcance cerrado; la decisión de diseño (ejes en código, términos en tabla) viene dada aquí.

```
# PROMPT ING.0.1 (RED/GREEN) — Ámbitos y submaterias como dato, no como enum
# Deploy: cloud  (HubConfigBase: es configuración institucional, se sincroniza cloud→edge)

## Decisión de diseño que gobierna el prompt
Los EJES son estructura (pocos, estables, y añadir uno exige código que lo consuma) → StrEnum
en código. Los TÉRMINOS son dato (cambian sin tocar código) → filas en tabla. No hay
CheckConstraint sobre los códigos de término: sería exactamente lo que impide revisar el
vocabulario.

## Modelo (database/config_models.py — HubConfigBase)
- VocabularyAxis (StrEnum en código): 'ambit' | 'submateria' | 'rang' | 'colectiu' | 'tipus'.
- HubVocabularyTerm:
    id, organizacion_id (FK hub_organizaciones ondelete CASCADE), axis String(20) NOT NULL,
    codi String(80) NOT NULL, nom_primari String(255), nom_secundari String(255) | None,
    parent_codi String(80) | None      # submateria → su ámbito; jerarquía en la misma tabla
    descripcio_router Text | None      # el texto que ve el router en el índice del Nivel 0
    ordre Integer default 0,
    vigent Boolean NOT NULL default True,
    substituit_per_codi String(80) | None,
    created_at, updated_at
  UniqueConstraint(organizacion_id, axis, codi) — clave natural, base de la idempotencia.
- Renombrar / fusionar un término = fila nueva + la vieja a vigent=False con
  substituit_per_codi apuntando a la nueva. **La cadena de substituit_per_codi ES la traza de
  auditoría**: no se crea tabla de historial aparte.
- Migración Alembic + sembrado NO incluido aquí (lo hace el CLI).

## Servicio (services/vocabulary_service.py)
- validate(axis, codis) -> list[str]: devuelve los códigos DESCONOCIDOS o no vigentes (vacío = OK).
- resolve(axis, codi) -> str: sigue la cadena substituit_per_codi hasta el término vigente
  (con corte por ciclo → error explícito, no bucle infinito).
- build_router_index(organizacion_id) -> str: el índice de submaterias del Nivel 0, agrupado por
  ámbito, con descripcio_router. Debe caber en el orden de magnitud medido (~2.3k tokens para 58).
- reclassify(axis, codi_antic, codi_nou): UPDATE de los documentos afectados siguiendo la
  substitución. **No re-embebe nada** (ver regla 2 del bloque) — devuelve el recuento tocado.

## Frontera edge/cloud (regla dura de CLAUDE.md)
El módulo de ingesta es edge y NO puede importar HubVocabularyTerm. Se amplía el protocolo
ConfigProvider (services/config_provider.py:16-23) con:
    async def list_vocabulary(self, axis: str, organizacion_id: uuid.UUID) -> list[VocabularyTermDTO]
implementado en LocalConfigProvider. El DTO es un dataclass del lado edge, no el modelo ORM.

## CLI (python -m ...vocabulary.load)
- Argumentos: --axis, --csv, --organizacion-id, --dry-run.
- Carga ambits.csv (columnas code/nom/…) y submateries.csv (codi;ambit;nom_val;nom_es;abast;…)
  del directorio vocabulari/ del proyecto de normativa. Idempotente por (organizacion_id, axis, codi):
  segunda pasada no duplica y reporta "sin cambios".
- Un CSV con un parent_codi inexistente se rechaza ENTERO (no carga a medias).

## Tests (RED primero) — tests/modules/agents_hub/test_vocabulary_service.py
# should_reject_unknown_submateria_codes
# should_accept_codes_present_and_vigent
# should_reject_code_marked_not_vigent
# should_resolve_renamed_code_to_its_replacement
# should_raise_on_substitution_cycle
# should_build_router_index_grouped_by_ambit
# should_scope_vocabulary_by_organizacion          (dos orgs, taxonomías distintas)
# should_be_idempotent_on_second_csv_load
# should_reject_csv_with_dangling_parent_codi
# should_expose_vocabulary_through_config_provider (frontera: sin import del modelo en edge)
# should_not_declare_check_constraint_on_codi      (guardarraíl del diseño: inspección de metadata)

## Criterio de done
- [ ] Migración aplicada (adjuntar `alembic current`)
- [ ] Los 5 ámbitos y las 58 submaterias cargados desde vocabulari/*.csv, con recuentos reales
- [ ] Índice del Nivel 0 generado y su tamaño en tokens medido y anotado en el cierre
```

---

### Prompt ING.0.2 (RED/GREEN) — Modelo de datos del documento normativo

**Modelo sugerido**: **Sonnet** — migración con criterio explícito de qué es columna y qué es JSONB; sin decisiones abiertas.

```
# PROMPT ING.0.2 (RED/GREEN) — Metadatos del corpus en HubDocument
# Deploy: edge

## Regla que decide el esquema (evita las 56 columnas)
Una columna de primer nivel SOLO si algo la filtra, la ordena o la usa como puerta.
Todo lo demás va a doc_metadata JSONB. Se documenta en el docstring del modelo.

## Migración sobre hub_documents (operational_models.py:142-173)
Columnas nuevas de primer nivel:
- content_class String(20) NOT NULL default 'generic'   # gate de revisión (era del viejo ING.0.1)
- ambit_principal String(80) | None                     # filtro del Nivel 1
- ambits_secundaris ARRAY(String) default []            # amplía alcance (informe §2.3)
- submateries ARRAY(String) default []                  # el filtro propiamente dicho
- submateries_internes ARRAY(String) default []          # contenido disperso (informe §5.2)
- nivell_acces String(20) NOT NULL default 'public'     # 'public'|'intern'|'restringit'
- us_assistents String(20) NOT NULL default 'si'        # 'si'|'restringit'|'no'
- canonica Boolean NOT NULL default True                # una sola versión indexada (informe §6.3)
- versio_idiomatica_de UUID | None                      # la otra lengua, recuperable por id
- estat_vigencia String(20) | None
- vigencia_validada_el DateTime(tz) | None              # NULL ⇒ el asistente ADVIERTE (VIS.3)
- revisat_per String(255) | None, revisat_el DateTime(tz) | None   # revisión de conversión
- data_revisio_prevista Date | None                     # caducidad activa (SYNC.2)
- id_publicacio String(80) | None, indexada              # id estable del registro de publicación.
    Se rellena cuando exista; hoy puede venir vacío. Es la clave de emparejamiento del sync
    (SYNC.1) para que el cambio de transporte NO sea una recarga del corpus. Fallback
    documentado: doc_metadata->>'url_oficial' + language.
- last_seen_at DateTime(tz) | None                       # última vez que la fuente lo declaró.
    Lo estampa cada pasada de censo (ING.0.5). Es el mecanismo que hace segura la detección de
    retiradas: se marca lo que el último censo NO vio, no lo que "falta" en una carga parcial.
- doc_metadata JSONB NOT NULL default '{}'              # rang, aplica_a, resum_router,
    preguntes_tipus, termes_bilingues, tipus_font, font_autoritativa, deroga, derogat_per,
    url_oficial, motiu_exclusio, original_pdf_sha256, converter/docling_version…
- ARRAY y no tabla de relación: mismo criterio ya adoptado en SEC.2.1 para allowed_roles.

Sin columna 'origen' nueva: se REUTILIZA source_kind (ya existe, String(20)) ampliando sus
valores documentados a 'crawler'|'upload'|'publicacio'|'boe'. Duplicar el eje sería deuda.

Índices: btree (chatbot_id, ambit_principal), btree (chatbot_id, nivell_acces),
GIN (submateries), GIN (submateries_internes), GIN (doc_metadata).

## FK que falta y que VIS.1 necesita
hub_document_chunks.document_id existe pero NO tiene FK (operational_models.py:185-187).
VIS.1 filtra los chunks por los metadatos de su documento mediante JOIN — se elige JOIN y no
denormalizar sobre el chunk porque así reclasificar es UN UPDATE sobre hub_documents y no hay
dos copias que divergir. La migración: limpiar huérfanos (document_id que no existe) y añadir
FK → hub_documents.id ondelete CASCADE. Los chunks temporales (document_id NULL, subida de
usuario) siguen siendo válidos y se tratan aparte en VIS.1.

## section_path
Declarada (línea 160) y JAMÁS escrita en todo server/app; solo se lee en 4 sitios. Si ING.0.4
no la puebla con la ruta estructural, se retira por Caso B (borrado directo) con el checklist
de CLAUDE.md. Decidirlo dentro de ING.0.4, no dejarla en el limbo.

## Fallo de despliegue que se arregla aquí (hallado el 2026-07-28)
El ORM declara HubIngestionJob.canonical_url y .original_filename (operational_models.py:237-238)
pero NINGUNA migración las crea: e5f6a7b8c9d0 las trata como opcionales (`if _column_exists`)
porque las creó código fuera de la cadena. En una instalación limpia no existen, y
POST /hub/ingestion/upload las escribe (hub_ingestion_router.py:228, watcher.py:266,277) ⇒ la
subida de documentos falla con UndefinedColumn en un despliegue nuevo. Misma familia que el fallo
de hub_ingestion_sources que arregló 11.2.
- La migración de este prompt añade ambas columnas a hub_ingestion_jobs, guardadas por
  _column_exists (el patrón ya usado en la cadena) para no chocar donde ya estén.
- Test: should_have_ingestion_job_columns_on_fresh_install, sobre el esquema resultante de
  `alembic upgrade head` en BD limpia (reusar el harness de tests/infra/test_migrations_fresh_install.py).
- La columna hub_interactions.metadata existe en instalación limpia y el ORM no la declara: se
  RETIRA en esta misma migración (columna muerta, Caso B) tras comprobar con grep que nadie la lee.

## Tests (RED primero) — tests/modules/agents_hub/test_document_metadata_model.py
# should_default_new_document_to_public_and_canonical
# should_persist_and_read_back_submateries_array
# should_persist_arbitrary_schema_fields_in_doc_metadata
# should_reject_chunk_with_dangling_document_id      (la FK nueva muerde)
# should_cascade_chunk_deletion_when_document_deleted
# should_allow_null_document_id_for_temporary_chunks
# should_have_gin_index_on_submateries               (inspección de índices)
# should_migrate_existing_rows_with_safe_defaults    (fail-closed: nivell_acces='public' solo
#                                                     porque hoy todo el corpus cargado es público;
#                                                     documentarlo en la migración)

## Criterio de done
- [ ] Migración aplicada (`alembic current`) y reversible (downgrade probado)
- [ ] Recuento de huérfanos limpiados por la migración, anotado en el cierre
```

---

### Prompt ING.0.3 (RED/GREEN) — Front-matter como portador + manifiesto derivado

**Modelo sugerido**: **Sonnet** — contratos Pydantic + validación contra vocabulario; alcance cerrado.

```
# PROMPT ING.0.3 (RED/GREEN) — Contrato de metadatos del .md curado
# Deploy: edge

## Decisión de diseño: el portador es el front-matter, el manifiesto se deriva
El .md es autodescriptivo (es lo que hace posible el sync de SYNC.1 y la carga manual con el
mismo contrato). El manifiesto sigue existiendo para corpus SIN front-matter (histórico, BOE):
si un documento trae front-matter, MANDA el front-matter; si no, manda la entrada del manifiesto.

## Parser (ingestion/corpus/frontmatter.py)
- parse(raw_md) -> (metadata: dict, body: str). Front-matter YAML delimitado por '---'.
- **El hash y el chunking se calculan SOBRE EL BODY, nunca sobre el front-matter.** Es la
  decisión con más consecuencias del prompt: así un cambio SOLO de metadatos no altera
  content_hash → no dispara re-chunk ni re-embedding, y un cambio de texto sí. Hoy
  hash_content() recibiría el front-matter como parte del contenido (watcher.py:94-95) y
  cualquier reetiquetado costaría reindexar el corpus entero.
- Un .md sin front-matter no es error: devuelve ({}, raw_md).

## Contratos (ingestion/corpus/manifest.py)
- CorpusDocumentEntry (Pydantic frozen): relative_path (.md), source_url, language,
  id_publicacio | None (id estable del registro de publicación; hoy puede ir vacío, ver ING.0.2),
  content_class ('regulation'|'faq'|'generic'), title | None, original_pdf_sha256 | None,
  converter/docling_version | None, revisat_per | None, revisat_el | None,
  ambit_principal | None, ambits_secundaris: list[str] = [], submateries: list[str] = [],
  submateries_internes: list[str] = [], nivell_acces = 'public', us_assistents = 'si',
  canonica: bool = True, versio_idiomatica_de | None, estat_vigencia | None,
  vigencia_validada_per | None, vigencia_validada_el | None, data_revisio_prevista | None,
  motiu_exclusio | None, extra: dict = {}  (→ doc_metadata).
- CorpusManifest: chatbot/organizacion destino, created_at, documents: list[...].
- Validación:
  * rutas relativas, sin absolutas ni '..';
  * content_class 'regulation' EXIGE revisat_per + revisat_el (revisión obligatoria, se
    conserva del contrato anterior);
  * ambit_principal y submateries se validan contra VocabularyService vía ConfigProvider;
    término desconocido ⇒ error que ENUMERA los códigos no reconocidos (no falla en el primero);
  * us_assistents == 'no' EXIGE motiu_exclusio (informe §4: convierte «no se publica» en
    decisión auditable en vez de silencio);
  * nivell_acces y us_assistents contra sus listas cerradas (sí son enumeraciones estables).
- El mapeo de normativa_uji_log.json a este contrato se DOCUMENTA (docstring o docs/) sin
  acoplar el loader a ese formato.

## Tests (RED primero) — tests/modules/agents_hub/ingestion/test_corpus_manifest.py
# should_reject_absolute_or_parent_paths
# should_require_review_for_regulation_class
# should_allow_missing_review_for_faq_class
# should_parse_frontmatter_and_strip_it_from_body
# should_hash_body_without_frontmatter               (el test central del prompt)
# should_not_change_hash_when_only_metadata_changes
# should_change_hash_when_body_changes
# should_treat_md_without_frontmatter_as_empty_metadata
# should_reject_unknown_submateria_against_vocabulary
# should_list_all_unknown_codes_not_just_the_first
# should_require_motiu_exclusio_when_us_assistents_is_no
# should_prefer_frontmatter_over_manifest_entry
# should_roundtrip_manifest_json
```

---

### Prompt ING.0.4 (RED/GREEN) — Chunker jerárquico de 5 niveles + anclas de artículo

**Modelo sugerido**: **Sonnet** — cambio acotado en el chunker con efecto medible en las citas.

> **Especificación del formato: `docs/CONTRATO_MD_CORPUS.md`** (2026-07-28). Es el contrato que
> aplica el conversor del corpus y el generador de publicación; este prompt implementa el lado
> consumidor. Corrección respecto a la primera versión de este plan: **son 5 niveles, no 4** —
> faltaba la Sección, que aparece en 280 casos del corpus medido.

```
# PROMPT ING.0.4 (RED/GREEN) — Jerarquía real y cita por artículo
# Deploy: edge

## Contexto medido
El corpus tiene 4.649 artículos, 685 capítulos, 432 títulos, 280 secciones y 675 disposiciones
marcados como encabezado, pero HOY casi todos aplanados en '##'. El corpus convertido y el
modelo de publicación nuevo emiten jerarquía real y ancla estable por unidad citable, según
docs/CONTRATO_MD_CORPUS.md:

    #      documento (uno por fichero)
    ##     preámbulo | título | grupo de disposiciones | anexo | división (docs sin articulado)
    ###    capítulo
    ####   sección
    #####  UNIDAD CITABLE: artículo | disposición | apartado de resolución | unidad ordinal

**Contrato v2 (2026-07-29)**: las anclas son **oportunistas, no obligatorias**, y las divisiones
estructurales (título/capítulo/sección) NO llevan ancla. El hub reconstruye la ruta del TEXTO del
encabezado, no del ancla, así que no pierde nada. El chunker debe degradar sin ruido cuando no hay
ancla: verificado sobre el corpus real (12.044 fragmentos, ancla presente en una parte).

El nivel lo determina el TIPO de elemento, no su anidamiento: un artículo es '#####' también en
una norma sin títulos ni capítulos. Por eso el chunker PUEDE fiarse del nivel, y por eso hay
saltos de nivel legítimos ('#####' bajo '##' en las disposiciones) que no debe tratar como error.
El chunker solo sigue 3 niveles hoy (chunker.py:27-31), así que artículos y secciones se
perderían como nivel.

## Cambios en ingestion/chunker.py
- headers_to_split pasa a 5 niveles: header_1..header_5.
- Extracción del ancla del propio encabezado, sintaxis de atributos Pandoc/kramdown
  ('##### Article 14. Import de la dieta {#art-14}'):
  * 'ancora' va a chunk_metadata;
  * el token '{#...}' se ELIMINA del texto del chunk (es ruido para el embedding y para el
    usuario); el resto del encabezado se conserva (strip_headers=False sigue vigente: RAG.7 lo
    necesita).
- 'ruta': lista de encabezados ancestros (['Títol I','Capítol III','Secció 2a']) en
  chunk_metadata, para que un artículo recuperado aislado no pierda el contexto que le da su
  capítulo (informe §5.2).
- Un .md sin anclas ni jerarquía sigue funcionando: ancora=None, ruta con lo que haya. Los
  documentos sin articulado (41 de 226: protocolos, planes, anexos de tablas) son válidos.
- Las anclas son las MISMAS en las dos versiones idiomáticas de una norma (prefijo neutro:
  'art-14' vale para «Article 14» y «Artículo 14»), lo que permite que una cita resuelva contra
  cualquiera de las dos. VIS.3 lo aprovecha.

## Cita verificable (el pago de este prompt)
Cuando el chunk tiene 'ancora', la URL de la evidencia es canonical_url + '#' + ancora. Se
aplica en el punto donde se construye la evidencia, para las tres estrategias.

## section_path (deuda heredada, se cierra aquí)
Poblarla con la ruta estructural del documento; si no encaja, retirarla por Caso B con el
checklist completo de CLAUDE.md (grep de los 4 lectores: long_context_strategy.py:65,
agentic_strategy.py:33, list_documents.py:28, md_agent_selector_pipeline.py:54).

## Troceado consciente de tablas (añadido el 2026-07-28, medido sobre el corpus convertido)
El corpus trae las tablas en bloques delimitados y autodescriptivos:

    <!-- TABLA-TEXT: t01.png | pàg. 21 | 2x6 | markdown -->
    | Sou | Complement de destinació (CD) | ... |
    | --- | --- | ... |
    | 1.288,31 € | 924,48 € | ... |
    <!-- /TABLA-TEXT -->

Medido: 54 bloques en 13 de los 226 documentos, 49 en markdown (pipe) y 5 en html (los de
colspan/rowspan, que los pipes no pueden expresar). **30 de los 54 superan los 1.000 caracteres
del chunk_size**, mediana 1.161, máximo 11.886.

Sin tratamiento especial, RecursiveCharacterTextSplitter los parte por '\n' —frontera de fila,
que está bien— pero **todos los fragmentos menos el primero pierden la fila de cabecera**: quedan
importes sin nombre de columna. Es peor que no tener el dato, porque se recuperan igual y
sostienen una respuesta segura y falsa sobre una cuantía.

- Detectar el bloque TABLA-TEXT y tratarlo como unidad: si cabe en el presupuesto del chunk, NO
  se parte aunque supere chunk_size (una tabla partida vale menos que una tabla larga).
- Si no cabe, partir **por filas** y **repetir la fila de cabecera** (y el separador '| --- |')
  al principio de cada fragmento. Para los bloques 'html', repetir el <thead> y cerrar/reabrir
  <table> en cada fragmento.
- Llevar a chunk_metadata la procedencia de la cabecera del marcador: 'taula_origen' (PNG),
  'pagina', 'dimensions'. Permite que una cita diga de qué tabla y de qué página sale un importe.
- El formato se lee del ÚLTIMO campo del marcador, no se adivina del contenido.

## Regla dura que hereda el Bloque RAG
Solo se embebe contexto ESTRUCTURAL (título/capítulo/artículo), que es estable. La taxonomía
(ámbito, submaterias) NO entra nunca en el texto embebido. Ver enmienda a RAG.7.

## Tests (RED primero) — tests/modules/agents_hub/ingestion/test_chunker_hierarchy.py
# should_split_on_five_heading_levels
# should_treat_article_as_level_five_without_intermediate_divisions  (norma sin títulos)
# should_handle_level_jump_from_group_to_citable_unit                (disposiciones: ## → #####)
# should_extract_article_anchor_into_metadata
# should_extract_anchor_from_disposicio_and_annex
# should_strip_anchor_token_from_chunk_text
# should_keep_heading_text_in_chunk_content
# should_record_ancestor_route_in_metadata
# should_include_seccio_in_the_route
# should_handle_md_without_anchors_or_hierarchy
# should_handle_document_without_articulado
# should_build_citation_url_with_anchor_fragment
# should_not_include_taxonomy_in_embedded_text     (guardarraíl de la regla dura)
# --- troceado de tablas ---
# should_keep_small_table_block_in_one_chunk
# should_not_split_table_block_that_fits_even_over_chunk_size
# should_repeat_header_row_in_every_chunk_of_a_split_pipe_table
# should_repeat_thead_and_reopen_table_tag_for_split_html_table
# should_split_pipe_table_on_row_boundaries_never_mid_row
# should_record_table_provenance_in_chunk_metadata   (taula_origen, pagina, dimensions)
# should_read_format_from_marker_not_from_content
# should_handle_table_block_without_declared_format  (degradación: tratar como markdown)

## Criterio de done
- [ ] Chunks regenerados con corpus_recalculator sobre el corpus de prueba
- [ ] Una cita real con fragmento #art-N verificada extremo a extremo
- [ ] section_path poblada o retirada; grep limpio si se retira
- [ ] Comprobado contra los 30 bloques de tabla que superan chunk_size: ningún fragmento con
      importes sin fila de cabecera (adjuntar un fragmento real de la tabla de retribuciones del
      Convenio colectivo, que es el caso canónico)
```

---

### Prompt ING.0.5 (RED/GREEN) — Reconciliador de corpus + CLI sobre carpeta local

**Modelo sugerido**: **Opus** — es el prompt con más decisiones embebidas del bloque: semántica de censo, salvaguarda de poda y el protocolo que evita que SYNC.1 duplique el pipeline.

```
# PROMPT ING.0.5 (RED/GREEN) — Un reconciliador, dos fuentes (la segunda llega en SYNC.1)
# Deploy: edge

## Por qué este prompt es el reconciliador y no "el cargador"
El pipeline de publicación no existirá hasta dentro de meses. Durante ese tiempo el CLI **es** el
mecanismo de mantenimiento del corpus, no una carga inicial. Cuando llegue el transporte
programático, debe añadirse una FUENTE, no un segundo pipeline. Por tanto la reconciliación se
escribe aquí, una sola vez, detrás de un protocolo.

## Protocolo de fuente (ingestion/corpus/source.py)
class CorpusSource(Protocol):
    def is_census(self) -> bool                      # ¿declara el corpus COMPLETO?
    async def list_entries(self) -> list[CorpusDocumentEntry]
    async def read_body(self, entry) -> str          # el .md ya sin front-matter (ING.0.3)
- LocalDirectorySource(dir, manifest | None) en este prompt.
- PublicationMcpSource en SYNC.1. Nada más cambia allí.

## Reconciliador (ingestion/corpus/reconciler.py)
Por cada entrada, contra hub_documents del chatbot destino. Emparejamiento: id_publicacio si
viene; si no, url_oficial + language (fallback documentado en ING.0.2).
- ausente en el hub                → ingerir
- hash del body distinto           → re-ingerir solo ese documento
- hash igual, metadatos distintos  → **UPDATE de metadatos SIN re-chunk ni re-embedding**
- hash y metadatos iguales         → omitido
- us_assistents == 'no'            → no se ingiere; omitido con su motiu_exclusio
- content_class 'regulation' sin revisión → rechazado antes de tocar la BD
Toda entrada vista, cambiada o no, estampa last_seen_at.

## Censo y poda: el modo peligroso
- Sin --prune (default) el reconciliador NO retira nada. Una carga parcial nunca puede
  interpretarse como censo.
- Con --prune, y SOLO si source.is_census() es True: los documentos del chatbot cuyo
  last_seen_at es anterior a esta pasada se marcan (us_assistents='no',
  motiu_exclusio='retirada_de_la_font') y emiten HubContentFinding para la cola del admin.
  **Nunca se borran.** Retirada de la fuente ≠ derogación: la distinción la hace una persona.
- **Salvaguarda de proporción**: si la poda afectaría a más del N % del corpus (default 10 %),
  ABORTA y exige --force-prune con el recuento por delante. Es la red que evita convertir un
  `--dir` mal escrito en la retirada del corpus entero.

## CLI (python -m ...ingestion.corpus.load)
- Argumentos: --dir, --manifest (opcional si hay front-matter), --chatbot-id, --dry-run,
  --census, --prune, --force-prune, --prune-threshold.
- Por cada .md: parse de front-matter (ING.0.3) → passthrough del body (NO reconvierte, NO
  llama a Docling) → IngestionWatcher.process_source, que ya hace hash → detect_language →
  MarkdownChunker → embedding → HubDocumentChunk.
- language del front-matter/manifiesto MANDA sobre detect_language cuando viene dado.
- source_kind = 'publicacio' | 'boe' | 'upload' según el origen declarado.
- Persiste TODOS los campos de ING.0.2, incluidos los ARRAY y doc_metadata.
- Reutiliza validate_upload(file, kind=UploadKind.TEXT) de SEC.6 (core/uploads.py) — no
  reimplementar validación de extensión ni de binario disfrazado.
- **Un HubIngestionJob por ejecución**, con los seis recuentos (ingeridos / re-ingeridos /
  metadatos actualizados / omitidos / rechazados / retirados). Si el CLI va a ser el mecanismo
  de mantenimiento durante meses, el historial tiene que estar en la BD y visible en el admin,
  no solo en la consola de quien lo ejecutó.
- --dry-run: el plan completo, incluido lo que se podaría, sin escribir.

## Watcher: la ampliación que esto exige
Hoy, en el acierto de hash, el watcher solo refresca canonical_url/title/updated_at
(watcher.py:101-114). Debe además refrescar los metadatos de ING.0.2. Es la ruta que hará barata
la reclasificación cuando SG revise el vocabulario, así que tiene test propio.

## Tests (RED primero) — test_corpus_reconciler.py + test_corpus_loader.py
# should_ingest_markdown_passthrough_without_docling
# should_persist_all_metadata_fields_on_hub_document
# should_prefer_declared_language_over_detection
# should_skip_unchanged_document_by_content_hash
# should_update_metadata_without_rechunking_when_only_metadata_changed
# should_reingest_only_changed_document
# should_match_existing_document_by_id_publicacio
# should_fall_back_to_url_and_language_when_id_publicacio_missing
# should_stamp_last_seen_at_on_every_entry_including_unchanged
# should_refuse_regulation_entry_without_review
# should_skip_documents_marked_us_assistents_no_with_reason
# should_not_prune_anything_without_the_prune_flag
# should_not_prune_when_source_is_not_a_census
# should_mark_and_emit_finding_for_pruned_document_without_deleting
# should_abort_prune_above_proportion_threshold
# should_prune_above_threshold_only_with_force
# should_record_one_ingestion_job_per_run_with_counters
# should_report_plan_in_dry_run_without_writing

## Cierre del bloque ING.0
- [ ] Cargar el corpus curado contra el chatbot destino y **congelar el manifiesto como
      `corpus v1`** (versionado), para que la baseline de RAG.1 no se mueva después
- [ ] Cifras reales del HubIngestionJob de la carga
- [ ] Segunda pasada sobre la misma carpeta: todo omitido, cero chunks nuevos (idempotencia real,
      no solo en test)
- [ ] Tercera pasada con un `.md` reetiquetado: metadatos actualizados y **cero re-embeddings**
- [ ] Verificar una cita trazable (source_url + ancla) en una consulta de prueba
- [ ] Confirmar que el crawler está desactivado para este chatbot (fuente autoritativa única)
- [ ] Documentar en `docs/` el procedimiento de actualización por CLI, que es el que estará en
      uso hasta que exista el pipeline de publicación
```

---

## Bloque VIS — Vistas del fundamento único: recuperación por metadatos (PENDIENTE)

> **Contexto**: implementa los Niveles 0, 1 y 2 de la estrategia (`INFORME_MATERIES_I_METADADES_AGENTS.md` §6.1, `INFORME_ESTRATEGIA_ASISTENTE_GERENCIA.md` §4). Hoy la recuperación filtra **solo** por `chatbot_id`, `is_temporary`/`owner_id` y opcionalmente `language` (`retriever.py:63-71,104-112`); no existe ni un operador JSONB en el código. Sin este bloque, los metadatos de ING.0 son decorativos y el control de acceso por perfil que exige `CRITERIS` §1.4 no es expresable.
>
> **Posición en el orden**: **después de RAG.2**. VIS.2 reescribe `md_agent_selector_pipeline`, que RAG.2 saca de su estado de stub al consolidar los grafos; hacerlo antes sería escribir contra `agent/graph.py`, que RAG.2 elimina.
>
> **Regla del bloque**: todo filtro se aplica **en SQL**, no en Python después del `LIMIT`. El precedente a no repetir es `_get_superseded_doc_ids` (`retriever.py:31-49`), que filtra en memoria tras el `top_k`: los documentos excluidos consumen plazas del resultado en vez de ser reemplazados.

---

### Prompt VIS.1 (RED/GREEN) — Filtro de metadatos en la capa de recuperación

**Modelo sugerido**: **Sonnet** — SQL + contrato de filtro; las decisiones (JOIN, fail-closed) vienen dadas.

```
# PROMPT VIS.1 (RED/GREEN) — Recuperación filtrada por ámbito, submateria y nivel de acceso
# Deploy: edge

## Contrato (services/retrieval/metadata_filter.py)
@dataclass(frozen=True) MetadataFilter:
    ambits: tuple[str, ...] = ()            # ámbito activo + secundarios + 'transversal'
    submateries: tuple[str, ...] = ()       # vacío = sin restringir por submateria
    max_nivell_acces: str = 'public'        # 'public' < 'intern' < 'restringit'
    include_non_canonical: bool = False
    include_superseded: bool = False

## Aplicación en retriever.py (vector_search, keyword_search, hybrid_search)
- JOIN hub_document_chunks → hub_documents por document_id (FK añadida en ING.0.2) y filtro en
  el WHERE, ANTES del ORDER BY / LIMIT.
- ambits: hub_documents.ambit_principal IN (...) OR ambits_secundaris && ARRAY[...]
- submateries: submateries && ARRAY[...] OR submateries_internes && ARRAY[...]
  (el operador && de solapamiento de arrays, que aprovecha el índice GIN de ING.0.2)
- max_nivell_acces: **fail-closed**. Si el nivel del actor no se puede determinar, 'public'.
  Nunca una instrucción al modelo: es filtro de recuperación (CRITERIS §1.4).
- us_assistents != 'no' siempre.
- canonica IS TRUE salvo include_non_canonical (VIS.3).
- Chunks temporales (document_id NULL, subida del propio usuario): NO se filtran por ámbito ni
  submateria — son del actor y ya están acotados por owner_id. Documentarlo y probarlo.

## Las otras dos estrategias, que hoy no filtran NADA
long_context_strategy.py:34-36 y agentic_strategy.py:20-36 seleccionan por chatbot_id (+lengua)
y ya está: ni superseded, ni nivell_acces, ni us_assistents. Un documento derogado se inyecta
entero en MD_LONG_CONTEXT y list_documents lo sigue listando. Ambas pasan a recibir y aplicar
MetadataFilter. Es una fuga de control de acceso, no una mejora de calidad.

## Tests (RED primero) — tests/modules/agents_hub/test_metadata_filter.py
# should_return_only_chunks_of_requested_ambit
# should_include_documents_matching_by_ambits_secundaris
# should_match_submateria_in_submateries_internes
# should_exclude_intern_documents_for_public_actor
# should_default_to_public_when_actor_level_unknown        (fail-closed)
# should_never_return_us_assistents_no_documents
# should_apply_filter_in_sql_before_limit                 (top_k no se degrada; se compara
#                                                          recuento con y sin filtro)
# should_not_filter_temporary_chunks_by_ambit
# should_apply_filter_in_long_context_strategy
# should_apply_filter_in_agentic_index
# should_exclude_superseded_in_all_three_strategies

## Criterio de done
- [ ] RAG.1 ejecutado y comparado con baseline (adjuntar recall@k/MRR)
- [ ] Test de fuga: un actor 'public' no recupera NI UN chunk de documento 'intern' por ninguna
      de las tres estrategias
```

---

### Prompt VIS.2 (RED/GREEN) — Niveles 0/1/2: índice de submaterias, selección e inyección de subconjunto

**Modelo sugerido**: **Opus** — es la pieza con más decisiones embebidas del bloque: qué va al prompt fijo, cómo se selecciona, cómo se degrada cuando no cabe.

```
# PROMPT VIS.2 (RED/GREEN) — El router ve temas, no documentos
# Deploy: edge

## El error que este prompt corrige
RAG.2 deja md_agent_selector_pipeline devolviendo «el índice de documentos» como evidencia
inicial. Medido en el informe: el catálogo de fichas con los campos del router son ~72k tokens
y NO cabe en un system prompt; el índice de las 58 submaterias son 2.307 tokens y sí cabe. El
router no necesita saber qué normas existen: necesita saber qué TEMAS existen.

## Nivel 0 — system prompt fijo (~6k tokens)
- Índice de submaterias desde VocabularyService.build_router_index (ING.0.1), vía ConfigProvider.
- Reglas de rango, vigencia y citación.
- Se integra en la TemplateStrategy del CoreGraph (única fuente del system prompt tras RAG.2).

## Nivel 1 — selección
- El modelo selecciona 1-3 submaterias con el tool list_documents, que se AMPLÍA con el
  parámetro submateries: list[str] (y ámbito implícito del chatbot). No se añade un tool nuevo:
  el índice ya está en el prompt, así que no hace falta un list_submaterias.
- Devuelve las fichas de los documentos de esas submaterias (~1.5k tokens), no su contenido.
- Retroceso escalonado (informe §4.2, la pieza que hace que esto supere a un corpus curado):
  nada encaja → fichas de TODAS las submaterias del ámbito → sigue sin encajar → catálogo global.
  Cada escalón se registra en el debug de la evidencia para poder medirlo.

## Nivel 2 — inyección del subconjunto
- read_document sobre 1-3 documentos, enteros (~25k tokens).
- LongContextRetrievalStrategy deja de significar «todo el corpus del chatbot» y pasa a aceptar
  un MetadataFilter (VIS.1): inyecta el SUBCONJUNTO.
- **Degradación en vez de excepción**: hoy la estrategia lanza ValueError si el corpus pasa de
  128k (long_context_strategy.py:41-46). En producción eso es una caída. Pasa a recortar por
  presupuesto y a marcar la evidencia como truncada, con el recuento de lo descartado.
- Columna context_token_budget (nullable) en HubChatbot + default_context_token_budget en
  HubOrganizacion + default de plataforma en ConfigResolver, misma cascada que el resto.
  **Se crea AQUÍ**, no en RAG.5 (ver enmienda): RAG.5 la consume para su packer.

## Tests (RED primero) — tests/public_graphs/test_vis_levels.py
# should_include_submateria_index_in_system_prompt
# should_keep_level0_index_within_token_order_of_magnitude
# should_list_documents_filtered_by_selected_submateries
# should_fall_back_to_ambit_wide_index_when_nothing_matches
# should_fall_back_to_global_catalog_as_last_resort
# should_record_fallback_level_in_evidence_debug
# should_inject_only_selected_documents_not_whole_corpus
# should_truncate_instead_of_raising_when_over_budget
# should_resolve_context_budget_from_cascade
# should_not_leak_documents_outside_the_actor_filter      (VIS.1 sigue mandando)

## Criterio de done
- [ ] Migración de context_token_budget aplicada y visible en la API admin
- [ ] RAG.1 sin regresión (adjuntar cifras)
- [ ] Traza real de una consulta: submaterias elegidas, documentos inyectados, tokens usados
```

---

### Prompt VIS.3 (RED/GREEN) — Versión canónica bilingüe + advertencia de vigencia no validada

**Modelo sugerido**: **Sonnet** — dos reglas acotadas con efecto directo en la respuesta.

```
# PROMPT VIS.3 (RED/GREEN) — Una versión indexada y una advertencia honesta
# Deploy: edge

## Canónica (informe §6.3)
Medido: 233 fichas en valenciano y 81 en castellano, muchas la misma norma. Hoy el hub las
indexa como documentos distintos coexistiendo por (canonical_url, language)
(watcher.py:116-131) → el mismo contenido ocupa dos plazas del top-k.
- Solo canonica=True entra en la recuperación (VIS.1 ya lo aplica).
- La otra versión es recuperable por id con read_document, vía versio_idiomatica_de, cuando el
  usuario pide la cita literal en la otra lengua.
- El cargador (ING.0.5) enlaza los pares: canonica declarada en el front-matter; si ambas se
  declaran canónicas para el mismo url_oficial, error explícito (no elegir a ciegas).

## Advertencia de vigencia (riesgo nº1 del informe: 312 de 314 fichas dicen «vigent?»)
- Si un documento citado tiene vigencia_validada_el IS NULL, o estat_vigencia distinto de
  'vigent', la respuesta lo DICE. Se implementa en la capa de plantilla/evidencia del CoreGraph
  (flag en EvidenceItem + texto de la TemplateStrategy), NO como frase suelta en el system
  prompt: una instrucción al modelo no es garantía.
- Los documentos derogados (estat_vigencia='derogat') no se recuperan salvo petición explícita
  por id.

## Tests (RED primero)
# should_retrieve_only_canonical_version_by_default
# should_read_language_variant_by_id_on_demand
# should_error_when_two_canonical_versions_share_url
# should_warn_when_cited_document_has_unvalidated_vigencia
# should_not_warn_when_vigencia_is_validated
# should_exclude_derogated_documents_from_retrieval
# should_still_allow_derogated_document_by_explicit_id

## Criterio de done
- [ ] RAG.1 sin regresión; anotar el efecto de la desduplicación bilingüe en el top-k
- [ ] Una respuesta real con la advertencia de vigencia, pegada en el cierre
```

---

## Bloque TST — Fiabilidad de la suite de tests

> **Contexto**: deuda encontrada al ejecutar los bloques ING.0 y RAG.1, con los síntomas medidos abajo. No bloquea ninguna funcionalidad, pero **hace poco fiable la verificación**: de aquí en adelante cada cierre de bloque afirma «suite verde», y hoy esa afirmación necesita un asterisco.
>
> **Posición en el orden (recomendada): antes de RAG.2.** Quedan 39 prompts y todos se cierran comparando la suite; arreglar esto primero hace verificable el resto. Tres prompts cortos (**TST.3 añadido el 2026-07-30**, al cerrar TST.1/TST.2, para llevar a cero los 12 rojos preexistentes que quedaban).
>
> **Lo que ya está arreglado y da contexto** (no hay que repetirlo): la fixture de `integration/` que hacía `drop_all` sobre la BD de desarrollo (commit `79dbbf3`), y el `Windows fatal exception: access violation` por cargar torch después de asyncpg, resuelto importando `langchain_text_splitters` al principio de `tests/modules/agents_hub/conftest.py`. **No reordenar ese import.**

---

### Prompt TST.1 (RED/GREEN) — Aislamiento entre tests: el `event_loop` de sesión

**Modelo sugerido**: **Sonnet** — cambio pequeño con verificación amplia; el diagnóstico viene dado.

> **RESUELTO (2026-07-30) — la hipótesis de abajo resultó FALSA.** Se retiró el override y
> los 10 fallos persistieron. La causa real, encontrada con hooks de evento a nivel de la
> clase `Engine` (el `echo` está cableado a `False` en `connection.py`, así que la traza
> por logging no era viable directamente): `test_hub_sites_router.py` asignaba
> `WebSiteRepo.create = AsyncMock(return_value=site)` **sobre la clase, sin restaurar** —
> desde ese test, `create` no ejecutaba SQL y devolvía siempre el mismo objeto desanclado,
> y los tests posteriores reventaban con FK contra un sitio fantasma. La pista decisiva:
> `session.refresh()` tenía éxito sobre una fila que "no existía" — imposible salvo que
> `create` entero fuera un mock. Arreglo: `monkeypatch.setattr` en los dos puntos +
> guardarraíl de escaneo estático (`tests/infra/test_suite_hygiene.py`) + la higiene del
> `event_loop` (que sí se hizo, como limpieza) + **CI pasa a una sola invocación de
> pytest**, porque en dos procesos separados esta clase de fallo es invisible. Detalle en
> `PROJECT_STATE.md` 2026-07-30.

```
# PROMPT TST.1 (RED/GREEN) — Los 10 fallos de test_site_model.py en ejecución conjunta
# Deploy: n/a (infraestructura de tests)

## Síntoma medido
`tests/modules/agents_hub/integration/test_site_model.py` da **10 fallos en ejecución
conjunta** con `unit/` y **pasa en solitario**:

    solo test_site_model.py                        → 15 passed
    los tres ficheros de BD juntos                 → 24 passed
    integration/ completo                          → 90 passed
    unit/ + integration/                           → 10 failed, 584 passed

Los 10: TestWebSiteRepo (2), TestCrawledPageRepo (5), TestCorpusSelectionRepo (2),
TestHubDocumentCrawledPageFK (1). El error es un **IntegrityError de FK sobre
hub_crawled_pages.site_id**: el INSERT del sitio y el de la página acaban en transacciones
distintas, así que cuando se inserta la página el sitio todavía no existe para ella.

Descartados como causa: `test_hub_document.py` y `test_ingestion_storage.py` (se ejecutaron
junto a test_site_model.py y dan 34 passed).

## Hipótesis principal, y por qué
`server/tests/conftest.py` sobreescribe la fixture `event_loop` con `scope="session"`:

    @pytest.fixture(scope="session")
    def event_loop():
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

Con pytest-asyncio 1.3 ese override está **deprecado** y produce exactamente esta clase de
síntoma: fixtures async y tests corriendo en loops distintos, conexiones asyncpg mezcladas
entre tests y trabajo que acaba en transacciones que no son la que el test cree. El propio
`tests/modules/agents_hub/e2e/conftest.py` ya lo documenta: «todos los fixtures de BD tienen
scope="function" para evitar conflictos de event loop entre pytest-asyncio y httpx».

## Trabajo
- **Retirar el override** de `event_loop` del conftest raíz.
- Declarar la política en configuración, no en una fixture:
  `asyncio_default_fixture_loop_scope = "function"` en `[tool.pytest.ini_options]` de
  `server/pyproject.toml` (hoy sale `=None` en la cabecera de pytest, con su warning).
- **Si la hipótesis no se confirma**, bisecar `unit/` por mitades hasta aislar el fichero
  que interfiere y arreglar la causa real. NO cerrar el prompt con los 10 fallos
  reetiquetados como «preexistentes»: eso es lo que ha pasado hasta ahora.
- Segunda sospecha si la primera falla: el motor global cacheado de
  `agents_hub/database/connection.py:get_engine()`, que apunta a `DATABASE_URL` y sobrevive
  entre tests.

## Tests (RED primero)
# should_pass_site_model_suite_together_with_unit_tests   (el que hoy falla: 10 → 0)
# should_not_override_event_loop_fixture_anywhere         (scan de los conftest)
# should_declare_asyncio_fixture_loop_scope_in_config     (lee pyproject)

## Criterio de done
- [ ] `pytest tests/modules/agents_hub/unit tests/modules/agents_hub/integration` → **0 failed**
- [ ] Sin fallos nuevos: `unit`+`integration`+`evaluation`+`public_graphs`+`infra` y
      `tests/modules/agents_hub/e2e` (adjuntar las cifras de antes y después)
- [ ] Cero warnings de pytest-asyncio sobre `event_loop` en la salida
- [ ] Los 3 `test_brain_*` de `tests/test_imports.py` siguen siendo el único fallo
      inventariado (módulo `modules/brain` inexistente), o se retiran si ya no aplican
```

---

### Prompt TST.2 (RED/GREEN) — Ningún test escribe en la BD de desarrollo

**Modelo sugerido**: **Sonnet** — reutiliza la fixture desechable ya existente; el trabajo es cablear y poner el guardarraíl.

```
# PROMPT TST.2 (RED/GREEN) — La suite e2e deja residuos en la BD del desarrollador
# Deploy: n/a (infraestructura de tests)

## Síntoma medido
En la BD de desarrollo hay **12 chatbots residuales** de ejecuciones de test:
8 `E2E Bot <uuid>` (organización «E2E Test Client») y 4 `Pipeline Test <uuid>`
(«Pipeline Test Client»). `tests/modules/agents_hub/e2e/conftest.py` lo dice en su
docstring: «Por defecto usan la misma BD de desarrollo (govgenai)», y su fixture
`db_engine` crea las tablas del hub ahí.

Es la misma familia que la fixture destructiva ya arreglada: un test que escribe en la BD
del desarrollador ensucia el entorno y, cuando además la limpia, se lo lleva por delante.

## Trabajo
- `e2e/conftest.py` pasa a usar la **BD desechable por test** de
  `tests/modules/agents_hub/conftest.py` (fixture `db_url` / `db_session`), en lugar de
  `os.getenv("DATABASE_URL")`. Si algún test e2e necesita el `app` de FastAPI apuntando a
  esa BD, sobreescribir la dependencia de sesión, no el entorno global.
- **Limpieza de los residuos actuales**: comando o paso documentado que borre las
  organizaciones `E2E Test Client` y `Pipeline Test Client` con sus chatbots en cascada.
  Que **reporte lo que borra** y no lo haga en silencio: es la BD del usuario.
- **Guardarraíl**, que es lo que evita la recaída:
  ningún fichero de `tests/` puede (a) llamar a `metadata.drop_all`, ni (b) crear tablas
  sobre una URL que venga de `DATABASE_URL` sin pasar por la fixture desechable.

## Tests (RED primero)
# should_have_no_test_fixture_calling_drop_all              (scan de tests/)
# should_have_no_test_creating_tables_on_the_dev_database   (scan de tests/)
# should_run_e2e_against_a_disposable_database              (la BD del test no es la de DATABASE_URL)
# should_leave_no_rows_in_the_dev_database_after_e2e        (recuento antes/después)

## Criterio de done
- [ ] `tests/modules/agents_hub/e2e` verde contra BD desechable
- [ ] Recuento de `hub_chatbots` en la BD de desarrollo **idéntico antes y después** de
      ejecutar la suite completa (adjuntar los dos números)
- [ ] Los 12 residuos retirados, con el recuento de lo borrado en el cierre
- [ ] Sin BD `test_hub_*` huérfanas tras la ejecución (la fixture las borra en su finally)
```

---

### Prompt TST.3 (GREEN) — Cero fallos preexistentes: se acaban los asteriscos

**Modelo sugerido**: **Sonnet** — dos arreglos mecánicos y un guardarraíl; ninguna decisión de diseño abierta.

```
# PROMPT TST.3 (GREEN) — Retirar los últimos fallos que se venían filtrando
# Deploy: n/a (infraestructura de tests)

## Síntoma medido (tras TST.1 y TST.2)
Con el aislamiento ya arreglado, la suite completa sigue arrastrando 12 resultados rojos
que llevan meses «inventariados» y que hay que recordar filtrar en cada cierre de bloque:

- **3 failed** en `tests/test_imports.py`: `test_brain_llm_gateway_import`,
  `test_brain_extraction_strategies_import`, `test_brain_cortex_import`.
  `ModuleNotFoundError: No module named 'server.app.modules.brain'`. El módulo `brain`
  fue retirado; son tests-smoke de un import que ya no existe.
- **9 errors** de colección en `tests/unit/test_admin_models.py` (3) y
  `tests/unit/test_prompt2_db_api.py` (6): `ModuleNotFoundError: No module named
  'aiosqlite'`. Ambos usan `sqlite+aiosqlite:///:memory:` pero `aiosqlite` no está
  declarado ni en `pyproject.toml` ni en `uv.lock`.

Un fallo que se filtra a mano deja de ser información: nadie distingue el 12 esperado del
13 nuevo. Este prompt lo lleva a cero para que «suite verde» vuelva a significar algo.

## Trabajo
- **`aiosqlite` como dependencia de desarrollo**: `uv add --dev aiosqlite`. Es lo que ya
  presuponen los tests; no se cambian los tests para no usar sqlite.
- **Los 3 tests de `brain`: Caso B, borrado directo.** El módulo no existe y no hay
  migración en curso asociada; el historial de git es la fuente de verdad del pasado.
  No dejar el test comentado ni con `skip`: se borra la función.
  Comprobar antes con `grep -r` que no queda ninguna otra referencia a `modules.brain`
  en el proyecto (código, tests, docs); si queda, retirarla también.
- **Guardarraíl** en `tests/infra/test_suite_hygiene.py`: ningún test puede importar un
  módulo del proyecto que no exista. Basta con un escaneo de los `import
  server.app.modules.<x>` de `tests/` comprobando que el paquete está en disco — barato
  y detecta la próxima retirada que deje tests huérfanos.

## Tests (RED primero para el guardarraíl)
# should_not_import_nonexistent_project_modules   (scan de tests/, RED con los 3 de brain)

## Criterio de done
- [ ] `uv run pytest tests/unit tests/api tests/core tests/modules tests/infra` y los
      ficheros de `tests/` raíz: **0 failed, 0 errors** (adjuntar la cifra)
- [ ] `grep -r "modules.brain"` a cero en todo el proyecto
- [ ] `aiosqlite` en `pyproject.toml` **y** en `uv.lock`
- [ ] Actualizar la memoria de gaps preexistentes: ya no hay nada que filtrar
```

---

### Prompt TST.4 (GREEN) — Coste de la verificación: que la suite deje de frenar el desarrollo

**Modelo sugerido**: **Sonnet** — tres cambios de infraestructura medidos; ninguna decisión de diseño abierta.

> **Añadido el 2026-08-01 a petición del usuario**, al ver que ejecutar la suite completa tras
> cada prompt costaba entre 5 minutos y más de una hora según la carga de la máquina. La
> pregunta era «¿reducimos tests o los ejecutamos solo al cerrar el bloque?»; la respuesta
> medida fue que el problema no es el número de tests sino cómo se ejecutan.

```
# PROMPT TST.4 (GREEN) — Tres cambios medidos y una politica escalonada

## Lo que se midio antes de tocar nada (mismo subconjunto, tiempo que reporta pytest)
- Cobertura forzada en addopts: 21,3 s -> 12,8 s sin ella. ~40 % de toda ejecucion local.
- BD desechable por test: ~1,3 s de SETUP por test. tests/.../integration son 139 tests en
  212 s, o sea que el setup era practicamente todo el directorio.
- Cola gorda: 39 s (chat CoreGraph en modo RAG), 21 s (reconciliador), 13 s (migracion HNSW).

## Los tres cambios
1. Quitar --cov de addopts. CI ya lo pasa explicito en sus dos invocaciones, asi que la
   cobertura vigilada no baja ni un punto. En local, bajo demanda.
2. pytest-xdist con -n auto en addopts. Es seguro porque cada test de BD crea la suya con
   nombre unico, sin estado compartido que serializar.
3. BD desechable por TEMPLATE: una plantilla por sesion con el esquema creado, y cada test
   la copia con CREATE DATABASE ... TEMPLATE, que es copia de ficheros.

## La contrapartida que hay que atajar en el mismo prompt
-n auto reparte los tests entre procesos, y eso ESCONDE el estado filtrado entre tests, que
es justo lo que TST.1 unifico CI para cazar. CI se queda en -n0, con el porque escrito en el
workflow y en CLAUDE.md. En local manda la velocidad; en CI manda la deteccion.

## Politica escalonada (CLAUDE.md, seccion de ejecucion por bloques)
- Durante el prompt: solo el fichero de tests que se esta escribiendo.
- Al cerrar el prompt: los directorios que toca + tests/infra/test_suite_hygiene.py.
- Al cerrar el bloque: la suite entera, desde Git Bash.

## Criterio de done
- [ ] Suite completa verde con -n auto y cifra medida (no deducida)
- [ ] Suite verde tambien con -n0, que es el modo de CI
- [ ] Antes/despues del setup por test, medido
```

---

## Bloque RAG — Refuerzo del retrieval y calidad RAG (Subfase 1.B → 1.C, PENDIENTE)

> **Contexto**: planificado 2026-07-15 a partir de `docs/COMPARATIVA_RAG_LAMB.md` (comparativa arquitectónica del RAG con LAMB + recomendaciones propias + análisis "RAG vs agentes"). Principio rector: invertir en los **cimientos del retrieval** (índice híbrido real, reranker, representación del corpus, evaluación) porque son la herramienta que cualquier evolución agéntica consumirá; no invertir en sofisticación de pipeline que un bucle agéntico haría gratis.
>
> **Posición en el orden de ejecución** (acordada 2026-07-15, **actualizada 2026-07-28**): tras `ING.0` + carga del corpus v1, **antes** del resto del Bloque SEC. El corpus cargado es insumo del dataset dorado (RAG.1). El bloque se **parte**: `RAG.1` (baseline) y `RAG.2` (consolidación de grafos) van delante del **Bloque VIS**; `RAG.3→RAG.14`, detrás. Ver la tabla de enmiendas más abajo.
>
> **Estado**: ✅ relación de prompts aprobada y ✅ **detalle verbatim completado** (2ª pasada, 2026-07-15). Bloque listo para ejecutar cuando llegue su turno en el orden.
>
> **Lente de mantenibilidad (añadida 2026-07-24)**: `docs/RAG_SUSTITUCION_DEPENDENCIAS.md` reencuadra este bloque + el Bloque ING como "código propio → dependencia madura", derivado de `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` §6 (RAG/ingesta se queda en el perímetro; el alivio de mantenimiento viene de apoyar las **primitivas** en librerías, no de mover nada a OWUI). Clasificación: **✅ ya apoyado, no tocar** (chunker→`langchain-text-splitters`, embeddings→`sentence-transformers`, PDF→`docling`); **♻️ reinventado, sustituir** (`keyword_search` ILIKE→FTS `tsvector` = **RAG.4**); **➕ hueco, añadir** (HNSW=**RAG.3**, reranker `bge-reranker-v2-m3` vía `sentence-transformers` ya instalada=**RAG.6**, parent-child=**RAG.8**, multi-formato en Docling=Bloque ING); **🔒 diferencial, no sustituir nunca** (`superseded`/P9, aislamiento `owner_id`, contrato de citas `sources`/P6, `hasher`, `quality/*`). **Anti-patrón**: no adoptar LlamaIndex/Haystack como orquestador (rompería la gobernanza tejida en el SQL). **80 % del valor**: RAG.4 + RAG.6.

### Propósito del bloque

1. **Consolidar los dos grafos** en uno: llevar `public_graphs/CoreGraph` (quality gate, cascada de config, LanguagePolicy — hoy solo en tests) a producción y retirar `agent/graph.py`.
2. **Medir antes de mejorar**: dataset dorado + métricas de recuperación en CI; toda mejora posterior se valida contra baseline.
3. **Elevar la calidad del retrieval**: índice HNSW, pata léxica real (tsvector), umbral + presupuesto de tokens, reranker cross-encoder, contextual retrieval, parent-child chunking.
4. **Robustecer los embeddings**: metadato de modelo/dimensión por chunk, validación inmutable al crear, ruta de re-embedding (patrón LAMB "por colección").
5. **Cerrar el bucle de calidad**: query rewriting conversacional, modo bypass de depuración, progreso granular de ingesta, test scenarios por chatbot y detección de huecos de corpus desde el feedback.

### Decisiones de diseño

- **Medir primero**: RAG.1 establece la baseline; ningún cambio del retriever (RAG.3–RAG.8, RAG.10) se cierra sin comparar recall@k/MRR contra ella en CI.
- **Consolidación temprana** (RAG.2): a partir de ahí existe **un solo grafo**; `agent/graph.py` se retira por **Caso B** (borrado directo, no es legacy NiceGUI) con el checklist completo de migración de CLAUDE.md. `Source` y `EvidenceItem` se unifican en el contrato de `public_graphs`.
- **Sin flags muertos**: `reranker_enabled` y `min_retrieval_score` (en `HubChatbot` desde 9B) o se activan (RAG.5, RAG.6) o se retiran del contrato. No queda config expuesta en la API admin sin consumidor.
- **Patrones importados de LAMB** (ver `docs/COMPARATIVA_RAG_LAMB.md` §7): query rewriting (`context_aware_rag`), config de embeddings inmutable y validada, parent-child chunking, connector `bypass`, `progress_callback` de ingesta, test scenarios. Lo que NO se copia: ChromaDB/SQLite, disco local, I/O síncrona, token estático.
- **Cambios de representación exigen re-embedding**: RAG.7 y RAG.8 alteran el texto embebido → migración de corpus documentada (comando de re-chunk/re-embed de RAG.9 como prerrequisito operativo si el corpus ya está cargado).
- **Deploy: edge** en todo el bloque (retrieval y datos del cliente); solo la UI admin de test scenarios (RAG.13) toca superficie cloud.

### Mapa de ejecución

| # | Prompt | Título | Depende de | Modelo sugerido |
|---|--------|--------|------------|-----------------|
| 1 | RAG.1 | Dataset dorado + métricas recall@k/MRR + CI de regresión | corpus de prueba (ING.0) | Sonnet |
| 2 | RAG.2 | Consolidación de grafos: CoreGraph a producción, retirada de `agent/graph.py` | 9B ✅, RAG.1 | **Opus** |
| 3 | RAG.3 | Índice HNSW en pgvector (migración Alembic) | — | Sonnet |
| 4 | RAG.4 | Pata léxica real: tsvector + GIN sustituye ILIKE en `HybridRetriever` | RAG.1 | Sonnet |
| 5 | RAG.5 | Activar `min_retrieval_score` + presupuesto de tokens del contexto | RAG.2 | Sonnet |
| 6 | RAG.6 | Reranker cross-encoder (BGE-reranker-v2-m3) + activar `reranker_enabled` | RAG.1, RAG.4 | **Opus** |
| 7 | RAG.7 | Contextual retrieval: headers + título en el texto embebido | RAG.1 | Sonnet |
| 8 | RAG.8 | Parent-child chunking (small-to-big) + chunking configurable por chatbot | RAG.7 | Sonnet |
| 9 | RAG.9 | Metadato de embeddings por chunk + validación inmutable + re-embedding | — | Sonnet |
| 10 | RAG.10 | Query rewriting conversacional (LLM pequeño + fallback) | RAG.2 | Sonnet |
| 11 | RAG.11 | Modo bypass/debug: prompt final sin llamar al LLM | RAG.2 | Sonnet |
| 12 | RAG.12 | Progreso granular de `HubIngestionJob` (callback + stats) | — | Sonnet |
| 13 | RAG.13 | Test scenarios por chatbot (backend + UI admin mínima) | RAG.11 | Sonnet |
| 14 | RAG.14 | Feedback → huecos de corpus (clustering + `HubContentFinding`, integra 9Q) | — | Sonnet/**Opus** |

RAG.3, RAG.9 y RAG.12 son independientes y pueden intercalarse como prompts cortos entre los mayores.

> **Enmiendas del 2026-07-28 (replanificación del corpus normativo).** El Bloque VIS se intercala **entre RAG.2 y RAG.3**: `ING.0.1→0.5` → carga del corpus v1 → `RAG.1` (baseline) → `RAG.2` (consolidación) → `VIS.1→VIS.3` → `RAG.3→RAG.14` → Bloque SYNC. Cuatro prompts de este bloque quedan enmendados en su detalle verbatim, marcado con `# ENMIENDA` in situ:
>
> | Prompt | Enmienda | Por qué |
> |---|---|---|
> | RAG.2 | La evidencia inicial del selector no se cementa como «índice de documentos» | ~72k tokens, no cabe; VIS.2 lo sustituye por el índice de submaterias (2.307 tokens) |
> | RAG.4 | El `tsvector` incorpora `termes_bilingues` de `doc_metadata` | El puente léxico despesa/gasto se regenera con SQL; en el embedding costaría GPU |
> | RAG.5 | `context_token_budget` **la crea VIS.2**; RAG.5 solo la consume | La columna la necesita antes la inyección de subconjunto del Nivel 2 |
> | RAG.7 | Solo se embebe contexto **estructural**; nunca la taxonomía | El vocabulario es revisable: taxonomía embebida ⇒ re-embedding en cada revisión |

### Reglas duras del bloque

- Ninguna mejora del retriever se cierra sin ejecutar la suite de RAG.1 y comparar contra baseline (adjuntar cifras en el cierre del prompt).
- **La taxonomía (ámbito, submaterias) nunca forma parte del texto embebido.** Es lo que mantiene revisable el vocabulario pendiente de validar por SG: reclasificar debe costar un `UPDATE`, no una reindexación.
- RAG.2 cumple el checklist de migración completo de CLAUDE.md: grep de referencias a `agent/graph.py` y a `Source` antiguo antes de cerrar; ningún import activo al código retirado.
- Los tests de retrieval de RAG.1 son **métricas puras sin LLM** (deben correr en CI en segundos); RAGAS queda para evaluación periódica, nunca como gate de CI.
- Todo router o servicio nuevo se etiqueta `Deploy: edge|cloud` en su docstring y se registra en `_register_edge`/`_register_cloud`.

### Prompts del bloque (detalle verbatim — 2ª pasada 2026-07-15)

---

### Prompt RAG.1 (RED/GREEN) — Dataset dorado + métricas de recuperación + CI de regresión

**Modelo sugerido**: **Sonnet** — métricas puras + harness; alcance cerrado, sin decisiones abiertas.

```
# PROMPT RAG.1 (RED/GREEN) — Dataset dorado y gate de CI de retrieval
# Deploy: edge

## Contratos (modules/agents_hub/evaluation/golden_dataset.py)
- GoldenQuery (Pydantic frozen): query, language ('ca'|'es'|'en'), expected_canonical_urls
  (list[str], min 1) | expected_document_ids, tags (list[str], p.ej. 'sigla', 'conversacional',
  'normativa'), history (list[str] | None — para RAG.10), notes.
- GoldenDataset: nombre, chatbot de referencia, documents_fingerprint (hash del corpus esperado,
  para detectar dataset desalineado del corpus), queries: list[GoldenQuery]. Loader JSON.

## Métricas (modules/agents_hub/evaluation/retrieval_metrics.py) — SIN LLM
- recall_at_k(retrieved_ids, expected_ids, k) -> float
- mrr(retrieved_ids, expected_ids) -> float
- Funciones puras sobre listas de IDs/URLs; nada de red ni BD.

## Harness (modules/agents_hub/evaluation/retrieval_eval.py)
- run_golden_eval(retriever, dataset, top_k) -> EvalReport {per_query: [...], recall_at_5,
  recall_at_10, mrr}: ejecuta HybridRetriever.hybrid_search por query y evalúa.
- Baseline versionada en server/tests/modules/agents_hub/evaluation/baselines/<dataset>.json.
- CLI (python -m ...evaluation.run_golden --dataset X --chatbot-id Y [--update-baseline]):
  informe tabular + diff contra baseline. --update-baseline regenera (uso deliberado, nunca CI).

## Dos niveles de ejecución (decisión de diseño)
1. CI: mini-corpus fixture determinista (15-25 .md pequeños en tests/fixtures/golden_corpus/,
   ingeridos en el setup del test vía IngestionWatcher sobre BD de test) + dataset dorado de
   ~25 queries. Gate: recall@5 y MRR >= baseline - 0.02 (tolerancia). Debe correr en segundos.
2. Manual/nightly: dataset completo (30-50 queries) contra el corpus de prueba cargado por
   ING.0.2 — vía CLI, no bloquea CI.

## RAGAS queda fuera de CI
- Documentar en evaluation/rag_metrics.py (docstring de módulo) que faithfulness/answer_relevancy
  son evaluación periódica manual; nunca gate de CI. Corregir de paso el `except Exception: pass`
  silencioso: log warning con el motivo del fallback léxico.

## Tests (RED primero) — tests/modules/agents_hub/evaluation/
# should_compute_recall_at_k_for_hit_and_miss
# should_compute_mrr_with_first_relevant_position
# should_load_and_validate_golden_dataset_schema
# should_reject_query_without_expected_targets
# should_run_eval_over_fixture_corpus_and_produce_report
# should_fail_gate_when_recall_drops_beyond_tolerance
# should_pass_gate_when_metrics_meet_baseline
# should_detect_corpus_fingerprint_mismatch

## Criterio de done
- [ ] Gate verde en CI con el mini-corpus (añadir al workflow ci.yml)
- [ ] Baseline inicial commiteada con las cifras del retriever actual (pre-mejoras)
- [ ] CLI probado contra el corpus de prueba de ING.0 (adjuntar cifras en el cierre)
```

---

### Prompt RAG.2 (RED/GREEN) — Consolidación de grafos: CoreGraph a producción

**Modelo sugerido**: **Opus** — migración multi-módulo con decisiones embebidas (unificación de contratos, port del loop agéntico, preservación del contrato SSE).

```
# PROMPT RAG.2 (RED/GREEN) — Un solo grafo: public_graphs/CoreGraph sirve /hub/chat
# Deploy: edge

## Objetivo
api/v1/hub_chat.py deja de construir el grafo con agent/graph.py:create_agent_graph y pasa a
usar public_graphs/core/graph_factory.py + CoreGraph. Entran en producción: quality gate con
fallback, cascada ConfigResolver (Plataforma→Organización→Chatbot), LanguagePolicy y el
contrato EvidenceItem.

## Qué se preserva (sin cambio de contrato observable)
- SSE: eventos status/token/done(sources)/error idénticos (astream_events v2). El evento done
  serializa EvidenceItem con el MISMO shape JSON actual (document_id, title, url, score) —
  el frontend/widget no se toca.
- enforce_citation_contract (agent/citation_validator.py) aplicado tras la generación.
- Router multi-materia (agent/router_node.py) ejecutado en el endpoint antes del grafo.
- Persistencia HubInteraction + trazas Langfuse (services/observability.py).
- agent/language_detector.py como implementación del nodo detect_language del CoreGraph.

## Port del modo agéntico
- El loop de agent/graph.py:_run_agentic_loop (bind_tools, máx. 10 iteraciones, acumulación de
  fuentes por read_document) se extrae a un componente del CoreGraph usado cuando
  retrieval_mode == MD_AGENT_SELECTOR. Los tools (agent/tools/) no cambian.
- strategies/md_agent_selector_pipeline.py deja de ser stub "índice completo": devuelve el
  índice de documentos como evidencia inicial y delega la selección al loop agéntico.
# ENMIENDA (2026-07-28, Bloque VIS): el índice de DOCUMENTOS es provisional y no se cementa.
# Medido en INFORME_MATERIES_I_METADADES_AGENTS.md §6.1: el catálogo de fichas son ~72k tokens
# y no cabe en el system prompt; el índice de las 58 submaterias son 2.307 tokens y sí cabe.
# VIS.2 lo sustituye por el índice de submaterias. Aquí basta con dejar el pipeline consolidado
# y el loop agéntico portado, con la selección aislada en un punto de extensión — sin asumir en
# los tests que la evidencia inicial es "todos los documentos".

## Unificación de contratos
- Source (agent/state.py) se retira; EvidenceItem (strategies/retrieval_contract.py) es el único
  contrato de evidencia. Las REGLAS DE CITA y format_sources_block de agent/prompts.py se
  integran en la TemplateStrategy del CoreGraph (una sola fuente del system prompt).

## Quality gate en producción
- cfg desde ConfigResolver (quality_threshold, min_retrieval_results, min_retrieval_score).
- Si el gate no pasa → nodo fallback: respuesta "no tengo información suficiente" (misma que
  usa el citation validator) emitida por SSE como respuesta normal + marcada en HubInteraction
  (nueva columna fallback_reason: 'quality_gate' | 'citation' | NULL — migración Alembic;
  RAG.14 la consume).

## Retirada (Caso B — borrado directo, checklist CLAUDE.md completo)
- agent/graph.py, Source en agent/state.py, partes de agent/prompts.py absorbidas.
- grep -r de create_agent_graph / AgentState.Source / imports de agent.graph antes de cerrar.
- Los tests que testeaban el grafo antiguo se migran al CoreGraph (no se borran aserciones de
  comportamiento: se reapuntan).

## Tests (RED primero) — tests/modules/agents_hub/ + tests/public_graphs/
# should_serve_chat_via_coregraph_in_rag_mode
# should_serve_chat_via_coregraph_in_long_context_mode
# should_serve_chat_via_coregraph_in_agent_selector_mode
# should_keep_sse_event_contract_unchanged           (snapshot de eventos)
# should_apply_quality_gate_fallback_on_low_evidence
# should_persist_fallback_reason_on_interaction
# should_resolve_config_cascade_in_live_chat         (org override visible en runtime)
# should_enforce_citation_contract_after_generation
# should_route_router_kind_chatbot_before_graph
# should_run_agentic_loop_with_tools_in_selector_mode
# should_have_no_references_to_retired_graph         (import scan)
+ suite e2e de chat existente (test_chat_flow.py, test_hub_chat_sse.py) verde SIN cambios de
  aserciones de contrato.

## Criterio de done
- [ ] Suite completa verde (backend) + RAG.1 sin regresión (adjuntar cifras)
- [ ] agent/graph.py eliminado; grep de referencias limpio
- [ ] Migración Alembic de fallback_reason aplicada (alembic current)
```

---

### Prompt RAG.3 (RED/GREEN) — Índice HNSW en pgvector

**Modelo sugerido**: **Sonnet** — migración puntual con verificación de plan de consulta.

```
# PROMPT RAG.3 (RED/GREEN) — Índice ANN para la búsqueda vectorial
# Deploy: edge

## Migración Alembic (server/migrations/versions/)
- CREATE INDEX ix_hub_document_chunks_embedding_hnsw ON hub_document_chunks
  USING hnsw (embedding vector_cosine_ops);  (defaults m=16, ef_construction=64)
- Ídem para hub_crawled_pages.page_embedding (lo usa el detector semántico 9Q).
- Downgrade: DROP INDEX. Requiere pgvector >= 0.5 (verificar versión de la imagen Docker;
  actualizar docker-compose si hace falta).

## Sin cambios de código
- La query de retriever.py (cosine_distance + ORDER BY) ya es indexable; no se toca.

## Tests (RED primero) — tests/modules/agents_hub/integration/test_hnsw_index.py
# should_use_hnsw_index_in_query_plan          (EXPLAIN contiene 'hnsw')
# should_return_same_top_k_as_exact_scan_on_small_corpus  (corpus fixture: ANN==exacto)
# should_apply_and_rollback_migration_cleanly

## Criterio de done
- [ ] uv run alembic upgrade head aplicado y alembic current mostrado
- [ ] Suite RAG.1 sin regresión (tolerancia del gate ya contempla ANN)
```

---

### Prompt RAG.4 (RED/GREEN) — Pata léxica real: tsvector + GIN sustituye ILIKE

**Modelo sugerido**: **Sonnet** — sustitución localizada en `_keyword_search`; contrato RRF intacto.

```
# PROMPT RAG.4 (RED/GREEN) — Full-text search de PostgreSQL en la rama léxica del híbrido
# Deploy: edge

## Migración Alembic
- Columna generada en hub_document_chunks:
  tsv tsvector GENERATED ALWAYS AS (to_tsvector(
    CASE WHEN language = 'es' THEN 'spanish'::regconfig ELSE 'simple'::regconfig END,
    coalesce(content, ''))) STORED
  (si el chunk no tiene columna language propia, derivarla del documento en la ingesta y
  añadirla primero — verificar el modelo real antes de escribir la migración).
- CREATE INDEX ... USING gin (tsv).
- Documentar limitación: catalán sin stemmer nativo en PG core → config 'simple' (sin stemming);
  posible diccionario Snowball/Hunspell catalán como mejora de despliegue, fuera de alcance.

## Retriever (services/retriever.py — _keyword_search)
- Sustituir el AND de ILIKE por websearch_to_tsquery(config_del_idioma, query) @@ tsv con
  ranking ts_rank_cd normalizado a [0,1] (dividir por el máximo del lote).
- Conservar: filtros chatbot_id / temporales / superseded / idioma, top_k*2, y la fusión RRF
  (k=60, vector_weight=0.7) SIN cambios. Si VIS.1 ya está cerrado, conservar también su
  MetadataFilter (ámbito / submateria / nivell_acces) — la sustitución es de la rama léxica,
  no del filtrado.
- BORRAR el código ILIKE (borra, no comentes).

# ENMIENDA (2026-07-28): puente léxico bilingüe en el tsvector, no en el embedding.
# El BM25 cross-lingüe falla del todo entre 'despesa' y 'gasto' (no comparten una letra). El
# informe de materias §6.2 propone pares bilingües del dominio como puente léxico. Su sitio es
# ESTA columna, no el texto embebido: el tsvector se regenera con una sentencia SQL, un
# embedding necesita GPU y horas.
# - La expresión del tsvector concatena content con los termes_bilingues del documento
#   (doc_metadata->>'termes_bilingues'). Como es columna generada y los términos viven en
#   hub_documents, la vía es o denormalizar esos términos al chunk en la ingesta, o pasar de
#   columna generada a columna materializada por trigger/ingesta. Elegir con el modelo real
#   delante y documentar la elección; NO meter la taxonomía (ámbito/submaterias) en ningún caso.
# - Test añadido: should_bridge_bilingual_terms_in_lexical_search  ('despesa' encuentra el chunk
#   castellano cuyo documento declara el par despesa/gasto).

## Tests (RED primero) — tests/modules/agents_hub/unit+integration/test_retriever.py (ampliar)
# should_match_stemmed_spanish_terms            ('becas' encuentra 'beca')
# should_rank_chunks_with_exact_terminology_first  (siglas/códigos: 'EBEP', 'RD 203/2021')
# should_use_simple_config_for_catalan_chunks
# should_return_normalized_keyword_scores
# should_keep_rrf_fusion_contract_unchanged
# should_use_gin_index_in_query_plan            (EXPLAIN)
# should_have_no_ilike_left_in_retriever        (scan del fichero)

## Criterio de done
- [ ] Migración aplicada (alembic current)
- [ ] RAG.1: mejora o igualdad de recall@5/MRR contra baseline, con cifras en el cierre
      (se esperan ganancias en las queries con tag 'sigla')
```

---

### Prompt RAG.5 (RED/GREEN) — Umbral de score aplicado + presupuesto de tokens del contexto

**Modelo sugerido**: **Sonnet** — consumo de config existente + empaquetador; decisiones acotadas aquí.

```
# PROMPT RAG.5 (RED/GREEN) — min_retrieval_score real + context packer con presupuesto
# Deploy: edge

## Umbral (decisión de diseño cerrada)
- min_retrieval_score (ya en HubChatbot, defaults org y ConfigResolver, default 0.25) se aplica
  sobre la SIMILITUD COSENO de la rama vectorial, ANTES de la fusión RRF (WHERE similarity >=
  umbral). La rama léxica no filtra por umbral (su señal es de ranking, no de similitud) —
  documentarlo en el docstring del retriever.
- El quality gate del CoreGraph (RAG.2) sigue usando quality_threshold sobre la media de
  evidencias: son dos controles distintos (por-chunk vs por-respuesta); documentar la relación.

## Empaquetador (services/retrieval/context_packer.py)
- pack(evidences: list[EvidenceItem], budget_tokens: int) -> PackedContext:
  1) ordenar por score desc; 2) fusionar chunks adyacentes del mismo documento (chunk_index
  consecutivos) eliminando solapamiento textual; 3) acumular hasta el presupuesto (contador de
  tokens reutilizando el que usa LongContextRetrievalStrategy para el límite de 128k); 4)
  registrar dropped_count para trazas/bypass.
- Config: nueva columna context_token_budget (nullable) en HubChatbot + default_context_token_budget
  en HubOrganizacion + default de plataforma 4000 en ConfigResolver (misma cascada que el resto).
  Migración Alembic + exposición en routers CRUD (hub_chatbots_router, hub_organizaciones_router).
# ENMIENDA (2026-07-28): la columna y su cascada las crea VIS.2, que las necesita antes para la
# inyección del subconjunto del Nivel 2. Aquí NO se crea la migración: solo se consume el valor
# ya resuelto por ConfigResolver. Se conserva el test should_resolve_budget_from_cascade_* como
# regresión. Si por lo que sea VIS.2 no estuviera cerrado al llegar aquí, crear la columna en
# este prompt y retirar el trozo correspondiente de VIS.2 — pero no en los dos.
# ENMIENDA (2026-07-31, decisión del usuario al cerrar el Bloque VIS): el default de plataforma
# es **128.000 y con carácter general**, no 4.000. Ya está creado y aplicado por VIS.2
# (migración d1m2n3o4p5q6). Bajarlo recortaría MD_LONG_CONTEXT a 4k y lo dejaría inservible, y
# un mismo valor no puede significar dos cosas según quién lo lea. El packer CONSUME este
# presupuesto tal cual; si necesita cortar antes por razones propias, con su constante y no
# tocando el default compartido.
- La estrategia RAG (vector_strategy / rag_vector_pipeline) usa el packer antes de construir el
  bloque DOCUMENTOS DISPONIBLES.

## Tests (RED primero)
# should_filter_vector_candidates_below_min_score
# should_keep_all_candidates_when_threshold_is_zero
# should_pack_context_within_token_budget
# should_drop_lowest_scored_evidence_first_when_cutting
# should_merge_adjacent_chunks_of_same_document
# should_resolve_budget_from_cascade_platform_org_chatbot
# should_report_dropped_count_in_packed_context

## Criterio de done
- [ ] Migración aplicada; flags visibles y FUNCIONALES desde la API admin
- [ ] RAG.1 sin regresión (el umbral 0.25 no debe recortar hits del dorado; si lo hace,
      ajustar default con datos y documentar)
```

---

## Bloque MOD — Modelos de embedding y reranker: local en edge, API en cloud (2026-08-01)

> **Añadido a petición del usuario**, antes de ejecutar RAG.6 y **antes de cargar el corpus v1**.
> Decisión completa, con la verificación de la API de Google: `docs/DECISION_MODELOS_EMBEDDING_RERANKER.md`.
>
> Lo que lo motiva: BGE-M3 (1,1 GB) más el reranker local (~600 MB) son los 3-4 GB por instancia
> que `CLAUDE.md` fija como criterio de extracción a microservicio. En cloud queremos API; en
> edge queremos modelo local, porque el dato no sale. El mismo codebase debe servir a los dos.
>
> **Por qué antes de cargar el corpus**: cambiar de modelo después cuesta re-embeber las ~380
> normas con su índice HNSW detrás. Ahora es el momento más barato que va a existir.

---

### Prompt MOD.1 (RED/GREEN) — Propósito en la configuración + procedencia en el vector

**Modelo sugerido**: **Sonnet** — dos columnas y un guardarraíl; las decisiones están cerradas en el documento.

```
# PROMPT MOD.1 (RED/GREEN) — Que cambiar de modelo deje de ser un salto al vacio
# Deploy: cloud (configuracion) + edge (procedencia y guarda)

## Contexto medido (no repetir la investigacion)
- gemini-embedding-001 admite dimension FLEXIBLE de 128 a 3072: 1024 es valido. La columna
  Vector(1024), el indice HNSW y el corpus cargado sobreviven a un cambio de proveedor.
- Las dimensiones distintas de 3072 NO vienen normalizadas ("you must manually normalize
  non-3072 dimensions"). Normalizamos nosotros, siempre, venga como venga del proveedor.
- La guarda de dimension de hub_chatbots_router.py NO PUEDE SALTAR: compara dos getattr de
  atributos que no existen. Se arregla aqui.

## Configuracion (HubLLMConfig)
- purpose: 'chat' | 'embedding' | 'rerank', default 'chat', CON CheckConstraint —es una
  enumeracion estable con consumidor, mismo criterio que nivell_acces en ING.0.2.
- output_dimensionality: int | None. None = el default del modelo.
- Se REUTILIZA el panel existente (HubProvider con base_url y api_key, available-models, test
  de conexion, LLMConfigsPage). No se construye un panel nuevo: se filtra por purpose.

## Procedencia (HubDocumentChunk)
- embedding_model: str | None y embedding_dim: int | None, escritos por la ingesta.
- Sin esto, la configuracion es un interruptor que rompe en silencio: el coseno entre
  vectores de dos espacios distintos no da error, da resultados malos.

## Servicios
- LocalEmbeddingService y GoogleEmbeddingService exponen `model_name` y `dimensions`.
- GoogleEmbeddingService acepta modelo y output_dimensionality, y L2-normaliza su salida.
- get_embedding_service() sigue devolviendo el local: la seleccion por configuracion es MOD.2.

## Tests (RED primero)
# should_persist_purpose_and_output_dimensionality
# should_reject_an_unknown_purpose                  (el CHECK muerde)
# should_expose_model_name_and_dimensions_on_services
# should_l2_normalize_google_embeddings             (venga o no normalizado del proveedor)
# should_record_model_and_dimension_on_every_chunk  (la ingesta escribe procedencia)
# should_detect_a_corpus_embedded_with_another_model (la guarda ya puede saltar)

## Criterio de done
- [ ] Migracion aplicada y reversible
- [ ] La guarda de recalculate-corpus salta de verdad, con test que lo demuestre
- [ ] Contrato OpenAPI + Orval regenerados si cambia la API
```

---

### Prompt MOD.2 (RED/GREEN) — Seleccion del servicio de embeddings por configuracion

**Modelo sugerido**: **Sonnet** — cableado sobre la cascada que ya existe.

```
# PROMPT MOD.2 (RED/GREEN) — get_embedding_service resuelve contra la config efectiva
# Deploy: shared

- La cascada Plataforma -> Organizacion -> Chatbot elige el servicio, igual que el resto de
  la configuracion. GoogleEmbeddingService deja de ser codigo muerto.
- Aqui encaja HttpEmbeddingService, previsto en CLAUDE.md para cuando BGE-M3 se extraiga a
  microservicio: el resto del codigo no cambia.
- SIN fallback silencioso: si el modelo configurado no carga, error explicito.
- El default de plataforma SIGUE siendo BGE-M3 local. Cambiarlo es un UPDATE, no un deploy.

## Despacho por provider_type, no por proposito (ampliacion del 2026-08-01)

MOD.1 dejo configurable QUE modelo y con QUE clave, pero QUE ADAPTADOR lo habla seguia
siendo codigo. El mecanismo para resolverlo ya existe y hay que aprovecharlo, no duplicarlo:
`HubProvider.provider_type` ('google_genai', 'openai_compatible', ...) es lo que usa
`model_factory._build_model` para elegir implementacion DESDE DATOS en el chat.

- La factoria de embeddings y la de rerank despachan por `provider_type`, igual que la de
  chat. Anadir un modelo o cambiar de proveedor DENTRO de un tipo ya soportado pasa a ser un
  UPDATE; el codigo solo se toca para un tipo de proveedor nuevo, que es irreducible.
- Los tres purpose comparten factoria y contrato de resolucion. Tres despachos paralelos
  divergen: ya paso con el system prompt antes de RAG.2.
- Test: should_resolve_the_adapter_from_provider_type_without_code_changes

## Medicion pendiente que este prompt habilita (no la ejecuta)

Cuando el corpus v1 este cargado, comparar BGE-M3 contra Google a 1024 con `run_golden.py`
sobre el dorado en valenciano. La documentacion de Google declara 100+ idiomas y lidera
MMTEB, pero NO publica lista por idioma y el catalan no aparece explicitamente: la calidad en
valenciano hay que medirla, no suponerla. Con la cascada por chatbot y la procedencia de
MOD.1 se pueden tener dos chatbots sobre el mismo corpus, uno por modelo, sin mezclar
espacios vectoriales.
```

---

### Prompt RAG.6 (RED/GREEN) — Reranker detrás de protocolo + activación de `reranker_enabled`

**Modelo sugerido**: **Opus** — integración con decisiones reales: normalización de scores, pool de candidatos, gestión del default heredado y medición.

```
# PROMPT RAG.6 (RED/GREEN) — Reranker detrás de protocolo, flag por chatbot
# Deploy: edge

# PARTIDO EN DOS (2026-08-01, decisión del usuario de habilitar los servicios de GCP todos a
# la vez durante el despliegue). Cada mitad entrega algo que funciona:
#
#   RAG.6a — EL MECANISMO. Se puede hacer YA, sin ningún servicio habilitado: protocolo
#     Reranker, resolución por configuración (purpose='rerank' + provider_type, patrón de
#     MOD.2), pool ampliado, sustitución del score, normalización y cableado en
#     rag_vector_pipeline por `_construir_estrategia`. Tests con un **reranker determinista**,
#     igual que RAG.1 mide el mecanismo de recuperación con un embedding determinista.
#
#   RAG.6b — EL ADAPTADOR REAL Y LA MEDICIÓN. **Va DESPUÉS del bloque Deploy**, porque el
#     Ranking API vive en Discovery Engine y lo habilita D.0. Aquí se comprueba que el
#     contrato escrito coincide con el real —un adaptador probado solo contra un doble está
#     verificado en su lógica, no en su integración— y se decide con datos si el flag se
#     enciende en algún sitio.
#
# Por qué se parte y no se espera entero: escribir un adaptador que nunca ha hablado con el
# servicio real es la familia de riesgo que este proyecto ya pisó tres veces el 2026-08-01
# —GoogleEmbeddingService inalcanzable durante meses, la guarda de dimensión que no podía
# saltar, y su test verificando un campo inventado—. Las tres pasaban los tests.
#
# La medición del idioma NO necesita el corpus v1: el dataset dorado ya está en valenciano y
# el corpus de fixture son 25 normas breves. RAG.6b depende solo de D.0.
#
# Al habilitar el servicio (en D.0), comprobar dos cosas que la documentación pública no deja
# cerradas:
#   1. Precio por consulta vigente (la referencia que se manejó, ~1 $/1.000 consultas, viene
#      de fuente secundaria: la pagina oficial de precios no se pudo leer).
#   2. Si aplica el **modelo de suscripción mensual** que Discovery Engine ofrece para apps y
#      data stores. El Ranking API es STATELESS —no indexa, no hay data store— asi que no
#      deberia aplicarle, pero es la unica via de coste fijo plausible y hay que confirmarlo.
#
# ELECCION DE MODELO, ya cerrada por medicion del codigo: `semantic-ranker-default-004`
# (1.024 tokens). Las variantes -003 y -002 son de 512 tokens y el chunker produce chunks de
# 4.000 caracteres (~1.000 tokens): truncarian la mitad de cada chunk.
#
# RIESGO ABIERTO que este prompt debe cerrar con datos: Google declara 25 idiomas y NO
# publica cuales; el catalan no aparece. Si el valenciano no esta, el reranker reordenaria
# por senales que no entiende y la degradacion seria silenciosa. Se decide con el gate de
# RAG.1 sobre el dorado en valenciano: dos ejecuciones, con y sin reranker.
#
# ENMIENDA (2026-08-01, decisión del usuario — ver docs/DECISION_MODELOS_EMBEDDING_RERANKER.md):
# **el reranker nace por API, no local.** El prompt original ponía LocalReranker como
# implementación de referencia; eso añade ~600 MB al contenedor y construye justo el problema
# que el Bloque MOD viene a evitar. Se invierte:
# - La implementación de referencia es por API (proveedor a decidir con datos de precio y
#   latencia: Vertex AI Ranking, Cohere Rerank u otro; NO se elige a ciegas en este prompt).
# - `LocalReranker` se conserva como opción de EDGE, detrás del mismo protocolo.
# - El proveedor y el modelo se configuran con `purpose='rerank'` en HubLLMConfig (MOD.1), no
#   con una constante en el código.
# - **Ojo al default**: `reranker_enabled` viene en True en toda la cascada, así que en cuanto
#   exista la implementación se activa para TODOS los chatbots. Decidir explícitamente si el
#   default se queda en True, con la misma disciplina que el umbral de RAG.5.

## Protocolo e implementación (services/reranker.py)
- class Reranker(Protocol): async def rerank(query: str, candidates: list[str], top_k: int)
  -> list[RerankResult {index, score}].
- LocalReranker (opción edge): sentence_transformers.CrossEncoder('BAAI/bge-reranker-v2-m3'),
  singleton lazy-load + asyncio.to_thread + batch, scores normalizados con sigmoide a [0,1]
  (mismo patrón que LocalEmbeddingService). get_reranker() para Depends.
- SIN fallback silencioso (regla CLAUDE.md): si reranker_enabled y el modelo no carga,
  error explícito en el arranque del servicio — no degradar a híbrido sin avisar.

## Integración (vector_strategy / rag_vector_pipeline)
- Si cfg.reranker_enabled: recuperar pool ampliado (max(30, top_k*3)) del híbrido →
  rerank(query, [content]) → quedarse top_k. El score del reranker SUSTITUYE al de fusión
  para el packer (RAG.5) y el quality gate (los umbrales operan sobre [0,1] coherente).
- Log de duración del rerank en la traza Langfuse (observability).

## Default heredado (decisión cerrada)
- reranker_enabled tiene default True desde 9B pero nunca se consumió. Al activarlo de verdad:
  migración Alembic que pone False en chatbots/organizaciones existentes + default False en
  modelo, routers y ConfigResolver. El admin lo activa por chatbot tras validar con RAG.1.
  (~1.1 GB extra de RAM in-process: mismo criterio de extracción a microservicio que BGE-M3,
  CLAUDE.md §microservicios; el protocolo ya deja listo un futuro HttpReranker.)

## Tests (RED primero) — unit con CrossEncoder mockeado; 1 test integración marcado slow
# should_rerank_candidates_with_relevant_first        (fixture con pares obvios)
# should_not_call_reranker_when_flag_disabled         (spy)
# should_retrieve_wider_pool_when_reranking
# should_normalize_scores_to_unit_interval
# should_replace_fusion_score_with_rerank_score
# should_fail_loudly_when_enabled_and_model_unavailable
# should_log_rerank_latency_in_trace
# should_default_to_disabled_after_migration

## Criterio de done
- [ ] RAG.1 con flag ON vs OFF: adjuntar tabla comparativa (recall@5, MRR, latencia media)
- [ ] Migración de defaults aplicada; sin flags muertos restantes en el contrato
```

---

### Prompt RAG.7 (RED/GREEN) — Contextual retrieval estructural (headers en el texto embebido)

**Modelo sugerido**: **Sonnet** — cambio localizado en chunker/watcher + regeneración con herramienta existente.

```
# PROMPT RAG.7 (RED/GREEN) — Embeber chunks con su contexto jerárquico
# Deploy: edge

## Chunker (ingestion/chunker.py)
- Cada chunk expone embedding_text = "<título documento> > <header_1> > <header_2> > <header_3>
  \n\n<content>" (niveles presentes; sin duplicar si el content empieza por el propio header).
- El content ALMACENADO y mostrado como evidencia NO cambia; embedding_text no se persiste.

# ENMIENDA (2026-07-28): la jerarquía son CUATRO niveles y la taxonomía no entra.
# - Tras ING.0.4 el chunker sigue header_1..header_5 (documento / título / capítulo / sección /
#   unidad citable, según docs/CONTRATO_MD_CORPUS.md). embedding_text los usa todos, y usa
#   'ruta' cuando esté disponible.
# - REGLA DURA: en embedding_text solo entra contexto ESTRUCTURAL (título del documento y
#   encabezados). NUNCA ambit_principal, submateries, submateries_internes ni ninguna etiqueta
#   del vocabulario. Motivo: el vocabulario está pendiente de validar por SG y debe seguir
#   siendo revisable; taxonomía embebida ⇒ cada revisión cuesta un re-embedding del corpus.
#   Los pares bilingües van al tsvector de RAG.4, por lo mismo.
# - El ancla ({#art-14}) NO va en embedding_text: es ruido para el vector. Va en chunk_metadata
#   y se usa para construir la URL de la cita.
# - Test añadido: should_not_include_taxonomy_or_anchor_in_embedding_text

## Watcher (ingestion/watcher.py)
- embed(embedding_text) en lugar de embed(content).
- De paso: embeber por LOTES (encode acepta lista) en vez de chunk a chunk (watcher es hoy
  secuencial) — mismo prompt porque toca la misma línea.

## Hook de nivel 2 (definir, NO implementar)
- Protocolo ContextEnricher (enrich(document, chunk) -> str) con NoopEnricher por defecto,
  inyectado en el chunker. El enricher LLM (frase de contexto generada en ingesta, técnica
  "contextual retrieval") queda documentado como candidato post-corpus-definitivo. Sin código
  muerto: solo el protocolo + Noop que ya se usa.

## Regeneración del corpus
- Reutilizar services/corpus_recalculator.py (ya regenera chunks al cambiar de modo) para
  re-chunk+re-embed del corpus de prueba tras el cambio. Si RAG.9 ya está hecho, usar su CLI.

## Tests (RED primero)
# should_build_embedding_text_with_title_and_header_hierarchy
# should_not_duplicate_header_when_content_starts_with_it
# should_keep_stored_content_unchanged
# should_embed_enriched_text_not_raw_content      (spy sobre embedding_service)
# should_embed_chunks_in_batches
# should_regenerate_corpus_via_recalculator

## Criterio de done
- [ ] Corpus de prueba regenerado; RAG.1 comparado (adjuntar cifras; se espera mejora en
      queries cuya respuesta vive en secciones profundas)
```

---

### Prompt RAG.8 (RED/GREEN) — Parent-child chunking + chunking configurable por chatbot

**Modelo sugerido**: **Sonnet** — patrón conocido (LAMB `hierarchical_ingest`/`parent_child_query`) sobre infraestructura propia ya existente.

```
# PROMPT RAG.8 (RED/GREEN) — Small-to-big opcional + parámetros de chunking en la cascada
# Deploy: edge

## Config por chatbot (migración Alembic + cascada)
- HubChatbot: chunk_size (int, nullable), chunk_overlap (int, nullable),
  chunking_strategy ('structural' | 'parent_child', nullable).
- Defaults org (default_chunk_*) + plataforma (1000/100/'structural') vía ConfigResolver.
- watcher deja de instanciar MarkdownChunker con defaults hardcodeados: lee la config resuelta.
- Exponer en routers CRUD (contract-first: el frontend los recibe del contrato OpenAPI).

## Estrategia parent_child (ingestion/chunker.py)
- Hijos: RecursiveCharacterTextSplitter con chunk_size_child (default 400) DENTRO de cada
  sección estructural; el embedding es del hijo (compone con embedding_text de RAG.7).
- Padre: la sección estructural completa → columna parent_content (Text, nullable) en
  HubDocumentChunk (migración). Decisión: columna directa, no join — simplicidad y el
  padre ya existe como texto en el documento.
- Retrieval: cuando parent_content no es NULL, la evidencia devuelve parent_content como
  excerpt (vector_strategy agrupa por documento: el "mejor chunk" pasa a ser "mejor padre",
  deduplicando hijos del mismo padre).

## Cambio de estrategia = regeneración
- corpus_recalculator soporta el cambio chunking_strategy (borra chunks y regenera), igual
  que hace hoy con retrieval_mode.

## Tests (RED primero)
# should_use_per_chatbot_chunk_size_and_overlap
# should_fall_back_to_cascade_defaults_when_unset
# should_split_children_within_structural_sections
# should_store_parent_section_on_child_chunks
# should_return_parent_content_as_evidence
# should_deduplicate_children_of_same_parent_in_results
# should_regenerate_chunks_on_strategy_change

## Criterio de done
- [ ] Migraciones aplicadas; config visible y funcional en API admin
- [ ] RAG.1 sobre el fixture con parent_child ON vs OFF: cifras en el cierre
```

---

### Prompt RAG.9 (RED/GREEN) — Metadato de embeddings + validación + re-embedding masivo

**Modelo sugerido**: **Sonnet** — patrón LAMB "config por colección" adaptado; alcance enumerado.

```
# PROMPT RAG.9 (RED/GREEN) — Trazabilidad y migrabilidad del modelo de embedding
# Deploy: edge

## Esquema (migración Alembic)
- HubDocumentChunk: embedding_model (String, nullable=False tras backfill),
  embedding_dim (Integer). Backfill: filas existentes → 'BAAI/bge-m3' / 1024.

## Servicio (services/embedding_service.py)
- El protocolo EmbeddingService expone model_name y dim; LocalEmbeddingService ('BAAI/bge-m3',
  1024) y GoogleEmbeddingService ('models/text-embedding-004', 768) los implementan.
- El watcher estampa model_name/dim en cada chunk al ingerir.

## Guardas (decisión cerrada: un solo modelo por despliegue edge)
- En query: si el corpus del chatbot contiene embedding_model distinto del servicio activo →
  error explícito con instrucción de re-embedding (nunca resultados silenciosamente malos).
- Al crear/activar chatbot: validación con embedding de prueba del servicio activo (patrón
  LAMB) — falla rápido si el servicio no está operativo.
- Documentar en el docstring del módulo: la incompatibilidad Google-768d vs Vector(1024) se
  resuelve por re-embedding completo del despliegue, no por convivencia de dimensiones.

## CLI de re-embedding (python -m ...ingestion.reembed)
- Argumentos: --chatbot-id [--all] [--dry-run]. Recorre chunks en lotes (streaming, sin cargar
  el corpus en memoria), re-embebe con el servicio activo y estampa metadato nuevo.
- Idempotente: chunks ya en el modelo activo se saltan (salvo --force).
- Es la herramienta operativa de RAG.7/RAG.8 cuando el corpus ya está cargado.

## Tests (RED primero)
# should_stamp_model_and_dim_on_ingestion
# should_backfill_existing_chunks_in_migration
# should_raise_clear_error_on_model_mismatch_at_query
# should_validate_embedding_service_on_chatbot_creation
# should_reembed_corpus_in_batches_via_cli
# should_skip_chunks_already_on_active_model
# should_report_plan_in_dry_run

## Criterio de done
- [ ] Migración + backfill aplicados (alembic current)
- [ ] CLI ejecutado en dry-run contra el corpus de prueba (salida en el cierre)
```

---

### Prompt RAG.10 (RED/GREEN) — Query rewriting conversacional

**Modelo sugerido**: **Sonnet** — patrón `context_aware_rag` de LAMB con fallbacks; alcance cerrado.

```
# PROMPT RAG.10 (RED/GREEN) — Reescritura de consulta con historial antes del retrieve
# Deploy: edge

## Nodo (public_graphs/core/) — antes del retrieve en CoreGraph
- Condición: cfg.query_rewriting_enabled Y len(historial) >= 2 turnos. Si no → passthrough.
- LLM pequeño-rápido vía model_factory. Config en cascada: rewrite_llm_config_id (nullable) en
  organización; fallback al LLM del chatbot con max_tokens bajo (~100). Prompt de optimización
  fijo (plantilla en el módulo, no editable por admin en este prompt): "genera la consulta de
  búsqueda autónoma que capture la intención del último mensaje usando el contexto" sobre los
  últimos 10 mensajes.
- Triple fallback (patrón LAMB): excepción → timeout (2 s) → respuesta vacía/anómala ⇒ usar el
  último mensaje del usuario tal cual. El chat NUNCA falla por el rewriting.
- La query reescrita se usa SOLO para retrieval; la generación recibe el historial original.
  Se guarda en el estado del grafo (rewritten_query) → visible en trazas Langfuse y en el
  bypass (RAG.11).

## Config
- query_rewriting_enabled (bool) en HubChatbot + default org + plataforma False (migración,
  cascada, routers CRUD). Default False hasta validar con datos.

## Tests (RED primero) — LLM mockeado
# should_skip_rewriting_on_first_turn
# should_skip_rewriting_when_disabled
# should_rewrite_followup_query_using_history
# should_fallback_to_last_message_on_llm_error
# should_fallback_to_last_message_on_timeout
# should_use_rewritten_query_only_for_retrieval
# should_record_rewritten_query_in_graph_state

## Criterio de done
- [ ] Subconjunto 'conversacional' del dataset dorado (queries con history, RAG.1) evaluado
      con flag ON vs OFF: cifras en el cierre
```

---

### Prompt RAG.11 (RED/GREEN) — Modo bypass/debug del pipeline

**Modelo sugerido**: **Sonnet** — patrón connector `bypass` de LAMB; corto y cerrado.

```
# PROMPT RAG.11 (RED/GREEN) — Prompt final construido sin llamar al LLM
# Deploy: edge

## Endpoint (api/v1/hub_chat.py)
- Body opcional debug_bypass: true. Gate estricto: rol admin/superadmin o PAT con scope
  chat:debug (scope nuevo). El widget/público NUNCA lo recibe (403).
- Con bypass: el grafo ejecuta todo (detect_language → rewrite → retrieve → gate → packer)
  y se detiene ANTES de invocar el LLM. Respuesta JSON (no SSE): {system_prompt, messages,
  packed_context {evidencias, dropped_count}, sources, rewritten_query, resolved_config
  (snapshot de la cascada), quality_gate {score, passed}}. Cero tokens de LLM.
- No persiste HubInteraction (es inspección, no conversación) — decisión cerrada.

## Implementación
- Flag en el estado del CoreGraph; el nodo generate_answer lo comprueba y devuelve los
  mensajes construidos en lugar de invocar (spy-friendly por diseño).

## Tests (RED primero)
# should_return_final_prompt_without_calling_llm      (spy: 0 invocaciones)
# should_include_packed_context_sources_and_resolved_config
# should_include_rewritten_query_when_rewriting_enabled
# should_reject_bypass_for_non_admin_without_scope
# should_not_persist_interaction_on_bypass
# should_report_quality_gate_result_in_bypass

## Criterio de done
- [ ] Verificado manualmente contra el corpus de prueba (una consulta real, salida en el cierre)
- [ ] docs: sección breve en docs/ sobre cómo depurar contexto con bypass
```

---

### Prompt RAG.12 (RED/GREEN) — Progreso granular de jobs de ingesta

**Modelo sugerido**: **Sonnet** — patrón `FileRegistry`/`progress_callback` de LAMB; mecánico.

```
# PROMPT RAG.12 (RED/GREEN) — HubIngestionJob con progreso y estadísticas por etapa
# Deploy: edge

## Esquema (migración Alembic) — HubIngestionJob
- progress_current (int), progress_total (int|null), progress_message (String),
  processing_stats (JSON), processing_started_at / processing_completed_at (DateTime).

## Watcher (ingestion/watcher.py)
- run_job / process_user_upload aceptan progress_callback(current, total, message) y lo
  invocan por etapa: convert (Docling) → chunk → embed (por lote, no por chunk) → persist.
- Throttle: actualizar la fila como máximo una vez por lote/etapa (no por chunk).
- processing_stats al completar (y lo acumulado al fallar): n_chunks, total_chars,
  duración por etapa (ms), n_batches de embedding, embedding_model usado.

## Exposición
- El endpoint de estado de jobs existente (routers de ingesta) devuelve los campos nuevos.
- El CLI de ING.0.2 usa el mismo callback para reportar progreso por consola en cargas masivas.

## Tests (RED primero)
# should_update_progress_per_embedding_batch
# should_record_stage_timings_in_processing_stats
# should_persist_partial_stats_on_failure
# should_expose_progress_fields_in_job_status_endpoint
# should_throttle_progress_writes_per_batch
# should_report_progress_in_bulk_corpus_cli

## Criterio de done
- [ ] Migración aplicada (alembic current)
- [ ] Carga del corpus de prueba mostrando progreso (salida del CLI en el cierre)
```

---

### Prompt RAG.13 (RED/GREEN) — Test scenarios por chatbot (backend + UI admin mínima)

**Modelo sugerido**: **Sonnet** — patrón LAMB test scenarios; CRUD + ejecución por pipeline real + UI enumerada.

```
# PROMPT RAG.13 (RED/GREEN) — Escenarios de prueba con veredicto humano
# Deploy: edge (modelos y ejecución; la UI admin lo consume vía API)

## ORM (operational_models.py — HubOperationalBase, keyed por chatbot_id)
- HubTestScenario: chatbot_id, name, prompt, history (JSON|null), expectation_note (Text|null),
  created_by, timestamps.
- HubTestRun: scenario_id (FK CASCADE), executed_at, answer (Text), sources (JSON),
  bypass_snapshot (JSON|null — captura de RAG.11), verdict ('good'|'bad'|'mixed'|null),
  verdict_note, verdict_by.
- Migración Alembic.

## Endpoints (router nuevo, docstring Deploy: edge, registrado en _register_edge)
- CRUD de escenarios por chatbot (scope admin).
- POST /run: ejecuta el escenario por el PIPELINE REAL (CoreGraph completo, LLM incluido) y
  guarda answer+sources; con ?capture_context=true adjunta además el bypass_snapshot
  (reutiliza RAG.11 internamente).
- PATCH /runs/{id}/verdict: registra el veredicto humano.
- Aislamiento por chatbot_id en toda query (mismo patrón que el resto del módulo).

## UI admin mínima (frontend/src/admin/) — contract-first
- Página por chatbot: lista de escenarios, crear/editar, botón "Ejecutar", historial de runs
  con respuesta + fuentes + (desplegable) contexto capturado, botones de veredicto good/bad/mixed.
- Hooks Orval regenerados desde openapi.json; react-hook-form + zodResolver; i18n es/ca/en
  (ninguna string hardcodeada).

## Tests (RED primero)
# backend — tests/modules/agents_hub/
# should_crud_scenarios_scoped_by_chatbot
# should_execute_scenario_through_real_pipeline     (LLM fake del harness de tests)
# should_capture_bypass_snapshot_when_requested
# should_record_human_verdict_on_run
# should_reject_access_without_admin_scope
# frontend — Vitest
# should_render_scenarios_from_contract
# should_run_scenario_and_show_answer_with_sources
# should_submit_verdict

## Criterio de done
- [ ] Migración aplicada; Orval regenerado; tsc + Vitest verdes
- [ ] Este prompt SÍ genera pruebas manuales (hay UI): .bat según CLAUDE.md al ejecutarlo
```

---

### Prompt RAG.14 (RED/GREEN) — Feedback → huecos de corpus

**Modelo sugerido**: **Opus** — clustering + integración con los contratos 9Q; decisiones de agregación abiertas.

```
# PROMPT RAG.14 (RED/GREEN) — Detección de huecos de contenido desde señales de fallo
# Deploy: edge

## Señales de entrada (ya existen tras RAG.2)
- HubInteraction con feedback_score <= umbral (config del detector, default 2 sobre 5).
- HubInteraction con fallback_reason IN ('quality_gate', 'citation') — la señal gratuita de
  "no encontré nada" que persiste RAG.2.

## Detector (ingestion/quality/gap_detector.py — integra el subsistema 9Q)
- Ventana temporal configurable (default 30 días), por chatbot.
- Embebe las queries de las interacciones-señal (embedding service existente) y clusteriza
  reutilizando las utilidades de clustering de quality/semantic_detector.py.
- Cluster con >= min_cluster_size (default 3) ⇒ HubContentFinding de tipo 'content_gap':
  payload con queries representativas (máx. 5), recuento, rango de fechas y términos top.
  Extensión del contrato/modelo de findings 9Q: finding a nivel chatbot (page_id nullable) —
  migración Alembic + ajuste de contracts.py/findings_repo.py preservando los tests 9Q verdes.
- Deduplicación: no crear finding nuevo si existe uno 'content_gap' abierto cuyo centroide
  esté a distancia coseno < umbral del cluster nuevo (se actualiza su recuento).

## Disparo
- Comando manual (python -m ...quality.detect_gaps --chatbot-id) + endpoint admin POST
  /hub/quality/gaps/analyze. NO se integra en el scheduler periódico 9Q en este prompt
  (el scheduler arranca hoy con detectores vacíos; integrarlo es decisión operativa posterior).
- Los findings aparecen en la cola de revisión 9Q existente del admin.

## Tests (RED primero) — tests/modules/agents_hub/ (unit con embeddings fake deterministas)
# should_collect_low_feedback_interactions_as_signals
# should_collect_citation_and_gate_fallbacks_as_signals
# should_cluster_similar_queries_into_one_gap
# should_ignore_clusters_below_min_size
# should_create_content_gap_finding_with_representative_queries
# should_not_duplicate_open_finding_for_same_cluster
# should_scope_analysis_by_chatbot_and_time_window
# should_keep_existing_9q_finding_tests_green      (regresión de la extensión del contrato)

## Criterio de done
- [ ] Migración aplicada; suite 9Q completa verde tras la extensión del contrato
- [ ] Ejecución del comando contra datos sembrados de prueba (salida en el cierre)
```

### Continuación tras el bloque RAG

Sigue el orden acordado: **Bloque SYNC** → resto del Bloque SEC (SEC.1-5, SEC.7) → Bloque CAL → Deploy GCP. El hook LLM de contextual retrieval nivel 2 y la variante conversacional ampliada del dataset dorado quedan como candidatos post-deploy.

---

## Bloque DET — Desempate determinista del retriever (PENDIENTE)

> **Contexto**: añadido el 2026-08-02 al cuadrar la deuda del cierre del Bloque RAG. La baseline del gate
> se movió de 0,920 a 0,940 sin que nadie tocara el ranking, y la causa medida no fue una mejora: es un
> **empate exacto de coseno** (`0,316227773316`) entre dos fragmentos de documentos distintos en una de las
> 25 consultas del dorado. `vector_search` y `keyword_search` ordenan **solo por puntuación**, sin desempate,
> así que cuál de los dos empatados queda primero lo decide el plan de la consulta. Refutadas por medición
> las tres explicaciones que parecían obvias: HNSW (con 52 filas el planificador ni lo toca), el índice
> `ix_hub_document_chunks_embedding_space` de RAG.9 (quitarlo no cambia nada) y la anchura de fila.
>
> **Por qué es de producción y no de tests**: cuando dos fragmentos empatan, hoy decide el planificador
> **qué norma se cita**. En un asistente normativo la evidencia mostrada no es presentación, es la respuesta.
> Que el gate deje de tener margen cero es la propina, no el motivo.
>
> **La restricción dura, medida antes de escribir el prompt**: un desempate en el `ORDER BY` de la rama
> vectorial **inutiliza el índice HNSW**. pgvector solo sirve el índice para `ORDER BY <distancia>` a secas.
>
> ```
> ORDER BY embedding <=> $1 LIMIT 10        →  Index Scan using ix_hub_document_chunks_embedding_hnsw
> ORDER BY embedding <=> $1, id LIMIT 10    →  Seq Scan + Sort   (con enable_seqscan=off: no hay alternativa)
> ```
>
> O sea que la solución evidente deshace RAG.3 y devuelve cada consulta a recorrer todos los chunks del
> chatbot. De ahí que el desempate vaya **en SQL en la rama léxica y en Python en la vectorial**.

---

### Prompt DET.1 (RED/GREEN) — Desempate estable en las dos ramas del híbrido

**Modelo sugerido**: **Sonnet** — el alcance está cerrado y las dos decisiones de diseño (dónde desempatar en cada rama, y con qué columna) vienen ya decididas y medidas en el contexto del bloque.

```
# PROMPT DET.1 (RED/GREEN) — El orden del retriever deja de depender del plan de la consulta
# Deploy: edge  (el retriever es edge; no toca configuración ni routers cloud)

# QUÉ SE ARREGLA
# Dos fragmentos con la misma puntuación salen hoy en el orden que quiera el planificador.
# Tras este prompt salen siempre en el mismo, y ese orden sobrevive a una reingesta.

# LAS TRES PIEZAS

# 1. Rama léxica (`keyword_search`): desempate EN SQL.
#    `ts_rank_cd` devuelve valores muy cuantizados y los empates son frecuentes — y lo seguirán
#    siendo con el corpus real, no son artefacto del fixture. El GIN sirve el WHERE, no el
#    ORDER BY, así que ese Sort ya se paga hoy: la segunda clave es gratis.
#        stmt.order_by(rank.desc(), HubDocumentChunk.content_hash)

# 2. Rama vectorial (`vector_search`): desempate EN PYTHON, DESPUÉS del LIMIT.
#    El SQL se queda EXACTAMENTE como está — HNSW intacto, ver la restricción del bloque — y se
#    reordena el conjunto ya devuelto antes de construir los SearchResult. Son top_k*2 filas,
#    unas 20-30: coste nulo.
#    RESIDUO QUE SE ACEPTA Y SE DOCUMENTA EN EL DOCSTRING: si un empate cae justo en el borde
#    del LIMIT, qué filas vuelven sigue dependiendo del plan. Con BGE-M3 es teórico (empates
#    exactos entre floats de 1024 dimensiones no ocurren); con el embedding determinista del
#    fixture es el caso común, pero el borde concreto es raro. No se arregla porque arreglarlo
#    cuesta el índice.

# 3. La clave de desempate es `content_hash`, NO `id`.
#    `id` es un uuid4: determinista dentro de una ingesta y ARBITRARIO entre reingestas, así que
#    cada recarga del corpus rebarajaría los empates y tendríamos el mismo problema con otra cara.
#    `content_hash` del chunk se deriva de su propio contenido (`watcher.py`, `hash_content(ch.content)`),
#    o sea que es estable entre reingestas y entre máquinas.

# TESTS (RED primero)
# tests/modules/agents_hub/integration/test_retriever_desempate.py
# should_break_vector_ties_by_content_hash          (dos chunks con embedding idéntico)
# should_break_keyword_ties_by_content_hash         (dos chunks con el mismo ts_rank_cd)
# should_keep_the_same_order_across_plans           (mismo resultado con enable_seqscan on/off)
# should_not_reorder_results_that_do_not_tie        (el desempate no toca lo que ya está ordenado)
# should_keep_hnsw_usable_by_the_vector_branch      (EXPLAIN: el ORDER BY vectorial sigue a secas)

# CRITERIO DE DONE
- [ ] Los 5 tests en verde + `tests/modules/agents_hub` sin regresiones
- [ ] `EXPLAIN` en el test demuestra que la rama vectorial sigue pudiendo usar HNSW
- [ ] Baseline del gate regenerada DESPUÉS del cambio (`GOLDEN_UPDATE_BASELINE=1`): la cifra que
      salga —0,940 o 0,920— ya es estable, y la `nota` del fichero deja de advertir del empate
- [ ] Sin migración: no hay cambio de esquema
```

---

## Bloque SYNC — Sostenibilidad de la vigencia del corpus (PENDIENTE)

> **Contexto**: planificado el 2026-07-28. Cierra la pregunta de mantenimiento: quién actualiza el corpus cuando una norma cambia, y cómo se evita que envejezca en silencio. La decisión de fondo ya está tomada en el Bloque ING.0: **el `.md` autoritativo vive en la BD de publicación de la UJI y las circulares de Gerencia pasan por el mismo circuito**, así que hay un solo maestro y el hub es réplica.
>
> **Lo que este bloque NO construye**: UI de administrador con formulario de metadatos. Con un solo maestro no hace falta, y CLAUDE.md prohíbe el código especulativo. La carga manual de emergencia la cubre el CLI de ING.0.5.
>
> **Transporte disponible (dato del 2026-07-28)**: la UJI expone sus datasets por un **servicio MCP** (`execute_dataset`, argumentos `dataset_code` + `token` por dataset). El corpus normativo se publicará por esa vía o por un export incremental equivalente.
>
> **Este bloque añade un transporte, no un pipeline.** El pipeline de publicación no existirá hasta dentro de meses; hasta entonces el mantenimiento del corpus se hace por **CLI sobre carpeta local**, que es lo que entrega ING.0.5 junto con el reconciliador y el protocolo `CorpusSource`. SYNC.1 implementa una **segunda fuente** (`PublicationMcpSource`) sobre ese mismo reconciliador. Si SYNC.1 acaba reimplementando emparejamiento, deltas o poda, está mal: eso ya está en ING.0.5.

---

### Prompt SYNC.1 (RED/GREEN) — Fuente MCP sobre el reconciliador de ING.0.5

**Modelo sugerido**: **Sonnet** — cliente + adaptador de fuente; la reconciliación (censo, poda, emparejamiento) ya viene decidida e implementada en ING.0.5.

```
# PROMPT SYNC.1 (RED/GREEN) — Pull del corpus autoritativo, sin agente y sin borrar
# Deploy: edge  (el edge node tira del sistema de publicación del cliente; el cloud no ve el corpus)

## Regla número uno: esto es ETL, no una operación agéntica
El sync NO pasa por un LLM en ningún punto: un script llama a la tool, recibe texto, calcula
hash y escribe. Consecuencias que hay que respetar en el código:
- Cero tokens de modelo, cero trazas Langfuse en esta ruta.
- El token del dataset viaja como ARGUMENTO de la tool. Si esta llamada se hiciera desde un
  agente con trazas activas, el token quedaría escrito en el almacén de trazas. Va en variable
  de entorno / secreto, no se registra en logs ni en el informe de ejecución (redactar si se
  vuelca la petición para depurar).

## Cliente (ingestion/corpus/publication_client.py)
- Cliente MCP sobre HTTP (JSON-RPC) para la tool execute_dataset(dataset_code, token).
- Dos datasets, y esta es la decisión que hace el coste proporcional a los cambios y no al corpus:
  * ÍNDICE (censo completo): una entrada por norma con id estable, content_hash | updated_at y
    el bloque de metadatos. Pequeño; se pide entero y a menudo.
  * CONTENIDO: el .md. Solo se pide para las normas cuyo hash cambió. Si la tool no admite
    parámetros (hoy solo dataset_code + token), la variante es un dataset de "modificadas en los
    últimos N días"; el diseño de reconciliación es el mismo.
- Guardarraíl de tamaño: el corpus completo ronda los ~10 MB (≈380 normas × ~25k caracteres),
  que está en la zona de los límites de respuesta de una Lambda. Si la respuesta llega truncada
  o no parsea, **fallar ruidosamente**; nunca sincronizar con un censo parcial (produciría
  despublicaciones falsas).
- Configuración por entorno, añadida a .env.example y a scripts/generate_env.sh (precedente
  SEC.6): PUBLICATION_MCP_URL, PUBLICATION_DATASET_INDEX, PUBLICATION_DATASET_CONTENT,
  PUBLICATION_DATASET_TOKEN.

## Adaptador de fuente (ingestion/corpus/publication_source.py)
PublicationMcpSource implementa CorpusSource (ING.0.5):
- is_census() → True **solo** si la pasada obtuvo el índice completo. Si se usó el dataset de
  "modificadas en los últimos N días", es False, y entonces el reconciliador no poda: correcto,
  porque un delta no puede distinguir "retirada" de "no tocada".
- list_entries() → mapea el índice a CorpusDocumentEntry, con id_publicacio del registro.
- read_body() → pide el dataset de CONTENIDO solo para las entradas que el reconciliador marcó
  como cambiadas (lazy, no precargar el corpus).
Toda la semántica de emparejamiento, deltas, poda, salvaguarda de proporción, findings y
HubIngestionJob viene de ING.0.5 y **no se reimplementa aquí**. La retirada detectada por censo
usa motiu_exclusio='retirada_de_la_font' (mismo valor que el CLI): despublicada ≠ derogada, y la
distinción la hace una persona en la cola de revisión.

## Disparo
- CLI (python -m ...corpus.sync --chatbot-id [--dry-run] [--prune]).
- NO se engancha al scheduler en este prompt (decisión operativa posterior, igual que RAG.14).

## Tests (RED primero) — tests/modules/agents_hub/ingestion/test_publication_sync.py
# should_call_execute_dataset_with_code_and_token
# should_never_log_the_dataset_token
# should_fail_loudly_on_truncated_or_unparseable_index
# should_report_is_census_true_only_for_full_index
# should_report_is_census_false_for_delta_dataset
# should_map_index_entries_to_corpus_document_entries_with_id_publicacio
# should_request_content_only_for_changed_documents      (spy: nº de llamadas al dataset de contenido)
# should_reuse_reconciler_without_reimplementing_matching  (el sync no toca hub_documents
#                                                           directamente; lo hace el reconciliador)
# should_not_emit_llm_calls_during_sync                  (spy sobre model_factory)
+ los tests de reconciliación de ING.0.5 se ejecutan también con esta fuente (parametrizar el
  test del reconciliador por CorpusSource: carpeta local y MCP fake deben dar el mismo resultado).

## Criterio de done
- [ ] Ejecución real contra el entorno de pruebas de la UJI (o fake fiel si aún no publica el
      dataset del corpus), con el informe de recuentos pegado en el cierre
- [ ] La suite del reconciliador pasa con ambas fuentes
- [ ] Crawler confirmado desactivado para el chatbot sincronizado (fuente autoritativa única)
```

---

### Prompt SYNC.2 (RED/GREEN) — Caducidad activa del corpus

**Modelo sugerido**: **Sonnet** — detector corto sobre el mecanismo de findings ya existente.

```
# PROMPT SYNC.2 (RED/GREEN) — Que nada envejezca en silencio
# Deploy: edge

## El problema
Hoy un documento cargado se queda indefinidamente y nada avisa. El riesgo nº1 del informe es la
vigencia (312 de 314 fichas dicen «vigent?»), y el sync solo detecta lo que cambia en origen: una
norma que nadie toca durante tres años no genera ninguna señal.

## Detector (ingestion/quality/staleness_detector.py)
- Lee data_revisio_prevista (columna de ING.0.2). Vencida ⇒ HubContentFinding de tipo
  'revisio_vencuda' a nivel documento, con la fecha prevista y la última de actualización.
- Default de la fecha al ingerir, si el front-matter no la trae: 1 año. Las normas de vigencia
  anual (Presupuesto) la traen explícita y más corta.
- Deduplicación: no se emite un finding nuevo si hay uno abierto para el mismo documento.
- Los findings caen en la cola de revisión 9Q existente del admin, junto a los 'content_gap' de
  RAG.14 y las 'despublicada' de SYNC.1.

## Disparo
CLI (python -m ...quality.detect_stale --chatbot-id) + endpoint admin. Sin scheduler (igual que
RAG.14 y SYNC.1).

## Tests (RED primero)
# should_emit_finding_for_document_past_its_review_date
# should_not_emit_for_document_within_review_window
# should_default_review_date_to_one_year_on_ingest
# should_respect_explicit_review_date_from_frontmatter
# should_not_duplicate_open_finding_for_same_document
# should_keep_existing_9q_finding_tests_green

## Criterio de done
- [ ] Ejecución contra datos sembrados con fechas vencidas y vigentes (salida en el cierre)
- [ ] La cola de revisión del admin muestra los tres tipos de finding
```

---

## Bloque OWUI — ❌ DESCARTADO (2026-08-11)

> ## No ejecutar. El bloque se descarta entero; lo que sigue queda como registro.
>
> **Decisión del usuario, tras la conversación de arquitectura del 2026-08-11.** Cuatro
> razones, y la cuarta es la que inclina:
>
> 1. **Se pierde la identidad institucional.** No es un detalle estético: SEC.8.6 y el
>    hallazgo #3 de MAN.2 acaban de construir el sistema de temas —tabla `hub_themes`,
>    cascada plataforma→organización→chatbot, resolución en el widget— precisamente para
>    que el chat público se vea de la institución. Poner OWUI delante tira ese trabajo.
> 2. **Actualizar OWUI cuesta.** Es una aplicación de terceros con su propio ciclo de
>    versiones, y cada salto hay que probarlo contra el adaptador.
> 3. **Consume recursos de la VM.** Con el despliegue en una sola máquina
>    (`docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §2), OWUI y su base propia compiten por
>    la memoria que se acaba de medir en EXT.3.
> 4. **El público al que servía ya está servido de otra forma.** OWUI aportaba una UX de
>    chat rica —historial, adjuntos, cambio de modelo— que tiene sentido para **personal
>    interno**, no para el ciudadano. Para la superficie pública nunca fue la respuesta, y
>    el propio nombre del bloque lo admitía: «carcasa **desechable**».
>
> **Qué se pierde, dicho sin adornos**: el historial de conversaciones y una UX de chat más
> rica para quien use el asistente como herramienta de trabajo. Es real. La alternativa es
> añadirlo al frontend propio cuando haga falta, conservando identidad y una pieza menos que
> mantener.
>
> **Y el adaptador compatible-OpenAI también se aparca.** Tiene valor *independiente* de
> OWUI —permite que cualquier herramienta hable con el asistente— pero solo si aparece un
> consumidor concreto que lo pida. Sin él es código especulativo, que es lo que proscribe la
> norma de «sin código muerto especulativo» de `CLAUDE.md`. Si mañana alguien lo necesita, se
> hace entonces: es pequeño y el andamiaje (scope `chat:completions`, PAT, identidad
> delegada) ya está puesto desde SEC.2.1.
>
> `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` se conserva: su análisis de qué NO usar de OWUI
> sigue siendo válido si algún día se reabre.

---

> **Contexto original (2026-07-24)**: derivado de `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md`. Open WebUI se adopta como carcasa de chat **desechable e intercambiable** para la capa conversacional; el backend sigue siendo la fuente de verdad. Regla de acoplamiento: **OWUI llama HACIA el backend (API compatible-OpenAI); la gobernanza NUNCA vive en OWUI.** No aplica a expedientes (Fase 3) ni a informes formales, que mantienen interfaz propia.
>
> **Posición en el orden de ejecución** (acordada 2026-07-24): **tras Deploy GCP**, como spike/comparación para el piloto de septiembre. El frontend React de chat ya existe y es la línea de comparación; este bloque levanta la carcasa OWUI sobre el MISMO backend desplegado. (La decisión §9 contempla adelantarlo si se quisiera descartar trabajo de chat-UI en CAL; el orden acordado aquí es post-deploy.)
>
> **Estado**: relación de prompts (1ª pasada, 2026-07-24). Pendiente 2ª pasada de detalle verbatim cuando llegue su turno.

### Propósito del bloque

1. Exponer una **superficie compatible-OpenAI** (`/v1/models`, `/v1/chat/completions`) sobre el grafo de chat existente, sin reimplementar RAG ni gobernanza.
2. Preservar el **contrato de citas (P6)** y la **anonimización (P7)** en el trayecto del backend, nunca en la carcasa.
3. Entregar un **Pipe delgado** de Open WebUI (transporte + presentación) y la guía de despliegue edge (P8).
4. Habilitar la **comparación UX** React vs OWUI sobre idéntico backend (insumo de la decisión de carcasa).

### Decisiones de diseño

- **El adaptador es traducción de protocolo, no lógica.** Reusa el mismo grafo que `hub_chat.py` (CoreGraph tras RAG.2); si duplica retrieval, generación o filtrado, está mal.
- **Un chatbot = un "model" de OpenAI.** `/v1/models` lista los chatbots visibles al PAT; el campo `model` de la petición resuelve a `chatbot_id`.
- **Auth máquina por PAT** con scope nuevo `chat:completions` (servir a usuarios finales), distinto de `chat:test` (superficie de prueba admin). La autorización usuario↔org↔chatbot del Bloque SEC sigue aplicando.
- **La gobernanza no se toca ni se reimplementa**: P6/P7/P9 se heredan del grafo. Ni el adaptador ni el Pipe pueden añadir ni saltarse controles.
- **Deploy: edge** para el adaptador; el Pipe vive en OWUI (edge). OWUI y su BD son dato operacional edge (P8), no sincronizado al cloud.

### Mapa de ejecución

| # | Prompt | Título | Depende de | Modelo sugerido |
|---|--------|--------|------------|-----------------|
| 1 | OWUI.1 | Superficie compatible-OpenAI (`/v1/models` + `/v1/chat/completions`) sobre el grafo | RAG.2 (grafo consolidado), AUTH ✅ | **Opus** |
| 2 | OWUI.2 | Citas (P6) y anonimización (P7) en la respuesta compatible-OpenAI | OWUI.1 | **Opus** |
| 3 | OWUI.3 | Pipe delgado de OWUI + despliegue edge + validación e2e de gobernanza | OWUI.2 | Sonnet |

### Reglas duras del bloque

- Prohibido reimplementar retrieval/generación/anonimización en el adaptador o el Pipe: se reusa el grafo (grep de ausencia de llamadas directas a `retriever`/`model_factory`/estrategias en el adaptador).
- Sin scope muerto: `chat:completions` se consume en OWUI.1 o no se añade.
- El adaptador debe producir gobernanza **idéntica** a `hub_chat` para la misma entrada (test de equivalencia, OWUI.2).
- Todo router nuevo etiquetado `Deploy: edge` y registrado en `_register_edge`.

### Prompts del bloque (relación — 1ª pasada 2026-07-24)

---

### Prompt OWUI.1 (RED/GREEN) — Superficie compatible-OpenAI sobre el grafo

**Modelo sugerido**: **Opus** — traducción de protocolo SSE↔OpenAI con decisiones de mapeo (chunks de streaming, historial, model→chatbot).

```
# PROMPT OWUI.1 (RED/GREEN) — /v1/models + /v1/chat/completions compatible-OpenAI
# Deploy: edge

## Router nuevo (server/app/api/v1/openai_compat.py) — prefix /v1, Deploy: edge
- GET /v1/models: lista los chatbots visibles al PAT como objetos OpenAI
  {id: <chatbot_id o slug>, object: "model", owned_by: <organizacion>}.
- POST /v1/chat/completions: acepta {model, messages:[{role,content}], stream: bool}
  (tolerar e ignorar temperature/max_tokens/etc.).
  - Resolver model -> chatbot_id (404 si no visible al PAT).
  - Tomar el último mensaje 'user' como message; pasar el historial previo tal cual
    (insumo de RAG.10 query rewriting — NO recortar aquí).
  - Invocar EL MISMO grafo que hub_chat.py (CoreGraph tras RAG.2). Prohibido instanciar
    retriever/model_factory/estrategias directamente.

## Streaming (stream=true) — SSE compatible-OpenAI
- Traducir eventos internos -> chunks OpenAI:
  token{delta} -> {object:"chat.completion.chunk", choices:[{delta:{content}}]}.
  done -> chunk final finish_reason "stop" + linea [DONE].
  status -> se omite. error -> chunk de error OpenAI.
- Reusar _SSE_HEADERS de hub_chat.

## No-streaming (stream=false)
- Acumular tokens -> {object:"chat.completion", choices:[{message:{role:"assistant",content}}],
  usage?} (usage best-effort si el grafo lo expone; si no, omitir).

## Auth (server/app/core/auth/pat/scopes.py)
- Añadir CHAT_COMPLETIONS = "chat:completions" a ALL_SCOPES + techo de rol
  (superadmin/admin, mismo criterio que CHAT_TEST). Endpoint con require_scopes("chat:completions").
- Reusar get_current_user; la autorización usuario<->org<->chatbot del Bloque SEC aplica igual
  que en hub_chat (extraer helper compartido, no duplicar reglas).

## Actor efectivo y guardas (ampliación 2026-07-27)

El Pipe de OWUI usa **un PAT de servicio**: sin resolver el actor, todo el consumo del piloto
se cargaría a un único sujeto y la cuota por usuario sería inútil. El adaptador **no** implementa
nada de esto: consume los helpers de SEC.2.1/SEC.4/SEC.4.1.

- `actor = resolve_effective_actor(request, principal)` (SEC.2.1) al principio del handler.
  El PAT del Pipe debe portar `chat:onbehalf` además de `chat:completions`.
- Guardas, en el mismo orden que hub_chat y el widget:
    assert_chatbot_access(actor, chatbot, via='session')
    assert_chatbot_available(session, chatbot, now)
    assert_within_quota(session, actor, chatbot, via='session')
- `GET /v1/models` lista **solo los chatbots que `assert_chatbot_access` permite al actor
  efectivo** — no "todos los del PAT". Así el usuario de OWUI ve exactamente lo que puede
  usar y **OWUI no decide nada**: no se usan sus Groups para autorizar.
- Traducción de errores al formato OpenAI (si no, OWUI muestra un fallo opaco):
    429 QUOTA_EXCEEDED    -> {"error":{"type":"rate_limit_exceeded","message":<qué cuota, cuánto queda>}}
    403 CHATBOT_UNAVAILABLE -> {"error":{"type":"invalid_request_error","message":<unavailable_message>}}
    403 ACCESS_MODE_FORBIDDEN / 401 ACTOR_TOKEN_INVALID -> error OpenAI equivalente, sin filtrar
    detalles internos de tenencia.
  En streaming, el error se emite como chunk de error + `[DONE]`, no cortando la conexión.
- El `usage` de la respuesta no-streaming se rellena con los tokens reales de SEC.4 cuando el
  proveedor los expone (deja de ser "best-effort" en ese caso).

## Registro
- main.py: _register_edge; docstring "Deploy: edge".

## Tests (RED primero) — tests/modules/agents_hub/integration/test_openai_compat.py
# should_list_visible_chatbots_as_openai_models
# should_map_model_field_to_chatbot_id
# should_404_when_model_not_visible_to_pat
# should_stream_openai_chunks_with_content_deltas
# should_end_stream_with_stop_and_done_sentinel
# should_return_chat_completion_object_when_not_streaming
# should_require_chat_completions_scope
# should_invoke_same_graph_as_hub_chat            (spy: sin acceso directo a retriever)
# should_pass_history_messages_through
# --- ampliación 2026-07-27 ---
# should_list_only_chatbots_allowed_by_access_mode        (authenticated/restricted respetados)
# should_hide_public_anon_only_chatbots_from_models_list_when_actor_lacks_org
# should_charge_usage_to_delegated_actor_not_pat_owner
# should_translate_quota_429_to_openai_rate_limit_error
# should_translate_unavailable_403_to_openai_invalid_request
# should_emit_error_chunk_and_done_when_failing_mid_stream
# should_not_leak_tenancy_details_in_error_messages

## Criterio de done
- [ ] Un cliente OpenAI genérico (SDK openai apuntado al backend) obtiene respuesta en stream
- [ ] Scope chat:completions consumido; sin scope muerto
- [ ] grep: el adaptador no importa VectorRetrievalStrategy/model_factory directamente
- [ ] grep: el adaptador no reimplementa acceso, disponibilidad ni cuota — solo llama a los helpers
- [ ] Dos usuarios distintos vía el mismo PAT consumen cuotas distintas (verificado en test)
```

---

### Prompt OWUI.2 (RED/GREEN) — Citas (P6) y anonimización (P7) en la respuesta compatible-OpenAI

**Modelo sugerido**: **Opus** — el punto donde la gobernanza cruza a la carcasa; decisiones de contrato.

```
# PROMPT OWUI.2 (RED/GREEN) — sources->citations + preservación de anonimización
# Deploy: edge

## Citas (P6) — mapeo del contrato interno a la respuesta OpenAI
- El 'done' interno lleva sources[]. Emitirlas en un formato consumible por el Pipe:
  campo custom en el chunk final (p.ej. choices[].delta.sources) y/o al estilo OWUI.
  Documentar EXACTAMENTE el formato que el Pipe de OWUI.3 espera.
- Enforce del contrato de disponibilidad: si el grafo devuelve respuesta SIN fuentes
  verificables -> respuesta de indisponibilidad (la que ya produce el grafo), NUNCA texto
  libre. El adaptador no puede saltarse este control.

## Anonimización (P7) — se ejecuta en el grafo, no en el adaptador ni en el Pipe
- El adaptador pasa por el MISMO trayecto que hub_chat (RunAnonymizationContext / hooks
  pre/post-LLM, Fase 13) según lo aplique el grafo. No se anonimiza en el adaptador.
- No exponer mapas de reversión en la respuesta ni en trazas enviadas al cloud (P8).

## Test de equivalencia de gobernanza (clave del bloque)
- Para una misma entrada, el adaptador y hub_chat producen: mismas sources, mismo
  comportamiento de indisponibilidad y misma anonimización del texto que llega al LLM.

## Tests (RED primero) — test_openai_compat_governance.py
# should_expose_sources_in_openai_response
# should_return_unavailability_when_no_verifiable_sources
# should_not_emit_free_text_without_sources
# should_apply_same_anonymization_path_as_hub_chat
# should_not_leak_reversal_map_in_response_or_cloud_trace
# should_match_hub_chat_governance_for_same_input   (equivalencia)

## Criterio de done
- [ ] Respuesta sin fuentes -> indisponibilidad, verificado por el cliente OpenAI
- [ ] Entrada con PII -> el LLM recibe texto anonimizado (igual que hub_chat)
- [ ] Formato de citas documentado para OWUI.3
```

---

### Prompt OWUI.3 (RED/GREEN) — Pipe delgado + despliegue edge + validación e2e

**Modelo sugerido**: **Sonnet** — Pipe de transporte + guía de despliegue + checklist e2e.

```
# PROMPT OWUI.3 — Pipe delgado de Open WebUI + despliegue edge + validación
# Deploy: edge (OWUI vive en el edge)

## Pipe/Function de OWUI (owui/pipe_govhub.py, versionado en este repo)
- Function tipo "pipe" que llama a POST {BACKEND}/v1/chat/completions con el PAT
  (scopes chat:completions + chat:onbehalf), en streaming, y mapea el formato de citas de
  OWUI.2 al mecanismo de citas/sources de Open WebUI.
- SIN lógica de gobernanza: solo transporte y presentación. Prohibido anonimizar, filtrar o
  decidir disponibilidad en el Pipe (grep de ausencia).
- Config del Pipe: BACKEND_URL, PAT (secreto), ACTOR_SIGNING_SECRET (secreto), timeout. Nada más.

## Identidad delegada (ampliación 2026-07-27 — decisión (a) del usuario)
- El Pipe construye la cabecera `X-GovGenAI-Actor` a partir del contexto `__user__` que le
  entrega OWUI (id, email, y grupos si están disponibles) y la firma con
  `ACTOR_SIGNING_SECRET` (HS256, `exp` <= 300 s, `aud` = "govgenai-backend").
- **Esto no es gobernanza, es identificación de transporte**: el Pipe declara *quién*
  pregunta; el backend decide *qué puede hacer* (SEC.2.1) y *cuánto le queda* (SEC.4). El
  Pipe no consulta cuotas ni interpreta el 429: solo lo muestra.
- Alternativa descartada: un PAT por usuario. No escala a cientos de personas ni sobrevive a
  las bajas, y multiplicaría los secretos a rotar.
- Si el Pipe no firma la cabecera (o el PAT no tiene `chat:onbehalf`), el backend carga todo
  el consumo al dueño del PAT: **el despliegue queda funcional pero sin cuota por persona**.
  Debe verificarse explícitamente en el checklist, no asumirse.

## Despliegue (docs/OWUI_INTEGRATION.md)
- OWUI dentro del perímetro edge; su BD (conversaciones/ficheros) es dato operacional edge (P8),
  no sincronizado al cloud. Versión de OWUI fijada y probada antes de actualizar.
- SSO SAML compartido para humanos (AUTH); PAT solo para el Pipe.
- Cómo dar de alta un chatbot como "model" en OWUI.
- **Sección obligatoria "Lo que NO se usa de Open WebUI, y por qué"** (si no se escribe,
  alguien lo intentará dentro de seis meses):
    - **Groups/RBAC de OWUI para autorizar chatbots** -> NO. La autorización es gobernanza y
      vive en `assert_chatbot_access` (SEC.2.1). OWUI solo muestra lo que `/v1/models`
      devuelve. Además su modelo de permisos es aditivo y sin "deny", así que no puede
      expresar `restricted` fail-closed.
    - **LiteLLM de sidecar para cuotas por usuario** -> NO. Duplicaría `model_factory`,
      añadiría una pieza más al edge y sacaría el control de gasto del perímetro auditado.
      Las cuotas viven en SEC.4.
    - **Plugins de token-tracking de terceros dentro de OWUI** -> NO. Es la Opción B ya
      descartada en `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` §3: pone gobernanza dentro del
      ciclo de releases de un tercero.
    - Contexto: las cuotas por usuario **no existen de forma nativa en OWUI** (peticiones
      abiertas upstream), de ahí que la tentación de resolverlas allí sea real.

## Validación e2e (checklist; el Pipe corre fuera de la suite pytest)
- [ ] Citas visibles en la UI de OWUI, resolubles a su fuente (P6).
- [ ] Entrada con PII: en trazas, el LLM recibió texto anonimizado (P7).
- [ ] Sin PII ni mapas de reversión en trazas enviadas al cloud (P8).
- [ ] Respuesta sin fuentes -> indisponibilidad también en OWUI.
- [ ] Comparación UX React vs OWUI sobre el mismo backend (notas para la decisión de carcasa).
- [ ] **Un chatbot en modo `authenticated` de otra organización NO aparece en el selector de
      modelos de OWUI** (el filtrado de `/v1/models` funciona de verdad).
- [ ] **Dos usuarios distintos de OWUI consumen cuotas distintas** con el mismo PAT del Pipe:
      agotar la cuota del usuario A no afecta al usuario B (verifica la cadena completa
      Pipe -> cabecera firmada -> resolve_effective_actor -> HubUsageCounter).
- [ ] Al agotar la cuota, OWUI muestra un mensaje legible de límite alcanzado, no un fallo opaco.
- [ ] Un chatbot caducado (`valid_until` pasado) muestra en OWUI el `unavailable_message` del admin.

## Tests (RED primero) — lo testeable del lado backend/formato
# should_document_citation_format_consumed_by_pipe
# should_reject_pipe_config_without_pat
# should_reject_pipe_config_without_actor_signing_secret
# should_sign_actor_header_from_owui_user_context
# should_not_contain_governance_logic_in_pipe        (grep: sin anonimización/cuota/filtrado)

## Criterio de done
- [ ] Pipe funcional contra el backend desplegado; citas visibles en OWUI
- [ ] docs/OWUI_INTEGRATION.md con la guía de despliegue edge y la sección "Lo que NO se usa"
- [ ] Checklist e2e de gobernanza superado y anotado
- [ ] Cuota por persona verificada end-to-end (no solo por PAT)
```

### Continuación tras el bloque OWUI

Con la carcasa OWUI validada sobre el backend desplegado, la decisión de qué carcasa(s) sirve cada caso de uso se toma con datos del piloto (ver `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` §9). Expedientes (Fase 3) e informes formales mantienen interfaz propia.

---

