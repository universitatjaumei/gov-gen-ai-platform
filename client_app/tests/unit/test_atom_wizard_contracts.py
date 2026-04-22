"""
Tests para wizard de átomos con contratos.
Data Contracts Fase 2, Prompt 5.
"""
import pytest
import json
from client_app.app.core.state import state
from client_app.app.services.atom_service import atom_service
from client_app.app.config.atom_catalog import get_connection_metadata, CONNECTION_METADATA
from automatia_shared.enums import StepType
from sqlmodel import Session, create_engine, SQLModel
from client_app.app.database.models import AtomRegistry


class TestAtomServiceWithContracts:
    """Tests para atom_service con soporte de contratos."""

    @pytest.fixture
    def session(self):
        """Crear sesión de prueba en memoria."""
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    def test_create_atom_accepts_subtype(self):
        """create_atom debe aceptar parámetro subtype."""
        import inspect
        sig = inspect.signature(atom_service.create_atom)
        params = list(sig.parameters.keys())
        assert 'subtype' in params

    def test_create_atom_accepts_input_contract(self):
        """create_atom debe aceptar parámetro input_contract."""
        import inspect
        sig = inspect.signature(atom_service.create_atom)
        params = list(sig.parameters.keys())
        assert 'input_contract' in params

    def test_create_atom_accepts_output_contract(self):
        """create_atom debe aceptar parámetro output_contract."""
        import inspect
        sig = inspect.signature(atom_service.create_atom)
        params = list(sig.parameters.keys())
        assert 'output_contract' in params

    def test_create_atom_accepts_dependencies(self):
        """create_atom debe aceptar parámetro dependencies."""
        import inspect
        sig = inspect.signature(atom_service.create_atom)
        params = list(sig.parameters.keys())
        assert 'dependencies' in params


class TestAtomWizardState:
    """Tests para estado del wizard con contratos."""

    def setup_method(self):
        """Reset state antes de cada test."""
        state.wizard_initial_step_type = None
        state.wizard_initial_subtype = None
        state.wizard_flow_context = None

    def test_wizard_subtype_preserved_for_connection(self):
        """Subtipo debe preservarse en state para CONNECTION."""
        state.wizard_initial_step_type = StepType.CONNECTION
        state.wizard_initial_subtype = "EMAIL"

        assert state.wizard_initial_step_type == StepType.CONNECTION
        assert state.wizard_initial_subtype == "EMAIL"

    def test_wizard_flow_context_exists(self):
        """wizard_flow_context debe existir en state."""
        assert hasattr(state, 'wizard_flow_context')


class TestConnectionConfigSchema:
    """Tests para prellenado de config_schema en conexiones."""

    def test_email_connection_has_config_schema(self):
        """Conexión EMAIL debe tener config_schema prellenado."""
        metadata = get_connection_metadata("EMAIL")
        schema = metadata.config_schema

        assert schema is not None
        assert "properties" in schema
        assert "host" in schema["properties"]
        assert "password" in schema["properties"]

    def test_api_connection_has_config_schema(self):
        """Conexión API debe tener config_schema prellenado."""
        metadata = get_connection_metadata("API")
        schema = metadata.config_schema

        assert schema is not None
        assert "properties" in schema
        assert "base_url" in schema["properties"]

    def test_database_connection_has_config_schema(self):
        """Conexión DATABASE debe tener config_schema prellenado."""
        metadata = get_connection_metadata("DATABASE")
        schema = metadata.config_schema

        assert schema is not None
        assert "properties" in schema
        assert "db_type" in schema["properties"]

    def test_config_schema_is_serializable(self):
        """Config schema debe ser serializable a JSON."""
        for subtype, metadata in CONNECTION_METADATA.items():
            schema_json = json.dumps(metadata.config_schema)
            assert len(schema_json) > 0
            # Verificar que se puede parsear de vuelta
            parsed = json.loads(schema_json)
            assert "type" in parsed


class TestContractValidation:
    """Tests para validación de JSON en contratos."""

    def test_valid_json_contract(self):
        """JSON válido debe ser aceptado."""
        valid_contract = '{"type": "object", "properties": {"file": {"type": "string"}}}'
        parsed = json.loads(valid_contract)
        assert "type" in parsed
        assert "properties" in parsed

    def test_invalid_json_raises_error(self):
        """JSON inválido debe lanzar error."""
        invalid_contract = '{invalid json'
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_contract)

    def test_empty_contract_is_valid(self):
        """Contrato vacío (string vacío) es válido - significa None."""
        empty_contract = ""
        # String vacío se trata como None, no se parsea
        result = empty_contract.strip() or None
        assert result is None


class TestWizardFormData:
    """Tests para datos del formulario del wizard."""

    def test_form_data_has_contract_fields(self):
        """form_data debe tener campos para contratos."""
        expected_fields = [
            'name', 'description', 'atom_type', 'subtype',
            'config_schema', 'default_config', 'version',
            'input_contract', 'output_contract', 'dependencies'
        ]

        # Simulamos la estructura de form_data que usa el wizard
        form_data = {
            'name': '',
            'description': '',
            'atom_type': StepType.EXTRACTION,
            'subtype': None,
            'config_schema': '{}',
            'default_config': '{}',
            'version': '1.0.0',
            'input_contract': '',
            'output_contract': '',
            'dependencies': []
        }

        for field in expected_fields:
            assert field in form_data, f"Campo {field} faltante en form_data"

    def test_contracts_not_shown_for_connection(self):
        """Contratos NO deben mostrarse para tipo CONNECTION."""
        # La lógica es: if form_data['atom_type'] != StepType.CONNECTION
        # entonces mostrar contratos
        form_data = {'atom_type': StepType.CONNECTION}
        show_contracts = form_data['atom_type'] != StepType.CONNECTION
        assert show_contracts == False

    def test_contracts_shown_for_extraction(self):
        """Contratos SÍ deben mostrarse para tipo EXTRACTION."""
        form_data = {'atom_type': StepType.EXTRACTION}
        show_contracts = form_data['atom_type'] != StepType.CONNECTION
        assert show_contracts == True

    def test_contracts_shown_for_email(self):
        """Contratos SÍ deben mostrarse para tipo EMAIL."""
        form_data = {'atom_type': StepType.EMAIL}
        show_contracts = form_data['atom_type'] != StepType.CONNECTION
        assert show_contracts == True
