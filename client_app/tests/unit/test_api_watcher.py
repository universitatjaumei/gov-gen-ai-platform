# client_app/tests/unit/test_api_watcher.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import json
from app.modules.watchers.api_watcher import APIWatcher


def create_mock_response(status_code: int, json_data: dict):
    """Helper para crear un mock de respuesta HTTP"""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock()
    return mock_response


def create_mock_client(get_side_effect=None, get_return_value=None):
    """Helper para crear un mock de httpx.AsyncClient"""
    mock_client = AsyncMock()

    if get_side_effect:
        mock_client.get = AsyncMock(side_effect=get_side_effect)
    elif get_return_value:
        mock_client.get = AsyncMock(return_value=get_return_value)

    return mock_client


@pytest.mark.asyncio
async def test_fetch_json_data(tmp_path: Path):
    """Verificar fetch de API JSON simple"""
    watcher = APIWatcher(base_dir=tmp_path)

    mock_response = create_mock_response(200, {"data": [{"id": 1, "name": "ACME"}]})
    mock_client = create_mock_client(get_return_value=mock_response)

    with patch("httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__.return_value = mock_client
        MockAsyncClient.return_value.__aexit__.return_value = None

        output_path = await watcher.fetch_data(
            config={
                "url": "https://api.crm/clients",
                "method": "GET",
                "response_format": "json"
            },
            execution_id="exec_001"
        )

    assert output_path.exists()

    # Verificar contenido guardado
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["data"][0]["name"] == "ACME"


@pytest.mark.asyncio
async def test_handles_pagination_offset(tmp_path: Path):
    """Verificar paginación con offset"""
    watcher = APIWatcher(base_dir=tmp_path)

    # Simular 2 páginas
    page1 = create_mock_response(200, {"items": [{"id": 1}], "total": 3})
    page2 = create_mock_response(200, {"items": [{"id": 2}, {"id": 3}], "total": 3})

    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return page1 if call_count == 1 else page2

    mock_client = AsyncMock()
    mock_client.get = mock_get

    with patch("httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__.return_value = mock_client
        MockAsyncClient.return_value.__aexit__.return_value = None

        output_path = await watcher.fetch_data(
            config={
                "url": "https://api.example.com/items",
                "method": "GET",
                "response_format": "json",
                "pagination": {
                    "type": "offset",
                    "limit": 1,
                    "offset_param": "offset",
                    "total_key": "total"
                }
            },
            execution_id="exec_002"
        )

    # Verificar que se hicieron 2 llamadas
    assert call_count == 2

    # Verificar que se consolidaron todos los items
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_auth_bearer_token(tmp_path: Path):
    """Verificar autenticación con Bearer token"""
    watcher = APIWatcher(base_dir=tmp_path)

    mock_response = create_mock_response(200, {"status": "ok"})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__.return_value = mock_client
        MockAsyncClient.return_value.__aexit__.return_value = None

        await watcher.fetch_data(
            config={
                "url": "https://api.secure.com/data",
                "method": "GET",
                "response_format": "json",
                "auth": {
                    "type": "bearer",
                    "token": "secret_token_123"
                }
            },
            execution_id="exec_003"
        )

        # Verificar que se pasó el header correcto
        call_kwargs = mock_client.get.call_args.kwargs
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer secret_token_123"


@pytest.mark.asyncio
async def test_retry_on_500_error(tmp_path: Path):
    """Verificar reintentos en caso de error 500"""
    watcher = APIWatcher(base_dir=tmp_path)

    success_response = create_mock_response(200, {"status": "ok"})

    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Server Error")
        return success_response

    mock_client = AsyncMock()
    mock_client.get = mock_get

    with patch("httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__.return_value = mock_client
        MockAsyncClient.return_value.__aexit__.return_value = None

        output_path = await watcher.fetch_data(
            config={
                "url": "https://api.flaky.com/data",
                "method": "GET",
                "response_format": "json",
                "max_retries": 3
            },
            execution_id="exec_004"
        )

    # Verificar que se intentó 2 veces (1 fallo + 1 éxito)
    assert call_count == 2
    assert output_path.exists()

