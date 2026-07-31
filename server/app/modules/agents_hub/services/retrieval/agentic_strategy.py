"""AgenticRetrievalStrategy -- el LLM elige que documentos leer.

VIS.1: el indice que ve el modelo esta filtrado por MetadataFilter. Listar un documento
que el actor no puede recuperar seria una fuga aunque nunca llegara a leerse: el titulo
ya dice que existe.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.agent.tools.list_documents import list_documents
from server.app.modules.agents_hub.agent.tools.read_document import read_document
from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.retrieval.metadata_filter import MetadataFilter
from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext


class AgenticRetrievalStrategy:
    mode = "MD_AGENT_SELECTOR"

    def __init__(
        self,
        session: AsyncSession,
        metadata_filter: MetadataFilter | None = None,
    ):
        self._session = session
        self._filter = metadata_filter if metadata_filter is not None else MetadataFilter()

    async def list_index(self, chatbot_id: uuid.UUID, language: str | None) -> list[dict]:
        stmt = select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
        if language:
            stmt = stmt.where(HubDocument.language == language)
        stmt = stmt.where(*self._filter.document_conditions())
        stmt = stmt.order_by(HubDocument.title)
        res = await self._session.execute(stmt)
        return [
            {
                "id": str(d.id),
                "title": d.title,
                "url": d.canonical_url,
                "language": d.language,
                "token_count": d.token_count,
            }
            for d in res.scalars().all()
        ]

    async def read(self, document_id: uuid.UUID) -> dict | None:
        doc = await self._session.get(HubDocument, document_id)
        if not doc:
            return None
        return {
            "title": doc.title,
            "url": doc.canonical_url,
            "markdown_content": doc.markdown_content,
        }

    async def get_context(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
    ) -> RetrievalContext:
        return RetrievalContext(sources=[], mode=self.mode, total_tokens=0)

    def get_agent_tools(self) -> list:
        return [list_documents, read_document]
