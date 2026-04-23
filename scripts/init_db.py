#!/usr/bin/env python
"""Inicializa la base de datos habilitando pgvector y ejecutando seeds."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from server.app.database.db import server_engine


async def init_database() -> None:
    async with server_engine.begin() as conn:
        print("Habilitando extensión pgvector...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    print("Ejecutando seeds del servidor...")
    from server.app.database.seeds import seed_all
    await seed_all()

    print("Ejecutando seeds Hub (chatbots y colecciones de ejemplo)...")
    from server.app.modules.agents_hub.database.seeds import seed_hub_defaults
    await seed_hub_defaults()

    await server_engine.dispose()
    print("Base de datos inicializada correctamente")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_database())
