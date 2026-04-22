import pytest
import json
import zipfile
from io import BytesIO
from unittest.mock import AsyncMock, patch
from client_app.app.services.import_validation_service import ImportValidationService, ImportPermission

@pytest.mark.asyncio
async def test_validate_package_rejects_partner_hmac():
    """
    Verify that a package with signature type PARTNER but algorithm HMAC is rejected.
    This prevents 'downgrade' attacks where a partner package is signed with a client key.
    """
    service = ImportValidationService()
    
    # Create a mock manifest with PARTNER signature but HMAC algorithm
    manifest = {
        "version": "1.0.0",
        "name": "Evil Package",
        "source": {
            "partner_id": "PARTNER-ABC",
            "license_id": "LIC-123"
        },
        "contents": {"scripts": []},
        "file_hashes": {},
        "signature": {
            "type": "PARTNER",
            "algorithm": "HMAC-SHA256",
            "value": "fake-signature"
        }
    }
    
    # Create a minimal ZIP in memory
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('manifest.json', json.dumps(manifest))
    
    package_bytes = buf.getvalue()
    
    # Mock dependencies
    with patch("client_app.app.services.import_validation_service.AsyncSession"):
        with patch.object(service, "_get_local_license_id", return_value="LIC-OTHER"):
            with patch.object(service, "_get_local_partner_id", return_value="PARTNER-OTHER"):
                
                result = await service.validate_package(package_bytes)
                
                assert result.is_valid is False
                assert any("Firma del manifiesto invalida" in err for err in result.errors)

@pytest.mark.asyncio
async def test_validate_package_allows_partner_rsa():
    """Verify that PARTNER signature with RSA (non-HMAC) is allowed to proceed to Brain verification."""
    service = ImportValidationService()
    
    manifest = {
        "version": "1.0.0",
        "name": "Good Package",
        "source": {
            "partner_id": "PARTNER-ABC",
            "license_id": "LIC-123"
        },
        "contents": {"scripts": []},
        "file_hashes": {},
        "signature": {
            "type": "PARTNER",
            "algorithm": "RSA-SHA256",
            "value": "fake-rsa-signature"
        }
    }
    
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('manifest.json', json.dumps(manifest))
    
    package_bytes = buf.getvalue()
    
    # Mock signature service to return True
    with patch.object(service._signature_service, "verify_partner_signature", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True
        
        with patch("client_app.app.services.import_validation_service.AsyncSession"):
            with patch.object(service, "_get_local_license_id", return_value="LIC-OTHER"):
                with patch.object(service, "_get_local_partner_id", return_value="PARTNER-ABC"): # Same partner
                    
                    result = await service.validate_package(package_bytes)
                    
                    assert result.is_valid is True
                    assert result.permission == ImportPermission.REQUIRES_PARTNER
                    mock_verify.assert_called_once()
