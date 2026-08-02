"""Punto de entrada FastAPI standalone del servidor Gov Gen AI.

Registra los routers de la plataforma migrada (Hub, redacción, automation API…).
Los routers automation/telemetry quedan pendientes de registrar aquí mientras se
completa la migración de su capa de servicio (AIBrainService).
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.app.core.cors import politica_cors
from server.app.database.db import init_server_db
from server.app.api.v1.hub_chat import router as hub_chat_router
from server.app.api.v1.hub_feedback import router as hub_feedback_router
from server.app.api.v1.hub_usage import router as hub_usage_router
from server.app.api.v1.hub_tasks import router as hub_tasks_router
from server.app.api.v1.ingestion import router as ingestion_router
from server.app.api.v1.edge_sync import router as edge_sync_router
from server.app.routers.auth_router import router as auth_router
from server.app.routers.saml_auth_router import router as saml_auth_router
from server.app.routers.pat_router import router as pat_router
from server.app.routers.library_router import router as library_router
from server.app.routers.hub_chatbots_router import router as hub_chatbots_router
from server.app.routers.hub_organizaciones_router import router as hub_organizaciones_router
from server.app.routers.hub_ingestion_router import router as hub_ingestion_router
from server.app.routers.hub_llm_configs_router import router as hub_llm_configs_router
from server.app.routers.hub_prompt_templates_router import router as hub_prompt_templates_router
from server.app.routers.redaccion.llm_drafts_router import router as llm_drafts_router
from server.app.routers.redaccion.hub_redaccion_router import router as hub_redaccion_router
from server.app.routers.redaccion.workspaces_router import router as redaccion_workspaces_router
from server.app.routers.redaccion.scripts_router import router as redaccion_scripts_router
from server.app.routers.redaccion.charts_router import router as redaccion_charts_router
from server.app.routers.redaccion.manifests_router import router as redaccion_manifests_router
from server.app.routers.redaccion.copilot_router import router as redaccion_copilot_router
from server.app.routers.redaccion.anonymization_router import router as redaccion_anonymization_router
from server.app.routers.hub_themes_router import router as hub_themes_router
from server.app.routers.hub_agents_router import router as hub_agents_router
from server.app.routers.hub_sites_router import router as hub_sites_router
from server.app.routers.hub_content_quality_router import router as hub_content_quality_router
from server.app.routers.hub_test_scenarios_router import router as hub_test_scenarios_router


async def _init_hub_db() -> None:
    """Crea las tablas de agents_hub (config y operacionales) si no existen."""
    from server.app.modules.agents_hub.database.connection import create_async_engine as hub_engine
    from server.app.modules.agents_hub.database.base import HubConfigBase, HubOperationalBase
    import server.app.modules.agents_hub.database.config_models  # noqa: F401 — registra tablas
    import server.app.modules.agents_hub.database.operational_models  # noqa: F401 — registra tablas

    engine = hub_engine()
    async with engine.begin() as conn:
        await conn.run_sync(HubConfigBase.metadata.create_all)
        await conn.run_sync(HubOperationalBase.metadata.create_all)
    await engine.dispose()


def _start_quality_scheduler():
    """Crea e inicia el scheduler de calidad de contenido web (9Q.5).

    Deploy: edge. Retorna el scheduler o None si está deshabilitado.
    """
    try:
        from server.app.core.config import get_settings
        settings = get_settings()

        if not settings.content_quality_enabled:
            return None

        from server.app.modules.agents_hub.database.connection import (
            create_async_engine,
            create_session_factory,
        )
        from server.app.modules.agents_hub.ingestion.quality.quality_job import (
            SiteQualityAnalysisJob,
        )
        from server.app.modules.agents_hub.ingestion.quality.quality_scheduler import (
            create_quality_scheduler,
        )

        engine = create_async_engine()
        hub_session_factory = create_session_factory(engine)

        # El job se construye con listas vacías de detectores y sin watcher para el
        # arranque inicial: los detectores completos (con LLM y embedding) se inyectan
        # en producción a través de la configuración de cada entorno. En este arranque
        # básico el scheduler solo realiza crawls y consolidaciones deterministas.
        job = SiteQualityAnalysisJob(
            session_factory=hub_session_factory,
            site_crawler=_NullCrawler(),
            detectors=[],
            watcher=None,
            selection_repo=_NullSelectionRepo(),
            run_semantic=settings.content_quality_semantic_enabled,
        )

        scheduler = create_quality_scheduler(
            hub_session_factory,
            job,
            interval_hours=settings.content_quality_interval_hours,
            enabled=settings.content_quality_enabled,
        )
        scheduler.start()
        # Registrar el job en el router de sitios para el endpoint /crawl
        from server.app.routers.hub_sites_router import set_quality_job
        set_quality_job(job)
        from server.app.routers.hub_content_quality_router import set_quality_job as set_cq_job
        set_cq_job(job)
        print(f"[STARTUP] Content quality scheduler started (every {settings.content_quality_interval_hours}h)")
        return scheduler
    except Exception as exc:
        print(f"[STARTUP] Content quality scheduler failed to start: {exc}")
        return None


class _NullCrawler:
    """Crawl stub para el arranque sin configuración completa."""

    async def crawl_site(self, site_id):  # noqa: ANN001
        from server.app.modules.agents_hub.ingestion.quality.site_crawler import SiteCrawlSummary
        return SiteCrawlSummary(errors=["no spider configured"])


class _NullSelectionRepo:
    """Selection repo stub para el arranque sin configuración completa."""

    async def list_by_site(self, site_id):  # noqa: ANN001
        return []

    def matches(self, selection, page_url: str) -> bool:
        return False


async def _fail_zombie_jobs() -> None:
    """Marca como fallidos los jobs que quedaron en running/pending al reiniciar el servidor."""
    from sqlalchemy import update
    from server.app.modules.agents_hub.database.connection import get_async_session
    from server.app.modules.agents_hub.database.operational_models import HubIngestionJob
    async for session in get_async_session():
        await session.execute(
            update(HubIngestionJob)
            .where(HubIngestionJob.status.in_(["running", "pending"]))
            .values(status="failed", error_message="Job interrumpido (servidor reiniciado)")
        )
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_server_db()
    await _init_hub_db()
    await _fail_zombie_jobs()
    from server.app.database.seeds import seed_all

    await seed_all()
    from server.app.modules.agents_hub.database.seeds import seed_hub_defaults

    await seed_hub_defaults()

    from server.app.services.model_fetcher import refresh_model_cache
    from server.app.services.pricing_service import update_prices_from_openrouter
    import asyncio

    # Initial refresh at startup (legacy behavior)
    print("[STARTUP] Refreshing AI model cache...")
    await refresh_model_cache()
    print("[STARTUP] Updating model prices...")
    await update_prices_from_openrouter()

    # Background loop for 24h refresh
    async def periodic_refresh():
        while True:
            await asyncio.sleep(24 * 60 * 60)  # 24 hours
            await refresh_model_cache()
            await update_prices_from_openrouter()

    refresh_task = asyncio.create_task(periodic_refresh())

    # Content quality scheduler (9Q.5) — Deploy: edge
    quality_scheduler = _start_quality_scheduler()

    yield

    refresh_task.cancel()
    if quality_scheduler is not None:
        quality_scheduler.shutdown(wait=False)


app = FastAPI(title="Gov Gen AI Platform", version="1.0.0", lifespan=lifespan)

# SEC.3: los orígenes salen de la configuración y no del código. En producción no hay
# comodín ni aunque la variable de entorno lo traiga; el porqué está en `core/cors.py`.
app.add_middleware(
    CORSMiddleware,
    **politica_cors(
        entorno=os.getenv("ENVIRONMENT", "development"),
        origenes_csv=os.getenv("CORS_ALLOWED_ORIGINS"),
    ),
)

DEPLOY_MODE = os.getenv("DEPLOY_MODE", "all").lower()
if DEPLOY_MODE not in ("cloud", "edge", "all"):
    raise RuntimeError(f"Invalid DEPLOY_MODE: {DEPLOY_MODE}")


def _register_cloud(app: FastAPI) -> None:
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(saml_auth_router, prefix="/api/v1")  # Deploy: cloud
    app.include_router(pat_router, prefix="/api/v1")  # Deploy: cloud
    app.include_router(library_router, prefix="/api")
    app.include_router(hub_chatbots_router, prefix="/api/v1")
    app.include_router(hub_organizaciones_router, prefix="/api/v1")
    app.include_router(hub_ingestion_router, prefix="/api/v1")
    app.include_router(hub_llm_configs_router, prefix="/api/v1")
    app.include_router(hub_prompt_templates_router, prefix="/api/v1")
    app.include_router(hub_themes_router, prefix="/api/v1")  # Deploy: cloud
    app.include_router(edge_sync_router, prefix="/api/v1")  # servido por cloud


def _register_edge(app: FastAPI) -> None:
    app.include_router(hub_chat_router, prefix="/api/v1")
    app.include_router(hub_feedback_router, prefix="/api/v1")
    app.include_router(hub_usage_router, prefix="/api/v1")  # Deploy: edge (SEC.4)
    app.include_router(hub_tasks_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")
    app.include_router(llm_drafts_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(hub_redaccion_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(redaccion_workspaces_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(redaccion_scripts_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(redaccion_charts_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(redaccion_manifests_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(redaccion_copilot_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(redaccion_anonymization_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(hub_agents_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(hub_sites_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(hub_content_quality_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(hub_test_scenarios_router, prefix="/api/v1")  # Deploy: edge


if DEPLOY_MODE in ("cloud", "all"):
    _register_cloud(app)
if DEPLOY_MODE in ("edge", "all"):
    _register_edge(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
