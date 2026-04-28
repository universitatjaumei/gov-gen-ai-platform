"""LongContextRetrievalStrategy -- empaqueta todo el corpus en el contexto del LLM."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext, Source


LONG_CONTEXT_TOKEN_LIMIT = 150_000


class LongContextRetrievalStrategy:
    mode = "long_context"

    def __init__(self, session: AsyncSession, token_limit: int = LONG_CONTEXT_TOKEN_LIMIT):
        self._session = session
        self._token_limit = token_limit

    async def get_context(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
    ) -> RetrievalContext:
        stmt = select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
        if language:
            stmt = stmt.where(HubDocument.language == language)
        stmt = stmt.order_by(HubDocument.created_at)
        result = await self._session.execute(stmt)
        documents = list(result.scalars().all())

        total = sum(d.token_count for d in documents)
        if total > self._token_limit:
            raise ValueError(
                f"long context mode no admite corpus de {total} tokens "
                f"(limite {self._token_limit}). Cambia el modo a 'agentic' o 'vector'."
            )

        sources = [
            Source(
                document_id=d.id,
                title=d.title,
                url=d.canonical_url,
                excerpt=d.markdown_content,
                score=1.0,
                metadata={
                    "language": d.language,
                    "section_path": d.section_path,
                    "cacheable": True,
                },
            )
            for d in documents
        ]
        return RetrievalContext(sources=sources, mode=self.mode, total_tokens=total)

    def get_agent_tools(self) -> list:
        return []
