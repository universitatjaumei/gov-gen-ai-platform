import pytest
from unittest.mock import MagicMock
from client_app.app.ui.focus_manager import FocusManager
from automatia_shared.dtos import TaskSpec

def test_focus_mode_toggle():
    manager = FocusManager()
    assert manager.is_active is False
    
    # Mock a TaskSpec with minimal required fields to pass validation
    step = TaskSpec(
        id='123', 
        type='etl', 
        name='Test ETL',
        status='pending',           # Required field
        inputs=[],                  # Required by new contract
        outputs=[]                  # Required by new contract
    )
    
    # Act: Enable focus
    manager.enable_focus(step)
    
    assert manager.is_active is True
    assert manager.current_step == step
    assert manager.current_step.type == 'etl'
    
    # Updated: Check layout state directly or via layout_classes dict keys
    # Old test used a getter, now we check the dict values
    assert manager.layout_classes['max-w-7xl'] is False
    assert manager.layout_classes['overflow-hidden'] is True
    
    # Assert Copilot auto-opened
    assert manager.layout_state.is_copilot_visible is True

def test_copilot_sidebar_visibility():
    manager = FocusManager()
    # Reset state from previous tests (Singleton)
    manager.disable_focus()
    
    # Default state
    assert manager.sidebar_state == 'summary'
    
    step = TaskSpec(
        id='456', 
        type='rpa_execute', 
        name='Test RPA',
        status='pending',
        inputs=[],
        outputs=[]
    )
    manager.enable_focus(step)
    
    # Upon entering focus, sidebar should become active assistant
    assert manager.sidebar_state == 'active_assistant'
    assert manager.layout_state.is_copilot_visible is True

def test_disable_focus():
    manager = FocusManager()
    step = TaskSpec(
        id='789', 
        type='extraction', 
        name='Test PDF',
        status='pending',
        inputs=[],
        outputs=[]
    )
    manager.enable_focus(step)
    
    manager.disable_focus()
    
    assert manager.is_active is False
    assert manager.current_step is None
    assert manager.sidebar_state == 'summary'
    assert manager.layout_classes['max-w-7xl'] is True
