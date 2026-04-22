
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.models import PartnerAccount, ClientAccount, License
from server.app.services.partner_client_service import PartnerClientService

# Setup in-memory DB
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False, future=True)

async def reproduce():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(test_engine) as session:
        # Create a Partner
        partner_id = "partner_001"
        partner = PartnerAccount(
            partner_id=partner_id,
            name="Partner Test",
            credits_balance=1000,
            is_active=True
        )
        session.add(partner)
        await session.commit()
        
        # Service
        service = PartnerClientService(session, partner_id)
        
        # Create Client 1
        client1, _, _ = await service.create_client_with_license("Client 1")
        print(f"Client 1 ID: {client1.client_id}")
        
        # Create Client 2
        client2, _, _ = await service.create_client_with_license("Client 2")
        print(f"Client 2 ID: {client2.client_id}")

        assert client1.client_id == "client_partner_001_001", f"Expected client_partner_001_001, got {client1.client_id}"
        assert client2.client_id == "client_partner_001_002", f"Expected client_partner_001_002, got {client2.client_id}"

if __name__ == "__main__":
    asyncio.run(reproduce())
