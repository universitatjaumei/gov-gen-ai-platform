"""Factoría dinámica de modelos LLM según configuración de la base de datos."""

import os
import uuid

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from server.app.modules.agents_hub.database.config_models import HubLLMConfig

from server.app.modules.agents_hub.services.config_provider import ConfigProvider


async def get_model(chatbot_id: uuid.UUID, config_provider: ConfigProvider):
    """Devuelve la instancia LLM configurada para el chatbot.

    Consulta a través del ConfigProvider y devuelve el objeto LangChain
    correspondiente al provider (google | openai | ollama).

    Args:
        chatbot_id: ID del chatbot
        config_provider: Proveedor de configuración

    Returns:
        Instancia del modelo LLM
    """
    chatbot = await config_provider.get_chatbot(chatbot_id)
    if chatbot is None:
        raise ValueError(f"Chatbot {chatbot_id} not found")

    config = await config_provider.get_llm_config(chatbot.llm_config_id)
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
