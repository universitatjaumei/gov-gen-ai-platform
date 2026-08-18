"""La misma página por dos esquemas es una página, no dos (RAS.5).

En el primer rastreo real del apartado, de 400 páginas rastreadas **la mitad eran duplicados**: el
portal responde por `http://` y por `https://`, el HTML enlaza a los dos, y el spider los tomó por
páginas distintas. Dos consecuencias, y las dos malas:

* **Se gastó la mitad del presupuesto** —y de la paciencia del servidor— pidiendo dos veces lo
  mismo. Con la pausa de cortesía a 2 s, eso son minutos regalados.
* El detector emitió **191 avisos de supersesión** entre `http` y `https` de la misma página.

El arreglo tiene dos mitades: normalizar el esquema antes de encolar —gratis, evita la petición— y
quedarse con la **URL final tras las redirecciones**, que es la única que dice de verdad qué página
se ha leído. `http://…` redirige a `https://…` en este portal: quien lo sabía era la respuesta, y se
estaba tirando.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from server.app.modules.curation.spider import GenericSpider

_RAIZ = "https://www.uji.es/centres/escola-doctorat/"


@dataclass
class _Sitio:
    root_url: str = _RAIZ
    config_json: dict = field(default_factory=dict)
    crawl_frontier: dict | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)


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


@pytest.mark.asyncio
async def test_un_enlace_en_http_no_se_pide_aparte_del_de_https():
    """El portal enlaza a los dos esquemas; el rastreo tiene que quedarse con uno."""
    pedidas: list[str] = []
    cuerpo = (
        '<html><body><a href="http://www.uji.es/centres/escola-doctorat/beques/">http</a>'
        '<a href="https://www.uji.es/centres/escola-doctorat/beques/">https</a></body></html>'
    )

    async def fetch(url: str) -> tuple[str, dict]:
        pedidas.append(url)
        if url.endswith("/robots.txt"):
            raise RuntimeError("404")
        return (cuerpo if url == _RAIZ else "<html><body>Beques</body></html>",
                {"content-type": "text/html"})

    reloj = _Reloj()
    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)

    resultado = await spider.crawl(_Sitio(config_json=_CONFIG))

    beques = [u for u in pedidas if u.endswith("/beques/")]
    assert len(beques) == 1, f"la misma página se pidió {len(beques)} veces: {beques}"
    assert beques[0].startswith("https://")
    assert resultado.pages_crawled == 2


@pytest.mark.asyncio
async def test_una_redireccion_a_algo_ya_visitado_no_cuenta_como_pagina_nueva():
    """Es lo que pasaba: `http://x` redirigía a `https://x`, ya leída, y se guardaba otra vez."""
    ya_visto = f"{_RAIZ}beques/"
    cuerpo = f'<html><body><a href="{ya_visto}">Beques</a>' \
             f'<a href="{_RAIZ}alias/">Alias</a></body></html>'

    async def fetch(url: str) -> tuple[str, dict]:
        if url.endswith("/robots.txt"):
            raise RuntimeError("404")
        if url == _RAIZ:
            return cuerpo, {"content-type": "text/html"}
        if url == f"{_RAIZ}alias/":
            # El servidor responde con el contenido de otra URL: la respuesta lo dice.
            return "<html><body>Beques</body></html>", {
                "content-type": "text/html", "x-final-url": ya_visto,
            }
        return "<html><body>Beques</body></html>", {"content-type": "text/html"}

    reloj = _Reloj()
    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)

    resultado = await spider.crawl(_Sitio(config_json=_CONFIG))

    assert resultado.crawled_urls.count(ya_visto) == 1
    assert f"{_RAIZ}alias/" not in resultado.crawled_urls


@pytest.mark.asyncio
async def test_un_enlace_a_otro_host_en_http_sigue_quedando_fuera():
    """Normalizar el esquema no puede colar páginas de otro dominio."""
    cuerpo = '<html><body><a href="http://otro.example.org/escola-doctorat/x">fuera</a></body></html>'

    async def fetch(url: str) -> tuple[str, dict]:
        if url.endswith("/robots.txt"):
            raise RuntimeError("404")
        return cuerpo, {"content-type": "text/html"}

    reloj = _Reloj()
    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)

    resultado = await spider.crawl(_Sitio(config_json=_CONFIG))

    assert all("otro.example.org" not in u for u in resultado.crawled_urls)
