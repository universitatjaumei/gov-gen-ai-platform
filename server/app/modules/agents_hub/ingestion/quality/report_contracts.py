"""Contratos Pydantic para el informe de auditoría web (9Q.8).

Deploy: edge.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ContentFindingView(BaseModel):
    id: uuid.UUID
    finding_type: str
    severity: str
    status: str
    confidence: float
    page_url: str | None
    related_page_url: str | None
    detected_at: datetime
    explanation: str | None


class FindingTypeSection(BaseModel):
    finding_type: str
    findings: list[ContentFindingView]
    recommendation: str


class WebQualityReport(BaseModel):
    site_id: uuid.UUID
    site_name: str
    generated_at: datetime
    totals_by_type: dict[str, int]
    totals_by_severity: dict[str, int]
    sections: list[FindingTypeSection]
