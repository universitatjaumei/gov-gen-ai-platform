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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_server_db()
    from server.app.database.seeds import seed_all

    await seed_all()
    from server.app.modules.agents_hub.database.seeds import seed_hub_defaults

    await seed_hub_defaults()
    yield


app = FastAPI(title="Gov Gen AI Platform", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    app.include_router(edge_sync_router, prefix="/api/v1")  # servido por cloud


def _register_edge(app: FastAPI) -> None:
    app.include_router(hub_chat_router, prefix="/api/v1")
    app.include_router(hub_feedback_router, prefix="/api/v1")
    app.include_router(hub_tasks_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")


if DEPLOY_MODE in ("cloud", "all"):
    _register_cloud(app)
if DEPLOY_MODE in ("edge", "all"):
    _register_edge(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
