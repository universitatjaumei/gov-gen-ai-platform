import pytest
from app.services.validation_loop import ValidationLoopManager
from app.database.models import ValidationHistory
from sqlmodel import select
import json

@pytest.fixture
def loop_manager(db_session):
    return ValidationLoopManager(db_session, max_retries=3)

@pytest.mark.asyncio
async def test_retry_logic_increments_counter(loop_manager):
    new_state = await loop_manager.handle_feedback(
        task_id="t1",
        action="retry",
        feedback="Error en fecha",
        who="user_123"
    )

    assert new_state['retries'] == 1
    assert new_state['status'] == 'regenerating'

@pytest.mark.asyncio
async def test_approve_closes_task(loop_manager):
    new_state = await loop_manager.handle_feedback(
        task_id="t1",
        action="approve",
        feedback=None,
        who="user_123"
    )

    assert new_state['status'] == 'approved'

@pytest.mark.asyncio
async def test_escalation_after_max_retries(loop_manager):
    # Simular que ya se usaron los 3 reintentos
    for i in range(3):
        await loop_manager.handle_feedback(
            task_id="t1", action="retry", feedback=f"Intento {i+1}", who="user"
        )

    # El siguiente retry debería escalar
    new_state = await loop_manager.handle_feedback(
        task_id="t1",
        action="retry",
        feedback="Sigue fallando",
        who="user"
    )

    assert new_state['status'] == 'escalated'

@pytest.mark.asyncio
async def test_structured_feedback_fields(loop_manager):
    new_state = await loop_manager.handle_feedback(
        task_id="t2",
        action="retry",
        feedback="Error en campos",
        who="user",
        fields=["fecha", "importe"]  # Feedback estructurado
    )

    assert new_state['fields_affected'] == ["fecha", "importe"]

@pytest.mark.asyncio
async def test_history_persisted(loop_manager, db_session):
    from app.database.models import ValidationHistory

    await loop_manager.handle_feedback(
        task_id="t3", action="retry", feedback="Test", who="user"
    )

    # Use wait_for or similar if async db operations are not fully blocking/synced in test env immediately?
    # Actually sqlmodel async session commit should be awaited.
    
    result = await db_session.execute(select(ValidationHistory).where(ValidationHistory.task_id == "t3"))
    history = result.scalars().all()
    
    assert len(history) == 1
    assert history[0].user_action == "retry"
    assert history[0].who == "user"

@pytest.mark.asyncio
async def test_reject_closes_task(loop_manager):
    new_state = await loop_manager.handle_feedback(
        task_id="t4",
        action="reject",
        feedback="No sirve",
        who="user_123"
    )

    assert new_state['status'] == 'rejected'

@pytest.mark.asyncio
async def test_manual_escalation_request(loop_manager):
    """Test manual escalation button trigger"""
    new_state = await loop_manager.handle_feedback(
        task_id="t5",
        action="escalate",
        feedback="Requesting expert help",
        who="user_123"
    )
    
    assert new_state['status'] == 'escalated'

