"""Tests TDD — CrawlSignalExtractor (Prompt 9Q.2).

Señales baratas extraídas durante el crawl: cabeceras HTTP (Last-Modified/ETag),
<link rel="canonical">, año de contenido y diff de sitemap.lastmod.

Puros: no tocan BD.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest


def _extractor():
    from server.app.modules.curation.signal_extractor import (
        CrawlSignalExtractor,
    )

    return CrawlSignalExtractor()


# ---------------------------------------------------------------------------
# extract_from_headers — RFC 7231 Last-Modified + ETag
# ---------------------------------------------------------------------------


class TestExtractFromHeaders:

    def test_parses_valid_last_modified_rfc7231(self) -> None:
        headers = {"Last-Modified": "Wed, 21 Oct 2015 07:28:00 GMT", "ETag": '"abc123"'}
        out = _extractor().extract_from_headers(headers)

        assert out["http_etag"] == '"abc123"'
        lm = out["http_last_modified"]
        assert isinstance(lm, datetime)
        assert lm.tzinfo is not None
        assert (lm.year, lm.month, lm.day) == (2015, 10, 21)

    def test_missing_headers_yield_none(self) -> None:
        out = _extractor().extract_from_headers({})
        assert out["http_last_modified"] is None
        assert out["http_etag"] is None

    def test_malformed_last_modified_is_tolerated(self) -> None:
        headers = {"Last-Modified": "no-es-una-fecha"}
        out = _extractor().extract_from_headers(headers)
        assert out["http_last_modified"] is None

    def test_header_lookup_is_case_insensitive(self) -> None:
        headers = {"last-modified": "Wed, 21 Oct 2015 07:28:00 GMT", "etag": '"z"'}
        out = _extractor().extract_from_headers(headers)
        assert out["http_last_modified"] is not None
        assert out["http_etag"] == '"z"'


# ---------------------------------------------------------------------------
# extract_canonical — <link rel="canonical">
# ---------------------------------------------------------------------------


class TestExtractCanonical:

    def test_extracts_canonical_href(self) -> None:
        html = (
            '<html><head>'
            '<link rel="canonical" href="https://uji.es/tramites/becas"/>'
            '</head><body>x</body></html>'
        )
        assert _extractor().extract_canonical(html) == "https://uji.es/tramites/becas"

    def test_first_canonical_wins(self) -> None:
        html = (
            '<link rel="canonical" href="https://uji.es/a">'
            '<link rel="canonical" href="https://uji.es/b">'
        )
        assert _extractor().extract_canonical(html) == "https://uji.es/a"

    def test_no_canonical_returns_none(self) -> None:
        html = "<html><head><title>Sin canonical</title></head></html>"
        assert _extractor().extract_canonical(html) is None


# ---------------------------------------------------------------------------
# extract_content_year — año en path > año plausible en texto
# ---------------------------------------------------------------------------


class TestExtractContentYear:

    def test_year_in_path_wins_over_text(self) -> None:
        url = "https://uji.es/normativa/2024/resolucion"
        text = "Publicado originalmente en 1999 y revisado."
        assert _extractor().extract_content_year(url, text) == 2024

    def test_most_recent_plausible_year_in_text_when_no_path_year(self) -> None:
        url = "https://uji.es/normativa/resolucion"
        text = "Versión de 2018, actualizada parcialmente en 2021 respecto a 1995."
        assert _extractor().extract_content_year(url, text) == 2021

    def test_no_year_returns_none(self) -> None:
        url = "https://uji.es/contacto"
        text = "Información de contacto del servicio."
        assert _extractor().extract_content_year(url, text) is None

    def test_absurd_years_discarded(self) -> None:
        url = "https://uji.es/articulo/12345"
        text = "Referencia al año 1066 y al código 9999."
        assert _extractor().extract_content_year(url, text) is None


# ---------------------------------------------------------------------------
# fetch_sitemap — XML simple + sitemap index + ausente
# ---------------------------------------------------------------------------


_SIMPLE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://uji.es/a</loc><lastmod>2024-01-15</lastmod></url>
  <url><loc>https://uji.es/b</loc><lastmod>2023-11-02T10:30:00+00:00</lastmod></url>
  <url><loc>https://uji.es/c</loc></url>
</urlset>
"""

_SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://uji.es/sitemap-1.xml</loc></sitemap>
  <sitemap><loc>https://uji.es/sitemap-2.xml</loc></sitemap>
</sitemapindex>
"""

_CHILD_1 = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://uji.es/x</loc><lastmod>2025-02-01</lastmod></url>
</urlset>
"""

_CHILD_2 = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://uji.es/y</loc><lastmod>2022-06-06</lastmod></url>
</urlset>
"""


class TestFetchSitemap:

    @pytest.mark.asyncio
    async def test_parses_simple_sitemap(self) -> None:
        async def fetch_fn(url: str) -> str:
            return _SIMPLE_SITEMAP

        out = await _extractor().fetch_sitemap("https://uji.es/sitemap.xml", fetch_fn)

        assert set(out.keys()) == {"https://uji.es/a", "https://uji.es/b", "https://uji.es/c"}
        assert out["https://uji.es/a"] == datetime(2024, 1, 15, tzinfo=timezone.utc)
        assert out["https://uji.es/b"] == datetime(2023, 11, 2, 10, 30, tzinfo=timezone.utc)
        assert out["https://uji.es/c"] is None

    @pytest.mark.asyncio
    async def test_follows_sitemap_index(self) -> None:
        bodies = {
            "https://uji.es/sitemap.xml": _SITEMAP_INDEX,
            "https://uji.es/sitemap-1.xml": _CHILD_1,
            "https://uji.es/sitemap-2.xml": _CHILD_2,
        }

        async def fetch_fn(url: str) -> str:
            return bodies[url]

        out = await _extractor().fetch_sitemap("https://uji.es/sitemap.xml", fetch_fn)

        assert set(out.keys()) == {"https://uji.es/x", "https://uji.es/y"}
        assert out["https://uji.es/x"] == datetime(2025, 2, 1, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_derives_sitemap_url_from_base(self) -> None:
        seen: list[str] = []

        async def fetch_fn(url: str) -> str:
            seen.append(url)
            return _SIMPLE_SITEMAP

        await _extractor().fetch_sitemap("https://uji.es", fetch_fn)
        assert seen[0] == "https://uji.es/sitemap.xml"

    @pytest.mark.asyncio
    async def test_missing_or_unparseable_sitemap_returns_empty(self) -> None:
        async def fail_fetch(url: str) -> str:
            raise RuntimeError("404 Not Found")

        async def garbage_fetch(url: str) -> str:
            return "esto no es xml <<<"

        assert await _extractor().fetch_sitemap("https://uji.es", fail_fetch) == {}
        assert await _extractor().fetch_sitemap("https://uji.es", garbage_fetch) == {}
