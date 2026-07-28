"""MdAgentSelectorPipeline — stub del pipeline de selección agéntica.

En esta fase devuelve todo el índice de documentos como EvidenceItem
(sin selección LLM real). La selección real se implementa en 9B.8+
cuando el CoreGraph integra el grafo con herramientas de lectura.

Deploy: edge
"""
from __future__ import annotations

import uuid
from collections import Counter

from sqlalchemy import select

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)


def _dominant_language(items: list[EvidenceItem]) -> str | None:
    langs = [i.language for i in items if i.language]
    if not langs:
        return None
    return Counter(langs).most_common(1)[0][0]


class MdAgentSelectorPipeline:
    """Stub: devuelve el índice de documentos sin selección LLM."""

    async def run(
        self,
        query: str,
        chatbot_id: str,
        cfg,
        deps,
    ) -> RetrievalResult:
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        cid = uuid.UUID(chatbot_id) if isinstance(chatbot_id, str) else chatbot_id
        stmt = select(HubDocument).where(HubDocument.chatbot_id == cid).order_by(HubDocument.title)
        result = await deps.session.execute(stmt)
        documents = list(result.scalars().all())

        items = [
            EvidenceItem(
                source_id=str(d.id),
                content=d.markdown_content or "",
                source_url=d.canonical_url,
                title=d.title,
                language=d.language,
                score=1.0,
                metadata={},
            )
            for d in documents
        ]
        return RetrievalResult(
            items=items,
            debug={
                "pipeline_mode": "MD_AGENT_SELECTOR",
                "docs_available": len(documents),
                "selection": "stub_all",
            },
            context_source_language=_dominant_language(items),
        )
