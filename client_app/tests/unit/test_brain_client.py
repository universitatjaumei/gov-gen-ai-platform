# client_app/tests/unit/test_brain_client.py
"""
Tests para BrainAPIClient - Cliente HTTP seguro para el servidor Brain.

Estos tests verifican:
- Autenticación via headers (X-License-Key)
- Timeouts configurados correctamente
- Manejo de errores de licencia
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.clients.brain_client import BrainAPIClient


class TestGenerateScript:
    """Tests para el método generate_script."""

    @pytest.mark.asyncio
    async def test_generate_script_sends_headers(self):
        """Verificar que generate_script envía la licencia en headers y el body correcto."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"script": "print('ok')", "tokens_used": 10}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock, return_value=mock_response) as mock_post:
            await client.generate_script(
                prompt="Test",
                output_schema={"key": "val"},
                license_key="secret_key"
            )

            # Verificar argumentos de la llamada
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Verificar headers
            assert call_args.kwargs['headers']['X-License-Key'] == "secret_key"
            assert call_args.kwargs['headers']['Content-Type'] == "application/json"

            # Verificar body JSON
            assert call_args.kwargs['json']['output_schema'] == {"key": "val"}
            assert call_args.kwargs['json']['prompt'] == "Test"

    @pytest.mark.asyncio
    async def test_generate_script_returns_response(self):
        """Verificar que generate_script retorna la respuesta correctamente."""
        
        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"script": "print('hello')", "tokens_used": 150}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock, return_value=mock_response):
            result = await client.generate_script(
                prompt="Extraer datos de factura",
                output_schema={"invoice_number": "string"},
                license_key="test_key"
            )

            assert "script" in result
            assert result["tokens_used"] == 150

    @pytest.mark.asyncio
    async def test_generate_script_invalid_license_raises_error(self):
        """Verificar que licencia inválida en generate_script lanza ValueError."""
        
        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Licencia no válida o expirada"}

        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(ValueError, match="Licencia no válida o expirada"):
                await client.generate_script(
                    prompt="Test",
                    output_schema={},
                    license_key="invalid_key"
                )


class TestValidateLicense:
    """Tests para el método validate_license."""

    @pytest.mark.asyncio
    async def test_validate_license_success(self):
        """Verificar validación de licencia via headers."""
        
        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True, "quota_remaining": 50000}
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock, return_value=mock_response) as mock_get:
            result = await client.validate_license(license_key="valid_key")

            # Verificar que la key va en HEADERS, no en params
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args.kwargs['headers']['X-License-Key'] == "valid_key"

            # Verificar respuesta
            assert result["valid"] is True
            assert result["quota_remaining"] == 50000

    @pytest.mark.asyncio
    async def test_validate_license_invalid_raises_error(self):
        """Verificar que licencia inválida lanza error."""
        
        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Licencia no válida"}

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(ValueError, match="Licencia no válida"):
                await client.validate_license(license_key="invalid_key")


class TestClientConfiguration:
    """Tests para configuración del cliente."""

    def test_client_strips_trailing_slash(self):
        """Verificar que el cliente elimina slash final de base_url."""

        client = BrainAPIClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_client_default_timeout_configuration(self):
        """Verificar configuración de timeouts por defecto."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        # Timeout total de 120s para LLM, 10s para conexión
        assert client.timeout.read == 120.0
        assert client.timeout.connect == 10.0


class TestPushToLibrary:
    """Tests para el método push_to_library."""

    @pytest.mark.asyncio
    async def test_push_to_library_sends_correct_payload(self):
        """Verificar que push_to_library envía el payload correcto."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "id": "script-001",
            "version": 1,
            "signed": True
        }
        mock_response.raise_for_status = MagicMock()

        manifest = {
            "id": "script-001",
            "name": "Test Script",
            "type": "extraction",
            "code_content": "def extract(): pass",
            "version": 1
        }

        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await client.push_to_library(
                manifest=manifest,
                license_key="test_key",
                partner_id="partner-abc"
            )

            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Verificar URL
            assert "/v1/library/push" in call_args.args[0]

            # Verificar headers
            assert call_args.kwargs['headers']['X-License-Key'] == "test_key"
            assert call_args.kwargs['headers']['X-Partner-ID'] == "partner-abc"

            # Verificar body
            assert call_args.kwargs['json']['id'] == "script-001"
            assert call_args.kwargs['json']['name'] == "Test Script"
            assert call_args.kwargs['json']['code_content'] == "def extract(): pass"

            # Verificar respuesta
            assert result["status"] == "success"
            assert result["signed"] is True

    @pytest.mark.asyncio
    async def test_push_to_library_invalid_license_raises_error(self):
        """Verificar que licencia inválida lanza ValueError."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(ValueError, match="Licencia no válida"):
                await client.push_to_library(
                    manifest={"id": "test"},
                    license_key="invalid_key"
                )

    @pytest.mark.asyncio
    async def test_push_to_library_server_error_raises_exception(self):
        """Verificar que errores de servidor lanzan HTTPStatusError."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Error de firma"}
        mock_response.request = MagicMock()

        with patch.object(httpx.AsyncClient, 'post', new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError, match="Error de firma"):
                await client.push_to_library(
                    manifest={"id": "test"},
                    license_key="test_key"
                )


class TestDownloadFromLibrary:
    """Tests para el método download_from_library."""

    @pytest.mark.asyncio
    async def test_download_from_library_returns_manifest_with_signature(self):
        """Verificar que download_from_library retorna el manifiesto con firma."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "script-001",
            "name": "Test Script",
            "type": "extraction",
            "code_content": "def extract(): pass",
            "version": 1,
            "signature": "abc123signature==",
            "is_workflow": False,
            "access_groups": []
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock, return_value=mock_response) as mock_get:
            result = await client.download_from_library(
                item_id="script-001",
                license_key="test_key",
                client_id="client-xyz",
                client_groups=["premium"]
            )

            mock_get.assert_called_once()
            call_args = mock_get.call_args

            # Verificar URL
            assert "/v1/library/download/script-001" in call_args.args[0]

            # Verificar headers
            assert call_args.kwargs['headers']['X-License-Key'] == "test_key"
            assert call_args.kwargs['headers']['X-Client-ID'] == "client-xyz"
            assert '["premium"]' in call_args.kwargs['headers']['X-Client-Groups']

            # Verificar respuesta incluye firma
            assert result["id"] == "script-001"
            assert result["signature"] == "abc123signature=="
            assert result["code_content"] == "def extract(): pass"

    @pytest.mark.asyncio
    async def test_download_from_library_not_found_raises_error(self):
        """Verificar que item no encontrado lanza HTTPStatusError 404."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.request = MagicMock()

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError, match="no encontrada"):
                await client.download_from_library(
                    item_id="nonexistent",
                    license_key="test_key"
                )

    @pytest.mark.asyncio
    async def test_download_from_library_access_denied_raises_error(self):
        """Verificar que acceso denegado lanza HTTPStatusError 403."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.request = MagicMock()

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError, match="Acceso denegado"):
                await client.download_from_library(
                    item_id="restricted-script",
                    license_key="test_key"
                )


class TestGetLibraryManifest:
    """Tests para el método get_library_manifest."""

    @pytest.mark.asyncio
    async def test_get_library_manifest_returns_list(self):
        """Verificar que get_library_manifest retorna lista de items."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "script-001", "name": "Script 1", "version": 1, "is_workflow": False},
            {"id": "flow-001", "name": "Flow 1", "version": 2, "is_workflow": True}
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, 'get', new_callable=AsyncMock, return_value=mock_response) as mock_get:
            result = await client.get_library_manifest(
                license_key="test_key",
                partner_id="partner-abc"
            )

            mock_get.assert_called_once()
            call_args = mock_get.call_args

            # Verificar URL
            assert "/v1/library/manifest" in call_args.args[0]

            # Verificar headers
            assert call_args.kwargs['headers']['X-Partner-ID'] == "partner-abc"

            # Verificar respuesta
            assert len(result) == 2
            assert result[0]["id"] == "script-001"
            assert result[1]["is_workflow"] is True


class TestLibraryHeaders:
    """Tests para generación de headers de biblioteca."""

    def test_library_headers_include_context(self):
        """Verificar que _get_library_headers incluye contexto de cliente."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        headers = client._get_library_headers(
            license_key="test_key",
            client_id="client-123",
            partner_id="partner-456",
            client_groups=["group1", "group2"]
        )

        assert headers["X-License-Key"] == "test_key"
        assert headers["X-Client-ID"] == "client-123"
        assert headers["X-Partner-ID"] == "partner-456"
        assert '["group1", "group2"]' in headers["X-Client-Groups"]

    def test_library_headers_omits_none_values(self):
        """Verificar que _get_library_headers no incluye valores None."""

        client = BrainAPIClient(base_url="http://localhost:8000")

        headers = client._get_library_headers(
            license_key="test_key",
            client_id=None,
            partner_id=None,
            client_groups=None
        )

        assert headers["X-License-Key"] == "test_key"
        assert "X-Client-ID" not in headers
        assert "X-Partner-ID" not in headers
        assert "X-Client-Groups" not in headers
