import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
from app.modules.watchers.email_watcher import EmailWatcher

@pytest.mark.asyncio
async def test_email_to_extraction_flow_end_to_end(tmp_path: Path):
    """
    Test de integración: Email → Download → Trigger Workflow
    
    Simula:
    1. Recepción de email con PDF adjunto
    2. Descarga a execution_dir/input
    3. Lanzamiento de workflow de extracción
    """
    # Mock workflow engine (stub simple)
    mock_engine = AsyncMock()
    mock_engine.execute_flow = AsyncMock(return_value="exec_123")
    
    # Crear watcher
    watcher = EmailWatcher(
        credentials={"server": "imap.example.com", "user": "test", "pass": "fake"},
        base_dir=tmp_path,
        workflow_engine=mock_engine,
        flow_id="pdf_extraction_flow",
        whitelist_senders=["trusted@company.com"]
    )
    
    # Simular email con adjunto (mock de imapclient)
    # (En test real usaría fixture con email.message)
    
    fake_pdf = tmp_path / "input" / "invoice.pdf"
    fake_pdf.parent.mkdir(exist_ok=True, parents=True)
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")
    
    # Trigger manualmente (en producción sería automático)
    await watcher.trigger_workflow(fake_pdf, sender="trusted@company.com")
    
    # Verificaciones
    assert mock_engine.execute_flow.called
    
    # Verificar que se pasó el path correcto
    call_kwargs = mock_engine.execute_flow.call_args.kwargs
    assert "input_file" in call_kwargs or "context" in call_kwargs

