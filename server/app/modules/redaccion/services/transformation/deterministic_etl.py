"""DeterministicETLService — ejecuta operaciones declarativas sobre un DataFrame (9R.5.8).

Engine síncrono in-memory: las operaciones se aplican en orden, devolviendo
un DataFrame nuevo. JoinOp usa un resolver inyectado para localizar el otro
DataFrame (típicamente desde `WorkspaceState.block_outputs`).
"""
from __future__ import annotations

import re
from typing import Callable

import pandas as pd

from server.app.modules.redaccion.services.transformation.operations import (
    AggregateOp,
    DropColumnsOp,
    DropNullRowsOp,
    FillNullsOp,
    FilterOp,
    FormatDatesOp,
    GroupByOp,
    JoinOp,
    MergeColumnsOp,
    NormalizeOp,
    NormalizeTextOp,
    Operation,
    PivotOp,
    RemoveDuplicatesOp,
    RenameColumnsOp,
    ReorderColumnsOp,
    ReplaceValuesOp,
)


class UnknownOperationError(TypeError):
    pass


class ColumnaInexistenteError(KeyError):
    """Una operación nombra una columna que la tabla no tiene.

    PRO.4 — el legacy devolvía el DataFrame intacto (`return df`) cuando la columna no
    existía. En una interfaz donde ves el resultado al momento eso es cómodo; en un informe que
    se genera en segundo plano es un renombrado que se pierde y una tabla que sale sin tocar y
    sin decirlo. El nodo convierte esto en un bloque `failed` con su motivo, que es visible.
    """


def _a_snake_case(texto: str) -> str:
    """`Importe Total` → `importe_total`, `creditoInicial` → `credito_inicial`."""
    con_guiones = re.sub(r"[\s\-]+", "_", texto)
    separado = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", con_guiones)
    return separado.lower()


def _exigir_columnas(df: pd.DataFrame, columnas: list[str], operacion: str) -> None:
    faltan = [c for c in columnas if c not in df.columns]
    if faltan:
        raise ColumnaInexistenteError(
            f"{operacion}: la tabla no tiene {faltan}. Columnas disponibles: {list(df.columns)}"
        )


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
            # PRO.4 — limpieza, portada del legacy.
            elif isinstance(op, DropColumnsOp):
                _exigir_columnas(result, op.columns, "drop_columns")
                result = result.drop(columns=op.columns)
            elif isinstance(op, RenameColumnsOp):
                _exigir_columnas(result, list(op.mapping), "rename_columns")
                result = result.rename(columns=op.mapping)
            elif isinstance(op, MergeColumnsOp):
                result = self._merge_columns(result, op)
            elif isinstance(op, ReorderColumnsOp):
                _exigir_columnas(result, op.columns, "reorder_columns")
                resto = [c for c in result.columns if c not in op.columns]
                result = result[op.columns + resto]
            elif isinstance(op, FormatDatesOp):
                result = self._format_dates(result, op)
            elif isinstance(op, ReplaceValuesOp):
                _exigir_columnas(result, [op.column], "replace_values")
                result = result.copy()
                result[op.column] = result[op.column].replace(op.replacements)
            elif isinstance(op, NormalizeTextOp):
                result = self._normalize_text(result, op)
            elif isinstance(op, FillNullsOp):
                _exigir_columnas(result, op.columns, "fill_nulls")
                result = result.copy()
                result[op.columns] = result[op.columns].fillna(op.value)
            elif isinstance(op, RemoveDuplicatesOp):
                if op.subset:
                    _exigir_columnas(result, op.subset, "remove_duplicates")
                result = result.drop_duplicates(subset=op.subset, keep=op.keep)
            elif isinstance(op, DropNullRowsOp):
                if op.subset:
                    _exigir_columnas(result, op.subset, "drop_null_rows")
                result = result.dropna(subset=op.subset, how=op.how)
            else:
                raise UnknownOperationError(f"Unknown operation type: {type(op).__name__}")
        return result

    # ------------------------------------------------------------------
    # Limpieza (PRO.4)
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_columns(df: pd.DataFrame, op: MergeColumnsOp) -> pd.DataFrame:
        _exigir_columnas(df, op.source_columns, "merge_columns")
        valores = df[op.source_columns].apply(
            lambda fila: op.separator.join(fila.astype(str)), axis=1
        )
        if not op.drop_source:
            salida = df.copy()
            salida[op.target_column] = valores
            return salida

        # La posición de la primera columna fusionada se conserva: si la referencia acabara al
        # final de la tabla, habría que reordenar después en otra operación.
        posicion = min(list(df.columns).index(c) for c in op.source_columns)
        salida = df.drop(columns=op.source_columns)
        salida.insert(posicion, op.target_column, valores)
        return salida

    @staticmethod
    def _format_dates(df: pd.DataFrame, op: FormatDatesOp) -> pd.DataFrame:
        _exigir_columnas(df, [op.column], "format_dates")
        salida = df.copy()
        # `errors="coerce"`: lo que no se entiende como fecha queda vacío, y eso **se ve** en la
        # tabla del informe. El legacy dejaba la columna entera intacta y escribía un `print`,
        # así que una fecha sin convertir pasaba desapercibida.
        #
        # `dayfirst=True` en la detección automática: `01/03/2026` es ambiguo y pandas lo lee
        # como **3 de enero** (convención de EE. UU.). En un fichero de esta institución es el
        # 1 de marzo, y equivocarse ahí no da error: da un informe con las fechas cambiadas.
        # Con `source_format` explícito manda el formato, que es lo inequívoco.
        if op.source_format:
            fechas = pd.to_datetime(salida[op.column], format=op.source_format, errors="coerce")
        else:
            fechas = pd.to_datetime(salida[op.column], errors="coerce", dayfirst=True)
        formato = "%Y-%m-%d" if op.target_format.upper() == "ISO8601" else op.target_format
        salida[op.column] = fechas.dt.strftime(formato)
        return salida

    @staticmethod
    def _normalize_text(df: pd.DataFrame, op: NormalizeTextOp) -> pd.DataFrame:
        _exigir_columnas(df, op.columns, "normalize_text")
        salida = df.copy()
        for col in op.columns:
            texto = salida[col].astype(str)
            if op.mode == "upper":
                salida[col] = texto.str.upper()
            elif op.mode == "lower":
                salida[col] = texto.str.lower()
            elif op.mode == "title":
                salida[col] = texto.str.title()
            elif op.mode == "strip":
                salida[col] = texto.str.strip()
            elif op.mode == "snake_case":
                salida[col] = texto.map(_a_snake_case)
        return salida

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
