import pytest
import pandas as pd
from pathlib import Path

from client_app.app.modules.factory.report_factory import ReportFactory


class TestReportFactoryHTML:
    """Tests para backend HTML de ReportFactory."""
    
    @pytest.fixture
    def factory_html(self):
        """Factory con backend HTML."""
        return ReportFactory(backend="html")
    
    @pytest.fixture
    def sample_data(self):
        return {
            "title": "Informe de Ventas Q1 2026",
            "subtitle": "Análisis Trimestral",
            "date": "2026-01-27",
            "summary": "Las ventas aumentaron un 15% respecto al año anterior."
        }
    
    @pytest.fixture
    def sample_dataframe(self):
        return pd.DataFrame({
            "Producto": ["Widget A", "Widget B", "Widget C"],
            "Ventas": [1250, 1890, 745],
            "Margen (%)": [12.5, 15.8, 10.2]
        })
    
    def test_export_html_only(self, factory_html, sample_data, tmp_path):
        """Exporta solo HTML sin generar PDF."""
        output_html = tmp_path / "report.html"
        
        factory_html.export_html(
            context=sample_data,
            output_path=str(output_html)
        )
        
        assert output_html.exists()
        content = output_html.read_text(encoding='utf-8')
        assert sample_data['title'] in content
        assert '<html' in content
        assert '</html>' in content
    
    def test_generate_pdf_with_html_export(self, factory_html, sample_data, sample_dataframe, tmp_path):
        """Genera PDF y también exporta HTML."""
        output_pdf = tmp_path / "report.pdf"
        output_html = tmp_path / "report.html"
        
        context = {
            **sample_data,
            "table_data": sample_dataframe
        }
        
        factory_html.generate_pdf(
            context=context,
            output_path=str(output_pdf),
            export_html=True,
            html_path=str(output_html)
        )
        
        # Verificar PDF generado
        assert output_pdf.exists()
        with open(output_pdf, "rb") as f:
            assert f.read(4) == b"%PDF"
        
        # Verificar HTML exportado
        assert output_html.exists()
        html_content = output_html.read_text(encoding='utf-8')
        assert sample_data['title'] in html_content
        assert 'Widget A' in html_content  # Verificar tabla
    
    def test_html_template_with_custom_styles(self, factory_html, sample_data, tmp_path):
        """Template HTML respeta estilos personalizados."""
        output_html = tmp_path / "styled.html"
        
        context = {
            **sample_data,
            "styles": {
                "title_color": "#FF0000",
                "title_size": 36,
                "body_color": "#333333",
                "body_size": 14
            }
        }
        
        factory_html.export_html(context=context, output_path=str(output_html))
        
        html_content = output_html.read_text(encoding='utf-8')
        assert '#FF0000' in html_content  # Color del título
        assert '36' in html_content  # Tamaño del título (check logic in template default)
    
    def test_html_with_sections(self, factory_html, sample_data, tmp_path):
        """HTML incluye secciones correctamente."""
        output_html = tmp_path / "sections.html"
        
        context = {
            **sample_data,
            "sections": [
                {"heading": "Sección 1", "content": "Contenido de prueba 1"},
                {"heading": "Sección 2", "content": "Contenido de prueba 2"}
            ]
        }
        
        factory_html.export_html(context=context, output_path=str(output_html))
        
        html_content = output_html.read_text(encoding='utf-8')
        assert "Sección 1" in html_content
        assert "Contenido de prueba 1" in html_content
        assert "Sección 2" in html_content
    
    def test_html_editable_after_export(self, factory_html, sample_data, tmp_path):
        """HTML exportado es editable y se puede abrir en navegador."""
        output_html = tmp_path / "editable.html"
        
        factory_html.export_html(context=sample_data, output_path=str(output_html))
        
        # Leer HTML
        original_content = output_html.read_text(encoding='utf-8')
        
        # Simular edición manual (cambiar título)
        # Note: In regex or replace, be careful with encoding or exact string match
        edited_content = original_content.replace(
            sample_data['title'],
            "TÍTULO EDITADO MANUALMENTE"
        )
        
        # Guardar versión editada
        output_html.write_text(edited_content, encoding='utf-8')
        
        # Verificar que el cambio se guardó
        final_content = output_html.read_text(encoding='utf-8')
        assert "TÍTULO EDITADO MANUALMENTE" in final_content
        assert sample_data['title'] not in final_content
