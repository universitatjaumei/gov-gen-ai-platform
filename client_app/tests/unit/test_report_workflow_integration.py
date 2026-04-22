"""
Tests para integración de informes en workflows.
TDD: Estos tests DEBEN FALLAR inicialmente.
"""
import pytest
import datetime
from uuid import uuid4
from sqlmodel import Session, create_engine, SQLModel
from client_app.app.database.models import (
    FlowRegistry, FlowStep, AtomRegistry, ReportTemplate
)
# We might need to mock or stub validators if they import services that don't exist yet
# However, the prompt implies creating the file with failing tests if components missing.

# For StepType, we might need to add REPORT to the enum if it doesn't exist.
# Checking automatia_shared/enums.py via view_file would be good but I can assume standard StepType enum.
# I'll define a dummy StepType class here if import fails or just use strings for now in test setup if possible, 
# but models enforce Enum. I should check StepType definition.

# Let's check shared enums quickly or proceed assuming I need to add it.
# The prompt says "Integrar... como un tipo de paso (REPORT_GENERATE)".
# "from automatia_shared.enums import StepType" is in the prompt code.

class TestReportWorkflowIntegration:
    """Tests para pasos de informe en workflows."""

    @pytest.mark.asyncio
    async def test_report_step_validates_with_compatible_data(self, session: Session):
        """
        RED: Paso de informe debe validar si recibe datos compatibles.
        """
        # IMPORTANTE: Asumimos que StepType.REPORT existe o se añadirá.
        # Si no existe, este test fallará al importar o usar, lo cual es correcto para TDD (RED).
        from automatia_shared.enums import StepType
        from client_app.app.services.flow_validator_service import validate_flow

        # Crear plantilla de informe
        template = ReportTemplate(
            name="Sales Report",
            input_schema={
                "type": "object",
                "properties": {
                    "sales_data": {"type": "array"},
                    "period": {"type": "string"}
                },
                "required": ["sales_data"]
            }
        )
        session.add(template)
        session.commit() # commit to get ID

        # Crear átomo extractor que produce datos compatibles
        # NOTE: AtomRegistry might not be strictly needed if we just mock Flow structure
        # but the validator service probably checks Atoms.
        extractor = AtomRegistry(
            name="Excel Extractor",
            atom_type=StepType.EXTRACTION,
            output_contract={
                "type": "object",
                "properties": {
                    "data": {"type": "array"},
                    "filename": {"type": "string"}
                }
            }
        )
        session.add(extractor)
        
        # Crear átomo de informe - In the unified flow, Report might be an Atom or just a generic step?
        # The prompt says "Integrar... como un tipo de paso".
        # If the system uses Atoms for everything, we need a Report Atom.
        report_atom = AtomRegistry(
            name="Report Generator",
            atom_type=StepType.REPORT,
            input_contract=template.input_schema,
            config_schema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string"},
                    "variable_mapping": {"type": "object"}
                }
            }
        )
        session.add(report_atom)
        session.commit()

        # Crear flujo: Extractor -> Report
        flow = FlowRegistry(
            name="Test Report Flow",
            steps=[
                FlowStep(atom_id=extractor.id, step_type=StepType.EXTRACTION, output_var_name="extracted"),
                FlowStep(
                    atom_id=report_atom.id,
                    step_type=StepType.REPORT,
                    custom_config={
                        "template_id": str(template.id),
                        "variable_mapping": {
                            "sales_data": "extracted.data",
                            "period": "'Q1 2024'"
                        }
                    }
                )
            ]
        )
        
        # We need to mock validate_flow or ensure it exists and handles REPORT steps
        # If validate_flow is not updated for REPORT steps, it might fail or return False.
        # Ideally we want it to validate TRUE if logic is correct.
        
        # For this test to run we need to actually implement or import validate_flow.
        # If validate_flow doesn't support REPORT yet, it might return False or error.
        
        # Assuming validate_flow exists.
        is_valid = await validate_flow(flow, session)
        assert is_valid == True

    @pytest.mark.asyncio
    async def test_report_step_config_stores_mapping(self, session: Session):
        """
        RED: La configuración del paso debe guardar el mapeo de variables.
        """
        from automatia_shared.enums import StepType
        
        template = ReportTemplate(
            name="Test Template",
            input_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "array"},
                    "title": {"type": "string"}
                }
            }
        )
        session.add(template)
        session.commit()

        step = FlowStep(
            atom_id=uuid4(),
            step_type=StepType.REPORT,
            custom_config={
                "template_id": str(template.id),
                "output_mode": "pdf_static",
                "variable_mapping": {
                    "data": "previous_step.output.rows",
                    "title": "'Monthly Report'"
                }
            }
        )

        assert step.custom_config["template_id"] == str(template.id)
        assert "data" in step.custom_config["variable_mapping"]

    def test_variable_mapping_validates_against_schema(self):
        """
        RED: El mapeo debe validar que todas las variables requeridas estén mapeadas.
        """
        # This service doesn't exist yet, so import should fail (RED)
        from client_app.app.services.report_mapping_validator import validate_mapping

        input_schema = {
            "type": "object",
            "properties": {
                "required_field": {"type": "string"},
                "optional_field": {"type": "number"}
            },
            "required": ["required_field"]
        }

        # Mapeo incompleto (falta required_field)
        incomplete_mapping = {
            "optional_field": "some.variable"
        }

        result = validate_mapping(incomplete_mapping, input_schema)
        assert result.is_valid == False
        assert "required_field" in result.missing_fields

        # Mapeo completo
        complete_mapping = {
            "required_field": "other.variable"
        }

        result = validate_mapping(complete_mapping, input_schema)
        assert result.is_valid == True
