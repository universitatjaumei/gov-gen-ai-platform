"""
Tests para DataFlowAnalyzer - Prompt 4.1.
Sistema de variables y contexto para el editor de flujos.
"""
import pytest
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType

from client_app.app.services.data_flow_analyzer import (
    data_flow_analyzer,
    DataFlowAnalyzer,
    VariableInfo,
)


# ============================================================================
# Tests originales (compatibilidad)
# ============================================================================

def test_get_available_variables_first_step():
    """Primer paso solo tiene variables de contexto"""
    analyzer = DataFlowAnalyzer()

    flow = FlowSpec(
        name="Test",
        steps=[TaskSpec(name="S1", type=StepType.EXTRACTION, config={})]
    )

    available = analyzer.get_available_variables(flow, step_index=0)
    var_names = [v.name if isinstance(v, VariableInfo) else v for v in available]

    assert 'execution_id' in var_names
    assert 'trigger_type' in var_names


def test_get_available_variables_second_step():
    """Segundo paso tiene output del primero"""
    analyzer = DataFlowAnalyzer()

    flow = FlowSpec(
        name="Test",
        steps=[
            TaskSpec(name="S1", type=StepType.EXTRACTION, config={'output_var': 'extraction_result'}),
            TaskSpec(name="S2", type=StepType.ETL_TRANSFORM, config={})
        ]
    )

    available = analyzer.get_available_variables(flow, step_index=1)
    var_names = [v.name if isinstance(v, VariableInfo) else v for v in available]

    assert 'extraction_result' in var_names
    assert 'previous_output' in var_names


def test_suggest_output_var_name():
    """Debe sugerir nombres consistentes por tipo"""
    analyzer = DataFlowAnalyzer()

    assert "extraction" in analyzer.suggest_output_var_name(StepType.EXTRACTION, 0).lower()
    assert "transform" in analyzer.suggest_output_var_name(StepType.ETL_TRANSFORM, 1).lower()


# ============================================================================
# Tests nuevos - Prompt 4.1
# ============================================================================

class TestTriggerVariables:
    """Tests para variables del trigger."""

    def test_step_0_has_trigger_variables_manual(self):
        """El primer paso tiene variables del trigger manual."""
        flow = FlowSpec(
            name="Test Flow",
            trigger_type="manual",
            steps=[
                TaskSpec(name="Paso 1", type=StepType.EXTRACTION, config={})
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 0)

        # Debe incluir variables básicas del contexto
        var_names = [v.name for v in variables]
        assert 'execution_id' in var_names
        assert 'trigger_type' in var_names

    def test_step_0_has_trigger_variables_email(self):
        """El primer paso tiene variables específicas del trigger email."""
        flow = FlowSpec(
            name="Test Flow",
            trigger_type="email",
            steps=[
                TaskSpec(name="Paso 1", type=StepType.EXTRACTION, config={})
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 0)

        var_names = [v.name for v in variables]
        # Trigger email debe tener estas variables
        assert 'email_from' in var_names
        assert 'email_subject' in var_names
        assert 'attachments' in var_names

    def test_step_0_has_trigger_variables_file(self):
        """El primer paso tiene variables del trigger file (folder watcher)."""
        flow = FlowSpec(
            name="Test Flow",
            trigger_type="file",
            steps=[
                TaskSpec(name="Paso 1", type=StepType.EXTRACTION, config={})
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 0)

        var_names = [v.name for v in variables]
        assert 'trigger_file' in var_names
        assert 'file_path' in var_names

    def test_get_trigger_variables_returns_variable_info(self):
        """get_trigger_variables retorna lista de VariableInfo."""
        variables = data_flow_analyzer.get_trigger_variables("email")

        assert len(variables) > 0
        for var in variables:
            assert isinstance(var, VariableInfo)
            assert var.name is not None
            assert var.var_type is not None


class TestPreviousOutputs:
    """Tests para outputs de pasos anteriores."""

    def test_step_n_has_previous_outputs(self):
        """Paso N tiene outputs de pasos 0..N-1."""
        flow = FlowSpec(
            name="Test Flow",
            steps=[
                TaskSpec(
                    name="Paso 1",
                    type=StepType.EXTRACTION,
                    config={"output_var": "datos_extraidos"}
                ),
                TaskSpec(
                    name="Paso 2",
                    type=StepType.API_FETCH,
                    config={"output_var": "respuesta_api"}
                ),
                TaskSpec(
                    name="Paso 3",
                    type=StepType.EMAIL_SEND,
                    config={}
                ),
            ]
        )

        # Paso 2 (índice 2) debe ver outputs de pasos 0 y 1
        variables = data_flow_analyzer.get_available_variables(flow, 2)
        var_names = [v.name for v in variables]

        assert 'datos_extraidos' in var_names
        assert 'respuesta_api' in var_names

    def test_step_0_has_no_previous_outputs(self):
        """El primer paso no tiene outputs de pasos anteriores."""
        flow = FlowSpec(
            name="Test Flow",
            steps=[
                TaskSpec(name="Paso 1", type=StepType.EXTRACTION, config={})
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 0)
        var_names = [v.name for v in variables]

        # No debe tener previous_output en el primer paso
        assert 'previous_output' not in var_names

    def test_step_n_has_previous_output_alias(self):
        """Paso N > 0 tiene la variable especial previous_output."""
        flow = FlowSpec(
            name="Test Flow",
            steps=[
                TaskSpec(name="Paso 1", type=StepType.EXTRACTION, config={}),
                TaskSpec(name="Paso 2", type=StepType.API_FETCH, config={}),
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 1)
        var_names = [v.name for v in variables]

        assert 'previous_output' in var_names


class TestVariableTypeInfo:
    """Tests para información de tipo de variables."""

    def test_variables_have_type_info(self):
        """Cada variable indica su tipo (string, file, json, etc.)."""
        flow = FlowSpec(
            name="Test Flow",
            trigger_type="email",
            steps=[
                TaskSpec(name="Paso 1", type=StepType.EXTRACTION, config={})
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 0)

        for var in variables:
            assert isinstance(var, VariableInfo)
            assert var.var_type is not None
            assert var.var_type in ('string', 'number', 'file', 'file[]', 'json', 'json[]', 'any', 'boolean')

    def test_extraction_output_has_json_type(self):
        """El output de EXTRACTION tiene tipo json."""
        flow = FlowSpec(
            name="Test Flow",
            steps=[
                TaskSpec(
                    name="Extracción",
                    type=StepType.EXTRACTION,
                    config={"output_var": "datos"}
                ),
                TaskSpec(name="Siguiente", type=StepType.API_FETCH, config={}),
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 1)
        datos_var = next((v for v in variables if v.name == 'datos'), None)

        assert datos_var is not None
        assert datos_var.var_type == 'json'

    def test_api_fetch_output_has_json_type(self):
        """El output de API_FETCH tiene tipo json."""
        flow = FlowSpec(
            name="Test Flow",
            steps=[
                TaskSpec(
                    name="API",
                    type=StepType.API_FETCH,
                    config={"output_var": "respuesta"}
                ),
                TaskSpec(name="Siguiente", type=StepType.EMAIL_SEND, config={}),
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 1)
        respuesta_var = next((v for v in variables if v.name == 'respuesta'), None)

        assert respuesta_var is not None
        assert respuesta_var.var_type == 'json'

    def test_variable_has_source_step_info(self):
        """Las variables de pasos anteriores indican el paso de origen."""
        flow = FlowSpec(
            name="Test Flow",
            steps=[
                TaskSpec(
                    name="Extracción",
                    type=StepType.EXTRACTION,
                    config={"output_var": "datos"}
                ),
                TaskSpec(name="Siguiente", type=StepType.API_FETCH, config={}),
            ]
        )

        variables = data_flow_analyzer.get_available_variables(flow, 1)
        datos_var = next((v for v in variables if v.name == 'datos'), None)

        assert datos_var is not None
        assert datos_var.source_step == 0
        assert datos_var.source_step_name == "Extracción"


class TestSuggestOutputName:
    """Tests para sugerencia de nombres de variables de salida."""

    def test_suggest_output_name_is_unique(self):
        """Las sugerencias no colisionan con variables existentes."""
        flow = FlowSpec(
            name="Test Flow",
            steps=[
                TaskSpec(
                    name="Extracción 1",
                    type=StepType.EXTRACTION,
                    config={"output_var": "extraction_result_1"}
                ),
                TaskSpec(
                    name="Extracción 2",
                    type=StepType.EXTRACTION,
                    config={}
                ),
            ]
        )

        # El paso 1 es otra extracción, pero extraction_result_1 ya existe
        suggested = data_flow_analyzer.suggest_output_var_name(
            StepType.EXTRACTION,
            step_index=1,
            flow=flow
        )

        # Debe ser diferente al existente
        assert suggested != "extraction_result_1"
        assert "extraction" in suggested.lower()

    def test_suggest_output_name_by_step_type(self):
        """Cada tipo de paso tiene un patrón de nombre sugerido."""
        assert "extraction" in data_flow_analyzer.suggest_output_var_name(
            StepType.EXTRACTION, 0
        ).lower()

        assert "api" in data_flow_analyzer.suggest_output_var_name(
            StepType.API_FETCH, 0
        ).lower()

        assert "script" in data_flow_analyzer.suggest_output_var_name(
            StepType.CUSTOM_SCRIPT, 0
        ).lower()

    def test_suggest_output_name_includes_index(self):
        """La sugerencia incluye el índice del paso para unicidad."""
        name_0 = data_flow_analyzer.suggest_output_var_name(StepType.EXTRACTION, 0)
        name_1 = data_flow_analyzer.suggest_output_var_name(StepType.EXTRACTION, 1)

        assert name_0 != name_1
        assert "1" in name_0 or "0" in name_0
        assert "2" in name_1 or "1" in name_1


class TestStepOutputDefinitions:
    """Tests para definiciones de outputs por tipo de paso."""

    def test_extraction_outputs(self):
        """EXTRACTION produce: extracted_data (json), source_file (file)."""
        outputs = data_flow_analyzer.get_step_type_outputs(StepType.EXTRACTION)

        assert 'extracted_data' in outputs
        assert outputs['extracted_data'] == 'json'

    def test_api_fetch_outputs(self):
        """API_FETCH produce: response_body (json), status_code (number)."""
        outputs = data_flow_analyzer.get_step_type_outputs(StepType.API_FETCH)

        assert 'response_body' in outputs
        assert outputs['response_body'] == 'json'
        assert 'status_code' in outputs
        assert outputs['status_code'] == 'number'

    def test_email_outputs(self):
        """EMAIL produce: emails (json[]), attachments (file[])."""
        outputs = data_flow_analyzer.get_step_type_outputs(StepType.EMAIL)

        assert 'emails' in outputs
        assert 'attachments' in outputs

    def test_custom_script_outputs(self):
        """CUSTOM_SCRIPT produce: result (any)."""
        outputs = data_flow_analyzer.get_step_type_outputs(StepType.CUSTOM_SCRIPT)

        assert 'result' in outputs
        assert outputs['result'] == 'any'


class TestVariablePreview:
    """Tests para preview de valores de variables."""

    def test_get_variable_preview_returns_none_without_execution(self):
        """Sin ejecución previa, el preview es None."""
        preview = data_flow_analyzer.get_variable_preview("some_var", flow_id=123)

        # Sin historial de ejecución, debe retornar None
        assert preview is None

    def test_variable_info_structure(self):
        """VariableInfo tiene todos los campos requeridos."""
        var = VariableInfo(
            name="test_var",
            var_type="json",
            source_step=0,
            source_step_name="Paso 1",
            description="Variable de prueba"
        )

        assert var.name == "test_var"
        assert var.var_type == "json"
        assert var.source_step == 0
        assert var.source_step_name == "Paso 1"
        assert var.description == "Variable de prueba"
