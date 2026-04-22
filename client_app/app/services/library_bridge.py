from automatia_shared.dtos import TaskSpec
from typing import Any, Dict

def sync_atom_outputs(task: TaskSpec, last_result: Any) -> TaskSpec:
    """
    Toma el resultado de 'Ejecutar' y actualiza el contrato del átomo.
    Esto es lo que permite que luego aparezcan las 'Data Pills'.
    """
    if isinstance(last_result, dict):
        # Update outputs list
        # Merge with existing to avoid losing manually defined ones? 
        # For now, let's assume result is authoritative for "Certified" outputs.
        # Use set to avoid duplicates but keep order if possible (List)
        current_outputs = set(task.outputs) if task.outputs else set()
        new_outputs = set(last_result.keys())
        
        updated_outputs = list(current_outputs.union(new_outputs))
        task.outputs = updated_outputs
        
        # Mark as validated
        if not task.metadata:
            task.metadata = {}
            
        task.metadata['validated'] = True
        task.metadata['last_run_result'] = last_result # Simplify debug
        
    return task
