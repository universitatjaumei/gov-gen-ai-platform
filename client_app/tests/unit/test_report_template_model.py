"""
Tests para el modelo ReportTemplate extendido.
TDD: Estos tests DEBEN FALLAR inicialmente.
"""
import pytest
import json
from uuid import uuid4
from client_app.app.database.models import ReportTemplate
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import text

# Setup for in-memory database given we don't have the full app context
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

class TestReportTemplateModel:
    """Tests para el modelo ReportTemplate."""

    def test_create_report_template_with_structure(self, session: Session):
        """
        RED: Crear plantilla con estructura de bloques.
        """
        structure = {
            "blocks": [
                {"id": "header", "type": "text", "content": "# Informe Mensual"},
                {"id": "chart1", "type": "chart", "chart_type": "bar", "x_field": "month", "y_field": "sales"},
                {"id": "table1", "type": "table", "columns": ["product", "quantity", "total"]}
            ]
        }

        template = ReportTemplate(
            name="Informe de Ventas",
            description="Resumen mensual de ventas por producto",
            structure=structure
        )
        session.add(template)
        session.commit()

        assert template.id is not None
        # Accessing as dict/json because the model field defines it as such
        # In SQLModel/Pydantic, if it's defined as Dict, it should be accessible as one.
        # Note: The prompt assumes `structure` field exists. In the current model it doesn't.
        # So this will fail with ValidatError or AttributeError depending on strictness.
        assert template.structure["blocks"][1]["chart_type"] == "bar"

    def test_input_schema_validation(self, session: Session):
        """
        RED: El input_schema debe definir las variables esperadas.
        """
        input_schema = {
            "type": "object",
            "properties": {
                "sales_data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "month": {"type": "string"},
                            "sales": {"type": "number"}
                        }
                    }
                },
                "report_title": {"type": "string"}
            },
            "required": ["sales_data"]
        }

        template = ReportTemplate(
            name="Test Template",
            input_schema=input_schema,
            structure={"blocks": []}
        )
        session.add(template)
        session.commit()

        assert "sales_data" in template.input_schema["required"]

    def test_style_config_with_render_options(self, session: Session):
        """
        RED: style_config debe incluir opciones de renderizado dual.
        """
        style_config = {
            "theme": "corporate",
            "colors": {"primary": "#1976D2", "secondary": "#424242"},
            "fonts": {"title": "Roboto", "body": "Open Sans"},
            "render": {
                "interactive_library": "echarts",
                "export_format": "svg",
                "export_dpi": 300,
                "page_size": "A4"
            }
        }

        template = ReportTemplate(
            name="Styled Template",
            style_config=style_config,
            structure={"blocks": []}
        )
        session.add(template)
        session.commit()

        assert template.style_config["render"]["interactive_library"] == "echarts"
        assert template.style_config["render"]["export_dpi"] == 300

    def test_preview_data_for_mock_rendering(self, session: Session):
        """
        RED: preview_data debe contener datos mock para diseño.
        """
        preview_data = {
            "sales_data": [
                {"month": "Enero", "sales": 15000},
                {"month": "Febrero", "sales": 18500},
                {"month": "Marzo", "sales": 22000}
            ],
            "report_title": "Vista Previa - Datos Ficticios"
        }

        template = ReportTemplate(
            name="Preview Template",
            preview_data=preview_data,
            structure={"blocks": []}
        )
        session.add(template)
        session.commit()

        assert len(template.preview_data["sales_data"]) == 3

    def test_chart_block_echarts_config(self, session: Session):
        """
        RED: Bloques de gráfico deben almacenar config ECharts/Plotly.
        """
        structure = {
            "blocks": [
                {
                    "id": "sales_chart",
                    "type": "chart",
                    "library": "echarts",
                    "config": {
                        "title": {"text": "Ventas Mensuales"},
                        "xAxis": {"type": "category", "data_field": "month"},
                        "yAxis": {"type": "value"},
                        "series": [
                            {"type": "bar", "data_field": "sales", "name": "Ventas"}
                        ]
                    }
                }
            ]
        }

        template = ReportTemplate(
            name="ECharts Template",
            structure=structure
        )
        session.add(template)
        session.commit()

        chart_block = template.structure["blocks"][0]
        assert chart_block["library"] == "echarts"
        assert chart_block["config"]["series"][0]["type"] == "bar"
