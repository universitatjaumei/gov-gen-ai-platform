"""MdLongContextPipeline — adapta LongContextRetrievalStrategy al contrato de RetrievalPipeline.

Deploy: edge
"""
from __future__ import annotations

import uuid
from collections import Counter

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
    LongContextRetrievalStrategy,
)
from server.app.modules.agents_hub.services.retrieval.types import Source


def _source_to_evidence(source: Source) -> EvidenceItem:
    return EvidenceItem(
        source_id=str(source.document_id),
        content=source.excerpt,
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


class MdLongContextPipeline:
    """Pipeline MD long context: corpus completo en contexto → EvidenceItem por documento."""

    async def run(
        self,
        query: str,
        chatbot_id: str,
        cfg,
        deps,
    ) -> RetrievalResult:
        cid = uuid.UUID(chatbot_id) if isinstance(chatbot_id, str) else chatbot_id
        strategy = LongContextRetrievalStrategy(session=deps.session)
        ctx = await strategy.get_context(query=query, chatbot_id=cid)
        items = [_source_to_evidence(s) for s in ctx.sources]
        return RetrievalResult(
            items=items,
            debug={
                "pipeline_mode": "MD_LONG_CONTEXT",
                "total_tokens": ctx.total_tokens,
                "docs": len(items),
            },
            context_source_language=_dominant_language(items),
        )
