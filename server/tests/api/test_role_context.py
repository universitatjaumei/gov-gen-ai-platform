
import pytest
from fastapi import FastAPI, Depends, Header
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
import asyncio

from server.app.api.deps import get_current_active_user, get_session
from server.app.database.models import AdminAccount, PartnerAccount

app = FastAPI()

@app.get("/test-protected")
async def protected_route(user = Depends(get_current_active_user)):
    return {"user_type": type(user).__name__, "email": user.email}

@pytest.fixture(name="session")
async def session_fixture():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_admin_context_success(session):
    # 1. Setup Admin
    admin = AdminAccount(name="Admin", email="admin@test.com", hashed_password="pw")
    session.add(admin)
    await session.commit()
    
    # Override dependency
    app.dependency_overrides[get_session] = lambda: session
    
    client = TestClient(app)
    
    # Test Admin
    response = client.get(
        "/test-protected", 
        headers={"X-Role-Context": "admin", "Authorization": "Bearer admin@test.com"}
    )
    
    # Cleanup overrides for next tests if needed, but here we use session fixture per test
    del app.dependency_overrides[get_session]
    
    assert response.status_code == 200
    assert response.json()["user_type"] == "AdminAccount"
    assert response.json()["email"] == "admin@test.com"

@pytest.mark.asyncio
async def test_partner_context_success(session):
    # 1. Setup Partner
    partner = PartnerAccount(partner_id="p1", name="Partner", email="partner@test.com")
    session.add(partner)
    await session.commit()
    
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    
    # Test Partner
    response = client.get(
        "/test-protected", 
        headers={"X-Role-Context": "partner", "Authorization": "Bearer partner@test.com"}
    )
    
    del app.dependency_overrides[get_session]
    
    assert response.status_code == 200
    assert response.json()["user_type"] == "PartnerAccount"
    assert response.json()["email"] == "partner@test.com"

@pytest.mark.asyncio
async def test_missing_header_fail():
    client = TestClient(app)
    # FastAPI returns 422 for missing required headers
    response = client.get("/test-protected")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_invalid_role_fail(session):
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    response = client.get(
        "/test-protected", 
        headers={"X-Role-Context": "invalid", "Authorization": "Bearer any"}
    )
    del app.dependency_overrides[get_session]
    assert response.status_code == 400 # Bad Request
