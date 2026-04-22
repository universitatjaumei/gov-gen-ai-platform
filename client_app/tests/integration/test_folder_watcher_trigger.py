import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from client_app.app.modules.watchers.folder_watcher import FolderWatcher

@pytest.mark.asyncio
async def test_folder_watcher_trigger_flow_spec():
    """
    Verify that FolderWatcher fetches the FlowSpec from DB and 
    calls workflow_engine.execute_flow with it.
    """
    # Setup
    mock_engine = AsyncMock()
    mock_watch_dir = Path("/tmp/test_folder")
    flow_id = 999
    
    watcher = FolderWatcher(
        watch_directory=mock_watch_dir,
        workflow_engine=mock_engine,
        flow_id=str(flow_id)
    )
    
    # Mock DB objects
    mock_flow_db = MagicMock()
    mock_flow_db.id = flow_id
    mock_flow_db.name = "Folder Flow"
    mock_flow_db.steps = '[{"name": "step1", "type": "extraction", "config": {}}]' # JSON string
    mock_flow_db.trigger_config = '{}'
    mock_flow_db.version = "1.0.0"
    mock_flow_db.status = "PUBLISHED"
    mock_flow_db.row_version = 1
    mock_flow_db.trigger_type = "file" # Changed from "folder" to "file"
    mock_flow_db.is_active = True
    mock_flow_db.owner_scope = None
    mock_flow_db.description = "Folder monitoring flow"

    # Mock wait_for_stability
    watcher._wait_for_stability = AsyncMock(return_value=True)

    # Patch AsyncSession in folder_watcher
    with patch("client_app.app.modules.watchers.folder_watcher.AsyncSession") as MockSessionClass:
        mock_session = AsyncMock()
        MockSessionClass.return_value.__aenter__.return_value = mock_session
        mock_session.get.return_value = mock_flow_db
        
        dummy_file = Path("/tmp/test_folder/invoice.pdf")
        
        await watcher._process_file(dummy_file)
    
    # Assert
    mock_engine.execute_flow.assert_awaited_once()
    args, kwargs = mock_engine.execute_flow.call_args
    
    flow_arg = kwargs.get('flow') or args[0] # Updated code uses 'flow' kwarg or first arg
        
    # Check FlowSpec
    assert not isinstance(flow_arg, str), f"Expected FlowSpec object, got string '{flow_arg}'"
    assert flow_arg.name == "Folder Flow"
    assert len(flow_arg.steps) == 1
    assert flow_arg.steps[0].name == "step1"

