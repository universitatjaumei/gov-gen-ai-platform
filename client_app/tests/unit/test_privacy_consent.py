import pytest
from client_app.app.services.privacy_guardian import PrivacyGuardian
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

def test_allow_execution_with_user_consent():
    # Scenario: PII flows to External Step
    task_a = TaskSpec(name="Source", type=StepType.PDF_EXTRACTION, outputs=["dni_empleado"])
    # "ERP_CONNECTOR" might not be in StepType enum yet, using valid external type or mocking
    # Assuming API_CONNECTOR is external.
    task_b = TaskSpec(name="Destination", type=StepType.API_CONNECTOR, inputs=["dni_empleado"])
    
    flow = FlowSpec(name="Test Flow", steps=[task_a, task_b])
    
    guardian = PrivacyGuardian()
    # Mock sensitive var identification
    guardian.sensitive_vars = {"Source.dni_empleado"} 
    
    # 1. Check without consent -> Should Block (Risk)
    issue = guardian.check_connection(flow, 0, 1)
    assert issue['is_risk'] is True
    assert issue['can_execute'] is False
    
    # 2. Grant Consent
    task_b.metadata['privacy_consent'] = True
    
    # 3. Check with consent -> Should Allow (Trusted Zone)
    issue_after = guardian.check_connection(flow, 0, 1)
    assert issue_after['is_risk'] is True # Still a risk technically
    assert issue_after['can_execute'] is True # But allowed
    assert issue_after['consent_granted'] is True
