import asyncio
from sqlalchemy import select
from server.app.modules.agents_hub.database.connection import create_async_engine, create_session_factory
from server.app.modules.agents_hub.database.config_models import HubLLMConfig

async def migrate_models():
    print("[MIGRATE] Updating gemini-2.0-flash to gemini-2.5-flash in the database...")
    engine = create_async_engine()
    factory = create_session_factory(engine)
    
    async with factory() as session:
        # Check how many to update
        result = await session.execute(
            select(HubLLMConfig).where(HubLLMConfig.model_name == 'gemini-2.0-flash')
        )
        configs = result.scalars().all()
        
        if not configs:
            print("[MIGRATE] No configs found with model_name='gemini-2.0-flash'. Nothing to do.")
            await engine.dispose()
            return
            
        print(f"[MIGRATE] Found {len(configs)} configs to update.")
        for c in configs:
            c.model_name = 'gemini-2.5-flash'
            print(f" - Updated config: {c.label} (ID: {c.id})")
            
        await session.commit()
        print("[MIGRATE] Update complete.")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_models())
