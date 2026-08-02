"""Prompt DET.1 — El orden del retriever deja de depender del plan de la consulta.

Dos fragmentos con la misma puntuación salían en el orden que quisiera el planificador, y eso
en un asistente normativo decide **qué norma se cita**. Se desempata por `content_hash`, que se
deriva del contenido del fragmento y por tanto sobrevive a una reingesta — `id` es un uuid4 y
rebarajaría los empates en cada recarga del corpus.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

# Ortogonales de verdad. Un `[0.1]*1024` frente a un `[0.9]*1024` NO sirve: el coseno ignora
# la magnitud, así que dos vectores paralelos dan similitud 1.0 y no habría nada lejano.
EMBEDDING_A = [0.0] * 512 + [1.0] + [0.0] * 511
EMBEDDING_LEJANO = [1.0] + [0.0] * 1023


@pytest.fixture
async def chatbot_con_empates(db_session):
    """Chatbot con dos pares de fragmentos empatados y uno que no empata con nadie.

    Los `content_hash` se fijan a mano —`aaa`/`bbb`— para que el orden esperado sea legible
    en la aserción y no dependa de qué texto hashea más bajo.
    """
    from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk

    chatbot_id = uuid.uuid4()
    db_session.add_all([
        # Empate vectorial exacto: mismo embedding, documentos distintos.
        HubDocumentChunk(
            chatbot_id=chatbot_id,
            content="Les practiques externes es tutoritzen pel professorat",
            source_url="https://uji.es/REG-114",
            content_hash="bbb",
            embedding=EMBEDDING_A,
            language="ca",
            embedding_model="test/bow",
            embedding_dim=1024,
        ),
        HubDocumentChunk(
            chatbot_id=chatbot_id,
            content="Les practiques externes es tutoritzen pel professorat",
            source_url="https://uji.es/REG-104",
            content_hash="aaa",
            embedding=EMBEDDING_A,
            language="ca",
            embedding_model="test/bow",
            embedding_dim=1024,
        ),
        # No empata: embedding lejano y sin el vocabulario de la consulta.
        HubDocumentChunk(
            chatbot_id=chatbot_id,
            content="Import maxim allotjament viatge",
            source_url="https://uji.es/REG-020",
            content_hash="zzz",
            embedding=EMBEDDING_LEJANO,
            language="ca",
            embedding_model="test/bow",
            embedding_dim=1024,
        ),
    ])
    await db_session.commit()
    return chatbot_id


class TestDesempateDeterminista:

    @pytest.mark.asyncio
    async def test_should_break_vector_ties_by_content_hash(
        self, chatbot_con_empates, db_session
    ):
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        resultados = await HybridRetriever(db_session).vector_search(
            EMBEDDING_A, chatbot_con_empates, top_k=10
        )

        empatados = [r for r in resultados if r.score > 0.99]
        assert len(empatados) == 2, "el fixture debe producir dos empatados exactos"
        assert [r.source_url for r in empatados] == [
            "https://uji.es/REG-104",
            "https://uji.es/REG-114",
        ], "los empatados deben salir por content_hash ascendente (aaa antes que bbb)"

    @pytest.mark.asyncio
    async def test_should_break_keyword_ties_by_content_hash(
        self, chatbot_con_empates, db_session
    ):
        """Los dos empatados tienen el MISMO texto, así que `ts_rank_cd` los empata."""
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        resultados = await HybridRetriever(db_session).keyword_search(
            "practiques externes", chatbot_con_empates, top_k=10, language="ca"
        )

        urls = [r.source_url for r in resultados]
        assert urls[:2] == [
            "https://uji.es/REG-104",
            "https://uji.es/REG-114",
        ], f"la rama lexica no desempata de forma estable: {urls}"

    @pytest.mark.asyncio
    async def test_should_keep_the_same_order_across_plans(
        self, chatbot_con_empates, db_session
    ):
        """Mismo orden con y sin escaneo secuencial: el plan deja de decidir."""
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        retriever = HybridRetriever(db_session)
        con_indice = await retriever.hybrid_search(
            query="practiques externes",
            query_embedding=EMBEDDING_A,
            chatbot_id=chatbot_con_empates,
            top_k=5,
        )

        await db_session.execute(text("SET LOCAL enable_indexscan = off"))
        await db_session.execute(text("SET LOCAL enable_bitmapscan = off"))
        sin_indice = await retriever.hybrid_search(
            query="practiques externes",
            query_embedding=EMBEDDING_A,
            chatbot_id=chatbot_con_empates,
            top_k=5,
        )

        assert [r.source_url for r in con_indice] == [
            r.source_url for r in sin_indice
        ], "el orden cambia segun el plan: el desempate no es estable"

    @pytest.mark.asyncio
    async def test_should_not_reorder_results_that_do_not_tie(
        self, chatbot_con_empates, db_session
    ):
        """El desempate solo actúa sobre iguales: no puede tocar el orden por puntuación.

        `zzz` hashea por encima de `aaa`/`bbb` pero está lejos en el espacio vectorial, así que
        tiene que quedar el último. Si el desempate se aplicara mal, subiría.
        """
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        resultados = await HybridRetriever(db_session).vector_search(
            EMBEDDING_A, chatbot_con_empates, top_k=10
        )

        assert resultados[-1].source_url == "https://uji.es/REG-020"
        puntuaciones = [r.score for r in resultados]
        assert puntuaciones == sorted(puntuaciones, reverse=True)

    @pytest.mark.asyncio
    async def test_should_keep_hnsw_usable_by_the_vector_branch(self, db_session):
        """La restricción dura de DET.1: el ORDER BY vectorial se queda a secas.

        pgvector solo sirve el índice HNSW para `ORDER BY <distancia>` sin más claves. Si
        alguien añade el desempate al SQL, el plan cae a `Seq Scan + Sort` y RAG.3 queda
        deshecho sin que ningún otro test se entere.
        """
        vector = "[" + ",".join(["1.0"] + ["0.0"] * 1023) + "]"
        await db_session.execute(text("SET LOCAL enable_seqscan = off"))
        plan = await db_session.execute(
            text(
                "EXPLAIN SELECT id FROM hub_document_chunks "
                "ORDER BY embedding <=> :v LIMIT 10"
            ),
            {"v": vector},
        )
        lineas = " ".join(str(fila[0]) for fila in plan)

        assert "ix_hub_document_chunks_embedding_hnsw" in lineas, (
            "la rama vectorial ya no puede usar HNSW: el ORDER BY ha dejado de ser "
            f"`embedding <=> $1` a secas.\n{lineas[:400]}"
        )
