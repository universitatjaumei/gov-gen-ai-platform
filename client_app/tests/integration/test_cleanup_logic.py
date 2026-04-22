
import pytest
import asyncio
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.services.script_library_service import script_library_service
from client_app.app.database.models import ScriptLibrary
from client_app.app.database.db import client_engine

@pytest.mark.asyncio
async def test_cleanup_stale_drafts():
    """Test cleaning up old draft scripts."""
    
    # 1. Add Stale Draft (simulated by mocking datetime or checking old records if any?)
    # Since we can't easily mock datetime.utcnow inside the service without patching,
    # we will rely on setting `older_than_hours=0` or very small usage.
    # But files also need creation.
    
    # Create a draft
    script = await script_library_service.add_script(
        source_module='test_cleanup',
        name='Stale Script',
        code='print("to be deleted")',
        description='Should be deleted',
        tags=['cleanup_test']
    )
    
    assert script.id is not None
    script_id = script.id
    
    # Manually backdate the created_at in the DB to simulate age
    async with AsyncSession(client_engine) as session:
        s = await session.get(ScriptLibrary, script_id)
        # Set created_at to 2 days ago
        from datetime import timedelta
        s.created_at = datetime.utcnow() - timedelta(days=2)
        session.add(s)
        await session.commit()
        
    # 2. Run Cleanup with 24h threshold
    deleted_count = await script_library_service.cleanup_stale_drafts(older_than_hours=24)
    
    assert deleted_count >= 1
    
    # 3. Verify Deletion
    deleted_script = await script_library_service.get_script(script_id)
    assert deleted_script is None

@pytest.mark.asyncio
async def test_cleanup_preserves_fresh_drafts():
    """Test that fresh drafts are not deleted."""
    
    # Create fresh draft
    script = await script_library_service.add_script(
        source_module='test_cleanup',
        name='Fresh Script',
        code='print("keep me")',
        # status='draft' is default
    )
    
    # Run Cleanup with 24h threshold
    # Since it was just created, it is < 24h old
    await script_library_service.cleanup_stale_drafts(older_than_hours=24)
    
    # Verify Existence
    s = await script_library_service.get_script(script.id)
    assert s is not None
    assert s.name == 'Fresh Script'
    
    # Cleanup manually
    await script_library_service.delete_script(script.id)
