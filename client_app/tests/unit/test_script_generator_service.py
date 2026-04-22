
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from client_app.app.services.script_generator_service import ScriptGeneratorService

@pytest.fixture
def mock_brain_client():
    mock = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_generate_script_success(mock_brain_client, test_client_db):
    """Test generating a script successfully."""
    # Mock LLM response
    mock_response = {
        "text": """
        ```json
        {
            "code": "import pandas as pd\\nprint('hello')",
            "description": "A simple script",
            "required_libraries": ["pandas"],
            "input_type": "file",
            "output_type": "text"
        }
        ```
        """
    }
    mock_brain_client.generate_script.return_value = mock_response

    # Mock internal helper to avoid DB issues
    service = ScriptGeneratorService()
    service._get_client_and_license = AsyncMock(return_value=(mock_brain_client, "valid_key"))
    service.check_libraries = AsyncMock(return_value={"allowed": [], "forbidden": [], "unknown": []}) 

    result = await service.generate_script(
        user_prompt="Analyze this CSV",
        output_type="text"
    )

    assert result["success"] is True
    assert result["code"] == "import pandas as pd\nprint('hello')"
    assert "pandas" in result["required_libraries"]
    
    # Verify BrainAPIClient was called with correct arguments
    mock_brain_client.generate_script.assert_called_once()
    call_args = mock_brain_client.generate_script.call_args
    assert call_args.kwargs['license_key'] == "valid_key"
    assert "Analyze this CSV" in call_args.kwargs['prompt']

@pytest.mark.asyncio
async def test_generate_script_refusal(mock_brain_client, test_client_db):
    """Test handling of LLM refusal or bad JSON."""
    mock_brain_client.generate_script.return_value = {"text": "I cannot do that."}
    
    # Mock internally
    service = ScriptGeneratorService()
    service._get_client_and_license = AsyncMock(return_value=(mock_brain_client, "valid_key"))
    service.check_libraries = AsyncMock(return_value={"allowed": [], "forbidden": [], "unknown": []})

    result = await service.generate_script("bad prompt")
        
    assert result["success"] is False
    assert "No se pudo generar" in result["error"] or "JSON" in result["error"]

@pytest.mark.asyncio
async def test_check_libraries(test_client_db):
    """Test library validation against policy."""
    # We patch the DB helper directly
    with patch("client_app.app.services.script_generator_service.get_security_policy") as mock_get_policy:
        mock_get_policy.return_value = MagicMock(
            allowed_imports='["pandas", "numpy"]',
            forbidden_imports='["os", "subprocess"]'
        )
        
        service = ScriptGeneratorService()
        
        # Validation
        result = await service.check_libraries(["pandas", "os", "requests"])
        
        assert "pandas" in result["allowed"]
        assert "os" in result["forbidden"]
        assert "requests" in result["unknown"]
