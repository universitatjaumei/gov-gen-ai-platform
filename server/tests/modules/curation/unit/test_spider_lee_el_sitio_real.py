"""VER.6 — el spider tiene que poder rastrear un `HubWebSite`.

El rastreo **nunca ha funcionado**. Al lanzarlo desde la pantalla, el sitio quedaba en
`status='error'` con:

    'HubWebSite' object has no attribute 'url'

`GenericSpider.crawl` lee `source.url`, y el modelo tiene `root_url` desde que
`HubWebSource` se renombró a `HubWebSite`. Ningún test lo cazó porque **todos doblan el
spider**: `test_site_crawler.py` usa un `_FakeSpider`, y su `_FakeSite` ya declara `root_url`,
así que el desajuste vivía justo en la única costura que nadie cruzaba.
"""
from __future__ import annotations

import uuid

import pytest

from server.app.modules.curation.spider import GenericSpider


class _SitioComoElDeLaBase:
    """Los campos que `HubWebSite` expone de verdad."""

    def __init__(self, root_url: str, config_json: dict | None = None) -> None:
        self.id = uuid.uuid4()
        self.root_url = root_url
        self.sitemap_url = None
        self.config_json = config_json or {}
        self.spider_type = "generic"


PAGINAS = {
    "https://normativa.uji.es/": '<html><a href="/html/reglament.html">Reglament</a></html>',
    "https://normativa.uji.es/html/reglament.html": "<html><body>Article 1.</body></html>",
}


async def _descargar(url: str):
    return PAGINAS.get(url, "<html></html>"), {}


class TestElSpiderYElSitio:

    @pytest.mark.asyncio
    async def test_should_crawl_a_site_as_the_database_stores_it(self):
        sitio = _SitioComoElDeLaBase("https://normativa.uji.es/")

        resultado = await GenericSpider(fetch_fn=_descargar).crawl(sitio)

        assert "https://normativa.uji.es/" in resultado.crawled_urls

    @pytest.mark.asyncio
    async def test_should_follow_the_links_it_finds(self):
        """Con profundidad 1 el spider sigue los enlaces de la raíz: es lo que convierte
        «una URL» en «un sitio»."""
        sitio = _SitioComoElDeLaBase("https://normativa.uji.es/", {"crawl_depth": 1})

        resultado = await GenericSpider(fetch_fn=_descargar).crawl(sitio)

        assert "https://normativa.uji.es/html/reglament.html" in resultado.crawled_urls

    @pytest.mark.asyncio
    async def test_should_stay_inside_the_site(self):
        """Un enlace externo no convierte el rastreo de un sitio en el de internet."""
        paginas = {
            "https://normativa.uji.es/": '<html><a href="https://www.boe.es/x">BOE</a></html>',
        }

        async def _descargar_externo(url: str):
            return paginas.get(url, "<html></html>"), {}

        sitio = _SitioComoElDeLaBase("https://normativa.uji.es/", {"crawl_depth": 1})

        resultado = await GenericSpider(fetch_fn=_descargar_externo).crawl(sitio)

        assert not any("boe.es" in u for u in resultado.crawled_urls)
