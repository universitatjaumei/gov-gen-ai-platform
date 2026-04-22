import pytest
from unittest.mock import AsyncMock, MagicMock
from automatia_shared.core.execution_manager import ExecutionManager, WorkflowContext, MissingDataDependency
from automatia_shared.dtos import TaskSpec, StepType

@pytest.mark.asyncio
async def test_workflow_context_persistence():
    """Verifica que el contexto almacena y recupera resultados."""
    ctx = WorkflowContext(execution_id="test_run_1")
    ctx.set_output("step_1", {"data": "hello"})
    
    assert ctx.get_output("step_1") == {"data": "hello"}
    assert ctx.execution_id == "test_run_1"

@pytest.mark.asyncio
async def test_input_resolution():
    """Verifica que los inputs del TaskSpec se resuelven desde el contexto."""
    manager = ExecutionManager()
    ctx = WorkflowContext("run_2")
    
    # Simular output previo
    ctx.set_output("step_pre", "my_file.csv")
    
    # Task que requiere ese input
    task = TaskSpec(
        name="Process CSV",
        type=StepType.ETL,
        inputs=["step_pre"], # Declare dependency
        config={}
    )
    
    # Resolver inputs
    resolved = manager.resolve_inputs(task, ctx)
    assert resolved["step_pre"] == "my_file.csv"

@pytest.mark.asyncio
async def test_missing_dependency_error():
    """Verifica que lanza error si falta un dato requerido."""
    manager = ExecutionManager()
    ctx = WorkflowContext("run_3")
    
    task = TaskSpec(
        name="Process Missing",
        type=StepType.ETL,
        inputs=["missing_step"],
        config={}
    )
    
    with pytest.raises(MissingDataDependency):
        manager.resolve_inputs(task, ctx)

@pytest.mark.asyncio
async def test_step_execution_delegation():
    """Verifica que el Manager delega al ejecutor correcto."""
    manager = ExecutionManager()
    
    mock_executor = AsyncMock(return_value="executed")
    manager.register_executor(StepType.ETL, mock_executor)
    
    ctx = WorkflowContext("run_4")
    task = TaskSpec(name="Test Step", type=StepType.ETL, inputs=[], config={})
    
    result = await manager.execute_step(task, ctx)
    
    assert result == "executed"
    mock_executor.assert_called_once()
