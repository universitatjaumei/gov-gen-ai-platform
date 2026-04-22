
import pytest
from automatia_shared.contracts.ui_contract import (
    UIContract, InputDefinition, InputType, Constraints,
    OutputSchema, OutputField
)
from client_app.app.services.flow_compatibility_service import (
    FlowCompatibilityService, CompatibilityStatus
)

class TestFlowCompatibilityService:
    def setup_method(self):
        self.service = FlowCompatibilityService()

    def test_compatible_types(self):
        """Should be compatible if types match."""
        source = OutputField(name="count", label="Count", type=InputType.INT)
        target = InputDefinition(name="count", label="Count", type=InputType.INT)
        
        result = self.service.check_field_compatibility(source, target)
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert not result.coercion_needed

    def test_coercible_types(self):
        """Int to Str should be coercible."""
        source = OutputField(name="count", label="Count", type=InputType.INT)
        target = InputDefinition(name="text", label="Text", type=InputType.STR)
        
        result = self.service.check_field_compatibility(source, target)
        assert result.status == CompatibilityStatus.COERCIBLE
        assert result.coercion_needed
        assert "str(" in result.coercion_code

    def test_incompatible_types(self):
        """Str to Int is risky/incompatible (marked as False in matrix)."""
        # In matrix: (InputType.STR, InputType.INT): (False, "int({value})") -> RISKY
        source = OutputField(name="text", label="Text", type=InputType.STR)
        target = InputDefinition(name="count", label="Count", type=InputType.INT)
        
        result = self.service.check_field_compatibility(source, target)
        assert result.status == CompatibilityStatus.RISKY
        # If no entry in matrix, it would be incompatible.

    def test_constraints_warning(self):
        """Warning if source max > target max."""
        source = OutputField(
            name="val", label="Val", type=InputType.INT,
            constraints=Constraints(max=100)
        )
        target = InputDefinition(
            name="val", label="Val", type=InputType.INT,
            constraints=Constraints(max=50)
        )
        
        result = self.service.check_field_compatibility(source, target)
        # Should be warning because 100 > 50
        assert result.status == CompatibilityStatus.WARNING
        assert "mayor al maximo" in result.message.lower() or "origen puede producir" in result.message.lower()

    def test_link_validation_missing_field(self):
        """Link should be incompatible if required field missing."""
        source = OutputSchema(fields=[])
        target = UIContract(inputs=[
            InputDefinition(name="req", label="Req", type=InputType.STR, required=True)
        ])
        
        result = self.service.validate_atom_link(source, target)
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert "req" in result.missing_fields

    def test_bridge_prompt_generation(self):
        """Should generate prompt if incompatible."""
        source = OutputSchema(fields=[])
        target = UIContract(inputs=[
            InputDefinition(name="req", label="Req", type=InputType.STR, required=True)
        ])
        
        result = self.service.validate_atom_link(source, target)
        assert result.bridge_prompt is not None
        assert "Genera un script Python" in result.bridge_prompt
