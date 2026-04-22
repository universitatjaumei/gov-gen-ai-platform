
import asyncio
import sys
import os

# Add project root
sys.path.insert(0, os.getcwd())

from app.database.db import server_engine
from app.database.models import ExtractionServiceConfig
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

async def update_metadata():
    print("--- UPDATING PROMPTS METADATA ---")
    async with AsyncSession(server_engine) as session:
        updates = [
            ("sys_phase3_factory_gen", "System: Script Factory (Phase 3)", "System: Script Factory (Phase 1)"),
            ("sys_phase3_audit_forensic", "System: Audit Forensic (Phase 3)", "System: Audit Forensic (Phase 2)"),
            ("sys_phase3_refinement", "System: Script Refinement Loop (Phase 3)", "System: Script Refinement Loop (Phase 3)") # Just ensuring consistency
        ]
        
        for pid, old_name, new_name in updates:
            p = await session.get(ExtractionServiceConfig, pid)
            if p:
                print(f"Updating {pid}...")
                print(f"  Old Name: {p.name}")
                p.name = new_name
                print(f"  New Name: {p.name}")
                session.add(p)
            else:
                print(f"Warning: Prompt {pid} not found.")
        
        await session.commit()
    print("--- UPDATE COMPLETE ---")

if __name__ == "__main__":
    if sys.platform == 'win32':
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(update_metadata())
