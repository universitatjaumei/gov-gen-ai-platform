import asyncio
from server.app.modules.agents_hub.database.base import HubOperationalBase, HubConfigBase
from server.app.modules.agents_hub.database.connection import create_async_engine

# Need to import models so they are attached to the metadata
from server.app.modules.agents_hub.database import config_models, operational_models

async def drop():
    engine = create_async_engine('postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai')
    async with engine.begin() as conn:
        await conn.run_sync(HubOperationalBase.metadata.drop_all)
        await conn.run_sync(HubConfigBase.metadata.drop_all)
    print('Dropped!')

asyncio.run(drop())
