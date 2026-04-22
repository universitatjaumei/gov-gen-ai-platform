import pytest
from datetime import datetime
from automatia_shared.dtos import AutomationBlueprintDTO
from automatia_shared.enums import AutomationType

def test_automation_dto_invalid_type():
    """Test RED: Validate that invalid types raise ValueError/ValidationError."""
    with pytest.raises(ValueError):
        AutomationBlueprintDTO(
            id="123", 
            name="Test Invalid", 
            type="INVALID_TYPE_XYZ", 
            code_content="print('hello')", 
            updated_at="2024-01-01"
        )

def test_automation_dto_extended_features():
    """Test GREEN: Validate new fields (signature, access_groups, is_workflow)."""
    data = {
        "id": "workflow-abc",
        "name": "Proceso Facturación Completo",
        "type": "workflow",  # Using one of the new types requested
        "code_content": '{"steps": []}',
        "version": 5,
        "updated_at": "2024-02-15T12:00:00",
        "partner_id": "partner_premium",
        "is_workflow": True,
        "access_groups": ["finanzas", "vip"],
        "signature": "valid_cryptographic_signature_here"
    }
    
    dto = AutomationBlueprintDTO(**data)
    
    # 1. Validar nuevos campos
    assert dto.is_workflow is True
    assert "finanzas" in dto.access_groups
    assert dto.signature == "valid_cryptographic_signature_here"
    
    # 2. Validar consistencia del hash con contenido (si el metodo existe)
    if hasattr(dto, "get_content_hash"):
        content_hash = dto.get_content_hash()
        assert len(content_hash) == 32 # MD5 hash length
    
    # 3. Validar serialización JSON
    json_data = dto.model_dump_json() # Pydantic v2 uses model_dump_json
    dto_recovered = AutomationBlueprintDTO.model_validate_json(json_data)
    assert dto_recovered.signature == "valid_cryptographic_signature_here"
    assert dto_recovered.is_workflow is True
