"""Tests MOD.1 — propósito en la configuración y procedencia en el vector.

Decisión completa en `docs/DECISION_MODELOS_EMBEDDING_RERANKER.md`. Lo que estos tests
protegen, en una frase: **cambiar de modelo de embeddings no puede ser un cambio silencioso**.

El coseno entre vectores de dos espacios distintos no da error, da resultados malos. Sin
procedencia grabada con el vector, esa avería es indistinguible de «el retriever funciona
regular», que es la clase de fallo que más caro sale encontrar.
"""
from __future__ import annotations

import math
import uuid

import pytest

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _chunk,
    _documento,
)


class TestPropositoEnLaConfiguracion:

    @pytest.mark.asyncio
    async def test_should_persist_purpose_and_output_dimensionality(self, db_session):
        from server.app.modules.agents_hub.database.config_models import (
            HubLLMConfig,
            HubProvider,
        )

        await db_session.merge(
            HubProvider(id="google", name="Google", provider_type="google_genai")
        )
        config = HubLLMConfig(
            provider="google",
            model_name="gemini-embedding-001",
            purpose="embedding",
            output_dimensionality=1024,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.purpose == "embedding"
        assert config.output_dimensionality == 1024

    @pytest.mark.asyncio
    async def test_should_default_purpose_to_chat(self, db_session):
        """Las filas que ya existen son de chat: el default no puede cambiarles el sentido."""
        from server.app.modules.agents_hub.database.config_models import (
            HubLLMConfig,
            HubProvider,
        )

        await db_session.merge(
            HubProvider(id="google", name="Google", provider_type="google_genai")
        )
        config = HubLLMConfig(provider="google", model_name="gemini-flash")
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.purpose == "chat"
        assert config.output_dimensionality is None

    @pytest.mark.asyncio
    async def test_should_reject_an_unknown_purpose(self, db_session):
        """CheckConstraint sí, al contrario que el vocabulario: son tres valores estables
        con consumidor en el código, mismo criterio que `nivell_acces` en ING.0.2."""
        from sqlalchemy.exc import IntegrityError

        from server.app.modules.agents_hub.database.config_models import (
            HubLLMConfig,
            HubProvider,
        )

        await db_session.merge(
            HubProvider(id="google", name="Google", provider_type="google_genai")
        )
        db_session.add(
            HubLLMConfig(provider="google", model_name="x", purpose="reranking")
        )

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestServiciosDeEmbedding:

    def test_should_expose_model_name_and_dimensions_on_services(self):
        """La guarda de `recalculate-corpus` lee estos atributos. Hasta MOD.1 no existían,
        así que caía siempre al default y la comparación era 1024 != 1024: no podía saltar."""
        from server.app.modules.agents_hub.services.embedding_service import (
            GoogleEmbeddingService,
            LocalEmbeddingService,
        )

        local = LocalEmbeddingService()
        assert local.model_name == "BAAI/bge-m3"
        assert local.dimensions == 1024

        google = GoogleEmbeddingService(client=object())
        assert google.model_name
        assert google.dimensions == 1024

    @pytest.mark.asyncio
    async def test_should_l2_normalize_google_embeddings(self):
        """Google NO normaliza las dimensiones distintas de 3072 («you must manually
        normalize non-3072 dimensions»), así que normalizamos nosotros. Depender de que lo
        haga el proveedor es depender de una nota al pie que cambia entre versiones.
        """
        from server.app.modules.agents_hub.services.embedding_service import (
            GoogleEmbeddingService,
        )

        class _ClienteSinNormalizar:
            async def aembed_query(self, text: str) -> list[float]:
                return [3.0, 4.0] + [0.0] * 1022  # norma 5, claramente sin normalizar

        vector = await GoogleEmbeddingService(client=_ClienteSinNormalizar()).embed("q")

        assert math.isclose(sum(v * v for v in vector) ** 0.5, 1.0, rel_tol=1e-6)
        assert math.isclose(vector[0], 0.6, rel_tol=1e-6)

    @pytest.mark.asyncio
    async def test_should_ask_google_for_the_configured_dimensionality(self):
        from server.app.modules.agents_hub.services.embedding_service import (
            GoogleEmbeddingService,
        )

        servicio = GoogleEmbeddingService(
            model_name="gemini-embedding-001", output_dimensionality=768, client=object()
        )

        assert servicio.dimensions == 768


class TestProcedenciaDelVector:

    @pytest.mark.asyncio
    async def test_should_record_model_and_dimension_on_every_chunk(self):
        from unittest.mock import AsyncMock, MagicMock

        from server.app.modules.agents_hub.database.operational_models import (
            HubDocument,
            HubDocumentChunk,
        )
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

        session = AsyncMock()
        session.add = MagicMock()
        session.execute = AsyncMock()

        # `embed_batch` explícito (RAG.7): un AsyncMock pelado lo fabrica solo y devuelve
        # algo que no es una lista de vectores, con lo que el watcher no crea ningún chunk
        # y el test falla por una razón que no tiene que ver con lo que prueba.
        embedding_svc = AsyncMock()
        embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)
        embedding_svc.embed_batch = AsyncMock(side_effect=lambda ts: [[0.1] * 1024] * len(ts))
        embedding_svc.model_name = "BAAI/bge-m3"
        embedding_svc.dimensions = 1024

        watcher = IngestionWatcher(
            session=session,
            embedding_service=embedding_svc,
            chatbot_provider=AsyncMock(),
        )
        doc = HubDocument(
            id=uuid.uuid4(), chatbot_id=uuid.uuid4(), title="Norma",
            canonical_url="https://ej.com/n", markdown_content="# Norma\n\nTexto.",
            content_hash="h" * 64, language="es", source_kind="publicacio",
        )

        await watcher._regenerate_chunks_for_document(doc)

        chunks = [
            c.args[0] for c in session.add.call_args_list
            if isinstance(c.args[0], HubDocumentChunk)
        ]
        assert chunks
        assert all(c.embedding_model == "BAAI/bge-m3" for c in chunks)
        assert all(c.embedding_dim == 1024 for c in chunks)

    @pytest.mark.asyncio
    async def test_should_detect_a_corpus_embedded_with_another_model(self, db_session):
        """La guarda que existía y no podía saltar, ahora salta."""
        from server.app.modules.agents_hub.services.embedding_space import (
            EmbeddingSpaceMismatch,
            assert_embedding_space_matches,
        )

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb)
        await _chunk(
            db_session, cb, doc, "Texto", embedding_model="BAAI/bge-m3", embedding_dim=1024
        )
        await db_session.commit()

        class _Servicio:
            model_name = "gemini-embedding-001"
            dimensions = 1024

        with pytest.raises(EmbeddingSpaceMismatch) as error:
            await assert_embedding_space_matches(db_session, cb, _Servicio())

        # El mensaje nombra los dos espacios: quien lo lea tiene que saber qué re-embeber
        assert "bge-m3" in str(error.value)
        assert "gemini-embedding-001" in str(error.value)

    @pytest.mark.asyncio
    async def test_should_accept_a_corpus_embedded_with_the_active_model(self, db_session):
        from server.app.modules.agents_hub.services.embedding_space import (
            assert_embedding_space_matches,
        )

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb)
        await _chunk(
            db_session, cb, doc, "Texto", embedding_model="BAAI/bge-m3", embedding_dim=1024
        )
        await db_session.commit()

        class _Servicio:
            model_name = "BAAI/bge-m3"
            dimensions = 1024

        await assert_embedding_space_matches(db_session, cb, _Servicio())  # no lanza
