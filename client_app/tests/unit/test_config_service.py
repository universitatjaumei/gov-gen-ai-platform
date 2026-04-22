import os
import pytest
from pathlib import Path
from unittest.mock import patch
from client_app.app.services.config_service import ConfigService

def test_config_service_singleton():
    """Verify that ConfigService is a singleton."""
    c1 = ConfigService()
    c2 = ConfigService()
    assert c1 is c2

def test_config_service_paths():
    """Verify that paths are correctly resolved."""
    service = ConfigService()
    scripts_dir = service.get_path("CUSTOM_SCRIPTS_DIR")
    docs_dir = service.get_path("CUSTOM_DOCS_DIR")
    
    assert isinstance(scripts_dir, Path)
    assert scripts_dir.name == "src"
    assert docs_dir.name == "docs"
    assert "scripts" in str(scripts_dir)

def test_config_service_env_override():
    """Verify that STORAGE_ROOT can be overridden via environment."""
    with patch.dict(os.environ, {"STORAGE_ROOT": "C:\\CustomStorage"}):
        # We need to bypass the singleton for this test or re-initialize
        # Since it's a singleton, we might need a fresh instance for testing initialization
        instance = object.__new__(ConfigService)
        instance._initialize()
        
        scripts_dir = instance.get_path("CUSTOM_SCRIPTS_DIR")
        assert "CustomStorage" in str(scripts_dir)

def test_config_service_get_bool():
    """Verify boolean helper."""
    service = ConfigService()
    assert service.get_bool("SANDBOX_STRICT_MODE") is True
    assert service.get_bool("NON_EXISTENT") is False

def test_config_service_missing_key():
    """Verify behavior on missing keys."""
    service = ConfigService()
    with pytest.raises(KeyError):
        service.get_path("UNKNOWN_KEY")
    assert service.get("UNKNOWN_KEY", "default") == "default"
