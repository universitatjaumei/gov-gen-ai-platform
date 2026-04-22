import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.models import FlowRegistry
from automatia_shared.dtos import FlowSpec
# Service to be implemented
from app.services.flow_registry_service import FlowRegistryService, OptimisticLockError

@pytest.fixture
async def db_session(test_client_db):
    """Fixture para crear sesión async a partir del engine de test"""
    async_session = sessionmaker(
        test_client_db, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.fixture
def service(db_session):
    return FlowRegistryService(db_session)

@pytest.mark.asyncio
async def test_create_flow(service):
    spec = FlowSpec(
        name="Test Flow",
        steps=[],
        owner_scope="partner_123"
    )
    created = await service.create_flow(spec)
    assert created.id is not None
    assert created.name == "Test Flow"
    assert created.version == "0.1.0"
    assert created.status == "DRAFT"
    assert created.row_version == 0
    assert created.owner_scope == "partner_123"

@pytest.mark.asyncio
async def test_get_flow(service):
    spec = FlowSpec(name="Get Me", steps=[])
    created = await service.create_flow(spec)
    
    fetched = await service.get_flow(created.id)
    assert fetched is not None
    assert fetched.name == "Get Me"

@pytest.mark.asyncio
async def test_list_flows_filter(service):
    await service.create_flow(FlowSpec(name="F1", status="DRAFT", owner_scope="A"))
    await service.create_flow(FlowSpec(name="F2", status="PUBLISHED", owner_scope="A"))
    await service.create_flow(FlowSpec(name="F3", status="DRAFT", owner_scope="B"))
    
    # Filter by status
    drafts = await service.list_flows(status="DRAFT")
    assert len(drafts) == 2
    
    # Filter by owner
    scope_a = await service.list_flows(owner_scope="A")
    assert len(scope_a) == 2
    
    # Filter by both
    draft_a = await service.list_flows(status="DRAFT", owner_scope="A")
    assert len(draft_a) == 1
    assert draft_a[0].name == "F1"

@pytest.mark.asyncio
async def test_update_flow_success(service):
    spec = FlowSpec(name="To Update", steps=[])
    created = await service.create_flow(spec)
    original_version = created.row_version
    
    # Update
    update_spec = FlowSpec(
        name="Updated Name",
        version="0.1.0", # same version logic, but generic for now
        row_version=original_version, # Correct row version
        steps=[]
    )
    
    updated = await service.update_flow(created.id, update_spec)
    assert updated.name == "Updated Name"
    assert updated.row_version == original_version + 1

@pytest.mark.asyncio
async def test_update_flow_optimistic_locking(service):
    spec = FlowSpec(name="Concurrency", steps=[])
    created = await service.create_flow(spec)
    original_v = created.row_version
    
    # Simulate first user update
    update1 = FlowSpec(name="U1", row_version=original_v, steps=[])
    await service.update_flow(created.id, update1)
    
    # Simulate second user trying to update with OLD row_version
    update2 = FlowSpec(name="U2", row_version=original_v, steps=[]) # old version 0
    
    with pytest.raises(OptimisticLockError):
        await service.update_flow(created.id, update2)

@pytest.mark.asyncio
async def test_delete_flow_soft(service):
    spec = FlowSpec(name="To Delete", steps=[])
    created = await service.create_flow(spec)
    
    await service.delete_flow(created.id)
    
    fetched = await service.get_flow(created.id)
    assert fetched.status == "DEPRECATED"
    # Or maybe we want is_active=False? Prompt said "Soft delete or status DEPRECATED"
    # Let's assume status DEPRECATED for now based on prompt Criterios.

