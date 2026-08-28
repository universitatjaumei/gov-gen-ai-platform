"""ACT.3 — una sola versión por norma: la de la lengua de quien pregunta.

**La regla, dicha por quien mantiene el corpus (2026-08-28):** cuando una norma tiene las dos
versiones aprobadas, las dos son OFICIALES —a l'UJI la normativa s'aprova en valencià salvo algún
reglamento del Consell Social, y el Reglament de Política Lingüística manda traducir algunas; la
traducción la publica Secretaría General o el órgano que dictó la resolución—. Se busca, se envía
al modelo y se cita **sólo la de la lengua de la pregunta**. Si la norma existe en una sola
lengua, se usa esa y se avisa. **Nunca las dos.**

Lo que había antes hacía dos cosas mal a la vez:

- `canonica` era un **filtro duro**: la versión castellana de una norma bilingüe no se recuperaba
  jamás, así que preguntar en castellano devolvía el texto valenciano. Con el corpus del 27-08
  eso pasaba de 33 normas a 57.
- Para las parejas **no declaradas**, las dos versiones competían en el top-k y **las dos se
  citaban**, que es el defecto que se observó en producción.

Por eso `canonica` se retira: no hay jerarquía entre dos versiones oficiales y el campo invitaba
a leer lo contrario. Lo que la regla necesita es el **emparejamiento**, que ya está en
`versio_idiomatica_de`.

La condición va en el `WHERE` y no después del top-k: una versión descartada en Python ya ha
consumido una plaza (regla 1 de `metadata_filter.py`).
"""
from __future__ import annotations

import uuid

import pytest

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _chunk,
    _documento,
    _emb,
)


async def _pareja(session, cb, *, titulo_val="Reglament", titulo_es="Reglamento"):
    """La misma norma en las dos lenguas, emparejadas como lo hace el corpus."""
    val = await _documento(session, cb, title=titulo_val, language="val")
    es = await _documento(
        session, cb, title=titulo_es, language="es", versio_idiomatica_de=val.id
    )
    await _chunk(session, cb, val, "Article 1 del reglament")
    await _chunk(session, cb, es, "Articulo 1 del reglamento")
    return val, es


async def _buscar(session, cb, language):
    from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
        MetadataFilter,
    )
    from server.app.modules.agents_hub.services.retriever import HybridRetriever

    return await HybridRetriever(session).vector_search(
        _emb(0), cb, top_k=10, metadata_filter=MetadataFilter(query_language=language)
    )


class TestLaVersionDeLaLenguaDeLaPregunta:

    @pytest.mark.asyncio
    async def test_should_return_the_spanish_version_when_asked_in_spanish(self, db_session):
        """Lo que antes era imposible: `canonica=false` la excluía siempre."""
        cb = uuid.uuid4()
        await _pareja(db_session, cb)
        await db_session.commit()

        textos = sorted(r.content for r in await _buscar(db_session, cb, "es"))

        assert textos == ["Articulo 1 del reglamento"]

    @pytest.mark.asyncio
    async def test_should_return_the_valencian_version_when_asked_in_valencian(
        self, db_session
    ):
        cb = uuid.uuid4()
        await _pareja(db_session, cb)
        await db_session.commit()

        textos = sorted(r.content for r in await _buscar(db_session, cb, "val"))

        assert textos == ["Article 1 del reglament"]

    @pytest.mark.asyncio
    async def test_should_never_return_both_versions_of_the_same_norm(self, db_session):
        """El defecto observado en producción: las dos versiones citadas como dos normas."""
        cb = uuid.uuid4()
        await _pareja(db_session, cb)
        await db_session.commit()

        for lengua in ("es", "val"):
            resultados = await _buscar(db_session, cb, lengua)
            assert len(resultados) == 1, (
                f"con la pregunta en «{lengua}» han vuelto {len(resultados)} versiones de la "
                "misma norma"
            )

    @pytest.mark.asyncio
    async def test_should_fall_back_to_the_only_version_there_is(self, db_session):
        """Si la norma no está traducida se usa la que existe, y el aviso lo dice."""
        cb = uuid.uuid4()
        solo_val = await _documento(db_session, cb, title="Només en valencià", language="val")
        await _chunk(db_session, cb, solo_val, "Norma sense traduir")
        solo_es = await _documento(db_session, cb, title="Solo en castellano", language="es")
        await _chunk(db_session, cb, solo_es, "Norma sin traducir")
        await db_session.commit()

        en_castellano = sorted(r.content for r in await _buscar(db_session, cb, "es"))
        en_valenciano = sorted(r.content for r in await _buscar(db_session, cb, "val"))

        assert en_castellano == ["Norma sense traduir", "Norma sin traducir"]
        assert en_valenciano == ["Norma sense traduir", "Norma sin traducir"]

    @pytest.mark.asyncio
    async def test_should_work_with_the_pairing_declared_the_other_way_round(
        self, db_session
    ):
        """El corpus declara `versio_idiomatica_de` en un solo lado, y su dirección es un
        detalle de escritura: no dice cuál vale más. La regla tiene que valer igual."""
        cb = uuid.uuid4()
        es = await _documento(db_session, cb, title="Reglamento", language="es")
        val = await _documento(
            db_session, cb, title="Reglament", language="val", versio_idiomatica_de=es.id
        )
        await _chunk(db_session, cb, es, "Articulo unico")
        await _chunk(db_session, cb, val, "Article unic")
        await db_session.commit()

        assert [r.content for r in await _buscar(db_session, cb, "es")] == ["Articulo unico"]
        assert [r.content for r in await _buscar(db_session, cb, "val")] == ["Article unic"]

    @pytest.mark.asyncio
    async def test_should_not_filter_by_language_when_none_is_given(self, db_session):
        """Sin lengua no hay regla que aplicar: es lo que significa `language_mode: none`."""
        cb = uuid.uuid4()
        await _pareja(db_session, cb)
        await db_session.commit()

        assert len(await _buscar(db_session, cb, None)) == 2


class TestCanonicaSeRetira:

    def test_should_not_have_a_canonica_flag_anymore(self):
        """`canonica` era una jerarquía que no existe entre dos versiones oficiales."""
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        from server.app.modules.agents_hub.ingestion.corpus.manifest import (
            CorpusDocumentEntry,
        )
        from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
            MetadataFilter,
        )

        assert not hasattr(HubDocument, "canonica")
        assert "canonica" not in CorpusDocumentEntry.model_fields
        assert not hasattr(MetadataFilter(), "include_non_canonical")

    def test_should_not_break_a_corpus_that_still_declares_it(self):
        """El `.md` del corpus todavía lo trae, y un paquete válido no puede dejar de serlo por
        un campo que aquí ya no se usa: cae a `extra`, como cualquier clave no enumerada."""
        from server.app.modules.agents_hub.ingestion.corpus.manifest import (
            entry_from_frontmatter,
        )

        entrada = entry_from_frontmatter(
            {"id_publicacio": "REG-001-es", "language": "es", "canonica": False,
             "versio_idiomatica_de": "REG-001"},
            relative_path="REG-001-es.md",
            source_url="https://www.uji.es/REG-001-es",
        )
        assert entrada.versio_idiomatica_de == "REG-001"
        assert entrada.extra.get("canonica") is False
