import asyncio
from sqlmodel import select
from client_app.app.database.db import client_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.models import ScriptLibrary

async def main():
    async with AsyncSession(client_engine) as session:
        stmt = select(ScriptLibrary).where(ScriptLibrary.source_module == 'extraction')
        result = await session.execute(stmt)
        scripts = result.scalars().all()
        for s in scripts:
            print(f"ID: {s.id}, Name: {s.name}, Status: {s.status}, SourceAutomationID: '{s.source_automation_id}' (Type: {type(s.source_automation_id)})")

if __name__ == "__main__":
    asyncio.run(main())
