import pytest
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.models import ScriptEscalation

@pytest.mark.asyncio
async def test_script_escalation_creation(db_session: AsyncSession):
    """Test creating a ScriptEscalation record."""
    escalation = ScriptEscalation(
        partner_id="partner_test",
        client_id="client_test",
        script_name="Broken Script",
        original_code="print('error')",
        status="PENDING",
        client_notes="It fails",
        created_at=datetime.utcnow()
    )
    db_session.add(escalation)
    await db_session.commit()
    await db_session.refresh(escalation)

    assert escalation.id is not None
    assert escalation.partner_id == "partner_test"
    assert escalation.status == "PENDING"
    assert escalation.original_code == "print('error')"

@pytest.mark.asyncio
async def test_script_escalation_status_update(db_session: AsyncSession):
    """Test updating status of escalation."""
    # Setup
    escalation = ScriptEscalation(
        partner_id="p1", client_id="c1", script_name="S1", original_code="x", status="PENDING", client_notes="n"
    )
    db_session.add(escalation)
    await db_session.commit()

    # Update
    escalation.status = "RESOLVED"
    await db_session.commit()
    await db_session.refresh(escalation)

    assert escalation.status == "RESOLVED"
