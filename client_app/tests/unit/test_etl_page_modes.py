import pytest
from client_app.app.services.layout_manager import LayoutManager
from automatia_shared.enums import StepType

def test_layout_manager_design_mode_for_etl():
    """Verifica que LayoutManager entra en modo diseño para ETL."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset
    
    lm.enter_design_mode(StepType.ETL, atom_id="etl_123")
    
    assert lm.current_mode == 'design'
    assert lm.drawer_visible is True
    assert lm.menu_mini_mode is True

def test_layout_manager_execution_mode_for_etl():
    """Verifica que LayoutManager entra en modo ejecución para ETL."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset
    
    lm.enter_execution_mode(atom_id="etl_456")
    
    assert lm.current_mode == 'execution'
    assert lm.drawer_visible is False
    assert lm.menu_mini_mode is False

def test_etl_color_scheme():
    """Verifica que el esquema de colores de ETL sea correcto (Verde)."""
    from client_app.app.ui.components.form_factory import AtomColorScheme
    colors = AtomColorScheme.get_colors(StepType.ETL)
    
    assert "green" in colors['border'] or "green" in colors['bg']
