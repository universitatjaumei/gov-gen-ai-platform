"""Prompt 2.6 â€” Tests del retriever hÃ­brido (TDD - RED â†’ GREEN)."""
import uuid
import pytest
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai"


@pytest.fixture
async def populated_session():
    """SesiÃ³n con tablas Hub y datos de prueba para el retriever."""
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )
    from server.app.modules.agents_hub.database.base import HubConfigBase, HubOperationalBase
    from server.app.modules.agents_hub.database.config_models import HubChatbot, HubClient, HubLLMConfig, HubProvider, HubPromptTemplate
    from server.app.modules.agents_hub.database.operational_models import HubDocument, HubDocumentChunk, HubInteraction, HubIngestionSource, HubIngestionJob

    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(HubConfigBase.metadata.create_all)
        await conn.run_sync(HubOperationalBase.metadata.create_all)

    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        await session.merge(HubProvider(id="google", name="Google", provider_type="google_genai"))
        await session.commit()

        llm = HubLLMConfig(provider="google", model_name="gemini-flash")
        session.add(llm)
        client = HubClient(name="Retriever Test", partner_id="partner_dev")
        session.add(client)
        await session.flush()

        chatbot = HubChatbot(
            client_id=client.id,
            llm_config_id=llm.id,
            name="Retriever Bot",
            system_prompt="Test",
            sources=[],
        )
        session.add(chatbot)
        await session.flush()

        chunks = [
            HubDocumentChunk(
                chatbot_id=chatbot.id,
                content="Python es genial para ciencia de datos",
                source_url="url1",
                content_hash="h1",
                embedding=[0.1] * 1024,
            ),
            HubDocumentChunk(
                chatbot_id=chatbot.id,
                content="Java es diferente a Python",
                source_url="url2",
                content_hash="h2",
                embedding=[0.9] * 1024,
            ),
        ]
        session.add_all(chunks)
        await session.commit()

        yield session, chatbot.id

    async with engine.begin() as conn:
        await conn.run_sync(HubOperationalBase.metadata.drop_all)
        await conn.run_sync(HubConfigBase.metadata.drop_all)
    await engine.dispose()


class TestHybridRetriever:

    @pytest.mark.asyncio
    async def test_vector_similarity_search(self, populated_session) -> None:
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        session, chatbot_id = populated_session
        retriever = HybridRetriever(session)

        results = await retriever.vector_search([0.12] * 1024, chatbot_id, top_k=2)

        assert len(results) >= 1
        assert "Python" in results[0].content

    @pytest.mark.asyncio
    async def test_keyword_search_finds_matching_content(self, populated_session) -> None:
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        session, chatbot_id = populated_session
        retriever = HybridRetriever(session)

        results = await retriever.keyword_search("Python", chatbot_id, top_k=5)

        assert len(results) >= 1
        assert all("Python" in r.content for r in results)

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_ranked_results(self, populated_session) -> None:
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        session, chatbot_id = populated_session
        retriever = HybridRetriever(session)

        results = await retriever.hybrid_search(
            query="Python datos",
            query_embedding=[0.12] * 1024,
            chatbot_id=chatbot_id,
            top_k=2,
        )

        assert len(results) >= 1
        # El primer resultado debe ser el mÃ¡s relevante para Python
        assert "Python" in results[0].content

    @pytest.mark.asyncio
    async def test_vector_search_with_language_filter(self, populated_session) -> None:
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        session, chatbot_id = populated_session
        retriever = HybridRetriever(session)

        # Los chunks de prueba tienen language="es" por defecto
        results_es = await retriever.vector_search(
            [0.12] * 1024, chatbot_id, top_k=5, language="es"
        )
        results_ca = await retriever.vector_search(
            [0.12] * 1024, chatbot_id, top_k=5, language="ca"
        )

        assert len(results_es) >= 1
        assert len(results_ca) == 0  # No hay chunks en catalÃ¡n
