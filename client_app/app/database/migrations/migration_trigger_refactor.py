"""
Migration script to initialize TriggerConfig and TriggerSubscription tables.
Also sets up some defaults if needed.
"""
import asyncio
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from client_app.app.database.db import client_engine as engine
from client_app.app.database.models import SQLModel, TriggerConfig, TriggerSubscription

async def migrate():
    print("Starting Trigger Refactor Migration...")
    async with engine.begin() as conn:
        # Create tables if not exist
        await conn.run_sync(SQLModel.metadata.create_all)
        print("Created tables: TriggerConfig, TriggerSubscription")

if __name__ == "__main__":
    asyncio.run(migrate())
