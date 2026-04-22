
import pytest
from unittest.mock import MagicMock
from automatia_shared.contracts.ui_contract import DataContract, OutputSchema, OutputField, InputType
from client_app.app.services.doc_generator_service import DocumentationGeneratorService

def test_build_readme_content_uses_data_contract():
    """
    Validates that build_readme_content accepts a DataContract and generates
    a correct Markdown table from its OutputSchema.
    """
    service = DocumentationGeneratorService()
    
    # 1. Create a unified DataContract
    fields = [
        OutputField(name="invoice_total", label="Total Invoice", type=InputType.FLOAT, description="Total amount extracted"),
        OutputField(name="vendor_name", label="Vendor", type=InputType.STR, description="Name of the vendor")
    ]
    
    contract = DataContract(
        version="1.0",
        description="Extracts invoice totals and vendor names.",
        output=OutputSchema(fields=fields),
        config={}
    )
    
    # 2. Generate README content
    # Note: We expect the method signature to be updated to accept DataContract
    readme_content = service.build_readme_content(contract)
    
    # 3. Verify content
    assert "Extracts invoice totals and vendor names." in readme_content
    
    # Verify table headers
    assert "| Nombre | Tipo | Descripción |" in readme_content or "| Name | Type | Description |" in readme_content
    
    # Verify rows
    assert "| invoice_total | float | Total amount extracted |" in readme_content
    assert "| vendor_name | string | Name of the vendor |" in readme_content

def test_build_readme_handles_empty_contract():
    """Validates behavior with empty contract."""
    service = DocumentationGeneratorService()
    contract = DataContract(
        version="1.0",
        description="Empty script",
        output=OutputSchema(fields=[]),
        config={}
    )
    
    readme_content = service.build_readme_content(contract)
    assert "Empty script" in readme_content
    assert "No hay campos de salida definidos" in readme_content or "No output fields" in readme_content
