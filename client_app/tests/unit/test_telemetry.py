
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from client_app.app.services.sync_service import sync_service, SyncService
from client_app.app.clients.brain_client import BrainAPIClient
from client_app.app.database.models import RunManifestLog

@pytest.mark.asyncio
async def test_log_run_manifest_mocked():
    """Verify logging logic using mocks without real DB engine."""
    
    execution_id = str(uuid.uuid4())
    
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    # Mock get_db context manager
    class MockDbContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, exc_type, exc, tb):
            pass

    with patch("client_app.app.services.sync_service.get_db", return_value=MockDbContext()):
        log = await sync_service.log_run_manifest(
            execution_id=execution_id,
            service_id="test_service",
            model_used="gpt-test",
            prompt_tokens=10,
            completion_tokens=20,
            duration_ms=100,
            status="success"
        )
        
        assert log is not None
        assert log.execution_id == execution_id
        assert log.total_tokens == 30
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_sync_manifests_to_server_mocked():
    """Verify syncing logic with mocks."""
    
    # Mock DB results
    mock_log = RunManifestLog(
        execution_id="e1", 
        service_id="s1", 
        model_used="m1", 
        prompt_tokens=10, 
        created_at=datetime.utcnow()
    )
    
    mock_conn = MagicMock()
    mock_conn.brain_url = "http://test"
    mock_conn.license_key = "key"
    mock_conn.is_active = True
    
    mock_session = AsyncMock()
    # First query (logs): return [mock_log]
    # Second query (conn): return [mock_conn]
    
    mock_result_logs = MagicMock()
    mock_result_logs.all.return_value = [mock_log]
    
    mock_result_conn = MagicMock()
    mock_result_conn.first.return_value = mock_conn
    
    # Side effects for exec calls
    mock_session.exec.side_effect = [mock_result_logs, mock_result_conn]
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    class MockDbContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, exc_type, exc, tb):
            pass
            
    with patch("client_app.app.services.sync_service.BrainAPIClient") as MockClientClass:
        mock_client = AsyncMock()
        MockClientClass.return_value = mock_client
        mock_client.post_generic.return_value = {"status": "success"}

        with patch("client_app.app.services.sync_service.get_db", return_value=MockDbContext()):
            await sync_service.sync_manifests_to_server(batch_size=10)
            
            # Verify client called
            mock_client.post_generic.assert_called_once()
            _, kwargs = mock_client.post_generic.call_args
            assert kwargs['endpoint'] == "/api/v1/telemetry/sync"
            assert len(kwargs['json_data']['logs']) == 1
            
            # Verify log updated
            assert mock_log.is_synced is True
            mock_session.commit.assert_called()

@pytest.mark.asyncio
async def test_brain_client_instrumentation_mocked():
    """Verify BrainAPIClient calls log_telemetry using mocks."""
    
    client = BrainAPIClient()
    
    with patch("client_app.app.services.sync_service.sync_service.log_run_manifest", new_callable=AsyncMock) as mock_log:
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "script": "ok", 
                "usage": {"prompt_tokens": 5, "completion_tokens": 5}
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            await client.generate_script(
                prompt="test",
                output_schema={},
                license_key="key"
            )
            
            mock_log.assert_called_once()
            _, kwargs = mock_log.call_args
            assert kwargs['service_id'] == "generate_script"
            assert kwargs['prompt_tokens'] == 5
