
import pytest
import re
from unittest.mock import AsyncMock, MagicMock
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.services.partner_client_service import PartnerClientService
from server.app.database.models import ClientAccount

@pytest.mark.asyncio
async def test_client_id_generation_standard():
    """Test generating ID for standard partner_XXX format"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)
    service = PartnerClientService(session, "partner_001")
    
    # Mock get_client to return None (meaning ID doesn't exist)
    service.get_client = AsyncMock(return_value=None)
    
    # We need to mock create_client to avoid DB operations
    service.create_client = AsyncMock()
    
    # Mock db.add/commit/refresh
    service.db.add = MagicMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()

    # Call the method
    client, license, _ = await service.create_client_with_license("Test Client")
    
    # Verify the generated ID was passed to create_client
    # The first argument to create_client is client_id
    call_args = service.create_client.call_args
    assert call_args is not None, "create_client was not called"
    client_id = call_args[0][0] # first arg
    
    assert client_id == "ID_C_001_001"

@pytest.mark.asyncio
async def test_client_id_generation_future_format():
    """Test generating ID for future ID_P_XXX format"""
    session = AsyncMock(spec=AsyncSession)
    service = PartnerClientService(session, "ID_P_005")
    
    service.get_client = AsyncMock(return_value=None)
    service.create_client = AsyncMock()
    service.db.add = MagicMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()

    await service.create_client_with_license("Test Client")
    
    client_id = service.create_client.call_args[0][0]
    assert client_id == "ID_C_005_001"

@pytest.mark.asyncio
async def test_client_id_generation_numeric():
    """Test generating ID for purely numeric partner ID"""
    session = AsyncMock(spec=AsyncSession)
    service = PartnerClientService(session, "042")
    
    service.get_client = AsyncMock(return_value=None)
    service.create_client = AsyncMock()
    
    # Need to mock DB adds for license creation
    service.db.add = MagicMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()

    await service.create_client_with_license("Test Client")
    
    client_id = service.create_client.call_args[0][0]
    assert client_id == "ID_C_042_001"

@pytest.mark.asyncio
async def test_client_id_generation_fallback():
    """Test generating ID for non-standard partner ID (fallback)"""
    session = AsyncMock(spec=AsyncSession)
    service = PartnerClientService(session, "partner_dev")
    
    service.get_client = AsyncMock(return_value=None)
    service.create_client = AsyncMock()
    service.db.add = MagicMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()

    await service.create_client_with_license("Test Client")
    
    client_id = service.create_client.call_args[0][0]
    # Expecting 3 digits. Since logic isn't written, I'll assume 000 for non-numeric
    # But wait, my plan said "hash-based or 000". Let's assume 000 for "dev" 
    # or ensure it matches the pattern ID_C_XXX_001
    
    assert client_id.startswith("ID_C_")
    assert client_id.endswith("_001")
    parts = client_id.split("_")
    assert len(parts[2]) == 3, "Partner part should be 3 digits"
    assert parts[2].isdigit()

@pytest.mark.asyncio
async def test_client_id_generation_sequence():
    """Test sequential ID generation"""
    session = AsyncMock(spec=AsyncSession)
    service = PartnerClientService(session, "partner_001")
    
    # Mock that 001 exists, 002 doesn't
    async def get_client_side_effect(client_id):
        if client_id == "ID_C_001_001":
            return ClientAccount(client_id="ID_C_001_001", partner_id="partner_001", name="Existing", license_key="x")
        return None
        
    service.get_client = AsyncMock(side_effect=get_client_side_effect)
    service.create_client = AsyncMock()
    service.db.add = MagicMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()

    await service.create_client_with_license("Test Client")
    
    client_id = service.create_client.call_args[0][0]
    assert client_id == "ID_C_001_002"
