"""Contratos Pydantic para la gestión de sitios y selecciones (9Q.7).

Deploy: edge.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SiteView(BaseModel):
    id: uuid.UUID
    organizacion_id: uuid.UUID | None
    name: str
    root_url: str
    sitemap_url: str | None
    spider_type: str
    crawl_interval_hours: int
    audit_semantic_scope: str
    last_crawled_at: datetime | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SiteCreate(BaseModel):
    name: str
    root_url: str
    sitemap_url: str | None = None
    audit_semantic_scope: str = "ingested"
    crawl_interval_hours: int = 24


class SitePatch(BaseModel):
    name: str | None = None
    root_url: str | None = None
    sitemap_url: str | None = None
    audit_semantic_scope: str | None = None
    crawl_interval_hours: int | None = None


class PageView(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    url: str
    title: str | None
    status: str
    token_count: int | None
    superseded: bool
    quality_score: float | None
    last_crawled_at: datetime | None

    model_config = {"from_attributes": True}


class SelectionView(BaseModel):
    id: uuid.UUID
    chatbot_id: uuid.UUID
    site_id: uuid.UUID
    rule_type: str
    rule_value: str | None
    auto_ingest_new: bool
    created_at: datetime

    model_config = {"from_attributes": True}


#: Los tipos de regla que `SelectionRepo.matches` sabe evaluar. Cualquier otro se guardaba
#: con un 201 y no casaba nunca: en la pantalla, una selección activa y ninguna página
#: seleccionada, sin nada que explicara por qué (VER.8). Mismo criterio que el spider
#: desconocido del dispatcher: fallar donde se ve, no caer a algo que parece funcionar.
TiposDeRegla = Literal["path_prefix", "sitemap_section", "manual"]


class SelectionCreate(BaseModel):
    site_id: uuid.UUID
    rule_type: TiposDeRegla
    rule_value: str | None = None
    auto_ingest_new: bool = True


class CandidatePageView(BaseModel):
    page_id: uuid.UUID
    url: str
    title: str | None
    matched_rule: str | None
    is_new: bool
