"""VectorRetrievalStrategy -- envuelve HybridRetriever y agrupa por documento."""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext, Source
from server.app.modules.agents_hub.services.retriever import HybridRetriever


class VectorRetrievalStrategy:
    mode = "RAG"

    def __init__(
        self,
        session: AsyncSession,
        embedding_service,
        top_k: int = 8,
    ):
        self._session = session
        self._embedding = embedding_service
        self._retriever = HybridRetriever(session)
        self._top_k = top_k

    async def get_context(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
    ) -> RetrievalContext:
        query_embedding = await self._embedding.embed(query)
        results = await self._retriever.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            chatbot_id=chatbot_id,
            top_k=self._top_k,
            language=language,
            include_superseded=False,  # el chatbot nunca sirve páginas superseded (9Q.6)
        )
        if not results:
            return RetrievalContext(sources=[], mode=self.mode, total_tokens=0)

        # Group chunks by document_id (from metadata or None for legacy chunks)
        by_doc: dict[uuid.UUID | None, list] = defaultdict(list)
        for r in results:
            raw_id = r.metadata.get("document_id")
            doc_id = uuid.UUID(raw_id) if raw_id else None
            by_doc[doc_id].append(r)

        # Bulk-load documents
        doc_ids = [d for d in by_doc.keys() if d is not None]
        docs_map: dict[uuid.UUID, HubDocument] = {}
        if doc_ids:
            stmt = select(HubDocument).where(HubDocument.id.in_(doc_ids))
            res = await self._session.execute(stmt)
            docs_map = {d.id: d for d in res.scalars().all()}

        sources: list[Source] = []
        total_tokens = 0
        for doc_id, chunks in by_doc.items():
            best = max(chunks, key=lambda c: c.score)
            doc = docs_map.get(doc_id) if doc_id else None
            title = doc.title if doc else best.source_url.rsplit("/", 1)[-1]
            url = doc.canonical_url if doc else best.source_url
            excerpt = best.content
            sources.append(Source(
                document_id=doc.id if doc else uuid.uuid4(),
                title=title,
                url=url,
                excerpt=excerpt,
                score=best.score,
                metadata={"chunks_matched": len(chunks)},
            ))
            total_tokens += len(excerpt) // 4

        sources.sort(key=lambda s: s.score, reverse=True)
        return RetrievalContext(sources=sources, mode=self.mode, total_tokens=total_tokens)

    def get_agent_tools(self) -> list:
        return []
