
"""
Tests para reactividad de DynamicExecutorForm.
Verifica que las dependencias entre campos funcionan correctamente.
"""
import pytest
from unittest.mock import MagicMock
# We will import the functions to be tested. 
# Note: These functions will be implemented in dynamic_form.py or a logic module.
# For now, assuming they will be in client_app.app.ui.components.dynamic_form
# If the file doesn't exist yet or the functions aren't there, we'll need to define where they go.
# The plan says client_app/app/ui/components/dynamic_form.py

from automatia_shared.contracts.ui_contract import (
    UIContract, InputDefinition, InputType,
    Dependency, DependencyCondition, DependencyOperator, DependencyAction,
    Constraints
)

# Import the functions to test (will fail until implemented, or we mock if we are strictly TDDing the logic separately)
# Since we are implementing the functions in the same file as the component, we'll try to import them.
# If the file doesn't exist, we will create it. 
# But for now, let's assume we will create a separate file for logic if needed, 
# or just import from the component file.
# To make this test runnable BEFORE the implementation exists without erroring on import, 
# we might need to handle the import. 
# However, for true TDD, we write the test expecting the code to be there.

try:
    from client_app.app.ui.components.dynamic_form import evaluate_field_visibility, validate_field_constraints
except ImportError:
    # If not found, define mocks to allow test collection, but fail usually.
    # Actually, let's just assume we will implement them immediately.
    pass

class TestDependencyEvaluation:
    """Tests para evaluación de dependencias."""

    def test_field_hidden_by_default_when_dependency_not_met(self):
        """Campo con dependencia debe estar oculto si la condición no se cumple."""
        contract = UIContract(inputs=[
            InputDefinition(
                name="mode",
                label="Modo",
                type=InputType.SELECT,
                options=["Simple", "Avanzado"]
            ),
            InputDefinition(
                name="advanced_config",
                label="Configuración Avanzada",
                type=InputType.STR,
                required=False,
                dependencies=[
                    Dependency(
                        condition=DependencyCondition(
                            field="mode",
                            operator=DependencyOperator.EQ,
                            value="Avanzado"
                        ),
                        action=DependencyAction(visible=True)
                    )
                ]
            )
        ])

        # El campo advanced_config debe tener visible=False por defecto
        # cuando mode != "Avanzado"
        visibility = evaluate_field_visibility(contract, "advanced_config", {"mode": "Simple"})
        assert visibility is False

    def test_field_shown_when_dependency_met(self):
        """Campo debe mostrarse cuando la condición se cumple."""
        contract = UIContract(inputs=[
            InputDefinition(
                name="mode",
                label="Modo",
                type=InputType.SELECT,
                options=["Simple", "Avanzado"]
            ),
            InputDefinition(
                name="advanced_config",
                label="Configuración Avanzada",
                type=InputType.STR,
                dependencies=[
                    Dependency(
                        condition=DependencyCondition(
                            field="mode",
                            operator=DependencyOperator.EQ,
                            value="Avanzado"
                        ),
                        action=DependencyAction(visible=True)
                    )
                ]
            )
        ])

        visibility = evaluate_field_visibility(contract, "advanced_config", {"mode": "Avanzado"})
        assert visibility is True


class TestConstraintsValidation:
    """Tests para validación de constraints en UI."""

    def test_regex_constraint_generates_validation_error(self):
        """Un constraint de regex debe generar error de validación."""
        contract = UIContract(inputs=[
            InputDefinition(
                name="email",
                label="Email",
                type=InputType.STR,
                constraints=Constraints(
                    regex=r"^[\w\.-]+@[\w\.-]+\.\w+$"
                )
            )
        ])

        errors = validate_field_constraints(contract, "email", "not-an-email")
        assert len(errors) > 0
        assert "formato" in errors[0].lower() or "regex" in errors[0].lower()

    def test_min_max_constraint_on_number(self):
        """Constraints min/max deben validarse en números."""
        contract = UIContract(inputs=[
            InputDefinition(
                name="quantity",
                label="Cantidad",
                type=InputType.INT,
                constraints=Constraints(min=1, max=100)
            )
        ])

        errors = validate_field_constraints(contract, "quantity", 150)
        assert len(errors) > 0
        assert "máximo" in errors[0].lower() or "max" in errors[0].lower()
