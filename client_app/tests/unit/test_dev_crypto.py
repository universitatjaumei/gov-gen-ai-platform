import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from client_app.app.services.dev_crypto_service import DevCryptoService

@pytest.fixture
def temp_keys_dir(tmp_path):
    keys_dir = tmp_path / "dev_keys"
    keys_dir.mkdir()
    return keys_dir

@pytest.fixture
def mock_config(temp_keys_dir):
    with patch("client_app.app.services.dev_crypto_service.config_service") as mock:
        mock.get_bool.side_effect = lambda key: {
            "DEBUG_MODE": True
        }.get(key, False)
        mock.get_path.side_effect = lambda key: {
            "DEV_KEYS_DIR": temp_keys_dir
        }.get(key)
        yield mock

def test_dev_crypto_generates_keys_if_missing(mock_config, temp_keys_dir):
    service = DevCryptoService()
    
    priv_path = temp_keys_dir / "private.pem"
    pub_path = temp_keys_dir / "public.pem"
    
    assert priv_path.exists()
    assert pub_path.exists()
    
    # Check content (starts with PEM header)
    assert priv_path.read_text().startswith("-----BEGIN PRIVATE KEY-----")
    assert pub_path.read_text().startswith("-----BEGIN PUBLIC KEY-----")

def test_dev_crypto_reuses_existing_keys(mock_config, temp_keys_dir):
    # First generation
    service1 = DevCryptoService()
    original_priv = (temp_keys_dir / "private.pem").read_text()
    
    # Reload service
    service2 = DevCryptoService()
    reloaded_priv = (temp_keys_dir / "private.pem").read_text()
    
    assert original_priv == reloaded_priv

def test_dev_crypto_returns_keys_correctly(mock_config, temp_keys_dir):
    service = DevCryptoService()
    
    pub_key = service.get_public_key()
    priv_key = service.get_private_key()
    
    assert isinstance(pub_key, bytes)
    assert isinstance(priv_key, bytes)
    assert pub_key.startswith(b"-----BEGIN PUBLIC KEY-----")
    assert priv_key.startswith(b"-----BEGIN PRIVATE KEY-----")

def test_dev_crypto_does_nothing_if_not_debug(temp_keys_dir):
    with patch("client_app.app.services.dev_crypto_service.config_service") as mock:
        mock.get_bool.side_effect = lambda key: {
            "DEBUG_MODE": False
        }.get(key, False)
        mock.get_path.side_effect = lambda key: {
            "DEV_KEYS_DIR": temp_keys_dir
        }.get(key)
        
        service = DevCryptoService()
        
        priv_path = temp_keys_dir / "private.pem"
        assert not priv_path.exists()
