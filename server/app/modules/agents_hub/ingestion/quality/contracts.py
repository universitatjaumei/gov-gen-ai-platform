"""Contratos Pydantic para hallazgos de calidad de contenido web (9Q.1)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


FindingType = Literal[
    "superseded",
    "duplicate",
    "contradiction",
    "empty",
    "thin",
    "stale",
    "crawl_error",
    "orphan_page",
]

FindingSeverity = Literal["info", "warning", "critical"]

FindingStatus = Literal["new", "confirmed", "dismissed", "resolved"]

_VALID_FINDING_TRANSITIONS: dict[str, set[str]] = {
    "new": {"confirmed", "dismissed"},
    "confirmed": {"resolved", "dismissed"},
    "dismissed": {"new"},
    "resolved": set(),
}


class InvalidFindingTransitionError(ValueError):
    pass


class ContentFinding(BaseModel, frozen=True):
    id: uuid.UUID
    site_id: uuid.UUID
    finding_type: FindingType
    severity: FindingSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    detected_at: datetime
    status: FindingStatus = "new"

    page_id: uuid.UUID | None = None
    related_page_id: uuid.UUID | None = None
    source_url: str | None = None
    signal: dict[str, Any] = Field(default_factory=dict)

    reviewed_at: datetime | None = None
    reviewed_by: uuid.UUID | None = None
    resolution_note: str | None = None
