"""ACT.8 — quien busca por fragmentos, los tiene.

La ingesta troceaba y embebía **sólo en modo RAG**. El banco agéntico está en
`MD_AGENT_SELECTOR`, así que al actualizar el corpus sus 6 documentos nuevos entraron **sin un
solo fragmento**, y el informe decía `ingeridos=6` sin mentir: el documento sí entró.

La premisa —«los otros dos modos no embeben nada»— estaba escrita igual en tres sitios del
código, así que fue una decisión. Pero es **anterior** a que el agéntico tuviera búsqueda por
fragmentos: su herramienta `search_knowledge` consulta justamente el índice vectorial, y el
bloque HIB reparó sus 14.198 fragmentos dejando escrito que «no son peso muerto».

**Y había un defecto latente peor que el hueco**: la rama que no trocea **borra** los fragmentos
que hubiera, así que reingerir un documento del agéntico le quitaba los que ya tenía.

La pregunta correcta no es el modo sino **si el asistente busca por fragmentos**. `RAG` los usa
como única vía y `MD_AGENT_SELECTOR` a través de `search_knowledge`; `MD_LONG_CONTEXT` no los
usa nunca —inyecta documentos enteros—, y ahí el borrado sigue siendo lo correcto.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select


async def _fragmentos(session, document_id) -> int:
    from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk

    return await session.scalar(
        select(func.count(HubDocumentChunk.id)).where(
            HubDocumentChunk.document_id == document_id
        )
    )


class _Embedding:
    model_name = "BAAI/bge-m3"
    dimensions = 1024

    def __init__(self) -> None:
        self.llamadas = 0

    async def embed(self, text: str) -> list[float]:
        self.llamadas += 1
        return [0.1] * 1024


class _Modo:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str:
        return self.mode


async def _ingerir(session, chatbot_id, modo: str, *, url: str, texto: str):
    from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

    watcher = IngestionWatcher(session, _Embedding(), chatbot_provider=_Modo(modo))
    doc, n = await watcher.process_source(
        source_url=url,
        chatbot_id=chatbot_id,
        language="val",
        citation_url=url,
        prefetched_content=texto,
        title="Norma de prova",
    )
    return doc, n


TEXTO = "# Norma\n\n##### Article 1. Objecte {#art-1}\n\nEl text de la norma.\n"


class TestQuienBuscaPorFragmentosLosTiene:

    @pytest.mark.asyncio
    async def test_should_chunk_for_the_agentic_mode(self, db_session):
        """El hueco: 6 documentos entraron sin un solo fragmento."""
        cb = uuid.uuid4()
        doc, n = await _ingerir(
            db_session, cb, "MD_AGENT_SELECTOR",
            url="https://www.uji.es/act8-a", texto=TEXTO,
        )
        await db_session.commit()

        assert n > 0, "el agéntico busca por fragmentos con `search_knowledge`"
        assert await _fragmentos(db_session, doc.id) > 0

    @pytest.mark.asyncio
    async def test_should_still_chunk_for_rag(self, db_session):
        cb = uuid.uuid4()
        doc, n = await _ingerir(
            db_session, cb, "RAG", url="https://www.uji.es/act8-b", texto=TEXTO,
        )
        await db_session.commit()

        assert n > 0
        assert await _fragmentos(db_session, doc.id) > 0

    @pytest.mark.asyncio
    async def test_should_not_chunk_for_long_context(self, db_session):
        """El único modo que de verdad no consulta el índice: inyecta documentos enteros."""
        cb = uuid.uuid4()
        doc, n = await _ingerir(
            db_session, cb, "MD_LONG_CONTEXT",
            url="https://www.uji.es/act8-c", texto=TEXTO,
        )
        await db_session.commit()

        assert n == 0
        assert await _fragmentos(db_session, doc.id) == 0

    @pytest.mark.asyncio
    async def test_should_keep_an_index_after_reingesting_the_agentic(self, db_session):
        """El defecto latente, peor que el hueco: el agéntico se vaciaba solo.

        Cuando el cuerpo de una norma cambia, `process_source` **borra el documento anterior** y
        crea uno nuevo. Con el troceado apagado para este modo, el nuevo nacía sin fragmentos: el
        agéntico habría ido perdiendo su índice norma a norma, según se fueran actualizando, y
        `search_knowledge` habría dejado de verlas sin que nada avisara.
        """
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        cb = uuid.uuid4()
        url = "https://www.uji.es/act8-d"
        await _ingerir(db_session, cb, "RAG", url=url, texto=TEXTO)
        await db_session.commit()

        await _ingerir(
            db_session, cb, "MD_AGENT_SELECTOR", url=url,
            texto=TEXTO + "\n##### Article 2. Ambit {#art-2}\n\nMes text.\n",
        )
        await db_session.commit()

        vigente = await db_session.scalar(
            select(HubDocument).where(
                HubDocument.chatbot_id == cb, HubDocument.canonical_url == url
            )
        )
        assert vigente is not None
        assert await _fragmentos(db_session, vigente.id) > 0, (
            "la norma actualizada se quedó sin fragmentos: `search_knowledge` deja de verla"
        )

    @pytest.mark.asyncio
    async def test_should_wipe_them_when_the_mode_really_does_not_use_them(self, db_session):
        """Cambiar a contexto largo sí limpia: allí los fragmentos son peso muerto."""
        cb = uuid.uuid4()
        url = "https://www.uji.es/act8-e"
        doc, _ = await _ingerir(db_session, cb, "RAG", url=url, texto=TEXTO)
        await db_session.commit()
        assert await _fragmentos(db_session, doc.id) > 0

        await _ingerir(db_session, cb, "MD_LONG_CONTEXT", url=url, texto=TEXTO)
        await db_session.commit()

        assert await _fragmentos(db_session, doc.id) == 0


class TestLaPremisaViveEnUnSoloSitio:
    """Estaba escrita igual en tres, y por eso envejeció sin que nadie la revisara."""

    def test_should_declare_the_modes_once(self):
        from server.app.modules.agents_hub.ingestion.watcher import (
            MODOS_QUE_BUSCAN_POR_FRAGMENTOS,
        )

        assert set(MODOS_QUE_BUSCAN_POR_FRAGMENTOS) == {"RAG", "MD_AGENT_SELECTOR"}

    def test_should_be_the_same_list_everywhere(self):
        from server.app.modules.agents_hub.ingestion.watcher import (
            MODOS_QUE_BUSCAN_POR_FRAGMENTOS,
        )
        from server.app.modules.agents_hub.services.corpus_recalculator import (
            MODOS_QUE_BUSCAN_POR_FRAGMENTOS as DEL_RECALCULADOR,
        )

        assert DEL_RECALCULADOR is MODOS_QUE_BUSCAN_POR_FRAGMENTOS


class TestElRecalculadorTambien:

    @pytest.mark.asyncio
    async def test_should_rebuild_the_index_for_the_agentic(self, db_session):
        from server.app.modules.agents_hub.services.corpus_recalculator import (
            recalculate_corpus,
        )

        cb = uuid.uuid4()
        doc, _ = await _ingerir(
            db_session, cb, "RAG", url="https://www.uji.es/act8-f", texto=TEXTO,
        )
        await db_session.commit()

        docs, creados, borrados = await recalculate_corpus(
            session=db_session,
            chatbot_id=cb,
            retrieval_mode="MD_AGENT_SELECTOR",
            embedding_service=_Embedding(),
        )
        await db_session.commit()

        assert docs == 1
        assert creados > 0, "recalcular en modo agéntico tiene que rehacer el índice"
        assert borrados == 0
