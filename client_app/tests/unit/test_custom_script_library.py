
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from typing import List

# Mock dependencies to allow importing the library page module
mock_ui = MagicMock()
mock_state = MagicMock()
mock_service = MagicMock()

# We need to patch sys.modules before importing the module under test
# because it likely imports 'nicegui', 'state', etc. at top level.
with patch.dict(sys.modules, {
    "nicegui": mock_ui,
    "client_app.app.core.state": mock_state,
    "client_app.app.services.custom_script_service": mock_service,
}):
    # Now we can safely import (or we will import inside test if we want to be safer)
    pass

@pytest.fixture
def library_state():
    """Returns a fresh LibraryState instance."""
    # We patch modules again to ensure import works during fixture execution
    with patch.dict(sys.modules, {
        "nicegui": MagicMock(),
        "client_app.app.core.state": MagicMock(),
        "client_app.app.services.custom_script_service": MagicMock(),
    }):
        from client_app.app.ui.custom_script_library import LibraryState
        return LibraryState()

@pytest.mark.asyncio
async def test_library_initial_state(library_state):
    assert library_state.search_query == ""
    assert library_state.filter_status == "All"
    assert library_state.show_favorites_only is False
    assert isinstance(library_state.scripts, list)

@pytest.mark.asyncio
async def test_filtering_logic(library_state):
    """Test that filter_scripts returns correct subset."""
    # Mock data
    s1 = MagicMock(name="Script 1", description="Sales Report", is_favorite=True, status="validated")
    s1.name = "Sales Report"
    s1.description = "Analyze sales"
    
    s2 = MagicMock(name="Script 2", description="Backup", is_favorite=False, status="draft")
    s2.name = "Backup"
    s2.description = "System backup"
    
    library_state.scripts = [s1, s2]
    
    # Test Search
    library_state.search_query = "Sales"
    filtered = library_state.get_filtered_scripts()
    assert len(filtered) == 1
    assert filtered[0] == s1
    
    # Test Favorite Filter
    library_state.search_query = ""
    library_state.show_favorites_only = True
    filtered = library_state.get_filtered_scripts()
    assert len(filtered) == 1
    assert filtered[0] == s1
    
    # Test Status Filter (Reset fav first)
    library_state.show_favorites_only = False
    library_state.filter_status = "draft"
    filtered = library_state.get_filtered_scripts()
    assert len(filtered) == 1
    assert filtered[0] == s2

@pytest.mark.asyncio
async def test_load_scripts_action(library_state):
    """Test loading scripts from service."""
    mock_service_instance = MagicMock()
    mock_scripts = [MagicMock(id=1), MagicMock(id=2)]
    mock_service_instance.get_all_scripts = AsyncMock(return_value=mock_scripts)
    
    # We need to simulate the service call. 
    # Usually the page logic calls service. 
    # We will assume a 'load_scripts' method in State or Controller function.
    
    # We'll use sys.modules patching to mock the service module used by the code
    with patch.dict(sys.modules, {
        "client_app.app.services.custom_script_service": MagicMock(custom_script_service=mock_service_instance)
    }):
        from client_app.app.ui.custom_script_library import load_scripts_logic
        
        await load_scripts_logic(library_state)
        
        assert len(library_state.scripts) == 2
        assert library_state.scripts == mock_scripts
