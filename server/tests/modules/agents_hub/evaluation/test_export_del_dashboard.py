"""HIB.G — lo que el dashboard de anotación exporta tiene que validar contra el contrato.

El dashboard vive en `_local/` porque opera sobre el corpus real, pero **su formato de salida
es un contrato entre dos piezas**: lo que el informador exporta desde el navegador es lo que
después leen `escenario_contrato.py` y `escenario_metricas.py`. Si divergen, el informador
descubre que su trabajo no vale al final de la sesión, que es el peor momento posible.

La instantánea de abajo es literal: se sacó del navegador ejecutando el dashboard de Gerencia
servido por HTTP, anotando dos preguntas por la interfaz —una contestable con fuente exigida y
otra aceptable, y un negativo con su motivo— y capturando el `Blob` que la exportación
construye. No es una réplica escrita a mano de lo que creo que produce.

Lo que este test protege, en concreto:

* El **ancla va separada** de la URL (`anchor: "a118"`, `canonical_url` sin `#`). Es lo que
  permite comparar anclas sin volver a trocear la cadena en cada consumidor.
* La URL es la del corpus y empieza por `http`, que es lo que `ExpectedSource` exige: un título
  escrito a mano no casaría con `canonical_url` y la métrica se perdería en silencio.
* Un negativo sale **sin** `expected_sources` y **con** `refusal_reason`.
* `provenance` viaja como `informador`, no como `equipo_provisional`.
"""
from __future__ import annotations

import pytest

from server.app.modules.agents_hub.evaluation.escenario_contrato import Lote

# Capturado del navegador el 2026-08-27, sobre `dashboard_anotacion_gerencia.html`.
EXPORTADO = {
    "name": "gerencia-econadm-reales-anotacion",
    "description": "Hoja de anotacion de fuente esperada.",
    "uso": "afinado",
    "scenarios": [
        {
            "name": "REAL-02",
            "prompt": "Quin es el limit d'un contracte menor?",
            "expectation_note": None,
            "kind": "tabla_o_dato",
            "language": "ca",
            "domain": "contratacion",
            "provenance": "informador",
            "answerable": True,
            "reference_answer": "El limite del contrato menor de servicios.",
            "expected_sources": {
                "required": [
                    {
                        "canonical_url": "https://www.uji.es/norma/contractacio",
                        "anchor": "a118",
                    }
                ],
                "acceptable": [
                    {
                        "canonical_url": "https://www.uji.es/norma/bases-execucio",
                        "anchor": "div-1",
                    }
                ],
            },
        },
        {
            "name": "REAL-03",
            "prompt": "Quiero comprarme un portátil. ¿Tengo que pedir alguna autorización?",
            "expectation_note": None,
            "kind": "negativo",
            "language": "es",
            "domain": None,
            "provenance": "informador",
            "answerable": False,
            "reference_answer": None,
            "refusal_reason": "dato_no_normativo",
        },
    ],
}


class TestLoQueElDashboardExportaValida:

    def test_should_validate_against_the_scenario_contract(self):
        lote = Lote.model_validate(EXPORTADO)

        assert len(lote.scenarios) == 2
        assert lote.uso == "afinado"

    def test_should_keep_the_anchor_apart_from_the_url(self):
        """Comparar anclas exige tenerlas separadas; si viajan dentro de la URL, cada
        consumidor tiene que volver a trocear la cadena y uno de ellos lo hará distinto."""
        lote = Lote.model_validate(EXPORTADO)
        fuente = lote.scenarios[0].expected_sources.required[0]

        assert fuente.anchor == "a118"
        assert "#" not in fuente.canonical_url

    def test_should_export_a_url_from_the_corpus(self):
        lote = Lote.model_validate(EXPORTADO)

        for escenario in lote.scenarios:
            if not escenario.expected_sources:
                continue
            for fuente in (
                escenario.expected_sources.required
                + escenario.expected_sources.acceptable
            ):
                assert fuente.canonical_url.startswith("http")

    def test_should_export_a_negative_without_sources_and_with_its_reason(self):
        lote = Lote.model_validate(EXPORTADO)
        negativo = lote.scenarios[1]

        assert negativo.answerable is False
        assert str(negativo.refusal_reason) == "dato_no_normativo"
        assert negativo.expected_sources is None

    def test_should_mark_the_provenance_as_the_informer(self):
        """Una fuente anotada por quien afinó el sistema no es evidencia independiente."""
        lote = Lote.model_validate(EXPORTADO)

        assert {str(e.provenance) for e in lote.scenarios} == {"informador"}

    def test_should_be_measurable_without_a_human(self):
        """El objetivo entero: que las tres métricas se calculen sobre esto."""
        from server.app.modules.agents_hub.evaluation.escenario_metricas import resume

        lote = Lote.model_validate(EXPORTADO)
        recuperado = [
            {
                "url": "https://www.uji.es/norma/contractacio#a118",
                "document_id": None,
            }
        ]

        fila = resume(lote.scenarios[0], recuperado, se_rindio=False)
        assert fila["todas_las_fuentes"] is True
        assert fila["ancla_correcta"] is True
        assert fila["rendicion_correcta"] is True

        # Y el negativo: callar es acertar.
        assert resume(lote.scenarios[1], [], se_rindio=True)["rendicion_correcta"] is True


class TestElContratoRechazaLoQueRompeLaMetrica:

    def test_should_reject_a_hand_written_source_title(self):
        roto = {
            **EXPORTADO,
            "scenarios": [
                {
                    **EXPORTADO["scenarios"][0],
                    "expected_sources": {
                        "required": [{"canonical_url": "el reglamento de contratación"}],
                        "acceptable": [],
                    },
                }
            ],
        }

        with pytest.raises(Exception, match="URL"):
            Lote.model_validate(roto)
