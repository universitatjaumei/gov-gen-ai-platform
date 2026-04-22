import pytest
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.form_factory import AtomColorScheme
from automatia_shared.enums import StepType

def test_connection_color_schemes():
    """Verifica que los nuevos tipos de conexión tengan colores asignados."""
    connection_types = [
        StepType.API_FETCH,
        StepType.EMAIL,
        StepType.SQL_QUERY,
        StepType.WEBHOOK,
        StepType.CONNECTION
    ]
    
    for ctype in connection_types:
        colors = AtomColorScheme.get_colors(ctype)
        assert colors is not None
        assert 'icon' in colors
        assert 'primary' in colors
        # Ensure it's not the fallback (CUSTOM_SCRIPT uses indigo)
        if ctype != StepType.CUSTOM_SCRIPT:
            assert 'indigo' not in colors['primary']

def test_layout_manager_transitions_for_connections():
    """Verifica que el LayoutManager cambie de estado correctamente para conexiones."""
    connection_types = [
        StepType.API_FETCH,
        StepType.EMAIL,
        StepType.SQL_QUERY,
        StepType.WEBHOOK,
        StepType.CONNECTION
    ]
    
    for ctype in connection_types:
        layout_manager.exit_focus_mode()
        assert layout_manager.current_mode is None
        
        # Enter Design Mode
        layout_manager.enter_design_mode(ctype, atom_id=123)
        assert layout_manager.current_mode == 'design'
        assert layout_manager.drawer_visible is True
        assert layout_manager.menu_mini_mode is True
        
        # Enter Execution Mode
        layout_manager.enter_execution_mode(atom_id=123)
        assert layout_manager.current_mode == 'execution'
        assert layout_manager.drawer_visible is False
        assert layout_manager.menu_mini_mode is False
        
        layout_manager.exit_focus_mode()
        assert layout_manager.current_mode is None
