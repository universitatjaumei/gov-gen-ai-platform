"""Tests RAG.8 — parent-child (small-to-big) y parámetros de troceado en la cascada.

La tensión que resuelve: un fragmento pequeño se **encuentra** mejor —el vector es más
específico— pero **responde** peor, porque le falta el contexto de alrededor. Small-to-big
busca con el hijo y responde con el padre.

Y una decisión que este prompt cierra, señalada al abrirlo: **la agrupación sigue siendo por
documento**. El plan pedía «deduplicar hijos del mismo padre», y agrupar por documento ya lo
consigue —es un superconjunto— sin emitir varias entradas por documento en el `sources` del
evento SSE, contrato que RAG.2 fijó por snapshot. De paso, eso deja sin motivo la fusión de
fragmentos adyacentes que RAG.5 descartó por ser código muerto: sigue sin haber productor.
"""
from __future__ import annotations

import uuid

import pytest

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _documento,
    _emb,
)

SECCION_LARGA = """# Reglament de dietes

## Article 7. Import i justificacio

L'import de la dieta per dia complet es de 53,34 euros quan el desplacament exigeix
pernoctacio fora del municipi de residencia habitual del personal afectat.
La justificacio s'ha de presentar en el termini de deu dies habils comptats des de la
finalitzacio del desplacament, acompanyada dels justificants originals de la despesa.
En cas de desplacament a l'estranger s'aplicaran els imports especifics previstos en
l'annex II d'aquest reglament, actualitzats anualment per acord del Consell de Govern.
"""


class _Emb:
    model_name = "BAAI/bge-m3"
    dimensions = 1024

    async def embed(self, text: str):
        return _emb(0)

    async def embed_batch(self, texts: list[str]):
        return [_emb(0) for _ in texts]


class TestConfiguracionEnLaCascada:

    @pytest.mark.asyncio
    async def test_should_fall_back_to_cascade_defaults_when_unset(self, db_session):
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )
        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        _, chatbot = await _organizacion_y_chatbot(db_session)
        await db_session.commit()

        cfg = await get_effective_public_graph_config(chatbot.id, db_session)

        assert cfg.chunk_size == 1000
        assert cfg.chunk_overlap == 100
        assert cfg.chunking_strategy == "structural"

    @pytest.mark.asyncio
    async def test_should_use_per_chatbot_chunk_size_and_overlap(self, db_session):
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )
        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        org, chatbot = await _organizacion_y_chatbot(db_session)
        org.default_chunk_size = 800
        chatbot.chunk_size = 600
        chatbot.chunking_strategy = "parent_child"
        await db_session.commit()

        cfg = await get_effective_public_graph_config(chatbot.id, db_session)

        assert cfg.chunk_size == 600, "el chatbot manda sobre la organizacion"
        assert cfg.chunk_overlap == 100, "lo no declarado sigue viniendo de plataforma"
        assert cfg.chunking_strategy == "parent_child"

    @pytest.mark.asyncio
    async def test_should_reject_an_unknown_chunking_strategy(self, db_session):
        from sqlalchemy.exc import IntegrityError

        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        _, chatbot = await _organizacion_y_chatbot(db_session)
        chatbot.chunking_strategy = "jerarquico"

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestTroceadoParentChild:

    def _chunks(self, **kwargs):
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        return MarkdownChunker(strategy="parent_child", **kwargs).split(
            SECCION_LARGA, document_title="Reglament de dietes"
        )

    def test_should_split_children_within_structural_sections(self):
        """Los hijos se trocean DENTRO de la sección, no atravesándola."""
        hijos = self._chunks(chunk_size_child=200)

        assert len(hijos) > 1, "no se troceo en hijos"
        # Ninguno mezcla el encabezado del documento con el cuerpo de otra sección
        assert all(len(h.content) <= 400 for h in hijos), [len(h.content) for h in hijos]

    def test_should_store_parent_section_on_child_chunks(self):
        hijos = self._chunks(chunk_size_child=200)

        assert all(h.parent_content for h in hijos)
        # Todos los hijos de la misma sección comparten padre, y el padre la contiene entera
        padres = {h.parent_content for h in hijos}
        assert len(padres) == 1
        assert "53,34" in padres.pop()

    def test_should_not_set_parent_content_in_structural_strategy(self):
        """La estrategia por defecto no cambia: sin padre, el excerpt es el propio chunk."""
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        chunks = MarkdownChunker().split(SECCION_LARGA, document_title="Reglament")

        assert all(not c.parent_content for c in chunks)


class TestRecuperacion:

    @pytest.mark.asyncio
    async def test_should_return_parent_content_as_evidence(self, db_session):
        """Se busca con el hijo y se responde con el padre: eso es small-to-big."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubDocumentChunk,
        )
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="ca")
        db_session.add(
            HubDocumentChunk(
                chatbot_id=cb, document_id=doc.id,
                content="L'import de la dieta per dia complet es de 53,34 euros",
                parent_content="Article 7. Import i justificacio. TEXTO COMPLETO DE LA SECCION.",
                source_url=doc.canonical_url, content_hash=uuid.uuid4().hex * 2,
                embedding=_emb(0), language="ca", chunk_metadata={},
                embedding_model="BAAI/bge-m3", embedding_dim=1024,
            )
        )
        await db_session.commit()

        ctx = await VectorRetrievalStrategy(db_session, _Emb(), top_k=5).get_context(
            query="import dieta", chatbot_id=cb
        )

        assert "TEXTO COMPLETO DE LA SECCION" in ctx.sources[0].excerpt

    @pytest.mark.asyncio
    async def test_should_deduplicate_children_of_same_parent_in_results(self, db_session):
        """Dos hijos del mismo padre no pueden ocupar dos plazas con el mismo texto."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubDocumentChunk,
        )
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="ca")
        padre = "Article 7 entero, con los dos parrafos."
        for texto in ("primer fragmento del articulo", "segundo fragmento del articulo"):
            db_session.add(
                HubDocumentChunk(
                    chatbot_id=cb, document_id=doc.id, content=texto, parent_content=padre,
                    source_url=doc.canonical_url, content_hash=uuid.uuid4().hex * 2,
                    embedding=_emb(0), language="ca", chunk_metadata={},
                    embedding_model="BAAI/bge-m3", embedding_dim=1024,
                )
            )
        await db_session.commit()

        ctx = await VectorRetrievalStrategy(db_session, _Emb(), top_k=5).get_context(
            query="fragmento articulo", chatbot_id=cb
        )

        assert len(ctx.sources) == 1
        assert ctx.sources[0].excerpt == padre


class TestRegeneracion:

    @pytest.mark.asyncio
    async def test_should_regenerate_chunks_on_strategy_change(self, db_session):
        """Cambiar de estrategia y recalcular deja el corpus con la nueva.

        No hizo falta tocar `corpus_recalculator`: ya regeneraba llamando al watcher, y el
        watcher lee la cascada desde RAG.8. Se comprueba en vez de darlo por hecho, porque
        «funciona de forma transitiva» es justo la clase de afirmación que este proyecto ha
        visto fallar en silencio varias veces.
        """
        from sqlalchemy import select

        from server.app.modules.agents_hub.database.operational_models import (
            HubDocumentChunk,
        )
        from server.app.modules.agents_hub.services.corpus_recalculator import (
            recalculate_corpus,
        )
        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        _, chatbot = await _organizacion_y_chatbot(db_session)
        await _documento(
            db_session, chatbot.id, language="ca", markdown_content=SECCION_LARGA,
        )
        await db_session.commit()

        await recalculate_corpus(
            session=db_session, chatbot_id=chatbot.id,
            retrieval_mode="RAG", embedding_service=_Emb(),
        )
        await db_session.commit()
        sin_padre = (await db_session.execute(
            select(HubDocumentChunk.parent_content).where(
                HubDocumentChunk.chatbot_id == chatbot.id
            )
        )).scalars().all()
        assert all(p is None for p in sin_padre), "structural no debe dejar padres"

        chatbot.chunking_strategy = "parent_child"
        await db_session.commit()
        await recalculate_corpus(
            session=db_session, chatbot_id=chatbot.id,
            retrieval_mode="RAG", embedding_service=_Emb(),
        )
        await db_session.commit()

        con_padre = (await db_session.execute(
            select(HubDocumentChunk.parent_content).where(
                HubDocumentChunk.chatbot_id == chatbot.id
            )
        )).scalars().all()
        assert con_padre, "no quedo ningun chunk tras regenerar"
        assert all(p for p in con_padre), "parent_child debe dejar padre en cada hijo"
