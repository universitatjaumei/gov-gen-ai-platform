"""Stub API de sincronización Edge.

Deploy: shared
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/edge", tags=["edge-sync"])


class EdgeClientOut(BaseModel):
    id: UUID
    name: str
    partner_id: str
    is_active: bool


class EdgeChatbotOut(BaseModel):
    id: UUID
    client_id: UUID
    llm_config_id: UUID
    name: str
    is_active: bool


class EdgeLLMConfigOut(BaseModel):
    id: UUID
    provider: str
    model_name: str
    temperature: float


class EdgePromptTemplateOut(BaseModel):
    id: UUID
    chatbot_id: UUID
    slug: str
    language: str


class EdgeConfigSnapshot(BaseModel):
    clients: list[EdgeClientOut]
    chatbots: list[EdgeChatbotOut]
    llm_configs: list[EdgeLLMConfigOut]
    prompt_templates: list[EdgePromptTemplateOut]
    generated_at: datetime


class EdgeTelemetryBatch(BaseModel):
    edge_node_id: str
    interactions_count: int
    avg_latency_ms: float
    window_start: datetime
    window_end: datetime


@router.get("/config", response_model=EdgeConfigSnapshot)
async def get_edge_config():
    """Obtiene la configuración cloud para sincronizar al edge."""
    raise HTTPException(501, "Not implemented")


@router.post("/telemetry", status_code=202)
async def ingest_edge_telemetry(body: EdgeTelemetryBatch):
    """Ingesta telemetría desde un edge node."""
    raise HTTPException(501, "Not implemented")
