"""Contratos de inputs — 9R.1.2.

InputSlot describe un archivo o campo que el usuario debe proporcionar antes
de iniciar el pipeline. InputContract agrupa los slots requeridos y opcionales.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

InputSlotKind = Literal["pdf", "excel", "csv", "text", "number", "date", "selector"]


class InputSlot(BaseModel):
    slot_id: str
    kind: InputSlotKind
    label: dict[str, str]  # i18n {es, ca, en}
    required: bool = True
    multiple: bool = False
    max_size_mb: int | None = None
    validation: dict | None = None  # regex, min/max, required_columns, etc.


class InputContract(BaseModel):
    required_slots: list[InputSlot] = []
    optional_slots: list[InputSlot] = []
