import pytest
import asyncio
from unittest.mock import MagicMock, patch

# Mock nicegui before importing etl_page_content
mock_ui = MagicMock()
mock_app = MagicMock()

with patch('nicegui.ui', mock_ui), patch('nicegui.app', mock_app):
    from client_app.app.ui.etl_page import etl_page_content

@pytest.mark.asyncio
async def test_etl_page_imports_and_asyncio():
    """Verify that etl_page_content can be executed without ImportError and asyncio is present."""
    with patch('client_app.app.core.state.state') as mock_state:
        # Mock i18n
        mock_state.i18n.t = lambda x, **kwargs: x
        
        # Mock refreshable
        def mock_refreshable(f):
            f.refresh = MagicMock()
            return f
        mock_ui.refreshable.side_effect = mock_refreshable
        
        # Execute content - this verifies that no immediate ImportError or NameError occurs
        etl_page_content()
        
        # Verify asyncio is present in the module
        import client_app.app.ui.etl_page as etl_page
        assert hasattr(etl_page, 'asyncio')
        assert etl_page.asyncio is asyncio

def test_no_get_async_session_reference():
    """Verify that get_async_session is no longer imported in the file."""
    from pathlib import Path
    file_path = Path("client_app/app/ui/etl_page.py")
    content = file_path.read_text(encoding='utf-8')
    assert "from client_app.app.database.db import get_async_session" not in content
    assert "get_async_session" not in content # Should not even be a string reference usually
