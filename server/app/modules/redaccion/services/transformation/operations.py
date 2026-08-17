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

import types
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, Field, TypeAdapter


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


Operation = Annotated[
    Union[
        FilterOp, AggregateOp, JoinOp, PivotOp, NormalizeOp, GroupByOp,
        DropColumnsOp, RenameColumnsOp, MergeColumnsOp, ReorderColumnsOp,
        FormatDatesOp, ReplaceValuesOp, NormalizeTextOp, FillNullsOp,
        RemoveDuplicatesOp, DropNullRowsOp,
    ],
    Field(discriminator="op"),
]

_OPERATION_LIST_ADAPTER: TypeAdapter[list[Operation]] = TypeAdapter(list[Operation])

#: El orden en que se le enseñan al modelo: primero limpiar, después analizar.
_MODELOS_DE_OPERACION = (
    DropColumnsOp, RenameColumnsOp, MergeColumnsOp, ReorderColumnsOp,
    FormatDatesOp, ReplaceValuesOp, NormalizeTextOp, FillNullsOp,
    RemoveDuplicatesOp, DropNullRowsOp,
    FilterOp, AggregateOp, GroupByOp, PivotOp, NormalizeOp, JoinOp,
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
            campos.append(f'"{nombre}": {_tipo_legible(campo.annotation)}')
        nombre_op = modelo.model_fields["op"].default
        lineas.append('  {"op": "%s"%s}' % (nombre_op, ", " + ", ".join(campos) if campos else ""))
    return "\n".join(lineas)


def _tipo_legible(anotacion: Any) -> str:
    """Los valores admitidos si son cerrados, y el nombre del tipo si no."""
    origen = get_origin(anotacion)
    if origen is Literal:
        return "|".join(str(v) for v in get_args(anotacion))
    # `Optional[x]` y `x | None` son la misma cosa con dos orígenes distintos: sin las dos, el
    # catálogo le enseña al modelo `list[str] | None` en vez de `[str]`.
    if origen is Union or origen is types.UnionType:
        partes = [a for a in get_args(anotacion) if a is not type(None)]
        return "|".join(_tipo_legible(p) for p in partes)
    if origen in (list, set):
        interno = get_args(anotacion)
        return f"[{_tipo_legible(interno[0])}]" if interno else "[]"
    if origen is dict:
        return "{...}"
    return getattr(anotacion, "__name__", str(anotacion))


def parse_operations(payload: list[dict]) -> list[Operation]:
    """Valida y parsea una lista de operaciones desde JSON crudo.

    Útil para hidratar la salida del LLM y para tests/serialización.
    """
    return _OPERATION_LIST_ADAPTER.validate_python(payload)
