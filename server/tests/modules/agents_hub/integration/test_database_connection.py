"""Prompt 2.2 — Tests de conexión a BD (TDD - RED → GREEN)."""
import pytest
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai"


class TestAsyncDatabaseConnection:

    @pytest.mark.asyncio
    async def test_async_engine_creates_connection(self) -> None:
        from server.app.modules.agents_hub.database.connection import create_async_engine

        engine = create_async_engine(DB_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_async_session_commits_transaction(self) -> None:
        from server.app.modules.agents_hub.database.connection import (
            create_async_engine,
            create_session_factory,
        )

        engine = create_async_engine(DB_URL)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            await session.execute(
                text("CREATE TEMP TABLE test_commit (id SERIAL, value TEXT)")
            )
            await session.execute(
                text("INSERT INTO test_commit (value) VALUES ('test')")
            )
            await session.commit()
            result = await session.execute(text("SELECT value FROM test_commit"))
            assert result.scalar() == "test"
        await engine.dispose()
