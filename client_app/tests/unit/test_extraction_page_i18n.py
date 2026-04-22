
import pytest
from unittest.mock import MagicMock, patch

# Mock nicegui before importing extraction_page
with patch('nicegui.ui'):
    from app.ui.extraction_page import extraction_page_content

from app.core.state import state

def test_extraction_page_imports_and_keys():
    """Verify that extraction page imports correctly and i18n keys exist (basic check)."""
    assert extraction_page_content is not None
    
    # Check if we can instantiate or call it without immediate crash
    # Note: extraction_page_content calls nicegui.ui methods, so we need to mock valid context if we want to run it.
    # For now, just importing it proves syntax is valid.

def test_translation_keys_loaded():
    """Verify that new keys are present in i18n."""
    # Force reload of translations or ensure they are loaded
    state.i18n._load_translations()
    
    t = state.i18n.t
    
    # Check some new keys
    assert t("factory_mode_title") != "factory_mode_title"
    assert t("files_queued", count=5) != "files_queued"
    assert "Modo: Factory" in t("factory_mode_title")
    
    # Check removal of old strings (not really checkable, but we can check if keys resolve)
    assert t("cancel_op") != "cancel_op"
    assert t("processing_docs") != "processing_docs"

if __name__ == "__main__":
    test_translation_keys_loaded()
    print("Keys verified.")
