"""Catálogo declarativo de operaciones ETL — 9R.5.8, ampliado en PRO.4.

Discriminated union por el campo `op`. Cada subtipo añade los campos
necesarios para describir la operación; la ejecución vive en
`DeterministicETLService`.

Hasta PRO.4 este catálogo se orientaba **sólo a análisis** (filter / aggregate / join / pivot /
normalize / groupby) «en lugar de limpieza», por decisión de 9R.5.8. Comparado con el legacy
(`AutomatIA/client_app/app/services/deterministic_etl_service.py`, 350 líneas) resultó que los
dos catálogos casi no se solapan: el suyo es **de limpieza** —quitar y renombrar columnas,
fusionarlas, reordenarlas, formatear fechas, sustituir valores, normalizar texto, rellenar
nulos, quitar duplicados y quitar filas vacías— y es lo que hace falta **primero**: un Excel
real llega con columnas que no se usan, fechas en tres formatos, filas duplicadas y celdas
vacías. Sin eso, «transformar» se quedaba en agrupar lo que ya estuviera limpio.

PRO.4 porta las diez que faltaban. La comparación completa está en
`docs/COMPARATIVA_ETL_LEGACY.md`.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from server.app.modules.redaccion.services.contrato_legible import tipo_legible


# ---------------------------------------------------------------------------
# Operaciones
# ---------------------------------------------------------------------------

FilterComparator = Literal[
    "==", "!=", ">", "<", ">=", "<=",
    "contains", "not_contains",
    "in", "isnull", "notnull",
]


class FilterOp(BaseModel):
    op: Literal["filter"] = "filter"
    col: str
    comparator: FilterComparator
    value: Any = None


AggregateFunction = Literal["sum", "mean", "min", "max", "count", "median", "std"]


class AggregateOp(BaseModel):
    op: Literal["aggregate"] = "aggregate"
    col: str
    function: AggregateFunction


JoinHow = Literal["inner", "left", "right", "outer"]


class JoinOp(BaseModel):
    op: Literal["join"] = "join"
    other_block_ref: str
    on: str | list[str]
    how: JoinHow = "inner"


PivotAggFunction = Literal["sum", "mean", "min", "max", "count"]


class PivotOp(BaseModel):
    op: Literal["pivot"] = "pivot"
    index: str | list[str]
    columns: str
    values: str
    aggfunc: PivotAggFunction = "sum"


NormalizeMethod = Literal["min_max", "z_score"]


class NormalizeOp(BaseModel):
    op: Literal["normalize"] = "normalize"
    cols: list[str]
    method: NormalizeMethod


class GroupByOp(BaseModel):
    op: Literal["groupby"] = "groupby"
    cols: list[str]
    agg_dict: dict[str, AggregateFunction]


# ---------------------------------------------------------------------------
# Limpieza — portadas del legacy en PRO.4
# ---------------------------------------------------------------------------

class DropColumnsOp(BaseModel):
    op: Literal["drop_columns"] = "drop_columns"
    columns: list[str]


class RenameColumnsOp(BaseModel):
    op: Literal["rename_columns"] = "rename_columns"
    mapping: dict[str, str]


class MergeColumnsOp(BaseModel):
    """Fusiona varias columnas en una.

    `drop_source` conserva la **posición de la primera**, como el legacy: una referencia
    fusionada que aparece al final de la tabla obliga a reordenar después.
    """

    op: Literal["merge_columns"] = "merge_columns"
    source_columns: list[str]
    target_column: str
    separator: str = " "
    drop_source: bool = True


class ReorderColumnsOp(BaseModel):
    """Reordena; lo que no se nombre queda al final, en su orden original."""

    op: Literal["reorder_columns"] = "reorder_columns"
    columns: list[str]


class FormatDatesOp(BaseModel):
    """Reformatea una columna de fechas. `source_format` vacío = detección automática."""

    op: Literal["format_dates"] = "format_dates"
    column: str
    source_format: str | None = None
    target_format: str = "ISO8601"


class ReplaceValuesOp(BaseModel):
    op: Literal["replace_values"] = "replace_values"
    column: str
    replacements: dict[str, Any]


NormalizeTextMode = Literal["upper", "lower", "title", "strip", "snake_case"]


class NormalizeTextOp(BaseModel):
    op: Literal["normalize_text"] = "normalize_text"
    columns: list[str]
    mode: NormalizeTextMode


class FillNullsOp(BaseModel):
    op: Literal["fill_nulls"] = "fill_nulls"
    columns: list[str]
    value: Any = ""


class RemoveDuplicatesOp(BaseModel):
    op: Literal["remove_duplicates"] = "remove_duplicates"
    subset: list[str] | None = None
    keep: Literal["first", "last"] = "first"


class DropNullRowsOp(BaseModel):
    op: Literal["drop_null_rows"] = "drop_null_rows"
    subset: list[str] | None = None
    how: Literal["any", "all"] = "any"


# ---------------------------------------------------------------------------
# PRO.9 — lo que una hoja de cálculo necesita para llegar a un informe
#
# Estas cuatro no vienen del legacy: allí tampoco existían. Son el hueco que quedaba entre
# «limpiar una tabla» y «tener los datos que el informe necesita».
# ---------------------------------------------------------------------------


class ToNumberOp(BaseModel):
    """Convierte a número una columna que llega como texto.

    **Es la operación más importante de las cuatro, y la que menos se ve.** Cualquier
    aplicación de gestión de aquí exporta `1.234,56 €`, y sobre texto `sum()` concatena o
    revienta: el informe sale con una cifra mal y **sin un error que mirar**. Va antes que
    cualquier cálculo o agregación.

    Los defectos son los de aquí (`,` decimal y `.` de millares); una hoja en inglés los
    declara al revés.
    """

    op: Literal["to_number"] = "to_number"
    columns: list[str]
    decimal_separator: str = ","
    thousands_separator: str = "."
    strip: list[str] = Field(
        default_factory=lambda: ["€", "%", "$", "EUR", "eur"],
        description="Símbolos que se quitan antes de convertir",
    )


OperadorAritmetico = Literal["+", "-", "*", "/"]


class ComputeColumnOp(BaseModel):
    """Una columna calculada a partir de dos operandos.

    `pct = obligaciones / credito * 100` es *la* transformación de un informe presupuestario.

    **Sin campo de fórmula y sin `eval`**, a propósito: el auditor de PRO.1 prohíbe
    exactamente eso en un script, y admitirlo aquí sería una puerta trasera a lo mismo por otra
    vía. Lo compuesto se consigue **encadenando** operaciones —`t = a + b`, `pct = t / c`,
    `drop t`—: más verboso, auditable, y se puede pintar en una pantalla.

    Un operando de texto es **siempre** un nombre de columna; si no existe, falla. Tomarlo por
    una constante de texto daría una columna de basura sin avisar.
    """

    op: Literal["compute_column"] = "compute_column"
    target: str
    left: str | float
    operator: OperadorAritmetico
    right: str | float
    scale: float = Field(default=1.0, description="Multiplica el resultado; 100 para un %")
    round_to: int | None = None


class SortRowsOp(BaseModel):
    """Ordena las filas. Una tabla de informe se lee ordenada."""

    op: Literal["sort_rows"] = "sort_rows"
    by: list[str]
    ascending: bool = True


class UnpivotOp(BaseModel):
    """De ancho a largo: las cabeceras `ene feb mar` pasan a ser valores de una columna.

    El inverso de `pivot`, que ya existía. Las hojas institucionales son anchas —un mes o un año
    por columna— y un informe necesita largo para agrupar y para dibujar.

    `value_columns` vacío = todas las que no sean identificador.
    """

    op: Literal["unpivot"] = "unpivot"
    id_columns: list[str]
    value_columns: list[str] | None = None
    variable_name: str = "variable"
    value_name: str = "value"


Operation = Annotated[
    Union[
        FilterOp, AggregateOp, JoinOp, PivotOp, NormalizeOp, GroupByOp,
        DropColumnsOp, RenameColumnsOp, MergeColumnsOp, ReorderColumnsOp,
        FormatDatesOp, ReplaceValuesOp, NormalizeTextOp, FillNullsOp,
        RemoveDuplicatesOp, DropNullRowsOp,
        ToNumberOp, ComputeColumnOp, SortRowsOp, UnpivotOp,
    ],
    Field(discriminator="op"),
]

_OPERATION_LIST_ADAPTER: TypeAdapter[list[Operation]] = TypeAdapter(list[Operation])

#: El orden en que se le enseñan al modelo: primero limpiar, después calcular, después analizar
#: y por último remodelar. `to_number` abre la lista porque sin ella todo lo que viene después
#: opera sobre texto.
_MODELOS_DE_OPERACION = (
    ToNumberOp,
    DropColumnsOp, RenameColumnsOp, MergeColumnsOp, ReorderColumnsOp,
    FormatDatesOp, ReplaceValuesOp, NormalizeTextOp, FillNullsOp,
    RemoveDuplicatesOp, DropNullRowsOp,
    ComputeColumnOp,
    FilterOp, AggregateOp, GroupByOp, PivotOp, UnpivotOp, NormalizeOp, JoinOp,
    SortRowsOp,
)


def catalogo_de_operaciones() -> str:
    """El catálogo en una línea por operación, generado de los propios modelos.

    PRO.4 — el prompt del ETL enumeraba las operaciones a mano, y con dieciséis una lista a
    mano se queda corta en el primer cambio: el síntoma es un modelo que no usa la mitad del
    catálogo y nadie sabe por qué. Esto sale de los modelos, así que no puede divergir.
    """
    lineas: list[str] = []
    for modelo in _MODELOS_DE_OPERACION:
        campos: list[str] = []
        for nombre, campo in modelo.model_fields.items():
            if nombre == "op":
                continue
            campos.append(f'"{nombre}": {tipo_legible(campo.annotation)}')
        nombre_op = modelo.model_fields["op"].default
        lineas.append('  {"op": "%s"%s}' % (nombre_op, ", " + ", ".join(campos) if campos else ""))
    return "\n".join(lineas)


def parse_operations(payload: list[dict]) -> list[Operation]:
    """Valida y parsea una lista de operaciones desde JSON crudo.

    Útil para hidratar la salida del LLM y para tests/serialización.
    """
    return _OPERATION_LIST_ADAPTER.validate_python(payload)
