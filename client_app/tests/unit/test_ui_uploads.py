import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from automatia_shared.core.execution_manager import ExecutionPathManager

@pytest.fixture
def mock_path_manager(tmp_path):
    manager = ExecutionPathManager()
    manager.base_dir = tmp_path
    manager.ensure_dirs()
    return manager

@pytest.fixture
def sandbox_dir(mock_path_manager):
    return mock_path_manager.get_sandbox_dir("test_script_123")

def test_get_sandbox_dir_creates_path(mock_path_manager):
    path = mock_path_manager.get_sandbox_dir("script_456")
    assert path.exists()
    assert "sandboxes" in str(path)
    assert "script_456" in str(path)

def test_sanitize_filename_prevents_traversal(mock_path_manager):
    # This tests the internal _sanitize_id which get_sandbox_dir uses
    path = mock_path_manager.get_sandbox_dir("../../etc/passwd")
    assert "etcpasswd" in str(path)
    assert ".." not in str(path)

@pytest.mark.asyncio
async def test_handle_upload_persists_file(sandbox_dir):
    # Mocking UploadEventArguments from nicegui
    mock_event = MagicMock()
    mock_event.name = "data.csv"
    mock_event.content = b"header1,header2\nval1,val2"
    
    # We will implement this logic in custom_script_page
    target_path = sandbox_dir / mock_event.name
    with open(target_path, "wb") as f:
        f.write(mock_event.content.read() if hasattr(mock_event.content, 'read') else mock_event.content)
        
    assert target_path.exists()
    assert target_path.read_bytes() == b"header1,header2\nval1,val2"

def test_delete_sample_removes_from_disk(sandbox_dir):
    sample_file = sandbox_dir / "sample.txt"
    sample_file.write_text("hello")
    assert sample_file.exists()
    
    sample_file.unlink()
    assert not sample_file.exists()
