"""Tests de integración del modelo HubIngestionSource."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select


DB_URL = "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai"


@pytest.fixture
async def db_session():
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )

    engine = create_async_engine(DB_URL)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class TestHubIngestionSource:

    @pytest.mark.asyncio
    async def test_can_create_ingestion_source(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubIngestionSource

        chatbot_id = uuid.uuid4()
        source = HubIngestionSource(
            chatbot_id=chatbot_id,
            url="https://example.com/doc.pdf",
            label="Documento de prueba",
        )
        db_session.add(source)
        await db_session.commit()

        result = await db_session.execute(
            select(HubIngestionSource).where(HubIngestionSource.chatbot_id == chatbot_id)
        )
        saved = result.scalar_one()
        assert saved.url == "https://example.com/doc.pdf"
        assert saved.label == "Documento de prueba"

        await db_session.delete(saved)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_source_defaults_to_active_status(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubIngestionSource

        source = HubIngestionSource(chatbot_id=uuid.uuid4(), url="https://example.com/a")
        db_session.add(source)
        await db_session.commit()

        assert source.status == "active"

        await db_session.delete(source)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_source_check_interval_defaults_to_24h(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubIngestionSource

        source = HubIngestionSource(chatbot_id=uuid.uuid4(), url="https://example.com/b")
        db_session.add(source)
        await db_session.commit()

        assert source.check_interval_hours == 24

        await db_session.delete(source)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_label_is_optional(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubIngestionSource

        source = HubIngestionSource(chatbot_id=uuid.uuid4(), url="https://example.com/c")
        db_session.add(source)
        await db_session.commit()

        assert source.label is None

        await db_session.delete(source)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_can_update_last_checked_at_and_hash(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubIngestionSource

        source = HubIngestionSource(chatbot_id=uuid.uuid4(), url="https://example.com/d")
        db_session.add(source)
        await db_session.commit()

        now = datetime.now(timezone.utc)
        source.last_checked_at = now
        source.last_content_hash = "abc123"
        await db_session.commit()

        result = await db_session.execute(
            select(HubIngestionSource).where(HubIngestionSource.id == source.id)
        )
        saved = result.scalar_one()
        assert saved.last_content_hash == "abc123"
        assert saved.last_checked_at is not None

        await db_session.delete(saved)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_can_pause_and_resume_source(self, db_session) -> None:
        from server.app.modules.agents_hub.database.operational_models import HubIngestionSource

        source = HubIngestionSource(chatbot_id=uuid.uuid4(), url="https://example.com/e")
        db_session.add(source)
        await db_session.commit()

        source.status = "paused"
        await db_session.commit()
        assert source.status == "paused"

        source.status = "active"
        await db_session.commit()
        assert source.status == "active"

        await db_session.delete(source)
        await db_session.commit()
