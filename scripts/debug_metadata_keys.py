
import asyncio
import sys
import os

# Add project root
sys.path.insert(0, os.getcwd())

from app.database.db import server_engine
from app.database.models import ExtractionServiceConfig
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

# COPY PASTE OF THE DICT FROM admin_prompts.py (Expected keys)
EXPECTED_METADATA_KEYS = [
    "System: Discovery (Fase 0)",
    "System: Precision Extraction (Fase 1)",
    "System: Refinement (Golden Record)",
    "System: Data Noise Filter",
    "System: RPA Analysis",
    "System: RPA Refinement",
    "System: RPA Vision",
    "System: Script Factory (Phase 1)",
    "System: Audit Forensic (Phase 2)",
    "System: Script Refinement Loop (Phase 3)"
]

async def check_mismatch():
    print("--- DEBUGGING KEYS ---")
    async with AsyncSession(server_engine) as session:
        prompts = (await session.exec(select(ExtractionServiceConfig))).all()
        
        db_names = {p.name: p for p in prompts}
        
        for key in EXPECTED_METADATA_KEYS:
            if key in db_names:
                print(f"✅ MATCH: '{key}'")
            else:
                print(f"❌ MISSING IN DB: '{key}'")
                # Try to find close matches or show what is in DB
                print("   Closest DB candidates:")
                for db_name in db_names:
                    if "Vision" in db_name or "Factory" in db_name or "Audit" in db_name:
                         print(f"   - DB has: {repr(db_name)}")

if __name__ == "__main__":
    if sys.platform == 'win32':
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_mismatch())
