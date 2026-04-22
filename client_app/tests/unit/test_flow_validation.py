import pytest
from client_app.app.services.flow_validation_service import FlowValidationService, flow_validation_service
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

def test_validate_valid_flow():
    """Un flujo completo debe ser válido"""
    flow = FlowSpec(
        name="Flow Válido",
        steps=[
            TaskSpec(name="Extr", type=StepType.EXTRACTION, config={'config_id': '123'}),
            TaskSpec(name="RPA", type=StepType.NAVIGATION, config={'playbook_id': 456})
        ]
    )
    errors = flow_validation_service.validate_flow(flow)
    assert len(errors) == 0

def test_validate_empty_flow():
    """Un flujo sin nombre o pasos debe fallar"""
    flow = FlowSpec(name="", steps=[])
    errors = flow_validation_service.validate_flow(flow)
    assert len(errors) >= 2  # Falta nombre y falta pasos

def test_validate_extraction_missing_config():
    """EXTRACTION requiere config_id"""
    step = TaskSpec(name="Extr", type=StepType.EXTRACTION, config={})
    error = flow_validation_service.validate_step(step)
    assert error is not None
    assert "requiere seleccionar una configuración" in error

def test_validate_rpa_missing_playbook():
    """RPA requiere playbook_id"""
    step = TaskSpec(name="RPA", type=StepType.NAVIGATION, config={})
    error = flow_validation_service.validate_step(step)
    assert error is not None
    assert "requiere seleccionar un playbook" in error

def test_validate_script_missing_id():
    """CUSTOM_SCRIPT requiere script_id"""
    step = TaskSpec(name="Script", type=StepType.CUSTOM_SCRIPT, config={})
    error = flow_validation_service.validate_step(step)
    assert error is not None
    assert "requiere seleccionar un script" in error

def test_validate_email_imap_missing_creds():
    """EMAIL input requiere credential_id"""
    step = TaskSpec(name="IMAP", type=StepType.EMAIL, config={'mode': 'input'})
    error = flow_validation_service.validate_step(step)
    assert error is not None
    assert "requiere seleccionar credenciales" in error

def test_validate_email_send_missing_fields():
    """EMAIL_SEND requiere to y credential_id"""
    # Caso 1: Falta to
    step = TaskSpec(name="SMTP", type=StepType.EMAIL_SEND, config={'credential_id': 1})
    error = flow_validation_service.validate_step(step)
    assert error is not None
    assert "requiere destinatarios" in error
    
    # Caso 2: Falta credencial
    step2 = TaskSpec(name="SMTP", type=StepType.EMAIL_SEND, config={'to': 'a@b.c'})
    error = flow_validation_service.validate_step(step2)
    assert error is not None
    assert "requiere seleccionar credencial" in error

def test_validate_etl_transform_missing_script():
    """ETL_TRANSFORM requiere script_id"""
    step = TaskSpec(name="ETL", type=StepType.ETL_TRANSFORM, config={})
    error = flow_validation_service.validate_step(step)
    assert error is not None
    assert "requiere seleccionar un script ETL" in error

def test_validate_report_missing_template():
    """REPORT_GENERATE requiere template"""
    step = TaskSpec(name="Report", type=StepType.REPORT_GENERATE, config={})
    error = flow_validation_service.validate_step(step)
    assert error is not None
    assert "requiere seleccionar un template" in error

def test_validate_api_missing_url():
    """API_FETCH requiere url o endpoint_id"""
    step = TaskSpec(name="API", type=StepType.API_FETCH, config={})
    error = flow_validation_service.validate_step(step)
    assert error is not None
    assert "requiere una URL" in error


# ============================================================================
# Prompt 2.1: Tests para StepValidationError y validación detallada
# ============================================================================

class TestStepValidationDetailed:
    """Tests para la validación detallada de pasos con StepValidationError."""

    def test_validate_step_api_fetch_requires_url(self):
        """API_FETCH sin URL es inválido - retorna StepValidationError."""
        from client_app.app.services.flow_validation_service import StepValidationError

        step = TaskSpec(name="Llamada API", type=StepType.API_FETCH, config={})
        errors = flow_validation_service.validate_step_detailed(step)

        assert len(errors) >= 1
        url_error = next((e for e in errors if e.field_name == "url"), None)
        assert url_error is not None
        assert url_error.severity == "error"
        assert "URL" in url_error.message or "url" in url_error.message.lower()

    def test_validate_step_api_fetch_valid(self):
        """API_FETCH con URL válida no genera errores."""
        step = TaskSpec(
            name="Llamada API",
            type=StepType.API_FETCH,
            config={"url": "https://api.ejemplo.com/datos"}
        )
        errors = flow_validation_service.validate_step_detailed(step)

        assert len(errors) == 0

    def test_validate_step_email_send_requires_recipients(self):
        """EMAIL_SEND sin destinatarios es inválido."""
        from client_app.app.services.flow_validation_service import StepValidationError

        step = TaskSpec(
            name="Enviar Email",
            type=StepType.EMAIL_SEND,
            config={"credential_id": 1, "subject": "Test"}
        )
        errors = flow_validation_service.validate_step_detailed(step)

        assert len(errors) >= 1
        to_error = next((e for e in errors if e.field_name == "to"), None)
        assert to_error is not None
        assert to_error.severity == "error"

    def test_validate_step_email_send_requires_subject(self):
        """EMAIL_SEND sin asunto es inválido."""
        from client_app.app.services.flow_validation_service import StepValidationError

        step = TaskSpec(
            name="Enviar Email",
            type=StepType.EMAIL_SEND,
            config={"credential_id": 1, "to": "user@example.com"}
        )
        errors = flow_validation_service.validate_step_detailed(step)

        assert len(errors) >= 1
        subject_error = next((e for e in errors if e.field_name == "subject"), None)
        assert subject_error is not None
        assert subject_error.severity == "error"

    def test_validate_step_email_send_valid(self):
        """EMAIL_SEND con todos los campos es válido."""
        step = TaskSpec(
            name="Enviar Email",
            type=StepType.EMAIL_SEND,
            config={
                "credential_id": 1,
                "to": "user@example.com",
                "subject": "Asunto del correo"
            }
        )
        errors = flow_validation_service.validate_step_detailed(step)

        assert len(errors) == 0

    def test_validate_step_extraction_requires_config(self):
        """EXTRACTION sin config_id es inválido."""
        from client_app.app.services.flow_validation_service import StepValidationError

        step = TaskSpec(name="Extracción", type=StepType.EXTRACTION, config={})
        errors = flow_validation_service.validate_step_detailed(step)

        assert len(errors) >= 1
        config_error = next((e for e in errors if e.field_name == "config_id"), None)
        assert config_error is not None
        assert config_error.severity == "error"

    def test_validate_step_custom_script_requires_script(self):
        """CUSTOM_SCRIPT sin script_id es inválido."""
        from client_app.app.services.flow_validation_service import StepValidationError

        step = TaskSpec(name="Script", type=StepType.CUSTOM_SCRIPT, config={})
        errors = flow_validation_service.validate_step_detailed(step)

        assert len(errors) >= 1
        script_error = next((e for e in errors if e.field_name == "script_id"), None)
        assert script_error is not None
        assert script_error.severity == "error"

    def test_validate_step_navigation_requires_playbook(self):
        """NAVIGATION sin playbook_id es inválido."""
        from client_app.app.services.flow_validation_service import StepValidationError

        step = TaskSpec(name="RPA", type=StepType.NAVIGATION, config={})
        errors = flow_validation_service.validate_step_detailed(step)

        assert len(errors) >= 1
        playbook_error = next((e for e in errors if e.field_name == "playbook_id"), None)
        assert playbook_error is not None
        assert playbook_error.severity == "error"

    def test_validate_step_returns_field_errors(self):
        """Los errores indican qué campo falta con estructura StepValidationError."""
        from client_app.app.services.flow_validation_service import StepValidationError

        # Paso con múltiples campos faltantes
        step = TaskSpec(
            name="Email incompleto",
            type=StepType.EMAIL_SEND,
            config={}  # Falta to, subject, credential_id
        )
        errors = flow_validation_service.validate_step_detailed(step)

        # Debe haber al menos 2 errores (to y subject son obligatorios según prompt)
        assert len(errors) >= 2

        # Verificar estructura de cada error
        for error in errors:
            assert isinstance(error, StepValidationError)
            assert error.field_name is not None
            assert error.message is not None
            assert error.severity in ("error", "warning")

    def test_validate_all_steps_returns_summary(self):
        """validate_all_steps retorna Dict[int, List[StepValidationError]]."""
        from client_app.app.services.flow_validation_service import StepValidationError

        flow = FlowSpec(
            name="Flujo de prueba",
            steps=[
                # Paso 0: Válido
                TaskSpec(
                    name="Extracción OK",
                    type=StepType.EXTRACTION,
                    config={"config_id": "123"}
                ),
                # Paso 1: Inválido (falta URL)
                TaskSpec(
                    name="API sin URL",
                    type=StepType.API_FETCH,
                    config={}
                ),
                # Paso 2: Inválido (falta script_id)
                TaskSpec(
                    name="Script sin ID",
                    type=StepType.CUSTOM_SCRIPT,
                    config={}
                ),
                # Paso 3: Válido
                TaskSpec(
                    name="RPA OK",
                    type=StepType.NAVIGATION,
                    config={"playbook_id": 456}
                ),
            ]
        )

        errors_by_step = flow_validation_service.validate_all_steps(flow)

        # Debe ser un diccionario
        assert isinstance(errors_by_step, dict)

        # Paso 0 no debe tener errores (o no estar en el dict)
        assert len(errors_by_step.get(0, [])) == 0

        # Paso 1 debe tener errores
        assert len(errors_by_step.get(1, [])) >= 1
        assert any(e.field_name == "url" for e in errors_by_step.get(1, []))

        # Paso 2 debe tener errores
        assert len(errors_by_step.get(2, [])) >= 1
        assert any(e.field_name == "script_id" for e in errors_by_step.get(2, []))

        # Paso 3 no debe tener errores
        assert len(errors_by_step.get(3, [])) == 0

    def test_validate_all_steps_empty_flow(self):
        """validate_all_steps con flujo vacío retorna diccionario vacío."""
        flow = FlowSpec(name="Flujo vacío", steps=[])
        errors_by_step = flow_validation_service.validate_all_steps(flow)

        assert isinstance(errors_by_step, dict)
        assert len(errors_by_step) == 0

    def test_step_validation_error_structure(self):
        """StepValidationError tiene los campos requeridos."""
        from client_app.app.services.flow_validation_service import StepValidationError

        error = StepValidationError(
            step_index=0,
            field_name="url",
            message="La URL es obligatoria",
            severity="error"
        )

        assert error.step_index == 0
        assert error.field_name == "url"
        assert error.message == "La URL es obligatoria"
        assert error.severity == "error"
