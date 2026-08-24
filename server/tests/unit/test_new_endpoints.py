import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from server.app.core.auth.models import UserInfo
from server.app.routers.library_router import SignManifestRequest, sign_manifest

# SEC.9.1: `sign_manifest` dejó de ser invocable sin identidad — era un oráculo de firma RSA
# abierto. La guarda es una dependencia de FastAPI, así que al llamar a la función directamente
# hay que pasar el principal que la app habría inyectado.
_SUPERADMIN = UserInfo(user_id="root", email="root@example.org", role="superadmin")


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

        result = await sign_manifest(request, _SUPERADMIN)

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
        await sign_manifest(request, _SUPERADMIN)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_sign_manifest_missing_id():
    """Un manifiesto sin `id` es una petición mal formada, así que **400 y no 500**.

    Antes daba 500 porque el `ValueError` caía en el `except Exception` genérico —que además
    devolvía `str(e)` al cliente—. SEC.9.1 lo separa: el error del llamante se le atribuye al
    llamante, y el detalle interno deja de viajar en la respuesta.
    """
    manifest_data = {"content": "no id"}
    request = SignManifestRequest(
        manifest_json=json.dumps(manifest_data),
        partner_id="p_001",
    )

    with pytest.raises(HTTPException) as exc:
        await sign_manifest(request, _SUPERADMIN)
    assert exc.value.status_code == 400
