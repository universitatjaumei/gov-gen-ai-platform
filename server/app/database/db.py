"""
Server database configuration and initialization.

This module manages the Brain server database (brain_server.db) which stores:
- AI configurations
- System prompts
- Token logs
- Model pricing
- Multitenancy data (Partners, Clients, Licenses)
"""

import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Import models to register them with SQLModel metadata
from server.app.database import models

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

SERVER_DB_URL = "sqlite+aiosqlite:///data/brain_server.db"

sqlite_connect_args = {
    "check_same_thread": False,
    "timeout": 15
}

server_engine = create_async_engine(
    SERVER_DB_URL,
    echo=False,
    future=True,
    connect_args=sqlite_connect_args
)


async def init_server_db():
    """Initialize server database and create all tables."""
    async with server_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA synchronous=NORMAL;"))


# Alias for backwards compatibility
init_db = init_server_db


async def seed_server_db():
    """
    Populates server DB with default configurations.
    """
    from server.app.database.models import AIConfig, ExtractionServiceConfig
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(server_engine) as session:
        # 1. Seed AI Configs
        print("[SERVER DB] Checking/Seeding AI Configs...")

        required_roles = {
            "logico_navegacion": {"provider": "google", "model_id": "gemini-3-flash-preview"},
            "supervision": {"provider": "google", "model_id": "gemini-3.1-pro-preview"},
            "extraccion_pdf": {"provider": "google", "model_id": "gemini-2.5-flash-lite"},
        }

        for role_key, default_cfg in required_roles.items():
            statement = select(AIConfig).where(AIConfig.role_key == role_key)
            results = await session.exec(statement)
            existing = results.first()

            if not existing:
                print(f"[SERVER DB] Creating role: {role_key}")
                new_config = AIConfig(
                    role_key=role_key,
                    provider=default_cfg["provider"],
                    model_id=default_cfg["model_id"]
                )
                session.add(new_config)
            elif existing.model_id == "gemini-3-pro-preview":
                print(f"[SERVER DB] Migrating role {role_key}: gemini-3-pro-preview -> gemini-3.1-pro-preview")
                existing.model_id = "gemini-3.1-pro-preview"
                session.add(existing)

        await session.commit()
        print("[SERVER DB] Seeding complete.")
