"""Modelos Pydantic del contrato HTTP del sandbox."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExecuteExtractionRequest(BaseModel):
    code: str
    file_path: str = ""
    raw_text: str = ""
    options: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 30
    # PRO.2 — el contenido del fichero, no su ruta.
    #
    # `file_path` era una ruta del host de la API, y dentro de este contenedor no existe
    # ningún fichero ahí: `pd.read_excel(file_path)` fallaba siempre. `/execute-chart` y
    # `/execute-etl` ya recibían el contenido (`data_csv`) y lo escribían en su temporal;
    # la extracción hace lo mismo. El nombre viaja porque pandas elige el motor por la
    # extensión.
    file_bytes_b64: str = ""
    file_name: str = ""


class ExtractionPayload(BaseModel):
    tables: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    free_text: str | None = None


class ExecuteExtractionResponse(BaseModel):
    result: ExtractionPayload
    stdout_truncated: bool = False


class ExecuteChartRequest(BaseModel):
    code: str
    data_csv: str
    output_format: Literal["png", "svg"] = "png"
    timeout_seconds: int = 30


class ExecuteEtlRequest(BaseModel):
    code: str
    data_csv: str
    timeout_seconds: int = 30
