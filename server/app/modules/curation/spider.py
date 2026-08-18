"""Spider genérico BFS con control de profundidad, filtros regex y límite de páginas.

Deploy: edge

**Cortesía (RAS.1)**: la pausa por host, el `robots.txt` y el `User-Agent` identificable viven en
`_fetch`, que es por donde pasan los dos bucles —el BFS de aquí y el recorrido por URL de
`SiteCrawler`—. La configuración del sitio puede relajarla, nunca al revés por descuido.
"""

import re
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Protocol
from urllib.parse import urljoin, urlparse

from server.app.modules.curation.cortesia import (
    PRESUPUESTO_POR_DEFECTO_SEGUNDOS,
    CortesiaDeRastreo,
    RutaProhibidaPorRobots,
    cortesia_desde_config,
)


#: Tope de páginas que se guardan en memoria para no volver a pedirlas. Con ~50 KB de HTML por
#: página, quinientas son unos 25 MB; por encima se vuelve a pedir, que es lento pero acotado.
_PAGINAS_RECORDADAS = 500


class CrawlStatus(Enum):
    COMPLETED = "completed"
    COMPLETED_PARTIAL = "completed_partial"


@dataclass
class CrawlResult:
    crawled_urls: list[str]
    pages_crawled: int
    pages_skipped: int
    status: CrawlStatus
    #: Por qué se paró antes de agotar la cola: `max_pages`, `time_budget` o nada.
    #: Sin esto, un rastreo truncado y uno completo se cuentan igual, y las páginas que no se
    #: llegaron a visitar acaban declaradas desaparecidas (ver `SiteCrawler`).
    stop_reason: str | None = None
    #: URLs excluidas por el `robots.txt` del sitio. No son errores: son decisiones del servidor.
    urls_prohibidas: int = 0
    #: La cola que quedó pendiente, con su profundidad (RAS.3). Vivía sólo en memoria, así que un
    #: corte en la página 8.000 obligaba a empezar de cero; con pausa de dos segundos, horas.
    frontier: list[tuple[str, int]] = field(default_factory=list)
    #: Todo lo visitado, incluido lo que venía de una ejecución anterior.
    visited: list[str] = field(default_factory=list)
    #: `True` si esta ejecución arrancó de una cola guardada y no de `root_url`.
    resumed: bool = False


class _WebSource(Protocol):
    """El sitio a rastrear, tal y como lo guarda la base.

    Decía `url`, y el modelo se llama `root_url` desde que `HubWebSource` pasó a ser
    `HubWebSite`: el rastreo fallaba **siempre** con `'HubWebSite' object has no attribute
    'url'` y el sitio quedaba en `status='error'`. No lo cazó ningún test porque todos doblan
    el spider, y el doble del sitio ya usaba `root_url`.
    """

    root_url: str
    config_json: dict


class GenericSpider:
    """Spider BFS que respeta crawl_depth, url_regex_filter y max_pages leídos de config_json."""

    def __init__(
        self,
        fetch_fn: Callable[[str], Awaitable[tuple[str, dict]]] | None = None,
        *,
        sleep_fn: Callable[[float], Awaitable[None]] | None = None,
        clock_fn: Callable[[], float] | None = None,
        contacto: str | None = None,
    ) -> None:
        self._fetch_fn = fetch_fn
        self._sleep_fn = sleep_fn
        self._clock_fn = clock_fn
        self._contacto = contacto
        # Cortesía por defecto hasta que un sitio diga otra cosa: si alguien llama a `_fetch`
        # antes de `crawl`, se rastrea despacio, no a toda velocidad.
        self._cortesia = self._nueva_cortesia({})
        # Lo descargado en esta ejecución, para no volver a pedirlo (RAS.3).
        self._leido: dict[str, tuple[str, dict]] = {}

    # -- configuración -------------------------------------------------------

    def _nueva_cortesia(self, config: dict) -> CortesiaDeRastreo:
        if self._contacto is None:
            from server.app.core.config import get_settings

            try:
                contacto = get_settings().crawler_contact
            except Exception:  # noqa: BLE001 — sin configuración cargada seguimos, sin contacto
                contacto = ""
        else:
            contacto = self._contacto
        return cortesia_desde_config(
            config, contacto=contacto, sleep_fn=self._sleep_fn, clock_fn=self._clock_fn
        )

    def configurar_cortesia(self, config: dict) -> None:
        """Aplica la cortesía que declara la configuración de un sitio."""
        self._cortesia = self._nueva_cortesia(config)

    def pausa_efectiva_para(self, url: str) -> float:
        return self._cortesia.pausa_efectiva_para(url)

    # -- descarga ------------------------------------------------------------

    async def _descargar(self, url: str) -> tuple[str, dict]:
        """La descarga a secas, sin cortesía: la usan `_fetch` y la lectura del `robots.txt`."""
        if self._fetch_fn is not None:
            return await self._fetch_fn(url)
        import httpx
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10.0,
            headers={"User-Agent": self._cortesia.user_agent},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text, dict(resp.headers)

    async def _fetch(self, url: str) -> tuple[str, dict]:
        """Descarga una URL respetando `robots.txt`, la pausa, la concurrencia y los reintentos.

        Si el recorrido ya la descargó en esta misma ejecución, se devuelve lo leído: `crawl()`
        pedía cada página para extraer sus enlaces y `SiteCrawler` la volvía a pedir para
        guardarla, o sea el doble de peticiones y el doble de tiempo contra el mismo servidor
        (medido en el sondeo del apartado real: 25 páginas, 50 peticiones).
        """
        if url in self._leido:
            return self._leido[url]

        if not await self._cortesia.permitido(url, self._descargar):
            raise RutaProhibidaPorRobots(url)

        async with self._cortesia.turno_de(url):
            await self._cortesia.esperar_turno(url)
            respuesta = await self._cortesia.con_reintentos(url, self._descargar)

        self._recordar(url, respuesta)
        return respuesta

    def _recordar(self, url: str, respuesta: tuple[str, dict]) -> None:
        """Guarda lo leído para no repetir la petición, con tope: un rastreo de miles de páginas
        no puede quedarse con todas en memoria, y degradar a volver a pedirlas es correcto."""
        if len(self._leido) >= _PAGINAS_RECORDADAS:
            return
        self._leido[url] = respuesta

    def olvidar_lo_leido(self) -> None:
        self._leido.clear()

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

    # -- recorrido -----------------------------------------------------------

    async def crawl(self, source: _WebSource) -> CrawlResult:
        config: dict = source.config_json
        crawl_depth: int = config.get("crawl_depth", 1)
        url_regex_filter: str | None = config.get("url_regex_filter")
        max_pages: int = config.get("max_pages", 50)
        max_seconds: float = float(
            config.get("max_seconds", PRESUPUESTO_POR_DEFECTO_SEGUNDOS)
        )

        self.configurar_cortesia(config)
        empezado = self._cortesia._reloj()

        regex = re.compile(url_regex_filter) if url_regex_filter else None
        base_netloc = urlparse(source.root_url).netloc

        # Cola BFS: pares (url, profundidad). Si el sitio guarda una cola de una ejecución
        # interrumpida, se retoma por ahí en vez de volver a empezar por la raíz (RAS.3).
        guardada = getattr(source, "crawl_frontier", None) or {}
        pendientes = [(u, int(d)) for u, d in (guardada.get("pending") or [])]
        ya_visitadas = set(guardada.get("visited") or [])
        reanudado = bool(pendientes)

        if reanudado:
            queue: deque[tuple[str, int]] = deque(pendientes)
            visited: set[str] = ya_visitadas | {u for u, _d in pendientes}
        else:
            queue = deque([(source.root_url, 0)])
            visited = {source.root_url}

        crawled_urls: list[str] = []
        pages_skipped = 0
        prohibidas = 0
        stop_reason: str | None = None

        while queue:
            if len(crawled_urls) >= max_pages:
                stop_reason = "max_pages"
                pages_skipped += len(queue)
                break
            if self._cortesia._reloj() - empezado >= max_seconds:
                # El presupuesto es de tiempo además de páginas porque el coste real de un
                # rastreo cortés es el tiempo: con pausa de un segundo, mil páginas son veinte
                # minutos. Parar y decirlo es mejor que no terminar nunca.
                stop_reason = "time_budget"
                pages_skipped += len(queue)
                break

            url, depth = queue.popleft()
            try:
                html, _headers = await self._fetch(url)
            except RutaProhibidaPorRobots:
                # No es un error del sitio ni nuestro: el servidor ha dicho que no. Se cuenta y
                # se sigue; convertirlo en `crawl_error` llenaría el informe de acusaciones.
                prohibidas += 1
                continue
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
                # Comprobar la exclusión **antes de encolar**: si sólo se viera al pedir, cada
                # ruta prohibida costaría una vuelta de la cola y una excepción.
                if not await self._cortesia.permitido(link, self._descargar):
                    prohibidas += 1
                    continue
                visited.add(link)
                queue.append((link, depth + 1))

        status = (
            CrawlStatus.COMPLETED_PARTIAL if stop_reason is not None else CrawlStatus.COMPLETED
        )
        return CrawlResult(
            crawled_urls=crawled_urls,
            pages_crawled=len(crawled_urls),
            pages_skipped=pages_skipped,
            status=status,
            stop_reason=stop_reason,
            urls_prohibidas=prohibidas,
            # La cola pendiente sólo tiene sentido si quedó algo: un rastreo completo no deja
            # nada que reanudar, y dejar restos haría que la siguiente ejecución arrancara por
            # la mitad de un recorrido ya terminado.
            frontier=list(queue) if stop_reason is not None else [],
            visited=sorted(visited),
            resumed=reanudado,
        )
