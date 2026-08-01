"""VectorRetrievalStrategy -- envuelve HybridRetriever y agrupa por documento."""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.retrieval.citations import with_anchor
from server.app.modules.agents_hub.services.retrieval.metadata_filter import MetadataFilter
from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext, Source
from server.app.modules.agents_hub.services.retrieval.vigencia import marca_de_vigencia
from server.app.modules.agents_hub.services.retriever import HybridRetriever


class VectorRetrievalStrategy:
    mode = "RAG"

    def __init__(
        self,
        session: AsyncSession,
        embedding_service,
        top_k: int = 8,
        metadata_filter: MetadataFilter | None = None,
        min_score: float = 0.0,
    ):
        self._session = session
        self._embedding = embedding_service
        self._retriever = HybridRetriever(session)
        self._top_k = top_k
        self._filter = metadata_filter if metadata_filter is not None else MetadataFilter()
        self._min_score = min_score

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
            # El filtro incluye la exclusión de páginas superseded (9Q.6) y el nivel de
            # acceso del actor (VIS.1); el defecto es cerrado.
            metadata_filter=self._filter,
            min_score=self._min_score,
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
            base_url = doc.canonical_url if doc else best.source_url
            # La cita apunta al artículo del que sale la evidencia, no al documento
            # entero: el ancla viene del chunk mejor puntuado (ING.0.4).
            url = with_anchor(base_url, best.metadata)
            excerpt = best.content
            sources.append(Source(
                document_id=doc.id if doc else uuid.uuid4(),
                title=title,
                url=url,
                excerpt=excerpt,
                score=best.score,
                metadata={
                    "chunks_matched": len(chunks),
                    "ancora": best.metadata.get("ancora"),
                    "ruta": best.metadata.get("ruta"),
                    # VIS.3: sin documento no hay dato de vigencia que consultar (chunk
                    # temporal o legado), y en ese caso no se advierte de lo que no se sabe.
                    **(marca_de_vigencia(doc) if doc else {}),
                },
            ))
            total_tokens += len(excerpt) // 4

        sources.sort(key=lambda s: s.score, reverse=True)
        return RetrievalContext(sources=sources, mode=self.mode, total_tokens=total_tokens)

    def get_agent_tools(self) -> list:
        return []
