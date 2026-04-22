import pytest
from client_app.app.ui.layout_state import LayoutState

def test_layout_initial_mode():
    state = LayoutState()
    # Reset singleton state
    state.view_mode = 'STANDARD'
    state.is_copilot_visible = False
    state.expert_mode = False
    state.suggestion_count = 0
    state.auto_opened = False
    
    assert state.view_mode == 'STANDARD'
    assert state.is_copilot_visible is False # El copiloto está oculto hasta que se necesite
    assert state.expert_mode is False # Por defecto simplificado

def test_layout_expert_toggle():
    state = LayoutState()
    assert state.expert_mode is False
    state.toggle_expert_mode()
    assert state.expert_mode is True
    state.toggle_expert_mode()
    assert state.expert_mode is False

def test_focus_mode_overlay_state():
    state = LayoutState()
    state.enter_focus_mode()
    
    # El layout debe saber que tiene algo encima para bloquear el scroll del fondo
    assert state.view_mode == 'FOCUS'
    assert "overflow-hidden" in state.main_container_classes
    assert "h-screen" in state.main_container_classes

def test_exit_focus_mode():
    state = LayoutState()
    state.enter_focus_mode()
    assert state.view_mode == 'FOCUS'
    
    state.exit_focus_mode()
    assert state.view_mode == 'STANDARD'
    assert "overflow-hidden" not in state.main_container_classes
