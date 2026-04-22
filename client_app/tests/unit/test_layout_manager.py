import pytest
from client_app.app.services.layout_manager import LayoutManager
from automatia_shared.enums import StepType

def test_layout_manager_singleton():
    """Verificar que LayoutManager es un singleton."""
    lm1 = LayoutManager()
    lm2 = LayoutManager()
    assert lm1 is lm2

def test_initial_state():
    """Verificar el estado inicial de LayoutManager."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset to clean state
    assert lm.current_mode is None
    assert lm.drawer_visible is False
    assert lm.menu_mini_mode is False

def test_enter_design_mode():
    """Verificar que el modo diseño activa las banderas correctas."""
    lm = LayoutManager()
    lm.exit_focus_mode()
    
    lm.enter_design_mode(atom_type=StepType.EXTRACTION)
    
    assert lm.current_mode == 'design'
    assert lm.drawer_visible is True
    assert lm.menu_mini_mode is True

def test_enter_execution_mode():
    """Verificar que el modo ejecución desactiva el drawer."""
    lm = LayoutManager()
    lm.exit_focus_mode()
    
    lm.enter_execution_mode(atom_id=123)
    
    assert lm.current_mode == 'execution'
    assert lm.drawer_visible is False
    assert lm.menu_mini_mode is False

def test_exit_focus_mode():
    """Verificar el reset total de banderas al salir de focus."""
    lm = LayoutManager()
    lm.enter_design_mode(atom_type=StepType.EXTRACTION)
    
    lm.exit_focus_mode()
    
    assert lm.current_mode is None
    assert lm.drawer_visible is False
    assert lm.menu_mini_mode is False

def test_watcher_notification():
    """Verificar que los observadores son notificados de los cambios."""
    lm = LayoutManager()
    lm.exit_focus_mode()
    
    notifications = []
    def callback():
        notifications.append(True)
    
    lm.add_watcher(callback)
    
    lm.enter_design_mode(atom_type=StepType.EXTRACTION)
    assert len(notifications) == 1
    
    lm.exit_focus_mode()
    assert len(notifications) == 2
    
    lm.remove_watcher(callback)
    lm.enter_execution_mode(123)
    assert len(notifications) == 2  # No debería haber notificación extra
