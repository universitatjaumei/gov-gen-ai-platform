"""GUI.4 — «x» significa el eje X, y el gráfico que se pide es el que sale.

Encontrado verificando GUI.3 con el modelo real: pidió un `barh` de porcentaje por concepto y
salió **un gráfico de barras verticales con 0, 1, 2, 3 en el eje** y las etiquetas cruzadas. Dos
defectos, y el primero es de diseño mío:

1. **PRO.8 hizo que `x_column` significara «la categoría»**, y el renderizador cruzaba los ejes
   en `barh`. El modelo —y cualquiera que rellene el contrato a mano— lee `x_axis` como «lo que
   va en el eje X», que es lo que dice el nombre y lo que dice su `x_label`. Así que el modelo
   cruzó las columnas y el renderizador las volvió a cruzar: dos cruces, ninguna.
2. **El formateador de cifras del eje pisaba las etiquetas de categoría.** Decidía qué eje es el
   numérico a partir del **tipo de gráfico**, así que en cuanto las columnas no seguían mi
   convención, escribía `0, 1, 2, 3` encima de los nombres. Ahora lo decide **por los datos**.

La convención queda: `x_column` es el eje X y `y_column` el eje Y, siempre. En `barh` la
categoría va en `y_column` porque las barras son horizontales. Nada se cruza por detrás.
"""
from __future__ import annotations

import pandas as pd
import pytest

from server.app.modules.redaccion.blocks.handlers import ChartHandler
from server.app.modules.redaccion.contracts.blocks import ChartBlockConfig
from server.app.modules.redaccion.services.charts.chart_configuration import ChartConfiguration
from server.app.modules.redaccion.services.charts.deterministic_chart_service import (
    DeterministicChartService,
)


@pytest.fixture
def ejecucion() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Concepto": ["Cap. 1 Personal", "Cap. 6 Inversiones", "Cap. 2 Bienes", "Cap. 4 Transf."],
            "Porcentaje Ejecucion": [85.56, 82.04, 75.2, 64.45],
        }
    )


def test_el_barh_que_pidio_el_modelo_sale_con_los_conceptos_no_con_el_indice(
    ejecucion: pd.DataFrame,
) -> None:
    """La configuración es la que devolvió `gemini-2.5-flash`, copiada literal."""
    cfg = ChartBlockConfig(
        chart_type="barh",
        x_axis="Porcentaje Ejecucion",
        y_axis="Concepto",
        x_label="Porcentaje de Ejecución (%)",
        y_label="Concepto Presupuestario",
        title="Porcentaje de Ejecución Presupuestaria por Concepto",
        show_values=True,
        sort="desc",
    )
    fig = DeterministicChartService().render_figure(
        ejecucion, ChartHandler._to_chart_config(cfg)
    )
    fig.canvas.draw()
    ax = fig.axes[0]

    etiquetas_y = [t.get_text() for t in ax.get_yticklabels()]
    assert "Cap. 1 Personal" in etiquetas_y, f"las categorías no están en el eje Y: {etiquetas_y}"
    # Y el eje de valores lleva cifras, no posiciones.
    etiquetas_x = [t.get_text() for t in ax.get_xticklabels()]
    assert etiquetas_x != ["0", "1", "2", "3"], "el eje de categorías se ha comido las etiquetas"


def test_las_etiquetas_de_eje_van_al_eje_que_nombran(ejecucion: pd.DataFrame) -> None:
    """`x_label` es la etiqueta del eje X. Si no, no se llamaría así."""
    fig = DeterministicChartService().render_figure(
        ejecucion,
        ChartConfiguration(
            chart_type="barh",
            x_column="Porcentaje Ejecucion",
            y_column="Concepto",
            x_label="Porcentaje (%)",
            y_label="Capítulo",
        ),
    )
    ax = fig.axes[0]
    assert ax.get_xlabel() == "Porcentaje (%)"
    assert ax.get_ylabel() == "Capítulo"


def test_el_orden_mira_la_columna_de_valores_no_la_de_categorias(
    ejecucion: pd.DataFrame,
) -> None:
    """Ordenar «de mayor a menor» ordena por el número, no alfabéticamente por el nombre."""
    fig = DeterministicChartService().render_figure(
        ejecucion,
        ChartConfiguration(
            chart_type="barh", x_column="Porcentaje Ejecucion", y_column="Concepto", sort="desc"
        ),
    )
    fig.canvas.draw()
    etiquetas = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert etiquetas[0] == "Cap. 1 Personal", etiquetas  # 85,56: el mayor


def test_un_bar_normal_sigue_teniendo_la_categoria_en_x(ejecucion: pd.DataFrame) -> None:
    """El cambio no puede romper el caso corriente: en `bar`, la categoría va en X."""
    fig = DeterministicChartService().render_figure(
        ejecucion,
        ChartConfiguration(
            chart_type="bar", x_column="Concepto", y_column="Porcentaje Ejecucion", sort="desc"
        ),
    )
    fig.canvas.draw()
    etiquetas_x = [t.get_text() for t in fig.axes[0].get_xticklabels()]
    assert etiquetas_x[0] == "Cap. 1 Personal", etiquetas_x


def test_las_cifras_encima_siguen_saliendo_en_un_barh(ejecucion: pd.DataFrame) -> None:
    fig = DeterministicChartService().render_figure(
        ejecucion,
        ChartConfiguration(
            chart_type="barh", x_column="Porcentaje Ejecucion", y_column="Concepto",
            show_values=True,
        ),
    )
    textos = [t.get_text() for t in fig.axes[0].texts]
    assert any("85,56" in t for t in textos), textos


def test_el_prompt_explica_donde_va_la_categoria_en_un_barh() -> None:
    """El modelo acertó por sentido común; que no tenga que adivinarlo."""
    from server.app.modules.redaccion.services.llm_spec_service import _campos_obligatorios

    texto = _campos_obligatorios()
    assert "barh" in texto
    assert "y_axis" in texto
