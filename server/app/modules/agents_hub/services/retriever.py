"""Prompt 2.7 — Retriever híbrido (vector + keyword, Reciprocal Rank Fusion)."""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk


@dataclass
class SearchResult:
    id: uuid.UUID
    content: str
    source_url: str
    language: str
    score: float
    metadata: dict = field(default_factory=dict)


class HybridRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def vector_search(
        self,
        query_embedding: list[float],
        chatbot_id: uuid.UUID,
        top_k: int = 5,
        language: str | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> list[SearchResult]:
        similarity = 1 - HubDocumentChunk.embedding.cosine_distance(query_embedding)
        query = (
            select(HubDocumentChunk, similarity.label("score"))
            .where(HubDocumentChunk.chatbot_id == chatbot_id)
            .where(HubDocumentChunk.embedding.isnot(None))
            .where(
                (not HubDocumentChunk.is_temporary)
                | (HubDocumentChunk.owner_id == owner_id)
            )
        )
        if language:
            query = query.where(HubDocumentChunk.language == language)
        query = query.order_by(similarity.desc()).limit(top_k)

        result = await self.session.execute(query)
        return [
            SearchResult(
                id=row.HubDocumentChunk.id,
                content=row.HubDocumentChunk.content,
                source_url=row.HubDocumentChunk.source_url,
                language=row.HubDocumentChunk.language,
                score=float(row.score),
                metadata=row.HubDocumentChunk.chunk_metadata or {},
            )
            for row in result.all()
        ]

    async def keyword_search(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        top_k: int = 5,
        language: str | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> list[SearchResult]:
        filters = [
            HubDocumentChunk.chatbot_id == chatbot_id,
            (not HubDocumentChunk.is_temporary)
            | (HubDocumentChunk.owner_id == owner_id),
        ]
        for word in query.split():
            filters.append(HubDocumentChunk.content.ilike(f"%{word}%"))
        if language:
            filters.append(HubDocumentChunk.language == language)

        stmt = select(HubDocumentChunk).where(*filters).limit(top_k)
        result = await self.session.execute(stmt)
        return [
            SearchResult(
                id=c.id,
                content=c.content,
                source_url=c.source_url,
                language=c.language,
                score=1.0,
                metadata=c.chunk_metadata or {},
            )
            for c in result.scalars().all()
        ]

    async def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        chatbot_id: uuid.UUID,
        top_k: int = 5,
        language: str | None = None,
        vector_weight: float = 0.7,
        owner_id: uuid.UUID | None = None,
    ) -> list[SearchResult]:
        vector_results = await self.vector_search(
            query_embedding, chatbot_id, top_k * 2, language, owner_id
        )
        keyword_results = await self.keyword_search(
            query, chatbot_id, top_k * 2, language, owner_id
        )

        k = 60
        scores: dict[uuid.UUID, tuple[SearchResult, float]] = {}
        for rank, r in enumerate(vector_results):
            scores[r.id] = (r, vector_weight * (1 / (k + rank + 1)))
        for rank, r in enumerate(keyword_results):
            rrf = (1 - vector_weight) * (1 / (k + rank + 1))
            if r.id in scores:
                scores[r.id] = (r, scores[r.id][1] + rrf)
            else:
                scores[r.id] = (r, rrf)

        sorted_results = sorted(scores.values(), key=lambda x: x[1], reverse=True)
        return [
            SearchResult(
                id=r.id,
                content=r.content,
                source_url=r.source_url,
                language=r.language,
                score=s,
                metadata=r.metadata,
            )
            for r, s in sorted_results[:top_k]
        ]
