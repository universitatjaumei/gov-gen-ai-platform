"""Punto de entrada FastAPI standalone del servidor Gov Gen AI.

Incluye únicamente routers sin dependencias de NiceGUI/client_app.
Los routers automation y telemetry dependen de AIBrainService→cortex→nicegui
y se registran en main.py (NiceGUI) hasta completar la migración.
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.app.database.db import init_server_db
from server.app.api.v1.hub_chat import router as hub_chat_router
from server.app.api.v1.hub_feedback import router as hub_feedback_router
from server.app.api.v1.hub_tasks import router as hub_tasks_router
from server.app.api.v1.ingestion import router as ingestion_router
from server.app.api.v1.edge_sync import router as edge_sync_router
from server.app.routers.auth_router import router as auth_router
from server.app.routers.library_router import router as library_router
from server.app.routers.hub_chatbots_router import router as hub_chatbots_router
from server.app.routers.hub_clients_router import router as hub_clients_router
from server.app.routers.hub_ingestion_router import router as hub_ingestion_router
from server.app.routers.hub_llm_configs_router import router as hub_llm_configs_router
from server.app.routers.hub_prompt_templates_router import router as hub_prompt_templates_router
from server.app.routers.redaccion.llm_drafts_router import router as llm_drafts_router
from server.app.routers.redaccion.hub_redaccion_router import router as hub_redaccion_router


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

    from server.app.modules.agents_hub.database.connection import (
        create_session_factory,
        get_engine,
    )
    from server.app.modules.agents_hub.ingestion.source_scheduler import create_scheduler
    from server.app.services.model_fetcher import refresh_model_cache
    from server.app.services.pricing_service import update_prices_from_openrouter
    import asyncio

    scheduler = create_scheduler(create_session_factory(get_engine()))
    scheduler.start()

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

    yield

    scheduler.shutdown(wait=False)
    refresh_task.cancel()


app = FastAPI(title="Gov Gen AI Platform", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEPLOY_MODE = os.getenv("DEPLOY_MODE", "all").lower()
if DEPLOY_MODE not in ("cloud", "edge", "all"):
    raise RuntimeError(f"Invalid DEPLOY_MODE: {DEPLOY_MODE}")


def _register_cloud(app: FastAPI) -> None:
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(library_router, prefix="/api")
    app.include_router(hub_chatbots_router, prefix="/api/v1")
    app.include_router(hub_clients_router, prefix="/api/v1")
    app.include_router(hub_ingestion_router, prefix="/api/v1")
    app.include_router(hub_llm_configs_router, prefix="/api/v1")
    app.include_router(hub_prompt_templates_router, prefix="/api/v1")
    app.include_router(edge_sync_router, prefix="/api/v1")  # servido por cloud


def _register_edge(app: FastAPI) -> None:
    app.include_router(hub_chat_router, prefix="/api/v1")
    app.include_router(hub_feedback_router, prefix="/api/v1")
    app.include_router(hub_tasks_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")
    app.include_router(llm_drafts_router, prefix="/api/v1")  # Deploy: edge
    app.include_router(hub_redaccion_router, prefix="/api/v1")  # Deploy: edge


if DEPLOY_MODE in ("cloud", "all"):
    _register_cloud(app)
if DEPLOY_MODE in ("edge", "all"):
    _register_edge(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
