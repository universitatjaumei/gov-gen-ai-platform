# client_app/tests/unit/test_http_connector.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from app.modules.output.http_connector import HttpConnectorService


def create_mock_response(status_code: int, json_data: dict):
    """Helper para crear un mock de respuesta HTTP"""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.mark.asyncio
async def test_send_json_simple():
    """Verificar envio JSON basico"""
    service = HttpConnectorService()

    mock_response = create_mock_response(200, {"status": "ok"})
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__.return_value = mock_client
        MockAsyncClient.return_value.__aexit__.return_value = None

        result = await service.send_json(
            method="POST",
            url="https://webhook.example.com/data",
            payload={"key": "value"}
        )

    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_retry_on_network_error():
    """Verificar reintentos en error de red"""
    service = HttpConnectorService(max_retries=3)

    success_response = create_mock_response(200, {"status": "ok"})

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Network Error")
        return success_response

    mock_client = AsyncMock()
    mock_client.post = mock_post

    with patch("httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__.return_value = mock_client
        MockAsyncClient.return_value.__aexit__.return_value = None

        result = await service.send_json(
            method="POST",
            url="https://api.example.com/endpoint",
            payload={"data": "test"}
        )

    assert call_count == 2  # 1 fallo + 1 exito
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_logs_to_task_log(tmp_path):
    """Verificar que registra en TaskLog"""
    # Mock de la sesion de DB
    mock_session = MagicMock()
    added_logs = []

    def capture_add(log):
        added_logs.append(log)

    mock_session.add = capture_add
    mock_session.commit = MagicMock()

    # Mock del modelo TaskLog
    class MockTaskLog:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    service = HttpConnectorService(
        task_log_session=mock_session,
        execution_id="exec_001"
    )

    mock_response = create_mock_response(200, {"ok": True})
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as MockAsyncClient, \
         patch("client_app.app.modules.output.http_connector.HttpConnectorService._log_to_task_log") as mock_log:

        MockAsyncClient.return_value.__aenter__.return_value = mock_client
        MockAsyncClient.return_value.__aexit__.return_value = None

        await service.send_json(
            method="POST",
            url="https://api.example.com/test",
            payload={"test": "data"}
        )

        # Verificar que se llamo a _log_to_task_log con los parametros correctos
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["url"] == "https://api.example.com/test"
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["status"] == "success"
        assert call_kwargs["status_code"] == 200


@pytest.mark.asyncio
async def test_send_multipart_file(tmp_path):
    """Verificar envio multipart con archivo"""
    service = HttpConnectorService()

    # Crear archivo de prueba
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    mock_response = create_mock_response(200, {"uploaded": True})
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__.return_value = mock_client
        MockAsyncClient.return_value.__aexit__.return_value = None

        result = await service.send_multipart(
            url="https://upload.example.com/files",
            files={"file": test_file},
            data={"description": "Test upload"}
        )

    assert result["uploaded"] is True

    # Verificar que se llamo con files
    call_kwargs = mock_client.post.call_args.kwargs
    assert "files" in call_kwargs

