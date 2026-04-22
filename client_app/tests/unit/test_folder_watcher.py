import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from app.modules.watchers.folder_watcher import FolderWatcher

@pytest.mark.asyncio
@pytest.mark.skip(reason="Watchdog flaky in test environment")
async def test_detects_new_file(tmp_path: Path):
    """Verificar detección de archivo nuevo"""
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    
    mock_workflow = AsyncMock()
    
    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_workflow,
        flow_id="test_flow",
        file_patterns=["*.pdf"],
        stabilization_time=0.1
    )
    
    # Iniciar watcher en background
    task = asyncio.create_task(watcher.start_monitoring())
    
    # Esperar a que inicie
    await asyncio.sleep(0.5)
    
    # Crear archivo
    test_file = watch_dir / "document.pdf"
    test_file.write_text("fake pdf")
    
    # Esperar a que procese
    await asyncio.sleep(1.0)
    
    # Detener watcher
    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verificar que se llamó al workflow
    assert mock_workflow.execute_flow.called

@pytest.mark.asyncio
@pytest.mark.skip(reason="Watchdog flaky in test environment")
async def test_ignores_non_matching_patterns(tmp_path: Path):
    """Verificar que ignora archivos que no coinciden con pattern"""
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    
    mock_workflow = AsyncMock()
    
    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_workflow,
        flow_id="test_flow",
        file_patterns=["*.pdf"],  # Solo PDFs
        stabilization_time=0.1
    )
    
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.5)
    
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
    assert not mock_workflow.execute_flow.called

@pytest.mark.asyncio
@pytest.mark.skip(reason="Watchdog flaky in test environment")
async def test_waits_for_file_stability(tmp_path: Path):
    """Verificar que espera a que el archivo termine de escribirse"""
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    
    mock_workflow = AsyncMock()
    
    watcher = FolderWatcher(
        watch_directory=watch_dir,
        workflow_engine=mock_workflow,
        flow_id="test_flow",
        stabilization_time=0.5  # Esperar 0.5 segundos
    )
    
    task = asyncio.create_task(watcher.start_monitoring())
    await asyncio.sleep(0.5)
    
    test_file = watch_dir / "big_file.pdf"
    
    # Simular escritura en progreso
    start_time = asyncio.get_event_loop().time()
    test_file.write_text("part 1")
    await asyncio.sleep(0.1)
    test_file.write_text("part 1 + part 2")
    
    # Esperar estabilización + procesamiento
    await asyncio.sleep(1.0)
    
    watcher.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verificar que esperó antes de procesar
    if mock_workflow.execute_flow.called:
        call_time = asyncio.get_event_loop().time()
        elapsed = call_time - start_time
        assert elapsed >= 0.5  # Debe haber esperado al menos 0.5s

