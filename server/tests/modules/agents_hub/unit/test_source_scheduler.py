"""Tests unitarios del scheduler de fuentes web monitorizadas."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_source(
    *,
    status: str = "active",
    last_checked_at: datetime | None = None,
    check_interval_hours: int = 24,
    last_content_hash: str | None = None,
    url: str = "https://example.com/doc.pdf",
):
    source = MagicMock()
    source.id = uuid.uuid4()
    source.chatbot_id = uuid.uuid4()
    source.url = url
    source.label = "Documento de prueba"
    source.status = status
    source.last_checked_at = last_checked_at
    source.check_interval_hours = check_interval_hours
    source.last_content_hash = last_content_hash
    source.error_message = None
    return source


def _make_session_with_sources(sources: list) -> AsyncMock:
    """Builds an AsyncMock session whose execute().scalars().all() returns sources."""
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = sources
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=execute_result)
    return mock_session


def _make_factory(mock_session: AsyncMock) -> MagicMock:
    """Construye un mock de async_sessionmaker compatible con 'async with factory() as s'."""
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=mock_cm)
    return factory


class TestCheckAllSources:

    @pytest.mark.asyncio
    async def test_skips_paused_sources(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_all_sources

        paused = _make_source(status="paused")
        mock_session = _make_session_with_sources([paused])

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.check_source",
            new_callable=AsyncMock,
        ) as mock_check:
            await check_all_sources(_make_factory(mock_session))
            mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_recently_checked_sources(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_all_sources

        recent = _make_source(
            last_checked_at=datetime.now(timezone.utc) - timedelta(hours=1),
            check_interval_hours=24,
        )
        mock_session = _make_session_with_sources([recent])

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.check_source",
            new_callable=AsyncMock,
        ) as mock_check:
            await check_all_sources(_make_factory(mock_session))
            mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_checks_overdue_source(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_all_sources

        overdue = _make_source(
            last_checked_at=datetime.now(timezone.utc) - timedelta(hours=25),
            check_interval_hours=24,
        )
        mock_session = _make_session_with_sources([overdue])

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.check_source",
            new_callable=AsyncMock,
        ) as mock_check:
            await check_all_sources(_make_factory(mock_session))
            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_checks_never_checked_source(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_all_sources

        new_source = _make_source(last_checked_at=None)
        mock_session = _make_session_with_sources([new_source])

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.check_source",
            new_callable=AsyncMock,
        ) as mock_check:
            await check_all_sources(_make_factory(mock_session))
            mock_check.assert_called_once()


class TestCheckSource:

    @pytest.mark.asyncio
    async def test_skips_when_source_not_found(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        await check_source(uuid.uuid4(), mock_session)

        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_paused_source(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source

        source = _make_source(status="paused")
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=source)

        await check_source(source.id, mock_session)

        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_job_when_content_changed(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source

        source = _make_source(last_content_hash="old_hash")
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=source)
        mock_session.flush = AsyncMock()

        mock_watcher = AsyncMock()

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.DoclingProcessor"
        ) as mock_proc_cls, patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.hash_content",
            return_value="new_hash",
        ), patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.IngestionWatcher",
            return_value=mock_watcher,
        ), patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.get_embedding_service",
        ):
            mock_proc_cls.return_value.process.return_value = "# Nuevo contenido"
            await check_source(source.id, mock_session)

        mock_session.add.assert_called_once()
        mock_watcher.run_job.assert_called_once()
        assert source.last_content_hash == "new_hash"
        assert source.status == "active"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_job_when_content_unchanged(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source

        source = _make_source(last_content_hash="same_hash")
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=source)

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.DoclingProcessor"
        ) as mock_proc_cls, patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.hash_content",
            return_value="same_hash",
        ):
            mock_proc_cls.return_value.process.return_value = "# Contenido igual"
            await check_source(source.id, mock_session)

        mock_session.add.assert_not_called()
        assert source.status == "active"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_marks_error_on_fetch_failure(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source

        source = _make_source()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=source)

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.DoclingProcessor",
            side_effect=RuntimeError("Connection refused"),
        ):
            await check_source(source.id, mock_session)

        assert source.status == "error"
        assert "Connection refused" in source.error_message
        assert source.last_checked_at is not None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_last_checked_at(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source

        source = _make_source(last_content_hash="same_hash")
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=source)

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.DoclingProcessor"
        ) as mock_proc_cls, patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.hash_content",
            return_value="same_hash",
        ):
            mock_proc_cls.return_value.process.return_value = "content"
            await check_source(source.id, mock_session)

        assert source.last_checked_at is not None


class TestCreateScheduler:

    @pytest.mark.asyncio
    async def test_scheduler_has_source_checker_job(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import create_scheduler

        scheduler = create_scheduler(MagicMock())
        scheduler.start()
        try:
            job = scheduler.get_job("source_checker")
            assert job is not None
            assert job.trigger is not None
        finally:
            scheduler.shutdown(wait=False)
