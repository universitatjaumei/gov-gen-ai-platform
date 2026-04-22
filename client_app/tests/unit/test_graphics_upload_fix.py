import pytest
import asyncio
import io
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from types import SimpleNamespace

# Mock NiceGUI components
mock_ui = MagicMock()
mock_app = MagicMock()

with patch.dict('sys.modules', {'nicegui': mock_ui, 'nicegui.ui': mock_ui, 'nicegui.app': mock_app}):
    from client_app.app.ui.components.graphics_wizard import GraphicsWizard

@pytest.mark.asyncio
async def test_graphics_handle_upload_csv():
    """Test async CSV upload in GraphicsWizard."""
    wizard = GraphicsWizard()
    
    # Mock event with CSV content
    csv_content = b"col1,col2\n1,2\n3,4"
    mock_event = SimpleNamespace(
        name="test.csv",
        content=SimpleNamespace(read=AsyncMock(return_value=csv_content))
    )
    
    # Mock factory methods
    wizard.factory.analyze_dataframe = MagicMock(return_value={
        "rows": 2, "columns": ["col1", "col2"], "dtypes": {}, "sample": [], "summary": {}
    })
    wizard.factory.generate_business_questions = AsyncMock(return_value=["Question?"])
    
    # Mock UI components/containers
    wizard._render_uploader = MagicMock()
    wizard._render_uploader.refresh = MagicMock()
    wizard.analysis_container = MagicMock()
    wizard.questions_container = MagicMock()
    wizard.prompt_input = MagicMock()
    
    # Execute upload
    await wizard._handle_upload(mock_event)
    
    # Verify
    assert wizard.filename == "test.csv"
    assert isinstance(wizard.df, pd.DataFrame)
    assert len(wizard.df) == 2
    assert wizard.df_metadata["rows"] == 2
    wizard.factory.analyze_dataframe.assert_called_once()

@pytest.mark.asyncio
async def test_graphics_handle_upload_xlsx():
    """Test async XLSX upload in GraphicsWizard with openpyxl engine."""
    import client_app.app.ui.components.graphics_wizard as gw
    assert hasattr(gw, 'asyncio')
    
    wizard = GraphicsWizard()
    
    # We don't need real Excel bytes, just mock pd.read_excel
    mock_event = SimpleNamespace(
        name="test.xlsx",
        content=SimpleNamespace(read=AsyncMock(return_value=b"fake excel"))
    )
    
    # Mock factory and UI
    wizard.factory.analyze_dataframe = MagicMock()
    wizard.factory.generate_business_questions = AsyncMock()
    wizard._render_uploader = MagicMock()
    wizard._render_uploader.refresh = MagicMock()
    wizard.analysis_container = MagicMock()
    wizard.questions_container = MagicMock()
    
    with patch("pandas.read_excel") as mock_read_excel:
        mock_read_excel.return_value = pd.DataFrame({"a": [1]})
        
        await wizard._handle_upload(mock_event)
        
        # Verify engine='openpyxl' was used
        args, kwargs = mock_read_excel.call_args
        assert kwargs.get("engine") == "openpyxl"
        assert wizard.filename == "test.xlsx"
