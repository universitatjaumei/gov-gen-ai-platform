import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from types import SimpleNamespace
from client_app.app.services.folder_watcher_service import FolderWatcherService
from client_app.app.ui.custom_script_page import execute_test_logic

@pytest.mark.asyncio
async def test_folder_watcher_start_validation():
    """Verify that start_watcher validates path and flow_id."""
    service = FolderWatcherService()
    service.set_workflow_engine(MagicMock())
    
    # Mock DB session and config
    with patch("client_app.app.services.folder_watcher_service.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Chain mocks: await exec -> mock_result, then mock_result.first() -> mock_config
        # We use a regular MagicMock for the result since .first() is NOT async
        mock_result = MagicMock()
        mock_session.exec.return_value = mock_result
        
        # Case 1: Non-existent path
        mock_config = SimpleNamespace(
            id=1,
            name="Test",
            watch_path="C:\\non\\existent\\path",
            flow_id="flow_1",
            file_patterns="*",
            stabilization_seconds=2.0,
            recursive=False,
            is_active=False
        )
        mock_result.first.return_value = mock_config
        
        success, msg = await service.start_watcher(1)
        assert success is False
        assert "no existe" in msg.lower() or "no definida" in msg.lower()

        # Case 2: Missing flow_id
        # Use a path that exists for sure (current working directory)
        mock_config.watch_path = str(Path.cwd())
        mock_config.flow_id = None
        
        success, msg = await service.start_watcher(1)
        assert success is False
        assert "flujo" in msg.lower() or "flow" in msg.lower()

@pytest.mark.asyncio
async def test_custom_script_ui_unfreezes_on_error():
    """Verify that execute_test_logic resets is_executing even on failure."""
    wizard = SimpleNamespace(
        is_executing=False,
        generated_script={'code': 'print("hello")'},
        execution_result=None,
        execution_status=None,
        execution_error=None
    )
    refresh = MagicMock()
    
    # Mock sandbox to raise exception - use full path
    with patch("client_app.app.services.sandbox_service.SandboxExecutionService") as mock_sandbox_cls:
        mock_sandbox = AsyncMock()
        mock_sandbox.execute_in_sandbox.side_effect = Exception("Sandbox Crash")
        mock_sandbox_cls.return_value = mock_sandbox
        
        # Mock ExecutionPathManager too
        with patch("automatia_shared.core.execution_manager.ExecutionPathManager"):
            await execute_test_logic(wizard, "test.pdf", refresh)
            
            assert wizard.is_executing is False
            assert wizard.execution_status == 'error'
            assert "Sandbox Crash" in wizard.execution_error
            # Verify refresh was called at the end (one start, one finally)
            assert refresh.call_count >= 2
