import sys
import os
import asyncio
from sqlmodel import text
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# Add root to path
sys.path.append(os.getcwd())

from server.app.database.db import server_engine

async def add_column_if_missing(session, table, column, col_type, default="''"):
    try:
        await session.exec(text(f"SELECT {column} FROM {table} LIMIT 1"))
        print(f"Column '{column}' in '{table}' already exists.")
    except Exception as e:
        if "no such column" in str(e).lower():
            print(f"Column missing. Adding '{column}' to '{table}'...")
            await session.exec(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}"))
            await session.commit()
            print(f"Column '{column}' added successfully.")
        else:
            print(f"Error checking '{column}' in '{table}': {e}")

async def fix_schema():
    print("Fixing database schema...")
    async with AsyncSession(server_engine) as session:
        # ScriptEscalation
        await add_column_if_missing(session, "scriptescalation", "escalation_type", "VARCHAR", "'extraction'")
        
        # ClientAccount
        await add_column_if_missing(session, "clientaccount", "email", "VARCHAR", "'dev@automatia.local'")
        
        # PartnerAccount
        await add_column_if_missing(session, "partneraccount", "email", "VARCHAR", "'partner@automatia.local'")
        
        print("Schema fix completed.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_schema())
