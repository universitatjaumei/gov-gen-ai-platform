import pytest
import pytest_asyncio
from pathlib import Path
from app.services.validation_loop import ValidationLoopManager
from app.services.support.support_packager import SupportPackager

@pytest.mark.asyncio
async def test_approve_action_saves_results(db_session):
    """Verificar que al aprobar se guarda el resultado y se cierra la tarea."""
    manager = ValidationLoopManager(db_session)
    task_id = "test-task-approve-001"

    result = await manager.handle_feedback(
        task_id=task_id,
        action='approve',
        feedback=None
    )

    assert result['status'] == 'approved'
    assert 'retries' in result

@pytest.mark.asyncio
async def test_retry_action_increments_counter(db_session):
    """Verificar que retry incrementa el contador y guarda feedback."""
    manager = ValidationLoopManager(db_session)
    task_id = "test-task-retry-002"

    # First retry
    result1 = await manager.handle_feedback(
        task_id=task_id,
        action='retry',
        feedback='La fecha está mal, debería ser 2026-01-15',
        fields=['fecha']
    )

    assert result1['status'] == 'regenerating'
    assert result1['retries'] == 1

    # Second retry
    result2 = await manager.handle_feedback(
        task_id=task_id,
        action='retry',
        feedback='El importe no coincide',
        fields=['importe']
    )

    assert result2['status'] == 'regenerating'
    assert result2['retries'] == 2

@pytest.mark.asyncio
async def test_escalate_creates_support_bundle(db_session, tmp_path):
    """Verificar que escalar crea un bundle de soporte."""
    # Create a mock anonymizer
    class MockAnonymizer:
        async def apply(self, input_path: str, output_path: str):
            # Just copy the file for testing
            Path(output_path).write_text("ANONYMIZED CONTENT")
    
    packager = SupportPackager(
        base_dir=tmp_path,
        anonymizer=MockAnonymizer(),
        max_size_mb=50
    )

    # Create a sample input file
    sample_file = tmp_path / "sample.pdf"
    sample_file.write_text("Sample PDF content")

    bundle_path = await packager.create_support_bundle(
        execution_id="exec-escalate-001",
        script_content="# Script que falló\nprint('test')",
        logs="Error: No se encontró el campo\nTraceback...",
        input_file=sample_file
    )

    assert Path(bundle_path).exists()
    assert Path(bundle_path).suffix == '.zip'
    assert 'support_exec-escalate-001.zip' in bundle_path

@pytest.mark.asyncio
async def test_max_retries_triggers_escalation(db_session):
    """Verificar que exceder max_retries escala automáticamente."""
    manager = ValidationLoopManager(db_session, max_retries=2)
    task_id = "test-task-max-retries-003"

    # Retry 1
    result1 = await manager.handle_feedback(
        task_id=task_id,
        action='retry',
        feedback='Primer intento'
    )
    assert result1['status'] == 'regenerating'

    # Retry 2
    result2 = await manager.handle_feedback(
        task_id=task_id,
        action='retry',
        feedback='Segundo intento'
    )
    assert result2['status'] == 'regenerating'

    # Retry 3 - should escalate
    result3 = await manager.handle_feedback(
        task_id=task_id,
        action='retry',
        feedback='Tercer intento - debería escalar'
    )
    assert result3['status'] == 'escalated'
    assert result3['retries'] == 3

