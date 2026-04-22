import pytest
from client_app.app.services.layout_manager import LayoutManager
from automatia_shared.enums import StepType

def test_layout_manager_design_mode_for_graphics():
    """Verifica que LayoutManager entra en modo diseño para gráficos."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset
    
    lm.enter_design_mode(StepType.REPORT_GENERATE, atom_id="chart_123")
    
    assert lm.current_mode == 'design'
    assert lm.drawer_visible is True
    assert lm.menu_mini_mode is True

def test_layout_manager_execution_mode_for_graphics():
    """Verifica que LayoutManager entra en modo ejecución para gráficos."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset
    
    lm.enter_execution_mode(atom_id="chart_456")
    
    assert lm.current_mode == 'execution'
    assert lm.drawer_visible is False
    assert lm.menu_mini_mode is False

def test_graphics_color_scheme():
    """Verifica que el esquema de colores de gráficos sea correcto (Rosa)."""
    from client_app.app.ui.components.form_factory import AtomColorScheme
    colors = AtomColorScheme.get_colors(StepType.REPORT_GENERATE)
    
    assert "pink" in colors['border'] or "pink" in colors['bg']
