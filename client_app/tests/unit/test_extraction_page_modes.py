import pytest
from client_app.app.ui.extraction_page_refactored import ExtractionAtom
from client_app.app.services.layout_manager import LayoutManager
from automatia_shared.enums import StepType

def test_extraction_atom_initialization():
    """Verifica que ExtractionAtom se inicializa correctamente."""
    atom = ExtractionAtom(1, "Test Extractor", "Factura")
    assert atom.id == 1
    assert atom.name == "Test Extractor"
    assert atom.config['doc_type'] == "Factura"
    assert atom.config['ocr_enabled'] is True
    assert atom.step_type == StepType.EXTRACTION

def test_extraction_atom_default_last_run():
    """Verifica que last_run tiene un valor por defecto."""
    atom = ExtractionAtom(1, "Test", "DNI")
    assert atom.last_run == "Nunca"

def test_layout_manager_design_mode_for_extraction():
    """Verifica que LayoutManager entra en modo diseño para extracción."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset
    
    lm.enter_design_mode(StepType.EXTRACTION, atom_id=123)
    
    assert lm.current_mode == 'design'
    assert lm.drawer_visible is True
    assert lm.menu_mini_mode is True

def test_layout_manager_execution_mode_for_extraction():
    """Verifica que LayoutManager entra en modo ejecución para extracción."""
    lm = LayoutManager()
    lm.exit_focus_mode()  # Reset
    
    lm.enter_execution_mode(atom_id=456)
    
    assert lm.current_mode == 'execution'
    assert lm.drawer_visible is False
    assert lm.menu_mini_mode is False
