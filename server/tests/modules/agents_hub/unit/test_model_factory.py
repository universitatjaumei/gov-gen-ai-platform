"""Tests para la factoría de modelos y el servicio de prompts."""
import uuid
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestModelFactory:

    @pytest.mark.asyncio
    async def test_model_factory_returns_google_model(self) -> None:
        from server.app.modules.agents_hub.services.model_factory import get_model

        mock_chatbot = Mock(llm_config_id=uuid.uuid4())
        mock_config = Mock(
            provider="google",
            model_name="gemini-2.0-flash",
            temperature=0.7,
            max_tokens=2048,
            api_key_secret_name="GOOGLE_API_KEY",
        )

        mock_session = AsyncMock()
        # Two consecutive execute() calls return different Mock results
        mock_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_chatbot)),
            Mock(scalar_one_or_none=Mock(return_value=mock_config)),
        ]

        with patch('server.app.modules.agents_hub.services.model_factory.ChatGoogleGenerativeAI') as mock_cls:
            mock_cls.return_value = Mock()
            model = await get_model(uuid.uuid4(), mock_session)

        mock_cls.assert_called_once()
        assert model is not None

    @pytest.mark.asyncio
    async def test_model_factory_returns_openai_model(self) -> None:
        from server.app.modules.agents_hub.services.model_factory import get_model

        mock_chatbot = Mock(llm_config_id=uuid.uuid4())
        mock_config = Mock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.5,
            max_tokens=1024,
            api_key_secret_name="OPENAI_API_KEY",
        )

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_chatbot)),
            Mock(scalar_one_or_none=Mock(return_value=mock_config)),
        ]

        with patch('server.app.modules.agents_hub.services.model_factory.ChatOpenAI') as mock_cls:
            mock_cls.return_value = Mock()
            model = await get_model(uuid.uuid4(), mock_session)

        mock_cls.assert_called_once()

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
        )
        config_openai = Mock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
            api_key_secret_name=None,
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
