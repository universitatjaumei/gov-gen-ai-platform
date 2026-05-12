"""Contratos del draft LLM — 9R.1.3.

ReportTemplateDraft es lo que devuelve LLMSpecService (9R.4.1).
No es persistente: requiere validación estructural + aprobación HITL antes
de convertirse en ReportTemplateContract.
"""
from __future__ import annotations

from pydantic import BaseModel

from server.app.modules.redaccion.contracts.blocks import BlockContract
from server.app.modules.redaccion.contracts.inputs import InputContract
from server.app.modules.redaccion.contracts.template import (
    ReportProfileId,
    SectionContract,
)


class ReportTemplateDraft(BaseModel):
    proposed_profile: str  # validado por DraftValidator; str para aceptar output crudo del LLM
    proposed_sections: list[SectionContract]
    proposed_blocks: list[BlockContract]
    proposed_inputs: InputContract
    rationale: str
    model_used: str
    prompt_version: str


class DraftValidationError(BaseModel):
    field: str
    message: str


class ReportTemplateDraftValidationResult(BaseModel):
    ok: bool
    normalized_draft: ReportTemplateDraft | None = None
    errors: list[DraftValidationError] = []
