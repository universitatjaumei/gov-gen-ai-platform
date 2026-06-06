"""Tests TDD — Retrieval que excluye páginas superseded (Prompt 9Q.6).

El retriever deja de servir chunks cuyo documento proviene de una página
marcada superseded=True. El flag vive en HubCrawledPage; la cadena es
chunk.document_id → HubDocument.crawled_page_id → HubCrawledPage.superseded.

Fakes en memoria: sin BD ni pgvector real. Se prueba la lógica de filtrado
mediante una subclase de HybridRetriever con _get_superseded_doc_ids mockeada.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest

# ───────────────────────── Fakes ─────────────────────────


class _FakeChunk:
    """Fake de HubDocumentChunk con los atributos que usa el retriever."""

    def __init__(
        self,
        chatbot_id: uuid.UUID,
        content: str,
        source_url: str,
        language: str = "es",
        document_id: uuid.UUID | None = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.chatbot_id = chatbot_id
        self.content = content
        self.source_url = source_url
        self.language = language
        self.document_id = document_id
        self.chunk_metadata = {"document_id": str(document_id)} if document_id else {}
        self.embedding = [0.1] * 1024
        self.is_temporary = False
        self.owner_id = None


class _FakeRow:
    """Fila con atributo HubDocumentChunk para simular el resultado de vector_search."""

    def __init__(self, chunk: _FakeChunk, score: float = 0.8) -> None:
        self.HubDocumentChunk = chunk
        self.score = score


class _FakeScalars:
    def __init__(self, items: list) -> None:
        self._items = items

    def all(self) -> list:
        return self._items


class _FakeResult:
    """Soporta tanto .all() (vector rows) como .scalars().all() (keyword scalars)."""

    def __init__(self, chunks: list[_FakeChunk]) -> None:
        self._chunks = chunks

    def all(self) -> list[_FakeRow]:
        return [_FakeRow(c) for c in self._chunks]

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._chunks)


class _FakeSession:
    """Siempre devuelve los mismos chunks independientemente del statement SQL."""

    def __init__(self, chunks: list[_FakeChunk]) -> None:
        self._chunks = chunks

    async def execute(self, stmt: Any) -> _FakeResult:
        return _FakeResult(self._chunks)


class _TestableRetriever:
    """HybridRetriever con _get_superseded_doc_ids inyectable para tests unitarios."""

    def __init__(
        self,
        session: _FakeSession,
        superseded_doc_ids: set[str] | None = None,
    ) -> None:
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        self._retriever = HybridRetriever(session)  # type: ignore[arg-type]
        # Override _get_superseded_doc_ids so the test controls what's "superseded"
        fake_ids = superseded_doc_ids or set()
        self._retriever._get_superseded_doc_ids = lambda chatbot_id: _async_return(fake_ids)

    async def vector_search(self, **kw: Any):
        return await self._retriever.vector_search(**kw)

    async def keyword_search(self, **kw: Any):
        return await self._retriever.keyword_search(**kw)

    async def hybrid_search(self, **kw: Any):
        return await self._retriever.hybrid_search(**kw)


async def _async_return(value):
    return value


# ───────────────────────── Fixtures ─────────────────────────


def _make_setup():
    """Devuelve chatbot_id, doc_id_superseded, doc_id_ok, chunk_superseded, chunk_ok."""
    chatbot_id = uuid.uuid4()
    doc_superseded = uuid.uuid4()
    doc_ok = uuid.uuid4()
    chunk_sup = _FakeChunk(chatbot_id, "Texto obsoleto", "https://ej.es/2022/x", document_id=doc_superseded)
    chunk_ok = _FakeChunk(chatbot_id, "Texto vigente", "https://ej.es/2024/x", document_id=doc_ok)
    return chatbot_id, doc_superseded, doc_ok, chunk_sup, chunk_ok


# ───────────────────────── Tests ─────────────────────────


@pytest.mark.asyncio
async def test_vector_search_excludes_superseded_by_default():
    """Página superseded → chunk de su documento NO aparece en vector_search."""
    chatbot_id, doc_sup, doc_ok, chunk_sup, chunk_ok = _make_setup()
    session = _FakeSession([chunk_sup, chunk_ok])
    retriever = _TestableRetriever(session, superseded_doc_ids={str(doc_sup)})

    results = await retriever.vector_search(
        query_embedding=[0.1] * 1024,
        chatbot_id=chatbot_id,
    )

    content_set = {r.content for r in results}
    assert chunk_sup.content not in content_set
    assert chunk_ok.content in content_set


@pytest.mark.asyncio
async def test_vector_search_include_superseded_true_shows_all():
    """include_superseded=True → el chunk superseded reaparece en los resultados."""
    chatbot_id, doc_sup, doc_ok, chunk_sup, chunk_ok = _make_setup()
    session = _FakeSession([chunk_sup, chunk_ok])
    retriever = _TestableRetriever(session, superseded_doc_ids={str(doc_sup)})

    results = await retriever.vector_search(
        query_embedding=[0.1] * 1024,
        chatbot_id=chatbot_id,
        include_superseded=True,
    )

    content_set = {r.content for r in results}
    assert chunk_sup.content in content_set
    assert chunk_ok.content in content_set


@pytest.mark.asyncio
async def test_keyword_search_excludes_superseded():
    """keyword_search también excluye chunks de páginas superseded."""
    chatbot_id, doc_sup, doc_ok, chunk_sup, chunk_ok = _make_setup()
    session = _FakeSession([chunk_sup, chunk_ok])
    retriever = _TestableRetriever(session, superseded_doc_ids={str(doc_sup)})

    results = await retriever.keyword_search(
        query="Texto",
        chatbot_id=chatbot_id,
    )

    content_set = {r.content for r in results}
    assert chunk_sup.content not in content_set
    assert chunk_ok.content in content_set


@pytest.mark.asyncio
async def test_keyword_search_include_superseded_true():
    """keyword_search con include_superseded=True restaura el chunk superseded."""
    chatbot_id, doc_sup, _, chunk_sup, chunk_ok = _make_setup()
    session = _FakeSession([chunk_sup, chunk_ok])
    retriever = _TestableRetriever(session, superseded_doc_ids={str(doc_sup)})

    results = await retriever.keyword_search(
        query="Texto",
        chatbot_id=chatbot_id,
        include_superseded=True,
    )

    content_set = {r.content for r in results}
    assert chunk_sup.content in content_set


@pytest.mark.asyncio
async def test_not_superseded_page_not_filtered():
    """Chunks de páginas no superseded aparecen normalmente (sin regresión)."""
    chatbot_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk = _FakeChunk(chatbot_id, "Contenido activo", "https://ej.es/activo", document_id=doc_id)
    session = _FakeSession([chunk])
    # Sin superseded_doc_ids → ningún doc excluido
    retriever = _TestableRetriever(session, superseded_doc_ids=set())

    results = await retriever.vector_search(
        query_embedding=[0.1] * 1024,
        chatbot_id=chatbot_id,
    )

    assert any(r.content == chunk.content for r in results)


@pytest.mark.asyncio
async def test_chunk_without_document_id_never_filtered():
    """HubDocument con crawled_page_id=None (PDF subido) → chunk nunca excluido.

    Los chunks legacy sin document_id en chunk_metadata no tienen página de origen
    y deben permanecer en resultados aunque include_superseded=False.
    """
    chatbot_id = uuid.uuid4()
    # Chunk sin document_id → chunk_metadata vacío → no en ningún set de exclusión
    chunk_legacy = _FakeChunk(chatbot_id, "PDF subido", "file://local.pdf", document_id=None)
    # Forzamos que _get_superseded_doc_ids devuelva algo para verificar que no afecta
    some_other_doc = uuid.uuid4()
    session = _FakeSession([chunk_legacy])
    retriever = _TestableRetriever(session, superseded_doc_ids={str(some_other_doc)})

    results = await retriever.vector_search(
        query_embedding=[0.1] * 1024,
        chatbot_id=chatbot_id,
    )

    assert any(r.content == chunk_legacy.content for r in results)


@pytest.mark.asyncio
async def test_two_chatbots_both_exclude_when_superseded():
    """Misma página ingerida por 2 chatbots → ambos excluyen sus chunks al marcarse superseded."""
    chatbot_a = uuid.uuid4()
    chatbot_b = uuid.uuid4()
    doc_a = uuid.uuid4()  # Documento del chatbot A desde la página superseded
    doc_b = uuid.uuid4()  # Documento del chatbot B desde la misma página superseded

    chunk_a = _FakeChunk(chatbot_a, "Contenido A de página obsoleta", "https://ej.es/p", document_id=doc_a)
    chunk_b = _FakeChunk(chatbot_b, "Contenido B de página obsoleta", "https://ej.es/p", document_id=doc_b)

    # Cada retriever tiene su propio set de doc IDs superseded (por chatbot)
    retriever_a = _TestableRetriever(_FakeSession([chunk_a]), superseded_doc_ids={str(doc_a)})
    retriever_b = _TestableRetriever(_FakeSession([chunk_b]), superseded_doc_ids={str(doc_b)})

    results_a = await retriever_a.vector_search(query_embedding=[0.1] * 1024, chatbot_id=chatbot_a)
    results_b = await retriever_b.vector_search(query_embedding=[0.1] * 1024, chatbot_id=chatbot_b)

    assert results_a == []
    assert results_b == []


@pytest.mark.asyncio
async def test_hybrid_search_excludes_superseded():
    """hybrid_search excluye chunks de páginas superseded."""
    chatbot_id, doc_sup, doc_ok, chunk_sup, chunk_ok = _make_setup()
    session = _FakeSession([chunk_sup, chunk_ok])
    retriever = _TestableRetriever(session, superseded_doc_ids={str(doc_sup)})

    results = await retriever.hybrid_search(
        query="Texto",
        query_embedding=[0.1] * 1024,
        chatbot_id=chatbot_id,
    )

    content_set = {r.content for r in results}
    assert chunk_sup.content not in content_set
    assert chunk_ok.content in content_set


@pytest.mark.asyncio
async def test_hybrid_search_rrf_order_maintained_after_filtering():
    """hybrid_search mantiene el orden RRF después de excluir superseded."""
    chatbot_id = uuid.uuid4()
    doc_sup = uuid.uuid4()
    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()
    doc_c = uuid.uuid4()

    # chunk_sup es el que se filtra; a, b, c deben ordenarse por RRF
    chunk_sup = _FakeChunk(chatbot_id, "Obsoleto", "https://ej.es/s", document_id=doc_sup)
    chunk_a = _FakeChunk(chatbot_id, "Primero activo", "https://ej.es/a", document_id=doc_a)
    chunk_b = _FakeChunk(chatbot_id, "Segundo activo", "https://ej.es/b", document_id=doc_b)
    chunk_c = _FakeChunk(chatbot_id, "Tercero activo", "https://ej.es/c", document_id=doc_c)

    session = _FakeSession([chunk_a, chunk_b, chunk_sup, chunk_c])
    retriever = _TestableRetriever(session, superseded_doc_ids={str(doc_sup)})

    results = await retriever.hybrid_search(
        query="Primero",
        query_embedding=[0.1] * 1024,
        chatbot_id=chatbot_id,
    )

    # El obsoleto no debe estar
    content_set = {r.content for r in results}
    assert chunk_sup.content not in content_set
    # Los scores deben estar en orden descendente (RRF)
    for i in range(len(results) - 1):
        assert results[i].score >= results[i + 1].score
