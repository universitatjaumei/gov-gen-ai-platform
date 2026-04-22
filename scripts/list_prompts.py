
import asyncio
import sys
import os

# Add project root
sys.path.insert(0, os.getcwd())

from app.database.db import server_engine
from app.database.models import ExtractionServiceConfig
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

async def list_prompts():
    print("--- DB PROMPTS LIST ---")
    async with AsyncSession(server_engine) as session:
        prompts = (await session.exec(select(ExtractionServiceConfig))).all()
        for p in prompts:
            print(f"ID: {p.service_id} | Name: {p.name} | Module: {p.module}")

if __name__ == "__main__":
    if sys.platform == 'win32':
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(list_prompts())
