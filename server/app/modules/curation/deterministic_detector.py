"""Detector determinista de calidad de contenido web — primera pasada sin LLM (9Q.3).

Deploy: edge.

Detecta sobre todo el sitio: páginas vacías/finas, stale, con error de crawl,
huérfanas (gone + documento aún ingerido) y supersesión temporal por patrón de URL + fecha.
Solo emite hallazgos vía ContentFindingRepo.upsert; NO muta HubCrawledPage.superseded
(eso lo hace el job 9Q.5 al consolidar).
"""
from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

from server.app.modules.curation.contracts import ContentFinding

_YEAR_SEG = re.compile(r"/((?:19|20)\d{2})(?=/|$)")

#: Qué se puede afirmar según la causa del fallo de rastreo (RAS.3). Lo que no se clasificó —las
#: páginas rastreadas antes de esto— conserva la severidad de antes: no se le atribuye una causa.
_SEVERIDAD_DEL_ERROR: dict[str | None, str] = {
    "not_found": "warning",     # el enlace apunta a algo que ya no está: hay que depurarlo
    "client_error": "warning",  # 403, 401: el servidor contesta, pero no sirve la página
    "transient": "info",        # red o servidor caído: no dice nada de la página
}


def _strip_year_segments(path: str) -> str:
    """Quita todos los segmentos de año de un path URL."""
    normalized = _YEAR_SEG.sub("", path)
    return normalized.rstrip("/") or "/"


def _identidad_de_pagina(url: str) -> str:
    """La URL sin los parámetros que sólo son navegación (RAS.5).

    El conmutador de idioma del portal genera variantes de cada página que llevan la URL actual
    dentro (`?urlRedirect=…&url=…`). Sin quitarlas, todas comparten path y el agrupador las tomaba
    por versiones de un mismo recurso: 107 supersesiones falsas sobre una sola página.
    """
    from server.app.modules.curation.spider import url_de_pagina

    return url_de_pagina(url) or url


def _process_key(canonical_url: str | None, url: str) -> str:
    """Clave de proceso para agrupar versiones temporales de un mismo recurso.

    Solo participa en la agrupación si la URL contiene un segmento de año
    explícito (/2023/, /2024/…). URLs sin año reciben una clave única que
    no colisiona con ninguna versión con año del mismo path.
    """
    base = _identidad_de_pagina(canonical_url or url)
    parsed = urlparse(base)
    path = parsed.path
    if not _YEAR_SEG.search(path):
        # Sin año en la URL: clave única, no participa en grupos de supersesión.
        #
        # RAS.5 — decía «única» y no lo era: sólo llevaba el path, así que `http://…/normestudi/`
        # y `https://…/normestudi/` —la misma página servida por los dos esquemas— caían en el
        # mismo grupo y una salía «superseded» por la otra. 191 avisos falsos en el primer
        # rastreo real. Con el esquema y el host dentro, dos URLs distintas nunca se agrupan si
        # no comparten un año.
        return f"__no_year__{parsed.scheme}://{parsed.netloc}{path.rstrip('/') or '/'}"
    return _strip_year_segments(path)


def _effective_date(page: Any, now: datetime) -> datetime:
    """Fecha efectiva más reciente disponible para ordenar versiones."""
    candidates: list[datetime] = []
    if page.sitemap_lastmod:
        candidates.append(page.sitemap_lastmod)
    if page.http_last_modified:
        candidates.append(page.http_last_modified)
    if page.content_year:
        candidates.append(datetime(page.content_year, 1, 1, tzinfo=timezone.utc))
    if hasattr(page, "first_seen_at") and page.first_seen_at:
        candidates.append(page.first_seen_at)
    return max(candidates) if candidates else datetime.min.replace(tzinfo=timezone.utc)


def _content_date(page: Any) -> tuple[datetime | None, str | None]:
    """Fecha de contenido para evaluar `stale`, y **de dónde sale** (RAS.5).

    Un año mencionado en el texto **no es** una fecha de publicación. Medido en el primer rastreo
    real: el portal no declara `Last-Modified`, ni `ETag`, ni publica `sitemap.xml`, así que la
    fecha salía del año más reciente citado en el cuerpo —una página menciona 1925, 2010, 2016,
    2021, 2024 y 2071— y eso marcaba como antiguas **303 de 400 páginas**. Un año en la URL sí es
    una señal del portal: así versiona sus documentos (`/2019/`, `/pext/19-20/`).
    """
    if page.sitemap_lastmod:
        return page.sitemap_lastmod, "sitemap_lastmod"
    if page.http_last_modified:
        return page.http_last_modified, "http_last_modified"
    if page.content_year and _YEAR_SEG.search(urlparse(page.url or "").path):
        return datetime(page.content_year, 1, 1, tzinfo=timezone.utc), "url_year"
    return None, None


class DeterministicQualityDetector:
    """Emite hallazgos deterministas sobre las páginas de un sitio."""

    def __init__(
        self,
        session: Any,
        *,
        finding_repo: Any,
        thin_token_threshold: int = 120,
        stale_days: int = 365,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repo = finding_repo
        self._thin_threshold = thin_token_threshold
        self._stale_days = stale_days
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    async def analyze(self, site_id: uuid.UUID) -> list[ContentFinding]:
        from server.app.modules.agents_hub.database.operational_models import (
            HubCrawledPage,
            HubDocument,
        )
        from sqlalchemy import select

        now = self._now_fn()
        findings: list[ContentFinding] = []

        # Cargar todas las páginas del sitio
        stmt = select(HubCrawledPage).where(HubCrawledPage.site_id == site_id)
        stmt._model_hint = "page"  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        pages: list = result.scalars().all()

        # Cargar documentos ingeridos cuyo crawled_page_id apunte a páginas gone
        gone_ids = {p.id for p in pages if p.status == "gone"}
        orphan_page_ids: set[uuid.UUID] = set()
        if gone_ids:
            doc_stmt = select(HubDocument).where(HubDocument.crawled_page_id.in_(gone_ids))
            doc_stmt._model_hint = "document"  # type: ignore[attr-defined]
            doc_result = await self._session.execute(doc_stmt)
            for doc in doc_result.scalars().all():
                orphan_page_ids.add(doc.crawled_page_id)

        # Primera pasada: reglas por página
        for page in pages:
            page_findings = await self._check_page(page, site_id, now, orphan_page_ids)
            for f in page_findings:
                await self._repo.upsert(f)
                findings.append(f)

        # Segunda pasada: supersesión (necesita todas las páginas)
        for f in await self._check_superseded(pages, site_id, now):
            await self._repo.upsert(f)
            findings.append(f)

        return findings

    async def _check_page(
        self,
        page: Any,
        site_id: uuid.UUID,
        now: datetime,
        orphan_page_ids: set[uuid.UUID],
    ) -> list[ContentFinding]:
        results: list[ContentFinding] = []

        # RAS.5 — una página que no se pudo descargar no tiene contenido **porque no se leyó**, y
        # eso ya lo dice `crawl_error`. En el primer rastreo real, los tres 404 salían además como
        # `empty` **crítico**: dos afirmaciones sobre el mismo hecho, y la segunda falsa.
        if page.status == "error":
            return self._otros_hallazgos(page, site_id, now, orphan_page_ids)

        empty = (
            page.markdown_content is None
            or not page.markdown_content.strip()
            or page.token_count == 0
        )

        # RAS.2 — si la página no se pudo leer sin renderizar, ni «vacía» ni «pobre» son
        # afirmaciones sostenibles: las dos hablan de la página, y lo que pasó es que el
        # rastreador no la vio. Lo único cierto es que hace falta un navegador para leerla.
        senales_de_render = list(getattr(page, "render_signals", None) or [])
        if senales_de_render and (
            empty
            or (page.token_count is not None and page.token_count < self._thin_threshold)
        ):
            return [self._finding(
                site_id=site_id,
                finding_type="needs_javascript",
                severity="warning",
                confidence=1.0,
                page_id=page.id,
                source_url=page.url,
                signal={"render_signals": senales_de_render,
                        "token_count": page.token_count},
                now=now,
            )] + self._otros_hallazgos(page, site_id, now, orphan_page_ids)

        if empty:
            results.append(self._finding(
                site_id=site_id,
                finding_type="empty",
                severity="critical",
                confidence=1.0,
                page_id=page.id,
                source_url=page.url,
                signal={},
                now=now,
            ))
        elif page.token_count is not None and page.token_count < self._thin_threshold:
            results.append(self._finding(
                site_id=site_id,
                finding_type="thin",
                severity="warning",
                confidence=1.0,
                page_id=page.id,
                source_url=page.url,
                signal={"token_count": page.token_count, "threshold": self._thin_threshold},
                now=now,
            ))

        results.extend(self._otros_hallazgos(page, site_id, now, orphan_page_ids))
        return results

    def _otros_hallazgos(
        self,
        page: Any,
        site_id: uuid.UUID,
        now: datetime,
        orphan_page_ids: set[uuid.UUID],
    ) -> list[ContentFinding]:
        """Lo que no depende de si la página se pudo leer: error de rastreo, antigüedad, huérfana."""
        results: list[ContentFinding] = []

        if page.status == "error":
            # RAS.3 — la severidad depende de qué se puede concluir. Un 404 es una respuesta del
            # servidor: el enlace apunta a algo que ya no está, y eso hay que depurarlo. Un 5xx o
            # un `timeout` tras varios intentos no dice nada de la página, así que no puede ser
            # crítico ni mezclarse con los hallazgos de contenido.
            clase = getattr(page, "error_kind", None)
            results.append(self._finding(
                site_id=site_id,
                finding_type="crawl_error",
                severity=_SEVERIDAD_DEL_ERROR.get(clase, "critical"),
                confidence=1.0,
                page_id=page.id,
                source_url=page.url,
                signal={
                    "error_message": page.error_message or "",
                    "kind": clase,
                    "attempts": getattr(page, "error_attempts", None),
                },
                now=now,
            ))

        content_date, origen = _content_date(page)
        if content_date is not None:
            age_days = (now - content_date).days
            if age_days > self._stale_days:
                results.append(self._finding(
                    site_id=site_id,
                    finding_type="stale",
                    severity="info",
                    confidence=1.0,
                    page_id=page.id,
                    source_url=page.url,
                    # De dónde sale la fecha: quien revisa tiene que poder distinguir «lo declara
                    # el servidor» de «lo dice la URL», que no valen lo mismo.
                    signal={
                        "date": content_date.isoformat(),
                        "age_days": age_days,
                        "source": origen,
                    },
                    now=now,
                ))

        if page.id in orphan_page_ids:
            results.append(self._finding(
                site_id=site_id,
                finding_type="orphan_page",
                severity="warning",
                confidence=1.0,
                page_id=page.id,
                source_url=page.url,
                signal={},
                now=now,
            ))

        return results

    async def _check_superseded(
        self,
        pages: list[Any],
        site_id: uuid.UUID,
        now: datetime,
    ) -> list[ContentFinding]:
        groups: dict[str, list] = defaultdict(list)
        for page in pages:
            # RAS.5 — una página que no se pudo leer no puede ser «la versión vigente». Sin fecha
            # de nada, el orden cae en `first_seen_at` —de hace un instante— y quedaba como la más
            # nueva del grupo: en el rastreo real, un acuerdo de 2017 que falló por un problema de
            # red declaraba superados los de 2023, 2024 y 2025.
            if getattr(page, "status", "active") == "error":
                continue
            key = _process_key(page.canonical_url, page.url)
            groups[key].append(page)

        results: list[ContentFinding] = []
        for key, group in groups.items():
            if len(group) < 2:
                continue
            sorted_group = sorted(group, key=lambda p: _effective_date(p, now))
            vigente = sorted_group[-1]
            for old_page in sorted_group[:-1]:
                results.append(self._finding(
                    site_id=site_id,
                    finding_type="superseded",
                    severity="warning",
                    confidence=1.0,
                    page_id=old_page.id,
                    related_page_id=vigente.id,
                    source_url=old_page.url,
                    signal={
                        "process_key": key,
                        "superseded_by": vigente.url,
                        "effective_date_old": _effective_date(old_page, now).isoformat(),
                        "effective_date_new": _effective_date(vigente, now).isoformat(),
                    },
                    now=now,
                ))
        return results

    @staticmethod
    def _finding(
        *,
        site_id: uuid.UUID,
        finding_type: str,
        severity: str,
        confidence: float,
        page_id: uuid.UUID | None = None,
        related_page_id: uuid.UUID | None = None,
        source_url: str | None = None,
        signal: dict,
        now: datetime,
    ) -> ContentFinding:
        return ContentFinding(
            id=uuid.uuid4(),
            site_id=site_id,
            finding_type=finding_type,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            confidence=confidence,
            detected_at=now,
            page_id=page_id,
            related_page_id=related_page_id,
            source_url=source_url,
            signal=signal,
        )
