"""Tests de integraciÃ³n del pipeline completo (Prompt 6.2).

Validan la integraciÃ³n entre BD, componentes RAG y autenticaciÃ³n JWT
en flujos reales de extremo a extremo.

Requieren PostgreSQL con pgvector corriendo en localhost:5432.

Rutas reales (monorepo):
  tests/integration/test_full_pipeline.py
    â†’ server/tests/modules/agents_hub/integration/test_full_pipeline.py
"""
import os
import uuid

import pytest
from sqlalchemy import text

_JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai",
)


class TestRAGPipeline:

    @pytest.mark.asyncio
    async def test_ingestion_to_retrieval_pipeline(self) -> None:
        """Pipeline completo: ingestiÃ³n â†’ chunking â†’ embedding â†’ retrieval."""
        from server.app.modules.agents_hub.database.connection import (
            create_async_engine,
            create_session_factory,
        )
        from server.app.modules.agents_hub.database.base import HubConfigBase, HubOperationalBase
        from server.app.modules.agents_hub.database.config_models import HubChatbot, HubOrganizacion, HubLLMConfig, HubProvider, HubPromptTemplate
        from server.app.modules.agents_hub.database.operational_models import HubDocument, HubDocumentChunk, HubInteraction, HubIngestionJob
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker
        from server.app.modules.agents_hub.ingestion.hasher import hash_content
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        engine = create_async_engine(DB_URL)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(HubConfigBase.metadata.create_all)
            await conn.run_sync(HubOperationalBase.metadata.create_all)

        factory = create_session_factory(engine)
        async with factory() as session:
            # 0. Crear proveedor
            await session.merge(HubProvider(id="google", name="Google", provider_type="google_genai"))
            await session.commit()

            # 1. Crear dependencias requeridas por HubChatbot
            llm_config = HubLLMConfig(
                provider="google",
                model_name="gemini-2.0-flash",
                temperature=0.7,
                max_tokens=2048,
            )
            session.add(llm_config)
            await session.flush()

            client = HubOrganizacion(
                name="Pipeline Test Client",
                partner_id="partner-pipeline-1",
            )
            session.add(client)
            await session.flush()

            chatbot = HubChatbot(
                organizacion_id=client.id,
                llm_config_id=llm_config.id,
                name=f"Pipeline Test {uuid.uuid4()}",
                system_prompt="Test",
                sources=[],
            )
            session.add(chatbot)
            await session.flush()

            # 2. Chunking
            markdown_content = (
                "# DocumentaciÃ³n de FastAPI\n\n"
                "FastAPI es un framework web moderno y rÃ¡pido para construir APIs con Python.\n\n"
                "## CaracterÃ­sticas\n\n"
                "- Alto rendimiento\n"
                "- FÃ¡cil de usar\n"
                "- Basado en estÃ¡ndares\n"
            )
            chunker = MarkdownChunker(chunk_size=200, chunk_overlap=20)
            chunks = chunker.split(markdown_content)
            assert len(chunks) >= 1

            # 3. Guardar chunks con embeddings sintÃ©ticos
            for i, chunk in enumerate(chunks):
                db_chunk = HubDocumentChunk(
                    chatbot_id=chatbot.id,
                    content=chunk.content,
                    source_url="https://fastapi.tiangolo.com",
                    content_hash=hash_content(chunk.content),
                    embedding=[0.1 + i * 0.01] * 1024,
                    language="es",
                )
                session.add(db_chunk)

            await session.commit()

            # 4. Retrieval: bÃºsqueda vectorial
            retriever = HybridRetriever(session)
            results = await retriever.vector_search(
                query_embedding=[0.11] * 1024,
                chatbot_id=chatbot.id,
                top_k=3,
            )

            assert len(results) >= 1
            assert any("FastAPI" in r.content for r in results)

            # 5. Retrieval: bÃºsqueda hÃ­brida
            hybrid_results = await retriever.hybrid_search(
                query="FastAPI framework",
                query_embedding=[0.11] * 1024,
                chatbot_id=chatbot.id,
                top_k=3,
            )
            assert len(hybrid_results) >= 1

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_chunker_splits_and_hasher_deduplicates(self) -> None:
        """El chunker divide el Markdown y el hasher evita duplicados."""
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker
        from server.app.modules.agents_hub.ingestion.hasher import hash_content

        content = (
            "# SecciÃ³n 1\n\nTexto largo de prueba para verificar que el chunker "
            "divide el contenido correctamente cuando supera el tamaÃ±o mÃ¡ximo configurado.\n\n"
            "# SecciÃ³n 2\n\nOtro bloque de contenido independiente.\n"
        )
        chunker = MarkdownChunker(chunk_size=100, chunk_overlap=10)
        chunks = chunker.split(content)

        # Verifica que se generan chunks
        assert len(chunks) >= 1

        # Verifica que hashes distintos para contenidos distintos
        hashes = {hash_content(c.content) for c in chunks}
        assert len(hashes) == len(chunks), "El hasher generÃ³ colisiones"


class TestAuthPipeline:

    def test_token_creation_and_validation(self) -> None:
        """Pipeline auth: crear token â†’ decodificar â†’ validar claims."""
        os.environ.update(_JWT_ENV)
        from server.app.core.auth import UserInfo, create_token, decode_token

        user = UserInfo(
            user_id="pipeline-user-456",
            email="pipeline@test.com",
            role="admin",
        )

        token = create_token(user)
        assert token is not None
        assert len(token) > 50

        decoded = decode_token(token)
        assert decoded.user_id == user.user_id
        assert decoded.email == user.email
        assert decoded.role == user.role

    def test_token_rejects_tampered_payload(self) -> None:
        """Un token con firma invÃ¡lida lanza AuthenticationError."""
        import base64
        os.environ.update(_JWT_ENV)
        from server.app.core.auth import UserInfo, create_token, decode_token
        from server.app.core.auth.exceptions import AuthenticationError

        user = UserInfo(user_id="u-1", email="u@test.com", role="user")
        token = create_token(user)

        # Manipular el payload (segunda parte del JWT)
        parts = token.split(".")
        parts[1] = base64.b64encode(b'{"sub":"hacker","email":"hacker@evil.com"}').decode().rstrip("=")
        tampered = ".".join(parts)

        with pytest.raises(AuthenticationError):
            decode_token(tampered)

    def test_expired_token_raises_authentication_error(self) -> None:
        """Token expirado lanza AuthenticationError."""
        os.environ.update(_JWT_ENV)
        from server.app.core.auth import UserInfo, create_token, decode_token
        from server.app.core.auth.exceptions import AuthenticationError

        user = UserInfo(user_id="u-exp", email="exp@test.com", role="user")
        token = create_token(user, expires_in_minutes=-1)

        with pytest.raises(AuthenticationError):
            decode_token(token)
