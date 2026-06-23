import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from server.app.routers.library_router import SignManifestRequest, sign_manifest


@pytest.mark.asyncio
async def test_sign_manifest_success():
    # Mock manifest_signature_service
    mock_sig_service = MagicMock()
    mock_sig_service.get_signable_fields.return_value = {"id": "test_id", "partner_id": "p_001"}
    mock_sig_service.sign_manifest.return_value = "mock_signature_base64"

    with patch("server.app.routers.library_router.manifest_signature_service", mock_sig_service):
        manifest_data = {"id": "test_id", "content": "print('hello')"}
        request = SignManifestRequest(
            manifest_json=json.dumps(manifest_data),
            partner_id="p_001",
        )

        result = await sign_manifest(request)

        assert result["signature"] == "mock_signature_base64"
        assert result["algorithm"] == "RSA-SHA256"
        assert result["partner_id"] == "p_001"


@pytest.mark.asyncio
async def test_sign_manifest_invalid_json():
    request = SignManifestRequest(
        manifest_json="invalid json {",
        partner_id="p_001",
    )

    with pytest.raises(HTTPException) as exc:
        await sign_manifest(request)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_sign_manifest_missing_id():
    manifest_data = {"content": "no id"}
    request = SignManifestRequest(
        manifest_json=json.dumps(manifest_data),
        partner_id="p_001",
    )

    with pytest.raises(HTTPException) as exc:
        await sign_manifest(request)
    assert exc.value.status_code == 500  # ValueError interno
