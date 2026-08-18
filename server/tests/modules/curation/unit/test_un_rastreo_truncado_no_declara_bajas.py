"""Un rastreo truncado no puede decir que las páginas que no vio han desaparecido (RAS.1).

`SiteCrawler` calcula las bajas como «páginas activas que no aparecen en este rastreo». Es correcto
cuando el rastreo ha visto el sitio entero, y **falso** en cuanto se trunca: al alcanzar `max_pages`
—o el presupuesto de tiempo que añade RAS.1— las páginas no visitadas pasarían a `gone` sin que nada
haya cambiado en el sitio.

En el módulo de curación eso no es un contador equivocado: una baja es la señal de «esto ya no
está» que alimenta los hallazgos y las decisiones de retirada del corpus. Un rastreo grande contra un
portal real se trunca casi siempre, así que la primera pasada declararía cientos de bajas falsas.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from server.app.modules.curation.spider import CrawlResult, CrawlStatus
from server.app.modules.curation.site_crawler import SiteCrawler


@dataclass
class _Pagina:
    id: uuid.UUID
    url: str
    content_hash: str | None = "viejo"
    status: str = "active"


class _RepoDePaginas:
    def __init__(self, existentes: list[_Pagina]) -> None:
        self.existentes = existentes
        self.marcadas_como_ida: list[uuid.UUID] = []

    async def upsert(self, *, site_id: uuid.UUID, url: str, **campos: Any) -> Any:
        return _Pagina(id=uuid.uuid4(), url=url)

    async def list_by_site(self, site_id: uuid.UUID, status: str | None = None) -> list:
        return list(self.existentes)

    async def mark_gone(self, page_ids: list[uuid.UUID]) -> int:
        self.marcadas_como_ida.extend(page_ids)
        return len(page_ids)


@dataclass
class _SitioFalso:
    id: uuid.UUID
    root_url: str = "https://www.uji.es"
    sitemap_url: str | None = None
    config_json: dict = field(default_factory=dict)
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


class _SpiderQueTrunca:
    def __init__(self, urls: list[str], status: CrawlStatus, stop_reason: str | None) -> None:
        self._urls = urls
        self._status = status
        self._stop_reason = stop_reason

    async def crawl(self, source: Any) -> CrawlResult:
        return CrawlResult(
            crawled_urls=list(self._urls),
            pages_crawled=len(self._urls),
            pages_skipped=40 if self._stop_reason else 0,
            status=self._status,
            stop_reason=self._stop_reason,
        )

    async def _fetch(self, url: str) -> tuple[str, dict]:
        return "<html>contenido</html>", {}


class _SinSitemap:
    def extract_from_headers(self, headers: dict) -> dict:
        return {"http_last_modified": None, "http_etag": None}

    def extract_canonical(self, html: str) -> str | None:
        return None

    def extract_content_year(self, url: str, text: str) -> int | None:
        return None

    async def fetch_sitemap(self, url: str, fetch_fn: Any) -> dict:
        return {}


async def _rastrear(*, status: CrawlStatus, stop_reason: str | None):
    antigua = _Pagina(id=uuid.uuid4(), url="https://www.uji.es/pagina-no-visitada")
    repo = _RepoDePaginas([antigua])
    sitio = _SitioFalso(id=uuid.uuid4())
    crawler = SiteCrawler(
        session=_Sesion(sitio),
        spider=_SpiderQueTrunca(["https://www.uji.es/visitada"], status, stop_reason),
        signal_extractor=_SinSitemap(),
        page_repo=repo,
    )
    resumen = await crawler.crawl_site(sitio.id)
    return resumen, repo, antigua


@pytest.mark.asyncio
async def test_un_rastreo_truncado_no_marca_bajas():
    resumen, repo, antigua = await _rastrear(
        status=CrawlStatus.COMPLETED_PARTIAL, stop_reason="max_pages"
    )

    assert repo.marcadas_como_ida == [], "declaró desaparecida una página que no llegó a visitar"
    assert resumen.pages_gone == 0


@pytest.mark.asyncio
async def test_un_rastreo_truncado_dice_que_no_ha_comprobado_las_bajas():
    """Callarlo dejaría un informe que parece completo. El motivo del truncado también consta."""
    resumen, _repo, _antigua = await _rastrear(
        status=CrawlStatus.COMPLETED_PARTIAL, stop_reason="time_budget"
    )

    assert resumen.truncated is True
    assert resumen.stop_reason == "time_budget"
    assert resumen.pages_pending == 40


@pytest.mark.asyncio
async def test_un_rastreo_completo_si_marca_las_bajas():
    resumen, repo, antigua = await _rastrear(status=CrawlStatus.COMPLETED, stop_reason=None)

    assert repo.marcadas_como_ida == [antigua.id]
    assert resumen.pages_gone == 1
    assert resumen.truncated is False
