"""
Unit tests for No-Code Data Contracts (Prompt 3).
Verifies file upload, field suggestion, and contract generation.
Mocks UI interactions to run in isolation.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from automatia_shared.enums import StepType
from automatia_shared.dtos import TaskSpec

@pytest.fixture
def mock_ui():
    """Mock the NiceGUI ui module used in the wizard."""
    with patch('client_app.app.ui.components.unified_creation_wizard.ui') as mock_ui:
        yield mock_ui

@pytest.mark.asyncio
async def test_handle_example_upload_calls_contract_service(mock_ui):
    """Verify upload handler calls data contract service."""
    from client_app.app.ui.components.unified_creation_wizard import UnifiedCreationWizard
    
    # Initialize wizard (ui mocked)
    wizard = UnifiedCreationWizard(context='standalone')
    # Mock container
    wizard.fields_container = Mock()
    
    # Mock the contract service response
    mock_result = {
        'suggested_fields': [
            {'name': 'invoice_number', 'type': 'string', 'description': 'Número de factura'},
            {'name': 'total_amount', 'type': 'number', 'description': 'Importe total'},
            {'name': 'date', 'type': 'date', 'description': 'Fecha de emisión'}
        ]
    }
    
    # Mock upload event
    mock_event = Mock()
    mock_event.name = 'test_invoice.pdf'
    mock_event.content = Mock()
    mock_event.content.read = Mock(return_value=b'fake pdf content')
    
    # Patch the service entry point
    with patch('client_app.app.services.data_contract_service.data_contract_service.suggest_contract', new_callable=AsyncMock) as mock_suggest:
        mock_suggest.return_value = mock_result
        
        # Mock render_fields_selection to verify it's called
        wizard.render_fields_selection = Mock()
        
        # Call handler
        await wizard.handle_example_upload(mock_event)
        
        # Verify service was called with file path for PDF logic (since we mock checking endswith)
        # In current implementation, if it ends with .pdf, it writes to temp.
        # We need to verify suggest_contract was called.
        assert mock_suggest.called
        
        # Verify fields were stored
        assert len(wizard.state.suggested_fields) == 3
        assert wizard.state.suggested_fields[0]['name'] == 'invoice_number'
        
        # Verify render called
        wizard.render_fields_selection.assert_called_once()


def test_generate_data_contract_creates_valid_structure(mock_ui):
    """Verify contract generation creates correct JSON structure."""
    from client_app.app.ui.components.unified_creation_wizard import UnifiedCreationWizard
    
    wizard = UnifiedCreationWizard(context='standalone')
    
    # Set up state with suggested fields
    wizard.state.suggested_fields = [
        {'name': 'invoice_number', 'type': 'string', 'description': 'Número de factura'},
        {'name': 'total_amount', 'type': 'number', 'description': 'Importe total'},
        {'name': 'date', 'type': 'date', 'description': 'Fecha de emisión'}
    ]
    
    # Select first two fields
    wizard.state.selected_fields = {
        'invoice_number': True,
        'total_amount': True,
        'date': False
    }
    
    # Create task spec
    wizard.state.task_spec = TaskSpec(
        id='test',
        name='Test',
        type=StepType.EXTRACTION,
        config={}
    )
    
    # Generate contract
    wizard.generate_data_contract()
    
    # Verify contract structure
    assert 'data_contract' in wizard.state.task_spec.config
    contract = wizard.state.task_spec.config['data_contract']
    
    assert 'fields' in contract
    assert len(contract['fields']) == 2
    
    # Verify field structure
    names = [f['name'] for f in contract['fields']]
    assert 'invoice_number' in names
    assert 'total_amount' in names
    assert 'date' not in names
    
    # Verify notification called
    mock_ui.notify.assert_called()


def test_contract_generation_requires_selection(mock_ui):
    """Verify contract generation validates at least one field is selected."""
    from client_app.app.ui.components.unified_creation_wizard import UnifiedCreationWizard
    
    wizard = UnifiedCreationWizard(context='standalone')
    
    wizard.state.suggested_fields = [
        {'name': 'field1', 'type': 'string'}
    ]
    
    # Deselect all fields
    wizard.state.selected_fields = {'field1': False}
    
    wizard.state.task_spec = TaskSpec(
        id='test',
        name='Test',
        type=StepType.EXTRACTION,
        config={}
    )
    
    # Generate contract (should notify warning)
    wizard.generate_data_contract()
    
    # Verify no contract was created
    assert 'data_contract' not in wizard.state.task_spec.config
    
    # Verify warning notification
    mock_ui.notify.assert_called_with('Selecciona al menos un campo', type='warning')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
