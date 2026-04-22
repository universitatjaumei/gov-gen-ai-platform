import pytest
import asyncio
import sys
from pathlib import Path
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "shared"))

# Only load nicegui.testing.plugin if selenium is available
try:
    import selenium
    pytest_plugins = ["nicegui.testing.plugin"]
except ImportError:
    pytest_plugins = []

@pytest.fixture(scope="session")
def event_loop():
    """Loop de eventos para tests async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def test_client_db():
    """BBDD local en memoria para tests"""
    from sqlalchemy.pool import StaticPool
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Import models to register metadata
    import client_app.app.database.models
    from automatia_shared.core.audit_models import EnterpriseAuditLog  # For enterprise_audit_log table
    
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Patch global engine
    import client_app.app.database.db as db_module
    original_engine = db_module.client_engine
    db_module.client_engine = test_engine
        
    yield test_engine
    
    # Restore
    db_module.client_engine = original_engine
    await test_engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_client_db):
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(
        test_client_db, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
