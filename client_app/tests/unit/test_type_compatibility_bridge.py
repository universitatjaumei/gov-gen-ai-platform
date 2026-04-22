
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.type_compatibility_service import TypeCompatibilityService, InputType

@pytest.mark.asyncio
async def test_request_bridge_script_delegation():
    """Verify TypeCompatibilityService delegates to BridgeGenerationService."""
    service = TypeCompatibilityService()
    
    # Mock BridgeGenerationService
    with patch("client_app.app.services.bridge_generation_service.bridge_generation_service") as mock_bridge_gen:
        mock_bridge_gen.generate_bridge_code = AsyncMock(return_value="def transform(x): return x")
        
        code = await service.request_bridge_script(
            source_type=InputType.STR,
            target_type=InputType.INT,
            source_name="my_str",
            target_name="my_int",
            example_value="123"
        )
        
        assert code == "def transform(x): return x"
        
        mock_bridge_gen.generate_bridge_code.assert_called_once()
        call_kwargs = mock_bridge_gen.generate_bridge_code.call_args.kwargs
        assert call_kwargs["source_type"] == "text" or call_kwargs["source_type"] == "str" or str(InputType.STR.value) in str(call_kwargs["source_type"])
        assert call_kwargs["target_type"] == "integer" or call_kwargs["target_type"] == "int" or str(InputType.INT.value) in str(call_kwargs["target_type"])
        assert "examples" in call_kwargs["context"]
        assert "123" in call_kwargs["context"]["examples"]
