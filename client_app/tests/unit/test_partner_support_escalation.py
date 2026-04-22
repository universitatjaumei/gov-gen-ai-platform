import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from client_app.app.clients.brain_client import BrainAPIClient

@pytest.mark.asyncio
async def test_escalate_support_request_payload():
    """Verifica que el payload enviado al servidor de soporte sea correcto."""
    client = BrainAPIClient(base_url="http://test-server")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "ticket_id": "TKT-123"}
    
    mock_post = AsyncMock(return_value=mock_response)
    
    with patch('httpx.AsyncClient.post', mock_post):
        result = await client.escalate_support_request(
            asset_id=42,
            asset_type="custom_script",
            details={"prompt": "test prompt", "code": "print('hi')"},
            user_comment="I need help with this",
            license_key="TEST-KEY"
        )
        
        # Verificar llamada
        assert mock_post.called
        args, kwargs = mock_post.call_args
        
        assert args[0] == "http://test-server/api/brain/support/escalate"
        assert kwargs['json']['asset_id'] == 42
        assert kwargs['json']['asset_type'] == "custom_script"
        assert kwargs['json']['user_comment'] == "I need help with this"
        assert kwargs['headers']['X-License-Key'] == "TEST-KEY"
        
        assert result['ticket_id'] == "TKT-123"

@pytest.mark.asyncio
async def test_escalate_support_request_unauthorized():
    """Verifica el manejo de error 401."""
    client = BrainAPIClient(base_url="http://test-server")
    
    mock_response = MagicMock()
    mock_response.status_code = 401
    
    with patch('httpx.AsyncClient.post', AsyncMock(return_value=mock_response)):
        with pytest.raises(ValueError, match="Licencia no válida o expirada"):
            await client.escalate_support_request(
                asset_id=None,
                asset_type="test",
                details={},
                user_comment="help",
                license_key="INVALID"
            )
