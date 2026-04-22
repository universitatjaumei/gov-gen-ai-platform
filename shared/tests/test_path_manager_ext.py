
import os
import shutil
import pytest
from pathlib import Path
from automatia_shared.core.execution_manager import ExecutionPathManager

@pytest.fixture
def mock_env_storage(monkeypatch, tmp_path):
    """Mock STORAGE_ROOT environment variable."""
    storage_root = tmp_path / "mock_storage"
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    return storage_root

def test_initialization_with_env_var(mock_env_storage):
    """Test that manager respects STORAGE_ROOT env var."""
    manager = ExecutionPathManager()
    assert manager.base_dir == mock_env_storage
    assert manager.get_automations_dir() == mock_env_storage / "automations"
    assert manager.get_scripts_dir() == mock_env_storage / "automations" / "scripts"
    assert manager.get_uploads_dir() == mock_env_storage / "uploads"

def test_directory_creation(mock_env_storage):
    """Test that directories are automatically created."""
    manager = ExecutionPathManager()
    
    assert (mock_env_storage / "automations").exists()
    assert (mock_env_storage / "automations" / "scripts").exists()
    assert (mock_env_storage / "automations" / "docs").exists()
    assert (mock_env_storage / "uploads").exists()
    assert (mock_env_storage / "tmp").exists()
    assert (mock_env_storage / "executions").exists()

def test_default_path_fallback(monkeypatch):
    """Test fallback to default if STORAGE_ROOT is not set."""
    monkeypatch.delenv("STORAGE_ROOT", raising=False)
    # We pass a test app name to avoid polluting real user data
    manager = ExecutionPathManager(app_name="test_suite_automatia")
    
    expected_base = Path.home() / "test_suite_automatia" / "data"
    assert manager.base_dir == expected_base
    
    # Cleanup
    if expected_base.exists():
        shutil.rmtree(expected_base.parent)

def test_path_accessors(mock_env_storage):
    """Test public accessor methods."""
    manager = ExecutionPathManager()
    
    assert isinstance(manager.get_automations_dir(), Path)
    assert manager.get_automations_dir().name == "automations"
    
    assert isinstance(manager.get_scripts_dir(), Path)
    assert manager.get_scripts_dir().name == "scripts"
    
    assert isinstance(manager.get_docs_dir(), Path)
    assert manager.get_docs_dir().name == "docs"
    
    assert isinstance(manager.get_uploads_dir(), Path)
    assert manager.get_uploads_dir().name == "uploads"
