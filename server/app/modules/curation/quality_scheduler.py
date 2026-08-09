"""Scheduler de calidad de contenido web (9Q.5).

Deploy: edge.

Mantiene un APScheduler que, cada N horas, selecciona los HubWebSite activos
cuyo crawl_interval_hours haya vencido y lanza SiteQualityAnalysisJob.run_for_site.

La función _get_due_sites está expuesta para facilitar los tests unitarios.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def _get_due_sites(session: Any, now: datetime) -> list:
    """Retorna los HubWebSite activos cuyo intervalo de crawl ha vencido.

    Un sitio es «debido» si:
    - last_crawled_at es None (nunca rastreado), o
    - now - last_crawled_at >= crawl_interval_hours.
    """
    from sqlalchemy import select

    from server.app.modules.agents_hub.database.operational_models import HubWebSite

    stmt = select(HubWebSite).where(HubWebSite.status == "active")
    result = await session.execute(stmt)
    sites = result.scalars().all()

    due: list = []
    for site in sites:
        if site.last_crawled_at is None:
            due.append(site)
        else:
            elapsed = now - site.last_crawled_at
            if elapsed >= timedelta(hours=site.crawl_interval_hours):
                due.append(site)
    return due


def create_quality_scheduler(
    session_factory: Any,
    site_quality_job: Any,
    *,
    interval_hours: int = 24,
    enabled: bool = True,
) -> Any:
    """Crea y configura el APScheduler de calidad de contenido.

    Args:
        session_factory: async context manager que cede una AsyncSession.
        site_quality_job: instancia de SiteQualityAnalysisJob.
        interval_hours: cadencia del job maestro (default: 24 h).
        enabled: si False, devuelve el scheduler sin jobs (para CONTENT_QUALITY_ENABLED=False).
    """
    import asyncio

    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler()

    if not enabled:
        return scheduler

    async def check_all_sites() -> None:
        logger.info("[QualityScheduler] check_all_sites started")
        now = datetime.now(timezone.utc)
        try:
            async with session_factory() as session:
                due_sites = await _get_due_sites(session, now)
        except Exception as exc:
            logger.exception("[QualityScheduler] Failed to get due sites: %s", exc)
            return

        logger.info("[QualityScheduler] %d sites due for quality check", len(due_sites))
        for site in due_sites:
            asyncio.create_task(
                _run_site_safe(site_quality_job, site.id),
                name=f"quality-{site.id}",
            )

    scheduler.add_job(
        check_all_sites,
        trigger="interval",
        hours=interval_hours,
        id="content_quality_check_all_sites",
    )

    return scheduler


async def _run_site_safe(
    site_quality_job: Any,
    site_id: uuid.UUID,
) -> None:
    """Ejecuta el job de calidad para un sitio sin propagar excepciones."""
    try:
        summary = await site_quality_job.run_for_site(site_id)
        logger.info(
            "[QualityScheduler] site %s done: new=%d superseded=%d auto_ingested=%d errors=%d",
            site_id,
            summary.pages_new,
            summary.pages_marked_superseded,
            summary.documents_auto_ingested,
            len(summary.errors),
        )
        if summary.errors:
            for err in summary.errors:
                logger.warning("[QualityScheduler] site %s error: %s", site_id, err)
    except Exception as exc:
        logger.exception("[QualityScheduler] Unexpected failure for site %s: %s", site_id, exc)
