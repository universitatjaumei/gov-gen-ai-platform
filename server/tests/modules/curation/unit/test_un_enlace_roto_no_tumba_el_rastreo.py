"""Un enlace roto no puede tumbar el rastreo entero (RAS.5).

Encontrado lanzando el primer rastreo real del apartado de la Escuela de Doctorado: devolvió
**cero páginas**. El motivo, en el resumen: un 404 en
`https://www.uji.es/centres/escola-doctorat/estudiantat/`.

El bucle del spider hacía `await self._fetch(url)` sin proteger la página: la excepción subía por
`crawl()`, la recogía el `except Exception` de `crawl_site` —que está pensado para un fallo *global*
del rastreo—, el sitio quedaba en `status="error"` y no se guardaba ni una página. O sea que
**cualquier portal con un enlace roto era irrastreable**, y todo portal real tiene enlaces rotos:
son justo lo que este módulo existe para encontrar.

Peor todavía: el 404 es información valiosa —contenido que ya no está y hay que depurar— y se
perdía, porque el rastreo moría en vez de registrarlo.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from server.app.modules.curation.site_crawler import SiteCrawler
from server.app.modules.curation.spider import CrawlStatus, GenericSpider

_RAIZ = "https://www.uji.es/centres/escola-doctorat/"
_ROTA = f"{_RAIZ}estudiantat/"
_BUENA = f"{_RAIZ}beques/"


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


def _spider_con_un_404():
    paginas = {
        _RAIZ: (
            f'<html><body>Inicio<a href="{_ROTA}">Estudiantat</a>'
            f'<a href="{_BUENA}">Beques</a></body></html>'
        ),
        _BUENA: "<html><body>Convocatoria de beques del programa</body></html>",
    }

    async def fetch(url: str) -> tuple[str, dict]:
        if url.endswith("/robots.txt"):
            raise RuntimeError("404")
        if url == _ROTA:
            respuesta = httpx.Response(404, request=httpx.Request("GET", url))
            raise httpx.HTTPStatusError("404", request=respuesta.request, response=respuesta)
        return paginas[url], {}

    reloj = _Reloj()
    return GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)


_CONFIG = {
    "crawl_depth": 2, "max_pages": 50, "delay_seconds": 0, "respect_robots": False,
    "url_regex_filter": r"escola-doctorat",
}


@pytest.mark.asyncio
async def test_el_recorrido_sigue_despues_de_un_404_y_lo_anota():
    spider = _spider_con_un_404()

    resultado = await spider.crawl(_Sitio(config_json=_CONFIG))

    assert _BUENA in resultado.crawled_urls, "el enlace roto se llevó por delante el resto"
    assert resultado.status == CrawlStatus.COMPLETED
    assert [f["url"] for f in resultado.fallos] == [_ROTA]
    assert resultado.fallos[0]["kind"] == "not_found"


class _RepoDePaginas:
    def __init__(self) -> None:
        self.guardadas: dict[str, dict] = {}

    async def upsert(self, *, site_id: uuid.UUID, url: str, **campos: Any) -> Any:
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


async def _rastrear_sitio() -> tuple[Any, _RepoDePaginas, _Sitio]:
    sitio = _Sitio(config_json=_CONFIG)
    repo = _RepoDePaginas()
    crawler = SiteCrawler(
        session=_Sesion(sitio), spider=_spider_con_un_404(),
        signal_extractor=_SinSitemap(), page_repo=repo,
    )
    resumen = await crawler.crawl_site(sitio.id)
    return resumen, repo, sitio


@pytest.mark.asyncio
async def test_el_rastreo_del_sitio_guarda_las_paginas_buenas():
    resumen, repo, sitio = await _rastrear_sitio()

    assert _BUENA in repo.guardadas, "cero páginas guardadas por un enlace roto"
    assert resumen.pages_new >= 2
    assert sitio.status == "active"


@pytest.mark.asyncio
async def test_el_404_queda_registrado_como_pagina_en_error_y_con_su_causa():
    """Es lo que hace útil el hallazgo: el enlace apunta a algo que ya no está."""
    _resumen, repo, _sitio = await _rastrear_sitio()

    assert _ROTA in repo.guardadas
    assert repo.guardadas[_ROTA]["status"] == "error"
    assert repo.guardadas[_ROTA]["error_kind"] == "not_found"


@pytest.mark.asyncio
async def test_el_resumen_cuenta_el_fallo_sin_llamarlo_fallo_global():
    resumen, _repo, _sitio = await _rastrear_sitio()

    assert resumen.pages_error == 1
    assert resumen.errors == [], "un enlace roto no es un fallo del rastreo entero"
