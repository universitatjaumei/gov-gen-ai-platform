import pytest
import json
import os
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock
from client_app.app.services.script_library_service import script_library_service
from client_app.app.database.models import ScriptLibrary

@pytest.fixture
def mock_keys():
    private_key = b"-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQ..."
    public_key = b"-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA..."
    
    with patch("client_app.app.services.script_library_service.dev_crypto_service") as mock:
        mock.get_private_key.return_value = private_key
        mock.get_public_key.return_value = public_key
        yield mock

@pytest.fixture
def mock_state():
    with patch("client_app.app.services.script_library_service.state") as mock:
        mock.current_role = "partner"
        yield mock

@pytest.fixture
def mock_storage(tmp_path):
    src_dir = tmp_path / "src"
    docs_dir = tmp_path / "docs"
    src_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    with patch("client_app.app.services.script_library_service.SCRIPTS_DIR", src_dir), \
         patch("client_app.app.services.script_library_service.DOCS_DIR", docs_dir):
        yield {"src": src_dir, "docs": docs_dir}

@pytest.mark.asyncio
async def test_seal_script_requires_partner_role(mock_state, mock_keys, mock_storage):
    mock_state.current_role = "client"
    # Create a dummy script entry to test retrieval
    script = await script_library_service.add_script(
        source_module="custom", name="Test", code="pass"
    )
    
    with pytest.raises(PermissionError, match="Acceso denegado"):
        await script_library_service.seal_script(script.id)

@pytest.mark.asyncio
async def test_seal_script_generates_signed_manifest(mock_state, mock_keys, mock_storage):
    script = await script_library_service.add_script(
        source_module="custom", name="Test Manifest", code="print(123)"
    )
    
    with patch("client_app.app.services.script_library_service.rsa_signer.sign_payload") as mock_sign:
        mock_sign.return_value = b"signature_bytes"
        
        success = await script_library_service.seal_script(script.id)
        assert success is True
        
        manifest_path = mock_storage["src"] / f"{script.script_path}.signed.json"
        assert manifest_path.exists()
        
        manifest = json.loads(manifest_path.read_text())
        assert "payload" in manifest
        assert "signature" in manifest
        assert manifest["signature"] == base64.b64encode(b"signature_bytes").decode('utf-8')

@pytest.mark.asyncio
async def test_seal_script_updates_status(mock_state, mock_keys, mock_storage):
    script = await script_library_service.add_script(
        source_module="rpa", name="Test RPA", code="[]"
    )
    
    with patch("client_app.app.services.script_library_service.rsa_signer.sign_payload") as mock_sign:
        mock_sign.return_value = b"signature_bytes"
        
        await script_library_service.seal_script(script.id)
        
        # Verify status in DB
        updated = await script_library_service.get_script(script.id)
        assert updated.status == "validated"
