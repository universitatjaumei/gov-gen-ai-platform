import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

# Import services to test
from client_app.app.services.data_contract_service import data_contract_service
from client_app.app.services.execution_session_service import execution_session_service
from client_app.app.services.sandbox_service import _extract_execution_metadata

@pytest.mark.asyncio
async def test_synthetic_data_generation():
    """Verifica que se generan datos sintéticos correctos basados en schema."""
    output_schema = {
        "fields": [
            {"name": "email_cliente", "type": "string"},
            {"name": "nombre_completo", "type": "string"},
            {"name": "total_factura", "type": "number"},
            {"name": "es_vip", "type": "boolean"},
            {"name": "fecha_registro", "type": "date"}
        ]
    }
    
    samples = await data_contract_service.generate_synthetic_data(output_schema, num_samples=3)
    
    assert len(samples) == 3
    sample = samples[0]
    
    # Verify smart field detection
    assert "@" in sample["email_cliente"]
    assert " " in sample["nombre_completo"]  # Names usually have spaces
    assert isinstance(sample["total_factura"], (int, float))
    assert isinstance(sample["es_vip"], bool)
    # Date format check (YYYY-MM-DD)
    assert len(sample["fecha_registro"]) == 10 
    assert sample["fecha_registro"].count("-") == 2

@pytest.mark.asyncio
async def test_contract_generation_from_metadata():
    """Verifica la generación de contratos JSON desde metadata."""
    
    # Input Metadata
    input_metadata = {
        "detected_fields": [
            {"name": "invoice_id", "type": "string", "label": "Invoice ID"},
            {"name": "amount", "type": "number", "required": True}
        ]
    }
    
    input_contract_json = await data_contract_service.generate_input_contract(input_metadata)
    input_contract = json.loads(input_contract_json)
    
    assert "inputs" in input_contract["inputs"]
    assert len(input_contract["inputs"]["inputs"]) == 2
    assert input_contract["inputs"]["inputs"][0]["name"] == "invoice_id"
    assert input_contract["inputs"]["inputs"][1]["required"] is True
    
    # Output Metadata
    output_metadata = {
        "fields": [
            {"name": "processed_total", "type": "number", "label": "Processed Total"}
        ]
    }
    
    output_contract_json = await data_contract_service.generate_output_contract(output_metadata)
    output_contract = json.loads(output_contract_json)
    
    assert "fields" in output_contract
    assert output_contract["fields"][0]["name"] == "processed_total"
    assert output_contract["fields"][0]["type"] == "float" # Mapped from number

@pytest.mark.asyncio
async def test_execution_session_lifecycle():
    """Verifica el ciclo de vida de una sesión de ejecución."""
    
    script_id = 999
    execution_id = "exec_test_123"
    
    # 1. Save Session
    session_id = await execution_session_service.save_execution_session(
        script_id=script_id,
        execution_id=execution_id,
        input_metadata={"file_count": 1},
        output_metadata={"fields": []},
        validated=False
    )
    
    assert session_id == f"{script_id}_{execution_id}"
    
    # 2. Verify not validated yet
    session = await execution_session_service.get_execution_session(script_id)
    assert session is None # Should return None as it's not validated
    
    # 3. Mark Validated
    found = await execution_session_service.mark_session_validated(execution_id)
    assert found is True
    
    # 4. Verify retrieval
    session = await execution_session_service.get_execution_session(script_id)
    assert session is not None
    assert session["execution_id"] == execution_id
    assert session["validated"] is True
    
    # Cleanup
    await execution_session_service.clear_script_sessions(script_id)
    session = await execution_session_service.get_execution_session(script_id)
    assert session is None

def test_sandbox_metadata_extraction():
    """Verifica la lógica de extracción de metadata de resultados de sandbox."""
    
    input_files = ["doc1.pdf", "doc2.pdf"]
    results = [
        {
            "status": "success",
            "data": {
                "nombre": "Juan Perez",
                "edad": 30,
                "activo": True,
                "saldo": 100.50,
                "fecha": "2023-01-01"
            }
        },
        {
            "status": "error",
            "error": "failed"
        }
    ]
    
    metadata = _extract_execution_metadata(input_files, results)
    
    # Check Input Metadata
    assert metadata["input_metadata"]["file_count"] == 2
    assert "pdf" in metadata["input_metadata"]["file_types"]
    
    # Check Output Metadata
    fields = metadata["output_metadata"]["fields"]
    assert len(fields) == 5
    
    # Verify inferred types
    field_map = {f["name"]: f["type"] for f in fields}
    assert field_map["nombre"] == "string"
    assert field_map["edad"] == "integer"
    assert field_map["activo"] == "boolean"
    assert field_map["saldo"] == "number"
    assert field_map["fecha"] == "date"

if __name__ == "__main__":
    # Allow running directly
    asyncio.run(test_synthetic_data_generation())
    asyncio.run(test_contract_generation_from_metadata())
    asyncio.run(test_execution_session_lifecycle())
    test_sandbox_metadata_extraction()
    print("All tests passed!")
