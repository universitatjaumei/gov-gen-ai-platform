"""Crawl de sitio entero + diff de sitemap (9Q.2).

Deploy: edge.

Orquesta el rastreo de un HubWebSite: une las URLs descubiertas por el spider con
las del sitemap, hace upsert de cada página con sus señales de frescura y calcula el
diff (nuevas / cambiadas / desaparecidas). El cloud orquesta, el edge ejecuta.
"""
from __future__ import annotations

import logging
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
from server.app.modules.curation.contenido_web import parece_html, texto_visible, titulo_de
from server.app.modules.curation.cortesia import RutaProhibidaPorRobots, clasificar_fallo
from server.app.modules.curation.sondeo_dinamico import senales_de_dinamismo


_log = logging.getLogger(__name__)

#: Lo que se guarda de la cola para reanudar. Con URLs de ~120 caracteres, cinco mil son unos
#: 600 KB de JSON en la fila del sitio: suficiente para un apartado y acotado para un portal.
_MAX_COLA_GUARDADA = 5_000
_MAX_VISITADAS_GUARDADAS = 20_000


@dataclass
class SiteCrawlSummary:
    """Resultado de un crawl de sitio. Insumo del job de calidad (9Q.5)."""

    pages_new: int = 0
    pages_changed: int = 0
    pages_gone: int = 0
    pages_error: int = 0
    pages_total: int = 0
    errors: list[str] = field(default_factory=list)
    #: El rastreo no vio el sitio entero (RAS.1). Mientras sea `True`, **no se declaran bajas**:
    #: una página no visitada no es una página desaparecida.
    truncated: bool = False
    stop_reason: str | None = None
    pages_pending: int = 0
    #: URLs que el `robots.txt` del sitio excluye. No son errores.
    pages_forbidden: int = 0
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
            target_urls, sitemap_map, recorrido = await self._discover_urls(site)
        except Exception as exc:  # fallo global del crawl → el sitio queda en error
            site.status = "error"
            site.error_message = str(exc)
            await self._session.flush()
            return SiteCrawlSummary(errors=[str(exc)])

        # Estado previo para el diff.
        existing_pages = await self._pages.list_by_site(site_id, status="active")
        existing_by_url = {p.url: p for p in existing_pages}

        summary = SiteCrawlSummary(pages_total=len(target_urls))
        # El recorrido del spider ya puede venir truncado por páginas o por presupuesto de
        # tiempo (RAS.1). Eso viaja hasta aquí porque cambia lo que se puede concluir.
        summary.truncated = getattr(recorrido, "stop_reason", None) is not None
        summary.stop_reason = getattr(recorrido, "stop_reason", None)
        summary.pages_pending = getattr(recorrido, "pages_skipped", 0) if summary.truncated else 0
        summary.pages_forbidden = getattr(recorrido, "urls_prohibidas", 0)
        seen_urls: set[str] = set()

        # 2. Por cada URL: fetch + señales + upsert. Un fallo de página no aborta el crawl.
        for url in sorted(target_urls):
            seen_urls.add(url)
            try:
                body, headers = await self._spider._fetch(url)
            except RutaProhibidaPorRobots:
                # El servidor ha dicho que no. No es un error de la página, así que no se
                # registra como tal: contarlo como error la acusaría de estar rota.
                summary.pages_forbidden += 1
                seen_urls.discard(url)
                summary.truncated = True
                summary.stop_reason = summary.stop_reason or "robots"
                continue
            except Exception as exc:
                # RAS.3 — un 404 y un `timeout` no dicen lo mismo: el primero es una respuesta
                # («esto ya no está», información útil) y el segundo un fallo del que no se
                # puede concluir nada sobre la página. Los dos producían el mismo hallazgo
                # crítico, así que un rastreo con mala red llenaba el informe de acusaciones.
                causa = getattr(exc, "causa", exc)
                await self._pages.upsert(
                    site_id=site_id,
                    url=url,
                    status="error",
                    error_message=str(exc),
                    error_kind=clasificar_fallo(causa),
                    error_attempts=getattr(exc, "intentos", 1),
                    last_crawled_at=now,
                )
                summary.pages_error += 1
                continue

            content_hash = hash_content(body)
            prev = existing_by_url.get(url)
            # Capturar el hash previo ANTES del upsert: el repo puede devolver el
            # mismo objeto identity-mapped y mutarlo, invalidando la comparación.
            prev_hash = prev.content_hash if prev is not None else None

            try:
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
            except Exception as exc:  # noqa: BLE001
                # Guardar una página tampoco puede tumbar el rastreo. Ocurrió en el rastreo real:
                # un PDF servido como si fuera página trajo bytes nulos, Postgres rechazó la fila
                # y el sitio quedó en error **con cero páginas**. Segunda cara del mismo patrón
                # que el enlace roto, esta vez en la escritura.
                _log.warning("No se pudo guardar %s: %s", url, exc)
                summary.pages_error += 1
                summary.errors.append(f"{url}: {exc}"[:500])
                continue

            # 3. Diff de sitemap: alta / cambio.
            if prev is None:
                summary.pages_new += 1
                summary.new_page_ids.append(upserted.id)
            elif prev_hash != content_hash:
                summary.pages_changed += 1
                summary.changed_page_ids.append(upserted.id)

        # 2.bis. Las páginas que el recorrido no pudo leer. Antes ni llegaban aquí: la excepción
        # tumbaba el rastreo entero. Se registran con su causa —un 404 es contenido que ya no
        # está, y eso es lo que hay que depurar— y se cuentan como vistas para que no se sumen
        # además como bajas.
        for fallo in getattr(recorrido, "fallos", None) or []:
            url = fallo.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            await self._pages.upsert(
                site_id=site_id,
                url=url,
                status="error",
                error_message=fallo.get("message", ""),
                error_kind=fallo.get("kind"),
                error_attempts=fallo.get("attempts", 1),
                last_crawled_at=now,
            )
            summary.pages_error += 1

        # 3. Diff de sitemap: bajas (páginas activas que ya no aparecen).
        #
        # Sólo si el rastreo vio el sitio entero. Con un rastreo truncado —por `max_pages`, por
        # presupuesto de tiempo o porque el `robots.txt` excluye parte— «no apareció» significa
        # «no se llegó a mirar», y una baja no es un contador: es la señal de «esto ya no está»
        # que alimenta los hallazgos y las decisiones de retirada del corpus.
        if not summary.truncated:
            gone_ids = [p.id for p in existing_pages if p.url not in seen_urls]
            if gone_ids:
                summary.pages_gone = await self._pages.mark_gone(gone_ids)
                summary.gone_page_ids = gone_ids

        # 4. Cierre del sitio, guardando la cola si quedó algo por ver (RAS.3).
        site.last_crawled_at = now
        site.status = "active"
        site.error_message = None
        site.crawl_frontier = self._cola_a_guardar(recorrido, summary)
        await self._session.flush()

        return summary

    @staticmethod
    def _cola_a_guardar(recorrido: Any, summary: SiteCrawlSummary) -> dict[str, Any] | None:
        """La cola pendiente que hay que guardar, o `None` si no hay nada que reanudar.

        Se acota lo que se persiste —una cola de cien mil URLs no cabe en una fila— y **se dice**
        cuánto se ha dejado fuera: un tope silencioso haría que la reanudación pareciera completa.
        """
        pendientes = list(getattr(recorrido, "frontier", None) or [])
        if not pendientes:
            return None

        visitadas = list(getattr(recorrido, "visited", None) or [])
        recortadas = max(0, len(pendientes) - _MAX_COLA_GUARDADA)
        if recortadas:
            summary.errors.append(
                f"la cola pendiente se ha guardado recortada: {recortadas} URLs quedan fuera "
                f"de la reanudación"
            )

        return {
            "pending": [[u, d] for u, d in pendientes[:_MAX_COLA_GUARDADA]],
            "visited": visitadas[:_MAX_VISITADAS_GUARDADAS],
            "dropped": recortadas,
        }

    async def _discover_urls(
        self, site: HubWebSite
    ) -> tuple[set[str], dict[str, datetime | None], Any]:
        """Unión de URLs del spider y del sitemap; el mapa de lastmod y el recorrido en bruto."""
        crawl_result = await self._spider.crawl(site)
        discovered = set(crawl_result.crawled_urls)

        async def _fetch_text(u: str) -> str:
            body, _headers = await self._spider._fetch(u)
            return body

        sitemap_map = await self._signals.fetch_sitemap(
            site.sitemap_url or site.root_url, _fetch_text
        )
        return discovered | set(sitemap_map.keys()), sitemap_map, crawl_result

    def _page_fields(self, url: str, body: str, headers: dict) -> dict[str, Any]:
        """Campos de contenido + señales para el upsert de una página.

        RAS.2 — de una página HTML se guarda **su texto**, no su marcado: con el marcado dentro,
        `token_count` medía plantillas (51 KB de HTML para 4 KB de texto en el portal real), el
        umbral de `thin` era inalcanzable y a la ingesta del asistente llegaban `<div>`. La
        evidencia de que la página necesita un navegador se guarda aquí porque el detector corre
        después y ya no tiene el HTML.
        """
        header_signals = self._signals.extract_from_headers(headers)
        declared_canonical = self._signals.extract_canonical(body)

        es_html = parece_html(body)
        contenido = texto_visible(body) if es_html else body
        titulo = titulo_de(body) if es_html else extract_title_from_markdown(body)
        senales = [s.como_dict() for s in senales_de_dinamismo(body)] if es_html else []

        return {
            "markdown_content": contenido,
            "title": titulo,
            "token_count": estimate_tokens(contenido),
            "language": detect_language(contenido),
            "render_signals": senales,
            "http_last_modified": header_signals["http_last_modified"],
            "http_etag": header_signals["http_etag"],
            "declared_canonical_url": declared_canonical,
            "canonical_url": declared_canonical or url,
            "content_year": self._signals.extract_content_year(url, body),
        }
