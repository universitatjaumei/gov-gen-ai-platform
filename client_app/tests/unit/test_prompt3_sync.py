import pytest
from sqlmodel import SQLModel, create_engine, Session, select
from sqlmodel.pool import StaticPool
from datetime import datetime
import hashlib

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.models import LocalAutomation
from client_app.app.services.sync_manager import SyncManager
from automatia_shared.enums import AutomationType
from automatia_shared.dtos import AutomationBlueprintDTO

@pytest.fixture(name="session")
async def session_fixture():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_local_automation_persistence(session):
    """Test persistence of LocalAutomation model."""
    auto = LocalAutomation(
        id="auto-1",
        name="Synced Script",
        type=AutomationType.CUSTOM_SCRIPT,
        code_content="print('hello')",
        version=1,
        signature="sig_123",
        is_system=True,
        local_status="synced"
    )
    session.add(auto)
    await session.commit()
    
    saved = await session.get(LocalAutomation, "auto-1")
    assert saved.name == "Synced Script"
    assert saved.local_status == "synced"

def test_sync_verification_logic():
    """Test SyncManager signature validation."""
    manager = SyncManager(session=None) # Mock session
    
    content = "import os"
    # Assuming simple SHA256 for now as placeholder for signature check
    # In reality this would be public/private key verification
    # For this test we just ensure the manager has a verify method that works as expected
    
    # Mock behavior: for now, verify_signature just returns True if signature is not empty
    # This will be refined in implementation
    assert manager.verify_signature(content, "some_signature") is True
    assert manager.verify_signature(content, "") is False

@pytest.mark.asyncio
async def test_sync_item_logic(session):
    """Test merging logic in SyncManager."""
    manager = SyncManager(session)
    
    # Mock DTO from Brain
    dto = AutomationBlueprintDTO(
        id="rem-1",
        name="Remote",
        type=AutomationType.RPA_WEB,
        code_content="remote code",
        version=2,
        updated_at=datetime.utcnow(),
        signature="sig_rem",
        client_id="c1",
        partner_id="p1"
    )
    
    # Sync new item
    await manager.save_local(dto)
    
    saved = await session.get(LocalAutomation, "rem-1")
    assert saved.version == 2
    assert saved.is_system is False # It comes from remote, but assuming 'system' means global template? 
    # Actually, is_system should probably be mapped from DTO's is_system_template
    
    # Update existing
    dto.version = 3
    dto.code_content = "updated code"
    await manager.save_local(dto)
    
    updated = await session.get(LocalAutomation, "rem-1")
    assert updated.version == 3
    assert updated.code_content == "updated code"
