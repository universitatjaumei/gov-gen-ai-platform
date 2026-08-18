"""Tests para el spider genérico con crawl_depth, regex y max_pages — TDD RED."""
import pytest
from dataclasses import dataclass, field


@dataclass
class FakeWebSource:
    """`root_url` y no `url`: es como se llama el campo en `HubWebSite` desde el renombrado
    de `HubWebSource`, y el desajuste hacía que el rastreo real fallara siempre (VER.6)."""

    root_url: str
    config_json: dict = field(default_factory=dict)


class TestGenericSpider:

    @pytest.mark.asyncio
    async def test_spider_respects_crawl_depth_zero(self) -> None:
        """Con crawl_depth=0 solo procesa la URL raíz, sin seguir ningún link."""
        from server.app.modules.curation.spider import GenericSpider

        fetched_urls: list[str] = []

        async def fake_fetch(url: str) -> tuple[str, dict]:
            fetched_urls.append(url)
            return '<html><body><a href="/pagina2">enlace</a></body></html>', {}

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            root_url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 0, "max_pages": 10},
        )
        result = await spider.crawl(source)

        # RAS.1 — la cortesía añade una petición por host, la del `robots.txt`, y es la única
        # que no es una página: se descuenta para comprobar lo que este test comprueba.
        paginas_pedidas = [u for u in fetched_urls if not u.endswith("/robots.txt")]
        assert paginas_pedidas == ["https://ejemplo.uji.es"]
        assert result.pages_crawled == 1

    @pytest.mark.asyncio
    async def test_spider_respects_crawl_depth_one(self) -> None:
        """Con crawl_depth=1 procesa raíz + links de primer nivel, sin bajar más."""
        from server.app.modules.curation.spider import GenericSpider

        pages = {
            "https://ejemplo.uji.es": '<html><a href="/a">A</a><a href="/b">B</a></html>',
            "https://ejemplo.uji.es/a": '<html><a href="/c">C</a></html>',
            "https://ejemplo.uji.es/b": "<html>contenido b</html>",
        }

        async def fake_fetch(url: str) -> tuple[str, dict]:
            return pages.get(url, "<html></html>"), {}

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            root_url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "max_pages": 50},
        )
        result = await spider.crawl(source)

        crawled = set(result.crawled_urls)
        assert "https://ejemplo.uji.es" in crawled
        assert "https://ejemplo.uji.es/a" in crawled
        assert "https://ejemplo.uji.es/b" in crawled
        assert "https://ejemplo.uji.es/c" not in crawled  # nivel 2, no debe llegar

    @pytest.mark.asyncio
    async def test_spider_url_regex_filter_excludes_non_matching_urls(self) -> None:
        """Con url_regex_filter, solo se indexan las URLs que machan la expresión."""
        from server.app.modules.curation.spider import GenericSpider

        pages = {
            "https://ejemplo.uji.es": (
                '<html><a href="/normativa/ley1">Ley</a>'
                '<a href="/noticias/nota">Noticia</a></html>'
            ),
            "https://ejemplo.uji.es/normativa/ley1": "<html>normativa</html>",
            "https://ejemplo.uji.es/noticias/nota": "<html>noticia</html>",
        }

        async def fake_fetch(url: str) -> tuple[str, dict]:
            return pages.get(url, "<html></html>"), {}

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            root_url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "url_regex_filter": r"/normativa/", "max_pages": 50},
        )
        result = await spider.crawl(source)

        assert "https://ejemplo.uji.es/normativa/ley1" in result.crawled_urls
        assert "https://ejemplo.uji.es/noticias/nota" not in result.crawled_urls

    @pytest.mark.asyncio
    async def test_spider_stops_at_max_pages_and_marks_partial(self) -> None:
        """Al alcanzar max_pages, el resultado se marca COMPLETED_PARTIAL."""
        from server.app.modules.curation.spider import GenericSpider, CrawlStatus

        async def fake_fetch(url: str) -> tuple[str, dict]:
            links = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(20))
            return f"<html>{links}</html>", {}

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            root_url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 2, "max_pages": 3},
        )
        result = await spider.crawl(source)

        assert result.pages_crawled <= 3
        assert result.status == CrawlStatus.COMPLETED_PARTIAL
        assert result.pages_skipped > 0

    @pytest.mark.asyncio
    async def test_spider_does_not_revisit_urls(self) -> None:
        """Una URL no se procesa dos veces aunque aparezca en múltiples páginas."""
        from server.app.modules.curation.spider import GenericSpider

        call_counts: dict[str, int] = {}

        async def fake_fetch(url: str) -> tuple[str, dict]:
            call_counts[url] = call_counts.get(url, 0) + 1
            return '<html><a href="https://ejemplo.uji.es">inicio</a></html>', {}

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            root_url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "max_pages": 10},
        )
        await spider.crawl(source)

        assert call_counts.get("https://ejemplo.uji.es", 0) == 1
