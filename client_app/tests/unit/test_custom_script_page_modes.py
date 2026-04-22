import pytest
from client_app.app.services.layout_manager import LayoutManager
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme

def test_custom_script_color_scheme():
    """Verifica que el esquema de colores para Custom Script sea Indigo/Código."""
    colors = AtomColorScheme.get_colors(StepType.CUSTOM_SCRIPT)
    assert 'indigo' in colors['primary']
    assert 'indigo' in colors['border']
    assert colors['icon'] == '💻'

def test_layout_manager_design_mode_for_custom_script():
    """Verifica que LayoutManager entra en modo diseño para Custom Scripts."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset
    
    lm.enter_design_mode(StepType.CUSTOM_SCRIPT, atom_id="cs_123")
    
    assert lm.current_mode == 'design'
    assert lm.drawer_visible is True
    assert lm.menu_mini_mode is True

def test_layout_manager_execution_mode_for_custom_script():
    """Verifica que LayoutManager entra en modo ejecución para Custom Scripts."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset
    
    lm.enter_execution_mode(atom_id="cs_456")
    
    assert lm.current_mode == 'execution'
    assert lm.drawer_visible is False
    assert lm.menu_mini_mode is False
