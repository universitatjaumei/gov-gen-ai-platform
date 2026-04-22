import pytest
from client_app.app.ui.components.form_factory import AtomColorScheme, FormContext, FormFactory
from automatia_shared.enums import StepType
from dataclasses import dataclass

@dataclass
class MockStep:
    step_type: StepType
    name: str = ""
    config: dict = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}

def test_atom_color_scheme_mapping():
    """Verifica que los tipos de átomo clave tienen colores e iconos asignados."""
    types_to_check = [
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.RPA_EXECUTE,
        StepType.CUSTOM_SCRIPT,
        StepType.REPORT_GENERATE
    ]
    
    for st in types_to_check:
        colors = AtomColorScheme.get_colors(st)
        assert 'primary' in colors
        assert 'light' in colors
        assert 'border' in colors
        assert 'text' in colors
        assert 'icon' in colors
        assert len(colors['icon']) > 0

def test_form_context_defaults():
    """Verifica los valores por defecto del FormContext."""
    context = FormContext()
    assert context.mode == 'standalone'
    assert context.flow_id is None
    assert context.available_variables == []

def test_form_factory_render_extraction_classes():
    """
    Verifica que el renderizado de extracción aplica las clases de color correctas.
    Nota: Probamos la lógica de selección de clases, no el motor de renderizado de NiceGUI.
    """
    step = MockStep(step_type=StepType.EXTRACTION, name="Test Extractor")
    context = FormContext(mode='standalone')
    
    colors = AtomColorScheme.get_colors(StepType.EXTRACTION)
    
    # En un test unitario sin loop de NiceGUI, no podemos instanciar ui.card() fácilmente 
    # sin inicializar el cliente, pero podemos verificar la lógica de obtención de clases.
    assert colors['light'] == 'bg-blue-100'
    assert colors['border'] == 'border-blue-500'
    assert colors['text'] == 'text-blue-700'
    assert colors['icon'] == '📄'

def test_form_factory_fallback():
    """Verifica que tipos no implementados muestran un aviso."""
    # StepType.API_FETCH no está en el if de render_form actualmente
    step = MockStep(step_type=StepType.API_FETCH)
    context = FormContext()
    
    # No debería lanzar excepción
    FormFactory.render_form(step, context)
