"""Tests VIS.3 — una sola versión indexada y una advertencia honesta (lado recuperación).

Dos hechos medidos en el informe que justifican este prompt: 233 fichas en valenciano y 81
en castellano, muchas la MISMA norma indexada dos veces (el mismo contenido ocupando dos
plazas del top-k); y 312 de 314 fichas con la vigencia sin validar («vigent?»), que es el
riesgo nº1 del corpus.

El aviso en la respuesta se prueba aparte, en `tests/public_graphs/test_vis_vigencia.py`:
aquí solo lo que decide la capa de recuperación.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _chunk,
    _documento,
    _emb,
)


class TestUnaVersionPorNorma:
    """ACT.3 reemplaza a la canonica: la version que vuelve es la de la LENGUA de la pregunta.

    Estos tests decian «solo la canonica se recupera», que era cierto y era el defecto: la
    version castellana de una norma bilingue no volvia nunca, asi que preguntar en castellano
    daba el texto valenciano. Lo que se conserva de VIS.3 es el invariante que de verdad
    importaba —**el mismo contenido no puede ocupar dos plazas del top-k**— y ahora se cumple
    sin declarar que una version vale mas que la otra.
    """

    @pytest.mark.asyncio
    async def test_should_retrieve_one_version_only(self, db_session):
        """El invariante que VIS.3 protegia, ahora resuelto por la lengua."""
        from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
            MetadataFilter,
        )
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        val = await _documento(db_session, cb, title="Reglament", language="val")
        es = await _documento(
            db_session, cb, title="Reglamento", language="es",
            versio_idiomatica_de=val.id,
        )
        await _chunk(db_session, cb, val, "Article 1 del reglament")
        await _chunk(db_session, cb, es, "Articulo 1 del reglamento", language="es")
        await db_session.commit()

        retriever = HybridRetriever(db_session)
        en_val = await retriever.vector_search(
            _emb(0), cb, top_k=10, metadata_filter=MetadataFilter(query_language="val")
        )
        en_es = await retriever.vector_search(
            _emb(0), cb, top_k=10, metadata_filter=MetadataFilter(query_language="es")
        )

        assert [r.content for r in en_val] == ["Article 1 del reglament"]
        assert [r.content for r in en_es] == ["Articulo 1 del reglamento"]

    @pytest.mark.asyncio
    async def test_should_read_language_variant_by_id_on_demand(self, db_session):
        """La otra lengua es legible por id cuando el usuario pide la cita literal."""
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )

        cb = uuid.uuid4()
        val = await _documento(db_session, cb, title="Reglament", language="val")
        es = await _documento(
            db_session, cb, title="Reglamento", language="es",
            versio_idiomatica_de=val.id,
            markdown_content="# Reglamento\n\nArticulo 1.",
        )
        await db_session.commit()

        estrategia = AgenticRetrievalStrategy(db_session)

        # El emparejamiento declara donde esta la hermana, en los dos sentidos.
        assert (await estrategia.read(val.id))["variant_id"] == str(es.id)
        assert (await estrategia.read(es.id))["variant_id"] == str(val.id)

        leida = await estrategia.read(es.id)
        assert "Articulo 1" in leida["markdown_content"]
        assert leida["language"] == "es"

    @pytest.mark.asyncio
    async def test_should_list_only_the_version_of_the_query_language(self, db_session):
        """El indice del agentico ensena UNA ficha por norma, no la canonica."""
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )

        cb = uuid.uuid4()
        val = await _documento(db_session, cb, title="Reglament", language="val")
        await _documento(
            db_session, cb, title="Reglamento", language="es",
            versio_idiomatica_de=val.id,
        )
        await db_session.commit()

        estrategia = AgenticRetrievalStrategy(db_session)

        assert [f["title"] for f in await estrategia.list_index(cb, language="val")] == [
            "Reglament"
        ]
        assert [f["title"] for f in await estrategia.list_index(cb, language="es")] == [
            "Reglamento"
        ]


class TestDerogats:

    @pytest.mark.asyncio
    async def test_should_exclude_derogated_documents_from_retrieval(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
            MetadataFilter,
        )
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        derogat = await _documento(db_session, cb, title="Derogat", estat_vigencia="derogat")
        vigent = await _documento(db_session, cb, title="Vigent", estat_vigencia="vigent")
        dubtos = await _documento(db_session, cb, title="Dubtos", estat_vigencia="vigent?")
        await _chunk(db_session, cb, derogat, "Text derogat")
        await _chunk(db_session, cb, vigent, "Text vigent")
        await _chunk(db_session, cb, dubtos, "Text dubtos")
        await db_session.commit()

        retriever = HybridRetriever(db_session)
        results = await retriever.vector_search(_emb(0), cb, top_k=10)
        # Ni con el filtro más abierto: derogado no es una preferencia de recuperación
        abierto = await retriever.vector_search(
            _emb(0), cb, top_k=10,
            metadata_filter=MetadataFilter(
                include_superseded=True,
                max_nivell_acces="restringit",
            ),
        )

        assert sorted(r.content for r in results) == ["Text dubtos", "Text vigent"]
        assert all("derogat" not in r.content for r in abierto)

    @pytest.mark.asyncio
    async def test_should_still_allow_derogated_document_by_explicit_id(self, db_session):
        """Citar la norma que YA no rige es una consulta legítima; hay que poder leerla."""
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )

        cb = uuid.uuid4()
        derogat = await _documento(
            db_session, cb, title="Derogat", estat_vigencia="derogat",
            markdown_content="# Norma derogada\n\nArticle 1.",
        )
        await db_session.commit()

        leida = await AgenticRetrievalStrategy(db_session).read(derogat.id)

        assert "Article 1" in leida["markdown_content"]
        assert leida["estat_vigencia"] == "derogat"

    @pytest.mark.asyncio
    async def test_should_exclude_derogated_from_long_context_and_index(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )

        cb = uuid.uuid4()
        await _documento(db_session, cb, title="Derogat", estat_vigencia="derogat")
        await _documento(db_session, cb, title="Vigent", estat_vigencia="vigent")
        await db_session.commit()

        ctx = await LongContextRetrievalStrategy(db_session).get_context("q", cb)
        fichas = await AgenticRetrievalStrategy(db_session).list_index(cb, language=None)

        assert [s.title for s in ctx.sources] == ["Vigent"]
        assert [f["title"] for f in fichas] == ["Vigent"]


class TestBanderaDeVigencia:
    """La recuperación marca el documento; el aviso lo emite la capa de respuesta."""

    @pytest.mark.asyncio
    async def test_should_flag_unvalidated_vigencia_in_retrieved_sources(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )

        cb = uuid.uuid4()
        await _documento(db_session, cb, title="Sense validar", estat_vigencia="vigent?")
        await db_session.commit()

        ctx = await LongContextRetrievalStrategy(db_session).get_context("q", cb)

        assert ctx.sources[0].metadata["vigencia_no_validada"] is True

    @pytest.mark.asyncio
    async def test_should_not_flag_when_vigencia_is_validated(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )

        cb = uuid.uuid4()
        await _documento(
            db_session, cb, title="Validada", estat_vigencia="vigent",
            vigencia_validada_el=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
        await db_session.commit()

        ctx = await LongContextRetrievalStrategy(db_session).get_context("q", cb)

        assert ctx.sources[0].metadata["vigencia_no_validada"] is False

    @pytest.mark.asyncio
    async def test_should_flag_unvalidated_vigencia_in_vector_sources(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        class _Emb:
            async def embed(self, text: str):
                return _emb(0)

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, title="Sense validar", estat_vigencia="vigent?")
        await _chunk(db_session, cb, doc, "Article 1")
        await db_session.commit()

        ctx = await VectorRetrievalStrategy(db_session, _Emb(), top_k=5).get_context("q", cb)

        assert ctx.sources[0].metadata["vigencia_no_validada"] is True
