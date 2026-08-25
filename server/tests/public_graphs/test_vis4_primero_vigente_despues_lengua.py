"""VIS.4 — Primero vigente, después lengua.

`PreferLanguagePolicy` resolvía bien lo que se le pidió —si no hay evidencia en la lengua de la
pregunta, busca otra vez y acepta la otra lengua— pero **no distinguía dos cosas que no son la
misma**: que la única versión disponible esté en otra lengua, y que esté en otro curso académico.

Medido el 2026-08-24 en el corpus real: las directrices académicas de **2026/2027 sólo existen en
castellano** y las de **2025/2026 sólo en valencià**, las cuatro marcadas vigentes y validadas.
Con la política anterior, «usa la otra lengua» y «usa una versión anterior» eran la misma acción,
y para quien pregunta son cosas muy distintas: una le da el texto que rige escrito en otra lengua,
y la otra le da el texto de su lengua que **ya no rige**.

**Decisión del usuario (2026-08-24)**: entre dos versiones de la misma norma manda **primero la
vigente y después la lengua**. Si la vigente sólo existe en la otra lengua, se cita la vigente y se
advierte de la lengua; nunca al revés — porque citar lo derogado en la lengua correcta es un error
de fondo, y citar lo vigente en otra lengua es una incomodidad.

**Nota sobre el alcance real.** Con el corpus de hoy esta regla **no cambia ningún resultado**,
porque cada norma tiene una sola versión: el emparejamiento bilingüe está incompleto (47
traducciones sin declarar de qué norma son versión). Empieza a decidir en cuanto entren las que
faltan, y por eso conviene tenerla escrita **antes** y no después — cuando el corpus la necesite,
nadie estará mirando esta parte del código.

La señal de vigencia es la que VIS.3 ya pone en cada evidencia:
`metadata["vigencia_no_validada"]`, que es `True` cuando el documento **no** puede presentarse
como vigente sin advertirlo. No se inventa una jerarquía nueva.
"""
from __future__ import annotations

from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
    PreferLanguagePolicy,
    StrictLanguagePolicy,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
)
from server.app.modules.agents_hub.services.retrieval.vigencia import CLAVE_METADATO


def _evidencia(
    ident: str, *, lengua: str, vigente: bool, score: float = 0.5
) -> EvidenceItem:
    return EvidenceItem(
        source_id=ident,
        content=f"contenido de {ident}",
        language=lengua,
        score=score,
        # `vigencia_no_validada` es la señal de VIS.3: True = no se puede presentar como vigente.
        metadata={CLAVE_METADATO: not vigente},
    )


class TestPrimeroVigente:

    def test_should_prefer_the_current_version_even_if_it_is_in_the_other_language(self):
        """El caso de las directrices: la vigente en castellano y la anterior en valencià."""
        vigente_otra_lengua = _evidencia("2026-27-es", lengua="es", vigente=True)
        anterior_mi_lengua = _evidencia("2025-26-ca", lengua="ca", vigente=False, score=0.9)

        ordenados = PreferLanguagePolicy().filter_items(
            "ca", [anterior_mi_lengua, vigente_otra_lengua]
        )

        assert ordenados[0].source_id == "2026-27-es", (
            "gana la versión anterior por estar en la lengua de la pregunta: citar lo que ya no "
            "rige en la lengua correcta es un error de fondo, no una comodidad"
        )

    def test_should_prefer_the_query_language_between_two_current_versions(self):
        """La preferencia de lengua no desaparece: opera **dentro** de la misma vigencia."""
        vigente_es = _evidencia("norma-es", lengua="es", vigente=True, score=0.9)
        vigente_ca = _evidencia("norma-ca", lengua="ca", vigente=True, score=0.5)

        ordenados = PreferLanguagePolicy().filter_items("ca", [vigente_es, vigente_ca])

        assert ordenados[0].source_id == "norma-ca"

    def test_should_keep_the_score_order_inside_the_same_bucket(self):
        """Dentro del mismo grupo manda la relevancia, que es lo que ya decidía antes. La regla
        añade un criterio por encima; no sustituye al que había."""
        mejor = _evidencia("a", lengua="ca", vigente=True, score=0.9)
        peor = _evidencia("b", lengua="ca", vigente=True, score=0.2)

        ordenados = PreferLanguagePolicy().filter_items("ca", [mejor, peor])

        assert [i.source_id for i in ordenados] == ["a", "b"]


class TestLoQueNoCambia:

    def test_should_not_change_behaviour_when_there_is_a_single_version(self):
        """El caso de hoy: una sola versión por norma. La regla no puede alterar nada aquí, y es
        lo que permite meterla antes de que el corpus la necesite."""
        unica = _evidencia("solo-una", lengua="ca", vigente=True)

        assert PreferLanguagePolicy().filter_items("ca", [unica]) == [unica]
        assert PreferLanguagePolicy().filter_items("es", [unica]) == [unica]

    def test_should_not_lose_any_item(self):
        """`prefer` **ordena**, no filtra: quitar evidencia sería cambiar de política."""
        items = [
            _evidencia("a", lengua="es", vigente=False),
            _evidencia("b", lengua="ca", vigente=True),
            _evidencia("c", lengua="es", vigente=True),
        ]

        ordenados = PreferLanguagePolicy().filter_items("ca", items)

        assert sorted(i.source_id for i in ordenados) == ["a", "b", "c"]

    def test_should_pass_everything_through_without_query_language(self):
        items = [_evidencia("a", lengua="es", vigente=False), _evidencia("b", lengua="ca", vigente=True)]

        assert PreferLanguagePolicy().filter_items(None, items) == items

    def test_should_not_touch_the_strict_policy(self):
        """`strict` filtra a la lengua del usuario por definición, así que allí la vigencia no
        compite con nada: si sólo hay versión vigente en la otra lengua, `strict` ya decidió que
        no la quiere. Cambiarlo sería cambiar el significado del modo."""
        vigente_otra_lengua = _evidencia("es", lengua="es", vigente=True)
        anterior_mi_lengua = _evidencia("ca", lengua="ca", vigente=False)

        filtrados = StrictLanguagePolicy().filter_items(
            "ca", [vigente_otra_lengua, anterior_mi_lengua]
        )

        assert [i.source_id for i in filtrados] == ["ca"]


class TestElAvisoDeLengua:

    def test_should_warn_about_language_when_only_the_other_language_is_current(self):
        """Si se cita la vigente en otra lengua, hay que decirlo: el enlace lleva a un documento
        que quien pregunta no escribió en su lengua."""
        politica = PreferLanguagePolicy()

        assert politica.should_warn_translation("ca", "es") is True
        assert politica.should_warn_translation("ca", "ca") is False
