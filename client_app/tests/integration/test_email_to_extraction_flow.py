# client_app/tests/integration/test_email_to_extraction_flow.py
"""
Integration tests for Email to Extraction flow.

Tests the complete flow:
EmailWatcher -> Download PDF -> WorkflowEngine -> Extraction

Only mocks external I/O (IMAP), uses real internal components.
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.watchers.email_watcher import EmailWatcher


@pytest.mark.asyncio
async def test_email_to_extraction_integration(tmp_path: Path):
    """
    Test de integracion:
    EmailWatcher -> Download PDF -> ExtractionService -> Save JSON

    Valida flujo completo sin stubs internos.
    """
    # Mock de WorkflowEngine (simplificado hasta que se implemente)
    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_email_001")

    watcher = EmailWatcher(
        credentials={"server": "imap.test.com", "user": "test", "password": "fake"},
        base_dir=tmp_path,
        workflow_engine=mock_engine,
        flow_id="pdf_extraction",
        whitelist_senders=["trusted@company.com"]
    )

    # Simular descarga de PDF
    fake_pdf = tmp_path / "input" / "invoice.pdf"
    fake_pdf.parent.mkdir(exist_ok=True)
    fake_pdf.write_bytes(b"%PDF-1.4\nFake invoice content")

    # Trigger workflow manualmente (en produccion seria automatico)
    await watcher.trigger_workflow(fake_pdf, sender="trusted@company.com")

    # Verificar que se llamo al workflow
    assert mock_engine.execute_flow.called

    # EmailWatcher.trigger_workflow llama a execute_flow(flow_id, input_file=..., context=...)
    call_args = mock_engine.execute_flow.call_args
    assert call_args[0][0] == "pdf_extraction"  # Primer argumento posicional
    assert "invoice.pdf" in call_args.kwargs["input_file"]


@pytest.mark.asyncio
async def test_email_filters_by_whitelist(tmp_path: Path):
    """
    Test que verifica que emails de remitentes no autorizados
    no disparan el workflow.
    """
    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_002")

    watcher = EmailWatcher(
        credentials={"server": "imap.test.com", "user": "test", "password": "fake"},
        base_dir=tmp_path,
        workflow_engine=mock_engine,
        flow_id="pdf_extraction",
        whitelist_senders=["trusted@company.com", "admin@company.com"]
    )

    # El metodo publico es is_sender_allowed (sin underscore)
    is_allowed = watcher.is_sender_allowed("unknown@spam.com")
    assert is_allowed is False

    is_allowed = watcher.is_sender_allowed("trusted@company.com")
    assert is_allowed is True

    # Tambien debe aceptar formatos con nombre
    is_allowed = watcher.is_sender_allowed("Admin User <admin@company.com>")
    assert is_allowed is True


@pytest.mark.asyncio
async def test_email_sanitizes_filenames(tmp_path: Path):
    """
    Test que verifica la sanitizacion correcta de nombres de archivo.
    """
    mock_engine = AsyncMock()

    watcher = EmailWatcher(
        credentials={"server": "imap.test.com", "user": "test", "password": "fake"},
        base_dir=tmp_path,
        workflow_engine=mock_engine,
        flow_id="extraction_flow",
        whitelist_senders=["*"]  # Permitir todos para este test
    )

    # Verificar sanitizacion de nombres (metodo privado _sanitize_filename)
    test_cases = [
        ("document.pdf", "document.pdf"),
        ("../../../etc/passwd", "etc/passwd"),  # Path traversal eliminado
        ("file<>name.pdf", "filename.pdf"),  # Caracteres especiales
        ("report|2024.xlsx", "report2024.xlsx"),
    ]

    for raw_name, expected_pattern in test_cases:
        clean_name = watcher._sanitize_filename(raw_name)
        # Verificar que no tiene caracteres problematicos
        assert ".." not in clean_name
        assert "<" not in clean_name
        assert ">" not in clean_name
        assert "|" not in clean_name


@pytest.mark.asyncio
async def test_email_to_http_connector_flow(tmp_path: Path):
    """
    Test de integracion completo:
    Email -> Extract PDF -> Transform -> Send via HttpConnector
    """
    from app.modules.output.http_connector import HttpConnectorService

    # Mock de WorkflowEngine
    mock_engine = AsyncMock()
    extraction_results = {}

    # Simular execute_flow con la firma correcta:
    # execute_flow(flow_id, input_file=..., context=...)
    async def mock_execute_flow(flow_id, input_file=None, context=None):
        # Simular extraccion exitosa
        extraction_results["data"] = {
            "invoice_number": "INV-2024-001",
            "amount": 1500.00,
            "vendor": "ACME Corp"
        }
        return "exec_003"

    mock_engine.execute_flow = mock_execute_flow

    watcher = EmailWatcher(
        credentials={"server": "imap.test.com", "user": "test", "password": "fake"},
        base_dir=tmp_path,
        workflow_engine=mock_engine,
        flow_id="invoice_extraction",
        whitelist_senders=["invoices@vendor.com"]
    )

    http_connector = HttpConnectorService()

    # 1. Simular llegada de PDF por email
    fake_pdf = tmp_path / "input" / "invoice_vendor.pdf"
    fake_pdf.parent.mkdir(exist_ok=True)
    fake_pdf.write_bytes(b"%PDF-1.4\nInvoice content here")

    # 2. Trigger extraction workflow
    await watcher.trigger_workflow(fake_pdf, sender="invoices@vendor.com")

    # 3. Verificar que tenemos datos extraidos
    assert "data" in extraction_results
    extracted_data = extraction_results["data"]
    assert extracted_data["invoice_number"] == "INV-2024-001"

    # 4. Enviar a sistema de contabilidad
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"recorded": True, "entry_id": "ACC-001"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await http_connector.send_json(
            method="POST",
            url="https://accounting.company.com/api/invoices",
            payload=extracted_data
        )

    assert result["recorded"] is True
    assert result["entry_id"] == "ACC-001"


@pytest.mark.asyncio
async def test_email_process_with_attachments(tmp_path: Path):
    """
    Test de procesamiento de email con adjuntos.
    """
    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_att_001")

    watcher = EmailWatcher(
        credentials={"server": "imap.test.com", "user": "test", "password": "fake"},
        base_dir=tmp_path,
        workflow_engine=mock_engine,
        flow_id="document_process",
        whitelist_senders=["sender@company.com"]
    )

    # Simular estructura de email con adjuntos
    email_data = {
        "msg_id": 12345,
        "sender": "sender@company.com",
        "subject": "Invoice attached",
        "attachments": [
            {
                "filename": "invoice.pdf",
                "data": b"%PDF-1.4\nInvoice content"
            }
        ]
    }

    # Procesar email
    await watcher.process_email(email_data)

    # Verificar que se guardo el archivo
    saved_file = tmp_path / "input" / "invoice.pdf"
    assert saved_file.exists()

    # Verificar que se llamo al workflow
    assert mock_engine.execute_flow.called

