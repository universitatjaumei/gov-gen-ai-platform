"""ChartConfiguration — contrato Pydantic para gráficos deterministas (9R.5.7).

Migrado de client_app/app/models/chart_configuration.py.
Reducido a los 5 tipos del MVP; el resto se añade en iteraciones futuras.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChartConfiguration(BaseModel):
    """Configuración de un gráfico determinista. Reproducible y JSON-serializable."""

    chart_type: Literal["bar", "line", "pie", "scatter", "histogram"] = Field(
        default="bar", description="Tipo de gráfico"
    )

    # Mapeo de columnas
    x_column: str | None = Field(default=None, description="Columna para el eje X")
    y_column: str | None = Field(default=None, description="Columna para el eje Y")
    color_column: str | None = Field(default=None, description="Columna para color/hue")
    label_column: str | None = Field(default=None, description="Columna de etiquetas (pie)")
    value_column: str | None = Field(default=None, description="Columna de valores (pie)")

    # Agregación
    aggregation: Literal["sum", "mean", "count", "min", "max", "none"] = "none"

    # Estilo
    title: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    palette: str = "viridis"
    style: str = "whitegrid"
    size: tuple[float, float] = (10, 6)

    # Opciones de visualización
    show_legend: bool = True
    show_values: bool = False
    show_grid: bool = True
    bins: int | None = None

    # Salida
    output_format: Literal["png", "svg"] = "png"
