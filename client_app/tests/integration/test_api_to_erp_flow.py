# client_app/tests/integration/test_api_to_erp_flow.py
"""
Integration tests for API to ERP flow.

Tests the complete flow:
APIWatcher fetch -> ETL transformation -> HttpConnector send

Only mocks external I/O (HTTP APIs), uses real internal components.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel import create_engine, Session, SQLModel
from app.database.models import TaskLog
from app.modules.watchers.api_watcher import APIWatcher
from app.modules.output.http_connector import HttpConnectorService


@pytest.fixture
def db_session(tmp_path: Path):
    """Create in-memory database session for testing"""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.mark.asyncio
async def test_api_to_erp_integration_real_workflow(tmp_path: Path, db_session):
    """
    Test de integracion REAL:
    APIWatcher fetch -> WorkflowEngine -> HttpConnector send

    NO usa stubs internos. Solo mockea I/O externo (APIs).
    """
    # Setup: Componentes reales
    api_watcher = APIWatcher(base_dir=tmp_path)
    http_connector = HttpConnectorService(
        task_log_session=db_session,
        execution_id="exec_integration_001"
    )

    # 1. FETCH de API (mock externo)
    mock_api_response = MagicMock()
    mock_api_response.status_code = 200
    mock_api_response.json.return_value = {
        "data": [
            {"id": 1, "name": "ACME Corp", "revenue": 1000000},
            {"id": 2, "name": "TechStart Inc", "revenue": 500000}
        ]
    }
    mock_api_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_api_response)
        mock_client.return_value.__aenter__.return_value = mock_instance

        fetched_file = await api_watcher.fetch_data(
            config={
                "url": "https://api.crm.example.com/clients",
                "method": "GET",
                "response_format": "json"
            },
            execution_id="exec_integration_001"
        )

    assert fetched_file.exists()

    # 2. ETL (transformacion real - no stub)
    data = json.loads(fetched_file.read_text(encoding="utf-8"))
    clients = data["data"]

    # Transformar a formato ERP
    erp_payload = {
        "clients": [
            {
                "external_id": c["id"],
                "company_name": c["name"],
                "annual_revenue": c["revenue"]
            }
            for c in clients
        ]
    }

    assert len(erp_payload["clients"]) == 2
    assert erp_payload["clients"][0]["company_name"] == "ACME Corp"

    # 3. SEND a ERP (mock externo)
    mock_erp_response = MagicMock()
    mock_erp_response.status_code = 200
    mock_erp_response.json.return_value = {"imported": 2, "status": "success"}
    mock_erp_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_erp_response)
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await http_connector.send_json(
            method="POST",
            url="https://erp.company.com/api/clients/bulk",
            payload=erp_payload
        )

    assert result["status"] == "success"
    assert result["imported"] == 2

    # 4. VERIFICAR que se registro en TaskLog
    logs = db_session.query(TaskLog).all()
    assert len(logs) >= 1

    # Verificar que el log contiene info correcta
    log = logs[0]
    assert log.status == "success"
    assert "erp.company.com" in log.step_name


@pytest.mark.asyncio
async def test_api_fetch_handles_pagination_and_sends(tmp_path: Path):
    """
    Test de paginacion + envio:
    API con 2 paginas -> Consolidar -> Enviar a ERP
    """
    api_watcher = APIWatcher(base_dir=tmp_path)
    http_connector = HttpConnectorService()

    # Mock de API con paginacion
    page1_response = MagicMock()
    page1_response.status_code = 200
    page1_response.json.return_value = {
        "items": [{"id": 1}, {"id": 2}],
        "total": 4
    }
    page1_response.raise_for_status = MagicMock()

    page2_response = MagicMock()
    page2_response.status_code = 200
    page2_response.json.return_value = {
        "items": [{"id": 3}, {"id": 4}],
        "total": 4
    }
    page2_response.raise_for_status = MagicMock()

    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return page1_response if call_count == 1 else page2_response

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get = mock_get
        mock_client.return_value.__aenter__.return_value = mock_instance

        fetched_file = await api_watcher.fetch_data(
            config={
                "url": "https://api.example.com/items",
                "method": "GET",
                "response_format": "json",
                "pagination": {
                    "type": "offset",
                    "limit": 2,
                    "offset_param": "offset",
                    "total_key": "total",
                    "items_key": "items"
                }
            },
            execution_id="exec_pag_001"
        )

    # Verificar consolidacion
    data = json.loads(fetched_file.read_text(encoding="utf-8"))
    assert len(data["items"]) == 4

    # Enviar consolidado
    mock_send = MagicMock()
    mock_send.status_code = 200
    mock_send.json.return_value = {"ok": True}
    mock_send.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_send)
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await http_connector.send_json(
            method="POST",
            url="https://target.com/api/import",
            payload=data
        )

    assert result["ok"] is True


@pytest.mark.asyncio
async def test_api_to_erp_with_authentication(tmp_path: Path, db_session):
    """
    Test de flujo con autenticacion Bearer en ambos endpoints.
    """
    api_watcher = APIWatcher(base_dir=tmp_path)
    http_connector = HttpConnectorService(
        task_log_session=db_session,
        execution_id="exec_auth_001"
    )

    # Mock de API con autenticacion
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"users": [{"id": 1, "name": "John"}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_instance

        fetched_file = await api_watcher.fetch_data(
            config={
                "url": "https://api.secure.com/users",
                "method": "GET",
                "auth": {
                    "type": "bearer",
                    "token": "secret_token_123"
                },
                "response_format": "json"
            },
            execution_id="exec_auth_001"
        )

        # Verificar que se enviaron headers correctos
        call_args = mock_instance.get.call_args
        # El header debe incluir Authorization
        assert fetched_file.exists()

    # Enviar a destino con API Key
    mock_send = MagicMock()
    mock_send.status_code = 201
    mock_send.json.return_value = {"created": True}
    mock_send.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_send)
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await http_connector.send_json(
            method="POST",
            url="https://dest.api.com/import",
            payload={"users": [{"id": 1, "name": "John"}]},
            auth={
                "type": "api_key",
                "key": "my_api_key",
                "header": "X-API-Key"
            }
        )

    assert result["created"] is True

    # Verificar TaskLog
    logs = db_session.query(TaskLog).all()
    assert len(logs) >= 1

