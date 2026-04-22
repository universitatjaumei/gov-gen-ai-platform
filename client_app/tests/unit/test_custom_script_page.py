
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys

# We need to ensure we can import the page module, 
# assuming 'client_app.app.ui.custom_script_page' is reachable 
# or we patch sys.modules first if even that fails (but previous tests passed so it's likely fine).

@pytest.fixture
def wizard_state():
    # We patch the dependencies of custom_script_page BEFORE importing it (or reload it)
    # But since it is a script, best is to patch imports used inside the functions dynamically.
    from client_app.app.ui.custom_script_page import WizardState
    return WizardState()

@pytest.mark.asyncio
async def test_wizard_state_initialization(wizard_state):
    assert wizard_state.phase == "description"
    assert wizard_state.user_prompt == ""
    assert wizard_state.output_type == "file"
    assert wizard_state.generated_script is None

@pytest.mark.asyncio
async def test_wizard_validation(wizard_state):
    wizard_state.user_prompt = "Short"
    assert wizard_state.can_generate() is False
    
    wizard_state.user_prompt = "Quiero analizar un archivo CSV de ventas y sacar graficos."
    assert wizard_state.can_generate() is True

@pytest.mark.asyncio
async def test_wizard_transition(wizard_state):
    wizard_state.user_prompt = "Valid prompt for generation."
    wizard_state.phase = "generation"
    assert wizard_state.phase == "generation"

@pytest.mark.asyncio
async def test_generation_flow(wizard_state):
    mock_result = {
        "success": True,
        "code": "print('gen')",
        "description": "Generated Code",
        "required_libraries": []
    }
    
    with patch("client_app.app.ui.custom_script_page.script_generator_service.generate_script", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_result
        
        wizard_state.user_prompt = "Make a script"
        result = await mock_gen(wizard_state.user_prompt)
        wizard_state.generated_script = result
        wizard_state.phase = "generation" 
        
        assert wizard_state.generated_script["code"] == "print('gen')"
        assert wizard_state.phase == "generation"

@pytest.mark.asyncio
async def test_testing_phase_execution(wizard_state):
    """Test execution flow using sys.modules patching for unavailable dependencies."""
    wizard_state.phase = "testing"
    wizard_state.generated_script = {"code": "print('ok')"}
    
    mock_exec_result = {"success": True, "output_files": ["out.csv"]}
    
    # Create Mock Modules
    mock_sandbox_pkg = MagicMock()
    mock_service_class = MagicMock()
    mock_service_instance = MagicMock()
    mock_service_instance.execute_in_sandbox = AsyncMock(return_value=mock_exec_result)
    mock_service_class.return_value = mock_service_instance
    mock_sandbox_pkg.SandboxExecutionService = mock_service_class
    
    mock_shared_pkg = MagicMock()
    mock_exec_manager = MagicMock()
    mock_shared_pkg.core.execution_manager.ExecutionPathManager = mock_exec_manager

    # Patch sys.modules to inject mocks for the imports inside 'execute_test_logic'
    with patch.dict(sys.modules, {
        "app.services.sandbox_service": mock_sandbox_pkg,
        "automatia_shared.core.execution_manager": mock_shared_pkg.core.execution_manager
    }):
        # Import logic calling local imports
        from client_app.app.ui.custom_script_page import execute_test_logic
        
        await execute_test_logic(wizard_state, "input.csv", MagicMock())
        
        assert wizard_state.execution_result == mock_exec_result
        assert wizard_state.execution_status == "success"

@pytest.mark.asyncio
async def test_refinement_loop(wizard_state):
    """Test refinement logic (imports script_generator_service from module, so normal patch works)."""
    wizard_state.phase = "testing"
    wizard_state.generated_script = {"code": "old code"}
    wizard_state.iteration_count = 0
    wizard_state.execution_error = "Error X"
    
    mock_refine_result = {"success": True, "code": "new code", "description": "Fixed X"}
    
    with patch("client_app.app.ui.custom_script_page.script_generator_service.refine_script", new_callable=AsyncMock) as mock_refine:
        mock_refine.return_value = mock_refine_result
        
        from client_app.app.ui.custom_script_page import refine_logic
        
        await refine_logic(wizard_state, "Fix this error", MagicMock())
        
        assert wizard_state.generated_script["code"] == "new code"
        assert wizard_state.iteration_count == 1

@pytest.mark.asyncio
async def test_escalation_action(wizard_state):
    """Test escalation trigger."""
    wizard_state.current_script_id = 999
    wizard_state.feedback_text = "Help me please"
    
    # Mock the service imported inside the function
    mock_service_pkg = MagicMock()
    mock_svc = MagicMock()
    mock_svc.escalate_script = AsyncMock(return_value="esc_123")
    mock_service_pkg.custom_script_service = mock_svc
    
    with patch.dict(sys.modules, {"client_app.app.services.custom_script_service": mock_service_pkg}):
        from client_app.app.ui.custom_script_page import escalate_logic
        
        # We also need to mock ui.notify since logic calls it
        with patch("client_app.app.ui.custom_script_page.ui.notify") as mock_notify:
            await escalate_logic(wizard_state, MagicMock())
            
            mock_svc.escalate_script.assert_called_once()
            args = mock_svc.escalate_script.call_args
            assert args[0][0] == 999 # ID matched default in mock logic 
            assert args[1]['reason'] == "User Request"
            assert args[1]['client_notes'] == "Help me please"
            
            mock_notify.assert_called_with('Script escalado al Partner', type='positive')
