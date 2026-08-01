"""Prompt 2.6 â€” Tests del retriever hÃ­brido (TDD - RED â†’ GREEN).

La fixture base `db_session` vive en el conftest.py de este directorio y usa una BD
desechable por test: antes este fichero creaba y DESTRUÃA las tablas de la BD de
desarrollo.
"""
import uuid
import pytest
from sqlalchemy import text


@pytest.fixture
async def populated_session(db_session):
    """SesiÃ³n con datos de prueba para el retriever."""
    from server.app.modules.agents_hub.database.config_models import HubChatbot, HubOrganizacion, HubLLMConfig, HubProvider
    from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk

    session = db_session
    if True:
        await session.merge(HubProvider(id="google", name="Google", provider_type="google_genai"))
        await session.commit()

        llm = HubLLMConfig(provider="google", model_name="gemini-flash")
        session.add(llm)
        client = HubOrganizacion(name="Retriever Test", partner_id="partner_dev")
        session.add(client)
        await session.flush()

        chatbot = HubChatbot(
            organizacion_id=client.id,
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
                language="es",
                embedding_model="BAAI/bge-m3",
                embedding_dim=1024,
            ),
            HubDocumentChunk(
                chatbot_id=chatbot.id,
                content="Java es diferente a Python",
                source_url="url2",
                content_hash="h2",
                embedding=[0.9] * 1024,
                language="es",
                embedding_model="BAAI/bge-m3",
                embedding_dim=1024,
            ),
        ]
        session.add_all(chunks)
        await session.commit()

        yield session, chatbot.id


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


# ─────────────────── RAG.4: pata léxica real (tsvector + GIN) ───────────────────
#
# El `ILIKE` que había aquí antes no era búsqueda léxica: era subcadena. No hacía
# stemming ('becas' no encontraba 'beca'), no ordenaba por relevancia —todos los
# resultados valían 1.0— y encadenaba un AND por palabra, así que una palabra de más
# vaciaba el resultado. Se sustituye por `tsvector` + `websearch_to_tsquery`.

from server.tests.modules.agents_hub.integration.test_metadata_filter import (  # noqa: E402
    _chunk,
    _documento,
    _emb,
)


class TestBusquedaLexica:

    @pytest.mark.asyncio
    async def test_should_match_stemmed_spanish_terms(self, db_session):
        """'becas' encuentra 'beca'. Con ILIKE no lo hacía: son subcadenas distintas."""
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="es")
        await _chunk(
            db_session, cb, doc,
            "La beca se concede al estudiante que acredite el requisito",
            language="es",
        )
        await db_session.commit()

        resultados = await HybridRetriever(db_session).keyword_search(
            "becas", cb, top_k=5, language="es"
        )

        assert len(resultados) == 1

    @pytest.mark.asyncio
    async def test_should_use_simple_config_for_catalan_chunks(self, db_session):
        """El catalán no tiene stemmer en PostgreSQL core: config 'simple', sin stemming.

        La consecuencia hay que conocerla: en catalán se busca por forma exacta de la
        palabra. Un diccionario Snowball catalán sería mejora de despliegue, no de código.
        """
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="ca")
        await _chunk(db_session, cb, doc, "La beca es concedeix a l'estudiant", language="ca")
        await db_session.commit()

        retriever = HybridRetriever(db_session)
        exacta = await retriever.keyword_search("beca", cb, top_k=5, language="ca")
        flexionada = await retriever.keyword_search("beques", cb, top_k=5, language="ca")

        assert len(exacta) == 1
        assert flexionada == []

    @pytest.mark.asyncio
    async def test_should_rank_chunks_with_exact_terminology_first(self, db_session):
        """Siglas y códigos son lo que más pesa en normativa: 'EBEP', 'RD 203/2021'."""
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="es")
        await _chunk(
            db_session, cb, doc,
            "El EBEP regula el regimen del personal y el EBEP se aplica con caracter basico",
            language="es",
        )
        await _chunk(
            db_session, cb, doc,
            "Norma generica sobre personal sin referencia al estatuto basico",
            language="es",
        )
        await db_session.commit()

        resultados = await HybridRetriever(db_session).keyword_search(
            "EBEP", cb, top_k=5, language="es"
        )

        assert resultados
        assert "EBEP" in resultados[0].content
        assert all(r.score <= resultados[0].score for r in resultados)

    @pytest.mark.asyncio
    async def test_should_return_normalized_keyword_scores(self, db_session):
        """Antes todos los resultados valían 1.0, que no es una puntuación sino un relleno."""
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="es")
        await _chunk(db_session, cb, doc, "dieta dieta dieta importe", language="es")
        await _chunk(db_session, cb, doc, "texto largo que menciona la dieta una sola vez "
                     + "y sigue hablando de otras cosas distintas", language="es")
        await db_session.commit()

        resultados = await HybridRetriever(db_session).keyword_search(
            "dieta", cb, top_k=5, language="es"
        )

        assert len(resultados) == 2
        assert max(r.score for r in resultados) == pytest.approx(1.0)
        assert all(0.0 <= r.score <= 1.0 for r in resultados)
        assert len({r.score for r in resultados}) == 2

    @pytest.mark.asyncio
    async def test_should_bridge_bilingual_terms_in_lexical_search(self, db_session):
        """'despesa' encuentra el chunk castellano cuyo documento declara despesa/gasto.

        El BM25 cross-lingüe falla del todo aquí: 'despesa' y 'gasto' no comparten una
        letra. El puente va en el tsvector —que se regenera con SQL— y NUNCA en el
        embedding, que costaría GPU y horas por cada revisión del vocabulario.
        """
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(
            db_session, cb, language="es",
            doc_metadata={"termes_bilingues": ["despesa/gasto", "dieta"]},
        )
        # `bilingual_terms` es lo que la ingesta copia del documento al chunk; que lo copie
        # se prueba aparte, en test_ingestion_creates_documents. Aquí se prueba el puente.
        await _chunk(
            db_session, cb, doc,
            "La ejecucion del gasto se autoriza por el organo competente",
            language="es", bilingual_terms="despesa gasto dieta",
        )
        await _chunk(
            db_session, cb, doc, "Norma sin relacion con el asunto economico",
            language="es",
        )
        await db_session.commit()

        resultados = await HybridRetriever(db_session).keyword_search(
            "despesa", cb, top_k=5, language="es"
        )

        assert len(resultados) == 1
        assert "gasto" in resultados[0].content

    @pytest.mark.asyncio
    async def test_should_keep_rrf_fusion_contract_unchanged(self, db_session):
        """La sustitución es de la rama léxica; la fusión RRF (k=60, 0.7) no se toca."""
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="es")
        await _chunk(db_session, cb, doc, "dieta por comision de servicio",
                     embedding=_emb(0), language="es")
        await _chunk(db_session, cb, doc, "otro contenido sin relacion",
                     embedding=_emb(500), language="es")
        await db_session.commit()

        resultados = await HybridRetriever(db_session).hybrid_search(
            query="dieta", query_embedding=_emb(0), chatbot_id=cb, top_k=5, language="es",
        )

        assert resultados
        assert "dieta" in resultados[0].content
        assert [r.score for r in resultados] == sorted(
            (r.score for r in resultados), reverse=True
        )

    @pytest.mark.asyncio
    async def test_should_use_gin_index_in_query_plan(self, db_session):
        from server.app.modules.agents_hub.services.retriever import HybridRetriever  # noqa: F401

        await db_session.execute(text("set local enable_seqscan = off"))
        plan = "\n".join(
            fila[0] for fila in (await db_session.execute(text(
                "explain select id from hub_document_chunks "
                "where tsv @@ websearch_to_tsquery('spanish', 'dieta')"
            ))).all()
        )

        assert "ix_hub_document_chunks_tsv" in plan, plan

    def test_should_have_no_ilike_left_in_retriever(self):
        """Borra, no comentes: el ILIKE desaparece del retriever."""
        from pathlib import Path

        fuente = Path(
            "app/modules/agents_hub/services/retriever.py"
        ).read_text(encoding="utf-8")

        assert "ilike" not in fuente.lower()

    @pytest.mark.asyncio
    async def test_should_refresh_the_bridge_when_the_document_is_relabelled(self, db_session):
        """Reetiquetar cuesta UN UPDATE: ni se trocea ni se embebe de nuevo.

        Es también el hueco que este prompt encontró: el reconciliador aplica el
        front-matter DESPUÉS de trocear, así que un documento recién ingerido nace sin
        puente y hay que refrescarlo. Si no, la búsqueda no falla: deja de encontrar
        'despesa' en silencio.
        """
        from sqlalchemy import select

        from server.app.modules.agents_hub.database.operational_models import (
            HubDocumentChunk,
        )
        from server.app.modules.agents_hub.ingestion.bilingual_bridge import (
            refrescar_puente_bilingue,
        )
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="es")
        chunk = await _chunk(
            db_session, cb, doc,
            "La ejecucion del gasto se autoriza por el organo competente",
            language="es",
        )
        await db_session.commit()

        retriever = HybridRetriever(db_session)
        assert await retriever.keyword_search("despesa", cb, top_k=5, language="es") == []

        # Llega el front-matter con los pares del dominio
        doc.doc_metadata = {"termes_bilingues": ["despesa/gasto"]}
        await refrescar_puente_bilingue(db_session, doc)
        await db_session.commit()

        embedding_intacto = (await db_session.execute(
            select(HubDocumentChunk.embedding).where(HubDocumentChunk.id == chunk.id)
        )).scalar_one()

        resultados = await retriever.keyword_search("despesa", cb, top_k=5, language="es")

        assert len(resultados) == 1
        assert embedding_intacto is not None  # no se re-embebio nada


class TestUmbralDeSimilitud:
    """RAG.5: `min_retrieval_score` se aplica en la rama VECTORIAL, antes de la fusión.

    Solo en la vectorial: la señal de la rama léxica es de ranking, no de similitud, y un
    `ts_rank_cd` de 0,3 no significa lo mismo que un coseno de 0,3. Filtrar las dos con el
    mismo número sería comparar magnitudes distintas.
    """

    @pytest.mark.asyncio
    async def test_should_filter_vector_candidates_below_min_score(self, db_session):
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb)
        await _chunk(db_session, cb, doc, "Muy parecido", embedding=_emb(0))
        await _chunk(db_session, cb, doc, "Nada que ver", embedding=_emb(500))
        await db_session.commit()

        resultados = await HybridRetriever(db_session).vector_search(
            _emb(0), cb, top_k=10, min_score=0.5
        )

        assert [r.content for r in resultados] == ["Muy parecido"]

    @pytest.mark.asyncio
    async def test_should_keep_all_candidates_when_threshold_is_zero(self, db_session):
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb)
        await _chunk(db_session, cb, doc, "Muy parecido", embedding=_emb(0))
        await _chunk(db_session, cb, doc, "Nada que ver", embedding=_emb(500))
        await db_session.commit()

        resultados = await HybridRetriever(db_session).vector_search(
            _emb(0), cb, top_k=10, min_score=0.0
        )

        assert len(resultados) == 2

    @pytest.mark.asyncio
    async def test_should_not_apply_the_threshold_to_the_lexical_branch(self, db_session):
        """El híbrido pasa el umbral a la rama vectorial y NO a la léxica."""
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, language="es")
        # Coseno nulo con la consulta, pero coincidencia léxica exacta
        await _chunk(db_session, cb, doc, "El importe de la dieta es de 53 euros",
                     embedding=_emb(500), language="es")
        await db_session.commit()

        resultados = await HybridRetriever(db_session).hybrid_search(
            query="dieta", query_embedding=_emb(0), chatbot_id=cb, top_k=5,
            language="es", min_score=0.5,
        )

        assert len(resultados) == 1
