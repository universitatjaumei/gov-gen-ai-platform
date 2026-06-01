"""Contratos Pydantic del Copilot."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CopilotTargetKind = Literal["chart_config", "etl_ops", "script_proposal"]
CopilotModule = Literal["redaccion", "chatbots", "general"]


class SourceRef(BaseModel):
    """Referencia trazable a un fragmento de la documentación indexada."""

    path: str
    chunk_idx: int
    excerpt: str
    module: CopilotModule = "general"


class CopilotAnswer(BaseModel):
    """Respuesta textual del Copilot con citas a la documentación."""

    answer: str
    source_refs: list[SourceRef] = Field(default_factory=list)


class CopilotAskRequest(BaseModel):
    """Pregunta del usuario al Copilot, contextualizada al módulo activo."""

    question: str = Field(..., min_length=1)
    module: CopilotModule | None = None
    top_k: int = Field(default=4, ge=1, le=10)


class CopilotTranslateRequest(BaseModel):
    """Instrucción NL del usuario que el Copilot traduce a configuración estructurada."""

    instruction: str = Field(..., min_length=1)
    target_kind: CopilotTargetKind
    sample_schema: dict[str, Any] | None = None


class CopilotTranslateResponse(BaseModel):
    """Configuración estructurada producida por el Copilot. El frontend la aplica al wizard activo."""

    kind: CopilotTargetKind
    payload: dict[str, Any]
