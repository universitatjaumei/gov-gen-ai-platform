"""Factoría dinámica de modelos LLM según configuración de la base de datos."""

import os
import uuid

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from server.app.modules.agents_hub.database.config_models import HubLLMConfig

from server.app.modules.agents_hub.services.config_provider import ConfigProvider


async def get_model_for_tier(tier: int, config_provider: ConfigProvider):
    """Devuelve el modelo marcado como is_default para el tier indicado."""
    config = await config_provider.get_llm_config_for_tier(tier)
    if config is None:
        raise ValueError(f"No hay configuración LLM por defecto para tier {tier}")
    return _build_model(config)


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
    """Construye la instancia LLM a partir del config y su proveedor."""
    provider = getattr(config, "provider_rel", None)
    if not provider:
        raise ValueError(f"Provider not loaded or missing for config {config.id}")

    # api_key is primarily from the provider table now. We can still allow api_key_secret_name as fallback if needed.
    api_key = provider.api_key
    if not api_key and config.api_key_secret_name:
        api_key = os.getenv(config.api_key_secret_name) or None

    ptype = provider.provider_type

    if ptype == "google_genai":
        kwargs: dict = dict(
            model=config.model_name,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        )
        if api_key:
            kwargs["google_api_key"] = api_key
        return ChatGoogleGenerativeAI(**kwargs)
        
    elif ptype == "openai_compatible":
        kwargs = dict(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        if api_key:
            kwargs["api_key"] = api_key
        # Use base_url from provider if available
        if provider.base_url:
            kwargs["base_url"] = provider.base_url
        return ChatOpenAI(**kwargs)
        
    elif ptype == "ollama":
        from langchain_community.chat_models import ChatOllama

        kwargs = dict(
            model=config.model_name,
            temperature=config.temperature,
        )
        if provider.base_url:
            kwargs["base_url"] = provider.base_url
        return ChatOllama(**kwargs)
        
    else:
        raise ValueError(f"Provider type desconocido: {ptype}")
