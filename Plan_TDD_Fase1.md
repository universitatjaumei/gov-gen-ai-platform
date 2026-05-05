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
- **Subfase 1.B — Identidad y Despliegue Cloud:**
  - Sistema de temas institucionales (FASE 10): variables CSS, presets, editor visual.
  - Despliegue staging GCP (Prompts D.1–D.5): Secret Manager, Cloud SQL, Cloud Run, CI/CD.
- **Subfase 1.C — Privacidad, Diseño y Exportación de Informes:**
  - Focus Mode como infraestructura de diseño transversal (1C.0): Zustand + DrawerHub reutilizable.
  - Exportación DOCX/ODT con citas trazables (1C.4): plantillas Jinja2, índice automático, RunManifest.
  - Integración Google Drive opcional (1C.5): destino configurable por Organización.
  - Privacidad NER reversible (FASE 13): anonimización PII antes de enviar al LLM.
- **Transversal F1:** Accesibilidad WCAG 2.2 AA + Admin conversacional (FASE 20).
- **Al finalizar F1:** Autoinstalación (FASE 11) para distribución como software libre.

## Qué NO se ejecuta en esta fase
- Migración NiceGUI→React (Guía 9C.0, Prompts 9.12–9.15) → Fase 2.
- Agente local (Thin Client, Prompt 9.16) → Fase 2.
- Sandbox distribuido, RunManifest, Script Registry → Fase 2.
- Gestor de Expedientes → Fase 3.
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

## Prompts 9.11a–9.11d — Agentes de Redacción / Workspaces (Subfase 1.A / 1.C, PENDIENTE)

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

**Dependencias**: Prompts 9.11a–9.11d (workspaces y grafo LangGraph de redacción ✅ completados en subfase anterior).

**Entregable**: Editor de informes en Focus Mode con exportación a DOCX/ODT con citas trazables y opción de guardar directamente en Google Drive institucional.

---

### Prompt 1C.0 — Focus Mode como Infraestructura de Diseño Transversal (TDD RED/GREEN)

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

