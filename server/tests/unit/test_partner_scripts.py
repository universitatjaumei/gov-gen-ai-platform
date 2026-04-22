
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from server.app.services.partner_scripts_service import PartnerScriptsService
from server.app.database.models import ScriptEscalation

# Test the Service Logic (The core business logic)
@pytest.mark.asyncio
async def test_partner_service_get_pending():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    
    service = PartnerScriptsService(mock_session, "p1")
    
    # Mock result
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = ["esc1", "esc2"]
    mock_session.execute.return_value = mock_result
    
    results = await service.get_pending_escalations()
    
    assert len(results) == 2
    mock_session.execute.assert_called_once()
    # Check query construction if needed, but simple call verify is enough for now

@pytest.mark.asyncio
async def test_partner_service_publish():
    mock_session = MagicMock()
    mock_session.get = AsyncMock()
    mock_session.commit = AsyncMock()
    
    service = PartnerScriptsService(mock_session, "p1")
    
    # Case: Found
    mock_esc = ScriptEscalation(id=1, status="PENDING", script_name="Test")
    mock_session.get.return_value = mock_esc
    
    success = await service.publish_script(1, "new code")
    
    assert success is True
    assert mock_esc.status == "RESOLVED"
    mock_session.add.assert_called_with(mock_esc)
    mock_session.commit.assert_awaited()

@pytest.mark.asyncio
async def test_partner_service_reject():
    mock_session = MagicMock()
    mock_session.get = AsyncMock()
    mock_session.commit = AsyncMock()
    
    service = PartnerScriptsService(mock_session, "p1")
    
    mock_esc = ScriptEscalation(id=1, status="PENDING", script_name="Test")
    mock_session.get.return_value = mock_esc
    
    success = await service.reject_escalation(1, "Bad code")
    
    assert success is True
    assert mock_esc.status == "REJECTED"
    assert "Bad code" in mock_esc.client_notes
    mock_session.commit.assert_awaited()

# Smoke Test for UI Module Loading
def test_ui_module_loads():
    # Mock dependencies to allow import
    with patch.dict(sys.modules, {
        "nicegui": MagicMock(),
        "server.app.database.db": MagicMock(),
        "server.app.ui.partner_layout": MagicMock(),
    }):
        import server.app.ui.partner_scripts
        assert server.app.ui.partner_scripts.partner_scripts_content is not None
