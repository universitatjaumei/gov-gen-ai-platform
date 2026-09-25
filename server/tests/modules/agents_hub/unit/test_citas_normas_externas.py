"""Una norma externa se cita en su diario oficial, no en nuestro sitio.

El sitio de publicación tiene página para las normas **propias** de la Universidad. La Ley
de Contratos, la LPAC y las de la Generalitat no: viven en el BOE y en el DOGV. Al citarlas
como si tuvieran página, el enlace daba **404**.

Visto al probar el asistente: la cita de la Ley 9/2017 apuntaba a
`…/html/es_BOE_A_2017_12902_….html#art-118`, que no existe.

La señal es explícita en el corpus —`tipus_document: norma_externa`— y no hay que deducirla.
"""
from __future__ import annotations

from types import SimpleNamespace

from server.app.modules.agents_hub.services.retrieval.citations import (
    BASE_DEL_SITIO,
    url_de_cita,
)

SITIO = "https://normativa.uji.es"
BOE_ACT = "https://www.boe.es/buscar/act.php?id=BOE-A-2017-12902"
BOE_ELI = "https://www.boe.es/eli/es/l/2017/11/08/9"


def _externa(**extra):
    metadatos = {
        "tipus_document": "norma_externa",
        "url_oficial": BOE_ACT,
        "url_eli": BOE_ELI,
        "relative_path": "es_BOE_A_2017_12902_ley_9_2017.md",
    }
    metadatos.update(extra)
    return SimpleNamespace(canonical_url=BOE_ACT, doc_metadata=metadatos)


def _propia():
    return SimpleNamespace(
        canonical_url="https://www.uji.es/reglament.pdf",
        doc_metadata={
            "tipus_document": "reglament",
            "relative_path": "val_Reglament_Sindicatura.md",
        },
    )


class TestNormaExterna:

    def test_should_cite_the_official_gazette_and_not_our_site(self, monkeypatch):
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        url = url_de_cita(_externa(), {"ancora": "art-118"})

        assert SITIO not in url, "cito nuestro sitio una norma que no tiene pagina alli"
        assert url.startswith(BOE_ACT)

    def test_should_not_compose_an_anchor_for_the_boe_either(self, monkeypatch):
        """Issue #152. El ancla del BOE **no se puede calcular** desde el número de artículo.

        Este test decía lo contrario —que `art-118` compone `#a118`— y esa regla acertaba en los
        nueve primeros artículos de cada ley y fallaba en todos los demás. **785 anclas rotas**
        salieron del barrido del corpus, todas del BOE y ninguna de nuestro sitio.

        **Lo medido el 2026-09-24**, que es lo que tumba la regla: el BOE usa **dos esquemas**
        según la norma, y sólo coinciden en los artículos de un dígito.

            Ley Orgánica 6/2001   #a110  → Artículo 110     (el ancla ES el artículo)
            Ley 9/2017 Contratos  #a1-10 → Artículo 18      (el ancla es un identificador de
                                                             bloque, y el propio BOE lo marca
                                                             como «[Bloque 26: #a1-10]»)

        De la 9/2017 salieron 338 anclas rotas: exactamente todos sus artículos del 10 en
        adelante. Y en la 6/2001, `#a114` no existe porque ese artículo está derogado — así que
        ni siquiera el esquema bueno es seguro.

        No hay otra fórmula que arreglarlo: para saber qué ancla lleva al artículo 18 hay que
        **leer la página**. Mientras no se lea, se cita la norma sin fragmento — que es la regla
        que este módulo ya tenía escrita y que aquí se aplica de verdad: «un ancla inventada es
        peor que ninguna, lleva a un punto que no existe sin que se note».

        Resolverlas en la ingesta es viable y tiene su propia issue.
        """
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        for ancora in ("art-118", "art-1", "art-9", "art-18"):
            url = url_de_cita(_externa(), {"ancora": ancora})
            assert url == BOE_ACT, (
                f"se ha compuesto un ancla para `{ancora}`: {url}. El ancla del BOE no se deduce "
                f"del número de artículo."
            )

    def test_should_not_invent_an_anchor_the_gazette_does_not_use(self, monkeypatch):
        """Sólo se traduce `art-N`. Para disposiciones el BOE usa otra forma y no se adivina:
        mejor el documento sin ancla que un enlace a un sitio que no existe."""
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        url = url_de_cita(_externa(), {"ancora": "da-2"})

        assert url == BOE_ACT

    def test_should_fall_back_to_the_eli_when_there_is_no_official_url(self, monkeypatch):
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        url = url_de_cita(_externa(url_oficial=None), {"ancora": "art-118"})

        assert url.startswith(BOE_ELI)

    def test_should_not_touch_anchors_outside_the_boe(self, monkeypatch):
        """El DOGV no usa el mismo esquema de anclas, así que se cita el documento."""
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)
        dogv = "https://dogv.gva.es/datos/2020/01/01/pdf/2020_1.pdf"

        url = url_de_cita(_externa(url_oficial=dogv, url_eli=None), {"ancora": "art-3"})

        assert url == dogv

    def test_should_keep_citing_our_site_for_our_own_regulations(self, monkeypatch):
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        url = url_de_cita(_propia(), {"ancora": "art-9"})

        assert url == f"{SITIO}/html/val_Reglament_Sindicatura.html#art-9"
