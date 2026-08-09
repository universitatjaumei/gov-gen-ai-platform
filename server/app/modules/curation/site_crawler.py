"""Crawl de sitio entero + diff de sitemap (9Q.2).

Deploy: edge.

Orquesta el rastreo de un HubWebSite: une las URLs descubiertas por el spider con
las del sitemap, hace upsert de cada página con sus señales de frescura y calcula el
diff (nuevas / cambiadas / desaparecidas). El cloud orquesta, el edge ejecuta.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from server.app.modules.agents_hub.services.language_detector import detect_language
from server.app.modules.agents_hub.database.operational_models import HubWebSite
from server.app.modules.agents_hub.ingestion.hasher import hash_content
from server.app.modules.agents_hub.ingestion.markdown_utils import (
    estimate_tokens,
    extract_title_from_markdown,
)


@dataclass
class SiteCrawlSummary:
    """Resultado de un crawl de sitio. Insumo del job de calidad (9Q.5)."""

    pages_new: int = 0
    pages_changed: int = 0
    pages_gone: int = 0
    pages_error: int = 0
    pages_total: int = 0
    errors: list[str] = field(default_factory=list)
    # IDs de páginas del diff — usados por SiteQualityAnalysisJob para auto-ingesta (9Q.5)
    new_page_ids: list[uuid.UUID] = field(default_factory=list)
    changed_page_ids: list[uuid.UUID] = field(default_factory=list)
    gone_page_ids: list[uuid.UUID] = field(default_factory=list)


class _Spider(Protocol):
    async def crawl(self, source: Any) -> Any: ...
    async def _fetch(self, url: str) -> tuple[str, dict]: ...


class _SignalExtractor(Protocol):
    def extract_from_headers(self, headers: dict) -> dict: ...
    def extract_canonical(self, html: str) -> str | None: ...
    def extract_content_year(self, url: str, text: str) -> int | None: ...
    async def fetch_sitemap(self, url: str, fetch_fn: Any) -> dict: ...


class _PageRepo(Protocol):
    async def upsert(self, *, site_id: uuid.UUID, url: str, **fields: Any) -> Any: ...
    async def list_by_site(self, site_id: uuid.UUID, status: str | None = ...) -> list: ...
    async def mark_gone(self, page_ids: list[uuid.UUID]) -> int: ...


class SiteCrawler:
    """Rastrea un sitio completo y materializa el diff sobre HubCrawledPage."""

    def __init__(
        self,
        session: Any,
        spider: _Spider,
        signal_extractor: _SignalExtractor,
        page_repo: _PageRepo,
    ) -> None:
        self._session = session
        self._spider = spider
        self._signals = signal_extractor
        self._pages = page_repo

    async def crawl_site(self, site_id: uuid.UUID) -> SiteCrawlSummary:
        site = await self._session.get(HubWebSite, site_id)
        if site is None:
            return SiteCrawlSummary(errors=[f"site {site_id} not found"])

        now = datetime.now(timezone.utc)

        # 1. Conjunto de URLs objetivo: unión(sitemap, enlaces descubiertos por el spider).
        try:
            target_urls, sitemap_map = await self._discover_urls(site)
        except Exception as exc:  # fallo global del crawl → el sitio queda en error
            site.status = "error"
            site.error_message = str(exc)
            await self._session.flush()
            return SiteCrawlSummary(errors=[str(exc)])

        # Estado previo para el diff.
        existing_pages = await self._pages.list_by_site(site_id, status="active")
        existing_by_url = {p.url: p for p in existing_pages}

        summary = SiteCrawlSummary(pages_total=len(target_urls))
        seen_urls: set[str] = set()

        # 2. Por cada URL: fetch + señales + upsert. Un fallo de página no aborta el crawl.
        for url in sorted(target_urls):
            seen_urls.add(url)
            try:
                body, headers = await self._spider._fetch(url)
            except Exception as exc:
                await self._pages.upsert(
                    site_id=site_id,
                    url=url,
                    status="error",
                    error_message=str(exc),
                    last_crawled_at=now,
                )
                summary.pages_error += 1
                continue

            content_hash = hash_content(body)
            prev = existing_by_url.get(url)
            # Capturar el hash previo ANTES del upsert: el repo puede devolver el
            # mismo objeto identity-mapped y mutarlo, invalidando la comparación.
            prev_hash = prev.content_hash if prev is not None else None

            upserted = await self._pages.upsert(
                site_id=site_id,
                url=url,
                last_crawled_at=now,
                status="active",
                error_message=None,
                sitemap_lastmod=sitemap_map.get(url),
                **self._page_fields(url, body, headers),
                content_hash=content_hash,
            )

            # 3. Diff de sitemap: alta / cambio.
            if prev is None:
                summary.pages_new += 1
                summary.new_page_ids.append(upserted.id)
            elif prev_hash != content_hash:
                summary.pages_changed += 1
                summary.changed_page_ids.append(upserted.id)

        # 3. Diff de sitemap: bajas (páginas activas que ya no aparecen).
        gone_ids = [p.id for p in existing_pages if p.url not in seen_urls]
        if gone_ids:
            summary.pages_gone = await self._pages.mark_gone(gone_ids)
            summary.gone_page_ids = gone_ids

        # 4. Cierre del sitio.
        site.last_crawled_at = now
        site.status = "active"
        site.error_message = None
        await self._session.flush()

        return summary

    async def _discover_urls(
        self, site: HubWebSite
    ) -> tuple[set[str], dict[str, datetime | None]]:
        """Unión de URLs del spider y del sitemap; devuelve también el mapa de lastmod."""
        crawl_result = await self._spider.crawl(site)
        discovered = set(crawl_result.crawled_urls)

        async def _fetch_text(u: str) -> str:
            body, _headers = await self._spider._fetch(u)
            return body

        sitemap_map = await self._signals.fetch_sitemap(
            site.sitemap_url or site.root_url, _fetch_text
        )
        return discovered | set(sitemap_map.keys()), sitemap_map

    def _page_fields(self, url: str, body: str, headers: dict) -> dict[str, Any]:
        """Campos de contenido + señales para el upsert de una página."""
        header_signals = self._signals.extract_from_headers(headers)
        declared_canonical = self._signals.extract_canonical(body)
        return {
            "markdown_content": body,
            "title": extract_title_from_markdown(body),
            "token_count": estimate_tokens(body),
            "language": detect_language(body),
            "http_last_modified": header_signals["http_last_modified"],
            "http_etag": header_signals["http_etag"],
            "declared_canonical_url": declared_canonical,
            "canonical_url": declared_canonical or url,
            "content_year": self._signals.extract_content_year(url, body),
        }
