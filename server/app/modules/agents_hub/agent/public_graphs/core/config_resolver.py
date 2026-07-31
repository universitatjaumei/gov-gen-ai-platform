"""ConfigResolver: resuelve la configuración efectiva del grafo público.

Cascada: PlatformDefaults → OrgDefaults (HubOrganizacion) → ChatbotOverrides (HubChatbot).
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
    # RAG.2: el system_prompt del chatbot entra por la cascada porque *es* configuración
    # efectiva del chatbot. Así la TemplateStrategy —única fuente del system prompt— lo
    # recibe por el mismo camino que el resto de la config, sin parámetros paralelos.
    system_prompt: str | None = None
    # VIS.2: presupuesto de contexto para la inyección de documentos. Mismo argumento que
    # el system_prompt para entrar por aquí.
    #
    # El default de plataforma son 128.000 tokens porque el Nivel 2 inyecta documentos
    # ENTEROS (1-3 normas, ~25k). **Aviso para RAG.5**, que reutiliza esta columna en su
    # empaquetador de chunks: su prompt pide un default de plataforma de 4.000, y bajarlo
    # aquí recortaría MD_LONG_CONTEXT a 4k, o sea lo dejaría inservible. Si el packer de
    # RAG necesita un techo más bajo, que lo aplique en el packer —`min(budget, 4_000)`—
    # y no en el default compartido. Un valor que significa dos cosas distintas según
    # quién lo lea es la clase de deuda que hay que ver venir.
    context_token_budget: int = 128_000
    # VIS.2 (Nivel 0): índice de submaterias del vocabulario de la organización. Se resuelve
    # solo en MD_AGENT_SELECTOR —en RAG serían ~2.300 tokens de prompt que nadie usa— y
    # entra por la cascada porque depende de la organización del chatbot, igual que el resto.
    router_index: str | None = None


_PLATFORM_DEFAULTS = PublicGraphConfig(
    profile="PUBLIC_KB_RICH",
    retrieval_mode="RAG",
    language_mode="prefer",
    quality_threshold=0.6,
    min_retrieval_results=2,
    min_retrieval_score=0.25,
    reranker_enabled=True,
    answer_template="generic",
    context_token_budget=128_000,
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
    from server.app.modules.agents_hub.database.config_models import HubChatbot, HubOrganizacion

    config = replace(_PLATFORM_DEFAULTS, chatbot_id=chatbot_id)

    chatbot = await session.get(HubChatbot, chatbot_id)
    if chatbot is None:
        return config

    organizacion = await session.get(HubOrganizacion, chatbot.organizacion_id)
    if organizacion is not None:
        config = _apply_layer(config, {
            "profile":               organizacion.default_public_graph_profile,
            "retrieval_mode":        organizacion.default_retrieval_mode,
            "language_mode":         organizacion.default_language_mode,
            "quality_threshold":     organizacion.default_quality_threshold,
            "min_retrieval_results": organizacion.default_min_retrieval_results,
            "min_retrieval_score":   organizacion.default_min_retrieval_score,
            "reranker_enabled":      organizacion.default_reranker_enabled,
            "answer_template":       organizacion.default_answer_template,
            "context_token_budget":  organizacion.default_context_token_budget,
        })

    config = _apply_layer(config, {
        "profile":               chatbot.public_graph_profile,
        "retrieval_mode":        chatbot.retrieval_mode,
        "system_prompt":         chatbot.system_prompt,
        "language_mode":         chatbot.language_mode,
        "quality_threshold":     chatbot.quality_threshold,
        "min_retrieval_results": chatbot.min_retrieval_results,
        "min_retrieval_score":   chatbot.min_retrieval_score,
        "reranker_enabled":      chatbot.reranker_enabled,
        "answer_template":       chatbot.answer_template,
        "context_token_budget":  chatbot.context_token_budget,
    })

    if config.retrieval_mode == "MD_AGENT_SELECTOR":
        config = replace(
            config,
            router_index=await _build_router_index(chatbot.organizacion_id, session),
        )

    return config


async def _build_router_index(organizacion_id: uuid.UUID, session: Any) -> str | None:
    """Índice de submaterias del Nivel 0, vía ConfigProvider (nunca el ORM del vocabulario).

    Devuelve None si la organización no tiene vocabulario cargado: el system prompt se
    compone igual y el modo selector degrada al catálogo de documentos, que es el
    comportamiento previo a VIS.2. Un vocabulario vacío no es un error de configuración.
    """
    from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
    from server.app.modules.agents_hub.services.vocabulary_service import VocabularyService

    servicio = VocabularyService(LocalConfigProvider(session), organizacion_id)
    index = await servicio.build_router_index()
    return index or None
