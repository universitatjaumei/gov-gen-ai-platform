"""ConfigResolver: resuelve la configuración efectiva del grafo público.

Cascada: PlatformDefaults → OrgDefaults (HubClient) → ChatbotOverrides (HubChatbot).
Un campo None en el chatbot o el org indica "heredar del nivel superior".

Deploy: edge
"""
import uuid
from dataclasses import dataclass, replace
from typing import Any


@dataclass
class PublicGraphConfig:
    profile: str
    retrieval_mode: str
    language_mode: str
    quality_threshold: float
    min_retrieval_results: int
    min_retrieval_score: float
    reranker_enabled: bool
    answer_template: str
    chatbot_id: uuid.UUID | None = None


_PLATFORM_DEFAULTS = PublicGraphConfig(
    profile="PUBLIC_KB_RICH",
    retrieval_mode="RAG",
    language_mode="prefer",
    quality_threshold=0.6,
    min_retrieval_results=2,
    min_retrieval_score=0.25,
    reranker_enabled=True,
    answer_template="generic",
)


def _apply_layer(config: PublicGraphConfig, values: dict[str, Any]) -> PublicGraphConfig:
    """Devuelve un nuevo PublicGraphConfig con los campos no-None de values aplicados."""
    overrides = {k: v for k, v in values.items() if v is not None}
    return replace(config, **overrides) if overrides else config


async def get_effective_public_graph_config(
    chatbot_id: uuid.UUID,
    session: Any,
) -> PublicGraphConfig:
    """Resuelve la configuración efectiva del grafo público para un chatbot.

    Aplica cascada: plataforma → organización → chatbot.
    """
    from server.app.modules.agents_hub.database.config_models import HubChatbot, HubClient

    config = replace(_PLATFORM_DEFAULTS, chatbot_id=chatbot_id)

    chatbot = await session.get(HubChatbot, chatbot_id)
    if chatbot is None:
        return config

    client = await session.get(HubClient, chatbot.client_id)
    if client is not None:
        config = _apply_layer(config, {
            "profile":               client.default_public_graph_profile,
            "retrieval_mode":        client.default_retrieval_mode,
            "language_mode":         client.default_language_mode,
            "quality_threshold":     client.default_quality_threshold,
            "min_retrieval_results": client.default_min_retrieval_results,
            "min_retrieval_score":   client.default_min_retrieval_score,
            "reranker_enabled":      client.default_reranker_enabled,
            "answer_template":       client.default_answer_template,
        })

    config = _apply_layer(config, {
        "profile":               chatbot.public_graph_profile,
        "retrieval_mode":        chatbot.retrieval_mode,
        "language_mode":         chatbot.language_mode,
        "quality_threshold":     chatbot.quality_threshold,
        "min_retrieval_results": chatbot.min_retrieval_results,
        "min_retrieval_score":   chatbot.min_retrieval_score,
        "reranker_enabled":      chatbot.reranker_enabled,
        "answer_template":       chatbot.answer_template,
    })

    return config
