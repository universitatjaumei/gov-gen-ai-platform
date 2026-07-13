
import pytest
from sqlmodel import SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
import asyncio

# We'll import SuperAdminAccount once it exists
# from server.app.database.models import SuperAdminAccount 

@pytest.fixture(name="session")
async def session_fixture():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    async with engine.begin() as conn:
        from server.app.database.models import SQLModel as ServerSQLModel
        await conn.run_sync(ServerSQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_admin_account_success(session):
    """Test creating a valid admin account."""
    from server.app.database.models import SuperAdminAccount
    
    admin = SuperAdminAccount(
        name="Super Admin",
        email="admin@automatia.com",
        hashed_password="hashed_dummy_pw"
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    
    assert admin.admin_id is not None
    assert admin.email == "admin@automatia.com"
    assert admin.is_active is True
    assert isinstance(admin.created_at, datetime)

@pytest.mark.asyncio
async def test_email_uniqueness(session):
    """Test that email must be unique."""
    from server.app.database.models import SuperAdminAccount
    
    admin1 = SuperAdminAccount(
        name="Admin 1",
        email="duplicate@test.com",
        hashed_password="pw1"
    )
    session.add(admin1)
    await session.commit()
    
    admin2 = SuperAdminAccount(
        name="Admin 2",
        email="duplicate@test.com",
        hashed_password="pw2"
    )
    session.add(admin2)
    
    with pytest.raises(IntegrityError):
        await session.commit()

@pytest.mark.asyncio
async def test_email_normalization(session):
    """Test that email is normalized to lowercase (logic should be in service or model)."""
    # Note: If we want the model to handle this, we can add a validator.
    from server.app.database.models import SuperAdminAccount
    
    admin = SuperAdminAccount(
        name="Case Test",
        email="UPPER@test.com",
        hashed_password="pw"
    )
    # Check if we implement normalization in model initializer or validator
    # For now, let's see if it works
    assert admin.email == "upper@test.com"

@pytest.mark.asyncio
async def test_password_hashing_integration():
    """Test utility of hashing separately or inside the model if implemented there."""
    from server.app.core.security import hash_password, verify_password
    
    raw_pw = "secret123"
    hashed = hash_password(raw_pw)
    
    assert hashed != raw_pw
    assert verify_password(raw_pw, hashed) is True
    assert verify_password("wrong", hashed) is False
