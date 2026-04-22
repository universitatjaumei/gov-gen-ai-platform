import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass
from client_app.app.services.script_adaptation_service import (
    script_adaptation_service,
    AdaptationResult
)
from client_app.app.services.script_generator_service import ScriptGeneratorService

@pytest.mark.asyncio
async def test_detect_main_function():
    """Detecta función principal del script"""
    code = "def process_data(data): return data"
    analysis = await script_adaptation_service.analyze_script(code)
    assert analysis.main_function == "process_data"

@pytest.mark.asyncio
async def test_wrap_script_with_transform():
    """Envuelve script en función transform usando templates"""
    code = "df['new'] = 1"
    # For template adaptation, we might expect simple wrapping
    result = script_adaptation_service.adapt_from_template(code, "etl_transform")
    
    assert "def transform(df):" in result.adapted_code
    assert "df['new'] = 1" in result.adapted_code
    assert result.success

@pytest.mark.asyncio
async def test_adapt_with_ai_calls_generator():
    """Llama al servicio de generación para adaptar con IA"""
    code = "import pandas"
    
    # Mock script generator response
    mock_response = {
        "success": True,
        "parsed": {
            "code": "def transform(df):\n    import pandas\n    return df",
            "description": "Adapted script"
        }
    }
    
    with patch('client_app.app.services.script_generator_service.script_generator_service.generate_custom_script', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response
        
        result = await script_adaptation_service.adapt_to_platform(
            code, 
            target_type="etl_transform",
            use_ai=True
        )
        
        assert result.success
        assert "def transform(df):" in result.adapted_code
        mock_gen.assert_called_once()
        # Verify prompt contains context
        _, kwargs = mock_gen.call_args
        prompt_arg = kwargs.get('prompt', '')
        assert "etl_transform" in prompt_arg
        assert code in prompt_arg

@pytest.mark.asyncio
async def test_generate_docstring():
    """Genera documentación (docstring) basada en la descripción de la IA"""
    code = "import pandas"
    description = "Transforma los datos filtrando columnas nulas"
    
    mock_response = {
        "success": True,
        "parsed": {
            "code": "def transform(df):\n    return df",
            "description": description
        }
    }
    
    with patch('client_app.app.services.script_generator_service.script_generator_service.generate_custom_script', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response
        
        result = await script_adaptation_service.adapt_to_platform(
            code, 
            target_type="etl_transform",
            use_ai=True
        )
        
        assert result.success
        # Verify description is included as docstring
        assert f'"""\n{description}\n"""' in result.adapted_code
        assert "def transform(df):" in result.adapted_code

@pytest.mark.asyncio
async def test_adapt_fails_gracefully():
    """Maneja fallos en la IA"""
    with patch('client_app.app.services.script_generator_service.script_generator_service.generate_custom_script', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"success": False, "error": "AI Error"}
        
        result = await script_adaptation_service.adapt_to_platform(
            "code", 
            target_type="etl_transform",
            use_ai=True
        )
        
        assert not result.success
        assert "AI Error" in result.error
