
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.script_generator_service import ScriptGeneratorService
from client_app.app.clients.brain_client import BrainAPIClient

@pytest.mark.asyncio
async def test_sg_get_client_monolith_mode():
    """
    Verify that when state.brain is present, LocalBrainClient is returned.
    """
    mock_brain = MagicMock()
    
    # Mock state.brain
    with patch('client_app.app.services.script_generator_service.state') as mock_state:
        mock_state.brain = mock_brain
        
        # Mock DB session
        with patch('client_app.app.services.script_generator_service.AsyncSession') as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            
            # The service is singleton, but we can verify generic logic locally instantiated if needed
            # or patching the instance methods.
            service = ScriptGeneratorService()
            
            # We need to verify _get_client_and_license logic.
            # Currently it relies on direct DB access inside, so we mocked AsyncSession.
            
            # Mock session.get return for ServerConnection
            mock_conn = MagicMock()
            mock_conn.license_key = "demo_key_123"
            mock_session.get.return_value = mock_conn
            
            client, key = await service._get_client_and_license()
            
            # Verify class name via string because LocalBrainClient is inner class
            assert type(client).__name__ == "LocalBrainClient"
            assert client.brain == mock_brain
            assert key == "DEV_LICENSE_KEY_12345" # Fix logic

@pytest.mark.asyncio
async def test_sg_get_client_split_mode():
    """
    Verify that when state.brain is missing, BrainAPIClient is returned.
    """
    with patch('client_app.app.services.script_generator_service.state') as mock_state:
        mock_state.brain = None
        # Ensure hasattr returns False or attribute is None
        del mock_state.brain 
        
        with patch('client_app.app.services.script_generator_service.AsyncSession') as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            
            mock_conn = MagicMock()
            mock_conn.brain_url = "http://remote:3000"
            mock_conn.license_key = "prod_key"
            mock_session.get.return_value = mock_conn
            
            service = ScriptGeneratorService()
            client, key = await service._get_client_and_license()
            
            assert isinstance(client, BrainAPIClient)
            assert client.base_url == "http://remote:3000"
            assert key == "prod_key"

@pytest.mark.asyncio
async def test_local_brain_client_adapter():
    """
    Verify LocalBrainClient adapter maps calls correctly (legacy method support).
    ScriptGeneratorService uses 'generate_script' which maps to 'generate_text' in local brain.
    """
    # Import LocalBrainClient from the module locally or access via service instance if possible
    from client_app.app.services.script_generator_service import LocalBrainClient
    
    mock_brain = AsyncMock()
    mock_brain.generate_text.return_value = "def foo(): pass"
    
    adapter = LocalBrainClient(mock_brain)
    
    res = await adapter.generate_script(
        prompt="foo", 
        output_schema={}, 
        license_key="TEST"
    )
    
    assert res['success'] is True
    assert res['script'] == "def foo(): pass"
    # Verify underlying call
    mock_brain.generate_text.assert_called_once()
    assert mock_brain.generate_text.call_args.kwargs['prompt'] == "foo"
