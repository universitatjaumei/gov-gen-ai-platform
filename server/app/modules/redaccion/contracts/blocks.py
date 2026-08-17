"""Contratos de bloque — 9R.1.2.

BlockContract es una discriminated union por `kind`. Cada subtipo añade solo los campos
obligatorios para ese tipo de bloque; los campos comunes viven en _BlockBase.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, model_validator

from server.app.modules.redaccion.contracts.block_io import BlockReference
from server.app.modules.redaccion.services.charts.chart_configuration import (
    OrdenDeCategorias,
    TipoDeGrafico,
)
from server.app.modules.redaccion.services.transformation.operations import Operation


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
    # PRO.3 — lo que el pipeline necesita además del fichero. Para `admin_script` es el
    # código aprobado (`{"code": ..., "approved": True}`), que la cola de aprobación incrusta
    # aquí: sin un sitio en el contrato, el bloque que escribía `approve` no validaba y la
    # plantilla quedaba ilegible para el grafo.
    options: dict[str, Any] = Field(default_factory=dict)


class TableBlock(_BlockBase):
    kind: Literal["TABLE"] = "TABLE"
    data_block_ref: str


class ChartBlockConfig(BaseModel):
    """Configuración de visualización para un ChartBlock.

    PRO.8 — esto es **lo que una plantilla puede pedir**, y hasta aquí no podía pedir ni un
    título: el renderizador sabía ponerlo, pero este contrato sólo pasaba tipo, columnas,
    paleta, agregación y formato. Un gráfico con `credito_inicial` como etiqueta de eje no es
    publicable, y arreglarlo exigía generar un script. Ahora la presentación completa es
    declarativa.
    """

    mode: Literal["deterministic", "ai"] = "deterministic"
    chart_type: TipoDeGrafico = "bar"
    x_axis: str | None = None
    y_axis: str | None = None
    color_by: str | None = None
    label_column: str | None = None
    value_column: str | None = None
    size_column: str | None = None
    nl_prompt: str | None = None
    palette: str = "viridis"
    aggregation: Literal["sum", "mean", "count", "min", "max", "none"] = "none"
    sort: OrdenDeCategorias = "none"
    output_format: Literal["png", "svg"] = "png"

    # Presentación
    title: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    show_values: bool = False
    show_legend: bool = True
    show_grid: bool = True
    bins: int | None = None
    size: tuple[float, float] = (10, 6)
    style: str = "whitegrid"
    value_format: str = "{:,.2f}"
    number_format: Literal["es", "en"] = "es"


class ChartBlock(_BlockBase):
    kind: Literal["CHART"] = "CHART"
    data_block_ref: str
    config: ChartBlockConfig | None = None


class DataTransformBlockConfig(BaseModel):
    """Configuración de un bloque DATA_TRANSFORM.

    `mode='deterministic'` aplica directamente `operations` sobre los datos
    referenciados por `source_block_ref`. `mode='ai'` traduce
    `nl_instruction` a operaciones declarativas (o, en última instancia, a
    un script Python auditado) usando el ETLFactory.
    """

    mode: Literal["deterministic", "ai"] = "deterministic"
    source_block_ref: BlockReference
    operations: list[Operation] | None = None
    nl_instruction: str | None = None

    @model_validator(mode="after")
    def _validate_mode_fields(self) -> "DataTransformBlockConfig":
        if self.mode == "deterministic" and not self.operations:
            raise ValueError("operations is required when mode='deterministic'")
        if self.mode == "ai" and not self.nl_instruction:
            raise ValueError("nl_instruction is required when mode='ai'")
        return self


class DataTransformBlock(_BlockBase):
    kind: Literal["DATA_TRANSFORM"] = "DATA_TRANSFORM"
    config: DataTransformBlockConfig


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
        DataTransformBlock,
        AIAssistedTextBlock,
        AISummaryBlock,
        AIRewriteBlock,
        CitationBlock,
        ReviewGateBlock,
    ],
    Field(discriminator="kind"),
]
