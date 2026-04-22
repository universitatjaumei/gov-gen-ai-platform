
import pytest
from pydantic import ValidationError
from automatia_shared.contracts.ui_contract import DataContract, OutputSchema, OutputField

def test_build_extraction_contract_returns_model():
    """El servicio debe devolver una instancia de DataContract, no un dict."""
    from client_app.app.services.extraction_service import ExtractionService
    
    service = ExtractionService()
    
    # Mock de datos mínimos
    raw_data = {
        "fields": [{"name": "total", "type": "float", "description": "Monto total"}]
    }
    
    contract = service.build_extraction_contract(raw_data)
    
    assert isinstance(contract, DataContract)
    assert isinstance(contract.outputs, OutputSchema)
    assert contract.outputs.fields[0].name == "total"

def test_invalid_contract_raises_error():
    """Debe fallar si los tipos de datos en el contrato son inválidos."""
    with pytest.raises(ValidationError):
        # Intentar crear un campo con un tipo no soportado o nombre vacío
        OutputField(name="", type="invalid_type")  # type: ignore
