# client_app/tests/test_field_import.py
"""
Test TDD for Field Import Service.
Prompt #4 BIS: Importador Masivo de Campos desde Excel/CSV.

Tests the bulk import of field definitions from Excel/CSV files
for extraction configuration.
"""
import pytest
import pandas as pd
import io
from typing import List, Dict

from client_app.app.services.field_import_service import FieldImportService
from automatia_shared.contracts.ui_contract import InputType


class TestFieldImportService:
    """Tests for FieldImportService."""

    @pytest.fixture
    def service(self):
        """Create a FieldImportService instance."""
        return FieldImportService()

    def test_import_fields_from_excel_success(self, service):
        """Test successful import from Excel file."""
        # 1. Create sample DataFrame
        data = {
            'nombre': ['cif_emisor', 'importe_total', 'fecha_factura'],
            'tipo': ['texto', 'numero', 'fecha'],
            'descripcion': ['CIF empresa', 'Total con IVA', 'Fecha emisión']
        }
        df = pd.DataFrame(data)

        # Save to memory buffer (simulating file upload)
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        # 2. Execute service
        fields = service.parse_file(excel_buffer, extension='.xlsx')

        # 3. Validations
        assert len(fields) == 3
        assert fields[0]['name'] == 'cif_emisor'
        assert fields[1]['type'] == InputType.INT  # 'numero' maps to INT
        assert fields[2]['type'] == InputType.DATE

    def test_import_fields_from_csv_success(self, service):
        """Test successful import from CSV file."""
        csv_content = """nombre,tipo,descripcion
num_factura,string,Número de factura
total,float,Importe total
fecha,date,Fecha de emisión
es_pagado,bool,Estado de pago"""

        csv_buffer = io.StringIO(csv_content)

        fields = service.parse_file(csv_buffer, extension='.csv')

        assert len(fields) == 4
        assert fields[0]['name'] == 'num_factura'
        assert fields[0]['type'] == InputType.STR
        assert fields[1]['type'] == InputType.FLOAT
        assert fields[2]['type'] == InputType.DATE
        assert fields[3]['type'] == InputType.BOOL

    def test_import_fields_invalid_format(self, service):
        """Test that invalid format raises ValueError."""
        # CSV without required columns
        bad_csv = io.StringIO("columna1,columna2\nval1,val2")

        with pytest.raises(ValueError, match="Columnas requeridas no encontradas"):
            service.parse_file(bad_csv, extension='.csv')

    def test_type_normalization(self, service):
        """Test that different type aliases are normalized correctly."""
        data = {
            'nombre': ['campo1', 'campo2', 'campo3', 'campo4', 'campo5', 'campo6'],
            'tipo': ['Texto', 'STRING', 'str', 'NUMERO', 'Integer', 'int']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        # All text types should map to STR
        assert fields[0]['type'] == InputType.STR
        assert fields[1]['type'] == InputType.STR
        assert fields[2]['type'] == InputType.STR

        # All numeric types should map to INT
        assert fields[3]['type'] == InputType.INT
        assert fields[4]['type'] == InputType.INT
        assert fields[5]['type'] == InputType.INT

    def test_name_sanitization(self, service):
        """Test that field names are sanitized to valid identifiers."""
        data = {
            'nombre': ['Nombre Cliente', 'Fecha Factura', 'Total con IVA', '123_invalid'],
            'tipo': ['texto', 'fecha', 'numero', 'texto']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        # Names should be sanitized to snake_case
        assert fields[0]['name'] == 'nombre_cliente'
        assert fields[1]['name'] == 'fecha_factura'
        assert fields[2]['name'] == 'total_con_iva'
        # Invalid names starting with numbers should be prefixed
        assert fields[3]['name'] == 'field_123_invalid'

    def test_unknown_type_defaults_to_str(self, service):
        """Test that unknown types default to STR with warning."""
        data = {
            'nombre': ['campo_raro'],
            'tipo': ['tipo_inexistente']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields, warnings = service.parse_file_with_warnings(excel_buffer, extension='.xlsx')

        assert len(fields) == 1
        assert fields[0]['type'] == InputType.STR  # Default
        assert len(warnings) > 0
        assert 'tipo_inexistente' in warnings[0].lower()

    def test_optional_description_column(self, service):
        """Test that description column is optional."""
        data = {
            'nombre': ['campo1', 'campo2'],
            'tipo': ['texto', 'numero']
            # No description column
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        assert len(fields) == 2
        assert fields[0]['description'] == ''  # Empty by default
        assert fields[1]['description'] == ''

    def test_is_optional_column(self, service):
        """Test that is_optional column is processed correctly."""
        data = {
            'nombre': ['campo_requerido', 'campo_opcional'],
            'tipo': ['texto', 'texto'],
            'opcional': [False, True]
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        assert fields[0]['is_optional'] is False
        assert fields[1]['is_optional'] is True

    def test_empty_file_raises_error(self, service):
        """Test that empty file raises appropriate error."""
        df = pd.DataFrame(columns=['nombre', 'tipo'])  # Empty

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        with pytest.raises(ValueError, match="[Aa]rchivo.*vacío|[Nn]o.*campos"):
            service.parse_file(excel_buffer, extension='.xlsx')

    def test_duplicate_names_handled(self, service):
        """Test that duplicate field names are made unique."""
        data = {
            'nombre': ['campo', 'campo', 'campo'],
            'tipo': ['texto', 'numero', 'fecha']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        names = [f['name'] for f in fields]
        # All names should be unique
        assert len(names) == len(set(names))

    def test_alternative_column_names(self, service):
        """Test that alternative column names are accepted."""
        # Using English column names instead of Spanish
        data = {
            'name': ['field1', 'field2'],
            'type': ['string', 'int'],
            'description': ['First field', 'Second field']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        assert len(fields) == 2
        assert fields[0]['name'] == 'field1'
        assert fields[0]['type'] == InputType.STR


class TestFieldImportServiceEdgeCases:
    """Edge case tests for FieldImportService."""

    @pytest.fixture
    def service(self):
        return FieldImportService()

    def test_whitespace_handling(self, service):
        """Test that whitespace is trimmed from values."""
        data = {
            'nombre': ['  campo_con_espacios  ', '  otro_campo  '],
            'tipo': ['  texto  ', '  numero  ']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        assert fields[0]['name'] == 'campo_con_espacios'
        assert fields[1]['name'] == 'otro_campo'

    def test_mixed_case_column_names(self, service):
        """Test that column names are case-insensitive."""
        data = {
            'NOMBRE': ['campo1'],
            'Tipo': ['texto'],
            'DESCRIPCION': ['Una descripción']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        assert len(fields) == 1
        assert fields[0]['name'] == 'campo1'

    def test_special_characters_in_description(self, service):
        """Test that special characters in description are preserved."""
        data = {
            'nombre': ['campo1'],
            'tipo': ['texto'],
            'descripcion': ['Campo con "comillas" y acentos: áéíóú']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        assert 'comillas' in fields[0]['description']
        assert 'áéíóú' in fields[0]['description']

    def test_numeric_type_variations(self, service):
        """Test various numeric type aliases."""
        data = {
            'nombre': ['f1', 'f2', 'f3', 'f4', 'f5'],
            'tipo': ['entero', 'integer', 'decimal', 'float', 'money']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        assert fields[0]['type'] == InputType.INT
        assert fields[1]['type'] == InputType.INT
        assert fields[2]['type'] == InputType.FLOAT
        assert fields[3]['type'] == InputType.FLOAT
        assert fields[4]['type'] == InputType.FLOAT

    def test_boolean_type_variations(self, service):
        """Test various boolean type aliases."""
        data = {
            'nombre': ['f1', 'f2', 'f3', 'f4'],
            'tipo': ['bool', 'boolean', 'booleano', 'si/no']
        }
        df = pd.DataFrame(data)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        fields = service.parse_file(excel_buffer, extension='.xlsx')

        assert fields[0]['type'] == InputType.BOOL
        assert fields[1]['type'] == InputType.BOOL
        assert fields[2]['type'] == InputType.BOOL
        assert fields[3]['type'] == InputType.BOOL
