import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from client_app.app.modules.watchers.email_watcher import EmailWatcher

@pytest.mark.asyncio
async def test_email_watcher_trigger_flow_spec():
    """
    Verify that EmailWatcher fetches the FlowSpec from DB and 
    calls workflow_engine.execute_flow with it.
    """
    # Setup
    mock_engine = AsyncMock()
    mock_base_dir = Path("/tmp/test_watcher")
    flow_id = 123
    
    watcher = EmailWatcher(
        credentials={},
        base_dir=mock_base_dir,
        workflow_engine=mock_engine,
        flow_id=str(flow_id)
    )
    
    # Mock DB objects
    mock_flow_db = MagicMock()
    mock_flow_db.id = flow_id
    mock_flow_db.name = "Test Flow"
    mock_flow_db.steps = '[{"name": "step1", "type": "extraction", "config": {}}]' # JSON string
    mock_flow_db.trigger_config = '{}'
    mock_flow_db.version = "1.0.0"
    mock_flow_db.status = "PUBLISHED"
    mock_flow_db.row_version = 1
    mock_flow_db.trigger_type = "email"
    mock_flow_db.is_active = True
    mock_flow_db.owner_scope = None
    mock_flow_db.description = "desc"

    # Mock Session and Engine
    # We need to patch client_engine and AsyncSession where they are imported/used
    with patch("client_app.app.services.mail_watcher_service.client_engine") as mock_client_engine: # Not used? EmailWatcher uses imported client_engine
         # Actually EmailWatcher imports client_engine directly. 
         # We should patch 'client_app.app.modules.watchers.email_watcher.client_engine' (if we imported it)
         # or simpler: patch the AsyncSession context manager.
         pass
         
    with patch("client_app.app.modules.watchers.email_watcher.AsyncSession") as MockSessionClass:
        mock_session = AsyncMock()
        MockSessionClass.return_value.__aenter__.return_value = mock_session
        mock_session.get.return_value = mock_flow_db
        
        # Act
        dummy_file = Path("test.pdf")
        sender = "test@example.com"
        
        await watcher.trigger_workflow(dummy_file, sender)
        
        # Assert
        mock_engine.execute_flow.assert_awaited_once()
        args, kwargs = mock_engine.execute_flow.call_args
        
        flow_arg = args[0]
        context_arg = kwargs.get('context') or args[1]
        
        # Check FlowSpec
        # It should be an object (FlowSpec instance), not string
        assert not isinstance(flow_arg, str)
        assert flow_arg.name == "Test Flow"
        assert len(flow_arg.steps) == 1
        assert flow_arg.steps[0].name == "step1"
        
        # Check Context
        assert context_arg['trigger'] == "email"
        assert context_arg['input_file'] == str(dummy_file)
