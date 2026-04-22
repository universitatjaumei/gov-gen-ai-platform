
import pytest
from client_app.app.services.type_coercion_service import TypeCoercionService
from automatia_shared.enums import InputType

def test_coerce_integer():
    assert TypeCoercionService.coerce("123", InputType.INTEGER) == 123
    assert TypeCoercionService.coerce(123, InputType.INTEGER) == 123
    with pytest.raises(ValueError):
        TypeCoercionService.coerce("abc", InputType.INTEGER)

def test_coerce_float():
    assert TypeCoercionService.coerce("123.45", InputType.FLOAT) == 123.45
    assert TypeCoercionService.coerce(123, InputType.FLOAT) == 123.0
    with pytest.raises(ValueError):
        TypeCoercionService.coerce("abc", InputType.FLOAT)

def test_coerce_boolean():
    # Truthy values
    for val in ["true", "True", "TRUE", "1", "yes", "on", True, 1]:
        assert TypeCoercionService.coerce(val, InputType.BOOLEAN) is True
    
    # Falsy values
    for val in ["false", "False", "FALSE", "0", "no", "off", False, 0, ""]:
        assert TypeCoercionService.coerce(val, InputType.BOOLEAN) is False

def test_coerce_list():
    # String splitting (comma separated)
    assert TypeCoercionService.coerce("a,b,c", InputType.LIST) == ["a", "b", "c"]
    assert TypeCoercionService.coerce("a, b, c", InputType.LIST) == ["a", "b", "c"] # Trimming
    
    # JSON array string
    assert TypeCoercionService.coerce('["x", "y"]', InputType.LIST) == ["x", "y"]
    
    # Direct list
    assert TypeCoercionService.coerce(["1", "2"], InputType.LIST) == ["1", "2"]
    
    # Single item
    assert TypeCoercionService.coerce("item", InputType.LIST) == ["item"]

def test_coerce_dict():
    # JSON object string
    assert TypeCoercionService.coerce('{"key": "val"}', InputType.DICT) == {"key": "val"}
    
    # Direct dict
    assert TypeCoercionService.coerce({"a": 1}, InputType.DICT) == {"a": 1}
    
    # Invalid JSON
    with pytest.raises(ValueError):
        TypeCoercionService.coerce("{invalid_json", InputType.DICT)

def test_coerce_string():
    assert TypeCoercionService.coerce(123, InputType.STRING) == "123"
    assert TypeCoercionService.coerce(None, InputType.STRING) == ""
    assert TypeCoercionService.coerce("text", InputType.STRING) == "text" 

def test_coerce_complex_nested():
    """Test coercion of complex structures (list of dicts) if supported or just basic recursive types."""
    # For now, just basic types.
    pass

def test_unknown_type_returns_value():
    """If type is not specified or unknown, return original value."""
    assert TypeCoercionService.coerce("test", None) == "test"
