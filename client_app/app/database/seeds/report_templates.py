"""
Seeds: Plantillas de informe de ejemplo.
"""
from uuid import uuid4


DEMO_TEMPLATES = [
    {
        "id": str(uuid4()),
        "name": "Resumen Ejecutivo",
        "description": "Informe ejecutivo con KPIs y gráficos de tendencia",
        "category": "ejecutivo",
        "structure": {
            "blocks": [
                {"id": "title", "type": "text", "content": "# {{report_title}}"},
                {"id": "summary", "type": "text", "content": "## Resumen\n{{executive_summary}}"},
                {"id": "kpis", "type": "chart", "library": "echarts", "chart_type": "gauge",
                 "config": {"series": [{"type": "gauge", "data": [{"value": "{{kpi_value}}"}]}]}},
                {"id": "trend", "type": "chart", "library": "echarts", "chart_type": "line",
                 "data_field": "trend_data", "x_field": "date", "y_field": "value"}
            ]
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "report_title": {"type": "string"},
                "executive_summary": {"type": "string"},
                "kpi_value": {"type": "number"},
                "trend_data": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["report_title", "trend_data"]
        },
        "preview_data": {
            "report_title": "Informe Q1 2024",
            "executive_summary": "Crecimiento del 15% respecto al trimestre anterior.",
            "kpi_value": 85,
            "trend_data": [
                {"date": "2024-01", "value": 100},
                {"date": "2024-02", "value": 115},
                {"date": "2024-03", "value": 130}
            ]
        },
        "style_config": {
            "theme": "corporate",
            "colors": {"primary": "#1976D2", "success": "#4CAF50"},
            "render": {"interactive_library": "echarts", "export_format": "svg", "export_dpi": 300}
        }
    },
    {
        "id": str(uuid4()),
        "name": "Informe de Ventas",
        "description": "Análisis de ventas por región y producto con tablas comparativas",
        "category": "ventas",
        "structure": {
            "blocks": [
                {"id": "header", "type": "text", "content": "# Informe de Ventas - {{period}}"},
                {"id": "by_region", "type": "chart", "library": "echarts", "chart_type": "pie",
                 "data_field": "sales_by_region", "x_field": "region", "y_field": "total"},
                {"id": "by_product", "type": "chart", "library": "echarts", "chart_type": "bar",
                 "data_field": "sales_by_product", "x_field": "product", "y_field": "quantity"},
                {"id": "detail_table", "type": "table", "data_field": "sales_detail",
                 "columns": [
                     {"field": "date", "header": "Fecha", "format": "date"},
                     {"field": "product", "header": "Producto"},
                     {"field": "quantity", "header": "Cantidad", "format": "number"},
                     {"field": "total", "header": "Total", "format": "currency"}
                 ]}
            ]
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string"},
                "sales_by_region": {"type": "array"},
                "sales_by_product": {"type": "array"},
                "sales_detail": {"type": "array"}
            },
            "required": ["period", "sales_detail"]
        },
        "preview_data": {
            "period": "Marzo 2024",
            "sales_by_region": [
                {"region": "Norte", "total": 45000},
                {"region": "Sur", "total": 32000},
                {"region": "Este", "total": 28000}
            ],
            "sales_by_product": [
                {"product": "Producto A", "quantity": 150},
                {"product": "Producto B", "quantity": 230},
                {"product": "Producto C", "quantity": 180}
            ],
            "sales_detail": [
                {"date": "2024-03-01", "product": "Producto A", "quantity": 50, "total": 5000},
                {"date": "2024-03-15", "product": "Producto B", "quantity": 80, "total": 12000}
            ]
        }
    }
]
