import pytest
from client_app.app.services.bridge_creator import BridgeService
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

def test_bridge_injection_logic():
    # Flujo original: A -> B (donde B falla porque falta un dato)
    task_a = TaskSpec(name="Origen", type=StepType.API_CONNECTOR, outputs=["json_data"])
    task_b = TaskSpec(name="Destino", type=StepType.CUSTOM_SCRIPT, inputs=["df_rows"])
    
    flow = FlowSpec(name="Test Flow", steps=[task_a, task_b])
    
    bridge = BridgeService(flow)
    
    # El código que supuestamente devuelve la IA
    generated_code = "def transform(data): return {'df_rows': []}"
    
    # Ejecutamos la inyección entre el paso 0 y 1
    new_flow = bridge.inject_bridge_task(
        at_index=1, 
        code=generated_code, 
        inputs=["json_data"], 
        outputs=["df_rows"]
    )
    
    assert len(new_flow.steps) == 3
    assert new_flow.steps[1].type == StepType.CUSTOM_SCRIPT
    assert "transform" in new_flow.steps[1].script_code
    assert new_flow.steps[1].name == "Puente de Transformación"
    assert new_flow.steps[1].metadata.get('is_bridge') is True
