import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from client_app.app.services.folder_watcher_service import FolderWatcherService
from client_app.app.database.models import FolderWatcherConfig, FolderWatcherState, ServerConnection, LocalCredentials

@pytest.mark.asyncio
async def test_check_all_paths_health_detects_disconnection(tmp_path):
    """
    Test that health check detects a missing directory, stops the watcher,
    and attempts to send an alert email.
    """
    service = FolderWatcherService()
    
    # 1. Setup mock data
    watch_dir = tmp_path / "to_watch"
    watch_dir.mkdir()
    
    config = FolderWatcherConfig(
        id=1,
        name="Test Watcher",
        watch_path=str(watch_dir),
        is_active=True,
        flow_id=1
    )
    
    server_conn = ServerConnection(
        id=1,
        client_email="client@example.com",
        partner_email="partner@example.com"
    )
    
    # Mock SMTP credentials
    smtp_creds = LocalCredentials(
        id=1,
        service_name="SMTP_Alerts",
        service_type="SMTP",
        encrypted_data='{"server": "smtp.test.com", "port": 587, "username": "alerts@test.com", "password": "password"}'
    )

    # 2. Mock service dependencies
    service._running_watchers = {1: MagicMock()} # Simulate running watcher
    service._workflow_engine = MagicMock()
    
    # Deleting the directory to simulate disconnection
    import shutil
    shutil.rmtree(watch_dir)
    
    # 3. Patching DB and EmailSender
    with patch("client_app.app.services.folder_watcher_service.AsyncSession") as mock_session_class, \
         patch("client_app.app.services.folder_watcher_service.EmailSender") as mock_email_sender_class, \
         patch("client_app.app.services.folder_watcher_service.get_machine_fingerprint") as mock_fp:
        
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        mock_fp.return_value = "TEST-MACHINE-ID"
        
        # Mocking DB queries
        # First query: FolderWatcherConfig (active)
        mock_result_configs = MagicMock()
        mock_result_configs.all.return_value = [config]
        
        # Second query: ServerConnection
        mock_result_server = MagicMock()
        mock_result_server.first.return_value = server_conn
        
        # Third query: LocalCredentials (SMTP)
        mock_result_creds = MagicMock()
        mock_result_creds.first.return_value = smtp_creds
        
        # Mocking session.exec calls in order
        mock_session.exec.side_effect = [mock_result_configs, mock_result_server, mock_result_creds]
        
        # Mocking singleton FolderWatcherState
        mock_state = FolderWatcherState(id=1)
        mock_result_state = MagicMock()
        mock_result_state.first.return_value = mock_state
        mock_session.exec.side_effect = [mock_result_configs, mock_result_server, mock_result_creds, mock_result_state]

        mock_email_instance = MagicMock()
        mock_email_sender_class.return_value = mock_email_instance
        
        # 4. Run health check
        await service.check_all_paths_health()
        
        # 5. Assertions
        assert config.is_active is False
        assert "no existe en el disco" in config.last_error
        assert 1 not in service._running_watchers
        
        # Verify email was sent
        mock_email_instance.send.assert_called_once()
        args, kwargs = mock_email_instance.send.call_args
        assert "client@example.com" in kwargs["to_addrs"]
        assert "partner@example.com" in kwargs["to_addrs"]
        assert "[ALERTA]" in kwargs["subject"]
        assert "TEST-MACHINE-ID" in kwargs["body"]
        assert kwargs["html"] is True
