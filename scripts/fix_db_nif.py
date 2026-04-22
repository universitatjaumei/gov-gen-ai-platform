import asyncio
import sys
import os
# Add current directory to path so we can import server
sys.path.append(os.getcwd())

from sqlalchemy import text
from server.app.database.db import server_engine

async def fix_schema():
    print("Checking database schema...")
    async with server_engine.begin() as conn:
        try:
            # Check if column exists (this is a bit hacky in raw SQL but works for SQLite)
            # In SQLite, we can just try to add it and ignore failure if it exists, 
            # or simply run it since we know it's missing based on the error.
            # We'll try to add it.
            print("Attempting to add 'nif' column to 'clientaccount'...")
            await conn.execute(text("ALTER TABLE clientaccount ADD COLUMN nif VARCHAR"))
            print("Success: Column 'nif' added.")
        except Exception as e:
            if "duplicate column" in str(e) or "no such table" in str(e): # Adjust check as needed
                print(f"info: {e}")
            else:
                # If it fails, it might be because it already exists or other error.
                # SQLite throws OperationalError if column exists usually.
                print(f"Note: {e}")

if __name__ == "__main__":
    asyncio.run(fix_schema())
