
import pytest
from automatia_shared.core.consolidator import DataConsolidator
from automatia_shared.contracts.ui_contract import OutputSchema, OutputField, InputType, CoercionConfig, PythonType

def test_filter_and_validate_schema_removes_extras():
    """Validates that fields not in the schema are removed."""
    raw_data = {
        "valid_field": "value",
        "hallucinated_field": "nonsense"
    }
    
    schema = OutputSchema(fields=[
        OutputField(name="valid_field", type=InputType.STR, label="Valid")
    ])
    
    clean_data = DataConsolidator.validate_against_schema(raw_data, schema)
    
    assert "valid_field" in clean_data
    assert "hallucinated_field" not in clean_data
    assert clean_data["valid_field"] == "value"

def test_validate_schema_coerces_types():
    """Validates type coercion."""
    raw_data = {
        "number_as_string": "123.45",
        "int_as_string": "42"
    }
    
    schema = OutputSchema(fields=[
        OutputField(name="number_as_string", type=InputType.FLOAT, label="Num"),
        OutputField(name="int_as_string", type=InputType.INT, label="Int")
    ])
    
    clean_data = DataConsolidator.validate_against_schema(raw_data, schema)
    
    assert isinstance(clean_data["number_as_string"], float)
    assert clean_data["number_as_string"] == 123.45
    assert isinstance(clean_data["int_as_string"], int)
    assert clean_data["int_as_string"] == 42
    
def test_consolidate_result_with_schema_integration():
    """Validates correct integration of validate_against_schema inside consolidate_result."""
    raw_data = {
        "valid": "ok",
        "extra": "bad"
    }
    schema = OutputSchema(fields=[OutputField(name="valid", type=InputType.STR, label="V")])
    
    result = DataConsolidator.consolidate_result(
        clean_data=raw_data,
        schema=schema
    )
    
    data = result["data"]
    assert "valid" in data
    assert "extra" not in data
    assert result["status"] == "ok"

def test_consolidate_result_without_schema_passthrough():
    """Validates legacy/ad-hoc behavior (Pass-through)."""
    raw_data = {"any": "thing"}
    
    result = DataConsolidator.consolidate_result(clean_data=raw_data)
    
    assert result["data"] == raw_data
