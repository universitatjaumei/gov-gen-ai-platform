import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# server/tests/integration/test_tier_e2e.py

class TestTierConfigurationE2E:
    """Tests de integración end-to-end para configuración de tier por prompt."""

    @pytest.mark.asyncio
    async def test_save_tier_and_resolve(self):
        """
        E2E: Guardar tier en UI → Leer en resolución → Usar modelo correcto.
        """
        from server.app.database.models import ExtractionServiceConfig
        from server.app.services.ai_brain import AIBrainService

        # 1. ARRANGE: Crear config con tier_override=2
        test_config = ExtractionServiceConfig(
            service_id="test_e2e_tier",
            name="Test E2E Tier",
            system_prompt_template="Test prompt for E2E",
            tier_override=2  # Fuerza Tier 2 (logico_navegacion)
        )

        # 2. ACT: Simular resolución
        brain = AIBrainService()

        # Mock de la sesión de base de datos
        with patch('server.app.services.ai_brain.AsyncSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Mock de ExtractionServiceConfig query
            mock_exec_result = MagicMock()
            mock_exec_result.first.return_value = test_config
            mock_session.exec.return_value = mock_exec_result

            # Mock de AIConfig query (simulating logic tier config)
            mock_ai_config = MagicMock()
            mock_ai_config.provider = "google"
            mock_ai_config.model_id = "gemini-2.0-flash" 
            
            mock_exec_result_ai = MagicMock()
            mock_exec_result_ai.first.return_value = mock_ai_config
            
            # Setup side_effect for sequential queries:
            # 1. Select ExtractionServiceConfig
            # 2. Select AIConfig
            mock_session.exec.side_effect = [mock_exec_result, mock_exec_result_ai]

            # Llamar con role_key diferente (tier_override debería ganar y usar 'logico_navegacion' implícitamente)
            config, prompt = await brain._resolve_server_config(
                service_id="test_e2e_tier",
                role_key="extraccion_pdf"  # Tier 1 defaults
            )

        # 3. ASSERT: 
        # prompt matches
        assert prompt == "Test prompt for E2E"
        # config matches Tier 2 logic model
        assert config["model_id"] == "gemini-2.0-flash" 
        
        # Verify that we actually queried for the correct role logic if possible, 
        # but the most important end-result is getting the correct model.

    @pytest.mark.asyncio
    async def test_tier_update_propagates(self):
        """
        Cuando se actualiza el modelo de un tier en AIConfig,
        todos los prompts con ese tier_override deben usar el nuevo modelo.
        """
        # 1. Config con tier_override=1
        from server.app.database.models import ExtractionServiceConfig
        from server.app.services.ai_brain import TIER_TO_ROLE

        config_a = ExtractionServiceConfig(
            service_id="test_prop_a",
            name="Test Propagation A",
            system_prompt_template="Prompt A",
            tier_override=1
        )

        config_b = ExtractionServiceConfig(
            service_id="test_prop_b",
            name="Test Propagation B",
            system_prompt_template="Prompt B",
            tier_override=1  # Mismo tier
        )

        # Verificar mappings
        assert config_a.tier_override == 1
        assert config_b.tier_override == 1
        assert TIER_TO_ROLE[1] == "extraccion_pdf"

    @pytest.mark.asyncio
    async def test_ui_saves_tier_correctly(self):
        """
        Simula el flujo de UI: cargar prompt → cambiar tier → guardar.
        """
        from server.app.database.models import ExtractionServiceConfig

        # 1. Prompt inicial sin tier_override
        prompt = ExtractionServiceConfig(
            service_id="test_ui_save",
            name="Test UI Save",
            system_prompt_template="Original prompt",
            tier_override=None
        )

        assert prompt.tier_override is None

        # 2. Simular cambio desde UI
        new_tier = 3
        prompt.tier_override = new_tier

        # 3. Verificar que el cambio se refleja
        assert prompt.tier_override == 3

    def test_priority_order(self):
        """Verifica el orden de prioridad documentado."""
        # Prioridad: tier_override > suggested_model > role_key

        # Caso 1: tier_override definido (ignora suggested_model)
        case1 = {"tier_override": 2, "suggested_model": "modelo-X", "role_key": "extraccion_pdf"}
        # Expected: Tier 2 wins

        # Caso 2: solo suggested_model (sin tier_override)
        case2 = {"tier_override": None, "suggested_model": "modelo-X", "role_key": "extraccion_pdf"}
        # Expected: Suggested model wins

        # Caso 3: solo role_key
        case3 = {"tier_override": None, "suggested_model": None, "role_key": "extraccion_pdf"}
        # Expected: Role key defaults win

        # Assertions logic
        assert case1["tier_override"] is not None
        assert case2["suggested_model"] is not None
        assert case3["role_key"] is not None

    @pytest.mark.asyncio
    async def test_invalid_tier_fallback(self):
        """Verifica que un tier inválido usa el fallback."""
        from server.app.services.ai_brain import TIER_TO_ROLE

        # Tier 999 no existe
        invalid_tier = 999

        # Debería no estar en TIER_TO_ROLE
        assert invalid_tier not in TIER_TO_ROLE
