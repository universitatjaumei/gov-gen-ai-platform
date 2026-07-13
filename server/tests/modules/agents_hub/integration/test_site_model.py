"""Tests de integración 9Q.0 — entidades sitio/página/selección + retirada de HubIngestionSource.

Requieren PostgreSQL con pgvector corriendo en localhost:5432.
"""
import os
import uuid

import pytest
from sqlalchemy import select, text


DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai",
)


@pytest.fixture
async def db_session():
    """Sesión con tablas Hub creadas y eliminadas al finalizar el test."""
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )
    from server.app.modules.agents_hub.database.base import HubConfigBase, HubOperationalBase

    import server.app.modules.agents_hub.database.config_models  # noqa: F401 — registra tablas
    import server.app.modules.agents_hub.database.operational_models  # noqa: F401 — registra tablas

    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(HubConfigBase.metadata.create_all)
        await conn.run_sync(HubOperationalBase.metadata.create_all)

    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(HubOperationalBase.metadata.drop_all)
        await conn.run_sync(HubConfigBase.metadata.drop_all)
    await engine.dispose()


# ────────────────────────────────────────────────────────────────────────────
#  WebSiteRepo
# ────────────────────────────────────────────────────────────────────────────


class TestWebSiteRepo:

    @pytest.mark.asyncio
    async def test_create_get_list_by_organizacion(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubWebSite
        from server.app.modules.agents_hub.ingestion.quality.site_repo import WebSiteRepo

        repo = WebSiteRepo(db_session)
        organizacion_id = uuid.uuid4()
        other_client_id = uuid.uuid4()

        site_a = await repo.create(
            organizacion_id=organizacion_id,
            name="Web de Trámites",
            root_url="https://uji.es/tramites",
        )
        site_b = await repo.create(
            organizacion_id=organizacion_id,
            name="Web institucional",
            root_url="https://uji.es",
        )
        site_other = await repo.create(
            organizacion_id=other_client_id,
            name="Otra entidad",
            root_url="https://other.example",
        )

        fetched = await repo.get(site_a.id)
        assert fetched is not None
        assert isinstance(fetched, HubWebSite)
        assert fetched.name == "Web de Trámites"

        listed = await repo.list_by_organizacion(organizacion_id)
        ids = {s.id for s in listed}
        assert site_a.id in ids
        assert site_b.id in ids
        assert site_other.id not in ids

    @pytest.mark.asyncio
    async def test_audit_semantic_scope_default_ingested(self, db_session) -> None:
        from server.app.modules.agents_hub.ingestion.quality.site_repo import WebSiteRepo

        repo = WebSiteRepo(db_session)
        site = await repo.create(
            organizacion_id=uuid.uuid4(),
            name="Web por defecto",
            root_url="https://example.com",
        )

        assert site.audit_semantic_scope == "ingested"
        assert site.spider_type == "generic"
        assert site.crawl_interval_hours == 24
        assert site.status == "active"

    @pytest.mark.asyncio
    async def test_delete_cascades_pages_and_selections(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import (
            HubCorpusSelection,
            HubCrawledPage,
        )
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CorpusSelectionRepo,
            CrawledPageRepo,
            WebSiteRepo,
        )

        site_repo = WebSiteRepo(db_session)
        page_repo = CrawledPageRepo(db_session)
        sel_repo = CorpusSelectionRepo(db_session)

        site = await site_repo.create(
            organizacion_id=uuid.uuid4(),
            name="Cascada",
            root_url="https://cascade.example",
        )
        page = await page_repo.upsert(site_id=site.id, url="https://cascade.example/a")
        sel = await sel_repo.create(
            chatbot_id=uuid.uuid4(),
            site_id=site.id,
            rule_type="manual",
        )

        await site_repo.delete(site.id)

        pages_left = (
            await db_session.execute(
                select(HubCrawledPage).where(HubCrawledPage.id == page.id)
            )
        ).scalar_one_or_none()
        selections_left = (
            await db_session.execute(
                select(HubCorpusSelection).where(HubCorpusSelection.id == sel.id)
            )
        ).scalar_one_or_none()

        assert pages_left is None
        assert selections_left is None


# ────────────────────────────────────────────────────────────────────────────
#  CrawledPageRepo
# ────────────────────────────────────────────────────────────────────────────


class TestCrawledPageRepo:

    @pytest.mark.asyncio
    async def test_upsert_respects_unique_constraint(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubCrawledPage
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CrawledPageRepo,
            WebSiteRepo,
        )

        site_repo = WebSiteRepo(db_session)
        page_repo = CrawledPageRepo(db_session)

        site = await site_repo.create(
            organizacion_id=uuid.uuid4(),
            name="Upsert site",
            root_url="https://up.example",
        )

        first = await page_repo.upsert(
            site_id=site.id,
            url="https://up.example/tramites/1",
            title="Trámite 1",
            token_count=10,
        )
        second = await page_repo.upsert(
            site_id=site.id,
            url="https://up.example/tramites/1",
            title="Trámite 1 actualizado",
            token_count=42,
        )

        assert first.id == second.id
        assert second.title == "Trámite 1 actualizado"
        assert second.token_count == 42

        rows = (
            await db_session.execute(
                select(HubCrawledPage).where(HubCrawledPage.site_id == site.id)
            )
        ).scalars().all()
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_page_defaults(self, db_session) -> None:
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CrawledPageRepo,
            WebSiteRepo,
        )

        site = await WebSiteRepo(db_session).create(
            organizacion_id=uuid.uuid4(),
            name="Defaults site",
            root_url="https://def.example",
        )
        page = await CrawledPageRepo(db_session).upsert(
            site_id=site.id, url="https://def.example/x"
        )

        assert page.status == "active"
        assert page.markdown_content is None
        assert page.error_message is None
        assert page.superseded is False
        assert page.title is None
        assert page.token_count is None

    @pytest.mark.asyncio
    async def test_list_by_site_filtered_by_status(self, db_session) -> None:
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CrawledPageRepo,
            WebSiteRepo,
        )

        site = await WebSiteRepo(db_session).create(
            organizacion_id=uuid.uuid4(),
            name="List site",
            root_url="https://list.example",
        )
        page_repo = CrawledPageRepo(db_session)
        p_active = await page_repo.upsert(site_id=site.id, url="https://list.example/a")
        p_gone = await page_repo.upsert(site_id=site.id, url="https://list.example/b")
        p_gone.status = "gone"
        await db_session.flush()

        all_pages = await page_repo.list_by_site(site.id)
        active_pages = await page_repo.list_by_site(site.id, status="active")

        all_ids = {p.id for p in all_pages}
        active_ids = {p.id for p in active_pages}
        assert {p_active.id, p_gone.id}.issubset(all_ids)
        assert active_ids == {p_active.id}

    @pytest.mark.asyncio
    async def test_mark_gone_updates_status_in_bulk(self, db_session) -> None:
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CrawledPageRepo,
            WebSiteRepo,
        )

        site = await WebSiteRepo(db_session).create(
            organizacion_id=uuid.uuid4(),
            name="Gone site",
            root_url="https://gone.example",
        )
        page_repo = CrawledPageRepo(db_session)
        p1 = await page_repo.upsert(site_id=site.id, url="https://gone.example/1")
        p2 = await page_repo.upsert(site_id=site.id, url="https://gone.example/2")
        p3 = await page_repo.upsert(site_id=site.id, url="https://gone.example/3")

        await page_repo.mark_gone([p1.id, p2.id])
        await db_session.refresh(p1)
        await db_session.refresh(p2)
        await db_session.refresh(p3)

        assert p1.status == "gone"
        assert p2.status == "gone"
        assert p3.status == "active"

    @pytest.mark.asyncio
    async def test_get_by_canonical(self, db_session) -> None:
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CrawledPageRepo,
            WebSiteRepo,
        )

        site = await WebSiteRepo(db_session).create(
            organizacion_id=uuid.uuid4(),
            name="Canon site",
            root_url="https://canon.example",
        )
        page_repo = CrawledPageRepo(db_session)
        canonical = "https://canon.example/canonical"
        await page_repo.upsert(
            site_id=site.id,
            url="https://canon.example/canonical?utm=1",
            canonical_url=canonical,
        )

        found = await page_repo.get_by_canonical(site.id, canonical)
        assert found is not None
        assert found.canonical_url == canonical

        not_found = await page_repo.get_by_canonical(site.id, "https://canon.example/missing")
        assert not_found is None


# ────────────────────────────────────────────────────────────────────────────
#  CorpusSelectionRepo
# ────────────────────────────────────────────────────────────────────────────


class TestCorpusSelectionRepo:

    @pytest.mark.asyncio
    async def test_create_list_by_chatbot_and_by_site(self, db_session) -> None:
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CorpusSelectionRepo,
            WebSiteRepo,
        )

        chatbot_id = uuid.uuid4()
        other_chatbot_id = uuid.uuid4()
        site_repo = WebSiteRepo(db_session)
        sel_repo = CorpusSelectionRepo(db_session)
        site_a = await site_repo.create(
            organizacion_id=uuid.uuid4(), name="A", root_url="https://a.example"
        )
        site_b = await site_repo.create(
            organizacion_id=uuid.uuid4(), name="B", root_url="https://b.example"
        )

        sel_a = await sel_repo.create(
            chatbot_id=chatbot_id,
            site_id=site_a.id,
            rule_type="path_prefix",
            rule_value="/tramites/",
        )
        sel_b = await sel_repo.create(
            chatbot_id=chatbot_id,
            site_id=site_b.id,
            rule_type="manual",
        )
        sel_other = await sel_repo.create(
            chatbot_id=other_chatbot_id,
            site_id=site_a.id,
            rule_type="manual",
        )

        by_bot = await sel_repo.list_by_chatbot(chatbot_id)
        ids_by_bot = {s.id for s in by_bot}
        assert {sel_a.id, sel_b.id} == ids_by_bot

        by_site_a = await sel_repo.list_by_site(site_a.id)
        ids_by_site = {s.id for s in by_site_a}
        assert {sel_a.id, sel_other.id} == ids_by_site

    @pytest.mark.asyncio
    async def test_matches_path_prefix_yes_and_no(self, db_session) -> None:
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CorpusSelectionRepo,
            WebSiteRepo,
        )

        site = await WebSiteRepo(db_session).create(
            organizacion_id=uuid.uuid4(), name="P", root_url="https://p.example"
        )
        sel = await CorpusSelectionRepo(db_session).create(
            chatbot_id=uuid.uuid4(),
            site_id=site.id,
            rule_type="path_prefix",
            rule_value="/tramites/",
        )

        repo = CorpusSelectionRepo(db_session)
        assert repo.matches(sel, "https://p.example/tramites/becas") is True
        assert repo.matches(sel, "https://p.example/tramites/") is True
        assert repo.matches(sel, "https://p.example/noticias/x") is False

    @pytest.mark.asyncio
    async def test_matches_manual_always_false(self, db_session) -> None:
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CorpusSelectionRepo,
            WebSiteRepo,
        )

        site = await WebSiteRepo(db_session).create(
            organizacion_id=uuid.uuid4(), name="M", root_url="https://m.example"
        )
        sel = await CorpusSelectionRepo(db_session).create(
            chatbot_id=uuid.uuid4(),
            site_id=site.id,
            rule_type="manual",
        )

        repo = CorpusSelectionRepo(db_session)
        assert repo.matches(sel, "https://m.example/anything") is False
        assert repo.matches(sel, "https://m.example/") is False


# ────────────────────────────────────────────────────────────────────────────
#  HubDocument.crawled_page_id FK
# ────────────────────────────────────────────────────────────────────────────


class TestHubDocumentCrawledPageFK:

    @pytest.mark.asyncio
    async def test_crawled_page_id_defaults_to_none(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        doc = HubDocument(
            chatbot_id=uuid.uuid4(),
            title="Doc sin página rastreada",
            canonical_url="https://upload.example/file.pdf",
            markdown_content="# Hola",
            content_hash="hash-no-page",
            language="es",
            source_kind="upload",
        )
        db_session.add(doc)
        await db_session.commit()

        await db_session.refresh(doc)
        assert doc.crawled_page_id is None

    @pytest.mark.asyncio
    async def test_fk_set_null_on_page_delete(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        from server.app.modules.agents_hub.ingestion.quality.site_repo import (
            CrawledPageRepo,
            WebSiteRepo,
        )

        site = await WebSiteRepo(db_session).create(
            organizacion_id=uuid.uuid4(), name="FK", root_url="https://fk.example"
        )
        page = await CrawledPageRepo(db_session).upsert(
            site_id=site.id, url="https://fk.example/x"
        )

        doc = HubDocument(
            chatbot_id=uuid.uuid4(),
            title="Doc con página",
            canonical_url="https://fk.example/x",
            markdown_content="# Página",
            content_hash="hash-page",
            language="es",
            source_kind="crawler",
            crawled_page_id=page.id,
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)
        assert doc.crawled_page_id == page.id

        await db_session.execute(
            text("DELETE FROM hub_crawled_pages WHERE id = :id"),
            {"id": page.id},
        )
        await db_session.commit()

        await db_session.refresh(doc)
        assert doc.crawled_page_id is None


# ────────────────────────────────────────────────────────────────────────────
#  Retirada de HubIngestionSource
# ────────────────────────────────────────────────────────────────────────────


class TestHubIngestionSourceRetired:

    def test_hub_ingestion_source_not_importable(self) -> None:
        import server.app.modules.agents_hub.database.operational_models as mod

        assert not hasattr(mod, "HubIngestionSource"), (
            "HubIngestionSource debe haberse retirado en 9Q.0; usa HubWebSite + HubCorpusSelection."
        )

    def test_source_scheduler_module_removed(self) -> None:
        with pytest.raises(ImportError):
            import server.app.modules.agents_hub.ingestion.source_scheduler  # noqa: F401
