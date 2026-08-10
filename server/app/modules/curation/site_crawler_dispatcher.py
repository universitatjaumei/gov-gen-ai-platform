"""Despachador de rastreo: del `site_id` al `SiteCrawler` que le corresponde (SEC.8.8).

Deploy: edge.

`SiteCrawler` recibe **un** spider ya construido, pero cuál es el correcto depende del
`spider_type` de cada sitio, que solo se sabe leyendo el sitio. Faltaba justo esa pieza: sin
ella no había forma de ir del `site_id` que llega por la ruta al rastreo, y por eso el
arranque cableaba un crawler nulo que respondía «no spider configured» a todo.

**Esto no ingiere nada al corpus.** El rastreo llena la bandeja del curador —páginas
descubiertas, cambiadas, desaparecidas— y ahí se queda; publicar al corpus sigue siendo una
decisión por candidata, según `docs/DECISION_CURACION_SEPARADA.md`. Una página nueva es una
señal para quien cura, no un disparador.

**Sobre la sesión**: el despachador abre la suya y hace commit al terminar, igual que hacía
el `_NullCrawler` al que sustituye. Un rastreo dura minutos y toca cientos de filas; colgarlo
de la sesión de la petición que lo encoló la mantendría abierta todo ese tiempo.

**Pendiente de Deploy**: hoy el rastreo se encola con `BackgroundTasks`, o sea dentro del
proceso web. En un entorno que escala a cero —Cloud Run— la instancia puede morir a mitad y
el rastreo desaparece sin dejar rastro. Para ese despliegue hace falta un ejecutor de
trabajos duradero; en local, en Docker y en un edge con contenedor persistente esto funciona
tal cual. Se decidió así a propósito: separar la ejecución, no la aplicación.
"""
from __future__ import annotations

import uuid
from typing import Any

from server.app.modules.agents_hub.database.operational_models import HubWebSite
from server.app.modules.curation.signal_extractor import CrawlSignalExtractor
from server.app.modules.curation.site_crawler import SiteCrawler, SiteCrawlSummary
from server.app.modules.curation.site_repo import CrawledPageRepo
from server.app.modules.curation.spider_factory import SpiderFactory

_SPIDER_POR_DEFECTO = "generic"


class SiteCrawlerDispatcher:
    """Resuelve el spider de cada sitio y ejecuta su rastreo.

    Cumple el mismo protocolo que consumía `SiteQualityAnalysisJob` (`crawl_site(site_id)`),
    así que sustituir el crawler nulo por este no toca el job.
    """

    def __init__(self, session_factory: Any, spider_factory: Any | None = None) -> None:
        self._session_factory = session_factory
        self._spiders = spider_factory or SpiderFactory()

    async def crawl_site(self, site_id: uuid.UUID) -> SiteCrawlSummary:
        async with self._session_factory() as session:
            site = await session.get(HubWebSite, site_id)
            if site is None:
                return SiteCrawlSummary(errors=[f"site {site_id} not found"])

            tipo = getattr(site, "spider_type", None) or _SPIDER_POR_DEFECTO
            try:
                spider = self._spiders.get_spider(tipo)
            except ValueError as exc:
                # Un tipo desconocido NO cae al genérico: rastrear el DOGV con el spider
                # equivocado produce páginas mal extraídas que alguien tendría que revisar
                # a mano después, y el coste de eso es mayor que el de no rastrear.
                return SiteCrawlSummary(errors=[str(exc)])

            crawler = SiteCrawler(
                session=session,
                spider=spider,
                signal_extractor=CrawlSignalExtractor(),
                page_repo=CrawledPageRepo(session),
            )
            resumen = await crawler.crawl_site(site_id)
            await session.commit()
            return resumen


class DeterministicDetectorDispatcher:
    """El detector determinista, con sesión propia por ejecución (SEC.8.8).

    `DeterministicQualityDetector` se construye con una sesión y un repositorio, así que no
    puede instanciarse una sola vez al arrancar: la sesión de entonces no serviría para el
    rastreo de dentro de seis horas. Este adaptador cumple el protocolo que el job consume
    —`analyze(site_id)`— y resuelve las dependencias en cada pasada, igual que el
    despachador de rastreo de arriba.
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def analyze(self, site_id: uuid.UUID) -> list:
        from server.app.modules.curation.deterministic_detector import (
            DeterministicQualityDetector,
        )
        from server.app.modules.curation.findings_repo import ContentFindingRepo

        async with self._session_factory() as session:
            detector = DeterministicQualityDetector(
                session, finding_repo=ContentFindingRepo(session)
            )
            hallazgos = await detector.analyze(site_id)
            await session.commit()
            return hallazgos
