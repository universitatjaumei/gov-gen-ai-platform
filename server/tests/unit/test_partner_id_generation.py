
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.services.partner_service import PartnerService
from server.app.database.models import PartnerAccount

@pytest.mark.asyncio
async def test_partner_id_generation():
    """Test generating sequential ID_P_XXX for partners"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)
    service = PartnerService(session)
    
    # Mock DB query result for existing IDs
    mock_result = MagicMock()
    # Scenario: ID_P_001 and ID_P_005 exist, and a legacy one
    mock_result.all.return_value = ["ID_P_001", "partner_old", "ID_P_005"]
    service.db.exec = AsyncMock(return_value=mock_result)

    # Mock DB add/commit/refresh
    service.db.add = MagicMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()

    # Call
    partner = await service.create_partner("New Partner")
    
    # Verify ID
    # Max existing was 005, so expected 006
    assert partner.partner_id == "ID_P_006"
    assert partner.name == "New Partner"

@pytest.mark.asyncio
async def test_partner_id_generation_empty():
    """Test generating first ID when no partners exist"""
    session = AsyncMock(spec=AsyncSession)
    service = PartnerService(session)
    
    mock_result = MagicMock()
    mock_result.all.return_value = []
    service.db.exec = AsyncMock(return_value=mock_result)

    service.db.add = MagicMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()

    partner = await service.create_partner("First Partner")
    
    assert partner.partner_id == "ID_P_001"
