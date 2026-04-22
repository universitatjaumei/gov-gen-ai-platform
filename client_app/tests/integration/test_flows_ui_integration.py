import pytest
import pytest_asyncio
from app.services.flow_registry_service import FlowRegistryService
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

@pytest_asyncio.fixture
async def flow_registry(db_session):
    return FlowRegistryService(db_session)

@pytest.mark.asyncio
async def test_ui_can_list_saved_flows(flow_registry):
    """
    Test that the UI would be able to retrieve a list of flows.
    """
    # 1. Setup: Create a flow in DB
    flow = FlowSpec(
        name="UI Test Flow",
        description="Created for UI Test",
        steps=[]
    )
    await flow_registry.create_flow(flow)
    
    # 2. Simulate retrieval (what the UI would do)
    flows = await flow_registry.list_flows()
    
    # 3. Verify
    assert len(flows) >= 1
    # Check if our flow is in the list
    found = next((f for f in flows if f.name == "UI Test Flow"), None)
    assert found is not None
    assert found.description == "Created for UI Test"

@pytest.mark.asyncio
async def test_ui_can_save_new_flow(flow_registry):
    """
    Test that the UI would be able to save a new flow constructed by the user.
    """
    # 1. Simulate flow construction from UI inputs
    new_flow = FlowSpec(
        name="New Composer Flow",
        steps=[
            TaskSpec(
                name="Extraction Step",
                type=StepType.EXTRACTION,
                config={"target": "generic"}
            )
        ]
    )
    
    # 2. Save
    db_record = await flow_registry.create_flow(new_flow)
    assert db_record.id is not None
    
    # 3. Verify persistence
    stored = await flow_registry.get_flow(db_record.id)
    assert stored.name == "New Composer Flow"
    # Stored steps are JSON string in DB model
    import json
    steps_list = json.loads(stored.steps)
    assert len(steps_list) == 1
    assert steps_list[0]['type'] == 'extraction'

@pytest.mark.asyncio
async def test_ui_can_delete_flow(flow_registry):
    """
    Test flow deletion capability for the UI.
    """
    # 1. Create content
    flow = FlowSpec(name="To Delete", steps=[])
    db_flow = await flow_registry.create_flow(flow)
    flow_id = db_flow.id
    
    # 2. Delete
    success = await flow_registry.delete_flow(flow_id)
    assert success is True
    
    # 3. Verify marked as deprecated (soft delete)
    listing = await flow_registry.list_flows()
    found = next((f for f in listing if f.id == flow_id), None)
    assert found is not None
    assert found.status == "DEPRECATED"

