"""Tests TDD — Etiquetado de idioma en la ingestión (Prompt 9.8.1)."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestProcessSourceLanguageDetection:
    """process_source() debe auto-detectar idioma cuando language=None
    y respetar el idioma explícito cuando se proporciona."""

    @pytest.mark.asyncio
    async def test_process_source_auto_detects_catalan_content(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

        catalan_content = "# Documentació\n\nAquest és un text en català sobre normativa universitària."

        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value.scalars.return_value = MagicMock(
            __iter__=lambda s: iter([])
        )

        watcher = IngestionWatcher(
            session=mock_session,
            embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024)),
        )

        with patch(
            "server.app.modules.agents_hub.ingestion.watcher.detect_language",
            return_value="ca",
        ) as mock_detect:
            chunks = await watcher.process_source(
                source_url="https://example.com/doc",
                chatbot_id=uuid.uuid4(),
                prefetched_content=catalan_content,
                language=None,  # debe auto-detectar
            )

        mock_detect.assert_called_once_with(catalan_content)
        assert all(c.language == "ca" for c in chunks)

    @pytest.mark.asyncio
    async def test_process_source_respects_explicit_language(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

        content = "Some English content about regulations."

        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value.scalars.return_value = MagicMock(
            __iter__=lambda s: iter([])
        )

        watcher = IngestionWatcher(
            session=mock_session,
            embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024)),
        )

        with patch(
            "server.app.modules.agents_hub.ingestion.watcher.detect_language"
        ) as mock_detect:
            chunks = await watcher.process_source(
                source_url="https://example.com/doc",
                chatbot_id=uuid.uuid4(),
                prefetched_content=content,
                language="en",  # idioma explícito — NO debe llamar a detect_language
            )

        mock_detect.assert_not_called()
        assert all(c.language == "en" for c in chunks)

    @pytest.mark.asyncio
    async def test_process_user_upload_auto_detects_language(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

        english_content = "# Report\n\nThis document describes the annual budget allocation."

        mock_session = AsyncMock()

        watcher = IngestionWatcher(
            session=mock_session,
            embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1] * 1024)),
        )

        with patch(
            "server.app.modules.agents_hub.ingestion.watcher.asyncio.to_thread",
            return_value=english_content,
        ):
            with patch(
                "server.app.modules.agents_hub.ingestion.watcher.detect_language",
                return_value="en",
            ) as mock_detect:
                chunks = await watcher.process_user_upload(
                    source_url="/tmp/report.pdf",
                    chatbot_id=uuid.uuid4(),
                    owner_id=uuid.uuid4(),
                )

        mock_detect.assert_called_once_with(english_content)
        assert all(c.language == "en" for c in chunks)


class TestRunJobPropagatesLanguage:
    """run_job() debe leer job.language y propagarlo a process_source()."""

    @pytest.mark.asyncio
    async def test_run_job_propagates_catalan_language(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
        from server.app.modules.agents_hub.database.operational_models import HubIngestionJob

        job_id = uuid.uuid4()
        chatbot_id = uuid.uuid4()
        job = HubIngestionJob(
            id=job_id,
            chatbot_id=chatbot_id,
            source_url="https://example.com",
            canonical_url="https://example.com",
            status="pending",
            language="ca",
        )

        mock_session = AsyncMock()
        mock_session.get.return_value = job

        watcher = IngestionWatcher(
            session=mock_session,
            embedding_service=AsyncMock(),
        )

        with patch.object(watcher, "process_source", new_callable=AsyncMock, return_value=[]) as mock_ps:
            await watcher.run_job(job_id)

        mock_ps.assert_called_once_with(
            job.source_url,
            job.chatbot_id,
            citation_url=job.canonical_url,
            prefetched_content=None,
            language="ca",
        )

    @pytest.mark.asyncio
    async def test_run_job_propagates_none_language_for_auto_detect(self) -> None:
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
        from server.app.modules.agents_hub.database.operational_models import HubIngestionJob

        job_id = uuid.uuid4()
        job = HubIngestionJob(
            id=job_id,
            chatbot_id=uuid.uuid4(),
            source_url="https://example.com",
            canonical_url=None,
            status="pending",
            language=None,  # auto-detectar
        )

        mock_session = AsyncMock()
        mock_session.get.return_value = job

        watcher = IngestionWatcher(session=mock_session, embedding_service=AsyncMock())

        with patch.object(watcher, "process_source", new_callable=AsyncMock, return_value=[]) as mock_ps:
            await watcher.run_job(job_id)

        _, kwargs = mock_ps.call_args
        assert kwargs.get("language") is None


class TestSchedulerPropagatesLanguage:
    """check_source() debe propagar source.language al HubIngestionJob creado."""

    @pytest.mark.asyncio
    async def test_check_source_propagates_english_language_to_job(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source
        from server.app.modules.agents_hub.database.operational_models import (
            HubIngestionSource,
            HubIngestionJob,
        )

        source_id = uuid.uuid4()
        source = HubIngestionSource(
            id=source_id,
            chatbot_id=uuid.uuid4(),
            url="https://example.com/en",
            status="active",
            language="en",
            last_content_hash="old_hash",
        )

        mock_session = AsyncMock()
        mock_session.get.return_value = source
        mock_session.flush = AsyncMock()

        added_objects = []
        mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.asyncio.to_thread",
            return_value="New English content about budget.",
        ):
            with patch(
                "server.app.modules.agents_hub.ingestion.source_scheduler.hash_content",
                return_value="new_hash",
            ):
                with patch(
                    "server.app.modules.agents_hub.ingestion.source_scheduler.IngestionWatcher"
                ) as mock_watcher_cls:
                    mock_watcher_cls.return_value.run_job = AsyncMock()

                    await check_source(source_id, mock_session)

        jobs = [o for o in added_objects if isinstance(o, HubIngestionJob)]
        assert len(jobs) == 1
        assert jobs[0].language == "en"

    @pytest.mark.asyncio
    async def test_check_source_propagates_none_language(self) -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source
        from server.app.modules.agents_hub.database.operational_models import (
            HubIngestionSource,
            HubIngestionJob,
        )

        source_id = uuid.uuid4()
        source = HubIngestionSource(
            id=source_id,
            chatbot_id=uuid.uuid4(),
            url="https://example.com",
            status="active",
            language=None,  # auto-detectar
            last_content_hash="old",
        )

        mock_session = AsyncMock()
        mock_session.get.return_value = source
        mock_session.flush = AsyncMock()

        added_objects = []
        mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        with patch(
            "server.app.modules.agents_hub.ingestion.source_scheduler.asyncio.to_thread",
            return_value="Contingut en català.",
        ):
            with patch(
                "server.app.modules.agents_hub.ingestion.source_scheduler.hash_content",
                return_value="new_hash",
            ):
                with patch(
                    "server.app.modules.agents_hub.ingestion.source_scheduler.IngestionWatcher"
                ) as mock_watcher_cls:
                    mock_watcher_cls.return_value.run_job = AsyncMock()

                    await check_source(source_id, mock_session)

        jobs = [o for o in added_objects if isinstance(o, HubIngestionJob)]
        assert len(jobs) == 1
        assert jobs[0].language is None
