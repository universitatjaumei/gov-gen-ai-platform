import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from automatia_shared.dtos import TaskSpec
from client_app.app.modules.runtime.workflow_engine import execute_email_send

@pytest.mark.asyncio
async def test_workflow_executes_email_step():
    """Verifica que el paso email_send recupera credenciales y llama a EmailSender."""
    
    # Mock context
    context = {"execution_dir": "/tmp/exec"}
    
    # Mock Task Config
    task = TaskSpec(
        name="Send Email",
        type="email_send",
        config={
            "credential_id": 123,
            "to": ["test@example.com"],
            "subject": "Test Subject",
            "body": "Test Body",
            "attach_previous_output": False
        }
    )
    
    # Mocks
    with patch("client_app.app.modules.runtime.workflow_engine.mail_watcher_service") as mock_service, \
         patch("client_app.app.modules.runtime.workflow_engine.EmailSender") as MockSender:
         
        # Mock get_credential
        mock_service.get_credential = AsyncMock(return_value={
            "server": "smtp.test", "port": 587, "user": "u", "password": "p"
        })
        
        # Mock EmailSender instance
        mock_sender_instance = MockSender.return_value
        mock_sender_instance.send_with_file_attachments.return_value = "msg-123"
        
        # Execute
        result = await execute_email_send(task, context)
        
        # Verify
        mock_service.get_credential.assert_awaited_with(123)
        MockSender.assert_called_once()
        mock_sender_instance.send_with_file_attachments.assert_called_with(
            from_addr="u",
            to_addrs=["test@example.com"],
            subject="Test Subject",
            body="Test Body",
            html=False,
            file_paths=[]
        )
        assert result == "msg-123"

@pytest.mark.asyncio
async def test_workflow_email_attaches_previous_output():
    """Verifica adjuntar archivo desde output anterior."""
    
    context = {
        "execution_dir": "/tmp/exec",
        "previous_output": "/tmp/exec/report.xlsx"
    }
    
    task = TaskSpec(
        name="Send Email",
        type="email_send",
        config={
            "credential_id": 1,
            "to": ["t@e.com"],
            "subject": "s",
            "body": "b",
            "attach_previous_output": True
        }
    )
    
    with patch("client_app.app.modules.runtime.workflow_engine.mail_watcher_service") as mock_service, \
         patch("client_app.app.modules.runtime.workflow_engine.EmailSender") as MockSender, \
         patch("pathlib.Path.exists", return_value=True), \
         patch("client_app.app.modules.runtime.workflow_engine.is_safe_path", return_value=True):
         
        mock_service.get_credential = AsyncMock(return_value={"user": "u"})
        mock_sender_instance = MockSender.return_value
        mock_sender_instance.send_with_file_attachments.return_value = "ok"
        
        await execute_email_send(task, context)
        
        # Verify send_with_file_attachments called
        args = mock_sender_instance.send_with_file_attachments.call_args
        assert args is not None
        # Check file_paths arg
        file_paths = args.kwargs.get('file_paths')
        assert len(file_paths) == 1
        # Use Path comparison for OS independence
        assert Path(file_paths[0]) == Path("/tmp/exec/report.xlsx")

@pytest.mark.asyncio
async def test_workflow_fails_unsafe_path():
    """Verifica que falla si el archivo está fuera del directorio seguro."""
    
    context = {
        "execution_dir": "/tmp/exec",
        "previous_output": "/etc/passwd"  # Unsafe
    }
    
    task = TaskSpec(
        name="Send Email",
        type="email_send",
        config={
            "credential_id": 1,
            "to": ["t@e.com"],
            "subject": "s", 
            "body": "b",
            "attach_previous_output": True
        }
    )
    
    # Needs to patch Path.exists to true for unsafe path too to reach the check
    with patch("client_app.app.modules.runtime.workflow_engine.mail_watcher_service") as mock_service, \
         patch("pathlib.Path.exists", return_value=True), \
         patch("client_app.app.modules.runtime.workflow_engine.is_safe_path", return_value=False):
         
        mock_service.get_credential = AsyncMock(return_value={"user": "u"})
        
        with pytest.raises(RuntimeError, match="Security Error"):
            await execute_email_send(task, context)
