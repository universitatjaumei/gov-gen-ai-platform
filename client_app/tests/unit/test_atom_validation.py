import pytest
from client_app.app.services.library_bridge import sync_atom_outputs
from automatia_shared.dtos import TaskSpec
from automatia_shared.enums import StepType

def test_execution_updates_contract_outputs():
    # Un átomo que aún no tiene definidos sus outputs
    # Using CUSTOM_SCRIPT type as generic example
    atom = TaskSpec(name="Test Atom", type=StepType.CUSTOM_SCRIPT, outputs=[])
    
    # Simulamos el resultado de una ejecución exitosa
    result_data = {"total": 12.1, "currency": "EUR"}
    
    # El sistema debe inferir los outputs del resultado
    updated_atom = sync_atom_outputs(atom, result_data)
    
    assert "total" in updated_atom.outputs
    assert "currency" in updated_atom.outputs
    assert updated_atom.metadata.get('validated') is True
    assert updated_atom.metadata.get('last_run_result') == result_data

def test_sync_handles_non_dict_result():
    atom = TaskSpec(name="Test Atom", type=StepType.CUSTOM_SCRIPT, outputs=[])
    result_data = "Just a string"
    
    updated_atom = sync_atom_outputs(atom, result_data)
    
    # Should not crash, maybe set a default output or ignore
    # For now, simplistic approach: ignore if not dict
    assert not updated_atom.outputs
