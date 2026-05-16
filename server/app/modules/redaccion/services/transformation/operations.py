"""Catálogo declarativo de operaciones ETL — 9R.5.8.

Discriminated union por el campo `op`. Cada subtipo añade los campos
necesarios para describir la operación; la ejecución vive en
`DeterministicETLService`.

Frente al legacy client_app/app/models/transform_operations.py, este
catálogo se orienta a análisis (filter / aggregate / join / pivot /
normalize / groupby) en lugar de limpieza, alineado con el uso típico
del módulo de redacción: agregar y resumir datos antes de redactar.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

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


Operation = Annotated[
    Union[FilterOp, AggregateOp, JoinOp, PivotOp, NormalizeOp, GroupByOp],
    Field(discriminator="op"),
]

_OPERATION_LIST_ADAPTER: TypeAdapter[list[Operation]] = TypeAdapter(list[Operation])


def parse_operations(payload: list[dict]) -> list[Operation]:
    """Valida y parsea una lista de operaciones desde JSON crudo.

    Útil para hidratar la salida del LLM y para tests/serialización.
    """
    return _OPERATION_LIST_ADAPTER.validate_python(payload)
