"""Charts module — 9R.5.7.

Proporciona dos modos de generación de gráficos:
  - Determinista: usuario configura tipo + ejes → DeterministicChartService
  - IA: prompt NL → script matplotlib → sandbox → ChartRenderer
"""
from server.app.modules.redaccion.services.charts.chart_configuration import ChartConfiguration
from server.app.modules.redaccion.services.charts.deterministic_chart_service import DeterministicChartService
from server.app.modules.redaccion.services.charts.chart_factory import ChartFactory, ChartScript
from server.app.modules.redaccion.services.charts.chart_renderer import render_chart_from_script, ChartRenderError

__all__ = [
    "ChartConfiguration",
    "DeterministicChartService",
    "ChartFactory",
    "ChartScript",
    "render_chart_from_script",
    "ChartRenderError",
]
