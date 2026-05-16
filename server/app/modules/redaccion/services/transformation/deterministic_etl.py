"""DeterministicETLService — ejecuta operaciones declarativas sobre un DataFrame (9R.5.8).

Engine síncrono in-memory: las operaciones se aplican en orden, devolviendo
un DataFrame nuevo. JoinOp usa un resolver inyectado para localizar el otro
DataFrame (típicamente desde `WorkspaceState.block_outputs`).
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from server.app.modules.redaccion.services.transformation.operations import (
    AggregateOp,
    FilterOp,
    GroupByOp,
    JoinOp,
    NormalizeOp,
    Operation,
    PivotOp,
)


class UnknownOperationError(TypeError):
    pass


JoinableResolver = Callable[[str], pd.DataFrame]


class DeterministicETLService:
    """Aplica una lista de Operation a un DataFrame, en orden."""

    def __init__(self, joinable_resolver: JoinableResolver | None = None) -> None:
        self._joinable_resolver = joinable_resolver

    def execute(self, df: pd.DataFrame, operations: list[Operation]) -> pd.DataFrame:
        result = df.copy()
        for op in operations:
            if isinstance(op, FilterOp):
                result = self._filter(result, op)
            elif isinstance(op, AggregateOp):
                result = self._aggregate(result, op)
            elif isinstance(op, JoinOp):
                result = self._join(result, op)
            elif isinstance(op, PivotOp):
                result = self._pivot(result, op)
            elif isinstance(op, NormalizeOp):
                result = self._normalize(result, op)
            elif isinstance(op, GroupByOp):
                result = self._groupby(result, op)
            else:
                raise UnknownOperationError(f"Unknown operation type: {type(op).__name__}")
        return result

    # ------------------------------------------------------------------
    # Operadores
    # ------------------------------------------------------------------

    @staticmethod
    def _filter(df: pd.DataFrame, op: FilterOp) -> pd.DataFrame:
        if op.col not in df.columns:
            return df
        series = df[op.col]
        comp = op.comparator
        if comp == "==":
            mask = series == op.value
        elif comp == "!=":
            mask = series != op.value
        elif comp == ">":
            mask = series > op.value
        elif comp == "<":
            mask = series < op.value
        elif comp == ">=":
            mask = series >= op.value
        elif comp == "<=":
            mask = series <= op.value
        elif comp == "contains":
            mask = series.astype(str).str.contains(str(op.value), na=False)
        elif comp == "not_contains":
            mask = ~series.astype(str).str.contains(str(op.value), na=False)
        elif comp == "in":
            values = op.value if isinstance(op.value, (list, tuple, set)) else [op.value]
            mask = series.isin(values)
        elif comp == "isnull":
            mask = series.isnull()
        elif comp == "notnull":
            mask = series.notnull()
        else:  # pragma: no cover — schema lo impide
            raise ValueError(f"Unsupported comparator: {comp!r}")
        return df.loc[mask].reset_index(drop=True)

    @staticmethod
    def _aggregate(df: pd.DataFrame, op: AggregateOp) -> pd.DataFrame:
        if op.col not in df.columns:
            return pd.DataFrame({f"{op.col}_{op.function}": []})
        value = getattr(df[op.col], op.function)()
        return pd.DataFrame({f"{op.col}_{op.function}": [value]})

    def _join(self, df: pd.DataFrame, op: JoinOp) -> pd.DataFrame:
        if self._joinable_resolver is None:
            raise ValueError(
                f"JoinOp on {op.other_block_ref!r} requires a joinable_resolver, "
                "but none was injected into DeterministicETLService."
            )
        other = self._joinable_resolver(op.other_block_ref)
        return df.merge(other, on=op.on, how=op.how)

    @staticmethod
    def _pivot(df: pd.DataFrame, op: PivotOp) -> pd.DataFrame:
        pivoted = pd.pivot_table(
            df,
            index=op.index,
            columns=op.columns,
            values=op.values,
            aggfunc=op.aggfunc,
            fill_value=0,
        )
        pivoted = pivoted.reset_index()
        pivoted.columns.name = None
        pivoted.columns = [str(c) for c in pivoted.columns]
        return pivoted

    @staticmethod
    def _normalize(df: pd.DataFrame, op: NormalizeOp) -> pd.DataFrame:
        result = df.copy()
        for col in op.cols:
            if col not in result.columns:
                continue
            series = result[col].astype(float)
            if op.method == "min_max":
                rng = series.max() - series.min()
                if rng == 0:
                    result[col] = 0.0
                else:
                    result[col] = (series - series.min()) / rng
            else:  # z_score
                std = series.std(ddof=0)
                if std == 0:
                    result[col] = 0.0
                else:
                    result[col] = (series - series.mean()) / std
        return result

    @staticmethod
    def _groupby(df: pd.DataFrame, op: GroupByOp) -> pd.DataFrame:
        return df.groupby(op.cols, as_index=False).agg(op.agg_dict)
