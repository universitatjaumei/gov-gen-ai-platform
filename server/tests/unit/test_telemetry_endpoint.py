import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from server.app.routers.telemetry_router import router, get_session
from server.app.database.models import ClientTelemetryLog

@pytest.mark.asyncio
async def test_sync_telemetry_success():
    # Setup Mocks
    mock_brain_service = MagicMock()
    mock_license = MagicMock()
    mock_license.client_id = "test_client_001"
    mock_brain_service._validate_license = AsyncMock(return_value=mock_license)
    
    mock_session = AsyncMock()
    async def override_get_session():
        yield mock_session

    with patch("server.app.routers.telemetry_router.AIBrainService", return_value=mock_brain_service):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_session] = override_get_session
        
        client = TestClient(app)
        
        payload = {
            "logs": [
                {
                    "execution_id": "exec_1",
                    "service_id": "svc_1",
                    "model_used": "gpt-4",
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "duration_ms": 100,
                    "status": "success",
                    "timestamp": "2023-01-01T12:00:00"
                }
            ]
        }
        
        # Test
        response = client.post(
            "/v1/telemetry/sync", 
            json=payload,
            headers={"x-license-key": "valid_key"}
        )
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["synced_count"] == 1
        
        # Verify DB interaction
        assert mock_session.add.call_count == 1
        assert mock_session.commit.call_count == 1
        
        # Verify mapped model
        args, _ = mock_session.add.call_args
        log_entry = args[0]
        assert isinstance(log_entry, ClientTelemetryLog)
        assert log_entry.client_id == "test_client_001"
        assert log_entry.manifest_id == "exec_1"
        assert log_entry.script_hash == "svc_1"
        assert log_entry.total_tokens == 30

@pytest.mark.asyncio
async def test_sync_telemetry_auth_fail():
    # Setup Failure Mock
    mock_brain_service = MagicMock()
    mock_brain_service._validate_license = AsyncMock(side_effect=ValueError("Invalid License"))
    
    with patch("server.app.routers.telemetry_router.AIBrainService", return_value=mock_brain_service):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        response = client.post(
            "/v1/telemetry/sync", 
            json={"logs": []},
            headers={"x-license-key": "invalid_key"}
        )
        
        assert response.status_code == 401
        assert "Invalid License" in response.json()["detail"]

@pytest.mark.asyncio
async def test_sync_telemetry_server_error():
    # Setup Exception Mock
    mock_brain_service = MagicMock()
    mock_brain_service._validate_license = AsyncMock(side_effect=Exception("DB Error"))
    
    with patch("server.app.routers.telemetry_router.AIBrainService", return_value=mock_brain_service):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        response = client.post(
            "/v1/telemetry/sync", 
            json={"logs": []},
            headers={"x-license-key": "valid_key"}
        )
        
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
