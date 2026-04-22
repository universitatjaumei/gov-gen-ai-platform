import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock nicegui before importing the component
mock_ui = MagicMock()
sys.modules["nicegui"] = MagicMock()
sys.modules["nicegui"].ui = mock_ui

# Now we can import
from client_app.app.ui.components.automation_selector import render_automation_selector
from client_app.app.database.models import LocalAutomation

@pytest.mark.asyncio
async def test_automation_selector_fetches_and_renders():
    # Mock DB Session and results
    mock_automation = LocalAutomation(
        id="auto-1", 
        name="Test Auto", 
        type="pdf_extractor", 
        code_content="print('hello')",
        local_status="synced"
    )
    
    # Mock DB Result
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [mock_automation]
    mock_session.exec.return_value = mock_result
    
    # Mock Context Manager for get_db
    mock_db_ctx = AsyncMock()
    mock_db_ctx.__aenter__.return_value = mock_session
    
    # We need to patch get_db inside the module
    with patch('client_app.app.ui.components.automation_selector.get_db', return_value=mock_db_ctx):
        
        mock_callback = MagicMock()
        
        # ACT
        await render_automation_selector("pdf_extractor", mock_callback)
        
        # ASSERT
        # 1. DB Query verification
        assert mock_session.exec.called
        
        # 2. UI Rendering verification
        # Since we mocked nicegui.ui as mock_ui globally
        assert mock_ui.label.called
        mock_ui.label.assert_called_with("Biblioteca de PDF_EXTRACTOR")
        
        # 3. Check options passed to select
        assert mock_ui.select.called
        call_args = mock_ui.select.call_args
        assert call_args is not None
        options = call_args.kwargs.get('options')
        assert options is not None
        assert options["auto-1"] == "Test Auto (synced)"
        assert options[None] == '--- Crear Nuevo / Grabar ---'
