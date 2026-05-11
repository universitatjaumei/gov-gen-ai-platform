"""Perfil PUBLIC_PORTAL_ROUTER — portal que enruta entre chatbots hijos.

Cada chatbot hijo cubre un dominio disjunto. El router selecciona el hijo
apropiado y ejecuta el pipeline con la configuración efectiva de ese hijo,
respetando su retrieval_mode.

Deploy: edge
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    get_effective_public_graph_config,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
    RetrievalOutput,
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


class PortalRouterRetrievalStrategy:
    """Enruta la consulta al chatbot hijo más relevante y usa su pipeline.

    child_chatbot_ids: lista ordenada de IDs de chatbots hijos disponibles.

    Stub de selección: devuelve siempre el primero de la lista.
    La selección semántica (por dominio o LLM) se introduce en prompts posteriores.
    """

    def __init__(self, child_chatbot_ids: list[uuid.UUID]) -> None:
        self.child_chatbot_ids = child_chatbot_ids

    async def retrieve(
        self,
        query: str,
        chatbot_id: str,
        cfg: "PublicGraphConfig",
        deps: "GraphDeps",
    ) -> RetrievalOutput:
        child_id = self._select_child()
        if child_id is None:
            return RetrievalOutput(buckets=[])

        child_cfg = await get_effective_public_graph_config(child_id, deps.session)
        pipeline = get_pipeline(child_cfg.retrieval_mode)
        result = await pipeline.run(query, str(child_id), child_cfg, deps)
        return RetrievalOutput(buckets=[result])

    def _select_child(self) -> uuid.UUID | None:
        """Selecciona el chatbot hijo. Stub: devuelve el primero disponible."""
        return self.child_chatbot_ids[0] if self.child_chatbot_ids else None
