"""PIL.2 — borrar un chatbot se lleva su corpus.

`hub_documents.chatbot_id` **no tiene FK**: se cayó al separar `HubConfigBase` de
`HubOperationalBase`, y la frontera edge-cloud pide que no vuelva. Consecuencia hasta aquí:
`DELETE /hub/chatbots/{id}` borraba la fila de configuración y dejaba documentos y
embeddings sin dueño en la base. Se descubrió limpiando los chatbots de prueba antes del
piloto.

Contra BD real y no con la sesión mockeada, que es la lección de los hallazgos del
2026-08-12/14: un `AsyncMock` acepta cualquier `delete` y no sabe nada de cascadas, así que
un test así habría pasado en verde con el bug dentro.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _chunk,
    _documento,
)


async def _interaccion(session, chatbot_id: uuid.UUID):
    from server.app.modules.agents_hub.database.operational_models import HubInteraction

    fila = HubInteraction(
        chatbot_id=chatbot_id,
        user_id="fabra@uji.es",
        user_message="com justifique una dieta?",
        assistant_message="Segons la circular...",
    )
    session.add(fila)
    await session.flush()
    return fila


async def _cuenta(session, modelo, chatbot_id: uuid.UUID) -> int:
    fila = await session.execute(
        select(func.count(modelo.id)).where(modelo.chatbot_id == chatbot_id)
    )
    return int(fila.scalar_one() or 0)


class TestPurgaDelCorpus:

    @pytest.mark.asyncio
    async def test_should_delete_documents_and_chunks_when_chatbot_is_deleted(
        self, db_session
    ):
        from server.app.modules.agents_hub.database.operational_models import (
            HubDocument,
            HubDocumentChunk,
        )
        from server.app.modules.agents_hub.services.corpus_purge import (
            purgar_corpus_del_chatbot,
        )

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb)
        for i in range(3):
            await _chunk(db_session, cb, doc, f"Article {i}")
        await db_session.flush()

        assert await _cuenta(db_session, HubDocument, cb) == 1
        assert await _cuenta(db_session, HubDocumentChunk, cb) == 3

        await purgar_corpus_del_chatbot(db_session, cb)

        assert await _cuenta(db_session, HubDocument, cb) == 0
        assert await _cuenta(db_session, HubDocumentChunk, cb) == 0

    @pytest.mark.asyncio
    async def test_should_not_delete_documents_of_other_chatbots(self, db_session):
        from server.app.modules.agents_hub.database.operational_models import (
            HubDocument,
            HubDocumentChunk,
        )
        from server.app.modules.agents_hub.services.corpus_purge import (
            purgar_corpus_del_chatbot,
        )

        borrado, superviviente = uuid.uuid4(), uuid.uuid4()
        doc_a = await _documento(db_session, borrado)
        doc_b = await _documento(db_session, superviviente)
        await _chunk(db_session, borrado, doc_a, "Article del borrat")
        await _chunk(db_session, superviviente, doc_b, "Article del que es queda")
        await db_session.flush()

        await purgar_corpus_del_chatbot(db_session, borrado)

        assert await _cuenta(db_session, HubDocument, superviviente) == 1
        assert await _cuenta(db_session, HubDocumentChunk, superviviente) == 1

    @pytest.mark.asyncio
    async def test_should_keep_interactions_after_chatbot_deletion(self, db_session):
        """Lo que el asistente contestó no se reescribe porque se borre el asistente.

        Es registro, no corpus, y con REV.1 encima es material de revisión.
        """
        from server.app.modules.agents_hub.database.operational_models import (
            HubInteraction,
        )
        from server.app.modules.agents_hub.services.corpus_purge import (
            purgar_corpus_del_chatbot,
        )

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb)
        await _chunk(db_session, cb, doc, "Article")
        await _interaccion(db_session, cb)
        await db_session.flush()

        await purgar_corpus_del_chatbot(db_session, cb)

        assert await _cuenta(db_session, HubInteraction, cb) == 1

    @pytest.mark.asyncio
    async def test_should_report_what_it_removed(self, db_session):
        """El recuento es lo que permite decir en voz alta qué se llevó por delante."""
        from server.app.modules.agents_hub.services.corpus_purge import (
            purgar_corpus_del_chatbot,
        )

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb)
        for i in range(4):
            await _chunk(db_session, cb, doc, f"Article {i}")
        await db_session.flush()

        retirados = await purgar_corpus_del_chatbot(db_session, cb)

        assert retirados.documentos == 1
        assert retirados.fragmentos == 4

    @pytest.mark.asyncio
    async def test_should_be_a_noop_for_a_chatbot_without_corpus(self, db_session):
        from server.app.modules.agents_hub.services.corpus_purge import (
            purgar_corpus_del_chatbot,
        )

        retirados = await purgar_corpus_del_chatbot(db_session, uuid.uuid4())

        assert (retirados.documentos, retirados.fragmentos) == (0, 0)

    @pytest.mark.asyncio
    async def test_should_leave_no_orphan_documents_in_the_database(self, db_session):
        """La comprobación que destapó el fallo, escrita como test.

        Es la misma consulta del criterio de cierre de PIL.5: ningún documento cuyo chatbot
        ya no exista. Aquí se ejerce sobre la purga; allí, sobre la base entera.
        """
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        from server.app.modules.agents_hub.services.corpus_purge import (
            purgar_corpus_del_chatbot,
        )

        cb = uuid.uuid4()
        doc = await _documento(db_session, cb)
        await _chunk(db_session, cb, doc, "Article")
        await db_session.flush()

        await purgar_corpus_del_chatbot(db_session, cb)

        quedan = await db_session.execute(
            select(func.count(HubDocument.id)).where(HubDocument.chatbot_id == cb)
        )
        assert int(quedan.scalar_one() or 0) == 0
