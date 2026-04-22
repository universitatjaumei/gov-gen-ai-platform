import pytest
from automatia_shared.dtos import TaskSpec, FlowSpec
from automatia_shared.enums import StepType
from client_app.app.services.health_service import WorkflowHealthService
from client_app.app.services.privacy_guardian import PrivacyGuardian

def test_task_spec_strict_contract():
    """Validates that TaskSpec adheres to the strict contract of Prompt 5.5"""
    task = TaskSpec(
        name="Strict Task",
        type=StepType.RPA_EXECUTE,
        inputs=["required_var"],
        outputs=["produced_var"],
        metadata={"ui_version": "2.0"}
    )
    
    # Verify fields exist and are typed correctly
    assert isinstance(task.inputs, list)
    assert "required_var" in task.inputs
    assert isinstance(task.outputs, list)
    assert "produced_var" in task.outputs
    assert isinstance(task.metadata, dict)
    assert task.metadata["ui_version"] == "2.0"

def test_migration_logic_inference():
    """Tests the extraction logic intended for the migration script."""
    from server.scripts.migrations.migrate_task_spec import extract_inputs_from_code, extract_outputs_from_code
    
    code = """
def execute(client_id, date_range):
    results = 100
    return {'total': results, 'status': 'ok'}
    """
    
    inputs = extract_inputs_from_code(code)
    outputs = extract_outputs_from_code(code)
    
    assert "client_id" in inputs
    assert "date_range" in inputs
    assert "total" in outputs
    assert "status" in outputs

def test_system_integrity_post_migration():
    """
    Simulates a post-migration scenario where a Flow has fully populated contracts.
    Verifies that Health and Privacy services utilize them correctly.
    """
    flow = FlowSpec(
        name="Migrated Flow",
        steps=[
            TaskSpec(name="Step 1", type=StepType.CUSTOM_SCRIPT, outputs=["email_address"]),
            TaskSpec(name="Step 2", type=StepType.EMAIL_SEND, inputs=["email_address"])
        ]
    )
    
    # Health Check
    health = WorkflowHealthService()
    issues = health.check_step(flow, 1)
    assert len(issues) == 0 # Contract fulfilled
    
    # Privacy Check on Data (Simulated runtime)
    guardian = PrivacyGuardian()
    sanitized, _ = guardian.anonymize("Sending to test@example.com")
    assert "[EMAIL_1]" in sanitized
