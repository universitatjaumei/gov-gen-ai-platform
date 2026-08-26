"""RagVectorPipeline — adapta VectorRetrievalStrategy al contrato de RetrievalPipeline.

Deploy: edge
"""
from __future__ import annotations

import uuid
from collections import Counter

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.services.reranker import resolve_reranker
from server.app.modules.agents_hub.services.retrieval.context_packer import pack
from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
    LONG_CONTEXT_TOKEN_LIMIT,
)
from server.app.modules.agents_hub.services.retrieval.types import Source
from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
    VectorRetrievalStrategy,
)


def _source_to_evidence(source: Source) -> EvidenceItem:
    # FAQ.2: si el fragmento sale de una FAQ, el aviso va DENTRO del texto que ve el modelo.
    # Marcarlo solo en el JSON dejaría que la respuesta presentara la sugerencia como si
    # fuera la norma, con una etiqueta al lado que la contradice.
    from server.app.modules.agents_hub.services.retrieval.citations import (
        marcar_autoridad,
    )

    return EvidenceItem(
        source_id=str(source.document_id),
        content=marcar_autoridad(source.excerpt, source.metadata),
        source_url=source.url,
        title=source.title,
        language=source.metadata.get("language"),
        score=source.score,
        metadata=source.metadata,
    )


def _dominant_language(items: list[EvidenceItem]) -> str | None:
    langs = [i.language for i in items if i.language]
    if not langs:
        return None
    return Counter(langs).most_common(1)[0][0]


class RagVectorPipeline:
    """Pipeline RAG vectorial: HybridRetriever + agrupación por documento → EvidenceItem."""

    async def _construir_estrategia(self, deps, cfg) -> VectorRetrievalStrategy:
        """Punto de extensión que RAG.5 dejó puesto y RAG.6a usa para el reranker.

        El reranker se resuelve **solo si el flag está encendido**, y si está encendido y no
        hay configuración, `resolve_reranker` lanza. Deliberado: seguir sin reranker en
        silencio haría creer al admin que está actuando. El flag viene en `False` por defecto
        desde MOD.2, así que nada de esto se activa por sorpresa.
        """
        reranker = None
        if getattr(cfg, "reranker_enabled", False):
            reranker = await resolve_reranker(deps.session)

        return VectorRetrievalStrategy(
            session=deps.session,
            embedding_service=deps.embedder,
            # RAG.15 — la ANCHURA, no el mínimo. Aquí iba `cfg.min_retrieval_results`, que en el
            # piloto valía 1: el asistente componía cada respuesta leyendo **un** fragmento de un
            # corpus de 23.306, y las 25 consultas del lote citaban una sola fuente. Los dos
            # números existían y significaban cosas distintas; sólo se leía uno.
            top_k=getattr(cfg, "retrieval_top_k", None) or cfg.min_retrieval_results,
            min_score=getattr(cfg, "min_retrieval_score", 0.0) or 0.0,
            reranker=reranker,
            # HIB.J — `None` deja que la estrategia lo derive con `pool_size(top_k)`.
            candidate_k=getattr(cfg, "candidate_k", None),
        )

    async def run(
        self,
        query: str,
        chatbot_id: str,
        cfg,
        deps,
    ) -> RetrievalResult:
        strategy = await self._construir_estrategia(deps, cfg)
        ctx = await strategy.get_context(
            query=query,
            chatbot_id=uuid.UUID(chatbot_id) if isinstance(chatbot_id, str) else chatbot_id,
        )
        # RAG.5: el contexto se empaqueta contra el presupuesto de la cascada antes de
        # construir el bloque DOCUMENTOS DISPONIBLES. Sin esto, quien recortaba era el
        # proveedor del modelo, y sin dejar traza de qué se habia perdido.
        presupuesto = getattr(cfg, "context_token_budget", None) or LONG_CONTEXT_TOKEN_LIMIT
        empaquetado = pack([_source_to_evidence(s) for s in ctx.sources], presupuesto)

        return RetrievalResult(
            items=empaquetado.items,
            debug={
                "pipeline_mode": "RAG",
                "total_tokens": empaquetado.total_tokens,
                "sources": len(empaquetado.items),
                "dropped_count": empaquetado.dropped_count,
                "context_token_budget": presupuesto,
                "min_retrieval_score": getattr(cfg, "min_retrieval_score", 0.0),
            },
            context_source_language=_dominant_language(empaquetado.items),
        )
