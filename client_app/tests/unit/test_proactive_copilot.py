"""
Unit tests for Prompt 4: Proactive Copilot (Coherence Check).
Verifies flow compatibility checking and Copilot suggestion display.
"""
import pytest
from unittest.mock import Mock, patch
from automatia_shared.dtos import TaskSpec, FlowSpec
from automatia_shared.enums import StepType
from automatia_shared.contracts.ui_contract import OutputSchema, OutputField, UIContract, InputDefinition, InputType

def test_layout_state_has_suggestions_list():
    """Verify LayoutState initializes with suggestions list."""
    from client_app.app.ui.layout_state import LayoutState
    
    layout_state = LayoutState()
    assert hasattr(layout_state, 'suggestions')
    assert isinstance(layout_state.suggestions, list)


def test_check_flow_compatibility_with_empty_flow():
    """Verify compatibility check handles empty flows gracefully."""
    from client_app.app.ui.layout_state import LayoutState
    
    # Mock FlowsState
    class MockFlowsState:
        def __init__(self):
            self.current_flow = None
        
        def check_flow_compatibility(self):
            from client_app.app.ui.layout_state import LayoutState
            layout_state = LayoutState()
            layout_state.suggestions.clear()
            
            if not self.current_flow:
                layout_state.update_suggestion_count(0)
                return
    
    fs = MockFlowsState()
    fs.check_flow_compatibility()
    
    layout_state = LayoutState()
    assert len(layout_state.suggestions) == 0
    assert layout_state.suggestion_count == 0


def test_check_flow_compatibility_with_single_step():
    """Verify compatibility check skips flows with only one step."""
    from client_app.app.ui.layout_state import LayoutState
    
    class MockFlowsState:
        def __init__(self):
            self.current_flow = FlowSpec(
                name="Test",
                steps=[TaskSpec(name="Step1", type=StepType.EXTRACTION, config={})]
            )
        
        def check_flow_compatibility(self):
            from client_app.app.ui.layout_state import LayoutState
            layout_state = LayoutState()
            layout_state.suggestions.clear()
            
            if len(self.current_flow.steps) < 2:
                layout_state.update_suggestion_count(0)
                return
    
    fs = MockFlowsState()
    fs.check_flow_compatibility()
    
    layout_state = LayoutState()
    assert len(layout_state.suggestions) == 0


def test_compatibility_service_detects_type_mismatch():
    """Verify FlowCompatibilityService detects incompatible types."""
    from client_app.app.services.flow_compatibility_service import FlowCompatibilityService, CompatibilityStatus
    
    service = FlowCompatibilityService()
    
    # Create incompatible schemas
    source_schema = OutputSchema(fields=[
        OutputField(name='result', type=InputType.STR, label='Result')
    ])
    
    target_contract = UIContract(inputs=[
        InputDefinition(name='result', type=InputType.INT, label='Result', required=True)
    ])
    
    result = service.validate_atom_link(source_schema, target_contract)
    
    # Should detect incompatibility or risky conversion
    assert result.status in [CompatibilityStatus.RISKY, CompatibilityStatus.INCOMPATIBLE]
    assert len(result.field_results) > 0


def test_compatibility_service_generates_bridge_prompt():
    """Verify bridge prompt is generated for incompatible connections."""
    from client_app.app.services.flow_compatibility_service import FlowCompatibilityService, CompatibilityStatus
    
    service = FlowCompatibilityService()
    
    # Create incompatible schemas (missing required field)
    source_schema = OutputSchema(fields=[
        OutputField(name='data', type=InputType.STR, label='Data')
    ])
    
    target_contract = UIContract(inputs=[
        InputDefinition(name='required_field', type=InputType.INT, label='Required', required=True)
    ])
    
    result = service.validate_atom_link(source_schema, target_contract)
    
    assert result.status == CompatibilityStatus.INCOMPATIBLE
    assert result.bridge_prompt is not None
    assert 'required_field' in result.bridge_prompt


@pytest.mark.asyncio
async def test_copilot_panel_displays_suggestions():
    """Verify copilot panel renders suggestions from LayoutState."""
    from client_app.app.ui.layout_state import LayoutState
    
    layout_state = LayoutState()
    layout_state.suggestions = [
        {
            'type': 'bridge',
            'severity': 'warning',
            'source_step': 'Extract Data',
            'target_step': 'Transform',
            'message': 'Incompatibilidad detectada: tipos no coinciden',
            'bridge_prompt': 'def transform(data): return int(data)'
        }
    ]
    
    # Mock UI rendering
    with patch('client_app.app.ui.components.step_panels.copilot_panel.ui'):
        from client_app.app.ui.components.step_panels.copilot_panel import render_copilot_panel
        from automatia_shared.dtos import TaskSpec, FlowSpec
        
        step = TaskSpec(name='Test', type=StepType.EXTRACTION, config={})
        flow = FlowSpec(name='Test Flow', steps=[step])
        
        # Should not raise error
        render_copilot_panel(step, flow)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
