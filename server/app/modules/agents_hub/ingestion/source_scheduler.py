"""Scheduler que comprueba periódicamente las fuentes web monitorizadas."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from server.app.modules.agents_hub.database.operational_models import (
    HubIngestionJob,
    HubIngestionSource,
)
from server.app.modules.agents_hub.ingestion.docling_processor import DoclingProcessor
from server.app.modules.agents_hub.ingestion.hasher import hash_content
from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
from server.app.modules.agents_hub.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


async def check_source(source_id: uuid.UUID, session: AsyncSession) -> None:
    """Comprueba una fuente: re-ingesta si el contenido ha cambiado.

    Obtiene el Markdown de la URL una sola vez, compara el hash con el almacenado
    y, si cambió, pasa el contenido ya procesado al IngestionWatcher para evitar
    un segundo fetch innecesario.
    """
    source = await session.get(HubIngestionSource, source_id)
    if not source or source.status != "active":
        return

    now = datetime.now(timezone.utc)
    try:
        def _fetch() -> str:
            return DoclingProcessor().process(source.url)

        content = await asyncio.to_thread(_fetch)
        new_hash = hash_content(content)

        if new_hash != source.last_content_hash:
            job = HubIngestionJob(
                chatbot_id=source.chatbot_id,
                source_url=source.url,
                canonical_url=source.url,
                original_filename=source.label or source.url,
                status="pending",
                language=source.language,
            )
            session.add(job)
            await session.flush()

            watcher = IngestionWatcher(
                session=session,
                embedding_service=get_embedding_service(),
            )
            await watcher.run_job(job.id, prefetched_content=content)
            source.last_content_hash = new_hash

        source.last_checked_at = now
        source.status = "active"
        source.error_message = None

    except Exception as exc:
        logger.error("Error checking source %s: %s", source.url, exc)
        source.status = "error"
        source.error_message = str(exc)
        source.last_checked_at = now

    await session.commit()


async def check_all_sources(session_factory: async_sessionmaker) -> None:
    """Comprueba todas las fuentes activas cuyo intervalo haya vencido."""
    now = datetime.now(timezone.utc)

    async with session_factory() as session:
        result = await session.execute(
            select(HubIngestionSource).where(HubIngestionSource.status == "active")
        )
        sources = result.scalars().all()

    due = [
        s for s in sources
        if s.status == "active"
        and (
            s.last_checked_at is None
            or (now - s.last_checked_at) >= timedelta(hours=s.check_interval_hours)
        )
    ]

    for source in due:
        async with session_factory() as session:
            await check_source(source.id, session)


def create_scheduler(session_factory: async_sessionmaker) -> AsyncIOScheduler:
    """Crea el scheduler: job maestro cada 15 min que decide qué fuentes comprobar."""
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        check_all_sources,
        trigger="interval",
        minutes=15,
        args=[session_factory],
        id="source_checker",
        replace_existing=True,
    )
    return scheduler
