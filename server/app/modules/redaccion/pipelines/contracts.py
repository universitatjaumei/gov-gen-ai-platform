"""Contratos comunes del sistema de extracción — 9R.5.1 / 9R.5.9.

Define el protocolo ExtractionPipeline y todos los tipos de datos que
los pipelines concretos (Excel, PDF, manual, admin_script) deben producir.
Análogo a RetrievalPipeline del bloque 9B.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Tipos de fuente
# ---------------------------------------------------------------------------

ExtractionSourceKind = Literal[
    "excel", "pdf_text", "pdf_table", "manual", "admin_script",
    # SEG.3 — los informes de seguimiento llegan como Markdown con sus tablas ya hechas.
    "md_table",
]

ExtractionPipelineId = str


# ---------------------------------------------------------------------------
# Referencia de almacenamiento (wrapper fsspec-agnóstico)
# ---------------------------------------------------------------------------

class StorageRef(BaseModel):
    """Puntero a un fichero en el backend de almacenamiento (local, S3, GCS)."""

    bucket: str
    key: str

    model_config = {"frozen": True}

    def __str__(self) -> str:
        return f"{self.bucket}/{self.key}"


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

class ExtractionInput(BaseModel):
    """Entrada común a todos los pipelines de extracción."""

    source_kind: ExtractionSourceKind
    file_ref: StorageRef | None = None
    raw_text: str | None = None
    options: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Salida: piezas atómicas
# ---------------------------------------------------------------------------

class ExtractedTable(BaseModel):
    """Tabla extraída de una fuente estructurada."""

    name: str
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    source_page: int | None = None


class ExtractedMetric(BaseModel):
    """Métrica escalar extraída (KPI, porcentaje, cantidad…)."""

    name: str
    value: float | int | str
    unit: str | None = None
    source_cell: str | None = None


class ExtractionWarning(BaseModel):
    """Aviso generado durante la extracción (columna ausente, confianza baja…)."""

    code: str
    message: str
    severity: Literal["info", "warning", "error"]


# ---------------------------------------------------------------------------
# Modelos de documento enriquecido (9R.5.9 — rich Docling extraction)
# ---------------------------------------------------------------------------

class ExtractedCell(BaseModel):
    """Celda de tabla con contenido y coordenadas de bbox."""

    text: str
    bbox: tuple[float, float, float, float] | None = None  # (l, t, r, b)
    col_span: int = 1
    row_span: int = 1


class ExtractedTableRich(BaseModel):
    """Tabla extraída con estructura rica (bbox por celda y tabla)."""

    name: str
    headers: list[str] = Field(default_factory=list)
    rows: list[list[ExtractedCell]] = Field(default_factory=list)
    source_page: int | None = None
    bbox: tuple[float, float, float, float] | None = None  # (l, t, r, b) de la tabla


class ExtractedPage(BaseModel):
    """Contenido de una página individual."""

    page_num: int
    markdown: str = ""
    tables: list[ExtractedTableRich] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    """Documento completo con páginas, markdown completo y estrategia de extracción."""

    pages: list[ExtractedPage] = Field(default_factory=list)
    markdown: str = ""
    extraction_strategy: Literal["text_linear", "complex_tables"] = "text_linear"


class ExtractionProvenance(BaseModel):
    """Trazabilidad de la extracción: quién extrajo, de dónde y cuándo."""

    pipeline_id: ExtractionPipelineId
    source_ref: str
    extracted_at: datetime
    column_mapping: dict | None = None
    pages: list[int] | None = None


# ---------------------------------------------------------------------------
# Resultado agregado
# ---------------------------------------------------------------------------

class ExtractionResult(BaseModel):
    """Resultado completo de la ejecución de un ExtractionPipeline."""

    tables: list[ExtractedTable] = Field(default_factory=list)
    metrics: list[ExtractedMetric] = Field(default_factory=list)
    free_text: str | None = None
    warnings: list[ExtractionWarning] = Field(default_factory=list)
    provenance: ExtractionProvenance
    document: ExtractedDocument | None = None


# ---------------------------------------------------------------------------
# Protocolo
# ---------------------------------------------------------------------------

@runtime_checkable
class ExtractionPipeline(Protocol):
    """Contrato que todo pipeline de extracción debe satisfacer.

    Análogo a RetrievalPipeline en el bloque 9B:
    - pipeline_id identifica de forma única la implementación.
    - extract() es la operación principal.
    - supports() permite que la Factory consulte la compatibilidad antes de invocar.
    """

    pipeline_id: ExtractionPipelineId

    def extract(self, inp: ExtractionInput) -> ExtractionResult:
        ...

    def supports(self, source_kind: str) -> bool:
        ...
