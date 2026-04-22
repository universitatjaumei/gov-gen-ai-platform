import pytest
from decimal import Decimal
from pathlib import Path
from automatia_shared.contracts.ui_contract import (
    UIContract, InputDefinition, InputType,
    Constraints, Dependency, DependencyCondition, DependencyAction, DependencyOperator,
    CoercionConfig, PythonType
)

def test_constraints_validation():
    """Test min, max, regex constraints"""
    contract = UIContract(inputs=[
        InputDefinition(
            name="age", label="Age", type=InputType.INT,
            constraints=Constraints(min=18, max=99)
        ),
        InputDefinition(
            name="code", label="Code", type=InputType.STR,
            constraints=Constraints(regex=r"^[A-Z]{3}$")
        )
    ])
    
    # Valid
    assert contract.validate_inputs({"age": 20, "code": "ABC"})
    
    # Invalid Min
    with pytest.raises(ValueError) as e:
        contract.validate_inputs({"age": 10, "code": "ABC"})
    assert "menor al minimo" in str(e.value)
    
    # Invalid Regex
    with pytest.raises(ValueError) as e:
        contract.validate_inputs({"age": 20, "code": "abc"})
    assert "Formato no valido" in str(e.value)

def test_dependency_required():
    """Test dynamic required status"""
    contract = UIContract(inputs=[
        InputDefinition(name="has_pets", label="Pets?", type=InputType.BOOL),
        InputDefinition(
            name="pet_name", label="Pet Name", type=InputType.STR,
            required=False, # Default optional
            dependencies=[
                Dependency(
                    condition=DependencyCondition(field="has_pets", operator=DependencyOperator.EQ, value=True),
                    action=DependencyAction(required=True) # Make required if True
                )
            ]
        )
    ])
    
    # Optional when has_pets=False
    contract.validate_inputs({"has_pets": False})
    
    # Required when has_pets=True
    with pytest.raises(ValueError) as e:
        contract.validate_inputs({"has_pets": True})
    assert "Campo requerido faltante: pet_name" in str(e.value)
    
    # Success when provided
    contract.validate_inputs({"has_pets": True, "pet_name": "Rex"})

def test_coercion():
    """Test Python type coercion"""
    contract = UIContract(inputs=[
        InputDefinition(
            name="price", label="Price", type=InputType.FLOAT,
            coercion=CoercionConfig(python_type=PythonType.DECIMAL)
        ),
        InputDefinition(
            name="folder", label="Folder", type=InputType.STR,
            coercion=CoercionConfig(python_type=PythonType.PATH)
        )
    ])
    
    res = contract.validate_inputs({"price": 10.5, "folder": "/tmp/test"})
    
    assert isinstance(res["price"], Decimal)
    assert res["price"] == Decimal("10.5")
    assert isinstance(res["folder"], Path)
    assert str(res["folder"]).replace('\\', '/') == "/tmp/test" # Normalize separator for assertion

def test_dependency_visibility():
    """Test that invisible fields are ignored/omitted"""
    contract = UIContract(inputs=[
        InputDefinition(name="show_more", label="Show", type=InputType.BOOL),
        InputDefinition(
            name="secret_field", label="Hidden", type=InputType.STR,
            dependencies=[
                Dependency(
                    condition=DependencyCondition(field="show_more", operator=DependencyOperator.EQ, value=False),
                    action=DependencyAction(visible=False)
                )
            ]
        )
    ])
    
    # If show_more=False, secret_field is invisible -> should not include it
    res = contract.validate_inputs({"show_more": False, "secret_field": "ShouldBeIgnored"})
    assert "secret_field" not in res
    
    # If show_more=True, secret_field is visible -> included
    res2 = contract.validate_inputs({"show_more": True, "secret_field": "VisibleValue"})
    assert res2["secret_field"] == "VisibleValue"
