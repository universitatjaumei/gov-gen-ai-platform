"""Protocolos de estrategias para grafos públicos.

RetrievalStrategy / MergeStrategy / TemplateStrategy / LanguagePolicy.
RetrievalStrategy delega al pipeline que corresponde a cfg.retrieval_mode
usando RetrievalPipelineFactory — sin que CoreGraph necesite conocer el modo.

Deploy: edge
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_factory import (
    get_pipeline,
)

if TYPE_CHECKING:
    from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
        PublicGraphConfig,
    )
    from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
        GraphDeps,
    )


@dataclass
class RetrievalOutput:
    """Salida de RetrievalStrategy.

    Contiene uno o varios buckets (RetrievalResult). Cada bucket corresponde
    a una fuente o estrategia de retrieval distinta; CoreGraph los fusiona
    antes de generar la respuesta.
    """

    buckets: list[RetrievalResult] = field(default_factory=list)


class RetrievalStrategy(Protocol):
    """Protocolo de estrategia de retrieval para grafos públicos."""

    async def retrieve(
        self,
        query: str,
        chatbot_id: str,
        cfg: "PublicGraphConfig",
        deps: "GraphDeps",
    ) -> RetrievalOutput: ...


class MergeStrategy(Protocol):
    """Fusiona los buckets de un RetrievalOutput en una lista plana de EvidenceItem."""

    def merge(self, output: RetrievalOutput) -> list[EvidenceItem]: ...


class TemplateStrategy(Protocol):
    """Construye el contexto de prompt que se entrega al LLM."""

    def build_prompt_context(
        self,
        items: list[EvidenceItem],
        language: str | None,
        query: str,
    ) -> str: ...


class LanguagePolicy(Protocol):
    """Política de idioma: detección + filtros post-merge + warning de traducción."""

    def detect(self, query: str) -> str | None: ...

    def needs_secondary_search(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> bool:
        """True si conviene lanzar una segunda búsqueda en el idioma del usuario."""
        ...

    def filter_items(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        """Devuelve los items permitidos por esta política (filtrado o pass-through)."""
        ...

    def should_warn_translation(
        self,
        query_language: str | None,
        context_source_language: str | None,
    ) -> bool:
        """True si la diferencia de idioma entre consulta y contexto merece un aviso."""
        ...


class PreferLanguagePolicy:
    """prefer: prioriza el idioma del usuario; omite doble búsqueda si ya hay evidencia."""

    def detect(self, query: str) -> str | None:
        return None  # subclases con detector real anulan este método

    def needs_secondary_search(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> bool:
        if query_language is None:
            return False
        return not any(item.language == query_language for item in items)

    def filter_items(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        return items  # prefer no filtra: pasa todos los items

    def should_warn_translation(
        self,
        query_language: str | None,
        context_source_language: str | None,
    ) -> bool:
        return (
            query_language is not None
            and context_source_language is not None
            and query_language != context_source_language
        )


class StrictLanguagePolicy:
    """strict: filtra items al idioma del usuario; puede disparar fallback si quedan pocos."""

    def detect(self, query: str) -> str | None:
        return None

    def needs_secondary_search(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> bool:
        return False  # strict filtra y acepta fallback; no busca de nuevo

    def filter_items(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        if query_language is None:
            return items
        return [item for item in items if item.language == query_language]

    def should_warn_translation(
        self,
        query_language: str | None,
        context_source_language: str | None,
    ) -> bool:
        return (
            query_language is not None
            and context_source_language is not None
            and query_language != context_source_language
        )


class NeutralLanguagePolicy:
    """none: sin filtros de idioma ni warnings de traducción."""

    def detect(self, query: str) -> str | None:
        return None

    def needs_secondary_search(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> bool:
        return False

    def filter_items(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        return items

    def should_warn_translation(
        self,
        query_language: str | None,
        context_source_language: str | None,
    ) -> bool:
        return False


class PipelineRetrievalStrategy:
    """Estrategia por defecto: delega al pipeline indicado por cfg.retrieval_mode.

    Así CoreGraph puede cambiar de modo de retrieval sin modificar su lógica:
    sólo cambia cfg.retrieval_mode y esta estrategia enruta al pipeline correcto.
    """

    async def retrieve(
        self,
        query: str,
        chatbot_id: str,
        cfg: "PublicGraphConfig",
        deps: "GraphDeps",
    ) -> RetrievalOutput:
        pipeline = get_pipeline(cfg.retrieval_mode)
        result = await pipeline.run(query, chatbot_id, cfg, deps)
        return RetrievalOutput(buckets=[result])
