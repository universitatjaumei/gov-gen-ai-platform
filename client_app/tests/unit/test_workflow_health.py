import pytest
from client_app.app.services.health_service import WorkflowHealthService
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

def test_health_check_detects_missing_variable():
    # Flujo con 2 pasos.
    # Paso 1: No genera nada.
    # Paso 2: Requiere "invoice_id".
    flow = FlowSpec(
        name="Broken Flow",
        steps=[
            TaskSpec(name="Step 1", type=StepType.RPA_EXECUTE, outputs=[]), 
            TaskSpec(name="Step 2", type=StepType.RPA_EXECUTE, inputs=["invoice_id"])
        ]
    )

def test_health_check_passes_valid_flow():
    # Flujo valido. Paso 1 genera "invoice_id". Paso 2 lo consume.
    flow = FlowSpec(
        name="Good Flow",
        steps=[
            TaskSpec(name="Step 1", type=StepType.RPA_EXECUTE, outputs=["invoice_id"]),
            TaskSpec(name="Step 2", type=StepType.RPA_EXECUTE, inputs=["invoice_id"])
        ]
    )
    
    service = WorkflowHealthService()
    issues = service.check_step(flow, 1)
    
    assert len(issues) == 0
