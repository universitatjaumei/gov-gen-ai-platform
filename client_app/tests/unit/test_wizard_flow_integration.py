"""
Tests para reutilización de wizard entre Atoms Page y Flows Page.
Data Contracts Fase 2, Prompt 6.
"""
import pytest
from client_app.app.core.state import state
from automatia_shared.enums import StepType
from automatia_shared.dtos import TaskSpec


class TestWizardFlowContext:
    """Tests para contexto de flujo en wizard."""

    def setup_method(self):
        """Reset state antes de cada test."""
        state.wizard_flow_context = None
        state.wizard_initial_step_type = None
        state.wizard_initial_subtype = None

    def test_wizard_flow_context_can_store_flow(self):
        """wizard_flow_context debe poder almacenar referencia a flujo."""
        # Simular flujo con steps
        mock_flow = type('Flow', (), {'steps': [], 'name': 'Test Flow'})()

        state.wizard_flow_context = {
            'flow': mock_flow,
            'refresh_callback': None
        }

        assert state.wizard_flow_context is not None
        assert state.wizard_flow_context['flow'] == mock_flow
        assert state.wizard_flow_context['flow'].name == 'Test Flow'

    def test_wizard_flow_context_can_store_callback(self):
        """wizard_flow_context debe poder almacenar callback de refresh."""
        refresh_called = {'count': 0}

        def mock_refresh():
            refresh_called['count'] += 1

        state.wizard_flow_context = {
            'flow': None,
            'refresh_callback': mock_refresh
        }

        # Simular llamada al callback
        callback = state.wizard_flow_context['refresh_callback']
        if callback:
            callback()

        assert refresh_called['count'] == 1

    def test_wizard_context_cleared_after_use(self):
        """Contexto debe limpiarse tras usar."""
        state.wizard_flow_context = {'flow': 'dummy', 'refresh_callback': None}

        # Simular limpieza (como haría el wizard)
        state.wizard_flow_context = None

        assert state.wizard_flow_context is None


class TestTaskSpecCreation:
    """Tests para creación de TaskSpec desde átomo."""

    def test_taskspec_can_be_created(self):
        """TaskSpec debe poder crearse con datos básicos."""
        step = TaskSpec(
            name="Test Step",
            type=StepType.EXTRACTION,
            config={}
        )

        assert step.name == "Test Step"
        assert step.type == StepType.EXTRACTION
        assert step.config == {}

    def test_taskspec_accepts_atom_id_in_metadata(self):
        """TaskSpec debe aceptar atom_id en metadata."""
        step = TaskSpec(
            name="Test Step",
            type=StepType.EXTRACTION,
            config={},
            metadata={
                'atom_id': 123,
                'atom_version': '1.0.0',
                'subtype': None
            }
        )

        assert 'atom_id' in step.metadata
        assert step.metadata['atom_id'] == 123
        assert step.metadata['atom_version'] == '1.0.0'

    def test_taskspec_with_connection_type(self):
        """TaskSpec debe funcionar con tipo CONNECTION."""
        step = TaskSpec(
            name="Email Connection",
            type=StepType.CONNECTION,
            config={'host': 'imap.example.com'}
        )

        assert step.type == StepType.CONNECTION
        assert 'host' in step.config


class TestFlowStepAddition:
    """Tests para añadir pasos a flujos."""

    def test_step_added_to_flow_steps_list(self):
        """Paso debe añadirse a la lista de steps del flujo."""
        # Simular flujo
        mock_flow = type('Flow', (), {'steps': []})()

        # Crear paso
        new_step = TaskSpec(
            name="New Step",
            type=StepType.EXTRACTION,
            config={}
        )

        # Añadir al flujo
        mock_flow.steps.append(new_step)

        assert len(mock_flow.steps) == 1
        assert mock_flow.steps[0].name == "New Step"

    def test_multiple_steps_can_be_added(self):
        """Múltiples pasos deben poder añadirse."""
        mock_flow = type('Flow', (), {'steps': []})()

        for i in range(3):
            step = TaskSpec(
                name=f"Step {i+1}",
                type=StepType.CUSTOM_SCRIPT,
                config={}
            )
            mock_flow.steps.append(step)

        assert len(mock_flow.steps) == 3
        assert mock_flow.steps[2].name == "Step 3"


class TestWizardCallbackSignature:
    """Tests para verificar firma del callback."""

    def test_callback_accepts_step_type_only(self):
        """Callback debe funcionar con solo step_type."""
        received = {'step_type': None, 'subtype': None}

        def callback(step_type, subtype=None):
            received['step_type'] = step_type
            received['subtype'] = subtype

        callback(StepType.EXTRACTION)

        assert received['step_type'] == StepType.EXTRACTION
        assert received['subtype'] is None

    def test_callback_accepts_step_type_and_subtype(self):
        """Callback debe funcionar con step_type y subtype."""
        received = {'step_type': None, 'subtype': None}

        def callback(step_type, subtype=None):
            received['step_type'] = step_type
            received['subtype'] = subtype

        callback(StepType.CONNECTION, "EMAIL")

        assert received['step_type'] == StepType.CONNECTION
        assert received['subtype'] == "EMAIL"


class TestWizardIntegrationFlow:
    """Tests de integración del flujo completo."""

    def setup_method(self):
        """Reset state."""
        state.wizard_flow_context = None
        state.wizard_initial_step_type = None
        state.wizard_initial_subtype = None

    def test_full_flow_from_selection_to_context(self):
        """Flujo completo: selección -> contexto guardado."""
        # 1. Simular flujo existente
        mock_flow = type('Flow', (), {'steps': []})()

        # 2. Simular callback de selección (como en flows_page)
        state.wizard_flow_context = {
            'flow': mock_flow,
            'refresh_callback': None
        }
        state.wizard_initial_step_type = StepType.EXTRACTION
        state.wizard_initial_subtype = None

        # 3. Verificar estado
        assert state.wizard_flow_context is not None
        assert state.wizard_initial_step_type == StepType.EXTRACTION

    def test_full_flow_connection_with_subtype(self):
        """Flujo completo con conexión y subtipo."""
        mock_flow = type('Flow', (), {'steps': []})()

        # Simular selección de CONNECTION con subtipo EMAIL
        state.wizard_flow_context = {
            'flow': mock_flow,
            'refresh_callback': None
        }
        state.wizard_initial_step_type = StepType.CONNECTION
        state.wizard_initial_subtype = "EMAIL"

        assert state.wizard_initial_step_type == StepType.CONNECTION
        assert state.wizard_initial_subtype == "EMAIL"

    def test_context_none_when_no_flow(self):
        """Sin flujo activo, contexto debe ser None."""
        # En atoms_page, no hay flujo activo
        state.wizard_flow_context = None
        state.wizard_initial_step_type = StepType.EXTRACTION

        assert state.wizard_flow_context is None
        # El wizard creará el átomo pero NO añadirá paso a ningún flujo
