"""BlockReference y proyección de outputs entre bloques — 9R.3.3."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


class BlockReference(BaseModel):
    block_id: str
    projection: Literal["raw", "summary", "field"] = "raw"
    field_path: str | None = None

    @model_validator(mode="after")
    def _field_path_required_for_field_projection(self) -> "BlockReference":
        if self.projection == "field" and self.field_path is None:
            raise ValueError("field_path is required when projection='field'")
        return self
