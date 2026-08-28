"""ACT.4 — la vigencia como el corpus la declara: un estado, una causa, marcas por artículo.

**Lectura A, decidida por quien mantiene el corpus el 2026-08-28.** «Vigente» significa que rige
HOY. Una norma es vigente o no lo es; si no lo es, hay una **causa**, y la derogación es sólo una
de ellas: también deja de regir la norma temporal cuyo plazo se ha acabado, la que servía a un
programa que ha finalizado y la dictada por un cargo cuyo mandato ha cesado. Y lo que ocurre
**dentro** de una norma vigente —un artículo suprimido, uno desplazado— se marca en el artículo.

El código sólo excluía `derogat` exacto, así que `no_vigent` se recuperaba **con aviso** sin que
nadie lo hubiera decidido, y `parcialment_derogat` era un estado de norma cuando debe ser `vigent`
más artículos marcados.

Y hay un caso que el modelo no tenía: la norma **sustituida que sigue rigiendo para algunos**
(`PRG-003`, cuya reducción por sexenios mantiene la disposición transitoria primera de `PRG-004`
hasta el curso 2026/2027). Es `vigent` y se recupera: si no entrara en la búsqueda, quien tiene
derecho al régimen transitorio recibiría el de la norma nueva, que para él es el equivocado.
"""
from __future__ import annotations

import uuid

import pytest

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _chunk,
    _documento,
    _emb,
)


async def _buscar(session, cb):
    from server.app.modules.agents_hub.services.retriever import HybridRetriever

    return await HybridRetriever(session).vector_search(_emb(0), cb, top_k=20)


class TestSoloVigenteSeRecupera:

    @pytest.mark.asyncio
    async def test_should_retrieve_only_documents_that_rule_today(self, db_session):
        cb = uuid.uuid4()
        casos = {
            "vigent": "Text vigent",
            "no_vigent": "Text no vigent",
            "futur": "Text futur",
        }
        for estat, texto in casos.items():
            doc = await _documento(db_session, cb, title=estat, estat_vigencia=estat)
            await _chunk(db_session, cb, doc, texto)
        # Sin `estat_vigencia` NO es una norma que haya dejado de regir: es un documento que no
        # tiene ese ciclo de vida —una página rastreada, un PDF que alguien sube—. Excluirlo
        # vaciaría el índice de todo chatbot que no se alimente del corpus curado.
        sin_estado = await _documento(db_session, cb, title="sense", estat_vigencia=None)
        await _chunk(db_session, cb, sin_estado, "Text sense estat")
        # La duda del catálogo original se ADVIERTE, no se oculta.
        dubtos = await _documento(db_session, cb, title="dubtos", estat_vigencia="vigent?")
        await _chunk(db_session, cb, dubtos, "Text dubtos")
        await db_session.commit()

        textos = sorted(r.content for r in await _buscar(db_session, cb))

        assert textos == ["Text dubtos", "Text sense estat", "Text vigent"], (
            "lo que se excluye es lo que AFIRMA que ya no rige, no lo que calla"
        )

    @pytest.mark.asyncio
    async def test_should_still_read_a_non_current_norm_by_explicit_id(self, db_session):
        """Preguntar qué regía el curso pasado es una consulta legítima."""
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )

        cb = uuid.uuid4()
        doc = await _documento(
            db_session, cb, title="Directrius 2025/2026", estat_vigencia="no_vigent",
            markdown_content="# Directrius\n\nArticle 1.",
            doc_metadata={
                "motiu_no_vigencia": "fi-de-vigencia-temporal",
                "substituida_per": ["DIR-009"],
            },
        )
        await db_session.commit()

        leida = await AgenticRetrievalStrategy(db_session).read(doc.id)

        assert "Article 1" in leida["markdown_content"]
        assert leida["estat_vigencia"] == "no_vigent"

    @pytest.mark.asyncio
    async def test_should_not_warn_about_a_norm_that_is_current_and_validated(
        self, db_session
    ):
        """El aviso queda para lo que nadie ha confirmado. Lo no vigente ya no llega al
        modelo, así que no hay nada que advertir sobre ello."""
        from datetime import datetime, timezone

        from server.app.modules.agents_hub.services.retrieval.vigencia import (
            vigencia_no_validada,
        )

        validada = datetime(2026, 7, 31, tzinfo=timezone.utc)
        assert vigencia_no_validada("vigent", validada) is False
        assert vigencia_no_validada("vigent", None) is True
        # «vigent?» del catálogo original: no está confirmado, se advierte.
        assert vigencia_no_validada("vigent?", None) is True


class TestMarcasPorArticulo:

    @pytest.mark.asyncio
    async def test_should_not_retrieve_a_suppressed_or_derogated_article(self, db_session):
        """Un artículo suprimido dentro de una norma vigente no se cita como vigente."""
        cb = uuid.uuid4()
        doc = await _documento(db_session, cb, estat_vigencia="vigent")
        await _chunk(
            db_session, cb, doc, "Article 1 suprimit",
            chunk_metadata={"ancora": "art-1", "estat": "suprimit", "classes": ["suprimit"]},
        )
        await _chunk(
            db_session, cb, doc, "Article 2 derogat",
            chunk_metadata={"ancora": "art-2", "estat": "derogat", "classes": ["derogat"]},
        )
        await _chunk(
            db_session, cb, doc, "Article 3 vigent",
            chunk_metadata={"ancora": "art-3", "estat": None, "classes": []},
        )
        await db_session.commit()

        textos = sorted(r.content for r in await _buscar(db_session, cb))

        assert textos == ["Article 3 vigent"]

    def test_should_know_derogated_as_a_consolidation_state(self):
        from server.app.modules.agents_hub.ingestion.chunker import ESTADOS_CONSOLIDACION

        assert "derogat" in ESTADOS_CONSOLIDACION


class TestVigenciaTransitoria:

    def test_should_put_the_notice_before_the_article(self):
        from server.app.modules.agents_hub.services.retrieval.vigencia import (
            hidratar_avisos_de_vigencia,
        )

        class _Doc:
            doc_metadata = {
                "vigencia_transitoria": {
                    "per": {
                        "id_norma": "PRG-004",
                        "norma": "Programa de suport al PDI (2024)",
                        "ancora": "dt-1",
                        "data": "2024-02-27",
                    },
                    "fins": "2027-07-31",
                    "abast": "Professorat amb un unic sexenni viu el 27-02-2024",
                    "regim": "La reduccio per sexennis del programa de 2021",
                }
            }

        texto = hidratar_avisos_de_vigencia("Reduccion por sexenios: 60 horas.", _Doc(), {})

        assert texto.startswith("AVISO DE VIGENCIA")
        assert "PRG-004" in texto
        assert "2027-07-31" in texto
        assert "sexenni viu" in texto
        assert "Reduccion por sexenios: 60 horas." in texto

    def test_should_only_hydrate_the_articles_that_remain_in_force(self):
        """Con `ancores_vigents`, el aviso acompaña sólo a los apartados que siguen."""
        from server.app.modules.agents_hub.services.retrieval.vigencia import (
            hidratar_avisos_de_vigencia,
        )

        class _Doc:
            doc_metadata = {
                "vigencia_transitoria": {
                    "per": {"id_norma": "PRG-004", "norma": "Programa", "data": "2024-02-27"},
                    "fins": "2027-07-31",
                    "abast": "un colectivo",
                    "ancores_vigents": ["div-3"],
                }
            }

        dentro = hidratar_avisos_de_vigencia("Sexenis.", _Doc(), {"ancora": "div-3"})
        fuera = hidratar_avisos_de_vigencia("Patents.", _Doc(), {"ancora": "div-7"})

        assert dentro.startswith("AVISO DE VIGENCIA")
        assert fuera == "Patents."

    def test_should_hydrate_the_whole_document_when_there_are_no_anchors(self):
        """Sin `ancores_vigents` la declaración vale a nivel de documento: es el caso de
        `PRG-003`, cuyas secciones no van numeradas y por tanto no tienen ancla."""
        from server.app.modules.agents_hub.services.retrieval.vigencia import (
            hidratar_avisos_de_vigencia,
        )

        class _Doc:
            doc_metadata = {
                "vigencia_transitoria": {
                    "per": {"id_norma": "PRG-004", "norma": "Programa", "data": "2024-02-27"},
                    "fins": "2027-07-31",
                    "abast": "un colectivo",
                }
            }

        for ancora in ("div-3", "div-7", None):
            texto = hidratar_avisos_de_vigencia("Text.", _Doc(), {"ancora": ancora})
            assert texto.startswith("AVISO DE VIGENCIA"), ancora


class TestLaCausaEsVocabularioYNoTextoLibre:

    @pytest.mark.asyncio
    async def test_should_reject_a_cause_outside_the_vocabulary(self):
        """`assert_vocabulary` aborta la ingesta ENTERA y enumera todos los códigos malos:
        un `extra` acepta cualquier cosa, y una errata viajaría a la base de datos sin que
        nadie se enterara."""
        from server.app.modules.agents_hub.ingestion.corpus.manifest import (
            CorpusDocumentEntry,
            CorpusValidationError,
            assert_vocabulary,
        )

        class _Vocabulario:
            async def validate(self, axis: str, codis: list[str]) -> list[str]:
                validos = {"motiu_no_vigencia": {"fi-de-mandat", "derogacio-expressa"}}
                return [c for c in codis if c not in validos.get(axis, set())]

        buena = CorpusDocumentEntry(
            relative_path="a.md", source_url="https://www.uji.es/a", language="val",
            estat_vigencia="no_vigent", motiu_no_vigencia="fi-de-mandat",
        )
        mala = CorpusDocumentEntry(
            relative_path="b.md", source_url="https://www.uji.es/b", language="val",
            estat_vigencia="no_vigent", motiu_no_vigencia="fi_de_mandat",
        )

        await assert_vocabulary([buena], _Vocabulario())
        with pytest.raises(CorpusValidationError) as error:
            await assert_vocabulary([buena, mala], _Vocabulario())
        assert "fi_de_mandat" in str(error.value)
        assert "b.md" in str(error.value)

    def test_should_have_the_axis_declared_as_structure(self):
        """Los ejes son estructura (`StrEnum`); los términos, dato (CLAUDE.md §5)."""
        from server.app.modules.agents_hub.services.vocabulary_service import (
            VocabularyAxis,
        )

        assert VocabularyAxis.MOTIU_NO_VIGENCIA.value == "motiu_no_vigencia"
