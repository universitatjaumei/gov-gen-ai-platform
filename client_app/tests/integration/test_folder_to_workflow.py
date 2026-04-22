import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock
from client_app.app.modules.watchers.folder_watcher import FolderWatcher

# QUITAR @pytest.mark.skip de todos los tests
# Se han eliminado los skips y habilitado los tests completos

@pytest.mark.asyncio
@pytest.mark.integration
async def test_folder_to_workflow_integration(tmp_path: Path):
    """
    Test de integración completo: FolderWatcher → WorkflowEngine
    
    Verifica:
    1. Detección de archivo
    2. Espera de estabilización
    3. Llamada a WorkflowEngine con contexto correcto
    """
    watch_dir = tmp_path / "input"
    watch_dir.mkdir()
    
    # Mock realista de WorkflowEngine
    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_123")
    
    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_engine,
        flow_id="pdf_extraction",
        file_patterns=["*.pdf", "*.docx"],
        stabilization_time=0.5  # Reducido para tests
    )
    
    # Iniciar watcher
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.3)
    
    # Simular llegada de archivo
    test_pdf = watch_dir / "invoice_2024.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 real content here")
    
    # Esperar procesamiento (estabilización + margen)
    await asyncio.sleep(5.0)
    
    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verificaciones
    assert mock_engine.execute_flow.called, "WorkflowEngine should be called"
    
    call_args = mock_engine.execute_flow.call_args
    assert call_args.kwargs["flow_id"] == "pdf_extraction"
    
    context = call_args.kwargs.get("context", {})
    assert "input_file" in context
    assert "invoice_2024.pdf" in context["input_file"] # Path can be absolute, check simplified
    assert str(test_pdf) in str(context["input_file"]) # Check matching path string
    assert context["trigger"] == "folder_watcher"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_folder_watcher_ignores_wrong_patterns(tmp_path: Path):
    """Verificar que ignora archivos que no coinciden con pattern."""
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    
    mock_engine = AsyncMock()
    
    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_engine,
        flow_id="test_flow",
        file_patterns=["*.pdf"],
        stabilization_time=0.3
    )
    
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.2)
    
    # Crear archivo NO-PDF
    test_file = watch_dir / "document.txt"
    test_file.write_text("text file")
    
    await asyncio.sleep(1.0)
    
    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # NO debe haber llamado al workflow
    assert not mock_engine.execute_flow.called


@pytest.mark.asyncio
@pytest.mark.integration
async def test_folder_watcher_multiple_patterns(tmp_path: Path):
    """Verificar que acepta múltiples patrones."""
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    
    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_123")
    
    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_engine,
        flow_id="test_flow",
        file_patterns=["*.pdf", "*.xml", "*.csv"],
        stabilization_time=0.3
    )
    
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.2)
    
    # Crear archivos de diferentes tipos
    (watch_dir / "doc.pdf").write_text("pdf")
    await asyncio.sleep(0.1)
    (watch_dir / "data.xml").write_text("<xml/>")
    await asyncio.sleep(0.1)
    (watch_dir / "table.csv").write_text("a,b,c")
    
    await asyncio.sleep(2.0) # Increased sleep
    
    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Debe haber llamado 3 veces
    assert mock_engine.execute_flow.call_count >= 3
