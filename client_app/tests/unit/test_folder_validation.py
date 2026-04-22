import pytest
import os
from unittest.mock import MagicMock, patch, AsyncMock
from client_app.app.services.folder_watcher_service import FolderWatcherService
from client_app.app.database.models import FolderWatcherConfig

@pytest.mark.asyncio
async def test_create_config_with_invalid_path():
    """Verify that creating a config with a non-existent path raises a ValueError."""
    service = FolderWatcherService()
    
    invalid_data = {
        "name": "Test Inexistente",
        "watch_path": "C:\\this\\path\\does\\not\\exist\\at\\all\\12345",
        "flow_id": 1
    }
    
    # We expect ValueError because the path doesn't exist
    with pytest.raises(ValueError, match="La ruta especificada no existe"):
        await service.create_config(invalid_data)

@pytest.mark.asyncio
async def test_start_watcher_with_deleted_path(tmp_path):
    """Verify that starting a watcher fails if the path was deleted after configuration."""
    service = FolderWatcherService()
    
    # Create a real temp path
    watch_dir = tmp_path / "to_watch_999"
    watch_dir.mkdir()
    
    # Mock necessary parts for start_watcher
    service._workflow_engine = MagicMock()
    
    mock_config = FolderWatcherConfig(
        id=999,
        name="Test Deleted Path",
        watch_path=str(watch_dir),
        flow_id=1
    )
    
    # Simulating deletion
    import shutil
    shutil.rmtree(watch_dir)
    
    # Mocking the DB session and query results
    with patch("client_app.app.services.folder_watcher_service.AsyncSession") as mock_session_class:
        # Create an instance mock
        mock_instance = MagicMock()
        mock_session_class.return_value = mock_instance
        
        # Async context manager setup
        mock_session = AsyncMock()
        mock_instance.__aenter__.return_value = mock_session
        mock_instance.__aexit__.return_value = False
        
        # Mocking session.exec(stmt).first()
        mock_result = MagicMock()
        mock_result.first.return_value = mock_config
        mock_session.exec.return_value = mock_result
        
        success, message = await service.start_watcher(999)
        
        assert success is False
        assert "no existe en el disco" in message
