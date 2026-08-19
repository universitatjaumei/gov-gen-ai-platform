"""Router de curación — sitios rastreados, selecciones y candidatas (9Q.7, re-etiquetado en CUR.1).

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
from server.app.core.auth.tenancy import (
    assert_chatbot_org_access,
    assert_org_access,
    assert_site_org_access,
    scope_query_to_orgs,
)
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import HubCrawledPage
from server.app.modules.curation.selection_contracts import (
    CandidatePageView,
    CrawlConfig,
    PageContentView,
    PageView,
    SelectionCreate,
    SelectionView,
    SiteCreate,
    SitePatch,
    SiteView,
)
from server.app.modules.curation.site_repo import (
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
    from server.app.modules.curation.selection_service import (
        CorpusSelectionService,
    )

    page_repo = CrawledPageRepo(session)
    sel_repo = CorpusSelectionRepo(session)
    return CorpusSelectionService(session, page_repo, sel_repo, watcher=None)


async def _servicio_que_puede_ingerir(session: AsyncSession, chatbot_id: uuid.UUID) -> Any:
    """El servicio de selección **con watcher**, que es el único que puede ingerir.

    El embedding lo resuelve la cascada del chatbot: ingerir con otro modelo del que usa su
    corpus dejaría vectores que no se pueden comparar con los que ya hay.
    """
    from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
    from server.app.modules.agents_hub.services.embedding_resolver import (
        resolve_embedding_service,
    )
    from server.app.modules.curation.selection_service import CorpusSelectionService

    watcher = IngestionWatcher(
        session=session,
        embedding_service=await resolve_embedding_service(session, chatbot_id),
    )
    return CorpusSelectionService(
        session, CrawledPageRepo(session), CorpusSelectionRepo(session), watcher=watcher
    )


async def _require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if not (user.is_superadmin or user.is_admin):
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
    organizacion_id: uuid.UUID | None = Query(default=None),
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Crea un nuevo sitio rastreado.

    Deploy: edge. organizacion_id se provee como query param; no va en el body.

    SEC.8.1: el parámetro lo elige quien llama, así que se valida contra el token. Sin
    organización el sitio quedaría fuera de toda cascada —y de todo listado acotado—, de
    modo que crear uno así queda reservado al superadministrador, igual que los temas de
    plataforma.
    """
    if organizacion_id is None:
        if not current_user.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Indica la organización del sitio",
            )
    else:
        assert_org_access(current_user, organizacion_id)

    repo = WebSiteRepo(session)
    site = await repo.create(
        organizacion_id=organizacion_id,
        name=body.name,
        root_url=body.root_url,
        sitemap_url=body.sitemap_url,
        crawl_interval_hours=body.crawl_interval_hours,
        audit_semantic_scope=body.audit_semantic_scope,
        # RAS.5 — la configuración del rastreo se podía leer pero no fijar, así que el filtro por
        # apartado (`url_regex_filter`) era inalcanzable desde la interfaz. Sin ella se guardan
        # los defectos conservadores de RAS.1, no un rastreo sin límites.
        config_json=(body.crawl_config or CrawlConfig()).model_dump(),
    )
    await session.commit()
    return site


@router.get(
    "/hub/sites",
    response_model=list[SiteView],
    operation_id="listSites",
)
async def list_sites(
    organizacion_id: uuid.UUID | None = Query(default=None),
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Lista sitios, opcionalmente filtrados por organizacion_id.

    Deploy: edge. SEC.8.1: el filtro por organización dejó de ser opcional. Antes acotaba
    solo si el cliente pasaba el parámetro —o sea, el filtro lo elegía quien preguntaba— y
    sin parámetro devolvía los sitios de todas las administraciones.
    """
    from server.app.modules.agents_hub.database.operational_models import HubWebSite

    stmt = scope_query_to_orgs(select(HubWebSite), current_user, HubWebSite)
    if organizacion_id is not None:
        assert_org_access(current_user, organizacion_id)
        stmt = stmt.where(HubWebSite.organizacion_id == organizacion_id)
    result = await session.execute(stmt.order_by(HubWebSite.created_at.desc()))
    return result.scalars().all()


@router.patch(
    "/hub/sites/{site_id}",
    response_model=SiteView,
    operation_id="patchSite",
)
async def patch_site(
    site_id: uuid.UUID,
    body: SitePatch,
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Actualiza campos de un sitio.

    Deploy: edge.
    """
    await assert_site_org_access(session, site_id, current_user)
    repo = WebSiteRepo(session)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    # La configuración del rastreo se guarda en `config_json`, que es como la lee el spider.
    if "crawl_config" in updates:
        updates["config_json"] = updates.pop("crawl_config")
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
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Elimina un sitio y todas sus páginas (CASCADE).

    Deploy: edge.
    """
    await assert_site_org_access(session, site_id, current_user)
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
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
    quality_job: Any = Depends(get_quality_job),
):
    """Dispara un crawl + análisis de calidad en background.

    Deploy: edge. Responde 202 Accepted inmediatamente.
    """
    await assert_site_org_access(session, site_id, current_user)

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
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Lista las páginas rastreadas de un sitio, opcionalmente filtradas por status.

    Deploy: edge.
    """
    await assert_site_org_access(session, site_id, current_user)
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
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Crea una regla de selección de corpus para un chatbot.

    Deploy: edge.
    """
    await assert_chatbot_org_access(session, chatbot_id, current_user)
    await assert_site_org_access(session, body.site_id, current_user)
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
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Lista las selecciones de corpus de un chatbot.

    Deploy: edge.
    """
    await assert_chatbot_org_access(session, chatbot_id, current_user)
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
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Elimina una selección de corpus.

    Deploy: edge.
    """
    await assert_chatbot_org_access(session, chatbot_id, current_user)
    repo = CorpusSelectionRepo(session)
    await repo.delete(selection_id)
    await session.commit()


@router.get(
    "/hub/pages/{page_id}/content",
    response_model=PageContentView,
    operation_id="getPageContent",
)
async def get_page_content(
    page_id: uuid.UUID,
    current_user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """El texto guardado de una página rastreada: lo que iría al corpus (CUR.4).

    Deploy: edge. El informe de calidad acusaba y no dejaba comprobar —«hay que copiar y pegar»—, y
    no había ninguna pantalla que mostrara el contenido de una página. Hace falta para juzgar si un
    hallazgo es cierto, para decidir si la página merece publicarse y, desde CUR.3, para comprobar
    que el recorte de plantilla no se ha llevado contenido por delante.
    """
    pagina = await session.get(HubCrawledPage, page_id)
    if pagina is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    # El texto de una página es contenido del cliente, así que la guarda de organización va aquí
    # igual que en el resto del módulo.
    await assert_site_org_access(session, pagina.site_id, current_user)

    return PageContentView(
        id=pagina.id,
        url=pagina.url,
        title=pagina.title,
        status=pagina.status,
        # Vacío y no nulo: una página en error no tiene texto, y eso hay que poder verlo sin
        # adivinar si falta el dato o falta el contenido.
        content=pagina.markdown_content or "",
        token_count=pagina.token_count,
        owner=getattr(pagina, "content_owner", None),
        published_at=getattr(pagina, "content_published_at", None),
        render_signals=list(getattr(pagina, "render_signals", None) or []),
    )


# ──────────────────────── Candidatas e ingestión ────────────────────────


@router.get(
    "/hub/sites/{site_id}/candidates",
    response_model=list[CandidatePageView],
    operation_id="listCandidates",
)
async def list_candidates(
    site_id: uuid.UUID,
    chatbot_id: uuid.UUID = Query(...),
    current_user: UserInfo = Depends(_require_admin),
    svc: Any = Depends(get_selection_service),
    session: AsyncSession = Depends(get_async_session),
):
    """Páginas candidatas a ingerir: activas, no ingeridas aún para el chatbot.

    Deploy: edge.
    """
    await assert_site_org_access(session, site_id, current_user)
    await assert_chatbot_org_access(session, chatbot_id, current_user)
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
    current_user: UserInfo = Depends(_require_admin),
    svc: Any = Depends(get_selection_service),
    session: AsyncSession = Depends(get_async_session),
):
    """Ingesta manual de una página concreta en un chatbot (idempotente).

    Deploy: edge. Encola la ingestión en background y responde 202.

    RAS.5 — el servicio inyectado se construye **sin watcher** (lo dice su propio docstring: para
    esta operación había que construirlo aquí, y no se hacía), así que `ingest_page` reventaba con
    `AttributeError` **dentro del `BackgroundTask`**: la respuesta era 202 «queued» y la página no
    llegaba nunca al corpus. Sin esto, la curación termina en una bandeja que no lleva a ningún
    sitio, que es justo el circuito que el módulo existe para cerrar.
    """
    await assert_chatbot_org_access(session, chatbot_id, current_user)
    servicio = await _servicio_que_puede_ingerir(session, chatbot_id)
    background_tasks.add_task(servicio.ingest_page, chatbot_id, page_id)
    return {"status": "queued", "chatbot_id": str(chatbot_id), "page_id": str(page_id)}


@router.delete(
    "/hub/chatbots/{chatbot_id}/pages/{page_id}",
    operation_id="retirePage",
)
async def retire_page(
    chatbot_id: uuid.UUID,
    page_id: uuid.UUID,
    current_user: UserInfo = Depends(_require_admin),
    svc: Any = Depends(get_selection_service),
    session: AsyncSession = Depends(get_async_session),
):
    """Retira todos los documentos de una página para un chatbot.

    Deploy: edge. Devuelve el número de documentos eliminados.
    """
    await assert_chatbot_org_access(session, chatbot_id, current_user)
    count = await svc.retire_page(chatbot_id, page_id)
    return {"documents_removed": count}
