"""Tests SEC.8.8 — el rastreo de curación deja de estar desconectado.

`main.py` construía el job de calidad con un `_NullCrawler` y `detectors=[]`, y el
comentario decía que los detectores reales «se inyectan en producción a través de la
configuración de cada entorno». No existía tal mecanismo: `SpiderFactory` y `SiteCrawler`
no tenían un solo llamante de producción, así que `POST /hub/sites/{id}/crawl` respondía
202 y acababa siempre en `errors=["no spider configured"]`.

Eso no dejaba «una funcionalidad de menos»: el rastreo es la **entrada** del flujo de
curación —descubrir páginas, auditarlas, seleccionar candidatas, publicar—, así que sin él
la herramienta que CUR.2 construyó se queda sin nada que revisar.

Lo que el rastreo NO hace, y es deliberado (`docs/DECISION_CURACION_SEPARADA.md`): ingerir
al corpus. Llena la bandeja del curador; publicar sigue siendo un botón por candidata.

La pieza que faltaba es el despachador: `SiteCrawler` recibe **un** spider ya construido,
pero el spider correcto depende del `spider_type` de cada sitio, que solo se sabe leyendo el
sitio. Sin algo que haga esa resolución, no había forma de pasar del `site_id` al rastreo.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock



class _SesionFalsa:
    def __init__(self, site):
        self._site = site
        self.commit = AsyncMock()
        self.flush = AsyncMock()

    async def get(self, _model, _pk):
        return self._site

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


def _factory_de(site):
    def _crear():
        return _SesionFalsa(site)

    return _crear


class TestDespachadorDeRastreo:

    async def test_should_select_the_spider_declared_by_the_site(self, monkeypatch):
        """El `spider_type` es del sitio, así que el spider se elige por sitio y no una
        vez al arrancar: dos sitios de la misma instalación pueden ser de tipos distintos."""
        from server.app.modules.curation.site_crawler_dispatcher import (
            SiteCrawlerDispatcher,
        )

        site = SimpleNamespace(
            id=uuid.uuid4(), spider_type="dogv", root_url="https://dogv.test"
        )
        elegidos: list[str] = []

        class _FactorySpy:
            def get_spider(self, source_type):
                elegidos.append(source_type)
                return MagicMock()

        despachador = SiteCrawlerDispatcher(
            session_factory=_factory_de(site), spider_factory=_FactorySpy()
        )

        crawler = MagicMock()
        crawler.crawl_site = AsyncMock(return_value=MagicMock(errors=[]))
        monkeypatch.setattr(
            "server.app.modules.curation.site_crawler_dispatcher.SiteCrawler",
            lambda *a, **k: crawler,
        )

        await despachador.crawl_site(site.id)

        assert elegidos == ["dogv"]
        crawler.crawl_site.assert_awaited_once_with(site.id, section_id=None)

    async def test_should_fall_back_to_the_generic_spider(self, monkeypatch):
        from server.app.modules.curation.site_crawler_dispatcher import (
            SiteCrawlerDispatcher,
        )

        site = SimpleNamespace(id=uuid.uuid4(), spider_type=None, root_url="https://x.test")
        elegidos: list[str] = []

        class _FactorySpy:
            def get_spider(self, source_type):
                elegidos.append(source_type)
                return MagicMock()

        despachador = SiteCrawlerDispatcher(
            session_factory=_factory_de(site), spider_factory=_FactorySpy()
        )
        crawler = MagicMock()
        crawler.crawl_site = AsyncMock(return_value=MagicMock(errors=[]))
        monkeypatch.setattr(
            "server.app.modules.curation.site_crawler_dispatcher.SiteCrawler",
            lambda *a, **k: crawler,
        )

        await despachador.crawl_site(site.id)

        assert elegidos == ["generic"]

    async def test_should_report_an_error_for_an_unknown_site(self):
        from server.app.modules.curation.site_crawler_dispatcher import (
            SiteCrawlerDispatcher,
        )

        despachador = SiteCrawlerDispatcher(session_factory=_factory_de(None))

        resumen = await despachador.crawl_site(uuid.uuid4())

        assert resumen.errors, "un sitio inexistente tiene que decirlo, no rastrear nada"

    async def test_should_report_an_error_for_an_unknown_spider_type(self):
        """Un `spider_type` que este despliegue no entiende se declara como error, no se
        sustituye por el genérico: rastrear el DOGV con el spider equivocado produce
        páginas basura que luego alguien tendría que revisar a mano."""
        from server.app.modules.curation.site_crawler_dispatcher import (
            SiteCrawlerDispatcher,
        )

        site = SimpleNamespace(
            id=uuid.uuid4(), spider_type="inventado", root_url="https://x.test"
        )
        despachador = SiteCrawlerDispatcher(session_factory=_factory_de(site))

        resumen = await despachador.crawl_site(site.id)

        assert resumen.errors


class TestElArranqueNoUsaUnCrawlerNulo:

    def test_should_not_keep_a_null_crawler_in_main(self):
        """El guardarraíl: mientras `_NullCrawler` siga cableado, el botón de rastrear de
        la interfaz responde 202 y no hace nada, que es peor que no tenerlo."""
        from server.app import main

        assert not hasattr(main, "_NullCrawler"), (
            "el arranque sigue construyendo el job de calidad con un crawler que no rastrea"
        )
