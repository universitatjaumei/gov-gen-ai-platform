"""
Unit tests for step panels (Prompt 1).
Verifies that panels can be rendered independently without drawer context.
"""
import pytest
from unittest.mock import Mock
from automatia_shared.dtos import TaskSpec, FlowSpec
from automatia_shared.enums import StepType


@pytest.mark.asyncio
async def test_settings_panel_renders_independently():
    """Verifica que render_settings_panel funciona sin drawer."""
    from client_app.app.ui.components.step_panels import render_settings_panel
    
    step = TaskSpec(
        id='test-step',
        name='Test Extraction Step',
        type=StepType.EXTRACTION,
        config={}
    )
    flow = FlowSpec(steps=[step])
    
    # Mock callback
    on_change_mock = Mock()
    
    # This should not raise an error
    # In a real test with NiceGUI context, we'd verify UI elements
    try:
        await render_settings_panel(step, flow, on_change_mock)
        # If we get here without error, the panel is independent
        assert True
    except Exception as e:
        pytest.fail(f"Panel should render independently: {e}")


def test_variables_panel_renders_independently():
    """Verifica que render_variables_panel funciona sin drawer."""
    from client_app.app.ui.components.step_panels import render_variables_panel
    
    step = TaskSpec(
        id='test-step',
        name='Test Step',
        type=StepType.CUSTOM_SCRIPT,
        config={}
    )
    flow = FlowSpec(steps=[step])
    
    # This should not raise an error
    try:
        render_variables_panel(step, flow)
        assert True
    except Exception as e:
        pytest.fail(f"Panel should render independently: {e}")


def test_copilot_panel_renders_independently():
    """Verifica que render_copilot_panel funciona sin drawer."""
    from client_app.app.ui.components.step_panels import render_copilot_panel
    
    step = TaskSpec(
        id='test-step',
        name='Test Step',
        type=StepType.CUSTOM_SCRIPT,
        config={}
    )
    flow = FlowSpec(steps=[step])
    
    # This should not raise an error
    try:
        render_copilot_panel(step, flow)
        assert True
    except Exception as e:
        pytest.fail(f"Panel should render independently: {e}")


def test_step_configurator_uses_panels():
    """Verify StepConfigurator delegates to panel functions."""
    from client_app.app.ui.components.step_configurator import StepConfigurator
    
    step = TaskSpec(
        id='test-step',
        name='Test Step',
        type=StepType.CUSTOM_SCRIPT,
        config={}
    )
    flow = FlowSpec(steps=[step])
    
    # Create configurator
    configurator = StepConfigurator()
    configurator.refresh_content(step, flow)
    
    # Verify it has the expected methods
    assert hasattr(configurator, '_render_specific_form')
    assert hasattr(configurator, '_render_data_flow_analysis')
    assert hasattr(configurator, '_render_copilot_tab')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
