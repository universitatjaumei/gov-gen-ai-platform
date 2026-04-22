
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from server.app.api.v1.brain import router
from fastapi.testclient import TestClient
from server.app.main import app # Assuming app is importable, otherwise we build a test app

# We need to mock dependencies before importing/testing
@pytest.mark.asyncio
async def test_generate_script_records_consumption():
    """
    Verifica que al llamar a /generate_script se invoca al BillingEngine.
    """
    # Mocks
    mock_billing_engine = AsyncMock()
    mock_ejecutar_tarea = AsyncMock(return_value={
        "response": "print('Hello')",
        "tokens_used": 150,
        "model_used": "gpt-4-turbo"
    })
    
    mock_brain_service = MagicMock()
    mock_brain_service._validate_license = AsyncMock(return_value=MagicMock(client_id="client_123"))
    mock_brain_service._resolve_server_config = AsyncMock(return_value=({}, "System Prompt"))
    
    # Patching
    with patch("server.app.api.v1.brain.billing_engine", mock_billing_engine), \
         patch("server.app.api.v1.brain.ejecutar_tarea", mock_ejecutar_tarea), \
         patch("server.app.api.v1.brain.AIBrainService", return_value=mock_brain_service):
         
        # Simulate request
        # Note: We are testing the API logic directly or via TestClient. 
        # Using direct function call might be easier if we can import the handler, but TestClient is more integration-like.
        
        # Simulating logic flow inside the endpoint:
        from server.app.api.v1.brain import generate_script, GenerateScriptRequest
        
        req = GenerateScriptRequest(prompt="Test", output_schema={})
        await generate_script(req, x_license_key="valid_key")
        
        # Assertions
        mock_billing_engine.record_consumption.assert_called_once()
        
        # Check arguments
        call_args = mock_billing_engine.record_consumption.call_args
        assert call_args is not None
        _, kwargs = call_args
        
        assert kwargs["client_id"] == "client_123"
        assert kwargs["tokens"] == 150
        assert kwargs["model"] == "gpt-4-turbo"
        assert kwargs["operation_type"] == "generate_script"
