"""Cuántas páginas tiene un sitio, antes de comprometerse a rastrearlo (CUR.6).

Del usuario: «convendría que al dar de alta un nuevo sitio se pudiera generar y descargar un
sitemap. De ese modo se podría valorar la extensión del sitio y si conviene hacerlo todo de golpe o
por subapartados». El portal **no publica sitemap** —medido en RAS.4: `/sitemap.xml` da 404—, así
que el sitemap hay que construirlo, y construirlo es recorrer.

Tres diferencias con el rastreo de verdad, y las tres importan:

* **No guarda nada.** Ni páginas, ni hallazgos, ni el sitio: se puede reconocer una URL que todavía
  no está dada de alta, que es justo el momento en que la pregunta se hace.
* **Va con prisa** —pausa corta y tope de páginas—, porque responde dentro de una petición HTTP.
  Por eso cuenta también **la cola pendiente**: si sólo contara lo visitado, el tope sería la
  respuesta («tiene 60 páginas» porque paramos en 60).
* **Estima con la cortesía del rastreo real**, no con la suya. Con dos segundos por página, mil
  URLs son treinta y cinco minutos; con la latencia del sondeo rápido saldrían tres. El número que
  decide «de golpe o por apartados» tiene que ser el del rastreo que se va a lanzar.

Deploy: edge — recorre el portal del cliente.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

from server.app.modules.curation.cortesia import PAUSA_POR_DEFECTO
from server.app.modules.curation.spider import GenericSpider

#: Cuántas URLs de muestra se guardan por apartado. Un recuento sin muestra no dice qué hay
#: dentro de «base»; doscientas muestras tampoco.
_EJEMPLOS_POR_APARTADO = 5

#: Lo que se sondea por defecto en una petición HTTP: bastante para estimar, poco para esperar.
PROFUNDIDAD_DE_SONDEO = 3
PAGINAS_DE_SONDEO = 60
PAUSA_DE_SONDEO = 0.2
PRESUPUESTO_DE_SONDEO_SEGUNDOS = 90.0


@dataclass(frozen=True)
class ApartadoDelSitio:
    """Un primer nivel de ruta bajo la raíz, con lo que se ha encontrado dentro."""

    apartado: str
    urls: int
    ejemplos: list[str]


@dataclass(frozen=True)
class InformeDeReconocimiento:
    root_url: str
    urls_encontradas: int
    paginas_sondeadas: int
    truncado: bool
    motivo_de_parada: str | None
    apartados: list[ApartadoDelSitio]
    segundos_por_pagina: float
    segundos_estimados: float
    urls: list[str] = field(default_factory=list)
    urls_prohibidas: int = 0
    no_legibles: int = 0
    fallos: int = 0


def apartados_de(urls: list[str], root_url: str) -> list[ApartadoDelSitio]:
    """Agrupa las URLs por su primer segmento de ruta bajo la raíz, de mayor a menor.

    La propia raíz va en `/`: no cuelga de ningún apartado y dejarla fuera haría que la suma de los
    apartados no cuadrara con el total.
    """
    base = urlparse(root_url).path.rstrip("/")
    cuentas: dict[str, list[str]] = {}

    for url in urls:
        cuentas.setdefault(_apartado_de(url, base), []).append(url)

    return sorted(
        (
            ApartadoDelSitio(
                apartado=nombre,
                urls=len(suyas),
                ejemplos=sorted(suyas)[:_EJEMPLOS_POR_APARTADO],
            )
            for nombre, suyas in cuentas.items()
        ),
        key=lambda a: (-a.urls, a.apartado),
    )


def _apartado_de(url: str, base: str) -> str:
    ruta = urlparse(url).path
    resto = ruta[len(base):] if ruta.startswith(base) else ruta
    segmentos = [s for s in resto.split("/") if s]
    return segmentos[0] if segmentos else "/"


def csv_de_apartados(urls: list[str], root_url: str) -> str:
    """El sitemap que se comparte con quien decide: una fila por URL, con su apartado.

    Con `csv.writer` y no con `join`, porque una URL con coma —`.../acta,2025/`— desplazaría la
    columna y el fichero diría algo falso sin avisar.
    """
    base = urlparse(root_url).path.rstrip("/")
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(["apartado", "url"])
    for url in sorted(urls):
        escritor.writerow([_apartado_de(url, base), url])
    return salida.getvalue()


class ReconocimientoDeSitio:
    """Recorre un sitio sin guardar nada y dice cuánto costaría rastrearlo."""

    def __init__(
        self,
        fetch_fn: Callable[[str], Awaitable[tuple[str, dict]]] | None = None,
        *,
        clock_fn: Callable[[], float] | None = None,
        contacto: str | None = None,
    ) -> None:
        self._fetch_fn = fetch_fn
        self._clock_fn = clock_fn
        self._contacto = contacto

    async def reconocer(
        self,
        root_url: str,
        *,
        max_depth: int = PROFUNDIDAD_DE_SONDEO,
        max_pages: int = PAGINAS_DE_SONDEO,
        delay_seconds: float = PAUSA_DE_SONDEO,
        max_seconds: float = PRESUPUESTO_DE_SONDEO_SEGUNDOS,
        url_regex_filter: str | None = None,
        respect_robots: bool = True,
        pausa_del_rastreo: float = PAUSA_POR_DEFECTO,
    ) -> InformeDeReconocimiento:
        spider = GenericSpider(
            self._fetch_fn, clock_fn=self._clock_fn, contacto=self._contacto
        )
        fuente = _FuenteDeSondeo(
            root_url=root_url,
            config_json={
                "crawl_depth": max_depth,
                "max_pages": max_pages,
                "max_seconds": max_seconds,
                "delay_seconds": delay_seconds,
                "respect_robots": respect_robots,
                "url_regex_filter": url_regex_filter,
            },
        )

        empezado = spider._cortesia._reloj()
        resultado = await spider.crawl(fuente)
        tardado = max(spider._cortesia._reloj() - empezado, 0.0)

        # Ojo con los nombres de `CrawlResult`: `visited` es lo **descubierto** —se añade al
        # encolar— y `crawled_urls` es lo que de verdad se pidió. El tope acota lo que se pide, no
        # lo que hay, y aquí interesan las dos cifras por separado.
        urls = sorted({*resultado.visited, *(u for u, _ in resultado.frontier)})
        pedidas = len(resultado.crawled_urls)
        sondeadas = max(pedidas, 1)

        latencia = tardado / sondeadas
        # La pausa del rastreo real manda sobre la del sondeo: es la que va a dominar el reloj.
        por_pagina = max(latencia, latencia_sin_pausa(latencia, delay_seconds) + pausa_del_rastreo)

        return InformeDeReconocimiento(
            root_url=root_url,
            urls_encontradas=len(urls),
            paginas_sondeadas=pedidas,
            truncado=resultado.stop_reason is not None,
            motivo_de_parada=resultado.stop_reason,
            apartados=apartados_de(urls, root_url),
            segundos_por_pagina=round(por_pagina, 3),
            segundos_estimados=round(len(urls) * por_pagina, 1),
            urls=urls,
            urls_prohibidas=resultado.urls_prohibidas,
            no_legibles=resultado.no_legibles,
            fallos=len(resultado.fallos),
        )


def latencia_sin_pausa(medida: float, pausa_del_sondeo: float) -> float:
    """Lo que costó la petición en sí, quitando la pausa que el sondeo se impuso."""
    return max(medida - pausa_del_sondeo, 0.0)


@dataclass
class _FuenteDeSondeo:
    """Lo que el spider necesita de un sitio, sin que el sitio exista en la base."""

    root_url: str
    config_json: dict[str, Any]
    crawl_frontier: dict | None = None
