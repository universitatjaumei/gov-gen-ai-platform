import pytest
from unittest.mock import AsyncMock, MagicMock
from server.app.services.partner_scripts_service import PartnerScriptsService
from server.app.database.models import ScriptEscalation, TrustedScript

@pytest.mark.asyncio
async def test_get_pending_escalations(db_session):
    """Test retrieving pending escalations for a partner."""
    # Setup
    e1 = ScriptEscalation(partner_id="p1", client_id="c1", script_name="S1", original_code="x", status="PENDING")
    e2 = ScriptEscalation(partner_id="p1", client_id="c2", script_name="S2", original_code="y", status="RESOLVED")
    e3 = ScriptEscalation(partner_id="p2", client_id="c3", script_name="S3", original_code="z", status="PENDING")
    db_session.add_all([e1, e2, e3])
    await db_session.commit()

    service = PartnerScriptsService(db_session, partner_id="p1")
    results = await service.get_pending_escalations()

    assert len(results) == 1
    assert results[0].script_name == "S1"

@pytest.mark.asyncio
async def test_publish_script(db_session):
    """Test publishing a script from escalation."""
    # Setup
    esc = ScriptEscalation(partner_id="p1", client_id="c1", script_name="MyScript", original_code="old", status="PENDING")
    db_session.add(esc)
    await db_session.commit()
    await db_session.refresh(esc)

    service = PartnerScriptsService(db_session, partner_id="p1")
    new_code = "print('fixed')"
    
    # Act
    trusted_script = await service.publish_script(esc.id, new_code)

    # Assert
    assert trusted_script is not None
    assert trusted_script.name == "MyScript"
    assert trusted_script.code == new_code
    assert trusted_script.status == "PUBLISHED"
    
    # Verify escalation status updated
    await db_session.refresh(esc)
    assert esc.status == "RESOLVED"

@pytest.mark.asyncio
async def test_reject_escalation(db_session):
    """Test rejecting an escalation."""
    esc = ScriptEscalation(partner_id="p1", client_id="c1", script_name="BadScript", original_code="x", status="PENDING")
    db_session.add(esc)
    await db_session.commit()
    await db_session.refresh(esc)

    service = PartnerScriptsService(db_session, partner_id="p1")
    await service.reject_escalation(esc.id, reason="Cannot fix")

    await db_session.refresh(esc)
    assert esc.status == "REJECTED"
    assert "Cannot fix" in esc.client_notes
