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
        monkeypatch.delenv(BASE_DEL_SITIO, raising=False)

        url = url_de_cita(_documento(), {"ancora": "art-9"})

        assert url == "https://uji.es/x.pdf#art-9"

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

        assert url == "https://uji.es/x.pdf#art-9"

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
