import pytest
from client_app.app.services.coherence_service import CoherenceService

def test_analyze_issues_generates_create_step_action():
    # Input: MISSING_VAR issue
    issues = [{
        'type': 'MISSING_VAR',
        'var_name': 'invoice_id',
        'severity': 'CRITICAL',
        'msg': "Falta la variable 'invoice_id'"
    }]
    
    service = CoherenceService()
    suggestions = service.analyze_issues(issues)
    
    assert len(suggestions) == 1
    action = suggestions[0]
    
    assert action['title'] == "Variable no encontrada"
    assert "invoice_id" in action['description']
    assert action['action_label'] == "Crear paso de extracción"
    assert action['action_type'] == "CREATE_STEP"
    assert action['action_payload'] == {'output_var': 'invoice_id'}

def test_analyze_issues_handles_privacy_risk():
    # Input: PRIVACY_RISK issue (Simulated, though PrivacyGuardian currently doesn't output this type in HealthService, 
    # but we are designing the CoherenceService to handle it future-proof)
    issues = [{
        'type': 'PRIVACY_RISK',
        'var_name': 'email_address',
        'severity': 'WARNING',
        'msg': "Posible PII detectado"
    }]
    
    service = CoherenceService()
    suggestions = service.analyze_issues(issues)
    
    assert len(suggestions) == 1
    action = suggestions[0]
    
    assert "Privacidad" in action['title']
    assert action['action_label'] == "Anonimizar Datos"
    assert action['action_type'] == "ANONYMIZE_VAR"
