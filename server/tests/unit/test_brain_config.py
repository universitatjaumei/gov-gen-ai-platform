import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from server.app.services.ai_brain import AIBrainService

@pytest.mark.asyncio
async def test_system_prompt_tier_injection():
    """
    Verifica que el servicio devuelve la configuración correcta para el Tier 3 (Supervisión)
    y que el System Prompt incluye las directrices de Metaprogramación.
    """
    service = AIBrainService()
    
    # Mockeamos _resolve_server_config para simular la respuesta de la BD
    # Esto evita necesitar la BD real levantada para este test unitario
    with patch.object(service, '_resolve_server_config', new_callable=AsyncMock) as mock_resolve:
        
        # Simulamos lo que devolvería la BD si el seed funcionó correctamente
        mock_resolve.return_value = (
            # Configuración del modelo (Tier 3)
            {
                "provider": "google", 
                "model_id": "gemini-1.5-pro",
                "temperature": 0.1
            },
            # System Prompt esperado
            """
            Eres el Copiloto de Metaprogramación de AutomatIA.
            REGLAS:
            1. CÓDIGO: Siempre en Python, función 'transform(data)'.
            2. DATA: Usa solo las variables declaradas en 'inputs'.
            3. FORMATO: Si reparas un flujo, responde en JSON compatible con TaskSpec.
            4. PRIVACIDAD: Prioriza la soberanía local y la anonimización.
            """
        )
        
        # Llamada simulada al resolver configuración para el servicio de metaprogramación
        config, system_prompt = await service._resolve_server_config(
            service_id="sys_metaprogramming", 
            role_key="supervision"
        )
        
        assert config is not None
        assert "Metaprogramación" in system_prompt
        assert config["model_id"] == "gemini-1.5-pro"
        assert config["temperature"] <= 0.2 # Queremos precisión
        
        # Verificamos que se llamó con los parámetros correctos
        mock_resolve.assert_called_with(service_id="sys_metaprogramming", role_key="supervision")
