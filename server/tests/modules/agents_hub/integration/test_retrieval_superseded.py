"""Tests 9Q.6 — el retriever no sirve chunks de paginas superseded.

Antes vivian en `unit/test_retrieval_quality_filter.py` contra una sesion falsa que
devolvia siempre los mismos chunks y con `_get_superseded_doc_ids` mockeado. VIS.1
retiro ese metodo: la exclusion es ahora una subconsulta correlacionada dentro del
WHERE, asi que solo una BD real puede comprobarla.

La cadena que se prueba: chunk.document_id -> HubDocument.crawled_page_id ->
HubCrawledPage.superseded.
"""
from __future__ import annotations

import uuid

import pytest

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _chunk,
    _documento,
    _emb,
    _pagina_superseded,
)


async def _corpus_con_obsoleto(session, chatbot_id: uuid.UUID):
    """Un documento de pagina superseded y otro vigente, con un chunk cada uno."""
    page = await _pagina_superseded(session)
    obsoleto = await _documento(session, chatbot_id, title="Obsolet", crawled_page_id=page.id)
    vigente = await _documento(session, chatbot_id, title="Vigent")
    await _chunk(session, chatbot_id, obsoleto, "Text obsolet de la pagina retirada")
    await _chunk(session, chatbot_id, vigente, "Text vigent de la pagina actual")
    await session.commit()
    return obsoleto, vigente


@pytest.mark.asyncio
async def test_vector_search_excludes_superseded_by_default(db_session):
    from server.app.modules.agents_hub.services.retriever import HybridRetriever

    cb = uuid.uuid4()
    await _corpus_con_obsoleto(db_session, cb)

    results = await HybridRetriever(db_session).vector_search(_emb(0), cb, top_k=10)

    assert [r.content for r in results] == ["Text vigent de la pagina actual"]


@pytest.mark.asyncio
async def test_keyword_search_excludes_superseded_by_default(db_session):
    from server.app.modules.agents_hub.services.retriever import HybridRetriever

    cb = uuid.uuid4()
    await _corpus_con_obsoleto(db_session, cb)

    results = await HybridRetriever(db_session).keyword_search("Text", cb, top_k=10)

    assert [r.content for r in results] == ["Text vigent de la pagina actual"]


@pytest.mark.asyncio
async def test_include_superseded_restores_the_retired_page(db_session):
    from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
        MetadataFilter,
    )
    from server.app.modules.agents_hub.services.retriever import HybridRetriever

    cb = uuid.uuid4()
    await _corpus_con_obsoleto(db_session, cb)

    results = await HybridRetriever(db_session).vector_search(
        _emb(0), cb, top_k=10,
        metadata_filter=MetadataFilter(include_superseded=True),
    )

    assert len(results) == 2


@pytest.mark.asyncio
async def test_document_without_crawled_page_is_never_excluded(db_session):
    """PDF subido: sin pagina de origen no hay nada que pueda marcarse superseded."""
    from server.app.modules.agents_hub.services.retriever import HybridRetriever

    cb = uuid.uuid4()
    await _pagina_superseded(db_session)  # hay paginas retiradas, pero no de este doc
    pdf = await _documento(db_session, cb, source_kind="upload", crawled_page_id=None)
    await _chunk(db_session, cb, pdf, "Contingut del PDF pujat")
    await db_session.commit()

    results = await HybridRetriever(db_session).vector_search(_emb(0), cb, top_k=10)

    assert [r.content for r in results] == ["Contingut del PDF pujat"]


@pytest.mark.asyncio
async def test_hybrid_search_keeps_rrf_order_after_excluding_superseded(db_session):
    from server.app.modules.agents_hub.services.retriever import HybridRetriever

    cb = uuid.uuid4()
    page = await _pagina_superseded(db_session)
    obsoleto = await _documento(db_session, cb, crawled_page_id=page.id)
    vigente = await _documento(db_session, cb)
    await _chunk(db_session, cb, obsoleto, "Text obsolet", embedding=_emb(0))
    for i in range(3):
        await _chunk(db_session, cb, vigente, f"Text vigent {i}", embedding=_emb(i))
    await db_session.commit()

    results = await HybridRetriever(db_session).hybrid_search(
        query="Text vigent", query_embedding=_emb(0), chatbot_id=cb, top_k=10,
    )

    assert all("obsolet" not in r.content for r in results)
    assert [r.score for r in results] == sorted((r.score for r in results), reverse=True)
