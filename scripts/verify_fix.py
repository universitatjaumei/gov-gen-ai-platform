
import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from app.database.db import init_db
from app.database.seeds_multitenancy import seed_multitenancy_defaults
from client_app.app.database.db import init_client_db, seed_client_db, client_engine
from server.app.database.db import server_engine
from server.app.database.models import ClientAccount, License
from client_app.app.database.models import ServerConnection
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from automatia_shared.enums import LicenseStatus
import hashlib

async def verify():
    print("--- STARTING VERIFICATION ---")
    
    # 1. Run Seeds
    print("\n[1] Running Seeds...")
    await init_db()
    await seed_multitenancy_defaults()
    await init_client_db()
    await seed_client_db()
    
    # 2. Verify Server DB
    print("\n[2] Verifying Server DB...")
    async with AsyncSession(server_engine) as session:
        # Check Client Key Hash
        client = await session.get(ClientAccount, "client_demo")
        expected_hash = hashlib.sha256("demo_key_123".encode()).hexdigest()
        
        if client.license_key == expected_hash:
            print(f"✅ Client License Key Hash MATCH: {client.license_key[:8]}...")
        else:
            print(f"❌ Client License Key Hash MISMATCH: Expected {expected_hash[:8]}..., Got {client.license_key[:8]}...")
            
        # Check Active Licenses Query (Fixed Logic)
        stmt = select(func.count(License.license_id)).where(License.status == LicenseStatus.ACTIVE.value)
        count = (await session.exec(stmt)).first()
        
        if count == 1:
            print(f"✅ Active Licenses Count MATCH: {count}")
        else:
            print(f"❌ Active Licenses Count MISMATCH: Expected 1, Got {count}")

    # 3. Verify Client DB
    print("\n[3] Verifying Client DB...")
    async with AsyncSession(client_engine) as session:
        conn = (await session.exec(select(ServerConnection))).first()
        if conn and conn.license_key == "demo_key_123":
            print(f"✅ Client Local Key MATCH: {conn.license_key}")
        else:
             print(f"❌ Client Local Key MISMATCH. Found: {conn.license_key if conn else 'None'}")
             
    print("\n--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(verify())
    except Exception as e:
        print(f"ERROR: {e}")
