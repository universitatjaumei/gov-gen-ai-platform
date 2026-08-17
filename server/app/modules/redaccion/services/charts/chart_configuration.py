"""ChartConfiguration — contrato Pydantic para gráficos deterministas (9R.5.7).

Migrado de client_app/app/models/chart_configuration.py.

PRO.8 — el MVP se quedó en 5 tipos «y el resto en iteraciones futuras». La iteración futura
llegó cuando se midió el coste de que falten: pedir un gráfico que no está en la lista **genera
un script** (`translate_nl_to_config` llamaba directamente a `generate_script`), o sea modelo
+ auditoría + sandbox para lo que aquí es un parámetro. Seis de los diez tipos del legacy son
exactamente eso, un parámetro de lo que ya hacíamos.

`violin` y `pairplot` del legacy **no entran**: son gráficos de exploración estadística, y
`pairplot` devuelve un grid de ejes que no cabe en el `fig, ax` de este servicio.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.app.modules.redaccion.services.contrato_legible import campos_legibles

TipoDeGrafico = Literal[
    "bar",          # barras verticales
    "barh",         # las mismas, en horizontal (etiquetas largas)
    "bar_stacked",  # apiladas por `color_column`
    "line",
    "pie",
    "donut",        # la misma tarta con el centro hueco
    "scatter",
    "bubble",       # scatter con el tamaño del punto en `size_column`
    "histogram",
    "boxplot",      # dispersión por grupo
    "heatmap",      # matriz x × y con el valor en color: capítulo × año
]

OrdenDeCategorias = Literal["none", "asc", "desc"]


class ChartConfiguration(BaseModel):
    """Configuración de un gráfico determinista. Reproducible y JSON-serializable."""

    chart_type: TipoDeGrafico = Field(default="bar", description="Tipo de gráfico")

    # Mapeo de columnas
    x_column: str | None = Field(default=None, description="Columna para el eje X")
    y_column: str | None = Field(default=None, description="Columna para el eje Y")
    color_column: str | None = Field(default=None, description="Columna para color/hue")
    label_column: str | None = Field(default=None, description="Columna de etiquetas (pie)")
    value_column: str | None = Field(default=None, description="Columna de valores (pie, heatmap)")
    size_column: str | None = Field(
        default=None, description="Columna que dimensiona el punto (bubble)"
    )

    # Agregación y orden
    aggregation: Literal["sum", "mean", "count", "min", "max", "none"] = "none"
    sort: OrdenDeCategorias = Field(
        default="none", description="Orden de las categorías por su valor"
    )

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
    value_format: str = Field(
        default="{:,.2f}", description="Formato de las cifras cuando show_values=True"
    )
    number_format: Literal["es", "en"] = Field(
        default="es",
        description="Convención de separadores de las cifras del gráfico: es → 128.340,55",
    )
    donut_ratio: float = Field(
        default=0.45, gt=0.0, lt=1.0, description="Radio del hueco central del donut"
    )

    # Salida
    output_format: Literal["png", "svg"] = "png"


def catalogo_de_configuracion() -> str:
    """La configuración tal y como se le enseña al modelo, generada del propio contrato.

    Mismo criterio que `catalogo_de_operaciones` en PRO.4: si el prompt enumera los tipos y los
    campos a mano, en el primer cambio el modelo pedirá un gráfico que el renderizador no sabe
    dibujar, o dejará de usar la mitad del catálogo.
    """
    return "\n".join(campos_legibles(ChartConfiguration, omitir=("output_format",)))
