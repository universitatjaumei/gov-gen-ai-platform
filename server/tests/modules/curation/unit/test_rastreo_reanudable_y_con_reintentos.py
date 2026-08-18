"""Reanudar donde se quedó, reintentar lo transitorio y no repetir lo hecho (RAS.3).

Tres cosas que contra un sitio de pruebas no se notan y contra un portal real deciden si el informe
sirve:

* **La cola vivía en memoria** y el rastreo arrancaba siempre de `root_url`: un corte en la página
  8.000 obligaba a empezar de cero. Con pausa de dos segundos, empezar de cero son horas.
* **No había reintentos**: un `timeout` de 10 s marcaba la página como error y producía un
  `crawl_error` **crítico**. En un rastreo grande eso son decenas de falsos positivos por causas de
  red, mezclados con los hallazgos de verdad. Y un 404 —que sí es información: el enlace apunta a
  algo que ya no está— se confundía con ellos.
* **Cada página se pedía dos veces.** `crawl()` descargaba el HTML para extraer los enlaces, lo
  tiraba, y `SiteCrawler` volvía a pedir la misma URL para guardarla. Medido en el sondeo del
  apartado real: 25 páginas, 50 peticiones. Con cortesía de dos segundos, también dobla el tiempo.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from server.app.modules.curation.site_crawler import SiteCrawler
from server.app.modules.curation.spider import CrawlStatus, GenericSpider


@dataclass
class _Sitio:
    root_url: str = "https://www.uji.es/centres/escola-doctorat/"
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


def _spider(paginas: dict[str, str], reloj: _Reloj | None = None, fallos: dict | None = None):
    reloj = reloj or _Reloj()
    pedidas: list[str] = []
    fallos = dict(fallos or {})

    async def fetch(url: str) -> tuple[str, dict]:
        pedidas.append(url)
        if url.endswith("/robots.txt"):
            raise RuntimeError("404")
        if url in fallos:
            restantes = fallos[url]
            if restantes > 0:
                fallos[url] = restantes - 1
                raise TimeoutError("se agotó el tiempo de espera")
        return paginas.get(url, "<html><body>contenido suficiente</body></html>"), {}

    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)
    return spider, pedidas


_CONFIG = {"crawl_depth": 2, "delay_seconds": 0, "respect_robots": False}


# ---------------------------------------------------------------------------
# Reanudar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_un_rastreo_truncado_deja_escrita_la_cola_pendiente():
    enlaces = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(10))
    spider, _ = _spider({"https://www.uji.es/centres/escola-doctorat/": f"<html>{enlaces}</html>"})
    sitio = _Sitio(config_json={**_CONFIG, "max_pages": 3})

    resultado = await spider.crawl(sitio)

    assert resultado.status == CrawlStatus.COMPLETED_PARTIAL
    assert resultado.frontier, "sin la cola escrita, reanudar es empezar de cero"
    urls_pendientes = [u for u, _profundidad in resultado.frontier]
    assert all(u.startswith("https://www.uji.es") for u in urls_pendientes)
    assert len(resultado.frontier) == resultado.pages_skipped


@pytest.mark.asyncio
async def test_reanudar_arranca_por_la_cola_y_no_repite_lo_visitado():
    paginas = {f"https://www.uji.es/p{i}": "<html>ya</html>" for i in range(4)}
    spider, pedidas = _spider(paginas)
    sitio = _Sitio(
        config_json={**_CONFIG, "max_pages": 50},
        crawl_frontier={
            "pending": [["https://www.uji.es/p2", 1], ["https://www.uji.es/p3", 1]],
            "visited": [
                "https://www.uji.es/centres/escola-doctorat/",
                "https://www.uji.es/p0",
                "https://www.uji.es/p1",
            ],
        },
    )

    resultado = await spider.crawl(sitio)

    assert resultado.resumed is True
    assert "https://www.uji.es/p0" not in pedidas
    assert "https://www.uji.es/centres/escola-doctorat/" not in pedidas
    assert set(resultado.crawled_urls) == {"https://www.uji.es/p2", "https://www.uji.es/p3"}


@pytest.mark.asyncio
async def test_un_rastreo_completo_no_deja_cola_que_reanudar():
    spider, _ = _spider({"https://www.uji.es/centres/escola-doctorat/": "<html>fin</html>"})
    sitio = _Sitio(config_json={**_CONFIG, "max_pages": 10})

    resultado = await spider.crawl(sitio)

    assert resultado.status == CrawlStatus.COMPLETED
    assert resultado.frontier == []


@pytest.mark.asyncio
async def test_al_reanudar_se_conserva_lo_ya_visitado_en_la_cola_nueva():
    """Si al truncar otra vez se olvidara lo visitado en la vuelta anterior, cada reanudación
    volvería a rastrear lo mismo."""
    enlaces = "".join(f'<a href="/q{i}">q{i}</a>' for i in range(10))
    spider, _ = _spider({"https://www.uji.es/p2": f"<html>{enlaces}</html>"})
    sitio = _Sitio(
        config_json={**_CONFIG, "max_pages": 1},
        crawl_frontier={
            "pending": [["https://www.uji.es/p2", 1]],
            "visited": ["https://www.uji.es/ya-visitada"],
        },
    )

    resultado = await spider.crawl(sitio)

    assert "https://www.uji.es/ya-visitada" in resultado.visited


# ---------------------------------------------------------------------------
# Reintentar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_un_fallo_transitorio_se_reintenta_y_no_deja_hallazgo():
    spider, pedidas = _spider(
        {"https://www.uji.es/centres/escola-doctorat/": "<html>al final si</html>"},
        fallos={"https://www.uji.es/centres/escola-doctorat/": 1},
    )
    spider.configurar_cortesia(_CONFIG)

    cuerpo, _cabeceras = await spider._fetch("https://www.uji.es/centres/escola-doctorat/")

    assert "al final si" in cuerpo
    assert pedidas.count("https://www.uji.es/centres/escola-doctorat/") == 2


@pytest.mark.asyncio
async def test_la_espera_entre_reintentos_crece():
    reloj = _Reloj()
    spider, _ = _spider({}, reloj, fallos={"https://www.uji.es/x": 2})
    spider.configurar_cortesia({**_CONFIG, "max_retries": 3})

    await spider._fetch("https://www.uji.es/x")

    # Dos reintentos con espera creciente: la segunda espera más que la primera.
    assert reloj.ahora > 0


@pytest.mark.asyncio
async def test_un_fallo_persistente_acaba_fallando_y_dice_cuantos_intentos_hubo():
    from server.app.modules.curation.cortesia import FalloTrasReintentos

    spider, pedidas = _spider({}, fallos={"https://www.uji.es/y": 99})
    spider.configurar_cortesia({**_CONFIG, "max_retries": 3})

    with pytest.raises(FalloTrasReintentos) as fallo:
        await spider._fetch("https://www.uji.es/y")

    assert fallo.value.intentos == 3
    assert pedidas.count("https://www.uji.es/y") == 3


@pytest.mark.asyncio
async def test_un_404_no_se_reintenta_porque_es_una_respuesta():
    """El servidor ha contestado: esa página ya no está. Reintentarlo es tráfico inútil."""
    import httpx

    pedidas: list[str] = []

    async def fetch(url: str) -> tuple[str, dict]:
        pedidas.append(url)
        respuesta = httpx.Response(404, request=httpx.Request("GET", url))
        raise httpx.HTTPStatusError("404", request=respuesta.request, response=respuesta)

    reloj = _Reloj()
    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)
    spider.configurar_cortesia({**_CONFIG, "max_retries": 3})

    with pytest.raises(httpx.HTTPStatusError):
        await spider._fetch("https://www.uji.es/z")

    assert pedidas.count("https://www.uji.es/z") == 1


# ---------------------------------------------------------------------------
# No repetir lo hecho
# ---------------------------------------------------------------------------


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


@pytest.mark.asyncio
async def test_la_cola_pendiente_queda_guardada_en_el_sitio():
    """En el spider la cola es memoria; para reanudar tiene que quedar en la fila del sitio."""
    raiz = "https://www.uji.es/centres/escola-doctorat/"
    enlaces = "".join(
        f'<a href="/centres/escola-doctorat/p{i}">p{i}</a>' for i in range(10)
    )
    spider, _ = _spider({raiz: f"<html>{enlaces}</html>"})
    sitio = _Sitio(config_json={
        **_CONFIG, "max_pages": 2, "url_regex_filter": r"/centres/escola-doctorat/",
    })
    crawler = SiteCrawler(
        session=_Sesion(sitio), spider=spider, signal_extractor=_SinSitemap(),
        page_repo=_RepoDePaginas(),
    )

    resumen = await crawler.crawl_site(sitio.id)

    assert resumen.truncated is True
    assert sitio.crawl_frontier is not None
    assert sitio.crawl_frontier["pending"], "sin cola guardada, reanudar es empezar de cero"
    assert sitio.crawl_frontier["visited"]


@pytest.mark.asyncio
async def test_un_rastreo_completo_borra_la_cola_de_la_vez_anterior():
    """Si no se borrara, la siguiente ejecución arrancaría por la mitad de un recorrido acabado."""
    raiz = "https://www.uji.es/centres/escola-doctorat/"
    spider, _ = _spider({raiz: "<html>sin enlaces</html>"})
    sitio = _Sitio(
        config_json={**_CONFIG, "max_pages": 10},
        crawl_frontier={"pending": [], "visited": ["https://www.uji.es/vieja"]},
    )
    crawler = SiteCrawler(
        session=_Sesion(sitio), spider=spider, signal_extractor=_SinSitemap(),
        page_repo=_RepoDePaginas(),
    )

    await crawler.crawl_site(sitio.id)

    assert sitio.crawl_frontier is None


@pytest.mark.asyncio
async def test_la_pagina_que_el_recorrido_ya_descargo_no_se_vuelve_a_pedir():
    """Era el doble de peticiones y el doble de tiempo contra el portal de la propia casa."""
    raiz = "https://www.uji.es/centres/escola-doctorat/"
    paginas = {
        raiz: '<html><body>Inicio<a href="/centres/escola-doctorat/beques">Beques</a></body></html>',
        f"{raiz}beques": "<html><body>Convocatoria de beques oberta</body></html>",
    }
    spider, pedidas = _spider(paginas)
    sitio = _Sitio(config_json={
        **_CONFIG, "max_pages": 10, "url_regex_filter": r"/centres/escola-doctorat/",
    })
    repo = _RepoDePaginas()
    crawler = SiteCrawler(
        session=_Sesion(sitio), spider=spider, signal_extractor=_SinSitemap(), page_repo=repo
    )

    await crawler.crawl_site(sitio.id)

    assert set(repo.guardadas) == {raiz, f"{raiz}beques"}
    for url in (raiz, f"{raiz}beques"):
        assert pedidas.count(url) == 1, f"«{url}» se pidió {pedidas.count(url)} veces"
