import pytest
from automatia_shared.contracts.ui_contract import UIContract, InputDefinition, InputType
from pydantic import ValidationError

def test_input_definition_validation():
    """Test valid definition of inputs"""
    # Valid
    inp = InputDefinition(name="my_var", label="My Var", type=InputType.STR)
    assert inp.name == "my_var"
    
    # Invalid name
    with pytest.raises(ValidationError):
        InputDefinition(name="Invalid Name", label="X", type=InputType.STR)

    # Missing options for SELECT
    with pytest.raises(ValidationError):
        InputDefinition(name="sel", label="Select", type=InputType.SELECT)

def test_contract_validation_success():
    """Test validation of valid data"""
    contract = UIContract(inputs=[
        InputDefinition(name="username", label="User", type=InputType.STR),
        InputDefinition(name="age", label="Age", type=InputType.INT),
        InputDefinition(name="active", label="Active", type=InputType.BOOL),
        InputDefinition(name="role", label="Role", type=InputType.SELECT, options=["admin", "user"])
    ])
    
    data = {
        "username": "fabra",
        "age": "30", # String to int conversion
        "active": "yes", # String to bool
        "role": "admin"
    }
    
    validated = contract.validate_inputs(data)
    assert validated["age"] == 30
    assert validated["active"] is True
    assert validated["role"] == "admin"

def test_contract_validation_required():
    """Test missing required fields"""
    contract = UIContract(inputs=[
        InputDefinition(name="req", label="Required", type=InputType.STR, required=True)
    ])
    
    with pytest.raises(ValueError) as exc:
        contract.validate_inputs({})
    assert "Campo requerido faltante" in str(exc.value)

def test_contract_to_schema():
    """Test JSON Schema generation"""
    contract = UIContract(inputs=[
        InputDefinition(name="file_path", label="File", type=InputType.FILE)
    ])
    
    schema = contract.to_schema()
    assert schema["type"] == "object"
    assert "file_path" in schema["properties"]
    assert schema["properties"]["file_path"]["format"] == "file-path"
