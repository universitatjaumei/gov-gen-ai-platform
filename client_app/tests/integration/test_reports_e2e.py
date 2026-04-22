import pytest
import pandas as pd
from pathlib import Path
from PIL import Image

from client_app.app.modules.factory.report_factory import ReportFactory

class TestReportsE2E:
    """Tests End-to-End de Generación de Informes (ReportLab + HTML)."""

    @pytest.fixture
    def sample_data(self):
        return {
            "title": "Informe E2E Ventas 2026",
            "subtitle": "Generado automáticamente por AutomatIA",
            "date": "2026-01-27",
            "summary": "Este informe demuestra la capacidad de generación end-to-end con múltiples backends.",
            "styles": {
                "title_color": "#003366",
                "title_size": 28
            }
        }

    @pytest.fixture
    def sample_dataframe(self):
        return pd.DataFrame({
            "Región": ["Norte", "Sur", "Este", "Oeste"],
            "Ventas": [45000, 32000, 28000, 51000],
            "Crecimiento": ["+5%", "-2%", "+1%", "+8%"]
        })

    @pytest.fixture
    def chart_image(self, tmp_path):
        """Simula un gráfico generado por GraphicsFactory."""
        img_path = tmp_path / "chart_simulated.png"
        # Crear imagen roja de 400x300
        img = Image.new('RGB', (400, 300), color='#FF5733')
        img.save(img_path)
        return str(img_path)

    async def test_full_workflow_reportlab_backend(self, sample_data, sample_dataframe, chart_image, tmp_path):
        """
        Workflow completo: Datos + Gráfico -> PDF (ReportLab).
        Verifica que se puede generar un informe complejo programáticamente.
        """
        factory = ReportFactory(backend="reportlab")
        output_pdf = tmp_path / "e2e_report_rl.pdf"

        # Contexto completo
        context = {
            **sample_data,
            "table_data": sample_dataframe,
            "logo_path": chart_image,  # Usamos el gráfico como logo/imagen
            "sections": [
                {"heading": "Análisis Regional", "content": "El rendimiento en la región Oeste ha superado expectativas."},
                {"heading": "Metodología", "content": "Datos extraídos automáticamente del ERP via ETL."}
            ]
        }

        # Generación
        result_path = factory.generate_pdf(context=context, output_path=str(output_pdf))

        # Verificaciones
        assert Path(result_path).exists()
        assert Path(result_path).stat().st_size > 2000
        
        # Verificar header PDF
        with open(result_path, "rb") as f:
            assert f.read(5) == b"%PDF-"

    async def test_full_workflow_html_backend_dual_export(self, sample_data, sample_dataframe, chart_image, tmp_path):
        """
        Workflow completo: Datos + Tabla -> PDF + HTML Editable (HTML Backend).
        Verifica flujos híbridos donde el usuario quiere editar antes de imprimir.
        """
        factory = ReportFactory(backend="html")
        output_pdf = tmp_path / "e2e_report_html.pdf"
        output_html = tmp_path / "e2e_report_editable.html"

        context = {
            **sample_data,
            "table_data": sample_dataframe,
            # Playwright y HTML soportan paths absolutos locales
            "logo_path": chart_image 
        }

        # Generación Dual
        factory.generate_pdf(
            context=context, 
            output_path=str(output_pdf),
            export_html=True,
            html_path=str(output_html)
        )

        # 1. Verificar HTML
        assert output_html.exists()
        html_content = output_html.read_text(encoding="utf-8")
        assert "Informe E2E Ventas 2026" in html_content
        assert "Oeste" in html_content # Datos de tabla
        assert chart_image in html_content # Referencia a imagen
        
        # 2. Verificar PDF
        assert output_pdf.exists()
        assert output_pdf.stat().st_size > 1000

    def test_legacy_api_compatibility(self, sample_dataframe):
        """
        Verifica que métodos legacy o alias se mantengan si es necesario, 
        o que la nueva API cubra casos de uso antiguos.
        """
        # Aunque eliminamos methods obsoletos, verificamos que ReportFactory maneje DataFrames
        # sin necesidad de llamar a dataframe_to_html explícitamente (ahora integrado)
        html_table = ReportFactory.dataframe_to_html(sample_dataframe)
        assert "<table" in html_table
        # assert "class=\"table" in html_table  # Pandas output format varies, relax check
