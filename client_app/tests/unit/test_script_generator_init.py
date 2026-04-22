import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.script_generator_service import ScriptGeneratorService

@pytest.mark.asyncio
async def test_script_generator_initialization_once():
    """Verify that _get_client_and_license is only called once during multiple generation calls."""
    service = ScriptGeneratorService()
    
    # Mock _get_client_and_license to track calls
    with patch.object(service, "_get_client_and_license", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = (MagicMock(), "fake-key")
        
        # Mock other dependencies of generate_script to avoid side effects
        with patch("client_app.app.services.script_generator_service.get_security_policy", new_callable=AsyncMock) as mock_policy:
            mock_policy.return_value = MagicMock(allowed_imports="[]", forbidden_imports="[]")
            
            # First call should trigger _get_client_and_license
            await service.generate_script(user_prompt="test 1")
            assert mock_get.call_count == 1
            
            # Internal state should be updated
            assert service._initialized is True
            assert service._license_key == "fake-key"
            
            # Second call should use cached values
            await service.generate_script(user_prompt="test 2")
            assert mock_get.call_count == 1 # Still 1

@pytest.mark.asyncio
async def test_ensure_initialized_sets_state():
    """Verify that _ensure_initialized correctly sets the internal state."""
    service = ScriptGeneratorService()
    
    mock_client = MagicMock()
    with patch.object(service, "_get_client_and_license", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = (mock_client, "license-123")
        
        await service._ensure_initialized()
        
        assert service._initialized is True
        assert service._brain_client == mock_client
        assert service._license_key == "license-123"
        mock_get.assert_called_once()
