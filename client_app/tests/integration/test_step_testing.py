import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services import step_tester_service as service_module
from client_app.app.services.step_tester_service import step_tester_service
from automatia_shared.dtos import TaskSpec
from automatia_shared.enums import StepType

@pytest.mark.asyncio
async def test_run_single_step_success():
    """Debe ejecutar un paso individual y retornar resultado"""
    
    step = TaskSpec(
        name="Test ETL",
        type=StepType.ETL_TRANSFORM,
        config={'script_id': 1}
    )
    test_input = {"data": "test"}
    
    # We use patch.object on the module where WorkflowEngine is imported
    with patch.object(service_module, 'WorkflowEngine') as MockEngine, \
         patch.object(service_module, 'AsyncSession') as MockSession, \
         patch.object(service_module, 'client_engine'):
         
        # Setup Mock Engine
        mock_engine_instance = MockEngine.return_value
        # Important: Ensure _execute_task is an AsyncMock
        mock_engine_instance._execute_task = AsyncMock(return_value={"result": "transformed"})
        
        # Setup Mock Session
        mock_session_instance = MockSession.return_value
        mock_session_instance.__aenter__.return_value = AsyncMock()
        
        result = await step_tester_service.run_step(step, test_input)
        
        if not result['success']:
             with open("C:/Users/fabra/Documents/AutomatIA/test_debug_output_2.txt", "w") as f:
                f.write(f"ERROR: {result.get('error')}\nTRACE: {result.get('traceback')}")

        try:
            assert result['success'] is True
            assert result['output'] == {"result": "transformed"}
        except AssertionError as e:
            with open("C:/Users/fabra/Documents/AutomatIA/test_assertion_error.txt", "w") as f:
                f.write(f"Assertion failed: {e}\nResult was: {result}")
            raise

@pytest.mark.asyncio
async def test_run_single_step_error():
    """Debe capturar errores y retornarlos formateados"""
    
    step = TaskSpec(name="Fail", type=StepType.EXTRACTION, config={})
    
    with patch.object(service_module, 'WorkflowEngine') as MockEngine, \
         patch.object(service_module, 'AsyncSession') as MockSession, \
         patch.object(service_module, 'client_engine'):
        
        mock_engine_instance = MockEngine.return_value
        mock_engine_instance._execute_task = AsyncMock(side_effect=Exception("Simulated error"))
        
        mock_session_instance = MockSession.return_value
        mock_session_instance.__aenter__.return_value = AsyncMock()
        
        result = await step_tester_service.run_step(step, {})
        
        assert result['success'] is False
        assert 'error' in result
        assert "Simulated error" in result['error']
