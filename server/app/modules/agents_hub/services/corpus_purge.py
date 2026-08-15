"""Retirada del corpus de un chatbot (PIL.2). Deploy: edge.

`hub_documents.chatbot_id` **no tiene clave ajena**, y no es un descuido: la cayó el split
entre `HubConfigBase` (configuración, se sincroniza cloud→edge) y `HubOperationalBase` (datos
del cliente, viven sólo en el edge), y la frontera de CLAUDE.md pide que no vuelva. Postgres,
por tanto, no puede cascadear de un chatbot a su corpus.

Lo que sí cascadea es `hub_document_chunks → hub_documents` (`fk_chunk_document_id`, ING.0.2),
así que basta con borrar los documentos: los fragmentos —y con ellos los embeddings, que es
lo que ocupa— se van detrás.

**Qué NO se borra: las interacciones.** Son el registro de lo que el asistente contestó, no
su corpus, y desde REV.1 son además material de revisión. Borrar un chatbot no reescribe la
historia de lo que dijo.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import (
    HubDocument,
    HubDocumentChunk,
)


@dataclass(frozen=True)
class CorpusRetirado:
    """Lo que se llevó por delante, para poder decirlo en voz alta."""

    documentos: int
    fragmentos: int


async def purgar_corpus_del_chatbot(
    session: AsyncSession, chatbot_id: uuid.UUID
) -> CorpusRetirado:
    """Retira documentos y fragmentos del chatbot. **No hace commit.**

    El commit es de quien llama, y eso es deliberado: la purga y el borrado del chatbot
    tienen que ser la misma transacción. Media limpieza —el chatbot borrado y su corpus
    dentro, o al revés— es peor que ninguna, porque deja de haber forma de encontrar lo que
    quedó suelto.
    """
    documentos = int(
        (
            await session.execute(
                select(func.count(HubDocument.id)).where(
                    HubDocument.chatbot_id == chatbot_id
                )
            )
        ).scalar_one()
        or 0
    )
    fragmentos = int(
        (
            await session.execute(
                select(func.count(HubDocumentChunk.id)).where(
                    HubDocumentChunk.chatbot_id == chatbot_id
                )
            )
        ).scalar_one()
        or 0
    )

    # Los fragmentos se borran explícitamente ADEMÁS de por la cascada: los adjuntos
    # temporales de una consulta (`is_temporary`) cuelgan del chatbot sin documento, así que
    # la cascada por sí sola los dejaría atrás.
    await session.execute(
        delete(HubDocumentChunk).where(HubDocumentChunk.chatbot_id == chatbot_id)
    )
    await session.execute(delete(HubDocument).where(HubDocument.chatbot_id == chatbot_id))

    return CorpusRetirado(documentos=documentos, fragmentos=fragmentos)
