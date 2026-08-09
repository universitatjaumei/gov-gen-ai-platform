"""Tests TDD — CorpusSelectionService (Prompt 9Q.7).

Lógica de selección de candidatas, ingestión manual y retirada de páginas.
Fakes en memoria: sin BD ni embedding real.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest


# ───────────────────────── Fakes ─────────────────────────


class _FakePage:
    def __init__(self, site_id: uuid.UUID, url: str, **kw: Any) -> None:
        self.id = uuid.uuid4()
        self.site_id = site_id
        self.url = url
        self.title = kw.get("title", url)
        self.markdown_content = kw.get("markdown_content", f"# {url}")
        self.status = kw.get("status", "active")


class _FakeSelection:
    def __init__(
        self,
        chatbot_id: uuid.UUID,
        site_id: uuid.UUID,
        rule_type: str = "path_prefix",
        rule_value: str = "/",
        auto_ingest_new: bool = True,
    ) -> None:
        self.id = uuid.uuid4()
        self.chatbot_id = chatbot_id
        self.site_id = site_id
        self.rule_type = rule_type
        self.rule_value = rule_value
        self.auto_ingest_new = auto_ingest_new


class _FakePageRepo:
    def __init__(self, pages: list[_FakePage] | None = None) -> None:
        self._pages = pages or []

    async def list_by_site(self, site_id: uuid.UUID, status: str | None = None) -> list[_FakePage]:
        out = [p for p in self._pages if p.site_id == site_id]
        if status:
            out = [p for p in out if p.status == status]
        return out

    async def get(self, page_id: uuid.UUID) -> _FakePage | None:
        return next((p for p in self._pages if p.id == page_id), None)


class _FakeSelectionRepo:
    def __init__(self, selections: list[_FakeSelection] | None = None) -> None:
        self._selections = selections or []

    async def list_by_chatbot(self, chatbot_id: uuid.UUID) -> list[_FakeSelection]:
        return [s for s in self._selections if s.chatbot_id == chatbot_id]

    def matches(self, selection: _FakeSelection, page_url: str) -> bool:
        if selection.rule_type == "path_prefix" and selection.rule_value:
            from urllib.parse import urlparse
            return urlparse(page_url).path.startswith(selection.rule_value)
        return False


class _FakeWatcher:
    def __init__(self, return_doc: Any = None) -> None:
        self.calls: list[dict] = []
        self._return_doc = return_doc or _FakeDoc()

    async def process_source(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        *,
        prefetched_content: str | None = None,
        title: str | None = None,
        crawled_page_id: uuid.UUID | None = None,
    ) -> tuple:
        self.calls.append({
            "source_url": source_url,
            "chatbot_id": chatbot_id,
            "crawled_page_id": crawled_page_id,
        })
        return (self._return_doc, 1)


class _FakeDoc:
    def __init__(self, chatbot_id: uuid.UUID | None = None, crawled_page_id: uuid.UUID | None = None) -> None:
        self.id = uuid.uuid4()
        self.chatbot_id = chatbot_id or uuid.uuid4()
        self.crawled_page_id = crawled_page_id


class _FakeOrmDoc:
    """Fake de HubDocument para tests de retire_page."""
    def __init__(self, chatbot_id: uuid.UUID, crawled_page_id: uuid.UUID) -> None:
        self.id = uuid.uuid4()
        self.chatbot_id = chatbot_id
        self.crawled_page_id = crawled_page_id


class _FakeSession:
    """Fake de AsyncSession para CorpusSelectionService."""

    def __init__(
        self,
        ingested_page_ids: set[uuid.UUID] | None = None,
        docs: list[_FakeOrmDoc] | None = None,
    ) -> None:
        self._ingested_ids = ingested_page_ids or set()
        self._docs = docs or []
        self.deleted: list = []
        self.executed_stmts: list = []
        self.flush_count = 0

    async def execute(self, stmt: Any) -> Any:
        self.executed_stmts.append(stmt)
        return _FakeDbResult(self._ingested_ids, self._docs)

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)

    async def flush(self) -> None:
        self.flush_count += 1


class _FakeDbResult:
    def __init__(self, ingested_ids: set[uuid.UUID], docs: list[_FakeOrmDoc]) -> None:
        self._ids = ingested_ids
        self._docs = docs

    def all(self) -> list:
        # Para SELECT HubDocument.crawled_page_id → devuelve tuples (id,)
        return [(pid,) for pid in self._ids]

    def scalars(self) -> "_FakeScalars":
        return _FakeScalars(self._docs)


class _FakeScalars:
    def __init__(self, docs: list) -> None:
        self._docs = docs

    def all(self) -> list:
        return self._docs


def _make_service(
    pages: list[_FakePage] | None = None,
    selections: list[_FakeSelection] | None = None,
    watcher: _FakeWatcher | None = None,
    ingested_page_ids: set[uuid.UUID] | None = None,
    docs: list[_FakeOrmDoc] | None = None,
):
    from server.app.modules.curation.selection_service import (
        CorpusSelectionService,
    )

    session = _FakeSession(ingested_page_ids=ingested_page_ids, docs=docs)
    page_repo = _FakePageRepo(pages)
    sel_repo = _FakeSelectionRepo(selections)
    w = watcher or _FakeWatcher()
    return CorpusSelectionService(session, page_repo, sel_repo, w), session, w


# ───────────────────────── Tests de candidates ─────────────────────────


@pytest.mark.asyncio
async def test_candidates_returns_matching_not_ingested():
    """candidates devuelve páginas que casan una selección path_prefix y no están ingeridas."""
    site_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()

    page = _FakePage(site_id, "https://ej.es/temas/agua")
    selection = _FakeSelection(chatbot_id, site_id, rule_type="path_prefix", rule_value="/temas/")

    svc, _, _ = _make_service(pages=[page], selections=[selection])
    result = await svc.candidates(site_id, chatbot_id)

    assert len(result) == 1
    assert result[0].url == page.url
    assert result[0].matched_rule == "/temas/"
    assert result[0].is_new is False  # Sí tiene regla → no es "nuevo sin regla"


@pytest.mark.asyncio
async def test_candidates_excludes_already_ingested():
    """candidates no incluye páginas cuya ingestión ya existe para este chatbot."""
    site_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()

    page = _FakePage(site_id, "https://ej.es/temas/agua")
    selection = _FakeSelection(chatbot_id, site_id, rule_type="path_prefix", rule_value="/temas/")

    svc, _, _ = _make_service(
        pages=[page],
        selections=[selection],
        ingested_page_ids={page.id},  # ya ingerida
    )
    result = await svc.candidates(site_id, chatbot_id)

    assert result == []


@pytest.mark.asyncio
async def test_candidates_includes_page_without_matching_rule_as_new():
    """Página activa sin selección que la case → se incluye como is_new=True."""
    site_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()

    page = _FakePage(site_id, "https://ej.es/noticias/2024/nota")
    # Selección que NO casa esta URL
    selection = _FakeSelection(chatbot_id, site_id, rule_type="path_prefix", rule_value="/temas/")

    svc, _, _ = _make_service(pages=[page], selections=[selection])
    result = await svc.candidates(site_id, chatbot_id)

    assert len(result) == 1
    assert result[0].is_new is True
    assert result[0].matched_rule is None


@pytest.mark.asyncio
async def test_candidates_empty_site_returns_empty():
    """Site sin páginas activas → lista vacía."""
    site_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()

    svc, _, _ = _make_service(pages=[])
    result = await svc.candidates(site_id, chatbot_id)

    assert result == []


# ───────────────────────── Tests de ingest_page ─────────────────────────


@pytest.mark.asyncio
async def test_ingest_page_calls_watcher_with_crawled_page_id():
    """ingest_page llama al watcher con el crawled_page_id correcto."""
    site_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()
    page = _FakePage(site_id, "https://ej.es/temas/agua")

    watcher = _FakeWatcher()
    svc, _, _ = _make_service(pages=[page], watcher=watcher)

    await svc.ingest_page(chatbot_id, page.id)

    assert len(watcher.calls) == 1
    call = watcher.calls[0]
    assert call["chatbot_id"] == chatbot_id
    assert call["crawled_page_id"] == page.id
    assert call["source_url"] == page.url


@pytest.mark.asyncio
async def test_ingest_page_passes_prefetched_content():
    """ingest_page pasa el markdown_content de la página al watcher."""
    site_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()
    page = _FakePage(site_id, "https://ej.es/x", markdown_content="# Contenido")

    watcher = _FakeWatcher()
    svc, _, _ = _make_service(pages=[page], watcher=watcher)
    await svc.ingest_page(chatbot_id, page.id)

    # El watcher guarda el call; la idempotencia la maneja el propio watcher
    assert watcher.calls[0]["source_url"] == "https://ej.es/x"


# ───────────────────────── Tests de retire_page ─────────────────────────


@pytest.mark.asyncio
async def test_retire_page_deletes_docs_and_returns_count():
    """retire_page borra documentos de esa página para el chatbot y devuelve el count."""
    site_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()
    page = _FakePage(site_id, "https://ej.es/obsoleta")

    doc = _FakeOrmDoc(chatbot_id, page.id)
    svc, session, _ = _make_service(pages=[page], docs=[doc])

    count = await svc.retire_page(chatbot_id, page.id)

    assert count == 1
    assert doc in session.deleted


@pytest.mark.asyncio
async def test_retire_page_returns_zero_when_no_docs():
    """retire_page retorna 0 cuando no hay documentos ingeridos para esa página y chatbot."""
    site_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()
    page = _FakePage(site_id, "https://ej.es/nueva")

    svc, _, _ = _make_service(pages=[page], docs=[])  # sin docs

    count = await svc.retire_page(chatbot_id, page.id)

    assert count == 0
