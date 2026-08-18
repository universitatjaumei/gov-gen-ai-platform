"""Un PDF enlazado no es una página web, y guardarlo como texto tumba el rastreo (RAS.5).

Segundo hallazgo del rastreo real del apartado de la Escuela de Doctorado. El recorrido siguió un
enlace a
`.../base/industrial/ACORDCDED22023_5_Comput_hores_formacio_gestio_patents.pdf`,
`httpx` decodificó los bytes del PDF como si fueran texto y se intentó guardar el resultado en
`markdown_content`. Postgres lo rechazó:

    invalid byte sequence for encoding "UTF8": 0x00

y con ello **murió el rastreo completo**, porque el `upsert` de una página no estaba protegido: el
`try` sólo cubría la descarga. Segunda vez que el mismo patrón deja el sitio en `error` con cero
páginas, esta vez por el lado de la escritura.

Y antes del error, lo que se estaba a punto de guardar ya era basura: 26.872 «tokens» de cabecera
binaria y `language: 'bn'` —bengalí— detectado sobre `%PDF-1.7`. Un PDF del portal puede ser
contenido interesante, pero **no por esta vía**: el corpus tiene su propio camino para documentos.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from server.app.modules.curation.site_crawler import SiteCrawler
from server.app.modules.curation.spider import CrawlStatus, GenericSpider

_RAIZ = "https://www.uji.es/centres/escola-doctorat/"
_PDF = f"{_RAIZ}base/industrial/ACORD_2023.pdf"
_BUENA = f"{_RAIZ}beques/"

#: Un PDF de verdad empieza así y lleva bytes nulos dentro.
_CUERPO_PDF = "%PDF-1.7\n%\x00\x00\x00\x00\n472 0 obj stream x\x00\x01binario"


@dataclass
class _Sitio:
    root_url: str = _RAIZ
    config_json: dict = field(default_factory=dict)
    crawl_frontier: dict | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    sitemap_url: str | None = None
    last_crawled_at: Any = None
    status: str = "active"
    error_message: str | None = None


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora

    async def dormir(self, segundos: float) -> None:
        self.ahora += segundos


_CONFIG = {
    "crawl_depth": 2, "max_pages": 50, "delay_seconds": 0, "respect_robots": False,
    "url_regex_filter": r"escola-doctorat",
}


def _spider_con_un_pdf():
    paginas = {
        _RAIZ: (
            f'<html><body>Inicio<a href="{_PDF}">Acord del consell</a>'
            f'<a href="{_BUENA}">Beques</a></body></html>'
        ),
        _BUENA: "<html><body>Convocatoria de beques del programa</body></html>",
    }
    pedidas: list[str] = []

    async def fetch(url: str) -> tuple[str, dict]:
        pedidas.append(url)
        if url.endswith("/robots.txt"):
            raise RuntimeError("404")
        if url == _PDF:
            return _CUERPO_PDF, {"content-type": "application/pdf"}
        return paginas[url], {"content-type": "text/html; charset=UTF-8"}

    reloj = _Reloj()
    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)
    return spider, pedidas


@pytest.mark.asyncio
async def test_el_recorrido_no_encola_un_enlace_a_un_pdf():
    """Se ve en la URL, así que ni hace falta pedirlo: es tráfico que no aporta nada."""
    spider, pedidas = _spider_con_un_pdf()

    resultado = await spider.crawl(_Sitio(config_json=_CONFIG))

    assert _PDF not in resultado.crawled_urls
    assert _PDF not in pedidas
    assert _BUENA in resultado.crawled_urls


@pytest.mark.asyncio
async def test_un_recurso_que_no_es_html_se_descarta_al_ver_su_tipo():
    """La extensión no siempre está: la verdad la dice el `Content-Type` de la respuesta."""
    sin_extension = f"{_RAIZ}descarrega"

    async def fetch(url: str) -> tuple[str, dict]:
        if url.endswith("/robots.txt"):
            raise RuntimeError("404")
        if url == sin_extension:
            return _CUERPO_PDF, {"content-type": "application/pdf"}
        return (
            f'<html><body><a href="{sin_extension}">Descarrega</a></body></html>',
            {"content-type": "text/html"},
        )

    reloj = _Reloj()
    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)

    resultado = await spider.crawl(_Sitio(config_json=_CONFIG))

    assert sin_extension not in resultado.crawled_urls
    assert resultado.status == CrawlStatus.COMPLETED
    assert resultado.no_legibles >= 1


class _RepoQueFalla:
    """Falla al guardar una página concreta, como falló Postgres con el byte nulo."""

    def __init__(self, url_que_falla: str | None = None) -> None:
        self.guardadas: dict[str, dict] = {}
        self._url_que_falla = url_que_falla

    async def upsert(self, *, site_id: uuid.UUID, url: str, **campos: Any) -> Any:
        if url == self._url_que_falla:
            raise RuntimeError('invalid byte sequence for encoding "UTF8": 0x00')
        self.guardadas[url] = campos

        class _P:
            id = uuid.uuid4()

        return _P()

    async def list_by_site(self, site_id: uuid.UUID, status: str | None = None) -> list:
        return []

    async def mark_gone(self, page_ids: list[uuid.UUID]) -> int:
        return 0


class _Sesion:
    def __init__(self, sitio: Any) -> None:
        self._sitio = sitio

    async def get(self, modelo: Any, ident: Any) -> Any:
        return self._sitio

    async def flush(self) -> None:
        return None


class _SinSitemap:
    def extract_from_headers(self, headers: dict) -> dict:
        return {"http_last_modified": None, "http_etag": None}

    def extract_canonical(self, html: str) -> str | None:
        return None

    def extract_content_year(self, url: str, text: str) -> int | None:
        return None

    async def fetch_sitemap(self, url: str, fetch_fn: Any) -> dict:
        return {}


@pytest.mark.asyncio
async def test_si_una_pagina_no_se_puede_guardar_las_demas_si_se_guardan():
    """El `upsert` de una página no puede tumbar el rastreo entero. Paso: 0 páginas → 1."""
    sitio = _Sitio(config_json=_CONFIG)
    repo = _RepoQueFalla(url_que_falla=_RAIZ)
    spider, _ = _spider_con_un_pdf()
    crawler = SiteCrawler(
        session=_Sesion(sitio), spider=spider, signal_extractor=_SinSitemap(), page_repo=repo
    )

    resumen = await crawler.crawl_site(sitio.id)

    assert _BUENA in repo.guardadas, "un fallo al guardar se llevó por delante el resto"
    assert resumen.pages_error >= 1
    assert sitio.status == "active"


@pytest.mark.asyncio
async def test_el_texto_que_se_guarda_no_lleva_bytes_nulos():
    """Cinturón: cualquier respuesta puede traerlos, y Postgres rechaza la fila entera."""
    from server.app.modules.curation.contenido_web import texto_visible

    assert "\x00" not in texto_visible("<p>hola\x00mundo</p>")
