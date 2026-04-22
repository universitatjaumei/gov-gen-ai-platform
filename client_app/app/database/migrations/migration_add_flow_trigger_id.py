"""
Migration to add trigger_id to FlowRegistry.
"""
import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from client_app.app.database.db import client_engine as engine
from sqlalchemy import text

async def migrate():
    print("Migrating FlowRegistry: Adding trigger_id...")
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("PRAGMA table_info(flowregistry)"))
        existing_columns = {row[1] for row in result.fetchall()}
        
        if "trigger_id" not in existing_columns:
            print("Adding trigger_id column to flowregistry")
            await conn.execute(text("ALTER TABLE flowregistry ADD COLUMN trigger_id INTEGER"))
            await conn.execute(text("CREATE INDEX ix_flowregistry_trigger_id ON flowregistry (trigger_id)"))
        else:
            print("Column trigger_id already exists.")

if __name__ == "__main__":
    asyncio.run(migrate())
