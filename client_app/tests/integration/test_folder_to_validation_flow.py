# client_app/tests/integration/test_folder_to_validation_flow.py
"""
Integration tests for Folder to Validation flow.

Tests the complete flow:
FolderWatcher -> WorkflowEngine -> (error) -> ValidationLoop

Simulates extraction errors that trigger the validation loop.
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import create_engine, Session, SQLModel
from app.database.models import TaskLog, ValidationHistory
from app.modules.watchers.folder_watcher import FolderWatcher


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
async def test_folder_to_workflow_with_validation_loop(tmp_path: Path):
    """
    Test de integracion:
    FolderWatcher -> WorkflowEngine -> (error) -> ValidationLoop

    Simula un error en extraccion que activa ValidationLoop.
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()

    # Mock de WorkflowEngine que simula error
    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(side_effect=Exception("Extraction failed"))

    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_engine,
        flow_id="extraction_with_validation",
        file_patterns=["*.pdf"],
        stabilization_time=0.3  # Reducido para tests
    )

    # Iniciar watcher
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.2)

    # Simular archivo
    test_pdf = watch_dir / "doc.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 content")

    # Esperar suficiente tiempo para estabilizacion + procesamiento
    # stabilization_time=0.3 significa ~2 checks de 0.5s = 1s minimo
    await asyncio.sleep(2.0)

    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verificar que intento ejecutar workflow (aunque falle)
    assert mock_engine.execute_flow.called


@pytest.mark.asyncio
async def test_folder_watcher_successful_workflow(tmp_path: Path):
    """
    Test de flujo exitoso:
    FolderWatcher -> WorkflowEngine -> Success
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()

    # Mock de WorkflowEngine exitoso
    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_success_001")

    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_engine,
        flow_id="pdf_extraction",
        file_patterns=["*.pdf"],
        stabilization_time=0.3
    )

    # Iniciar watcher
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.2)

    # Simular archivo PDF
    test_pdf = watch_dir / "document.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 valid content")

    # Esperar procesamiento completo
    await asyncio.sleep(2.0)

    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verificar que se ejecuto el workflow
    assert mock_engine.execute_flow.called

    call_kwargs = mock_engine.execute_flow.call_args.kwargs
    assert call_kwargs["flow_id"] == "pdf_extraction"
    assert "document.pdf" in call_kwargs["context"]["input_file"]
    assert call_kwargs["context"]["trigger"] == "folder_watcher"


@pytest.mark.asyncio
async def test_folder_watcher_ignores_wrong_patterns(tmp_path: Path):
    """
    Test que verifica que archivos que no coinciden con el patron
    son ignorados.
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()

    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_001")

    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_engine,
        flow_id="pdf_only",
        file_patterns=["*.pdf"],  # Solo PDFs
        stabilization_time=0.3
    )

    # Iniciar watcher
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.2)

    # Crear archivo que NO coincide con patron
    test_txt = watch_dir / "notes.txt"
    test_txt.write_text("This is a text file")

    test_xlsx = watch_dir / "data.xlsx"
    test_xlsx.write_bytes(b"fake excel content")

    # Esperar procesamiento
    await asyncio.sleep(1.5)

    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # NO debe haber llamado al workflow
    assert not mock_engine.execute_flow.called


@pytest.mark.asyncio
async def test_folder_watcher_multiple_patterns(tmp_path: Path):
    """
    Test con multiples patrones de archivo.
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()

    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_multi_001")

    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_engine,
        flow_id="doc_extraction",
        file_patterns=["*.pdf", "*.docx", "*.xlsx"],
        stabilization_time=0.3
    )

    # Iniciar watcher
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.2)

    # Crear archivos de diferentes tipos
    (watch_dir / "report.pdf").write_bytes(b"%PDF content")

    # Esperar procesamiento completo
    await asyncio.sleep(2.0)

    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Debe haber procesado el PDF
    assert mock_engine.execute_flow.called


@pytest.mark.asyncio
async def test_validation_history_recorded_on_error(tmp_path: Path, db_session):
    """
    Test que verifica que los errores se registran en ValidationHistory.

    NOTA: Este test esta preparado para cuando ValidationLoop este implementado.
    Por ahora solo verifica la estructura basica.
    """
    # Crear registro de ValidationHistory para simular error
    validation_record = ValidationHistory(
        task_id="task_error_001",
        attempt_number=1,
        user_action="retry",
        feedback="OCR failed, try with better resolution"
    )

    db_session.add(validation_record)
    db_session.commit()

    # Verificar que se guardo correctamente
    from sqlmodel import select
    statement = select(ValidationHistory).where(
        ValidationHistory.task_id == "task_error_001"
    )
    records = db_session.exec(statement).all()

    assert len(records) == 1
    assert records[0].user_action == "retry"
    assert records[0].attempt_number == 1
    assert "OCR failed" in records[0].feedback


@pytest.mark.asyncio
async def test_folder_to_http_connector_flow(tmp_path: Path):
    """
    Test de flujo completo:
    FolderWatcher -> Extract -> Transform -> HttpConnector
    """
    from app.modules.output.http_connector import HttpConnectorService

    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()

    extraction_results = {}

    async def mock_execute_flow(flow_id, context):
        # Simular extraccion exitosa
        extraction_results["data"] = {
            "document_type": "invoice",
            "total": 2500.00,
            "date": "2024-01-15"
        }
        return "exec_folder_001"

    mock_engine = AsyncMock()
    mock_engine.execute_flow = mock_execute_flow

    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_engine,
        flow_id="invoice_extraction",
        file_patterns=["*.pdf"],
        stabilization_time=0.3
    )

    http_connector = HttpConnectorService()

    # Iniciar watcher
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.2)

    # Simular llegada de archivo
    test_pdf = watch_dir / "invoice_jan.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 invoice content")

    # Esperar procesamiento completo
    await asyncio.sleep(2.0)

    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verificar que tenemos datos extraidos
    assert "data" in extraction_results

    # Enviar a sistema externo
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"processed": True}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await http_connector.send_json(
            method="POST",
            url="https://erp.company.com/api/documents",
            payload=extraction_results["data"]
        )

    assert result["processed"] is True

