"""Protocolo RetrievalPipeline para grafos públicos.

Cada implementación concreta (RAG, MD_LONG_CONTEXT, MD_AGENT_SELECTOR)
debe cumplir este contrato. El CoreGraph usa exclusivamente este protocolo,
sin depender de ninguna implementación específica.

Deploy: edge
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
        PublicGraphConfig,
    )
    from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
        RetrievalResult,
    )


@dataclass
class GraphDeps:
    """Dependencias de ejecución inyectadas en cada pipeline.

    session: sesión async de SQLAlchemy (para consultar documentos y chunks).
    embedder: servicio de embedding (protocolo EmbeddingService).
    llm: modelo de lenguaje opcional (requerido por MD_AGENT_SELECTOR).
    """

    session: Any
    embedder: Any
    llm: Any = None


class RetrievalPipeline(Protocol):
    """Contrato que deben cumplir todas las implementaciones de pipeline de retrieval."""

    async def run(
        self,
        query: str,
        chatbot_id: str,
        cfg: "PublicGraphConfig",
        deps: GraphDeps,
    ) -> "RetrievalResult": ...
