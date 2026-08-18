"""La trampa de rastreador del portal: parámetros de redirección que se acumulan (RAS.5).

Encontrado en el segundo rastreo real, con las cifras delante: 107 avisos de supersesión y 526 URLs
pendientes que no se acababan nunca. Todos apuntaban a la misma página:

    /centres/escola-doctorat/
    /centres/escola-doctorat/?urlRedirect=https://www.uji.es/centres/escola-doctorat/&url=/centres/escola-doctorat/
    /centres/escola-doctorat/?urlRedirect=…&url=…&urlRedirect=…&url=…

El conmutador de idioma del portal construye enlaces que **llevan la URL actual dentro**, así que
cada página rastreada genera una variante más larga de sí misma: un espacio de URLs infinito con el
mismo contenido detrás. Es la trampa de rastreador clásica, y contra un portal real aparece sola.

Dos consecuencias, y las dos se veían en el informe: el presupuesto se gastaba en variantes de la
misma página —el apartado nunca se terminaba de rastrear— y el detector las agrupaba por su path
común, declarando que una versión «supersede» a la otra.

La regla: un parámetro cuyo valor **es una URL o una ruta** es un ayudante de navegación, no
identidad de página. Se quita antes de encolar. Y un tope de longitud como red de seguridad, porque
ninguna página de contenido necesita 500 caracteres de URL.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pytest

from server.app.modules.curation.spider import GenericSpider, url_de_pagina

_RAIZ = "https://www.uji.es/centres/escola-doctorat/"
_TRAMPA = (
    f"{_RAIZ}?urlRedirect=https://www.uji.es/centres/escola-doctorat/"
    "&url=/centres/escola-doctorat/"
)


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
    "crawl_depth": 3, "max_pages": 50, "delay_seconds": 0, "respect_robots": False,
    "url_regex_filter": r"escola-doctorat",
}


# ---------------------------------------------------------------------------
# La normalización, a solas
# ---------------------------------------------------------------------------


def test_un_parametro_que_lleva_una_url_dentro_no_es_identidad_de_pagina():
    assert url_de_pagina(_TRAMPA) == _RAIZ


def test_un_parametro_que_lleva_una_ruta_dentro_tampoco():
    assert url_de_pagina(f"{_RAIZ}?url=/centres/escola-doctorat/") == _RAIZ


def test_un_parametro_de_verdad_se_conserva():
    """Un identificador o una página de listado sí distinguen contenido."""
    con_pagina = f"{_RAIZ}noticies/?pagina=3"
    assert url_de_pagina(con_pagina) == con_pagina


def test_una_url_sin_parametros_se_queda_igual():
    assert url_de_pagina(_RAIZ) == _RAIZ


def test_una_url_absurdamente_larga_se_descarta():
    larga = _RAIZ + "?x=" + "a" * 600
    assert url_de_pagina(larga) is None


# ---------------------------------------------------------------------------
# El recorrido
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_el_recorrido_no_persigue_las_variantes_de_la_misma_pagina():
    """Con la trampa puesta, el rastreo se quedaba dando vueltas sobre una sola página."""
    pedidas: list[str] = []
    # Cada página enlaza a su propia variante con parámetros, como hace el portal.
    def cuerpo(url: str) -> str:
        return (
            f'<html><body><a href="{url}?urlRedirect={url}&url=/centres/escola-doctorat/">idioma</a>'
            f'<a href="{_RAIZ}beques/">Beques</a></body></html>'
        )

    async def fetch(url: str) -> tuple[str, dict]:
        pedidas.append(url)
        if url.endswith("/robots.txt"):
            raise RuntimeError("404")
        return cuerpo(url), {"content-type": "text/html"}

    reloj = _Reloj()
    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)

    resultado = await spider.crawl(_Sitio(config_json=_CONFIG))

    con_parametros = [u for u in pedidas if "urlRedirect" in u]
    assert con_parametros == [], f"persiguió {len(con_parametros)} variantes de la misma página"
    assert f"{_RAIZ}beques/" in resultado.crawled_urls
    assert resultado.pages_crawled == 2


@pytest.mark.asyncio
async def test_dos_variantes_de_la_misma_pagina_no_son_dos_paginas():
    """Antes: 107 avisos de «hay una versión nueva y la vieja sigue ahí» sobre una sola página."""
    from server.app.modules.curation.deterministic_detector import _process_key

    assert _process_key(None, _TRAMPA) == _process_key(None, _RAIZ)
