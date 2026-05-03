"""Tests para la factoría de modelos y el servicio de prompts."""
import uuid
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestModelFactory:

    @pytest.mark.asyncio
    async def test_model_factory_returns_google_model(self) -> None:
        from server.app.modules.agents_hub.services.model_factory import get_model

        mock_chatbot = Mock(llm_config_id=uuid.uuid4(), use_prompt_caching=True, cache_ttl=7200)
        mock_config = Mock(
            provider="google",
            model_name="gemini-2.0-flash",
            temperature=0.7,
            max_tokens=2048,
            api_key_secret_name="GOOGLE_API_KEY",
            provider_rel=Mock(provider_type="google_genai", api_key="test-key"),
        )

        mock_config_provider = AsyncMock()
        mock_config_provider.get_chatbot.return_value = mock_chatbot
        mock_config_provider.get_llm_config.return_value = mock_config

        with patch('server.app.modules.agents_hub.services.model_factory.ChatGoogleGenerativeAI') as mock_cls:
            model_instance = Mock()
            mock_cls.return_value = model_instance
            model = await get_model(uuid.uuid4(), mock_config_provider)

        mock_cls.assert_called_once()
        assert model is not None
        assert getattr(model, "_prompt_caching_enabled") is True
        assert getattr(model, "_prompt_cache_ttl") == 7200

    @pytest.mark.asyncio
    async def test_model_factory_returns_openai_model(self) -> None:
        from server.app.modules.agents_hub.services.model_factory import get_model

        mock_chatbot = Mock(llm_config_id=uuid.uuid4(), use_prompt_caching=False, cache_ttl=3600)
        mock_config = Mock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.5,
            max_tokens=1024,
            api_key_secret_name="OPENAI_API_KEY",
            provider_rel=Mock(provider_type="openai_compatible", api_key="test-key", base_url=None),
        )

        mock_config_provider = AsyncMock()
        mock_config_provider.get_chatbot.return_value = mock_chatbot
        mock_config_provider.get_llm_config.return_value = mock_config

        with patch('server.app.modules.agents_hub.services.model_factory.ChatOpenAI') as mock_cls:
            model_instance = Mock()
            mock_cls.return_value = model_instance
            model = await get_model(uuid.uuid4(), mock_config_provider)

        mock_cls.assert_called_once()
        assert getattr(model, "_prompt_caching_enabled") is False
        assert getattr(model, "_prompt_cache_ttl") == 3600

    @pytest.mark.asyncio
    async def test_model_factory_switching(self) -> None:
        """Cambiar el provider en la config devuelve el tipo correcto sin reiniciar."""
        from server.app.modules.agents_hub.services.model_factory import _build_model

        config_google = Mock(
            provider="google",
            model_name="gemini-2.0-flash",
            temperature=0.7,
            max_tokens=2048,
            api_key_secret_name=None,
            provider_rel=Mock(provider_type="google_genai", api_key="test-key"),
        )
        config_openai = Mock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
            api_key_secret_name=None,
            provider_rel=Mock(provider_type="openai_compatible", api_key="test-key", base_url=None),
        )

        with patch('server.app.modules.agents_hub.services.model_factory.ChatGoogleGenerativeAI') as g_cls, \
             patch('server.app.modules.agents_hub.services.model_factory.ChatOpenAI') as o_cls:
            g_cls.return_value = Mock(spec=["provider"])
            o_cls.return_value = Mock(spec=["provider"])

            model_g = _build_model(config_google)
            model_o = _build_model(config_openai)

        g_cls.assert_called_once()
        o_cls.assert_called_once()


class TestPromptService:

    @pytest.mark.asyncio
    async def test_prompt_formats_variables(self) -> None:
        from server.app.modules.agents_hub.services.prompt_service import get_formatted_prompt

        template = Mock()
        template.template_text = "Hola {name}, tienes {count} tareas."

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=template))
        )

        result = await get_formatted_prompt(
            chatbot_id=uuid.uuid4(),
            slug="greeting",
            language="es",
            session=mock_session,
            name="Ana",
            count="3",
        )

        assert result == "Hola Ana, tienes 3 tareas."

    @pytest.mark.asyncio
    async def test_prompt_injection_safety(self) -> None:
        """Variables inexistentes no rompen el flujo — devuelve template sin formatear."""
        from server.app.modules.agents_hub.services.prompt_service import get_formatted_prompt

        template = Mock()
        template.template_text = "Hola {name}, tienes {count} tareas."

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=template))
        )

        # Solo se pasa 'name', falta 'count'
        result = await get_formatted_prompt(
            chatbot_id=uuid.uuid4(),
            slug="greeting",
            language="es",
            session=mock_session,
            name="Ana",
        )

        # Devuelve el template sin formatear en lugar de lanzar excepción
        assert "{name}" in result or "Ana" in result
