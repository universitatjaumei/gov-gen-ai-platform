"""HIB.G — las tres métricas que se calculan solas cuando la fuente esperada es estructurada."""

from server.app.modules.agents_hub.evaluation.escenario_contrato import (
    Escenario,
    ExpectedSource,
    ExpectedSources,
    Kind,
    Provenance,
    RefusalReason,
)
from server.app.modules.agents_hub.evaluation.escenario_metricas import (
    ancla_correcta,
    fuentes_requeridas_recuperadas,
    rendicion_correcta,
    resume,
)

URL = "https://www.uji.es/norma/permanencia"


def _contestable(fuentes: ExpectedSources, **cambios) -> Escenario:
    datos = dict(
        name="ORI-01",
        prompt="Quants credits?",
        kind=Kind.ARTICULO_UNICO,
        language="ca",
        provenance=Provenance.REAL,
        expected_sources=fuentes,
    )
    datos.update(cambios)
    return Escenario(**datos)


def _negativo() -> Escenario:
    return Escenario(
        name="NEG-01",
        prompt="A quina hora obri la biblioteca?",
        kind=Kind.NEGATIVO,
        language="ca",
        provenance=Provenance.SINTETICO,
        answerable=False,
        refusal_reason=RefusalReason.DATO_NO_NORMATIVO,
    )


class TestFuenteEsperadaEnLoRecuperado:

    def test_should_find_the_required_source_by_canonical_url(self):
        e = _contestable(ExpectedSources(required=[ExpectedSource(canonical_url=URL)]))
        assert fuentes_requeridas_recuperadas(e, [{"url": URL + "#art-4"}]) == (1, 1)

    def test_should_ignore_the_trailing_slash_and_the_scheme(self):
        """El portal sirve la misma sección con y sin barra, y por http y https."""
        e = _contestable(ExpectedSources(required=[ExpectedSource(canonical_url=URL + "/")]))
        assert fuentes_requeridas_recuperadas(
            e, [{"url": "http://www.uji.es/norma/permanencia"}]
        ) == (1, 1)

    def test_should_find_the_required_source_by_document_id(self):
        e = _contestable(
            ExpectedSources(required=[ExpectedSource(document_id="abc-123")])
        )
        assert fuentes_requeridas_recuperadas(e, [{"document_id": "abc-123"}]) == (1, 1)

    def test_should_report_a_fraction_when_several_articles_are_required(self):
        e = _contestable(
            ExpectedSources(
                required=[
                    ExpectedSource(canonical_url=URL),
                    ExpectedSource(canonical_url="https://www.uji.es/norma/grado"),
                ]
            ),
            kind=Kind.VARIOS_ARTICULOS,
        )
        assert fuentes_requeridas_recuperadas(e, [{"url": URL}]) == (1, 2)

    def test_should_report_none_for_a_negative_scenario(self):
        assert fuentes_requeridas_recuperadas(_negativo(), [{"url": URL}]) is None


class TestAnclaCorrecta:

    def test_should_confirm_the_anchor_of_the_expected_article(self):
        e = _contestable(
            ExpectedSources(required=[ExpectedSource(canonical_url=URL, anchor="art-4")])
        )
        assert ancla_correcta(e, [{"url": URL + "#art-4"}]) is True

    def test_should_detect_an_anchor_pointing_at_another_article(self):
        e = _contestable(
            ExpectedSources(required=[ExpectedSource(canonical_url=URL, anchor="art-4")])
        )
        assert ancla_correcta(e, [{"url": URL + "#art-7"}]) is False

    def test_should_accept_the_anchor_written_with_or_without_hash(self):
        e = _contestable(
            ExpectedSources(required=[ExpectedSource(canonical_url=URL, anchor="#ART-4")])
        )
        assert ancla_correcta(e, [{"url": URL + "#art-4"}]) is True

    def test_should_not_judge_the_anchor_when_no_anchor_is_expected(self):
        e = _contestable(ExpectedSources(required=[ExpectedSource(canonical_url=URL)]))
        assert ancla_correcta(e, [{"url": URL + "#art-4"}]) is None

    def test_should_not_blame_the_anchor_when_the_document_was_not_retrieved(self):
        """Si el documento no entró, el fallo es de recuperación: contarlo también aquí
        sería contarlo dos veces."""
        e = _contestable(
            ExpectedSources(required=[ExpectedSource(canonical_url=URL, anchor="art-4")])
        )
        assert ancla_correcta(e, [{"url": "https://www.uji.es/otra"}]) is None


class TestRendicionCorrecta:

    def test_should_count_a_refusal_on_a_negative_as_correct(self):
        assert rendicion_correcta(_negativo(), se_rindio=True) is True

    def test_should_count_an_answer_to_a_negative_as_wrong(self):
        assert rendicion_correcta(_negativo(), se_rindio=False) is False

    def test_should_count_a_refusal_on_an_answerable_question_as_wrong(self):
        e = _contestable(ExpectedSources(required=[ExpectedSource(canonical_url=URL)]))
        assert rendicion_correcta(e, se_rindio=True) is False

    def test_should_count_an_answer_to_an_answerable_question_as_correct(self):
        e = _contestable(ExpectedSources(required=[ExpectedSource(canonical_url=URL)]))
        assert rendicion_correcta(e, se_rindio=False) is True


class TestElResumenArrastraLaProcedencia:

    def test_should_keep_the_provenance_next_to_the_result(self):
        e = _contestable(
            ExpectedSources(required=[ExpectedSource(canonical_url=URL, anchor="art-4")]),
            provenance=Provenance.EQUIPO_PROVISIONAL,
        )
        fila = resume(e, [{"url": URL + "#art-4"}], se_rindio=False)
        assert fila["provenance"] == "equipo_provisional"
        assert fila["todas_las_fuentes"] is True
        assert fila["ancla_correcta"] is True
        assert fila["rendicion_correcta"] is True

    def test_should_leave_source_metrics_null_on_a_negative(self):
        fila = resume(_negativo(), [], se_rindio=True)
        assert fila["fuentes_exigidas"] is None
        assert fila["todas_las_fuentes"] is None
        assert fila["rendicion_correcta"] is True
