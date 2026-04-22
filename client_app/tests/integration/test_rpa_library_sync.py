
import pytest
import sys
from pathlib import Path

# Add shared to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'shared'))

from client_app.app.database.models import RpaPlaybook, ScriptLibrary
from client_app.app.services.rpa_library_sync import rpa_sync_service
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.db import client_engine

@pytest.mark.asyncio
async def test_rpa_sync_creates_library_entry():
    """Test that syncing a playbook creates a corresponding ScriptLibrary entry."""
    
    # 1. Create a dummy Playbook
    playbook = RpaPlaybook(
        name="Test Playbook Sync",
        base_url="http://example.com",
        description="A test playbook for sync verification",
        actions=[{"action": "click", "selector": "#btn"}]
    )
    
    # Save to DB first (needed for ID)
    async with AsyncSession(client_engine) as session:
        session.add(playbook)
        await session.commit()
        await session.refresh(playbook)
        session.expunge(playbook) # Detach to prevent lazy loading issues
        
        # 2. Sync (Pass Session)
        library_entry = await rpa_sync_service.sync_playbook_to_library(playbook, session=session)
        
        # 3. Verify
        assert library_entry is not None
        assert library_entry.name == "Test Playbook Sync"
        assert library_entry.source_module == 'rpa'
        assert library_entry.source_automation_id == playbook.id
        
        # Verify contracts generated
        assert library_entry.data_contract is not None
        assert library_entry.ui_contract is not None
        assert "input_file" in str(library_entry.ui_contract)
        
        # Verify docs
        assert library_entry.doc_path is not None
        
        # Clean up
        await session.delete(playbook)
        await session.delete(library_entry)
        await session.commit()

@pytest.mark.asyncio
async def test_rpa_sync_updates_existing_entry():
    """Test that syncing updates existing library entry instead of creating new."""
    
    # 1. Create playbook
    playbook = RpaPlaybook(
        name="Update Test Playbook",
        base_url="http://update.com",
        description="Original Desc",
        actions=[]
    )
    
    async with AsyncSession(client_engine) as session:
        session.add(playbook)
        await session.commit()
        await session.refresh(playbook)
        
        # 2. First Sync (Pass Session)
        entry1 = await rpa_sync_service.sync_playbook_to_library(playbook, session=session)
        assert entry1.description == "Original Desc"
        
        # 3. Modify Playbook & Sync Again
        playbook.description = "Updated Desc"
        
        # Pass Session - No redundant/conflicting sessions
        entry2 = await rpa_sync_service.sync_playbook_to_library(playbook, session=session)
        
        # 4. Verify Update (eager access inside session)
        assert entry2 is not None
        assert entry2.id == entry1.id  # Same ID
        assert entry2.description == "Updated Desc"
        
        # Clean up
        await session.delete(playbook)
        await session.delete(entry2)
        await session.commit()
