"""AgenticRetrievalStrategy -- el LLM elige que documentos leer.

VIS.1: el indice que ve el modelo esta filtrado por MetadataFilter. Listar un documento
que el actor no puede recuperar seria una fuga aunque nunca llegara a leerse: el titulo
ya dice que existe.

VIS.2 (Nivel 1): el indice se pide por SUBMATERIA y devuelve FICHAS, no contenido. Si la
seleccion del modelo no encaja con nada, el indice retrocede en escalones —submateria ->
ambito -> catalogo global— y cada escalon queda anotado en `last_index_level`, que la
evidencia arrastra para poder medir cuantas consultas necesitan ensanchar el tema.

El retroceso ensancha el TEMA, nunca el PERMISO: `nivell_acces`, `us_assistents`,
`canonica` y la exclusion de superseded se aplican en los tres escalones.
"""

import uuid
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.agent.tools.list_documents import list_documents
from server.app.modules.agents_hub.agent.tools.read_document import read_document
from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.services.retrieval.metadata_filter import MetadataFilter
from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext

# Escalones del indice, de mas estrecho a mas ancho.
INDEX_LEVEL_SUBMATERIES = "submateries"
INDEX_LEVEL_AMBIT = "ambit"
INDEX_LEVEL_GLOBAL = "global"


class AgenticRetrievalStrategy:
    mode = "MD_AGENT_SELECTOR"

    def __init__(
        self,
        session: AsyncSession,
        metadata_filter: MetadataFilter | None = None,
    ):
        self._session = session
        self._filter = metadata_filter if metadata_filter is not None else MetadataFilter()
        self.last_index_level: str | None = None

    async def list_index(
        self,
        chatbot_id: uuid.UUID,
        language: str | None,
        submateries: list[str] | None = None,
    ) -> list[dict]:
        """Fichas de los documentos del tema pedido, con retroceso escalonado."""
        escalones: list[tuple[str, MetadataFilter]] = []
        if submateries:
            escalones.append((
                INDEX_LEVEL_SUBMATERIES,
                replace(self._filter, submateries=tuple(submateries)),
            ))
        if self._filter.ambits:
            escalones.append((
                INDEX_LEVEL_AMBIT,
                replace(self._filter, submateries=()),
            ))
        escalones.append((
            INDEX_LEVEL_GLOBAL,
            replace(self._filter, submateries=(), ambits=()),
        ))

        fichas: list[dict] = []
        for nivel, filtro in escalones:
            self.last_index_level = nivel
            fichas = await self._fichas(chatbot_id, language, filtro)
            if fichas:
                break
        return fichas

    async def _fichas(
        self,
        chatbot_id: uuid.UUID,
        language: str | None,
        filtro: MetadataFilter,
    ) -> list[dict]:
        stmt = select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
        if language:
            stmt = stmt.where(HubDocument.language == language)
        stmt = stmt.where(*filtro.document_conditions())
        stmt = stmt.order_by(HubDocument.title)
        res = await self._session.execute(stmt)
        # La ficha lleva de qué va la norma y con qué rango manda; el cuerpo se pide
        # despues con read_document. Devolver markdown aqui es volcar el corpus al prompt,
        # que es exactamente lo que el modo selector viene a evitar.
        return [
            {
                "id": str(d.id),
                "title": d.title,
                "url": d.canonical_url,
                "language": d.language,
                "token_count": d.token_count,
                "resum_router": (d.doc_metadata or {}).get("resum_router"),
                "rang": (d.doc_metadata or {}).get("rang"),
                "submateries": list(d.submateries or []),
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
