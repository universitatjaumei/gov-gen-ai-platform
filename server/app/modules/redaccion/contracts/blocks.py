"""Contratos de bloque — 9R.1.2.

BlockContract es una discriminated union por `kind`. Cada subtipo añade solo los campos
obligatorios para ese tipo de bloque; los campos comunes viven en _BlockBase.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from server.app.modules.redaccion.contracts.block_io import BlockReference


class _BlockBase(BaseModel):
    id: str
    title: str
    required: bool = False
    depends_on: list[BlockReference] = []
    order: int = 0


class StaticTextBlock(_BlockBase):
    kind: Literal["STATIC_TEXT"] = "STATIC_TEXT"
    content: str = ""


class UserInputBlock(_BlockBase):
    kind: Literal["USER_INPUT"] = "USER_INPUT"
    field_type: str = "text"


class DeterministicDataBlock(_BlockBase):
    kind: Literal["DETERMINISTIC_DATA"] = "DETERMINISTIC_DATA"
    source_pipeline: str


class TableBlock(_BlockBase):
    kind: Literal["TABLE"] = "TABLE"
    data_block_ref: str


class ChartBlock(_BlockBase):
    kind: Literal["CHART"] = "CHART"
    data_block_ref: str


class AIAssistedTextBlock(_BlockBase):
    kind: Literal["AI_ASSISTED_TEXT"] = "AI_ASSISTED_TEXT"
    ai_prompt_template_id: str
    review_policy_id: str


class AISummaryBlock(_BlockBase):
    kind: Literal["AI_SUMMARY"] = "AI_SUMMARY"
    ai_prompt_template_id: str
    review_policy_id: str


class AIRewriteBlock(_BlockBase):
    kind: Literal["AI_REWRITE"] = "AI_REWRITE"
    ai_prompt_template_id: str
    review_policy_id: str


class CitationBlock(_BlockBase):
    kind: Literal["CITATION_BLOCK"] = "CITATION_BLOCK"
    source_block_refs: list[str] = []


class ReviewGateBlock(_BlockBase):
    kind: Literal["REVIEW_GATE"] = "REVIEW_GATE"
    review_policy_id: str


BlockContract = Annotated[
    Union[
        StaticTextBlock,
        UserInputBlock,
        DeterministicDataBlock,
        TableBlock,
        ChartBlock,
        AIAssistedTextBlock,
        AISummaryBlock,
        AIRewriteBlock,
        CitationBlock,
        ReviewGateBlock,
    ],
    Field(discriminator="kind"),
]
