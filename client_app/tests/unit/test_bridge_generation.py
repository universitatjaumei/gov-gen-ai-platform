
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.bridge_generation_service import BridgeGenerationService
from client_app.app.services.bridge_creator import BridgeService
from automatia_shared.dtos import FlowSpec

@pytest.mark.asyncio
async def test_bridge_generation_service_call():
    """Verify BridgeGenerationService calls ScriptGeneratorService correctly."""
    service = BridgeGenerationService()
    
    # Mock script generator
    with patch("client_app.app.services.bridge_generation_service.script_generator_service") as mock_gen:
        mock_gen.generate_script = AsyncMock(return_value={
            "success": True, 
            "code": "def transform(x): return x"
        })
        
        code = await service.generate_bridge_code(
            source_type="List[Dict]", 
            target_type="DataFrame",
            context={"examples": ["[{\"a\":1}]"]}
        )
        
        assert "def transform(x): return x" in code
        
        mock_gen.generate_script.assert_called_once()
        call_kwargs = mock_gen.generate_script.call_args.kwargs
        prompt = call_kwargs["user_prompt"]
        assert "List[Dict]" in prompt
        assert "DataFrame" in prompt
        assert "transform" in prompt
        assert "input_data" in prompt
        assert "Ejemplos" in prompt

@pytest.mark.asyncio
async def test_bridge_creator_integration():
    """Verify BridgeService uses BridgeGenerationService and wraps code."""
    flow_mock = MagicMock(spec=FlowSpec)
    steps = []
    flow_mock.steps = steps
    
    bridge_service = BridgeService(flow_mock)
    
    # Mock BridgeGenerationService
    with patch("client_app.app.services.bridge_generation_service.bridge_generation_service") as mock_bridge_gen:
        mock_bridge_gen.generate_bridge_code = AsyncMock(return_value="def transform(data): return data")
        
        result_code = await bridge_service.generate_bridge_code(
            source_var="my_list",
            source_type="list",
            target_var="my_df",
            target_type="dataframe"
        )
        
        assert "Smart Bridge" in result_code
        assert "def transform(data): return data" in result_code
        assert "if 'my_list' in globals():" in result_code
        assert "my_df = result" in result_code
        
        mock_bridge_gen.generate_bridge_code.assert_called_once()
