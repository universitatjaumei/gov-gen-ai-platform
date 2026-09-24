"""PUB.3 — la cita apunta al sitio publicado, que sí tiene anclas.

El PDF oficial se abre por la primera página: quien pregunta recibe un enlace a un
documento de cuarenta páginas y tiene que buscar el artículo a mano. El sitio de
publicación del corpus **sí** tiene anclas —`html/<slug>.html#art-9` abre el artículo— y es
lo que convierte el esfuerzo de generar 6.571 anclas en algo que se nota al usarlo.

`CORPUS_SITE_BASE_URL` vacía significa desactivado: sin sitio publicado se cita el PDF,
como hasta ahora. No hay nada que decidir hasta que el sitio exista.
"""
from __future__ import annotations

from types import SimpleNamespace

from server.app.modules.agents_hub.services.retrieval.citations import (
    BASE_DEL_SITIO,
    url_de_cita,
)

SITIO = "https://normativa.uji.es"


def _documento(relative_path: str | None = "REG-048_sindicatura.md", url: str = "https://uji.es/x.pdf"):
    metadatos = {"relative_path": relative_path} if relative_path else {}
    return SimpleNamespace(canonical_url=url, doc_metadata=metadatos)


class TestCitaAlSitioPublicado:

    def test_should_cite_the_pdf_when_no_site_is_configured(self, monkeypatch):
        """Sin sitio publicado se cita el PDF, y **sin ancla** (issue #15).

        Hasta el 2026-09-24 esta rama devolvía `…x.pdf#art-9`. El razonamiento de por qué eso
        era fabricar un puntero está en
        `test_should_not_compose_an_anchor_onto_a_target_that_cannot_serve_it`.
        """
        monkeypatch.delenv(BASE_DEL_SITIO, raising=False)

        url = url_de_cita(_documento(), {"ancora": "art-9"})

        assert url == "https://uji.es/x.pdf"

    def test_should_cite_the_published_page_with_its_anchor(self, monkeypatch):
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        url = url_de_cita(_documento(), {"ancora": "art-9"})

        assert url == f"{SITIO}/html/REG-048_sindicatura.html#art-9"

    def test_should_tolerate_a_trailing_slash_in_the_base(self, monkeypatch):
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO + "/")

        url = url_de_cita(_documento(), {"ancora": "art-9"})

        assert url == f"{SITIO}/html/REG-048_sindicatura.html#art-9"

    def test_should_cite_the_page_without_anchor_when_the_chunk_has_none(self, monkeypatch):
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        url = url_de_cita(_documento(), {})

        assert url == f"{SITIO}/html/REG-048_sindicatura.html"

    def test_should_fall_back_to_the_pdf_when_the_document_has_no_slug(self, monkeypatch):
        """Un documento anterior a PUB.3 no trae `relative_path`.

        No se inventa un slug: se cita el PDF, que es peor pero es cierto.
        """
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        url = url_de_cita(_documento(relative_path=None), {"ancora": "art-9"})

        assert url == "https://uji.es/x.pdf"

    def test_should_not_compose_an_anchor_onto_a_target_that_cannot_serve_it(
        self, monkeypatch
    ):
        """Issue #15. Un `#art-9` sobre un PDF es un puntero fabricado.

        **El ancla la componemos nosotros**, a partir de los encabezados del `.md` que ingerimos.
        Sólo la sirve quien publica ese `.md` como HTML, que es nuestro sitio — lo dice el propio
        `url_de_cita`: «es el único que tiene anclas». Pegada a un PDF no lleva a ninguna parte:
        el visor ignora un fragmento que no entiende y el lector aterriza en la primera página
        creyendo que va al artículo 9.

        Y eso es justo lo que `citation_validator` existe para impedir. Su regla está escrita:
        «degradar al documento pierde precisión y no veracidad; componer un ancla que nadie leyó
        sería fabricar un puntero». El contrato la aplicaba sobre lo que decía el modelo, y
        resulta que el puntero lo fabricábamos nosotros un paso antes.

        **Por qué esto arregla el caso medido.** Las normas propias de Gerencia daban cero aciertos
        de ancla, y la issue lo diagnostica como defecto «de publicación, no de recuperación»:
        se publican sin fragmento direccionable. Son exactamente las que caen por esta rama. Al
        no llevar ancla la evidencia, cualquier cita anclada que emita el modelo se degrada sola
        con la lógica que ya existe, sin tocar el validador.

        El mismo criterio ya estaba aplicado una rama más arriba: al diario oficial sólo se le
        compone ancla si es el BOE, y si no, se quita.
        """
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        for ancora in ("art-9", "da-1", "Primer"):
            url = url_de_cita(_documento(relative_path=None), {"ancora": ancora})
            assert "#" not in url, (
                f"se ha compuesto `#{ancora}` sobre {url}. Ese destino no sirve el fragmento: "
                f"la cita aparenta una precisión que no tiene."
            )

    def test_should_strip_the_directory_from_the_relative_path(self, monkeypatch):
        monkeypatch.setenv(BASE_DEL_SITIO, SITIO)

        url = url_de_cita(_documento(relative_path="subcarpeta/REG-048.md"), {"ancora": "da-1"})

        assert url == f"{SITIO}/html/REG-048.html#da-1"


class TestLaIngestaGuardaElSlug:

    def test_should_keep_the_relative_path_in_the_document_metadata(self):
        """Sin esto la cita al sitio no se puede construir.

        `canonical_url` no sirve: para los 234 documentos publicados es la URL del PDF del
        portal, que no dice nada del nombre de la página.
        """
        from server.app.modules.agents_hub.ingestion.corpus.reconciler import _A_METADATA

        assert "relative_path" in _A_METADATA
