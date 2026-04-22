"""
Chart Configuration Models for Deterministic Graphics.

Defines Pydantic models for chart configuration without AI intervention.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional, Tuple


class ChartConfiguration(BaseModel):
    """Configuration for deterministic chart generation."""

    # Chart type
    chart_type: Literal[
        'bar', 'barh', 'bar_stacked', 'bar_grouped',
        'line', 'line_multi',
        'pie', 'donut',
        'scatter', 'bubble',
        'histogram', 'boxplot', 'violin',
        'heatmap', 'pairplot'
    ] = Field(..., description="Type of chart to generate")

    # Data mapping
    x_column: Optional[str] = Field(default=None, description="Column for X axis")
    y_column: Optional[str] = Field(default=None, description="Column for Y axis")
    color_column: Optional[str] = Field(default=None, description="Column for color grouping")
    size_column: Optional[str] = Field(default=None, description="Column for size (bubble charts)")
    y_columns: Optional[List[str]] = Field(default=None, description="Multiple Y columns for multi-series")
    label_column: Optional[str] = Field(default=None, description="Column for labels (pie charts)")
    value_column: Optional[str] = Field(default=None, description="Column for values (pie charts)")

    # Aggregation
    aggregation: Literal['sum', 'mean', 'count', 'min', 'max', 'median', 'none'] = Field(
        default='none', description="Aggregation function for Y values"
    )

    # Styling
    title: Optional[str] = Field(default=None, description="Chart title")
    x_label: Optional[str] = Field(default=None, description="X axis label")
    y_label: Optional[str] = Field(default=None, description="Y axis label")
    palette: str = Field(default='viridis', description="Color palette name")
    style: str = Field(default='whitegrid', description="Seaborn style")
    size: Tuple[float, float] = Field(default=(10, 6), description="Figure size in inches (width, height)")

    # Display options
    show_legend: bool = Field(default=True, description="Show legend")
    show_values: bool = Field(default=False, description="Show values on bars/points")
    show_grid: bool = Field(default=True, description="Show grid lines")
    orientation: Literal['vertical', 'horizontal'] = Field(default='vertical', description="Chart orientation")

    # Histogram specific
    bins: Optional[int] = Field(default=None, description="Number of bins for histogram")

    # Pie specific
    explode_segment: Optional[str] = Field(default=None, description="Segment to explode in pie chart")
    donut_ratio: float = Field(default=0.3, description="Inner radius ratio for donut charts")

    # Advanced
    sort_values: bool = Field(default=False, description="Sort values before plotting")
    sort_ascending: bool = Field(default=True, description="Sort in ascending order")
    limit_categories: Optional[int] = Field(default=None, description="Limit number of categories shown")
    top_n: Optional[int] = Field(default=None, description="Show only top N values")


# Chart type metadata for UI
CHART_TYPES = {
    'bar': {
        'label': 'Barras Verticales',
        'icon': 'bar_chart',
        'description': 'Comparar valores entre categorias',
        'required_fields': ['x_column', 'y_column'],
        'optional_fields': ['color_column', 'aggregation']
    },
    'barh': {
        'label': 'Barras Horizontales',
        'icon': 'align_horizontal_left',
        'description': 'Ideal para nombres largos',
        'required_fields': ['x_column', 'y_column'],
        'optional_fields': ['color_column', 'aggregation']
    },
    'bar_stacked': {
        'label': 'Barras Apiladas',
        'icon': 'stacked_bar_chart',
        'description': 'Mostrar composicion de totales',
        'required_fields': ['x_column', 'y_column', 'color_column'],
        'optional_fields': ['aggregation']
    },
    'bar_grouped': {
        'label': 'Barras Agrupadas',
        'icon': 'view_column',
        'description': 'Comparar grupos lado a lado',
        'required_fields': ['x_column', 'y_column', 'color_column'],
        'optional_fields': ['aggregation']
    },
    'line': {
        'label': 'Linea Simple',
        'icon': 'show_chart',
        'description': 'Tendencias en el tiempo',
        'required_fields': ['x_column', 'y_column'],
        'optional_fields': ['color_column']
    },
    'line_multi': {
        'label': 'Lineas Multiples',
        'icon': 'multiline_chart',
        'description': 'Comparar varias series',
        'required_fields': ['x_column', 'y_columns'],
        'optional_fields': []
    },
    'pie': {
        'label': 'Pastel',
        'icon': 'pie_chart',
        'description': 'Proporcion del total',
        'required_fields': ['label_column', 'value_column'],
        'optional_fields': ['explode_segment']
    },
    'donut': {
        'label': 'Dona',
        'icon': 'donut_large',
        'description': 'Pastel con espacio central',
        'required_fields': ['label_column', 'value_column'],
        'optional_fields': ['donut_ratio']
    },
    'scatter': {
        'label': 'Dispersion',
        'icon': 'scatter_plot',
        'description': 'Correlacion entre variables',
        'required_fields': ['x_column', 'y_column'],
        'optional_fields': ['color_column']
    },
    'bubble': {
        'label': 'Burbujas',
        'icon': 'bubble_chart',
        'description': 'Tres dimensiones de datos',
        'required_fields': ['x_column', 'y_column', 'size_column'],
        'optional_fields': ['color_column']
    },
    'histogram': {
        'label': 'Histograma',
        'icon': 'equalizer',
        'description': 'Distribucion de frecuencias',
        'required_fields': ['x_column'],
        'optional_fields': ['bins', 'color_column']
    },
    'boxplot': {
        'label': 'Box Plot',
        'icon': 'candlestick_chart',
        'description': 'Estadisticas de distribucion',
        'required_fields': ['y_column'],
        'optional_fields': ['x_column', 'color_column']
    },
    'violin': {
        'label': 'Violin',
        'icon': 'graphic_eq',
        'description': 'Distribucion con densidad',
        'required_fields': ['y_column'],
        'optional_fields': ['x_column', 'color_column']
    },
    'heatmap': {
        'label': 'Mapa de Calor',
        'icon': 'grid_on',
        'description': 'Matriz de correlacion',
        'required_fields': [],
        'optional_fields': []
    }
}

# Color palettes available
COLOR_PALETTES = {
    'viridis': 'Viridis (secuencial)',
    'plasma': 'Plasma (secuencial)',
    'inferno': 'Inferno (secuencial)',
    'magma': 'Magma (secuencial)',
    'cividis': 'Cividis (daltónico)',
    'Blues': 'Azules',
    'Greens': 'Verdes',
    'Oranges': 'Naranjas',
    'Reds': 'Rojos',
    'Purples': 'Purpuras',
    'Set1': 'Set 1 (categorico)',
    'Set2': 'Set 2 (categorico)',
    'Set3': 'Set 3 (categorico)',
    'Paired': 'Paired (categorico)',
    'tab10': 'Tab 10 (categorico)',
    'tab20': 'Tab 20 (categorico)',
    'coolwarm': 'Frio-Calido (divergente)',
    'RdYlGn': 'Rojo-Amarillo-Verde',
    'RdBu': 'Rojo-Azul (divergente)'
}

# Seaborn styles
CHART_STYLES = {
    'whitegrid': 'Fondo blanco con cuadricula',
    'darkgrid': 'Fondo gris con cuadricula',
    'white': 'Fondo blanco limpio',
    'dark': 'Fondo oscuro',
    'ticks': 'Solo marcas en ejes'
}
