"""MdAgentSelectorPipeline — evidencia inicial del modo de selección agéntica.

El pipeline entrega un **índice** como evidencia inicial y delega la selección al
`AgenticLoop`, que lee los documentos que decida a través de los tools.

## Por qué el índice es un punto de extensión (enmienda del Bloque VIS, 2026-07-28)

El índice de **documentos** es provisional y no se cementa. Medido en
`INFORME_MATERIES_I_METADADES_AGENTS.md` §6.1: el catálogo de fichas son ~72k tokens y no
cabe en el system prompt; el índice de las 58 submaterias son 2.307 tokens y sí cabe.
**VIS.2 sustituye el proveedor**, no el pipeline ni el grafo — de ahí `IndexProvider`.

Corolario: el índice lleva título y id, **nunca el markdown completo**. La versión anterior
de este fichero devolvía `markdown_content` de todos los documentos del chatbot, que es
exactamente lo que el modo selector viene a evitar: volcar el corpus entero en el prompt.

Deploy: edge
"""
from __future__ import annotations

import uuid
from collections import Counter
from typing import Protocol

from sqlalchemy import select

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.services.retrieval.metadata_filter import MetadataFilter

INDEX_TITLE_MAX = 300


def _dominant_language(items: list[EvidenceItem]) -> str | None:
    langs = [i.language for i in items if i.language]
    if not langs:
        return None
    return Counter(langs).most_common(1)[0][0]


class IndexProvider(Protocol):
    """Construye el índice que se ofrece al selector como evidencia inicial."""

    async def build_index(self, chatbot_id: str, deps) -> list[EvidenceItem]: ...


class DocumentIndexProvider:
    """Índice por documento: título + id, sin el cuerpo.

    Provisional: VIS.2 lo sustituye por el índice de submaterias.

    Aplica el `MetadataFilter` de VIS.1 con el mismo defecto cerrado que las tres
    estrategias de recuperación. Un índice sin filtrar sería una fuga aunque el modelo
    no llegara a leer el documento: el título ya dice que existe.
    """

    def __init__(self, metadata_filter: MetadataFilter | None = None) -> None:
        self._filter = metadata_filter if metadata_filter is not None else MetadataFilter()

    async def build_index(self, chatbot_id: str, deps) -> list[EvidenceItem]:
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        cid = uuid.UUID(chatbot_id) if isinstance(chatbot_id, str) else chatbot_id
        stmt = (
            select(HubDocument)
            .where(HubDocument.chatbot_id == cid)
            .where(*self._filter.document_conditions())
            .order_by(HubDocument.title)
        )
        result = await deps.session.execute(stmt)
        documentos = list(result.scalars().all())

        return [
            EvidenceItem(
                source_id=str(d.id),
                content=f"{(d.title or '(sin título)')[:INDEX_TITLE_MAX]} (id: {d.id})",
                source_url=d.canonical_url,
                title=d.title,
                language=d.language,
                score=1.0,
                metadata={"index_entry": True},
            )
            for d in documentos
        ]


class MdAgentSelectorPipeline:
    """Devuelve el índice del proveedor inyectado; la selección la hace el AgenticLoop."""

    def __init__(self, index_provider: IndexProvider | None = None) -> None:
        self._index_provider = (
            index_provider if index_provider is not None else DocumentIndexProvider()
        )

    async def run(
        self,
        query: str,
        chatbot_id: str,
        cfg,
        deps,
    ) -> RetrievalResult:
        items = await self._index_provider.build_index(chatbot_id, deps)
        return RetrievalResult(
            items=items,
            debug={
                "pipeline_mode": "MD_AGENT_SELECTOR",
                "index_entries": len(items),
                "index_provider": type(self._index_provider).__name__,
            },
            context_source_language=_dominant_language(items),
        )
