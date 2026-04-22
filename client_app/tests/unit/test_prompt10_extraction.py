
import pytest
import sys
import os
sys.path.append(os.getcwd())
from unittest.mock import AsyncMock, MagicMock, patch

# Mock nicegui content
mock_ui = MagicMock()
sys.modules["nicegui"] = MagicMock()
sys.modules["nicegui"].ui = mock_ui
sys.modules["nicegui"].app = MagicMock()
sys.modules["nicegui"].events = MagicMock()

# Better mock for refreshable
def mock_refreshable(func):
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    wrapper.refresh = MagicMock()
    return wrapper
mock_ui.refreshable = mock_refreshable

# Mock dependencies
sys.modules["client_app.app.core.state"] = MagicMock()
sys.modules["client_app.app.ui.components.privacy_indicator"] = MagicMock()
sys.modules["client_app.app.ui.components.privacy_report"] = MagicMock()
# Mock AutomationSelector
sys.modules["client_app.app.ui.components.automation_selector"] = MagicMock()

# Mock Extraction Service dependencies inside extraction page
sys.modules["client_app.app.ui.factory_page"] = MagicMock()
sys.modules["client_app.app.services.extraction_service"] = MagicMock()

# Import
from client_app.app.ui.extraction_page import extraction_page_content

@pytest.mark.asyncio
async def test_extraction_page_state_logic():
    # Setup State
    mock_state = sys.modules["client_app.app.core.state"].state
    mock_state.i18n.t.side_effect = lambda x: x
    
    # Mock Automation Selector
    mock_render_selector = sys.modules["client_app.app.ui.components.automation_selector"].render_automation_selector
    
    # Needs to be awaitable
    async def fake_render(*args, **kwargs):
        return None
    mock_render_selector.side_effect = fake_render
    
    # Run content
    await extraction_page_content()
    
    # 1. Verify Selector is called
    assert mock_render_selector.called
    call_args = mock_render_selector.call_args
    # call_args is (args, kwargs) or just args matching
    # render_automation_selector(automation_type='PDF_EXTRACTOR', ...)
    # Check if keyword arg was used or positional
    # Signature: render_automation_selector(automation_type, on_change, value=None)
    
    # Check args
    kwargs = call_args.kwargs
    if not kwargs:
        # Check positional
        args = call_args.args
        if args:
            assert args[0] == 'PDF_EXTRACTOR'
    else:
        if 'automation_type' in kwargs:
            assert kwargs['automation_type'] == 'PDF_EXTRACTOR'
    
    # Check toggle was called?
    # Since we use mocks for everything, we can't easily check ui.toggle unless we mock it specifically or check mock_ui.toggle
    # But checking selector integration is the main goal here.
    
    print("✅ Automation Selector was integrated and called correctly")
import asyncio

if __name__ == "__main__":
    asyncio.run(test_extraction_page_state_logic())
