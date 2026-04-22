
import pytest

def test_configurator_mapping():
    """Calculates if the configurator correctly maps UI string inputs to schema types."""
    # We simulate a schema (subset of TaskSpec parameters)
    schema = {
        "url": {"type": "string", "default": ""},
        "retries": {"type": "integer", "default": 3},
        "debug": {"type": "boolean", "default": False}
    }
    
    # We need to import the coercion function (not implemented yet)
    # This import will fail initially (Red), or the function usage will fail if empty.
    from client_app.app.components.atom_configurator import coerce_value
    
    # Test Integer coercion
    assert coerce_value("5", "integer") == 5
    assert isinstance(coerce_value("5", "integer"), int)
    
    # Test Boolean coercion
    assert coerce_value("True", "boolean") is True
    assert coerce_value("true", "boolean") is True
    assert coerce_value("1", "boolean") is True
    assert coerce_value("False", "boolean") is False
    assert coerce_value(False, "boolean") is False # Should handle already-bool input
    
    # Test String pass-through
    assert coerce_value("hello", "string") == "hello"
