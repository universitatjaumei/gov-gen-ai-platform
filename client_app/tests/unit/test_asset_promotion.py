import pytest
from client_app.app.services.promotion_service import AssetPromotionService
from automatia_shared.dtos import TaskSpec
from automatia_shared.enums import StepType

def test_promote_step_to_atom():
    # Paso que queremos guardar
    step = TaskSpec(
        name="Conversor JSON-CSV",
        type=StepType.CUSTOM_SCRIPT,
        script_code="def transform(x): return x.to_csv()",
        inputs=["data_json"],
        outputs=["data_csv"]
    )
    
    # Datos que usamos para probarlo con éxito en el sandbox
    success_test_data = {"data_json": "[{'id': 1}]"}
    
    service = AssetPromotionService()
    atom_id = service.promote(step, test_data=success_test_data)
    
    # Verificamos que se guardó en la biblioteca
    promoted_atom = service.get_from_library(atom_id)
    
    assert promoted_atom.name == "Conversor JSON-CSV"
    assert promoted_atom.metadata.get('validation_test') == success_test_data
    assert promoted_atom.metadata.get('is_template') is True
    assert promoted_atom.metadata.get('is_bridge') is False # Should clear flow-specific flags if any (optional)
