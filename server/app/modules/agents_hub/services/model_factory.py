"""Factoría dinámica de modelos LLM según configuración de la base de datos."""

import os
import uuid

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from server.app.modules.agents_hub.database.config_models import HubLLMConfig

from server.app.modules.agents_hub.services.config_provider import ConfigProvider

DEFAULT_API_KEY_ENV_BY_PROVIDER_ID: dict[str, str] = {
    "google": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
}


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

    return _build_model(config, chatbot=chatbot)


def _apply_prompt_caching(model, chatbot) -> None:
    if not chatbot:
        return
    enabled = bool(getattr(chatbot, "use_prompt_caching", False))
    ttl = int(getattr(chatbot, "cache_ttl", 3600) or 3600)
    setattr(model, "_prompt_caching_enabled", enabled)
    setattr(model, "_prompt_cache_ttl", ttl)

def _build_model(config: HubLLMConfig, chatbot=None):
    """Construye la instancia LLM a partir del config y su proveedor."""
    provider = getattr(config, "provider_rel", None)
    if not provider:
        raise ValueError(f"Provider not loaded or missing for config {config.id}")

    provider_id = str(getattr(provider, "id", None) or getattr(config, "provider", "") or "").lower()
    provider_name = str(getattr(provider, "name", None) or "").lower()
    provider_base_url = str(getattr(provider, "base_url", None) or "").lower()
    configured_secret_name = (config.api_key_secret_name or "").strip()
    fallback_secret_name = DEFAULT_API_KEY_ENV_BY_PROVIDER_ID.get(provider_id)

    # Detección robusta de OpenRouter aunque el id no sea exactamente "openrouter".
    is_openrouter = (
        "openrouter" in provider_id
        or "openrouter" in provider_name
        or "openrouter.ai" in provider_base_url
    )
    if not fallback_secret_name and is_openrouter:
        fallback_secret_name = "OPENROUTER_API_KEY"

    # Prioridad: api_key explícita del proveedor -> variable configurada en la config -> fallback por proveedor.
    api_key = provider.api_key
    if not api_key and configured_secret_name:
        api_key = os.getenv(configured_secret_name) or None
    if not api_key and fallback_secret_name:
        api_key = os.getenv(fallback_secret_name) or None

    ptype = provider.provider_type

    if ptype == "google_genai":
        kwargs: dict = dict(
            model=config.model_name,
            temperature=config.temperature,
            top_p=getattr(config, "top_p", 1.0),
            max_output_tokens=config.max_tokens,
        )
        if api_key:
            kwargs["google_api_key"] = api_key
        model = ChatGoogleGenerativeAI(**kwargs)
        _apply_prompt_caching(model, chatbot)
        return model
        
    elif ptype == "openai_compatible":
        kwargs = dict(
            model=config.model_name,
            temperature=config.temperature,
            top_p=getattr(config, "top_p", 1.0),
            max_tokens=config.max_tokens,
        )
        if api_key:
            kwargs["api_key"] = api_key
        # Use base_url from provider if available
        if provider.base_url:
            kwargs["base_url"] = provider.base_url

        if not kwargs.get("api_key"):
            raise ValueError(
                "Falta API key para provider openai_compatible. "
                "Configura `api_key` en el proveedor o `api_key_secret_name` "
                "(por ejemplo OPENROUTER_API_KEY / OPENAI_API_KEY)."
            )

        model = ChatOpenAI(**kwargs)
        _apply_prompt_caching(model, chatbot)
        return model
        
    elif ptype == "ollama":
        from langchain_community.chat_models import ChatOllama

        kwargs = dict(
            model=config.model_name,
            temperature=config.temperature,
            top_p=getattr(config, "top_p", 1.0),
        )
        if provider.base_url:
            kwargs["base_url"] = provider.base_url
        model = ChatOllama(**kwargs)
        _apply_prompt_caching(model, chatbot)
        return model
        
    else:
        raise ValueError(f"Provider type desconocido: {ptype}")
