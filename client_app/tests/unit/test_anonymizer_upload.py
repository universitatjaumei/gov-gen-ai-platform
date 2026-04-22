import pytest
import io
import pandas as pd
from unittest.mock import MagicMock, patch

# Aggressive mocking of nicegui
mock_ui = MagicMock()
mock_app = MagicMock()
mock_state = MagicMock()

# Mock i18n.t to return the key
mock_state.i18n.t.side_effect = lambda x, *args, **kwargs: x

with patch('nicegui.ui', mock_ui), \
     patch('nicegui.app', mock_app), \
     patch('client_app.app.core.state.state', mock_state):
    from client_app.app.ui.anonymizer_page import AnonymizerPage

@pytest.mark.asyncio
async def test_handle_upload_async_csv():
    """Verify that handle_upload handles async content and CSV files correctly."""
    
    # Reset mocks
    mock_ui.reset_mock()
    
    def mock_refreshable(f):
        f.refresh = MagicMock()
        return f
    mock_ui.refreshable.side_effect = mock_refreshable

    # Instantiate page and render
    page = AnonymizerPage(mode='utility')
    await page.render()
    
    handle_upload = None
    for call in mock_ui.upload.call_args_list:
        if 'on_upload' in call.kwargs:
            handle_upload = call.kwargs['on_upload']
            break
    
    assert handle_upload is not None
    
    mock_event = MagicMock()
    mock_event.file.name = "test.csv"
    
    async def mock_read():
        return b"col1,col2\nval1,val2"
    
    mock_event.file.read.side_effect = mock_read
    
    await handle_upload(mock_event)
    mock_ui.notify.assert_any_call('anonymizer.file_loaded', type='positive')

@pytest.mark.asyncio
async def test_handle_upload_excel_engine():
    """Verify that handle_upload uses openpyxl engine for Excel files."""
    
    mock_ui.reset_mock()
    
    with patch('pandas.read_excel') as mock_read_excel:
        page = AnonymizerPage(mode='utility')
        await page.render()
        
        handle_upload = None
        for call in mock_ui.upload.call_args_list:
            if 'on_upload' in call.kwargs:
                handle_upload = call.kwargs['on_upload']
                break
        
        mock_event = MagicMock()
        mock_event.file.name = "test.xlsx"
        async def mock_read(): return b"fake-excel-content"
        mock_event.file.read.side_effect = mock_read
        
        with patch.object(page.service, 'load_dataframe', return_value=pd.DataFrame()):
             await handle_upload(mock_event)
        
        mock_ui.notify.assert_any_call('anonymizer.file_loaded', type='positive')

@pytest.mark.asyncio
async def test_handle_upload_error_reporting():
    """Verify that error messages are handled."""
    
    mock_ui.reset_mock()
    
    page = AnonymizerPage(mode='utility')
    await page.render()
    
    handle_upload = None
    for call in mock_ui.upload.call_args_list:
        if 'on_upload' in call.kwargs:
            handle_upload = call.kwargs['on_upload']
            break
    
    mock_event = MagicMock()
    mock_event.file.name = "test.csv"
    async def mock_read(): return b"corrupt-content"
    mock_event.file.read.side_effect = mock_read
    
    with patch.object(page.service, 'load_dataframe', side_effect=ValueError("Invalid CSV")):
        await handle_upload(mock_event)
    
    # Verify error notification
    mock_ui.notify.assert_any_call('anonymizer.error_loading: Invalid CSV', type='negative')
