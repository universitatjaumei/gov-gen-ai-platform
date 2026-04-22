import pytest
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType
from client_app.app.ui.pill_logic import PillProvider
from client_app.app.services.health_service import WorkflowHealthService
from client_app.app.services.privacy_guardian import PrivacyGuardian

def test_system_consolidation_integrity():
    """
    Validates that:
    1. A Flow can be constructed with the new TaskSpec fields (inputs, outputs, metadata).
    2. Data Pills can be extracted from this Flow.
    3. Workflow Health can validate this Flow.
    4. Privacy Guardian can operate on data related to this Flow.
    """
    
    # 1. Construct Valid Flow
    flow = FlowSpec(
        name="Consolidated Logic Flow",
        steps=[
            TaskSpec(
                name="Extraction Step",
                type=StepType.PDF_EXTRACTION,
                outputs=["customer_email", "invoice_amount"],
                metadata={"ui_pos": "0,0"}
            ),
            TaskSpec(
                name="Email Step",
                type=StepType.EMAIL_SEND,
                inputs=["customer_email"],
                metadata={"ui_pos": "0,1"}
            )
        ]
    )
    
    # 2. Pill Logic Validation
    provider = PillProvider(flow)
    pills = provider.get_available_pills(current_step_index=1) # For Email Step
    assert len(pills) == 2
    assert any(p.label == "customer_email" for p in pills)
    
    # 3. Health Logic Validation
    health = WorkflowHealthService()
    issues = health.check_step(flow, 1) # Check Email Step
    assert len(issues) == 0 # Should pass as customer_email is provided
    
    # Simulate Error
    flow.steps[1].inputs.append("missing_var")
    issues_bad = health.check_step(flow, 1)
    assert len(issues_bad) == 1
    assert issues_bad[0]['type'] == 'MISSING_VAR'
    
    # 4. Privacy Logic Validation
    # Simulate that we got actual data for 'customer_email'
    real_data = "john.doe@example.com"
    guardian = PrivacyGuardian()
    sanitized, mapping = guardian.anonymize(f"Send to {real_data}")
    
    assert real_data not in sanitized
    assert "[EMAIL_1]" in sanitized
    assert guardian.deanonymize(sanitized, mapping) == f"Send to {real_data}"

    print("\n[SUCCESS] All logical pillars (Pills, Health, Privacy) operate correctly on the Unified DTO.")
