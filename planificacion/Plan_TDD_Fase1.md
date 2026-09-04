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
(Ver §4 de docs/Arquitectura.md para el mapeo completo SuperAdmin←Admin, Admin←Partner, Organización←Cliente.)

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

---

## Los bloques y las fases, un fichero cada uno

Este plan eran **27.449 líneas en un solo fichero**, y eso es lo único del método que no escalaba a
más manos: no se puede revisar en un *pull request*, ni comentar por línea, ni saber por dónde
empezar. Cada bloque y cada fase viven ahora en `planificacion/fase1/`, con su número de orden
delante para conservar la secuencia de lectura —y porque hay **dos** bloques llamados `CUR`, así
que el código solo no identifica un fichero—.

**El contenido no ha cambiado**: el corte se verificó reconstruyendo el original byte a byte antes
de escribir nada. Y las referencias que otros documentos hacen a «`Plan_TDD_Fase1.md` §Bloque XXX»
siguen funcionando: llevan aquí, y aquí está el enlace.

**Para saber cuál toca**, el cursor está en [`PROJECT_STATE.md`](PROJECT_STATE.md). Para saber qué
**garantiza** ya el sistema —que es otra pregunta— está
[`../docs/ESPECIFICACIONES.md`](../docs/ESPECIFICACIONES.md).

| # | Fichero | Sección |
|---|---|---|
| 01 | [`01_FASE_1.md`](fase1/01_FASE_1.md) | FASE 1: Autenticación y Estado del Agente — REDUCIDA |
| 02 | [`02_FASE_2.md`](fase1/02_FASE_2.md) | FASE 2: Base de Datos y Migraciones — PARCIALMENTE REDUCIDA |
| 03 | [`03_FASE_3.md`](fase1/03_FASE_3.md) | FASE 3: Ingestión de Documentos (Asíncrona) |
| 04 | [`04_FASE_4.md`](fase1/04_FASE_4.md) | FASE 4: Agente LangGraph con Herramientas y RAGAS |
| 05 | [`05_FASE_5.md`](fase1/05_FASE_5.md) | FASE 5: API Endpoints y Robustez |
| 06 | [`06_FASE_6.md`](fase1/06_FASE_6.md) | FASE 6: Tests End-to-End y Flujos Completos |
| 07 | [`07_FASE_7.md`](fase1/07_FASE_7.md) | FASE 7: Despliegue y Containerización — REDUCIDA |
| 08 | [`08_FASE_8.md`](fase1/08_FASE_8.md) | FASE 8: Observabilidad y Panel de Feedback |
| 09 | [`09_FASE_9.md`](fase1/09_FASE_9.md) | FASE 9: Frontend React — Admin Hub, Widget y Migración NiceGUI |
| 10 | [`10_BLOQUE_9A.md`](fase1/10_BLOQUE_9A.md) | BLOQUE 9A — Admin Hub |
| 11 | [`11_BLOQUE_9B.md`](fase1/11_BLOQUE_9B.md) | BLOQUE 9B — Grafo Público: Plataforma Multi-organización (Subfase 1.A, PENDIENTE) |
| 12 | [`12_FASE_9B.md`](fase1/12_FASE_9B.md) | FASE 9B: Grafo Público Extensible (CoreGraph + GraphProfiles + RetrievalPipelineFactory) |
| 13 | [`13_BLOQUE_9R.md`](fase1/13_BLOQUE_9R.md) | BLOQUE 9R — Redacción Contract-First: ReportProfiles, UI Contracts y DraftingCoreGraph (Subfase 1.A → 1.C, PENDIENTE) |
| 14 | [`14_FASE_1.C.md`](fase1/14_FASE_1.C.md) | Subfase 1.C — Infraestructura de Diseño y Exportación Avanzada de Informes (PENDIENTE) |
| 15 | [`15_FASE_13.md`](fase1/15_FASE_13.md) | Fase 13 — NER reversible en el flujo de redacción (Subfase 1.C, PENDIENTE) |
| 16 | [`16_FASE_20.md`](fase1/16_FASE_20.md) | Fase 20 reducida — WCAG 2.2 AA transversal (PENDIENTE) |
| 17 | [`17_FASE_10.md`](fase1/17_FASE_10.md) | FASE 10: Sistema de Plantillas y Temas (Chatbots, Panel Admin, Partners y UI Principal) |
| 18 | [`18_BLOQUE_FAQ.md`](fase1/18_BLOQUE_FAQ.md) | Bloque FAQ — Preguntas frecuentes como contenido citable (PENDIENTE) |
| 19 | [`19_BLOQUE_RHR.md`](fase1/19_BLOQUE_RHR.md) | Bloque RHR — Revisión humana de las respuestas del asistente interno (PENDIENTE) |
| 20 | [`20_BLOQUE_COR.md`](fase1/20_BLOQUE_COR.md) | Bloque COR — Un documento, muchos chatbots (❌ DESCARTADO el 2026-08-11, el mismo día que se planificó) |
| 21 | [`21_BLOQUE_DER.md`](fase1/21_BLOQUE_DER.md) | Bloque DER — Deriva entre copias del corpus (PENDIENTE, sustituye al descartado COR) |
| 22 | [`22_BLOQUE_EXT.md`](fase1/22_BLOQUE_EXT.md) | Bloque EXT — Frontera de la extracción: qué entra al corpus y qué es contexto (PENDIENTE, va ANTES de Deploy) |
| 23 | [`23_BLOQUE_REV.md`](fase1/23_BLOQUE_REV.md) | Bloque REV (continuación) — REV.11 a REV.13 (PENDIENTE) |
| 24 | [`24_BLOQUE_MT.md`](fase1/24_BLOQUE_MT.md) | Bloque MT — Multitenencia real: qué está aislado y qué no (PENDIENTE, planificado el 2026-08-23) |
| 25 | [`25_FASE_DEPLOY.md`](fase1/25_FASE_DEPLOY.md) | Fase Deploy — Despliegue Staging GCP (Subfase 1.B, PENDIENTE) |
| 26 | [`26_FASE_DEPLOY.md`](fase1/26_FASE_DEPLOY.md) | Fase Deploy — Paso a producción en GCP |
| 27 | [`27_FASE_13.md`](fase1/27_FASE_13.md) | FASE 13: Privacidad y Anonimización Reversible NER (Zero-Knowledge) |
| 28 | [`28_FASE_20.md`](fase1/28_FASE_20.md) | FASE 20: Accesibilidad WCAG 2.2 AA + Admin Conversacional |
| 29 | [`29_BLOQUE_SBX.md`](fase1/29_BLOQUE_SBX.md) | Bloque SBX — Seguridad de la Información: Sandbox aislado de ejecución de scripts (Subfase 1.B → 1.C, PENDIENTE) |
| 30 | [`30_BLOQUE_9Q.md`](fase1/30_BLOQUE_9Q.md) | Bloque 9Q — Motor de auditoría de sitios web (Subfase 1.A → 1.C, COMPLETO 9Q.0–9Q.9) |
| 31 | [`31_BLOQUE_AUTH.md`](fase1/31_BLOQUE_AUTH.md) | Bloque AUTH — SSO SAML institucional + Personal Access Tokens (adelanto de Subfase 1.B.1, PENDIENTE) |
| 32 | [`32_BLOQUE_MCP.md`](fase1/32_BLOQUE_MCP.md) | Bloque MCP — Servidor MCP stdio para autoría de plantillas y configuración de chatbots (PENDIENTE) |
| 33 | [`33_BLOQUE_ROL.md`](fase1/33_BLOQUE_ROL.md) | Bloque ROL — Renombrado de nomenclatura institucional (Subfase 1.B, PENDIENTE) |
| 34 | [`34_BLOQUE_SEC.md`](fase1/34_BLOQUE_SEC.md) | Bloque SEC — Endurecimiento de seguridad (Subfase 1.B, PENDIENTE, BLOQUEANTE DE DESPLIEGUE) |
| 35 | [`35_BLOQUE_SEC.8.md`](fase1/35_BLOQUE_SEC.8.md) | Bloque SEC.8 — Endurecimiento pre-deploy, segunda auditoría (Subfase 1.B, PENDIENTE, BLOQUEANTE DE DESPLIEGUE) |
| 36 | [`36_BLOQUE_SEC.9.md`](fase1/36_BLOQUE_SEC.9.md) | Bloque SEC.9 — Endurecimiento pre-deploy, tercera auditoría (Subfase 1.B, PENDIENTE, BLOQUEANTE DE DESPLIEGUE) |
| 37 | [`37_BLOQUE_AIS.md`](fase1/37_BLOQUE_AIS.md) | Bloque AIS — Aislamiento del núcleo y saneamiento previo al piloto (Subfase 1.B, PENDIENTE) |
| 38 | [`38_BLOQUE_CAL.md`](fase1/38_BLOQUE_CAL.md) | Bloque CAL — Deuda de calidad previa al repositorio público (Subfase 1.B, PENDIENTE) |
| 39 | [`39_BLOQUE_MAN.md`](fase1/39_BLOQUE_MAN.md) | Bloque MAN — Validación manual de la plataforma completa |
| 40 | [`40_BLOQUE_CUR.md`](fase1/40_BLOQUE_CUR.md) | Bloque CUR — La curación como producto propio (PENDIENTE) |
| 41 | [`41_BLOQUE_ING.0.md`](fase1/41_BLOQUE_ING.0.md) | Bloque ING.0 — Fundamentos del corpus normativo (Subfase 1.A, PENDIENTE) |
| 42 | [`42_BLOQUE_VIS.md`](fase1/42_BLOQUE_VIS.md) | Bloque VIS — Vistas del fundamento único: recuperación por metadatos (PENDIENTE) |
| 43 | [`43_BLOQUE_RES.md`](fase1/43_BLOQUE_RES.md) | Bloque RES — Que el asistente responda (PENDIENTE, va ANTES de Deploy) |
| 44 | [`44_BLOQUE_TST.md`](fase1/44_BLOQUE_TST.md) | Bloque TST — Fiabilidad de la suite de tests |
| 45 | [`45_BLOQUE_RAG.md`](fase1/45_BLOQUE_RAG.md) | Bloque RAG — Refuerzo del retrieval y calidad RAG (Subfase 1.B → 1.C, PENDIENTE) |
| 46 | [`46_BLOQUE_MOD.md`](fase1/46_BLOQUE_MOD.md) | Bloque MOD — Modelos de embedding y reranker: local en edge, API en cloud (2026-08-01) |
| 47 | [`47_BLOQUE_DET.md`](fase1/47_BLOQUE_DET.md) | Bloque DET — Desempate determinista del retriever (PENDIENTE) |
| 48 | [`48_BLOQUE_SYNC.md`](fase1/48_BLOQUE_SYNC.md) | Bloque SYNC — Sostenibilidad de la vigencia del corpus (PENDIENTE) |
| 49 | [`49_BLOQUE_OWUI.md`](fase1/49_BLOQUE_OWUI.md) | Bloque OWUI — ❌ DESCARTADO (2026-08-11) |
| 50 | [`50_BLOQUE_PIL.md`](fase1/50_BLOQUE_PIL.md) | Bloque PIL — Los dos asistentes del piloto: Vertex, corpus real y pruebas en local |
| 51 | [`51_BLOQUE_VER.md`](fase1/51_BLOQUE_VER.md) | Bloque VER — Verificación de Informes y Curación antes del despliegue |
| 52 | [`52_BLOQUE_PRO.md`](fase1/52_BLOQUE_PRO.md) | Bloque PRO — Las puertas al LLM del módulo de Informes, con el legacy delante |
| 53 | [`53_BLOQUE_LEG.md`](fase1/53_BLOQUE_LEG.md) | Bloque LEG — Retirada del legacy de prompts de AutomatIA |
| 54 | [`54_BLOQUE_SEG.md`](fase1/54_BLOQUE_SEG.md) | Bloque SEG — El asistente de informes de seguimiento: valoración anclada a su tabla |
| 55 | [`55_BLOQUE_RAS.md`](fase1/55_BLOQUE_RAS.md) | Bloque RAS — Rastreo de un portal institucional real |
| 56 | [`56_BLOQUE_CUR.md`](fase1/56_BLOQUE_CUR.md) | Bloque CUR — La curación vista por quien cura |
| 57 | [`57_BLOQUE_INF.md`](fase1/57_BLOQUE_INF.md) | Bloque INF — El módulo de informes, utilizable de punta a punta |
| 58 | [`58_BLOQUE_NIC.md`](fase1/58_BLOQUE_NIC.md) | Bloque NIC — La retirada del legacy NiceGUI, con inventario antes de borrar |
| 59 | [`59_BLOQUE_PLAT.md`](fase1/59_BLOQUE_PLAT.md) | Bloque PLAT — La administración de la plataforma, separada de la de Chatbots |
| 60 | [`60_BLOQUE_IDE.md`](fase1/60_BLOQUE_IDE.md) | Bloque IDE — Identidad y permisos: alta manual hoy, grupos del IdP mañana |
| 61 | [`61_BLOQUE_REPO.md`](fase1/61_BLOQUE_REPO.md) | Bloque REPO — Sustituir el repositorio de GitHub por uno sin objetos huérfanos |
| 62 | [`62_BLOQUE_HIB.md`](fase1/62_BLOQUE_HIB.md) | Bloque HIB — madurar el asistente para el piloto con informadores, y elegir configuración con lo que las 25 consultas pueden decidir |
| 63 | [`63_BLOQUE_ACT.md`](fase1/63_BLOQUE_ACT.md) | Bloque ACT — actualizar el corpus sin pagar dos veces, y hacer que idioma, emparejamiento y vigencia signifiquen lo que el corpus dice |
| 64 | [`64_BLOQUE_REG.md`](fase1/64_BLOQUE_REG.md) | Bloque REG — La plataforma como registro de actividad IA y servicios hacia fuera (PENDIENTE, planificado el 2026-08-31) |
| 65 | [`65_BLOQUE_VAS.md`](fase1/65_BLOQUE_VAS.md) | Bloque VAS — Verificaciones como servicio: citas, vigencia y auditoría estática por API (PENDIENTE, planificado el 2026-09-02) |
| 66 | [`66_BLOQUE_DIN.md`](fase1/66_BLOQUE_DIN.md) | Bloque DIN — Secciones parametrizables y ciclo de vida de la ingesta automática (PENDIENTE, planificado el 2026-08-31) |
| 67 | [`67_BLOQUE_USR.md`](fase1/67_BLOQUE_USR.md) | Bloque USR — Contraseña local para las personas, hasta que llegue el SSO (PENDIENTE, planificado el 2026-09-01) |
| 68 | [`68_BLOQUE_DOM.md`](fase1/68_BLOQUE_DOM.md) | Bloque DOM — El dominio institucional sirve lo público (PENDIENTE, planificado el 2026-09-01, **rehecho el 2026-09-02** cuando apareció el DNS) |
| 69 | [`69_BLOQUE_LANG.md`](fase1/69_BLOQUE_LANG.md) | Bloque LANG — Política de lengua configurable: monolingüe y respuesta fija (PENDIENTE, planificado el 2026-09-01) |
| 70 | [`70_BLOQUE_PLG.md`](fase1/70_BLOQUE_PLG.md) | Bloque PLG — Perfiles, estrategias y pipelines de recuperación descubiertos por *entry points* (PENDIENTE, planificado el 2026-09-02, ampliado el mismo día con las estrategias) |
| 71 | [`71_BLOQUE_FUN.md`](fase1/71_BLOQUE_FUN.md) | Bloque FUN — Catálogo de funciones deterministas: de scripts copiados a funciones versionadas y compartidas (PENDIENTE, planificado el 2026-09-01) |
| 72 | [`72_BLOQUE_PRC.md`](fase1/72_BLOQUE_PRC.md) | Bloque PRC — El catálogo de procedimientos entra al asistente de normativa (PENDIENTE, planificado el 2026-09-02) |
| 73 | [`73_BLOQUE_BD.md`](fase1/73_BLOQUE_BD.md) | Bloque BD — Una sola fuente para el esquema de la base de datos (BD.1 ejecutado el 2026-09-04; BD.2 arranca el mismo día) |
