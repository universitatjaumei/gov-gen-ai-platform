import pytest
from client_app.app.ui.pill_logic import PillProvider, DataPill
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

def test_pill_provider_extracts_variables():
    # Creamos un flujo con un paso de extracción previo
    flow = FlowSpec(
        name="Test Flow", 
        steps=[
            TaskSpec(
                name="Extractor Facturas", 
                type=StepType.PDF_EXTRACTION,
                outputs=["total", "fecha", "cif"] # Campos que este paso genera
            ),
             TaskSpec(
                name="Paso Actual", 
                type=StepType.LLM_PROCESS,
                inputs=[]
            )
        ]
    )
    
    provider = PillProvider(flow)
    # Pedimos pills disponibles para el paso 1 (el segundo paso)
    pills = provider.get_available_pills(current_step_index=1)
    
    assert len(pills) == 3
    assert pills[0].label == "total"
    # El ID es opcional en la definicion actual de TaskSpec del servidor, 
    # pero para referencia necesitaria un ID. 
    # Como TaskSpec aqui no tiene ID obligatorio, usaremos el indice o nombre?
    # El prompt sugiere `step.id`. En DTO actual no hay ID explícito en TaskSpec?
    # Revisemos DTO. No tiene ID!
    # AÑADIREMOS ID MOCKEADO o usaremos el nombre normalizado.
    
    # Check Logic Implementation expectation:
    # If TaskSpec doesn't have ID, we might need to handle it.
    # For now, let's assume logic uses name or index if ID missing.
    
def test_pill_formatting():
    pill = DataPill(label="Importe Total", origin_step="PDF", var_name="total")
    assert pill.get_display_text() == "[PDF] Importe Total"
    assert pill.reference == "{{PDF.total}}"
