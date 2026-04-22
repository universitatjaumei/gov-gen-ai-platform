
import pytest
from unittest.mock import MagicMock, patch
from client_app.app.ui.components.anonymizer_field_row import AnonymizerFieldRow

class TestAnonymizerFieldRow:
    
    @patch('client_app.app.ui.components.anonymizer_field_row.ui')
    def test_person_field_options(self, mock_ui):
        """Verificar opciones para campo tipo PERSON."""
        # Setup mocks
        mock_row = MagicMock()
        mock_ui.row.return_value.__enter__.return_value = mock_row
        mock_col = MagicMock()
        mock_ui.column.return_value.__enter__.return_value = mock_col
        mock_select = MagicMock()
        mock_ui.select.return_value = mock_select
        
        # Test Data
        field_info = {
            'field': 'Nombre',
            'type': 'PERSON',
            'is_sensitive': True,
            'recommended_strategy': 'masking'
        }
        
        # Instantiate
        row = AnonymizerFieldRow(field_info)
        
        # Check select options passed to ui.select
        # The constructor calls _build_ui which calls ui.select(options=...)
        # We need to find the call to ui.select
        
        call_args = mock_ui.select.call_args
        assert call_args is not None, "ui.select no fue llamado"
        
        kwargs = call_args[1]
        options = kwargs.get('options')
        
        # Verify 'Datos Sintéticos' NOT in options
        # Note: The code passes options=list(options.keys())
        # So we check the keys (display values)
        
        assert "Datos Sintéticos (IA)" not in options, "Datos Sintéticos no debería aparecer"
        assert "Ocultación (XXXX)" in options, "Ocultación debería aparecer"
        assert "Iniciales (J.P.)" in options, "Iniciales deberia aparecer para PERSON"
        
    @patch('client_app.app.ui.components.anonymizer_field_row.ui')
    def test_email_field_options(self, mock_ui):
        """Verificar opciones para campo tipo EMAIL (no PERSON)."""
        # Setup mocks
        mock_ui.select.return_value = MagicMock()
        
        # Test Data
        field_info = {
            'field': 'Email',
            'type': 'EMAIL',
            'is_sensitive': True
        }
        
        row = AnonymizerFieldRow(field_info)
        
        call_args = mock_ui.select.call_args
        kwargs = call_args[1]
        options = kwargs.get('options')
        
        assert "Iniciales (J.P.)" not in options, "Iniciales NO debería aparecer para EMAIL"
        assert "Ocultación (XXXX)" in options

if __name__ == "__main__":
    t = TestAnonymizerFieldRow()
    try:
        # Mock ui for manual run
        with patch('client_app.app.ui.components.anonymizer_field_row.ui') as mock_ui:
             t.test_person_field_options(mock_ui)
             print("✅ Campo PERSON verificado correctamente.")
             t.test_email_field_options(mock_ui)
             print("✅ Campo EMAIL verificado correctamente.")
    except Exception as e:
        print(f"❌ Fallo en las pruebas de UI: {e}")
        exit(1)
