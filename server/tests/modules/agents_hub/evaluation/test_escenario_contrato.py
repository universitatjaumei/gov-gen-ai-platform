"""HIB.G — el contrato del escenario de evaluación.

Lo que estos tests protegen no es un formato: es la posibilidad de medir sin una persona
delante. Un escenario contestable sin fuente esperada estructurada convierte cualquier
ablación en una nueva petición de trabajo a los informadores, y por eso las ablaciones no se
hacían.
"""
import pytest
from pydantic import ValidationError

from server.app.modules.agents_hub.evaluation.escenario_contrato import (
    Escenario,
    ExpectedSource,
    ExpectedSources,
    Kind,
    Lote,
    Provenance,
    RefusalReason,
)


def _fuente(anchor: str | None = "art-4") -> ExpectedSources:
    return ExpectedSources(
        required=[
            ExpectedSource(
                canonical_url="https://www.uji.es/norma/permanencia",
                anchor=anchor,
            )
        ]
    )


def _escenario(**cambios) -> dict:
    base = dict(
        name="ORI-01",
        prompt="Quants credits he de superar?",
        kind=Kind.ARTICULO_UNICO,
        language="ca",
        provenance=Provenance.REAL,
        expected_sources=_fuente(),
    )
    base.update(cambios)
    return base


class TestUnEscenarioContestableExigeFuente:

    def test_should_accept_a_scenario_with_a_required_source(self):
        e = Escenario(**_escenario())
        assert e.expected_sources.required[0].anchor == "art-4"

    def test_should_reject_a_scenario_without_expected_sources_when_answerable(self):
        with pytest.raises(ValidationError, match="fuente esperada"):
            Escenario(**_escenario(expected_sources=None))

    def test_should_reject_an_empty_required_set_when_answerable(self):
        with pytest.raises(ValidationError, match="fuente esperada"):
            Escenario(**_escenario(expected_sources=ExpectedSources()))

    def test_should_reject_a_refusal_reason_on_an_answerable_scenario(self):
        with pytest.raises(ValidationError, match="`refusal_reason` sólo tiene sentido"):
            Escenario(**_escenario(refusal_reason=RefusalReason.FUERA_DE_ALCANCE))


class TestUnNegativoExigeSuMotivo:

    def test_should_reject_an_unanswerable_scenario_without_refusal_reason(self):
        with pytest.raises(ValidationError, match="necesita `refusal_reason`"):
            Escenario(
                **_escenario(
                    answerable=False,
                    expected_sources=None,
                    kind=Kind.NEGATIVO,
                    provenance=Provenance.SINTETICO,
                )
            )

    def test_should_accept_an_unanswerable_scenario_with_its_reason(self):
        e = Escenario(
            **_escenario(
                answerable=False,
                expected_sources=None,
                kind=Kind.NEGATIVO,
                provenance=Provenance.SINTETICO,
                refusal_reason=RefusalReason.PREMISA_FALSA,
            )
        )
        assert e.refusal_reason is RefusalReason.PREMISA_FALSA

    def test_should_reject_an_unanswerable_scenario_that_demands_sources(self):
        with pytest.raises(ValidationError, match="no puede exigir fuentes"):
            Escenario(
                **_escenario(
                    answerable=False,
                    kind=Kind.NEGATIVO,
                    provenance=Provenance.SINTETICO,
                    refusal_reason=RefusalReason.FUERA_DE_ALCANCE,
                )
            )


class TestLosEjesDelAnalisisSonObligatorios:

    def test_should_require_language_kind_and_provenance(self):
        for falta in ("language", "kind", "provenance"):
            datos = _escenario()
            del datos[falta]
            with pytest.raises(ValidationError):
                Escenario(**datos)

    def test_should_reject_a_language_outside_ca_and_es(self):
        with pytest.raises(ValidationError, match="'ca' o 'es'"):
            Escenario(**_escenario(language="en"))

    def test_should_require_history_on_a_follow_up_scenario(self):
        with pytest.raises(ValidationError, match="necesita `history`"):
            Escenario(**_escenario(kind=Kind.SEGUIMIENTO))

    def test_should_require_a_document_identifier_on_a_source(self):
        with pytest.raises(ValidationError, match="`document_id` o `canonical_url`"):
            ExpectedSource(anchor="art-4")


class TestElLoteSeSabeDescribir:

    def test_should_report_its_composition_by_every_axis(self):
        lote = Lote(
            name="prueba",
            scenarios=[
                Escenario(**_escenario(name="A", language="ca")),
                Escenario(**_escenario(name="B", language="es", kind=Kind.TABLA_O_DATO)),
                Escenario(
                    **_escenario(
                        name="C",
                        language="es",
                        answerable=False,
                        expected_sources=None,
                        kind=Kind.NEGATIVO,
                        provenance=Provenance.SINTETICO,
                        refusal_reason=RefusalReason.FUERA_DE_ALCANCE,
                    )
                ),
            ],
        )
        c = lote.composicion()
        assert c["total"] == 3
        assert c["language"] == {"ca": 1, "es": 2}
        assert c["answerable"] == {"False": 1, "True": 2}
        assert c["con_fuente_requerida"] == 2
        assert c["con_ancla"] == 2

    def test_should_default_to_declaring_the_lot_is_for_tuning(self):
        """El lote afina; el piloto informa. Si nadie lo declara, se confunden."""
        lote = Lote(name="prueba", scenarios=[Escenario(**_escenario())])
        assert lote.uso == "afinado"
