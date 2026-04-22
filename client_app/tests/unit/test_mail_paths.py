import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from client_app.app.modules.watchers.email_watcher import EmailWatcher

@pytest.fixture
def mock_path_manager():
    manager = MagicMock()
    # Mock create_run to return a deterministic execution_id
    manager.create_run.return_value = "run_test_001"
    # Mock get_input_dir to return a temp path
    manager.get_input_dir.return_value = Path("tmp/run_test_001/input")
    return manager

@pytest.fixture
def mock_workflow_engine():
    return MagicMock()

@pytest.fixture
def email_watcher(mock_path_manager, mock_workflow_engine):
    credentials = {"server": "imap.test.com", "user": "test@test.com", "password": "password"}
    return EmailWatcher(
        credentials=credentials,
        path_manager=mock_path_manager,
        workflow_engine=mock_workflow_engine,
        flow_id="flow_123"
    )

@pytest.mark.asyncio
async def test_process_email_creates_isolated_path(email_watcher, mock_path_manager, tmp_path):
    # Setup mock paths to use tmp_path
    exec_id = "run_2026_test"
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True)
    
    mock_path_manager.create_run.return_value = exec_id
    mock_path_manager.get_input_dir.return_value = input_dir
    
    email_data = {
        "sender": "sender@test.com",
        "subject": "Test subject",
        "attachments": [
            {"filename": "test.pdf", "data": b"fake pdf data"}
        ]
    }
    
    # We mock trigger_workflow to avoid DB calls in this unit test
    with patch.object(EmailWatcher, 'trigger_workflow', return_value=None) as mock_trigger:
        await email_watcher.process_email(email_data)
        
        # Verify ExecutionPathManager was used
        mock_path_manager.create_run.assert_called_once_with("EMAIL_TRIGGER")
        mock_path_manager.get_input_dir.assert_called_once_with(exec_id)
        
        # Verify file was written to the isolated path
        expected_file = input_dir / "test.pdf"
        assert expected_file.exists()
        assert expected_file.read_bytes() == b"fake pdf data"
        
        # Verify coordination with workflow trigger
        mock_trigger.assert_called_once()
        args, kwargs = mock_trigger.call_args
        assert args[0] == expected_file
        assert args[1] == "sender@test.com"
        # Optional: verify execution_id is passed if we decide to pass it explicitly
        assert kwargs.get('execution_id') == exec_id
