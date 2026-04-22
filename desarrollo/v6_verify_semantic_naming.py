import asyncio
import json
from unittest.mock import AsyncMock, patch
from automatia_shared.enums import StepType
from client_app.app.services.data_flow_analyzer import data_flow_analyzer

async def test_suggestion():
    print("Testing semantic name suggestion...")
    
    step_type = StepType.EXTRACTION
    config = {"doc_type": "Factura", "ocr_enabled": True}
    
    # Mock BrainAPIClient
    with patch('client_app.app.clients.brain_client.BrainAPIClient.call_llm', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "lista_facturas_pro"
        
        name = await data_flow_analyzer.suggest_semantic_name(step_type, config)
        
        print(f"Suggested name: {name}")
        
        # Verify call parameters
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        print(f"Service ID used: {kwargs.get('service_id')}")
        print(f"Config Summary: {kwargs.get('config_summary')}")
        
        assert name == "lista_facturas_pro"
        assert kwargs.get('service_id') == "sys_semantic_naming"
        assert "EXTRACTION" in kwargs.get('config_summary')['step_type']
        
    print("Test passed!")

if __name__ == "__main__":
    asyncio.run(test_suggestion())
