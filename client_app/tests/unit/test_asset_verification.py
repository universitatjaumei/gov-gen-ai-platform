import pytest
import json
import os
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock
from client_app.app.services.script_library_service import script_library_service
from client_app.app.database.models import ScriptLibrary

@pytest.fixture
def mock_storage(tmp_path):
    src_dir = tmp_path / "src"
    docs_dir = tmp_path / "docs"
    src_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    with patch("client_app.app.services.script_library_service.SCRIPTS_DIR", src_dir), \
         patch("client_app.app.services.script_library_service.DOCS_DIR", docs_dir):
        yield {"src": src_dir, "docs": docs_dir}

@pytest.fixture
async def signed_script(mock_storage):
    # Setup keys and state to sign
    with patch("client_app.app.services.script_library_service.state") as mock_state:
        mock_state.current_role = "partner"
        
        # Add script
        script = await script_library_service.add_script(
            source_module="custom", name="Verified Script", code="print('secure')"
        )
        
        # Sign it
        with patch("client_app.app.services.script_library_service.rsa_signer.sign_payload") as mock_sign:
            mock_sign.return_value = b"valid_signature"
            await script_library_service.seal_script(script.id)
            return script

@pytest.mark.asyncio
async def test_verify_asset_seal_no_manifest_returns_true(mock_storage):
    script = await script_library_service.add_script(
        source_module="custom", name="Unsigned", code="pass"
    )
    # No manifest exists
    success = await script_library_service.verify_asset_seal(script.id)
    assert success is True

@pytest.mark.asyncio
async def test_verify_asset_seal_valid_signature(signed_script, mock_storage):
    with patch("client_app.app.services.script_library_service.rsa_signer.verify_signature") as mock_verify:
        mock_verify.return_value = True
        
        success = await script_library_service.verify_asset_seal(signed_script.id)
        assert success is True

@pytest.mark.asyncio
async def test_verify_asset_seal_tampered_code(signed_script, mock_storage):
    # Alter the code on disk
    src_path = mock_storage["src"] / signed_script.script_path
    src_path.write_text("print('tampered')")
    
    with pytest.raises(ValueError, match="Integridad violada"):
        await script_library_service.verify_asset_seal(signed_script.id)

@pytest.mark.asyncio
async def test_verify_asset_seal_invalid_signature(signed_script, mock_storage):
    with patch("client_app.app.services.script_library_service.rsa_signer.verify_signature") as mock_verify:
        mock_verify.return_value = False # Signature mismatch
        
        with pytest.raises(ValueError, match="Firma inválida"):
            await script_library_service.verify_asset_seal(signed_script.id)
