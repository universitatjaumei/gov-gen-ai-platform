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
from datetime import datetime, timezone
from typing import Any, Protocol

from server.app.modules.curation.reconciliacion import (
    reconciliar_hallazgos,
    tipos_a_reconciliar,
)

logger = logging.getLogger(__name__)


# ──────────────────────────── Protocolos ────────────────────────────


class _SiteCrawler(Protocol):
    async def crawl_site(
        self, site_id: uuid.UUID, section_id: uuid.UUID | None = None
    ) -> Any: ...


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
    #: RAS.5 — páginas del corpus que cambiaron en el portal y se han vuelto a ingerir. El rastreo
    #: ya detectaba el cambio y nadie lo propagaba: el asistente seguía citando el texto viejo.
    documents_reingested: int = 0
    #: CUR.9 — hallazgos retirados porque este análisis ya no los emite. Sin esta cifra, «41 nuevos»
    #: y «41 nuevos y 300 retirados» se leerían igual, y son dos noticias muy distintas.
    findings_retired: int = 0
    errors: list[str] = field(default_factory=list)
    #: DIN.2 — qué ámbito cubrió la pasada: la sección, o el sitio entero. El diario de DIN.6 lo
    #: escribe y la auto-retirada de DIN.4 decide con él.
    section_id: uuid.UUID | None = None

    @property
    def ambito(self) -> str:
        return "sitio" if self.section_id is None else str(self.section_id)


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
        finding_repo: Any = None,
        watcher_factory: Any = None,
    ) -> None:
        self._session_factory = session_factory
        self._site_crawler = site_crawler
        self._detectors = detectors
        self._watcher = watcher
        self._selection_repo = selection_repo
        self._run_semantic = run_semantic
        # Para avisar de las páginas del corpus que se han actualizado (RAS.5). Opcional: sin él
        # la reingesta sigue ocurriendo, pero sin dejar aviso en la bandeja.
        self._finding_repo = finding_repo
        # RAS.5 — el watcher necesita el servicio de embeddings **del chatbot**, así que una única
        # instancia no puede servir a varios: ingerir con otro modelo del que usa su corpus deja
        # vectores incomparables. Con fábrica, cada ingesta usa el suyo. Sin ella se usa el
        # watcher fijo, que es lo que hacen los tests que doblan esta pieza.
        self._watcher_factory = watcher_factory

    async def _watcher_para(self, session: Any, chatbot_id: uuid.UUID) -> Any:
        """El watcher que ingiere para ese chatbot, con su servicio de embeddings."""
        if self._watcher_factory is not None:
            return await self._watcher_factory(session, chatbot_id)
        return self._watcher

    async def _reingerir_lo_que_cambio(
        self,
        session: Any,
        site_id: uuid.UUID,
        changed_page_ids: list,
        summary: SiteQualitySummary,
    ) -> None:
        """Vuelve a ingerir las páginas del corpus que han cambiado, y avisa de cada una."""
        if not changed_page_ids or (self._watcher is None and self._watcher_factory is None):
            return

        from sqlalchemy import select

        from server.app.modules.agents_hub.database.operational_models import (
            HubCrawledPage,
            HubDocument,
        )

        for page_id in changed_page_ids:
            page = await session.get(HubCrawledPage, page_id)
            if page is None:
                continue

            documentos = (
                await session.execute(
                    select(HubDocument).where(HubDocument.crawled_page_id == page_id)
                )
            ).scalars().all()
            # Un asistente puede tener la página una vez; varios pueden tenerla cada uno.
            chatbots = {doc.chatbot_id for doc in documentos}
            if not chatbots:
                continue

            actualizados = 0
            for chatbot_id in chatbots:
                try:
                    watcher = await self._watcher_para(session, chatbot_id)
                    await watcher.process_source(
                        source_url=page.url,
                        chatbot_id=chatbot_id,
                        prefetched_content=page.markdown_content,
                        title=page.title,
                        crawled_page_id=page.id,
                    )
                    actualizados += 1
                    summary.documents_reingested += 1
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Reingesta fallida de %s para el chatbot %s", page.url, chatbot_id
                    )
                    summary.errors.append(f"reingesta {page.url}: {exc}")

            if actualizados and self._finding_repo is not None:
                await self._avisar_de_la_actualizacion(site_id, page, actualizados)

    async def _avisar_de_la_actualizacion(
        self, site_id: uuid.UUID, page: Any, chatbots_actualizados: int
    ) -> None:
        from datetime import datetime, timezone

        from server.app.modules.curation.contracts import ContentFinding

        try:
            await self._finding_repo.upsert(ContentFinding(
                id=uuid.uuid4(),
                site_id=site_id,
                finding_type="content_updated",
                severity="info",
                confidence=1.0,
                detected_at=datetime.now(timezone.utc),
                page_id=page.id,
                source_url=page.url,
                signal={
                    "chatbots_actualizados": chatbots_actualizados,
                    "title": page.title,
                },
            ))
        except Exception:  # noqa: BLE001 — el aviso no puede tumbar el job de calidad
            logger.exception("No se pudo registrar el aviso de actualización de %s", page.url)

    async def run_for_site(
        self, site_id: uuid.UUID, section_id: uuid.UUID | None = None
    ) -> SiteQualitySummary:
        """Ejecuta el ciclo completo de calidad para un ámbito del sitio.

        `section_id` acota la pasada a una sección (DIN.2): con él, el censo de bajas se compara
        sólo contra las páginas de ese apartado. Sin él, el ámbito es el sitio entero, que es el
        comportamiento de siempre.

        Nunca propaga excepción: todos los errores se acumulan en summary.errors.
        """
        summary = SiteQualitySummary(section_id=section_id)

        # ── 1. CRAWL ──────────────────────────────────────────────────────────
        try:
            crawl_summary = await self._site_crawler.crawl_site(
                site_id, section_id=section_id
            )
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
        # CUR.9 — quién ha mirado de verdad y quién no. La reconciliación de abajo sólo puede
        # retirar los tipos de los detectores que **han corrido**: un detector que se saltó, o que
        # falló, no autoriza a retirar nada suyo.
        ejecutados: list = []
        omitidos: list = []
        for detector in self._detectors:
            is_sem = getattr(detector, "_is_semantic", False)
            if is_sem and not self._run_semantic:
                omitidos.append(detector)
                continue
            try:
                findings = await detector.analyze(site_id)
                all_findings.extend(findings)
                ejecutados.append(detector)
            except Exception as exc:
                logger.exception("Detector failed for site %s", site_id)
                summary.errors.append(f"detector: {exc}")
                omitidos.append(detector)

        # Conteo por tipo de hallazgo
        for f in all_findings:
            key = getattr(f, "finding_type", "unknown")
            summary.findings_by_type[key] = summary.findings_by_type.get(key, 0) + 1

        # ── 3. CONSOLIDACIÓN + quality_score ──────────────────────────────────
        async with self._session_factory() as session:
            from server.app.modules.agents_hub.database.operational_models import (
                HubCrawledPage,
            )

            # ── 3.pre. RECONCILIACIÓN (CUR.9) ─────────────────────────────────
            #
            # El detector sólo sabía añadir: afirmaba y nunca dejaba de afirmar. Medido tras CUR.7:
            # 241 hallazgos `stale` guardados donde el detector emitía 207, porque las páginas que
            # pasaron a agruparse como serie dejaron de producir aviso y su fila vieja seguía ahí.
            # Del usuario: «no tiene sentido que haya filas que ya no sean ciertas».
            #
            # Va antes de calcular `quality_score` a propósito: la nota de una página no puede
            # seguir castigada por hallazgos que ya se han retirado.
            try:
                summary.findings_retired = await reconciliar_hallazgos(
                    session,
                    site_id,
                    tipos=tipos_a_reconciliar(ejecutados=ejecutados, omitidos=omitidos),
                    emitidos=all_findings,
                    now=datetime.now(timezone.utc),
                )
            except Exception as exc:  # noqa: BLE001 — retirar de más es peor que no retirar
                logger.exception("Reconciliation failed for site %s", site_id)
                summary.errors.append(f"reconciliation: {exc}")

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

            # ── 3.bis. REINGESTA DE LO QUE CAMBIÓ (RAS.5) ─────────────────────
            #
            # El rastreo ya detectaba el cambio —compara `content_hash` y llena
            # `changed_page_ids`—, pero nadie lo consumía: una página ya publicada se
            # actualizaba en el portal y el asistente seguía respondiendo con el texto viejo.
            #
            # Se reingiere **sólo donde ya estaba**: actualizar lo que alguien aprobó una vez no
            # es publicar lo que nadie ha aprobado. Y no en silencio: queda el aviso
            # `content_updated` para poder revisar qué cambió.
            await self._reingerir_lo_que_cambio(
                session, site_id, getattr(crawl_summary, "changed_page_ids", []), summary
            )

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
