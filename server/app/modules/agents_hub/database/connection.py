"""Conexión asíncrona a PostgreSQL para agents_hub."""

import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine as sa_create_async_engine,
)


def create_async_engine(url: str | None = None, **kwargs: Any) -> AsyncEngine:
    if url is None:
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai",
        )
    return sa_create_async_engine(url, echo=False, pool_pre_ping=True, **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine()
    return _engine


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = create_session_factory(get_engine())
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
