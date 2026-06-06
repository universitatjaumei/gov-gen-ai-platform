"""Gestión de sitios rastreados, selecciones y candidatas (9Q.7).

Deploy: edge.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import HubCrawledPage
from server.app.modules.agents_hub.ingestion.quality.selection_contracts import (
    CandidatePageView,
    PageView,
    SelectionCreate,
    SelectionView,
    SiteCreate,
    SitePatch,
    SiteView,
)
from server.app.modules.agents_hub.ingestion.quality.site_repo import (
    CorpusSelectionRepo,
    CrawledPageRepo,
    WebSiteRepo,
)

router = APIRouter(tags=["hub-sites"])

# ──────────────────────── Job de calidad inyectable ────────────────────────

_quality_job: Any = None


def set_quality_job(job: Any) -> None:
    """Registra la instancia de SiteQualityAnalysisJob para el endpoint de crawl."""
    global _quality_job
    _quality_job = job


def get_quality_job() -> Any:
    """Dependencia FastAPI que provee el job de calidad (o None si no está configurado)."""
    return _quality_job


# ──────────────────────── Dependencia de CorpusSelectionService ────────────────────────


async def get_selection_service(
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Crea CorpusSelectionService con dependencias mínimas (sin embedding, sin watcher real).

    Para operaciones que necesiten watcher real (ingest_page), el endpoint
    construye el watcher directamente.
    """
    from server.app.modules.agents_hub.ingestion.quality.selection_service import (
        CorpusSelectionService,
    )

    page_repo = CrawledPageRepo(session)
    sel_repo = CorpusSelectionRepo(session)
    return CorpusSelectionService(session, page_repo, sel_repo, watcher=None)


async def _require_admin_or_partner(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if not (user.is_admin or user.is_partner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return user


# ──────────────────────── CRUD de sitios ────────────────────────


@router.post(
    "/hub/sites",
    response_model=SiteView,
    status_code=status.HTTP_201_CREATED,
    operation_id="createSite",
)
async def create_site(
    body: SiteCreate,
    client_id: uuid.UUID | None = Query(default=None),
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Crea un nuevo sitio rastreado.

    Deploy: edge. client_id se provee como query param; no va en el body.
    """
    repo = WebSiteRepo(session)
    site = await repo.create(
        client_id=client_id,
        name=body.name,
        root_url=body.root_url,
        sitemap_url=body.sitemap_url,
        crawl_interval_hours=body.crawl_interval_hours,
        audit_semantic_scope=body.audit_semantic_scope,
    )
    await session.commit()
    return site


@router.get(
    "/hub/sites",
    response_model=list[SiteView],
    operation_id="listSites",
)
async def list_sites(
    client_id: uuid.UUID | None = Query(default=None),
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Lista sitios, opcionalmente filtrados por client_id.

    Deploy: edge.
    """
    from server.app.modules.agents_hub.database.operational_models import HubWebSite

    stmt = select(HubWebSite).order_by(HubWebSite.created_at.desc())
    if client_id is not None:
        stmt = stmt.where(HubWebSite.client_id == client_id)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.patch(
    "/hub/sites/{site_id}",
    response_model=SiteView,
    operation_id="patchSite",
)
async def patch_site(
    site_id: uuid.UUID,
    body: SitePatch,
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Actualiza campos de un sitio.

    Deploy: edge.
    """
    repo = WebSiteRepo(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    site = await repo.update(site_id, **updates)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    await session.commit()
    return site


@router.delete(
    "/hub/sites/{site_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteSite",
)
async def delete_site(
    site_id: uuid.UUID,
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Elimina un sitio y todas sus páginas (CASCADE).

    Deploy: edge.
    """
    repo = WebSiteRepo(session)
    await repo.delete(site_id)
    await session.commit()


# ──────────────────────── Crawl trigger ────────────────────────


@router.post(
    "/hub/sites/{site_id}/crawl",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="triggerSiteCrawl",
)
async def trigger_crawl(
    site_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
    quality_job: Any = Depends(get_quality_job),
):
    """Dispara un crawl + análisis de calidad en background.

    Deploy: edge. Responde 202 Accepted inmediatamente.
    """
    from server.app.modules.agents_hub.database.operational_models import HubWebSite

    site = await session.get(HubWebSite, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    if quality_job is not None:
        background_tasks.add_task(quality_job.run_for_site, site_id)

    return {"status": "queued", "site_id": str(site_id)}


# ──────────────────────── Páginas del sitio ────────────────────────


@router.get(
    "/hub/sites/{site_id}/pages",
    response_model=list[PageView],
    operation_id="listSitePages",
)
async def list_site_pages(
    site_id: uuid.UUID,
    page_status: str | None = Query(default=None, alias="status"),
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Lista las páginas rastreadas de un sitio, opcionalmente filtradas por status.

    Deploy: edge.
    """
    stmt = select(HubCrawledPage).where(HubCrawledPage.site_id == site_id)
    if page_status is not None:
        stmt = stmt.where(HubCrawledPage.status == page_status)
    stmt = stmt.order_by(HubCrawledPage.url)
    result = await session.execute(stmt)
    return result.scalars().all()


# ──────────────────────── CRUD de selecciones ────────────────────────


@router.post(
    "/hub/chatbots/{chatbot_id}/selections",
    response_model=SelectionView,
    status_code=status.HTTP_201_CREATED,
    operation_id="createSelection",
)
async def create_selection(
    chatbot_id: uuid.UUID,
    body: SelectionCreate,
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Crea una regla de selección de corpus para un chatbot.

    Deploy: edge.
    """
    repo = CorpusSelectionRepo(session)
    sel = await repo.create(
        chatbot_id=chatbot_id,
        site_id=body.site_id,
        rule_type=body.rule_type,
        rule_value=body.rule_value,
        auto_ingest_new=body.auto_ingest_new,
    )
    await session.commit()
    return sel


@router.get(
    "/hub/chatbots/{chatbot_id}/selections",
    response_model=list[SelectionView],
    operation_id="listSelections",
)
async def list_selections(
    chatbot_id: uuid.UUID,
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Lista las selecciones de corpus de un chatbot.

    Deploy: edge.
    """
    from server.app.modules.agents_hub.database.operational_models import HubCorpusSelection

    stmt = (
        select(HubCorpusSelection)
        .where(HubCorpusSelection.chatbot_id == chatbot_id)
        .order_by(HubCorpusSelection.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.delete(
    "/hub/chatbots/{chatbot_id}/selections/{selection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteSelection",
)
async def delete_selection(
    chatbot_id: uuid.UUID,
    selection_id: uuid.UUID,
    current_user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_async_session),
):
    """Elimina una selección de corpus.

    Deploy: edge.
    """
    repo = CorpusSelectionRepo(session)
    await repo.delete(selection_id)
    await session.commit()


# ──────────────────────── Candidatas e ingestión ────────────────────────


@router.get(
    "/hub/sites/{site_id}/candidates",
    response_model=list[CandidatePageView],
    operation_id="listCandidates",
)
async def list_candidates(
    site_id: uuid.UUID,
    chatbot_id: uuid.UUID = Query(...),
    current_user: UserInfo = Depends(_require_admin_or_partner),
    svc: Any = Depends(get_selection_service),
):
    """Páginas candidatas a ingerir: activas, no ingeridas aún para el chatbot.

    Deploy: edge.
    """
    return await svc.candidates(site_id, chatbot_id)


@router.post(
    "/hub/chatbots/{chatbot_id}/pages/{page_id}/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="ingestPage",
)
async def ingest_page(
    chatbot_id: uuid.UUID,
    page_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: UserInfo = Depends(_require_admin_or_partner),
    svc: Any = Depends(get_selection_service),
):
    """Ingesta manual de una página concreta en un chatbot (idempotente).

    Deploy: edge. Encola la ingestión en background y responde 202.
    """
    background_tasks.add_task(svc.ingest_page, chatbot_id, page_id)
    return {"status": "queued", "chatbot_id": str(chatbot_id), "page_id": str(page_id)}


@router.delete(
    "/hub/chatbots/{chatbot_id}/pages/{page_id}",
    operation_id="retirePage",
)
async def retire_page(
    chatbot_id: uuid.UUID,
    page_id: uuid.UUID,
    current_user: UserInfo = Depends(_require_admin_or_partner),
    svc: Any = Depends(get_selection_service),
):
    """Retira todos los documentos de una página para un chatbot.

    Deploy: edge. Devuelve el número de documentos eliminados.
    """
    count = await svc.retire_page(chatbot_id, page_id)
    return {"documents_removed": count}
