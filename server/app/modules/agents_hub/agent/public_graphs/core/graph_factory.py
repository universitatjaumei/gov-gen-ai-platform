"""GraphFactory — punto de integración: config → perfil → CoreGraph.

Flujo:
  1. get_effective_public_graph_config(chatbot_id, session) → PublicGraphConfig
  2. registry.get_profile(cfg.profile) → ProfileFactory
  3. ProfileFactory(cfg, deps, llm) → CoreGraph

Deploy: edge
"""
from __future__ import annotations

import uuid
from typing import Any

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    get_effective_public_graph_config,
)
from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import CoreGraph
from server.app.modules.agents_hub.agent.public_graphs.registry import (
    GraphProfileRegistry,
    _default_registry,
    register_profile,
)
from server.app.modules.agents_hub.agent.public_graphs.types import PublicGraphProfile


class GraphFactory:
    """Resuelve la config efectiva, selecciona el perfil del registry y crea CoreGraph."""

    def __init__(self, registry: GraphProfileRegistry | None = None) -> None:
        self._registry = registry if registry is not None else _default_registry

    async def build(
        self,
        chatbot_id: uuid.UUID,
        deps: Any,
        llm: Any = None,
    ) -> CoreGraph:
        cfg = await get_effective_public_graph_config(chatbot_id, deps.session)
        profile_factory = self._registry.get_profile(cfg.profile)
        grafo = profile_factory(cfg, deps, llm)
        # RAG.10: el LLM de reescritura se asigna aquí y no se pasa por las tres factorías
        # de perfil. Es una decisión de composición que depende de la cascada —igual que el
        # AgenticLoop— y añadirlo a sus firmas obligaría a los tres perfiles a conocer algo
        # que ninguno usa. Si el modelo no se puede construir, la reescritura simplemente no
        # está disponible: el chat no puede caerse por una optimización de recuperación.
        if getattr(cfg, "query_rewriting_enabled", False):
            grafo.rewrite_llm = await _resolver_llm_de_reescritura(cfg, deps)
        return grafo


# ---------------------------------------------------------------------------
# Registro de perfiles en el registry por defecto
# ---------------------------------------------------------------------------


async def _resolver_llm_de_reescritura(cfg: Any, deps: Any):
    """Modelo de reescritura, o None si no se puede construir (RAG.10).

    Devolver None en vez de propagar es lo mismo que hacen los tres fallbacks del
    reescritor, y por el mismo motivo: la conversación no se cae porque falte un modelo
    auxiliar. Aquí sí es correcto tragarse el error —no es el patrón «fallback silencioso»
    que el proyecto prohíbe, porque no se degrada a otro modelo: se apaga el paso entero y
    se busca con lo que escribió el usuario, que es el comportamiento por defecto.
    """
    import logging

    from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
    from server.app.modules.agents_hub.services.model_factory import get_rewrite_model

    try:
        return await get_rewrite_model(
            cfg.chatbot_id,
            LocalConfigProvider(deps.session),
            rewrite_llm_config_id=getattr(cfg, "rewrite_llm_config_id", None),
        )
    except Exception as fallo:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "Reescritura no disponible para %s: %s", cfg.chatbot_id, fallo
        )
        return None


def build_agentic_loop_if_needed(cfg: Any, deps: Any):
    """AgenticLoop sólo en MD_AGENT_SELECTOR y sólo si hay LLM al que hacer bind_tools.

    Vive aquí, en el punto de integración, porque es una decisión de composición: el
    CoreGraph no debe conocer el retrieval_mode (RAG.2).
    """
    if cfg.retrieval_mode != "MD_AGENT_SELECTOR":
        return None

    from server.app.modules.agents_hub.agent.public_graphs.strategies.agentic_loop import (
        AgenticLoop,
    )
    from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
        AgenticRetrievalStrategy,
    )

    estrategia = AgenticRetrievalStrategy(deps.session)
    return AgenticLoop(
        reader=_ReaderDesdeEstrategia(estrategia),
        tools=estrategia.get_agent_tools(),
    )


class _ReaderDesdeEstrategia:
    """Adapta AgenticRetrievalStrategy al protocolo DocumentReader del AgenticLoop."""

    def __init__(self, estrategia: Any) -> None:
        self._estrategia = estrategia

    @property
    def last_index_level(self) -> str | None:
        """Escalón del último índice servido; el loop lo sella en la evidencia (VIS.2)."""
        return getattr(self._estrategia, "last_index_level", None)

    async def list_index(
        self,
        chatbot_id: str,
        language: str | None,
        submateries: list[str] | None = None,
    ) -> str:
        from server.app.modules.agents_hub.agent.tools.list_documents import list_documents

        return await list_documents(chatbot_id, self._estrategia, language, submateries)

    async def read(self, document_id: Any) -> dict | None:
        return await self._estrategia.read(document_id)


def _make_public_kb_rich(cfg: Any, deps: Any, llm: Any = None) -> CoreGraph:
    from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
        DefaultLanguagePolicy,
        GenericAnswerTemplateStrategy,
        PassthroughMergeStrategy,
        SingleSourceRetrievalStrategy,
    )

    return CoreGraph(
        retrieval_strategy=SingleSourceRetrievalStrategy(),
        merge_strategy=PassthroughMergeStrategy(),
        template_strategy=GenericAnswerTemplateStrategy(
            base_system_prompt=getattr(cfg, "system_prompt", None),
            retrieval_mode=cfg.retrieval_mode,
            router_index=getattr(cfg, "router_index", None),
        ),
        language_policy=DefaultLanguagePolicy(),
        cfg=cfg,
        deps=deps,
        llm=llm,
        agentic_loop=build_agentic_loop_if_needed(cfg, deps),
    )


def _make_public_portal_aggregator(cfg: Any, deps: Any, llm: Any = None) -> CoreGraph:
    """Stub: usa UUID nulo como placeholder; los IDs reales se configuran por tenant."""
    from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
        DefaultLanguagePolicy,
    )
    from server.app.modules.agents_hub.agent.public_graphs.profiles.public_portal_aggregator import (
        UjiAnswerTemplateStrategy,
        UjiDualSourceRetrievalStrategy,
        UjiMergeStrategy,
    )

    return CoreGraph(
        retrieval_strategy=UjiDualSourceRetrievalStrategy(
            procedimientos_chatbot_id=uuid.UUID(int=0),
            normativa_chatbot_id=uuid.UUID(int=0),
        ),
        merge_strategy=UjiMergeStrategy(),
        template_strategy=UjiAnswerTemplateStrategy(),
        language_policy=DefaultLanguagePolicy(),
        cfg=cfg,
        deps=deps,
        llm=llm,
    )


def _make_public_portal_router(cfg: Any, deps: Any, llm: Any = None) -> CoreGraph:
    """Stub: sin chatbots hijos; la lista se configura por tenant."""
    from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
        DefaultLanguagePolicy,
        GenericAnswerTemplateStrategy,
        PassthroughMergeStrategy,
    )
    from server.app.modules.agents_hub.agent.public_graphs.profiles.public_portal_router import (
        PortalRouterRetrievalStrategy,
    )

    return CoreGraph(
        retrieval_strategy=PortalRouterRetrievalStrategy(child_chatbot_ids=[]),
        merge_strategy=PassthroughMergeStrategy(),
        template_strategy=GenericAnswerTemplateStrategy(),
        language_policy=DefaultLanguagePolicy(),
        cfg=cfg,
        deps=deps,
        llm=llm,
    )


register_profile(PublicGraphProfile.PUBLIC_KB_RICH, _make_public_kb_rich)
register_profile(PublicGraphProfile.PUBLIC_PORTAL_AGGREGATOR, _make_public_portal_aggregator)
register_profile(PublicGraphProfile.PUBLIC_PORTAL_ROUTER, _make_public_portal_router)
