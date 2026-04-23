"""Factoría dinámica de modelos LLM según configuración de la base de datos."""
import os
import uuid

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.models import HubLLMConfig


async def get_model(chatbot_id: uuid.UUID, session: AsyncSession):
    """Devuelve la instancia LLM configurada para el chatbot.

    Consulta la tabla hub_llm_configs y devuelve el objeto LangChain
    correspondiente al provider (google | openai | ollama).

    Args:
        chatbot_id: ID del chatbot
        session: Sesión de base de datos

    Returns:
        Instancia del modelo LLM
    """
    from server.app.modules.agents_hub.database.models import HubChatbot

    result = await session.execute(
        select(HubChatbot).where(HubChatbot.id == chatbot_id)
    )
    chatbot = result.scalar_one_or_none()
    if chatbot is None:
        raise ValueError(f"Chatbot {chatbot_id} not found")

    result = await session.execute(
        select(HubLLMConfig).where(HubLLMConfig.id == chatbot.llm_config_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise ValueError(f"LLM config not found for chatbot {chatbot_id}")

    return _build_model(config)


def _build_model(config: HubLLMConfig):
    """Construye la instancia LLM a partir del config."""
    api_key = os.getenv(config.api_key_secret_name or "", "")

    if config.provider == "google":
        return ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=api_key,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        )
    elif config.provider == "openai":
        return ChatOpenAI(
            model=config.model_name,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    elif config.provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=config.model_name,
            temperature=config.temperature,
        )
    else:
        raise ValueError(f"Provider desconocido: {config.provider}")
