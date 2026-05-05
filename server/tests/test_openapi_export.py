"""
CF.1.1 (RED) — Test: el backend puede exportar openapi.json offline.

Estado inicial esperado:
  - TestOpenAPIFileExists: todos FALLAN porque los archivos no existen aún.
  - TestOpenAPIInMemory: deben PASAR si la app importa correctamente sin BD.
    Si fallan, revisar los comentarios de obstáculos conocidos.

Una vez ejecutado export_openapi.py (CF.1.2), toda la suite debe pasar.
Referencia: Plan_Contrato_OpenAPI.md, Bloque CF.1.
"""

import json
import os
from pathlib import Path

import pytest

# Variables de entorno mínimas establecidas ANTES de importar app.main,
# por si get_settings() se llama en algún import de nivel de módulo.
# Obstáculos conocidos documentados en CF.1.1:
#   - JWT_SECRET_KEY: RuntimeError si no está al instanciar Settings.
#   - DATABASE_URL: tiene default en db.py, no debería bloquear.
#   - DATABASE_URL_SYNC: usado por Alembic, puede ser necesario.
os.environ.setdefault("JWT_SECRET_KEY", "test-openapi-export-ci-key-min-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql+psycopg2://x:x@localhost/x")

# El conftest añade AI_agents_hub/ a sys.path → el prefijo correcto es server.app.*
from server.app.main import app  # noqa: E402

# server/tests/test_openapi_export.py → parents[1] = server/
_SERVER_ROOT = Path(__file__).parents[1]
OPENAPI_PATH = _SERVER_ROOT / "openapi.json"
FRONTEND_OPENAPI_PATH = _SERVER_ROOT.parent / "frontend" / "openapi.json"


class TestOpenAPIFileExists:
    """openapi.json debe existir en disco tras ejecutar export_openapi.py.

    Todos estos tests FALLAN hasta que se complete CF.1.2.
    """

    def test_server_openapi_json_exists(self):
        """server/openapi.json debe existir tras ejecutar export_openapi.py."""
        assert OPENAPI_PATH.exists(), (
            f"openapi.json no encontrado en {OPENAPI_PATH}.\n"
            "Solución: cd server && python export_openapi.py"
        )

    def test_server_openapi_json_is_valid(self):
        """server/openapi.json debe ser JSON válido y OpenAPI 3.x."""
        if not OPENAPI_PATH.exists():
            pytest.skip("Archivo no existe — ejecuta CF.1.2 primero")
        schema = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
        assert isinstance(schema, dict), "openapi.json no es un objeto JSON"
        assert schema.get("openapi", "").startswith("3."), "No es OpenAPI 3.x"

    def test_frontend_openapi_json_exists(self):
        """frontend/openapi.json debe existir (copia de server/openapi.json)."""
        assert FRONTEND_OPENAPI_PATH.exists(), (
            f"frontend/openapi.json no encontrado en {FRONTEND_OPENAPI_PATH}.\n"
            "Solución: copiar server/openapi.json a frontend/openapi.json"
        )


class TestOpenAPIInMemory:
    """app.openapi() debe funcionar en memoria sin conexión a base de datos.

    Si estos tests fallan, el mensaje de error documenta el obstáculo.
    Crear un issue antes de continuar con CF.1.2.
    """

    def test_app_generates_openapi_schema(self):
        """app.openapi() devuelve un dict con estructura OpenAPI 3.x válida."""
        schema = app.openapi()

        assert isinstance(schema, dict), "app.openapi() no devuelve un dict"
        assert "openapi" in schema, "Falta clave raíz 'openapi'"
        assert "info" in schema, "Falta clave raíz 'info'"
        assert "paths" in schema, "Falta clave raíz 'paths'"
        assert "components" in schema, "Falta clave raíz 'components'"
        assert schema["openapi"].startswith("3."), "Versión OpenAPI no es 3.x"

    def test_schema_has_api_paths(self):
        """El schema debe contener al menos un path de la API del hub."""
        schema = app.openapi()
        paths = schema.get("paths", {})

        assert len(paths) > 0, "No hay ningún path registrado en la app"

        hub_paths = [p for p in paths if "/hub/" in p or "/api/v1/" in p]
        assert len(hub_paths) > 0, (
            "No se encontraron paths bajo /hub/ ni /api/v1/.\n"
            f"Paths registrados: {sorted(paths.keys())[:15]}"
        )

    def test_schema_has_chatbot_schemas(self):
        """components.schemas debe incluir al menos un schema de la entidad Chatbot."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})

        chatbot_schemas = [k for k in schemas if "chatbot" in k.lower()]
        assert len(chatbot_schemas) > 0, (
            "No se encontraron schemas de Chatbot en components.schemas.\n"
            f"Schemas disponibles:\n  " + "\n  ".join(sorted(schemas.keys()))
        )

    def test_schema_has_client_schemas(self):
        """components.schemas debe incluir al menos un schema de la entidad Client."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})

        client_schemas = [k for k in schemas if "client" in k.lower()]
        assert len(client_schemas) > 0, (
            "No se encontraron schemas de Client en components.schemas.\n"
            f"Schemas disponibles:\n  " + "\n  ".join(sorted(schemas.keys()))
        )

    def test_schema_has_llmconfig_schemas(self):
        """components.schemas debe incluir al menos un schema de LLMConfig."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})

        llm_schemas = [k for k in schemas if "llm" in k.lower() or "model" in k.lower()]
        assert len(llm_schemas) > 0, (
            "No se encontraron schemas de LLMConfig en components.schemas.\n"
            f"Schemas disponibles:\n  " + "\n  ".join(sorted(schemas.keys()))
        )


class TestOpenAPISchemaContract:
    """CF.1.3 (RED) — El contrato tiene nombres de schema estables y enums correctos.

    Estos tests fallan hasta que CF.1.4 renombre los modelos Pydantic de respuesta.
    Documenta los gaps entre el contrato actual y lo que el frontend necesita.
    """

    # -- Nombres estables de Read schemas --

    def test_chatbot_read_schema_has_stable_name(self):
        """El schema de respuesta de Chatbot debe llamarse 'ChatbotRead', no usar prefijo de módulo.

        Nombre actual: server__app__routers__hub_chatbots_router__ChatbotOut
        Nombre esperado: ChatbotRead
        Impacto: Orval genera tipos TypeScript con el nombre del schema.
        Un nombre inestable rompe el cliente generado si el archivo se mueve.
        """
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})
        assert "ChatbotRead" in schemas, (
            "Schema 'ChatbotRead' no encontrado.\n"
            "Schemas de chatbot presentes: "
            + str([k for k in schemas if "chatbot" in k.lower()])
            + "\nSolución (CF.1.4): renombrar la clase ChatbotOut -> ChatbotRead "
            "en server/app/routers/hub_chatbots_router.py"
        )

    def test_client_read_schema_has_stable_name(self):
        """El schema de respuesta de Client debe llamarse 'ClientRead'."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})
        assert "ClientRead" in schemas, (
            "Schema 'ClientRead' no encontrado.\n"
            "Schemas de client presentes: "
            + str([k for k in schemas if "client" in k.lower()])
            + "\nSolución (CF.1.4): renombrar ClientOut -> ClientRead "
            "en server/app/routers/hub_clients_router.py"
        )

    def test_llmconfig_read_schema_has_stable_name(self):
        """El schema de respuesta de LLMConfig debe llamarse 'LLMConfigRead'."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})
        assert "LLMConfigRead" in schemas, (
            "Schema 'LLMConfigRead' no encontrado.\n"
            "Schemas de llm presentes: "
            + str([k for k in schemas if "llm" in k.lower()])
            + "\nSolución (CF.1.4): renombrar LLMConfigOut -> LLMConfigRead "
            "en server/app/routers/hub_llm_configs_router.py"
        )

    def test_prompt_template_read_schema_has_stable_name(self):
        """El schema de respuesta de PromptTemplate debe llamarse 'PromptTemplateRead'."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})
        assert "PromptTemplateRead" in schemas, (
            "Schema 'PromptTemplateRead' no encontrado.\n"
            "Schemas de prompt presentes: "
            + str([k for k in schemas if "prompt" in k.lower()])
            + "\nSolución (CF.1.4): renombrar PromptTemplateOut -> PromptTemplateRead "
            "en server/app/routers/hub_prompt_templates_router.py"
        )

    # -- Enum de retrieval_mode --

    def test_retrieval_mode_has_enum_values(self):
        """retrieval_mode en ChatbotCreate debe exponer sus valores válidos como enum.

        El frontend hardcodea ['RAG', 'MD_LONG_CONTEXT', 'MD_AGENT_SELECTOR'].
        Si el contrato no expone el enum, el frontend puede quedar desalineado
        cuando se añadan o eliminen modos.
        Solución (CF.1.4): usar Literal['RAG', 'MD_LONG_CONTEXT', 'MD_AGENT_SELECTOR']
        en el modelo Pydantic ChatbotCreate.
        """
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})
        chatbot_create = schemas.get("ChatbotCreate", {})
        retrieval_mode_prop = chatbot_create.get("properties", {}).get("retrieval_mode", {})

        enum_values = retrieval_mode_prop.get("enum") or retrieval_mode_prop.get("allOf", [{}])[0].get("enum")
        assert enum_values is not None, (
            "retrieval_mode en ChatbotCreate no tiene enum definido en el contrato.\n"
            f"Definicion actual: {retrieval_mode_prop}\n"
            "Solucion (CF.1.4): cambiar el tipo de retrieval_mode en los schemas Pydantic "
            "a Literal['RAG', 'MD_LONG_CONTEXT', 'MD_AGENT_SELECTOR']"
        )
        assert set(enum_values) == {"RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR"}, (
            f"Valores de enum incorrectos: {enum_values}"
        )

    # -- Campos de los Read schemas (verificación de contenido, no de nombre) --

    def test_chatbot_read_fields_are_complete(self):
        """El schema de respuesta de Chatbot (sea cual sea su nombre actual) tiene los campos
        que el frontend espera en su interfaz Chatbot manual."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})

        # Buscar por nombre estable o por el nombre actual con módulo
        read_schema = schemas.get("ChatbotRead") or schemas.get(
            next((k for k in schemas if "hub_chatbots" in k), ""), {}
        )
        props = set(read_schema.get("properties", {}).keys())

        expected = {
            "id", "name", "client_id", "llm_config_id", "system_prompt",
            "sources", "is_active", "retrieval_mode", "retrieval_top_k",
            "use_prompt_caching", "cache_ttl", "kind", "parent_chatbot_id",
            "created_at", "updated_at",
        }
        missing = expected - props
        assert not missing, (
            f"Campos faltantes en el schema de respuesta de Chatbot: {sorted(missing)}"
        )

    def test_client_read_fields_are_complete(self):
        """El schema de respuesta de Client tiene los campos que el frontend espera."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})

        read_schema = schemas.get("ClientRead") or schemas.get(
            next((k for k in schemas if "hub_clients" in k), ""), {}
        )
        props = set(read_schema.get("properties", {}).keys())

        expected = {
            "id", "name", "partner_id", "theme_config", "is_active",
            "chatbot_count", "created_at", "updated_at",
        }
        missing = expected - props
        assert not missing, (
            f"Campos faltantes en el schema de respuesta de Client: {sorted(missing)}"
        )

    def test_llmconfig_read_fields_are_complete(self):
        """El schema de respuesta de LLMConfig tiene los campos que el frontend espera."""
        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})

        read_schema = schemas.get("LLMConfigRead") or schemas.get(
            next((k for k in schemas if "hub_llm_configs" in k), ""), {}
        )
        props = set(read_schema.get("properties", {}).keys())

        expected = {
            "id", "provider", "model_name", "temperature",
            "top_p", "max_tokens", "api_key_secret_name", "tier", "label", "is_default",
        }
        missing = expected - props
        assert not missing, (
            f"Campos faltantes en el schema de respuesta de LLMConfig: {sorted(missing)}"
        )
