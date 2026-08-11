"""Contratos Pydantic para hallazgos de calidad de contenido web (9Q.1)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


FindingType = Literal[
    "superseded",
    "duplicate",
    "contradiction",
    "empty",
    "thin",
    "stale",
    "crawl_error",
    "orphan_page",
    # RAG.14: hueco de corpus. A diferencia de los demas, no sale de auditar paginas
    # sino de leer conversaciones que salieron mal.
    "content_gap",
    # SYNC.2: la fecha de revision prevista de un documento ha vencido. Tampoco sale de
    # auditar paginas: sale de que pase el tiempo. El sync detecta lo que cambia en origen,
    # y una norma que nadie toca durante tres anos no emite ninguna senal.
    "revisio_vencuda",
    # DER.2: la misma norma con contenidos distintos en dos chatbots de la organización.
    # Es la factura de haber descartado compartir el documento (COR): filas separadas
    # conservan que cada asistente elija su modelo de embedding, y a cambio pueden derivar.
    "copia_divergent",
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
    """Un hallazgo tiene UN sujeto: un sitio web (9Q) o un chatbot (RAG.14).

    El validador no es decoracion: nullable en la columna significa «este hallazgo usa
    el otro sujeto», nunca «sin sujeto». Un hallazgo sin sujeto no se puede revisar.
    """

    id: uuid.UUID
    site_id: uuid.UUID | None = None
    chatbot_id: uuid.UUID | None = None
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

    @model_validator(mode="after")
    def _exactamente_un_sujeto(self) -> "ContentFinding":
        if (self.site_id is None) == (self.chatbot_id is None):
            raise ValueError(
                "un hallazgo cuelga de un sitio O de un chatbot, nunca de los dos ni "
                "de ninguno: sin sujeto no se puede revisar"
            )
        return self
