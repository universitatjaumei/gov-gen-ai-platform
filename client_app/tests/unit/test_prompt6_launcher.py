import pytest
from client_app.app.services.launcher import LauncherService
from client_app.app.database.models import LocalAutomation
from automatia_shared.enums import AutomationType

@pytest.mark.asyncio
async def test_launcher_execution(db_session):
    # Setup
    item = LocalAutomation(
        id="launch-test-1", 
        name="Launcher Test", 
        type=AutomationType.CUSTOM_SCRIPT,
        code_content="print('hello')",
        signature="mock-sig",
        is_system=True,
        local_status="synced"
    )
    db_session.add(item)
    await db_session.commit()
    
    service = LauncherService(db_session)
    
    # Act
    result = await service.launch(item.id)
    
    # Assert
    assert result["success"] is True
    assert result["automation_id"] == "launch-test-1"
    assert result["type"] == AutomationType.CUSTOM_SCRIPT
    assert "simulated" in result["message"]

@pytest.mark.asyncio
async def test_launcher_not_found(db_session):
    service = LauncherService(db_session)
    result = await service.launch("non-existent")
    assert result["success"] is False
    assert result["error"] == "Automation not found"
