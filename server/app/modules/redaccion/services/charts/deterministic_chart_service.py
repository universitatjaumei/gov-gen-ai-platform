"""DeterministicChartService — generación de gráficos sin IA (9R.5.7).

Migrado de client_app/app/services/deterministic_graphics_service.py.
Reducido a 5 tipos MVP (bar, line, pie, scatter, histogram).
In-process con matplotlib Agg: sin subprocess, sin LLM.
"""
from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")  # backend no interactivo; debe llamarse antes de pyplot
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from server.app.modules.redaccion.services.charts.chart_configuration import ChartConfiguration


class DeterministicChartService:
    """Genera gráficos a partir de configuración explícita del usuario."""

    def render(self, df: pd.DataFrame, config: ChartConfiguration) -> bytes:
        """Renderiza el gráfico y devuelve bytes PNG o SVG.

        Síncrono: CPU-bound, sin I/O externo.
        """
        sns.set_style(config.style)
        fig, ax = plt.subplots(figsize=config.size)

        plot_df = self._prepare_data(df, config)

        if config.chart_type == "bar":
            self._render_bar(plot_df, ax, config)
        elif config.chart_type == "line":
            self._render_line(plot_df, ax, config)
        elif config.chart_type == "pie":
            self._render_pie(plot_df, ax, config)
        elif config.chart_type == "scatter":
            self._render_scatter(plot_df, ax, config)
        elif config.chart_type == "histogram":
            self._render_histogram(plot_df, ax, config)

        self._apply_styling(fig, ax, config)
        return self._to_bytes(fig, config.output_format)

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------

    def _prepare_data(self, df: pd.DataFrame, config: ChartConfiguration) -> pd.DataFrame:
        if config.aggregation == "none":
            return df.copy()
        group_cols = [c for c in [config.x_column, config.color_column] if c and c in df.columns]
        value_col = config.y_column or config.value_column
        if not group_cols or not value_col or value_col not in df.columns:
            return df.copy()
        agg_map = {"sum": "sum", "mean": "mean", "count": "count", "min": "min", "max": "max"}
        func = agg_map.get(config.aggregation, "sum")
        return df.groupby(group_cols, as_index=False).agg({value_col: func})

    # ------------------------------------------------------------------
    # Chart renderers
    # ------------------------------------------------------------------

    def _render_bar(self, df: pd.DataFrame, ax, config: ChartConfiguration) -> None:
        if config.color_column and config.color_column in df.columns:
            sns.barplot(
                data=df, x=config.x_column, y=config.y_column,
                hue=config.color_column, palette=config.palette, ax=ax,
            )
        else:
            color = sns.color_palette(config.palette)[0]
            sns.barplot(data=df, x=config.x_column, y=config.y_column, color=color, ax=ax)

    def _render_line(self, df: pd.DataFrame, ax, config: ChartConfiguration) -> None:
        if config.color_column and config.color_column in df.columns:
            sns.lineplot(
                data=df, x=config.x_column, y=config.y_column,
                hue=config.color_column, palette=config.palette, marker="o", ax=ax,
            )
        else:
            sns.lineplot(data=df, x=config.x_column, y=config.y_column, marker="o", ax=ax)

    def _render_pie(self, df: pd.DataFrame, ax, config: ChartConfiguration) -> None:
        label_col = config.label_column or config.x_column
        value_col = config.value_column or config.y_column
        if not label_col or not value_col:
            ax.text(0.5, 0.5, "Pie: faltan label_column/value_column", ha="center", va="center")
            return
        labels = df[label_col].tolist() if label_col in df.columns else []
        values = df[value_col].tolist() if value_col in df.columns else []
        colors = sns.color_palette(config.palette, len(labels))
        ax.pie(values, labels=labels, autopct="%1.1f%%", colors=colors, startangle=90)
        ax.axis("equal")

    def _render_scatter(self, df: pd.DataFrame, ax, config: ChartConfiguration) -> None:
        if config.color_column and config.color_column in df.columns:
            sns.scatterplot(
                data=df, x=config.x_column, y=config.y_column,
                hue=config.color_column, palette=config.palette, ax=ax, s=60,
            )
        else:
            sns.scatterplot(data=df, x=config.x_column, y=config.y_column, ax=ax, s=60)

    def _render_histogram(self, df: pd.DataFrame, ax, config: ChartConfiguration) -> None:
        bins: int | str = config.bins or "auto"
        if config.color_column and config.color_column in df.columns:
            sns.histplot(
                data=df, x=config.x_column, hue=config.color_column,
                bins=bins, palette=config.palette, ax=ax, alpha=0.7,
            )
        else:
            color = sns.color_palette(config.palette)[0]
            sns.histplot(data=df, x=config.x_column, bins=bins, ax=ax, color=color)

    # ------------------------------------------------------------------
    # Styling / output
    # ------------------------------------------------------------------

    def _apply_styling(self, fig, ax, config: ChartConfiguration) -> None:
        if config.title:
            ax.set_title(config.title, fontsize=14, fontweight="bold", pad=15)
        if config.x_label:
            ax.set_xlabel(config.x_label)
        elif config.x_column:
            ax.set_xlabel(config.x_column)
        if config.y_label:
            ax.set_ylabel(config.y_label)
        elif config.y_column:
            ax.set_ylabel(config.y_column)
        if not config.show_grid:
            ax.grid(False)
        if not config.show_legend:
            legend = ax.get_legend()
            if legend:
                legend.remove()
        plt.tight_layout()

    def _to_bytes(self, fig, output_format: str) -> bytes:
        buf = io.BytesIO()
        fig.savefig(buf, format=output_format, dpi=150, bbox_inches="tight", facecolor="white")
        buf.seek(0)
        plt.close(fig)
        return buf.read()
