
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.extraction_service import ExtractionService, LocalBrainClient
from client_app.app.clients.brain_client import BrainAPIClient

@pytest.mark.asyncio
async def test_get_brain_client_monolith_mode():
    """
    Verify that when state.brain is present, LocalBrainClient is returned.
    """
    mock_brain = MagicMock()
    
    # Mock state.brain
    with patch('client_app.app.services.extraction_service.state') as mock_state:
        mock_state.brain = mock_brain
        
        # Mock DB session for license key
        with patch('client_app.app.services.extraction_service.AsyncSession') as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            
            # Simulate NO active connection returned from DB -> triggers default logic?
            # Or assume we mock _get_active_license_key directly for simplicity
            service = ExtractionService()
            
            # Patch internal helper to avoid DB complexity
            with patch.object(service, '_get_active_license_key', return_value="demo_key_123"):
                client, key = await service._get_brain_client()
                
                assert isinstance(client, LocalBrainClient)
                assert client.brain == mock_brain
                # Verify license key fix for local dev
                assert key == "DEV_LICENSE_KEY_12345"

@pytest.mark.asyncio
async def test_get_brain_client_split_mode():
    """
    Verify that when state.brain is missing, BrainAPIClient is returned.
    """
    # Mock state.brain = None
    with patch('client_app.app.services.extraction_service.state') as mock_state:
        del mock_state.brain  # Ensure attribute missing or None
        
        service = ExtractionService()
        
        # Patch internal helper
        # If we return a valid key that demands split mode?
        # Actually split mode fallback happens if state.brain is missing.
        with patch.object(service, '_get_active_license_key', return_value="remote_key_abc"):
             # Mock DB session for fetching ServerConnection URL
            with patch('client_app.app.services.extraction_service.AsyncSession') as mock_session_cls:
                mock_session = AsyncMock()
                mock_session_cls.return_value.__aenter__.return_value = mock_session
                
                # Mock select result for ServerConnection
                mock_conn = MagicMock()
                mock_conn.brain_url = "http://remote-brain:8000"
                mock_session.get.return_value = mock_conn
                
                client, key = await service._get_brain_client()
                
                assert isinstance(client, BrainAPIClient)
                assert client.base_url == "http://remote-brain:8000"
                assert key == "remote_key_abc"

@pytest.mark.asyncio
async def test_local_brain_client_strips_license_key():
    """
    Verify that LocalBrainClient removes 'license_key' from kwargs before calling local service.
    """
    mock_brain_service = AsyncMock()
    adapter = LocalBrainClient(mock_brain_service)
    
    # define arguments
    args = ("doc1", "doc2")
    kwargs = {"option": "A", "license_key": "SHOULD_BE_REMOVED"}
    
    # Call adapter method
    await adapter.analyze_document_structure(*args, **kwargs)
    
    # Verify local brain called WITHOUT license_key
    mock_brain_service.analyze_document_structure.assert_called_once()
    call_args = mock_brain_service.analyze_document_structure.call_args
    assert "license_key" not in call_args.kwargs
    assert call_args.kwargs["option"] == "A"
