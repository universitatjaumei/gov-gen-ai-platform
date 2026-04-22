"""
Unit tests for Property 3.1: Data Contract Generalization.
Verifies DataContractService strategies for JSON, CSV and delegates PDF.
"""
import pytest
from unittest.mock import AsyncMock, patch
import json

@pytest.mark.asyncio
async def test_infer_from_json_strategy():
    """Verify inference from JSON content."""
    from client_app.app.services.data_contract_service import data_contract_service
    
    json_content = json.dumps({
        "customer_id": 123,
        "is_active": True,
        "name": "Acme Corp",
        "score": 98.5
    })
    
    result = await data_contract_service.suggest_contract(json_content, 'application/json')
    fields = result['suggested_fields']
    
    assert len(fields) == 4
    
    # Check type inference
    field_map = {f['name']: f['type'] for f in fields}
    assert field_map['customer_id'] == 'integer'
    assert field_map['is_active'] == 'boolean'
    assert field_map['name'] == 'string'
    assert field_map['score'] == 'number'


@pytest.mark.asyncio
async def test_infer_from_csv_strategy():
    """Verify inference from CSV content."""
    from client_app.app.services.data_contract_service import data_contract_service
    
    csv_content = "Order ID,Product Name,Quantity\n1001,Widget A,5"
    
    result = await data_contract_service.suggest_contract(csv_content, 'text/csv')
    fields = result['suggested_fields']
    
    assert len(fields) == 3
    
    names = [f['name'] for f in fields]
    assert 'order_id' in names
    assert 'product_name' in names
    assert 'quantity' in names


@pytest.mark.asyncio
async def test_infer_from_pdf_delegation():
    """Verify PDF inference delegates to ExtractionService."""
    from client_app.app.services.data_contract_service import data_contract_service
    
    mock_response = {'suggested_fields': [{'name': 'test'}]}
    
    with patch('client_app.app.services.extraction_service.extraction_service.suggest_fields_from_doc1', new_callable=AsyncMock) as mock_ext:
        mock_ext.return_value = mock_response
        
        result = await data_contract_service.suggest_contract('/path/to/doc.pdf', 'application/pdf', 'doc.pdf')
        
        assert result == mock_response
        mock_ext.assert_called_once()    


@pytest.mark.asyncio
async def test_unsupported_format_raises_error():
    """Verify helpful error for unknown formats."""
    from client_app.app.services.data_contract_service import data_contract_service
    
    with pytest.raises(ValueError):
        await data_contract_service.suggest_contract(b'xyz', 'application/unknown')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
