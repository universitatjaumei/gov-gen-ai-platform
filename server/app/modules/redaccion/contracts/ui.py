"""Contrato UI adaptativo — 9R.1.2.

ReportUIContract describe al frontend qué componentes renderizar, en qué orden y
con qué configuración. El frontend lo consume via Orval sin hardcodear lógica.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class UIFieldDescriptor(BaseModel):
    slot_id: str
    label: dict[str, str]
    field_type: str = "text"
    placeholder: dict[str, str] = {}
    required: bool = False


class UIDropzoneDescriptor(BaseModel):
    slot_id: str
    label: dict[str, str]
    accept: list[str] = []
    multiple: bool = False
    max_size_mb: int | None = None


class UISection(BaseModel):
    id: str
    title: str
    order: int
    block_ids: list[str] = []


class ReportUIContract(BaseModel):
    wizard_steps: list[UISection]
    dropzones: list[UIDropzoneDescriptor]
    manual_fields: list[UIFieldDescriptor]
    block_editor_enabled: bool
    ai_review_panel_enabled: bool
    preview_layout: Literal["markdown", "docx-like", "split"]
