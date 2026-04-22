import pytest
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
from client_app.app.modules.watchers.email_watcher import EmailWatcher

def test_filters_sender_by_whitelist():
    """Verificar filtrado por whitelist de remitentes"""
    mock_workflow_engine = AsyncMock()
    
    w = EmailWatcher(
        credentials=MagicMock(),
        whitelist_senders=["allowed@domain.com"],
        workflow_engine=mock_workflow_engine,
        base_dir=Path("./tmp"),
        flow_id="test_flow"
    )
    
    assert w.is_sender_allowed("Allowed User <allowed@domain.com>")
    assert not w.is_sender_allowed("spam@malicious.com")

def test_extracts_clean_filename():
    """Verificar sanitización de nombres de archivo"""
    mock_workflow_engine = AsyncMock()
    w = EmailWatcher(
        credentials=MagicMock(),
        workflow_engine=mock_workflow_engine,
        base_dir=Path("./tmp"),
        flow_id="test_flow"
    )
    
    # Nombres peligrosos deben sanitizarse
    clean = w._sanitize_filename("../../etc/passwd")
    assert ".." not in clean
    assert "/" not in clean
    
    clean2 = w._sanitize_filename("invoice<script>.pdf")
    assert "<" not in clean2
    assert ">" not in clean2

@pytest.mark.asyncio
async def test_triggers_workflow_on_attachment(tmp_path: Path):
    """Verificar que lanza workflow al recibir adjunto válido"""
    mock_workflow_engine = AsyncMock()
    
    w = EmailWatcher(
        credentials=MagicMock(),
        base_dir=tmp_path,
        workflow_engine=mock_workflow_engine,
        flow_id="email_pdf_extraction"  # Flow a lanzar
    )
    
    # Simular adjunto
    attachment_path = tmp_path / "input" / "test.pdf"
    attachment_path.parent.mkdir(exist_ok=True, parents=True)
    attachment_path.write_text("fake pdf content")
    
    # Trigger workflow
    await w.trigger_workflow(attachment_path, sender="user@example.com")
    
    # Verificar que se llamó al engine
    mock_workflow_engine.execute_flow.assert_called_once()
    
    call_args = mock_workflow_engine.execute_flow.call_args
    assert "email_pdf_extraction" in str(call_args)


# ============================================================
# Tests para subject_filter
# ============================================================

def test_subject_filter_allows_matching_subject():
    """Verificar que subject_filter permite asuntos que contienen el texto"""
    mock_workflow_engine = AsyncMock()

    w = EmailWatcher(
        credentials=MagicMock(),
        workflow_engine=mock_workflow_engine,
        base_dir=Path("./tmp"),
        flow_id="test_flow",
        subject_filter="factura"
    )

    assert w.is_subject_allowed("Nueva factura de enero")
    assert w.is_subject_allowed("FACTURA PENDIENTE")  # Case insensitive
    assert w.is_subject_allowed("Re: factura adjunta")


def test_subject_filter_blocks_non_matching_subject():
    """Verificar que subject_filter bloquea asuntos que no contienen el texto"""
    mock_workflow_engine = AsyncMock()

    w = EmailWatcher(
        credentials=MagicMock(),
        workflow_engine=mock_workflow_engine,
        base_dir=Path("./tmp"),
        flow_id="test_flow",
        subject_filter="factura"
    )

    assert not w.is_subject_allowed("Pedido nuevo")
    assert not w.is_subject_allowed("Newsletter mensual")
    assert not w.is_subject_allowed("")


def test_subject_filter_allows_all_when_empty():
    """Verificar que sin filtro permite todos los asuntos"""
    mock_workflow_engine = AsyncMock()

    w = EmailWatcher(
        credentials=MagicMock(),
        workflow_engine=mock_workflow_engine,
        base_dir=Path("./tmp"),
        flow_id="test_flow",
        subject_filter=None  # Sin filtro
    )

    assert w.is_subject_allowed("Cualquier asunto")
    assert w.is_subject_allowed("")
    assert w.is_subject_allowed(None)


def test_subject_filter_strips_whitespace():
    """Verificar que el filtro ignora espacios en blanco"""
    mock_workflow_engine = AsyncMock()

    w = EmailWatcher(
        credentials=MagicMock(),
        workflow_engine=mock_workflow_engine,
        base_dir=Path("./tmp"),
        flow_id="test_flow",
        subject_filter="  factura  "  # Con espacios
    )

    # El filtro debería limpiarse a "factura"
    assert w.subject_filter == "factura"
    assert w.is_subject_allowed("Nueva factura")

