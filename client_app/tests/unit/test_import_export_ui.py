
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from client_app.app.ui.import_export_page import PackagesPageState

@pytest.fixture
def state():
    return PackagesPageState()

def test_initial_state(state):
    # Export state
    assert len(state.selected_scripts) == 0
    assert state.package_name == ""
    
    # Import state
    assert state.uploaded_file is None
    assert state.validation_result is None
    assert state.import_result is None

def test_export_validation(state):
    assert not state.can_export()
    state.selected_scripts.add(1)
    assert not state.can_export() # Needs name
    state.package_name = "Test Package"
    assert state.can_export()

def test_import_reset(state):
    state.uploaded_file = b"content"
    state.validation_result = MagicMock()
    state.reset_import()
    assert state.uploaded_file is None
    assert state.validation_result is None
