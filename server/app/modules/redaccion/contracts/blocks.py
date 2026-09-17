"""Contratos de bloque — 9R.1.2.

BlockContract es una discriminated union por `kind`. Cada subtipo añade solo los campos
obligatorios para ese tipo de bloque; los campos comunes viven en _BlockBase.
"""
from __future__ import annotations

import uuid
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


class FuncionRef(BaseModel):
    """Qué función del catálogo ejecuta un bloque, y **en qué versión exacta** (FUN.3).

    El anclaje por versión es la clave de bóveda del bloque FUN: publicar v2 no toca ninguna
    plantilla anclada a v1. Sin él, «arreglar una vez» sería «cambiar en silencio informes ya
    aprobados» y el `RunManifest` dejaría de ser reproducible.
    """

    funcion_id: uuid.UUID
    version: int = Field(ge=1)


class DeterministicDataBlock(_BlockBase):
    kind: Literal["DETERMINISTIC_DATA"] = "DETERMINISTIC_DATA"
    source_pipeline: str
    #: FUN.3 — la función del catálogo que este bloque ejecuta. **Sustituye al código
    #: incrustado**: dos plantillas que necesitan la misma extracción la referencian, en vez de
    #: llevar dos copias que pueden divergir.
    funcion_ref: FuncionRef | None = None
    # PRO.3 — lo que el pipeline necesita además del fichero.
    #
    # **Ya no lleva el código.** FUN.3 lo retira del contrato, no sólo del sitio que lo
    # escribía: si `options.code` siguiera validando, una plantilla podría volver a llevar el
    # código dentro y nadie lo vería hasta que divergiera de su función.
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _un_script_se_referencia_y_no_se_incrusta(self) -> "DeterministicDataBlock":
        prohibidas = sorted({"code", "approved"} & set(self.options))
        if prohibidas:
            raise ValueError(
                f"{', '.join(prohibidas)} ya no va en las opciones de un bloque: el código de "
                "una función vive en el catálogo y el bloque lo referencia con `funcion_ref` "
                "(FUN.3)"
            )
        if self.source_pipeline == "admin_script" and self.funcion_ref is None:
            raise ValueError(
                "un bloque `admin_script` necesita `funcion_ref`: sin función no hay nada que "
                "ejecutar, y antes eso se manifestaba como «script no aprobado», que acusaba a "
                "la aprobación cuando lo que faltaba era el código"
            )
        return self


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


class _BloqueDeIA(_BlockBase):
    """Lo común a los tres bloques que escriben texto con un modelo.

    SEG.1 — `data_block_refs` es lo que permite decir «valora **esta** tabla». Sin él, el nodo
    entregaba a cada apartado un contexto con **todos** los bloques extraídos del informe: con
    treinta tablas, cada valoración recibía las treinta y el encargo de «redacta esta sección»,
    que es la receta del resumen que mezcla y omite.

    Vacío significa «todo el informe», que es el comportamiento anterior: hay plantillas vivas
    que dependen de él. Pero el alcance usado queda registrado en el bloque, porque una
    valoración cuya fuente no consta no se puede auditar.
    """

    ai_prompt_template_id: str
    review_policy_id: str
    data_block_refs: list[str] = []


class AIAssistedTextBlock(_BloqueDeIA):
    kind: Literal["AI_ASSISTED_TEXT"] = "AI_ASSISTED_TEXT"


class AISummaryBlock(_BloqueDeIA):
    kind: Literal["AI_SUMMARY"] = "AI_SUMMARY"


class AIRewriteBlock(_BloqueDeIA):
    kind: Literal["AI_REWRITE"] = "AI_REWRITE"


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
