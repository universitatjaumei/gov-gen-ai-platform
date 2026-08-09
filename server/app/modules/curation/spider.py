"""Spider genérico BFS con control de profundidad, filtros regex y límite de páginas.

Deploy: edge
"""

import re
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Protocol
from urllib.parse import urljoin, urlparse


class CrawlStatus(Enum):
    COMPLETED = "completed"
    COMPLETED_PARTIAL = "completed_partial"


@dataclass
class CrawlResult:
    crawled_urls: list[str]
    pages_crawled: int
    pages_skipped: int
    status: CrawlStatus


class _WebSource(Protocol):
    url: str
    config_json: dict


class GenericSpider:
    """Spider BFS que respeta crawl_depth, url_regex_filter y max_pages leídos de config_json."""

    def __init__(
        self, fetch_fn: Callable[[str], Awaitable[tuple[str, dict]]] | None = None
    ) -> None:
        self._fetch_fn = fetch_fn

    async def _fetch(self, url: str) -> tuple[str, dict]:
        """Descarga una URL y devuelve (cuerpo, cabeceras HTTP)."""
        if self._fetch_fn is not None:
            return await self._fetch_fn(url)
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text, dict(resp.headers)

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        links: list[str] = []
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            href = match.group(1).strip()
            if not href or href.startswith(("mailto:", "javascript:", "#")):
                continue
            absolute = urljoin(base_url, href).split("#")[0]
            if absolute:
                links.append(absolute)
        return links

    async def crawl(self, source: _WebSource) -> CrawlResult:
        config: dict = source.config_json
        crawl_depth: int = config.get("crawl_depth", 1)
        url_regex_filter: str | None = config.get("url_regex_filter")
        max_pages: int = config.get("max_pages", 50)

        regex = re.compile(url_regex_filter) if url_regex_filter else None
        base_netloc = urlparse(source.url).netloc

        # Cola BFS: pares (url, profundidad)
        queue: deque[tuple[str, int]] = deque([(source.url, 0)])
        visited: set[str] = {source.url}

        crawled_urls: list[str] = []
        pages_skipped = 0

        while queue:
            if len(crawled_urls) >= max_pages:
                pages_skipped += len(queue)
                break

            url, depth = queue.popleft()
            html, _headers = await self._fetch(url)
            crawled_urls.append(url)

            # No encolar hijos si hemos alcanzado la profundidad máxima
            if depth >= crawl_depth:
                continue

            for link in self._extract_links(html, url):
                if link in visited:
                    continue
                if urlparse(link).netloc != base_netloc:
                    continue
                if regex and not regex.search(link):
                    continue
                visited.add(link)
                queue.append((link, depth + 1))

        status = (
            CrawlStatus.COMPLETED_PARTIAL if pages_skipped > 0 else CrawlStatus.COMPLETED
        )
        return CrawlResult(
            crawled_urls=crawled_urls,
            pages_crawled=len(crawled_urls),
            pages_skipped=pages_skipped,
            status=status,
        )
