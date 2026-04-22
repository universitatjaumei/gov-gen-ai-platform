import pytest
import pandas as pd
import zipfile
import os
from xml.etree import ElementTree as ET
from client_app.app.modules.factory.report_factory import ReportFactory

class TestODTCompatibility:
    """Integration checks for ODT file validity and compatibility."""

    @pytest.fixture
    def factory(self):
        return ReportFactory(backend="reportlab")

    @pytest.fixture
    def sample_context(self):
        return {
            'title': 'Informe de Prueba',
            'subtitle': 'Generado automáticamente',
            'date': '2024-01-15',
            'summary': 'Este es un resumen del informe con datos de ejemplo.',
            'sections': [
                {'heading': 'Introducción', 'content': 'Texto de introducción...'},
                {'heading': 'Resultados', 'content': 'Texto de resultados...'}
            ],
            'table_data': pd.DataFrame({
                'Producto': ['A', 'B', 'C'],
                'Cantidad': [100, 200, 150],
                'Precio': [10.5, 20.0, 15.75]
            }),
            'styles': {
                'title_color': '#1a365d',
                'title_size': 24
            }
        }

    def test_odt_is_valid_zip(self, factory, sample_context, tmp_path):
        """ODT must be a valid ZIP file containing standard ODF structure."""
        output_path = tmp_path / "structure_test.odt"
        factory.generate_odt(sample_context, str(output_path))
        
        assert zipfile.is_zipfile(output_path)
        
        with zipfile.ZipFile(output_path, 'r') as z:
            # Check mandatory ODF files are present
            file_list = z.namelist()
            assert 'content.xml' in file_list
            assert 'styles.xml' in file_list
            assert 'META-INF/manifest.xml' in file_list
            assert 'mimetype' in file_list

    def test_odt_has_correct_mimetype(self, factory, sample_context, tmp_path):
        """Mimetype file must contain the correct ODT mimetype string."""
        output_path = tmp_path / "mimetype_test.odt"
        factory.generate_odt(sample_context, str(output_path))
        
        with zipfile.ZipFile(output_path, 'r') as z:
            mimetype = z.read('mimetype').decode('utf-8')
            assert mimetype == 'application/vnd.oasis.opendocument.text'

    def test_odt_content_xml_is_valid(self, factory, sample_context, tmp_path):
        """content.xml must be parseable XML."""
        output_path = tmp_path / "xml_validity_test.odt"
        factory.generate_odt(sample_context, str(output_path))
        
        with zipfile.ZipFile(output_path, 'r') as z:
            with z.open('content.xml') as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    assert root is not None
                except ET.ParseError as e:
                    pytest.fail(f"content.xml is not valid XML: {e}")

    def test_odt_with_special_characters(self, factory, tmp_path):
        """Must handle special characters (accents, currency symbols) correctly."""
        output_path = tmp_path / "special_chars.odt"
        context = {
            'title': 'Año 2024 - Cálculo € 100',
            'summary': 'Camión, Cigüeña, 100$',
            'sections': [{'heading': 'Sección Única', 'content': 'Más caracteres: ñ, ú, ¿?'}]
        }
        
        factory.generate_odt(context, str(output_path))
        
        # Verify content.xml has the encoded characters or correct UTF-8
        with zipfile.ZipFile(output_path, 'r') as z:
            content_xml = z.read('content.xml').decode('utf-8')
            assert 'Año 2024' in content_xml
            assert 'Cálculo € 100' in content_xml
            assert 'Camión' in content_xml
            assert 'ñ' in content_xml

    def test_odt_with_large_dataframe(self, factory, tmp_path):
        """Must handle large DataFrames without error impacting integrity."""
        output_path = tmp_path / "large_df.odt"
        
        # Create a dataframe with 1000 rows
        large_df = pd.DataFrame({'col': range(1000), 'val': ['test'] * 1000})
        
        context = {
            'title': 'Large Report',
            'table_data': large_df
        }
        
        factory.generate_odt(context, str(output_path))
        
        assert os.path.exists(output_path)
        
        # Verify it has many rows roughly by ensuring file size > empty or xml structure
        file_size = os.path.getsize(output_path)
        assert file_size > 1000 # Just a basic check that data was written
