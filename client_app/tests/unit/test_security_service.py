
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import json

from client_app.app.services.security_service import SecurityService
from client_app.app.database.models import ServerConnection

class TestSecurityService:
    
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.exec = AsyncMock()
        session.exec.return_value = MagicMock() # Return of await exec() must be MagicMock (Result object)
        session.add = MagicMock() # Sync method
        return session

    @pytest.fixture
    def mock_brain_client(self):
        with patch("client_app.app.clients.brain_client.BrainAPIClient") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield client_instance

    @pytest.fixture
    def mock_rsa_signer(self):
        with patch("client_app.app.services.security_service.RSASigner") as mock:
            instance = MagicMock()
            instance.verify_signature.return_value = True
            mock.return_value = instance
            # Mock static method
            mock.canonicalize_json.return_value = b'{}' 
            yield mock

    @pytest.fixture
    def mock_policy_manager(self):
        with patch("client_app.app.services.security_service.PartnerPolicyManager") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_sync_policy_success(self, mock_session, mock_brain_client, mock_rsa_signer, tmp_path):
        """Test successful policy sync from server."""
        # Setup
        service = SecurityService(mock_session)
        service.CACHE_FILE = tmp_path / "security_policy.json"
        
        # Mock active connection
        mock_connection = MagicMock(spec=ServerConnection)
        mock_connection.brain_url = "http://test"
        mock_connection.license_key = "test_key"
        mock_connection.partner_public_key = "public_key"
        
        mock_session.exec.return_value.first.return_value = mock_connection
        
        # Mock API response
        policy_payload = {
            "policy": {"max_execution_time": 600},
            "signature": "valid_sig"
        }
        mock_brain_client.return_value.get_effective_policy.return_value = policy_payload
        
        # Act
        await service.sync_policy_from_server()
        
        # Assert
        # 1. Verify API called
        mock_brain_client.return_value.get_effective_policy.assert_called_once_with("test_key")
        
        # 2. Verify Cache created
        assert service.CACHE_FILE.exists()
        with open(service.CACHE_FILE) as f:
            data = json.load(f)
            assert data == policy_payload
            
        # 3. Verify DB updated
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_offline_fallback(self, mock_session, mock_brain_client, mock_rsa_signer, mock_policy_manager, tmp_path):
        """Test fallback to cache when server is unreachable."""
        # Setup
        service = SecurityService(mock_session)
        service.CACHE_FILE = tmp_path / "security_policy.json"
        service.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Create existing cache
        cached_policy = {
            "policy": {"max_execution_time": 120},
            "signature": "cached_sig"
        }
        with open(service.CACHE_FILE, 'w') as f:
            json.dump(cached_policy, f)
            
        # Mock Connection (needed for public key to verify cache)
        mock_connection = MagicMock(spec=ServerConnection)
        mock_connection.partner_public_key = "public_key"
        mock_session.exec.return_value.first.return_value = mock_connection

        # Mock API Failure
        mock_brain_client.return_value.get_effective_policy.side_effect = Exception("Network Error")
        
        # Act
        await service.initialize_security()
        
        # Assert
        # Verify PolicyManager was initialized with cached policy
        mock_policy_manager.assert_called()
        _, kwargs = mock_policy_manager.call_args
        assert kwargs['client_policy'] == cached_policy['policy']

    @pytest.mark.asyncio
    async def test_invalid_signature_blocks_policy(self, mock_session, mock_brain_client, mock_rsa_signer, mock_policy_manager, tmp_path):
        """Test that invalid signature prevents policy application."""
        # Setup
        service = SecurityService(mock_session)
        service.CACHE_FILE = tmp_path / "security_policy.json"
        
        # Mock active connection
        mock_connection = MagicMock(spec=ServerConnection)
        mock_connection.partner_public_key = "public_key"
        mock_session.exec.return_value.first.return_value = mock_connection
        
        # Mock API response
        policy_payload = {
            "policy": {"max_execution_time": 9999}, # Malicious policy
            "signature": "bad_sig"
        }
        mock_brain_client.return_value.get_effective_policy.return_value = policy_payload
        
        # Mock Signature Failure
        mock_rsa_signer.return_value.verify_signature.return_value = False
        
        # Act & Assert
        with pytest.raises(ValueError, match="signature verification failed"):
            await service.sync_policy_from_server()
            
        # Verify DB NOT updated
        mock_session.add.assert_not_called()
