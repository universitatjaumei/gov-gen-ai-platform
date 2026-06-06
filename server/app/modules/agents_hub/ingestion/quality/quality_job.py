"""Job de calidad de contenido web por sitio (9Q.5).

Deploy: edge.

Orquesta por sitio: crawl + detección (determinista + semántica) + consolidación de
flags (superseded/quality_score) + auto-ingesta de páginas nuevas que casan una
HubCorpusSelection con auto_ingest_new=True.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ──────────────────────────── Protocolos ────────────────────────────


class _SiteCrawler(Protocol):
    async def crawl_site(self, site_id: uuid.UUID) -> Any: ...


class _Detector(Protocol):
    _is_semantic: bool
    async def analyze(self, site_id: uuid.UUID) -> list: ...


class _Watcher(Protocol):
    async def process_source(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        *,
        prefetched_content: str | None = None,
        title: str | None = None,
        crawled_page_id: uuid.UUID | None = None,
    ) -> Any: ...


class _SelectionRepo(Protocol):
    async def list_by_site(self, site_id: uuid.UUID) -> list: ...
    def matches(self, selection: Any, page_url: str) -> bool: ...


# ──────────────────────────── SiteQualitySummary ────────────────────────────


@dataclass
class SiteQualitySummary:
    pages_new: int = 0
    pages_changed: int = 0
    pages_gone: int = 0
    pages_error: int = 0
    pages_total: int = 0
    findings_by_type: dict[str, int] = field(default_factory=dict)
    pages_marked_superseded: int = 0
    documents_auto_ingested: int = 0
    errors: list[str] = field(default_factory=list)


# ──────────────────────────── Heurística de calidad ────────────────────────────


_SEVERITY_PENALTY: dict[str, float] = {
    "critical": 0.5,
    "warning": 0.2,
    "info": 0.1,
}


def _compute_quality_score(findings: list) -> float:
    """Score de calidad [0.0, 1.0] = 1.0 menos penalizaciones acumuladas por hallazgo."""
    score = 1.0
    for f in findings:
        score -= _SEVERITY_PENALTY.get(getattr(f, "severity", "info"), 0.0)
    return max(0.0, score)


# ──────────────────────────── SiteQualityAnalysisJob ────────────────────────────


class SiteQualityAnalysisJob:
    """Orquesta crawl + detección + consolidación + auto-ingesta para un sitio."""

    def __init__(
        self,
        session_factory: Any,
        site_crawler: _SiteCrawler,
        detectors: list[_Detector],
        watcher: _Watcher | None,
        selection_repo: _SelectionRepo,
        *,
        run_semantic: bool = True,
    ) -> None:
        self._session_factory = session_factory
        self._site_crawler = site_crawler
        self._detectors = detectors
        self._watcher = watcher
        self._selection_repo = selection_repo
        self._run_semantic = run_semantic

    async def run_for_site(self, site_id: uuid.UUID) -> SiteQualitySummary:
        """Ejecuta el ciclo completo de calidad para un sitio.

        Nunca propaga excepción: todos los errores se acumulan en summary.errors.
        """
        summary = SiteQualitySummary()

        # ── 1. CRAWL ──────────────────────────────────────────────────────────
        try:
            crawl_summary = await self._site_crawler.crawl_site(site_id)
            summary.pages_new = crawl_summary.pages_new
            summary.pages_changed = crawl_summary.pages_changed
            summary.pages_gone = crawl_summary.pages_gone
            summary.pages_error = crawl_summary.pages_error
            summary.pages_total = crawl_summary.pages_total
        except Exception as exc:
            logger.exception("Crawl failed for site %s", site_id)
            summary.errors.append(f"crawl: {exc}")
            return summary  # Sin crawl no hay diff para detectar ni consolidar

        # ── 2. DETECCIÓN (cada detector aislado) ──────────────────────────────
        all_findings: list = []
        for detector in self._detectors:
            is_sem = getattr(detector, "_is_semantic", False)
            if is_sem and not self._run_semantic:
                continue
            try:
                findings = await detector.analyze(site_id)
                all_findings.extend(findings)
            except Exception as exc:
                logger.exception("Detector failed for site %s", site_id)
                summary.errors.append(f"detector: {exc}")

        # Conteo por tipo de hallazgo
        for f in all_findings:
            key = getattr(f, "finding_type", "unknown")
            summary.findings_by_type[key] = summary.findings_by_type.get(key, 0) + 1

        # ── 3. CONSOLIDACIÓN + quality_score ──────────────────────────────────
        async with self._session_factory() as session:
            from server.app.modules.agents_hub.database.operational_models import (
                HubCrawledPage,
            )

            # Flags de supersesión sobre HubCrawledPage
            for f in all_findings:
                if (
                    getattr(f, "finding_type", "") == "superseded"
                    and getattr(f, "status", "new") in ("new", "confirmed")
                ):
                    page_id = getattr(f, "page_id", None)
                    if page_id:
                        page = await session.get(HubCrawledPage, page_id)
                        if page is not None and not page.superseded:
                            page.superseded = True
                            page.superseded_by_page_id = getattr(f, "related_page_id", None)
                            summary.pages_marked_superseded += 1

            # quality_score por página
            findings_by_page: dict[uuid.UUID, list] = {}
            for f in all_findings:
                pid = getattr(f, "page_id", None)
                if pid:
                    findings_by_page.setdefault(pid, []).append(f)

            for page_id, page_findings in findings_by_page.items():
                page = await session.get(HubCrawledPage, page_id)
                if page is not None:
                    page.quality_score = _compute_quality_score(page_findings)

            await session.flush()

            # ── 4. AUTO-INGESTA (páginas nuevas del diff) ──────────────────────
            new_page_ids: list[uuid.UUID] = getattr(crawl_summary, "new_page_ids", [])
            if new_page_ids and self._watcher is not None:
                selections = await self._selection_repo.list_by_site(site_id)
                auto_sels = [s for s in selections if getattr(s, "auto_ingest_new", False)]

                if auto_sels:
                    for page_id in new_page_ids:
                        page = await session.get(HubCrawledPage, page_id)
                        if page is None:
                            continue
                        for sel in auto_sels:
                            if self._selection_repo.matches(sel, page.url):
                                try:
                                    await self._watcher.process_source(
                                        source_url=page.url,
                                        chatbot_id=sel.chatbot_id,
                                        prefetched_content=page.markdown_content,
                                        title=page.title,
                                        crawled_page_id=page.id,
                                    )
                                    summary.documents_auto_ingested += 1
                                except Exception as exc:
                                    logger.exception(
                                        "Auto-ingest failed for page %s chatbot %s",
                                        page.url,
                                        sel.chatbot_id,
                                    )
                                    summary.errors.append(f"auto-ingest {page.url}: {exc}")

        return summary
