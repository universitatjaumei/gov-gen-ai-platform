from automatia_shared.dtos import TaskSpec
import uuid
from typing import Dict, Any, Optional

# Mock in-memory storage for now
_LIBRARY_STORAGE: Dict[str, TaskSpec] = {}

class AssetPromotionService:
    def promote(self, step: TaskSpec, test_data: Dict[str, Any]) -> str:
        """Convierte una tarea de flujo en un Átomo de la biblioteca."""
        # Clonamos y limpiamos para que sea una plantilla genérica
        atom = step.model_copy()
        
        # New clean ID for library asset
        new_id = f"atom_{uuid.uuid4().hex[:8]}"
        # Note: TaskSpec usually doesn't have 'id' field in current DTO definition 
        # (it relies on DB id or container list index), 
        # but if we are storing it in a library, we might need a handle.
        # We will assume we store it by key in our storage.
        
        if not atom.metadata:
            atom.metadata = {}
            
        atom.metadata['is_template'] = True
        atom.metadata['validation_test'] = test_data
        
        # Remove flow-specific execution flags
        atom.metadata.pop('validated', None) 
        atom.metadata.pop('last_run_result', None)
        
        self.save_to_storage(new_id, atom)
        
        return new_id

    def save_to_storage(self, atom_id: str, atom: TaskSpec):
        # Stub: Guardado en base de datos local (simulated)
        _LIBRARY_STORAGE[atom_id] = atom

    def get_from_library(self, atom_id: str) -> Optional[TaskSpec]:
        return _LIBRARY_STORAGE.get(atom_id)
