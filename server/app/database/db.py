"""
Server database configuration and initialization (PostgreSQL + asyncpg).
"""

import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# Import models to register them with SQLModel metadata
from server.app.database import models  # noqa: F401

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai",
)

server_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    server_engine, class_=AsyncSession, expire_on_commit=False
)


async def init_server_db():
    """Create all tables (development only — use Alembic in production)."""
    async with server_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# Alias for backwards compatibility
init_db = init_server_db


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def seed_server_db():
    """Populates server DB with default configurations."""
    from server.app.database.models import AIConfig
    from sqlmodel import select

    async with AsyncSessionLocal() as session:
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
                session.add(AIConfig(
                    role_key=role_key,
                    provider=default_cfg["provider"],
                    model_id=default_cfg["model_id"],
                ))

        await session.commit()
        print("[SERVER DB] Seeding complete.")
