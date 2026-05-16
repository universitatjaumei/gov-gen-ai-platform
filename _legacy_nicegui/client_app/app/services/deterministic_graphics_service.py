"""
Deterministic Graphics Service - Generates charts without AI.

This service handles deterministic chart generation using matplotlib and seaborn
based on user configuration, without requiring AI-generated code.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import io
from typing import Optional, List, Tuple
from client_app.app.models.chart_configuration import ChartConfiguration


class DeterministicGraphicsService:
    """Generates deterministic visualizations without AI intervention."""

    def __init__(self):
        # Set default style
        plt.style.use('seaborn-v0_8-whitegrid')

    async def generate_chart(
        self,
        df: pd.DataFrame,
        config: ChartConfiguration
    ) -> bytes:
        """
        Generate a chart based on deterministic configuration.

        Args:
            df: DataFrame with the data
            config: Chart configuration

        Returns:
            PNG image bytes
        """
        # Apply seaborn style
        sns.set_style(config.style)

        # Create figure
        fig, ax = plt.subplots(figsize=config.size)

        # Prepare data if aggregation is needed
        plot_df = self._prepare_data(df, config)

        # Render based on chart type
        if config.chart_type == 'bar':
            self._render_bar_chart(plot_df, ax, config)
        elif config.chart_type == 'barh':
            self._render_barh_chart(plot_df, ax, config)
        elif config.chart_type == 'bar_stacked':
            self._render_bar_stacked(plot_df, ax, config)
        elif config.chart_type == 'bar_grouped':
            self._render_bar_grouped(plot_df, ax, config)
        elif config.chart_type == 'line':
            self._render_line_chart(plot_df, ax, config)
        elif config.chart_type == 'line_multi':
            self._render_line_multi(plot_df, ax, config)
        elif config.chart_type == 'pie':
            self._render_pie_chart(plot_df, ax, config)
        elif config.chart_type == 'donut':
            self._render_donut_chart(plot_df, ax, config)
        elif config.chart_type == 'scatter':
            self._render_scatter_chart(plot_df, ax, config)
        elif config.chart_type == 'bubble':
            self._render_bubble_chart(plot_df, ax, config)
        elif config.chart_type == 'histogram':
            self._render_histogram(plot_df, ax, config)
        elif config.chart_type == 'boxplot':
            self._render_boxplot(plot_df, ax, config)
        elif config.chart_type == 'violin':
            self._render_violin(plot_df, ax, config)
        elif config.chart_type == 'heatmap':
            self._render_heatmap(plot_df, ax, config)
        else:
            raise ValueError(f"Unknown chart type: {config.chart_type}")

        # Apply common styling
        self._apply_styling(fig, ax, config)

        # Convert to bytes
        return self._figure_to_bytes(fig)

    def _prepare_data(self, df: pd.DataFrame, config: ChartConfiguration) -> pd.DataFrame:
        """Prepare data with aggregation if needed."""
        if config.aggregation == 'none':
            result = df.copy()
        else:
            # Determine groupby columns
            group_cols = []
            if config.x_column and config.x_column in df.columns:
                group_cols.append(config.x_column)
            if config.color_column and config.color_column in df.columns:
                group_cols.append(config.color_column)
            if config.label_column and config.label_column in df.columns:
                group_cols.append(config.label_column)

            if not group_cols:
                return df.copy()

            # Determine value column
            value_col = config.y_column or config.value_column
            if not value_col or value_col not in df.columns:
                return df.copy()

            # Apply aggregation
            agg_func = {
                'sum': 'sum',
                'mean': 'mean',
                'count': 'count',
                'min': 'min',
                'max': 'max',
                'median': 'median'
            }.get(config.aggregation, 'sum')

            result = df.groupby(group_cols, as_index=False).agg({value_col: agg_func})

        # Sort if requested
        if config.sort_values and config.y_column:
            result = result.sort_values(
                config.y_column,
                ascending=config.sort_ascending
            )

        # Limit categories if requested
        if config.limit_categories:
            result = result.head(config.limit_categories)

        if config.top_n:
            if config.y_column:
                result = result.nlargest(config.top_n, config.y_column)

        return result

    def _render_bar_chart(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render vertical bar chart."""
        if config.color_column and config.color_column in df.columns:
            sns.barplot(
                data=df,
                x=config.x_column,
                y=config.y_column,
                hue=config.color_column,
                palette=config.palette,
                ax=ax
            )
        else:
            # Use single color from palette when no hue (avoids FutureWarning)
            color = sns.color_palette(config.palette)[0]
            sns.barplot(
                data=df,
                x=config.x_column,
                y=config.y_column,
                color=color,
                ax=ax
            )

        if config.show_values:
            self._add_bar_values(ax, config.orientation == 'horizontal')

    def _render_barh_chart(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render horizontal bar chart."""
        if config.color_column and config.color_column in df.columns:
            sns.barplot(
                data=df,
                y=config.x_column,  # Swap for horizontal
                x=config.y_column,
                hue=config.color_column,
                palette=config.palette,
                orient='h',
                ax=ax
            )
        else:
            # Use single color from palette when no hue (avoids FutureWarning)
            color = sns.color_palette(config.palette)[0]
            sns.barplot(
                data=df,
                y=config.x_column,
                x=config.y_column,
                color=color,
                orient='h',
                ax=ax
            )

        if config.show_values:
            self._add_bar_values(ax, horizontal=True)

    def _render_bar_stacked(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render stacked bar chart."""
        if not config.color_column:
            return self._render_bar_chart(df, ax, config)

        # Pivot for stacked
        pivot_df = df.pivot_table(
            index=config.x_column,
            columns=config.color_column,
            values=config.y_column,
            aggfunc='sum'
        ).fillna(0)

        pivot_df.plot(
            kind='bar',
            stacked=True,
            ax=ax,
            colormap=config.palette
        )

    def _render_bar_grouped(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render grouped bar chart."""
        if not config.color_column:
            return self._render_bar_chart(df, ax, config)

        sns.barplot(
            data=df,
            x=config.x_column,
            y=config.y_column,
            hue=config.color_column,
            palette=config.palette,
            ax=ax
        )

    def _render_line_chart(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render line chart."""
        if config.color_column and config.color_column in df.columns:
            sns.lineplot(
                data=df,
                x=config.x_column,
                y=config.y_column,
                hue=config.color_column,
                palette=config.palette,
                marker='o',
                ax=ax
            )
        else:
            sns.lineplot(
                data=df,
                x=config.x_column,
                y=config.y_column,
                marker='o',
                ax=ax
            )

    def _render_line_multi(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render multi-line chart."""
        if not config.y_columns:
            return self._render_line_chart(df, ax, config)

        colors = sns.color_palette(config.palette, len(config.y_columns))

        for i, col in enumerate(config.y_columns):
            if col in df.columns:
                ax.plot(
                    df[config.x_column],
                    df[col],
                    marker='o',
                    label=col,
                    color=colors[i]
                )

        ax.legend()

    def _render_pie_chart(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render pie chart."""
        labels = df[config.label_column].tolist()
        values = df[config.value_column].tolist()

        # Handle explode
        explode = None
        if config.explode_segment and config.explode_segment in labels:
            explode = [0.1 if label == config.explode_segment else 0 for label in labels]

        colors = sns.color_palette(config.palette, len(labels))

        ax.pie(
            values,
            labels=labels,
            explode=explode,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )
        ax.axis('equal')

    def _render_donut_chart(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render donut chart."""
        labels = df[config.label_column].tolist()
        values = df[config.value_column].tolist()

        colors = sns.color_palette(config.palette, len(labels))

        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            pctdistance=0.75
        )

        # Add center circle for donut effect
        centre_circle = plt.Circle((0, 0), config.donut_ratio, fc='white')
        ax.add_artist(centre_circle)
        ax.axis('equal')

    def _render_scatter_chart(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render scatter plot."""
        if config.color_column and config.color_column in df.columns:
            sns.scatterplot(
                data=df,
                x=config.x_column,
                y=config.y_column,
                hue=config.color_column,
                palette=config.palette,
                ax=ax,
                s=60
            )
        else:
            sns.scatterplot(
                data=df,
                x=config.x_column,
                y=config.y_column,
                ax=ax,
                s=60
            )

    def _render_bubble_chart(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render bubble chart (scatter with size)."""
        sizes = df[config.size_column] if config.size_column in df.columns else 60

        # Normalize sizes
        if isinstance(sizes, pd.Series):
            sizes = (sizes - sizes.min()) / (sizes.max() - sizes.min()) * 500 + 50

        if config.color_column and config.color_column in df.columns:
            sns.scatterplot(
                data=df,
                x=config.x_column,
                y=config.y_column,
                hue=config.color_column,
                size=config.size_column,
                sizes=(50, 500),
                palette=config.palette,
                ax=ax
            )
        else:
            ax.scatter(
                df[config.x_column],
                df[config.y_column],
                s=sizes,
                alpha=0.6
            )

    def _render_histogram(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render histogram."""
        bins = config.bins or 'auto'

        if config.color_column and config.color_column in df.columns:
            sns.histplot(
                data=df,
                x=config.x_column,
                hue=config.color_column,
                bins=bins,
                palette=config.palette,
                ax=ax,
                alpha=0.7
            )
        else:
            sns.histplot(
                data=df,
                x=config.x_column,
                bins=bins,
                ax=ax,
                color=sns.color_palette(config.palette)[0]
            )

    def _render_boxplot(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render box plot."""
        has_hue = config.color_column and config.color_column in df.columns

        if config.x_column and config.x_column in df.columns:
            if has_hue:
                sns.boxplot(
                    data=df,
                    x=config.x_column,
                    y=config.y_column,
                    hue=config.color_column,
                    palette=config.palette,
                    ax=ax
                )
            else:
                color = sns.color_palette(config.palette)[0]
                sns.boxplot(
                    data=df,
                    x=config.x_column,
                    y=config.y_column,
                    color=color,
                    ax=ax
                )
        else:
            color = sns.color_palette(config.palette)[0]
            sns.boxplot(
                data=df,
                y=config.y_column,
                color=color,
                ax=ax
            )

    def _render_violin(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render violin plot."""
        has_hue = config.color_column and config.color_column in df.columns

        if config.x_column and config.x_column in df.columns:
            if has_hue:
                sns.violinplot(
                    data=df,
                    x=config.x_column,
                    y=config.y_column,
                    hue=config.color_column,
                    palette=config.palette,
                    ax=ax
                )
            else:
                color = sns.color_palette(config.palette)[0]
                sns.violinplot(
                    data=df,
                    x=config.x_column,
                    y=config.y_column,
                    color=color,
                    ax=ax
                )
        else:
            color = sns.color_palette(config.palette)[0]
            sns.violinplot(
                data=df,
                y=config.y_column,
                color=color,
                ax=ax
            )

    def _render_heatmap(self, df: pd.DataFrame, ax, config: ChartConfiguration):
        """Render correlation heatmap."""
        # Select only numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        corr_matrix = numeric_df.corr()

        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt='.2f',
            cmap=config.palette,
            ax=ax,
            square=True,
            linewidths=0.5
        )

    def _apply_styling(self, fig, ax, config: ChartConfiguration):
        """Apply common styling to the chart."""
        if config.title:
            ax.set_title(config.title, fontsize=14, fontweight='bold', pad=15)

        if config.x_label:
            ax.set_xlabel(config.x_label, fontsize=11)
        elif config.x_column:
            ax.set_xlabel(config.x_column, fontsize=11)

        if config.y_label:
            ax.set_ylabel(config.y_label, fontsize=11)
        elif config.y_column:
            ax.set_ylabel(config.y_column, fontsize=11)

        if not config.show_grid:
            ax.grid(False)

        if not config.show_legend:
            legend = ax.get_legend()
            if legend:
                legend.remove()

        # Rotate x labels if many categories
        try:
            if len(ax.get_xticklabels()) > 6:
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        except:
            pass

        plt.tight_layout()

    def _add_bar_values(self, ax, horizontal: bool = False):
        """Add value labels to bars."""
        for container in ax.containers:
            if horizontal:
                ax.bar_label(container, fmt='%.1f', padding=3)
            else:
                ax.bar_label(container, fmt='%.1f', padding=3)

    def _figure_to_bytes(self, fig) -> bytes:
        """Convert matplotlib figure to PNG bytes."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        return buf.read()

    def generate_script(self, config: ChartConfiguration) -> str:
        """Generate Python script for the chart configuration."""
        lines = [
            "import pandas as pd",
            "import matplotlib.pyplot as plt",
            "import seaborn as sns",
            "",
            f"# Seaborn style",
            f"sns.set_style('{config.style}')",
            "",
            "def generate_chart(df: pd.DataFrame) -> bytes:",
            "    '''Generate chart from DataFrame.'''",
            f"    fig, ax = plt.subplots(figsize={config.size})",
            ""
        ]

        # Add aggregation if needed
        if config.aggregation != 'none':
            group_cols = []
            if config.x_column:
                group_cols.append(f"'{config.x_column}'")
            if config.color_column:
                group_cols.append(f"'{config.color_column}'")

            value_col = config.y_column or config.value_column
            lines.extend([
                f"    # Aggregate data",
                f"    df = df.groupby([{', '.join(group_cols)}], as_index=False).agg({{'{value_col}': '{config.aggregation}'}})",
                ""
            ])

        # Chart-specific code
        if config.chart_type in ['bar', 'barh', 'bar_grouped']:
            hue = f", hue='{config.color_column}'" if config.color_column else ""
            orient = ", orient='h'" if config.chart_type == 'barh' else ""
            x_col = config.x_column if config.chart_type != 'barh' else config.y_column
            y_col = config.y_column if config.chart_type != 'barh' else config.x_column
            lines.append(f"    sns.barplot(data=df, x='{x_col}', y='{y_col}'{hue}, palette='{config.palette}'{orient}, ax=ax)")

        elif config.chart_type == 'line':
            hue = f", hue='{config.color_column}'" if config.color_column else ""
            lines.append(f"    sns.lineplot(data=df, x='{config.x_column}', y='{config.y_column}'{hue}, palette='{config.palette}', marker='o', ax=ax)")

        elif config.chart_type in ['pie', 'donut']:
            lines.extend([
                f"    labels = df['{config.label_column}'].tolist()",
                f"    values = df['{config.value_column}'].tolist()",
                f"    colors = sns.color_palette('{config.palette}', len(labels))",
                f"    ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)",
            ])
            if config.chart_type == 'donut':
                lines.append(f"    ax.add_artist(plt.Circle((0, 0), {config.donut_ratio}, fc='white'))")
            lines.append("    ax.axis('equal')")

        elif config.chart_type == 'scatter':
            hue = f", hue='{config.color_column}'" if config.color_column else ""
            lines.append(f"    sns.scatterplot(data=df, x='{config.x_column}', y='{config.y_column}'{hue}, palette='{config.palette}', ax=ax)")

        elif config.chart_type == 'histogram':
            bins = config.bins or "'auto'"
            lines.append(f"    sns.histplot(data=df, x='{config.x_column}', bins={bins}, ax=ax)")

        elif config.chart_type == 'boxplot':
            x_param = f", x='{config.x_column}'" if config.x_column else ""
            lines.append(f"    sns.boxplot(data=df{x_param}, y='{config.y_column}', palette='{config.palette}', ax=ax)")

        elif config.chart_type == 'heatmap':
            lines.extend([
                "    numeric_df = df.select_dtypes(include=['number'])",
                "    corr_matrix = numeric_df.corr()",
                f"    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='{config.palette}', ax=ax)"
            ])

        # Add styling
        lines.extend([
            "",
            "    # Styling"
        ])
        if config.title:
            lines.append(f"    ax.set_title('{config.title}', fontsize=14, fontweight='bold')")
        if config.x_label:
            lines.append(f"    ax.set_xlabel('{config.x_label}')")
        if config.y_label:
            lines.append(f"    ax.set_ylabel('{config.y_label}')")

        lines.extend([
            "",
            "    plt.tight_layout()",
            "",
            "    # Convert to bytes",
            "    import io",
            "    buf = io.BytesIO()",
            "    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')",
            "    buf.seek(0)",
            "    plt.close(fig)",
            "    return buf.read()"
        ])

        return "\n".join(lines)
