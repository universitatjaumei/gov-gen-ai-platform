import pytest
from unittest.mock import AsyncMock, MagicMock
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType
from client_app.app.modules.runtime.workflow_engine import WorkflowEngine
from client_app.app.database.models import TaskLog
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def db_session(test_client_db):
    """Fixture para crear sesión async a partir del engine de test"""
    async_session = sessionmaker(
        test_client_db, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.fixture
def engine(db_session):
    return WorkflowEngine(db_session)

@pytest.mark.asyncio
async def test_linear_execution_flow(engine):
    flow = FlowSpec(
        name="Test Flow",
        steps=[
            TaskSpec(name="S1", type=StepType.EXTRACTION, config={"ret": "data1"}),
            TaskSpec(name="S2", type=StepType.ETL, config={"append": "_processed"}),
        ],
    )

    # Mock executors
    # We will need to patch the registry or the method. 
    # Since _execute_task is an internal method, we can mock it on the instance for this test
    # to test the orchestration flow separately from the actual executors.
    engine._execute_task = AsyncMock(side_effect=["data1", "data1_processed"])

    result = await engine.execute_flow(flow, context={})

    assert result["status"] == "completed"
    assert engine._execute_task.call_count == 2
    
@pytest.mark.asyncio
async def test_tasklog_created_for_each_step(engine, db_session):
    flow = FlowSpec(
        name="Log Test",
        steps=[
            TaskSpec(name="Step1", type=StepType.EXTRACTION, config={}),
        ],
    )
    engine._execute_task = AsyncMock(return_value={"ok": True})

    result = await engine.execute_flow(flow, context={})

    # Query logs
    # Note: db_session comes from the fixture wrapping our in-memory DB
    from sqlalchemy import select
    stmt = select(TaskLog).filter_by(execution_id=result["execution_id"])
    logs = (await db_session.execute(stmt)).scalars().all()
    
    assert len(logs) == 1
    assert logs[0].step_name == "Step1"
    assert logs[0].status == "completed"
    assert logs[0].duration_ms is not None

@pytest.mark.asyncio
async def test_stop_on_error_halts_execution(engine):
    flow = FlowSpec(
        name="Error Flow",
        steps=[
            TaskSpec(name="S1", type=StepType.EXTRACTION, config={}),
            TaskSpec(name="S2", type=StepType.ETL, config={}),
        ],
    )
    # S1 fails, S2 should not run
    engine._execute_task = AsyncMock(side_effect=[Exception("Fail"), "never_called"])

    result = await engine.execute_flow(flow, context={}, stop_on_error=True)

    assert result["status"] == "failed"
    assert engine._execute_task.call_count == 1

@pytest.mark.asyncio
async def test_retry_on_failure(engine):
    flow = FlowSpec(
        name="Retry Flow",
        steps=[
            # retries=2 means: initial attempt + up to 2 retries
            TaskSpec(name="S1", type=StepType.EXTRACTION, config={"retries": 2}),
        ],
    )

    # Fails 2 times, succeeds on 3rd (last attempt)
    engine._execute_task = AsyncMock(
        side_effect=[Exception("Fail1"), Exception("Fail2"), "success"]
    )

    result = await engine.execute_flow(flow, context={})

    assert result["status"] == "completed"
    assert engine._execute_task.call_count == 3

@pytest.mark.asyncio
async def test_output_passed_as_input_to_next_step(engine):
    flow = FlowSpec(
        name="Chain Flow",
        steps=[
            TaskSpec(name="S1", type=StepType.EXTRACTION, config={}),
            TaskSpec(name="S2", type=StepType.ETL, config={}),
        ],
    )

    async def mock_execute(task, context):
        if task.name == "S1":
            return {"extracted": "value"}
        elif task.name == "S2":
            # Verify S2 receives output from S1 in context
            assert context.get("previous_output") == {"extracted": "value"}
            return {"processed": True}
        return None

    engine._execute_task = mock_execute

    result = await engine.execute_flow(flow, context={})
    assert result["status"] == "completed"

