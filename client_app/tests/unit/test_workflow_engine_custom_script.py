
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from automatia_shared.dtos import TaskSpec
# We don't import WorkflowEngine yet

@pytest.fixture
def mock_engine_module():
    mock_custom_svc = MagicMock()
    mock_sandbox_svc = MagicMock()
    
    # Create a mock for the module imports
    with patch.dict(sys.modules, {
        "client_app.app.services.custom_script_service": MagicMock(custom_script_service=mock_custom_svc),
        "client_app.app.services.sandbox_service": MagicMock(sandbox_service=mock_sandbox_svc),
        "client_app.app.database.models": MagicMock()
    }):
        # Now import the module
        import client_app.app.modules.runtime.workflow_engine as engine_mod
        
        # Determine if we need to reload?
        # If it was already imported, StepRegistry is already populated.
        # But we want to test the executor function which uses the global imports.
        # Since we patched sys.modules, if we reload, it will pick up mocks.
        import importlib
        importlib.reload(engine_mod)
        
        yield engine_mod, mock_custom_svc, mock_sandbox_svc

@pytest.mark.asyncio
async def test_execute_custom_script_step(mock_engine_module):
    engine_mod, mock_custom_svc, mock_sandbox_svc = mock_engine_module
    
    # Setup Data
    script_id = 123
    script_code = "print('hello')"
    
    mock_script = MagicMock()
    mock_script.code = script_code
    mock_script.input_type = "file"
    mock_custom_svc.get_script = AsyncMock(return_value=mock_script)
    
    mock_exec_result = {"success": True, "output_files": ["out.csv"]}
    mock_sandbox_svc.execute = AsyncMock(return_value=mock_exec_result)
    mock_custom_svc.log_execution_start = AsyncMock(return_value=MagicMock(id=1))
    mock_custom_svc.log_execution_end = AsyncMock()
    
    # Get executor
    executor = engine_mod.StepRegistry.get("custom_script")
    assert executor is not None
    
    # Create Task Spec
    task = TaskSpec(
        name="Run Script",
        type="custom_script",
        config={
            "script_id": script_id,
            "input_mapping": {"file": "input.csv"}
        }
    )
    
    context = {"input.csv": "path/to/file.csv"} 
    
    # Execute
    result = await executor(task, context)
    
    # Assertions
    mock_custom_svc.get_script.assert_called_with(script_id)
    mock_sandbox_svc.execute.assert_awaited()
    assert result == "out.csv" # The logic returns the first output file if present
