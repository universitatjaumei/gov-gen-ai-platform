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

### Prompt 1C.2 — Editor accesible: shortcuts, focus trap y WCAG 2.2 AA (TDD RED/GREEN)

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


---

## Fase Deploy — Despliegue Staging GCP (Subfase 1.B, PENDIENTE)

> Nota: El Prompt D.6 (Edge node híbrido) pertenece a la Fase 3 y se detalla en Plan_TDD_Fase3.md.

## Fase Deploy — Paso a producción en GCP

Esta fase no añade funcionalidad nueva: convierte la pila de desarrollo (Docker Compose local) en un sistema desplegado en Google Cloud Platform. El codebase ya está diseñado para ello (ver sección "Infraestructura objetivo" en CLAUDE.md); estos prompts completan la configuración y documentan el proceso operativo.

**Requisito previo**: tener acceso a un proyecto GCP con facturación activa y los servicios habilitados: Cloud Run, Cloud SQL, Cloud Storage, Artifact Registry, Secret Manager, Cloud Build.

```
Fase Deploy
  ├── D.1  Autenticación pública del widget — API key por chatbot
  ├── D.2  Secrets y variables de entorno — migración a Secret Manager
  ├── D.3  Base de datos en producción — Cloud SQL + migraciones Alembic
  ├── D.4  Imágenes Docker — Artifact Registry + Cloud Run
  ├── D.5  CI/CD — pipeline GitHub Actions → Cloud Build → Cloud Run
  └── D.6  Edge node — despliegue híbrido cloud/edge en GCP
```

---

### Prompt D.1 — Autenticación pública del widget: API key por chatbot

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

### Prompt D.4 — Imágenes Docker: Artifact Registry y Cloud Run

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

### Prompt D.5 — CI/CD: pipeline GitHub Actions → Cloud Run

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

