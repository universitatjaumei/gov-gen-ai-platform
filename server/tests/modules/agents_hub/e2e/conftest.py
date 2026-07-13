"""Fixtures compartidas para tests E2E de agents_hub.

Requieren PostgreSQL con pgvector corriendo en localhost:5432.
Por defecto usan la misma BD de desarrollo (govgenai).
En CI se sobreescribe DATABASE_URL con las credenciales del servicio.

Nota de diseño: todos los fixtures de BD tienen scope="function" para
evitar conflictos de event loop entre pytest-asyncio y httpx.AsyncClient.
"""
import os
import uuid

import pytest

_JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
    "GOOGLE_API_KEY": "test-key",
    "GEMINI_API_KEY": "test-key",
}

_TEST_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai",
)


@pytest.fixture(autouse=True)
def _set_jwt_env():
    os.environ.update(_JWT_ENV)


@pytest.fixture
async def db_engine():
    """Motor de BD por test: crea las tablas hub_ si no existen."""
    from server.app.modules.agents_hub.database.connection import create_async_engine
    from server.app.modules.agents_hub.database.base import HubConfigBase, HubOperationalBase

    engine = create_async_engine(_TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(HubConfigBase.metadata.create_all)
        await conn.run_sync(HubOperationalBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Sesión de BD por test."""
    from server.app.modules.agents_hub.database.connection import create_session_factory

    factory = create_session_factory(db_engine)
    async with factory() as session:
        yield session


@pytest.fixture
def auth_headers():
    """Headers JWT para usuario final (e2e-user-1)."""
    from server.app.core.auth import UserInfo, create_token

    token = create_token(
        UserInfo(user_id="e2e-user-1", email="e2e@test.com", role="user")
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    """Headers JWT para administrador."""
    from server.app.core.auth import UserInfo, create_token

    token = create_token(
        UserInfo(user_id="admin-e2e-1", email="admin-e2e@test.com", role="admin")
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def setup_chatbot(db_session):
    """Crea un chatbot de prueba con cliente, config LLM y chunk de conocimiento."""
    from server.app.modules.agents_hub.database.config_models import HubChatbot, HubOrganizacion, HubLLMConfig, HubProvider
    from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk
    from server.app.modules.agents_hub.ingestion.hasher import hash_content

    await db_session.merge(HubProvider(id="google", name="Google", provider_type="google_genai"))
    await db_session.commit()

    llm_config = HubLLMConfig(
        provider="google",
        model_name="gemini-2.0-flash",
        temperature=0.7,
    )
    db_session.add(llm_config)
    await db_session.flush()

    client = HubOrganizacion(name="E2E Test Client", partner_id="partner-e2e-1")
    db_session.add(client)
    await db_session.flush()

    chatbot = HubChatbot(
        organizacion_id=client.id,
        llm_config_id=llm_config.id,
        name=f"E2E Bot {uuid.uuid4()}",
        system_prompt="Eres un asistente de prueba.",
        sources=["https://example.com"],
    )
    db_session.add(chatbot)
    await db_session.flush()

    content = "Python es un lenguaje de programación versátil y fácil de aprender."
    chunk = HubDocumentChunk(
        chatbot_id=chatbot.id,
        content=content,
        source_url="https://example.com/python",
        content_hash=hash_content(content),
        embedding=[0.1] * 1024,
        language="es",
    )
    db_session.add(chunk)
    await db_session.commit()

    return chatbot


@pytest.fixture
def test_app(db_engine):
    """App FastAPI de test con los routers hub y la sesión de test inyectada."""
    from fastapi import FastAPI
    from server.app.api.v1.hub_chat import router as chat_router
    from server.app.api.v1.hub_tasks import router as tasks_router
    from server.app.modules.agents_hub.database.connection import (
        create_session_factory,
        get_async_session,
    )

    async def _override_session():
        factory = create_session_factory(db_engine)
        async with factory() as session:
            yield session

    app = FastAPI()
    app.dependency_overrides[get_async_session] = _override_session
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    return app
