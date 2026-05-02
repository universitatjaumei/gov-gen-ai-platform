"""Prompt 2.4 — Tests de modelos ORM (TDD - RED → GREEN)."""
import uuid
import pytest
from sqlalchemy import select, text

DB_URL = "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai"


@pytest.fixture
async def db_session():
    """Sesión con tablas Hub creadas y eliminadas al finalizar el test."""
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )
    from server.app.modules.agents_hub.database.base import HubConfigBase, HubOperationalBase

    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(HubConfigBase.metadata.create_all)
        await conn.run_sync(HubOperationalBase.metadata.create_all)

    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(HubOperationalBase.metadata.drop_all)
        await conn.run_sync(HubConfigBase.metadata.drop_all)
    await engine.dispose()


class TestHubLLMConfigModel:

    @pytest.mark.asyncio
    async def test_llm_config_persistence(self, db_session) -> None:
        """Prompt 2.8 — Validar que se pueden guardar y recuperar parámetros LLM."""
        from server.app.modules.agents_hub.database.config_models import HubLLMConfig

        config = HubLLMConfig(
            provider="google",
            model_name="gemini-2.5-flash",
            temperature=0.3,
            max_tokens=4096,
        )
        db_session.add(config)
        await db_session.commit()

        result = await db_session.execute(
            select(HubLLMConfig).where(HubLLMConfig.model_name == "gemini-2.5-flash")
        )
        saved = result.scalar_one()
        assert saved.temperature == pytest.approx(0.3)
        assert saved.max_tokens == 4096
        assert saved.provider == "google"


class TestHubChatbotModel:

    @pytest.mark.asyncio
    async def test_create_chatbot_requires_llm_config(self, db_session) -> None:
        """Prompt 2.9 — Validar que no se puede crear un chatbot sin llm_config_id."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot, HubClient

        client = HubClient(name="Test Inst", partner_id="partner_dev")
        db_session.add(client)
        await db_session.flush()

        chatbot = HubChatbot(
            client_id=client.id,
            llm_config_id=uuid.uuid4(),  # FK inválido — debe fallar
            name="Bot sin modelo",
            system_prompt="Test",
            sources=[],
        )
        db_session.add(chatbot)
        with pytest.raises(Exception):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_create_chatbot_with_valid_model(self, db_session) -> None:
        """Chatbot con llm_config válido se persiste correctamente."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot, HubClient, HubLLMConfig

        llm = HubLLMConfig(provider="openai", model_name="gpt-4o", temperature=0.5)
        db_session.add(llm)
        await db_session.flush()

        client = HubClient(name="Univ. Test", partner_id="partner_dev")
        db_session.add(client)
        await db_session.flush()

        chatbot = HubChatbot(
            client_id=client.id,
            llm_config_id=llm.id,
            name="Bot Válido",
            system_prompt="Eres útil.",
            sources=[],
        )
        db_session.add(chatbot)
        await db_session.commit()

        result = await db_session.execute(
            select(HubChatbot).where(HubChatbot.name == "Bot Válido")
        )
        saved = result.scalar_one()
        assert saved.llm_config_id == llm.id


class TestHubPromptTemplateModel:

    @pytest.mark.asyncio
    async def test_chatbot_retrieves_correct_prompt_by_language(self, db_session) -> None:
        """Prompt 2.8 — Al pedir 'system_base' en catalán no devuelve el de castellano."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot, HubClient, HubLLMConfig, HubPromptTemplate

        llm = HubLLMConfig(provider="google", model_name="gemini-flash")
        db_session.add(llm)
        client = HubClient(name="Univ. CA", partner_id="partner_dev")
        db_session.add(client)
        await db_session.flush()

        chatbot = HubChatbot(
            client_id=client.id,
            llm_config_id=llm.id,
            name="Bot CA",
            system_prompt="Base",
            sources=[],
        )
        db_session.add(chatbot)
        await db_session.flush()

        db_session.add_all([
            HubPromptTemplate(
                chatbot_id=chatbot.id,
                slug="system_base",
                language="es",
                template_text="Eres un asistente.",
            ),
            HubPromptTemplate(
                chatbot_id=chatbot.id,
                slug="system_base",
                language="ca",
                template_text="Ets un assistent.",
            ),
        ])
        await db_session.commit()

        result = await db_session.execute(
            select(HubPromptTemplate).where(
                HubPromptTemplate.chatbot_id == chatbot.id,
                HubPromptTemplate.slug == "system_base",
                HubPromptTemplate.language == "ca",
            )
        )
        ca_prompt = result.scalar_one()
        assert "assistent" in ca_prompt.template_text
        assert "asistente" not in ca_prompt.template_text


class TestHubDocumentChunkModel:

    @pytest.mark.asyncio
    async def test_create_chunk_with_vector(self, db_session) -> None:
        from server.app.modules.agents_hub.database.config_models import HubChatbot, HubClient, HubLLMConfig
        from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk

        llm = HubLLMConfig(provider="google", model_name="gemini-flash")
        db_session.add(llm)
        client = HubClient(name="Test", partner_id="partner_dev")
        db_session.add(client)
        await db_session.flush()

        chatbot = HubChatbot(
            client_id=client.id,
            llm_config_id=llm.id,
            name="Chunk Bot",
            system_prompt="Test",
            sources=[],
        )
        db_session.add(chatbot)
        await db_session.flush()

        chunk = HubDocumentChunk(
            chatbot_id=chatbot.id,
            content="Python es genial",
            source_url="https://example.com",
            content_hash="abc123",
            embedding=[0.1] * 1024,
        )
        db_session.add(chunk)
        await db_session.commit()

        result = await db_session.execute(
            select(HubDocumentChunk).where(HubDocumentChunk.content_hash == "abc123")
        )
        saved = result.scalar_one()
        assert len(saved.embedding) == 1024
