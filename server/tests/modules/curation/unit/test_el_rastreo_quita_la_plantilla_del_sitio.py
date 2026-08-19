"""El rastreo quita la plantilla, y dice cuánta ha quitado (CUR.3).

Los selectores declarados sólo llegan hasta donde alguien los escribió. La pasada de repetición no
necesita saber nada del portal: una línea que sale igual en casi todas sus páginas es menú. Se hace
al final del rastreo, cuando ya están todas leídas, porque es lo único que permite verlo.

Y las cifras del recorte van en el resumen: sin ellas no se puede juzgar si merece la pena, ni notar
que un día dejó de funcionar.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from server.app.modules.curation.site_crawler import SiteCrawler
from server.app.modules.curation.spider import CrawlResult, CrawlStatus

_RAIZ = "https://ejemplo.org/apartado/"
_MENU = "Inici Serveis Contacte Cercar al lloc"
_PIE = "Universitat. Avinguda. Telefon. Avis legal"


def _pagina_html(n: int) -> str:
    return (
        f"<html><body><div class='menu'>{_MENU}</div>"
        f"<main><h1>Titol de la pagina {n}</h1>"
        f"<p>Contingut propi i diferent de la pagina numero {n}, amb prou text.</p></main>"
        f"<div class='peu'>{_PIE}</div></body></html>"
    )


@dataclass
class _PaginaGuardada:
    url: str
    markdown_content: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    content_hash: str | None = None
    status: str = "active"
    token_count: int | None = None


class _Repo:
    """Repo en memoria que se comporta como el de verdad para lo que este test mira."""

    def __init__(self) -> None:
        self.paginas: dict[str, _PaginaGuardada] = {}

    async def upsert(self, *, site_id: uuid.UUID, url: str, **campos: Any) -> Any:
        existente = self.paginas.get(url)
        if existente is None:
            existente = _PaginaGuardada(url=url, markdown_content=campos.get("markdown_content", ""))
            self.paginas[url] = existente
        for clave, valor in campos.items():
            if hasattr(existente, clave):
                setattr(existente, clave, valor)
        return existente

    async def list_by_site(self, site_id: uuid.UUID, status: str | None = None) -> list:
        return [p for p in self.paginas.values() if status is None or p.status == status]

    async def mark_gone(self, page_ids: list[uuid.UUID]) -> int:
        return 0


@dataclass
class _Sitio:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    root_url: str = _RAIZ
    sitemap_url: str | None = None
    config_json: dict = field(default_factory=dict)
    crawl_frontier: dict | None = None
    last_crawled_at: Any = None
    status: str = "active"
    error_message: str | None = None


class _Sesion:
    def __init__(self, sitio: Any) -> None:
        self._sitio = sitio

    async def get(self, modelo: Any, ident: Any) -> Any:
        return self._sitio

    async def flush(self) -> None:
        return None


class _Spider:
    def __init__(self, cuantas: int) -> None:
        self._urls = [f"{_RAIZ}p{i}/" for i in range(cuantas)]

    async def crawl(self, source: Any) -> CrawlResult:
        return CrawlResult(
            crawled_urls=list(self._urls),
            pages_crawled=len(self._urls),
            pages_skipped=0,
            status=CrawlStatus.COMPLETED,
        )

    async def _fetch(self, url: str) -> tuple[str, dict]:
        n = int(url.rstrip("/").rsplit("p", 1)[-1])
        return _pagina_html(n), {"content-type": "text/html"}


class _SinSitemap:
    def extract_from_headers(self, headers: dict) -> dict:
        return {"http_last_modified": None, "http_etag": None}

    def extract_canonical(self, html: str) -> str | None:
        return None

    def extract_content_year(self, url: str, text: str) -> int | None:
        return None

    async def fetch_sitemap(self, url: str, fetch_fn: Any) -> dict:
        return {}


async def _rastrear(cuantas: int = 8, config: dict | None = None):
    sitio = _Sitio(config_json=config or {})
    repo = _Repo()
    crawler = SiteCrawler(
        session=_Sesion(sitio), spider=_Spider(cuantas),
        signal_extractor=_SinSitemap(), page_repo=repo,
    )
    resumen = await crawler.crawl_site(sitio.id)
    return resumen, repo


@pytest.mark.asyncio
async def test_el_menu_repetido_no_queda_en_ninguna_pagina():
    """Sin declarar ningún selector: se reconoce por repetición."""
    _resumen, repo = await _rastrear()

    for pagina in repo.paginas.values():
        assert _MENU not in pagina.markdown_content
        assert _PIE not in pagina.markdown_content


@pytest.mark.asyncio
async def test_el_contenido_propio_de_cada_pagina_se_conserva():
    _resumen, repo = await _rastrear()

    guardadas = list(repo.paginas.values())
    assert all("Contingut propi" in p.markdown_content for p in guardadas)
    # Y cada una conserva el suyo, no el de otra.
    assert "numero 3" in repo.paginas[f"{_RAIZ}p3/"].markdown_content


@pytest.mark.asyncio
async def test_el_resumen_dice_cuanta_plantilla_se_ha_quitado():
    """Sin cifras no se puede juzgar si el recorte merece la pena ni notar que dejó de funcionar."""
    resumen, _repo = await _rastrear()

    assert resumen.boilerplate_blocks >= 2
    assert resumen.pages_trimmed == 8
    assert resumen.boilerplate_chars_removed > 8 * len(_MENU)


@pytest.mark.asyncio
async def test_el_recuento_de_tokens_se_recalcula_con_el_texto_recortado():
    """Si no, `thin` seguiría midiendo el menú y el umbral no significaría nada."""
    _resumen, repo = await _rastrear()

    pagina = repo.paginas[f"{_RAIZ}p1/"]
    assert pagina.token_count is not None
    assert pagina.token_count < 40


@pytest.mark.asyncio
async def test_con_el_selector_de_contenido_declarado_el_recorte_es_el_mismo_o_mejor():
    """`main` quita el menú antes de guardar; la repetición ya no tiene nada que hacer."""
    _resumen, repo = await _rastrear(config={"content_selector": "main"})

    for pagina in repo.paginas.values():
        assert _MENU not in pagina.markdown_content
        assert "Contingut propi" in pagina.markdown_content


@pytest.mark.asyncio
async def test_un_sitio_de_tres_paginas_no_se_recorta_por_repeticion():
    """Con tan pocas páginas, lo repetido puede ser contenido: no se concluye nada."""
    _resumen, repo = await _rastrear(cuantas=3)

    assert any(_MENU in p.markdown_content for p in repo.paginas.values())
