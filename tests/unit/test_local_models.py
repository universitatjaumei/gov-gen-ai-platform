"""
Tests unitarios para modelos locales y cifrado (PROMPT 02).

TDD: Estos tests se escriben ANTES de completar la implementación.
"""
import pytest
from datetime import datetime


def test_server_connection_model():
    """Verificar modelo ServerConnection"""
    from client_app.app.database.models import ServerConnection

    conn = ServerConnection(
        brain_url="https://brain.test.com/api",
        license_key="test_license_key_12345",
        is_active=True
    )
    assert conn.brain_url == "https://brain.test.com/api"
    assert conn.license_key == "test_license_key_12345"
    assert conn.is_active is True


def test_local_credentials_model():
    """Verificar modelo LocalCredentials"""
    from client_app.app.database.models import LocalCredentials

    cred = LocalCredentials(
        service_name="Gmail IMAP",
        encrypted_data="encrypted_json_data_here"
    )
    assert cred.service_name == "Gmail IMAP"
    assert cred.encrypted_data == "encrypted_json_data_here"


def test_encryption_service_encrypt_decrypt_cycle():
    """Verificar ciclo completo de cifrado/descifrado"""
    from client_app.app.modules.security.encryption_service import EncryptionService

    service = EncryptionService()
    original = {"user": "admin", "pass": "secret123", "server": "imap.gmail.com"}

    encrypted = service.encrypt(original)
    decrypted = service.decrypt(encrypted)

    assert decrypted == original
    assert encrypted != str(original)  # Debe estar cifrado


def test_encryption_service_encrypted_is_not_plaintext():
    """Verificar que datos cifrados no son texto plano"""
    from client_app.app.modules.security.encryption_service import EncryptionService

    service = EncryptionService()
    data = {"password": "super_secret_password_123"}

    encrypted = service.encrypt(data)

    # El texto cifrado no debe contener la contraseña en texto plano
    assert "super_secret_password_123" not in encrypted


def test_flow_registry_model():
    """Verificar modelo FlowRegistry"""
    from client_app.app.database.models import FlowRegistry

    flow = FlowRegistry(
        name="Email to ERP Flow",
        description="Process invoices from email",
        trigger_type="email",
        trigger_config='{"sender_whitelist": ["invoices@example.com"]}',
        steps='[{"type": "extraction", "script_id": "uuid1"}]',
        is_active=True
    )
    assert flow.name == "Email to ERP Flow"
    assert flow.trigger_type == "email"
    assert flow.is_active is True


def test_task_log_model():
    """Verificar modelo TaskLog"""
    from client_app.app.database.models import TaskLog
    from automatia_shared.enums import TaskStatus

    log = TaskLog(
        execution_id="exec_001",
        step_index=0,
        step_name="Extract Invoice Data",
        status=TaskStatus.IN_PROGRESS.value
    )
    assert log.execution_id == "exec_001"
    assert log.step_index == 0
    assert log.status == "in_progress"


def test_validation_history_model():
    """Verificar modelo ValidationHistory"""
    from client_app.app.database.models import ValidationHistory

    history = ValidationHistory(
        task_id="task_001",
        attempt_number=1,
        user_action="retry",
        feedback="El DNI no se extrajo correctamente"
    )
    assert history.task_id == "task_001"
    assert history.user_action == "retry"
    assert history.feedback == "El DNI no se extrajo correctamente"


def test_security_policy_model():
    """Verificar modelo SecurityPolicy"""
    from client_app.app.database.models import SecurityPolicy

    policy = SecurityPolicy(
        name="Default Policy",
        allowed_domains='["example.com", "trusted.com"]',
        allowed_imports='["pandas", "json", "re"]',
        max_execution_time=300,
        max_memory_mb=512
    )
    assert policy.name == "Default Policy"
    assert policy.max_execution_time == 300
    assert policy.max_memory_mb == 512


def test_api_endpoint_config_model():
    """Verificar modelo APIEndpointConfig"""
    from client_app.app.database.models import APIEndpointConfig

    endpoint = APIEndpointConfig(
        name="CRM API",
        url="https://api.crm.com/v1/clients",
        method="GET",
        auth_type="bearer",
        response_format="json"
    )
    assert endpoint.name == "CRM API"
    assert endpoint.url == "https://api.crm.com/v1/clients"
    assert endpoint.method == "GET"
    assert endpoint.auth_type == "bearer"


def test_trusted_script_model():
    """Verificar modelo TrustedScript (servidor)"""
    from server.app.database.models import TrustedScript

    script = TrustedScript(
        script_id="script_001",
        name="Invoice Extractor v1",
        code="def extraer_datos(filename): pass",
        code_hash="abc123hash",
        status="draft"
    )
    assert script.script_id == "script_001"
    assert script.name == "Invoice Extractor v1"
    assert script.status == "draft"
