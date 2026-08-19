"""Cuántas páginas tiene esto, antes de comprometerse (CUR.6).

Del usuario: «convendría que al dar de alta un nuevo sitio se pudiera generar y descargar un
sitemap. De ese modo se podría valorar la extensión del sitio y si conviene hacerlo todo de golpe o
por subapartados». El portal **no publica sitemap** —`/sitemap.xml` da 404, medido en RAS.4—, así
que hay que construirlo: es el recorrido de siempre sin guardar nada, con su recuento.

Lo que decide de verdad «de golpe o por apartados» es el **tiempo**, y con dos segundos de cortesía
por página no es una cifra despreciable. Así que el reconocimiento la mide en vez de suponerla.
"""
from __future__ import annotations

import pytest

from server.app.modules.curation.reconocimiento import (
    ReconocimientoDeSitio,
    apartados_de,
    csv_de_apartados,
)

_RAIZ = "https://www.uji.es/centres/escola-doctorat/"


def _pagina(*enlaces: str) -> tuple[str, dict]:
    cuerpo = "".join(f'<a href="{e}">x</a>' for e in enlaces)
    return (f"<html><body>{cuerpo}</body></html>", {"content-type": "text/html"})


class _RelojFalso:
    """Un reloj que avanza medio segundo por consulta: la latencia medida sin red de verdad."""

    def __init__(self, paso: float = 0.5) -> None:
        self._t = 0.0
        self._paso = paso

    def __call__(self) -> float:
        valor = self._t
        self._t += self._paso
        return valor


# ───────────────────────── Agrupar por apartado ─────────────────────────


def test_las_urls_se_agrupan_por_el_primer_nivel_de_ruta():
    """«Por subapartados» es exactamente esto: el primer segmento después de la raíz."""
    urls = [
        f"{_RAIZ}base/doctorands/",
        f"{_RAIZ}base/escola/normativa/",
        f"{_RAIZ}base/escola/",
        f"{_RAIZ}info-general/organitzacio/",
        _RAIZ,
    ]

    apartados = apartados_de(urls, _RAIZ)

    por_nombre = {a.apartado: a.urls for a in apartados}
    assert por_nombre["base"] == 3
    assert por_nombre["info-general"] == 1
    # La propia raíz no cuelga de ningún apartado y tiene que constar igual.
    assert por_nombre["/"] == 1


def test_el_apartado_mas_grande_va_primero():
    """Quien decide mira el recuento, y lo que decide es qué apartado se rastrea primero."""
    urls = [f"{_RAIZ}a/{i}/" for i in range(5)] + [f"{_RAIZ}b/1/"]

    apartados = apartados_de(urls, _RAIZ)

    assert [a.apartado for a in apartados] == ["a", "b"]


def test_cada_apartado_trae_ejemplos_para_reconocerlo():
    """Un recuento sin una URL de muestra no dice qué hay dentro de «base»."""
    urls = [f"{_RAIZ}base/{i}/" for i in range(20)]

    apartados = apartados_de(urls, _RAIZ)

    assert apartados[0].urls == 20
    assert 0 < len(apartados[0].ejemplos) <= 5
    assert apartados[0].ejemplos[0].startswith(f"{_RAIZ}base/")


# ───────────────────────── El CSV que se comparte ─────────────────────────


def test_el_csv_lleva_una_fila_por_url_con_su_apartado():
    """«Lo que se puede compartir con quien decide»: la URL y de qué apartado es."""
    urls = [f"{_RAIZ}base/doctorands/", f"{_RAIZ}info-general/"]

    csv = csv_de_apartados(urls, _RAIZ)
    filas = csv.strip().splitlines()

    assert filas[0] == "apartado,url"
    assert f"base,{_RAIZ}base/doctorands/" in filas
    assert f"info-general,{_RAIZ}info-general/" in filas


def test_una_url_con_coma_no_rompe_el_csv():
    """Sin escapado, una coma en la URL desplaza la columna y el fichero miente."""
    urls = [f"{_RAIZ}base/acta,2025/"]

    csv = csv_de_apartados(urls, _RAIZ)

    assert '"' in csv.splitlines()[1]


# ───────────────────────── El reconocimiento entero ─────────────────────────


@pytest.mark.asyncio
async def test_el_reconocimiento_cuenta_lo_encontrado_sin_guardar_nada():
    paginas = {
        _RAIZ: _pagina(f"{_RAIZ}base/", f"{_RAIZ}info-general/"),
        f"{_RAIZ}base/": _pagina(f"{_RAIZ}base/doctorands/"),
        f"{_RAIZ}info-general/": _pagina(),
        f"{_RAIZ}base/doctorands/": _pagina(),
    }

    async def traer(url: str) -> tuple[str, dict]:
        return paginas.get(url, ("", {"content-type": "text/html"}))

    servicio = ReconocimientoDeSitio(fetch_fn=traer, clock_fn=_RelojFalso())
    informe = await servicio.reconocer(_RAIZ, max_depth=3, max_pages=10, delay_seconds=0)

    assert informe.urls_encontradas == 4
    assert informe.paginas_sondeadas == 4
    assert {a.apartado for a in informe.apartados} == {"/", "base", "info-general"}


@pytest.mark.asyncio
async def test_lo_descubierto_y_no_visitado_tambien_cuenta():
    """Con tope de páginas, la cola pendiente es parte de «cuántas páginas tiene esto».

    Contar sólo lo visitado convertiría el tope en la respuesta: «tiene 2 páginas» porque paramos
    en 2. La cola pendiente es lo que hace que el número sirva para decidir.
    """
    paginas = {
        _RAIZ: _pagina(f"{_RAIZ}a/", f"{_RAIZ}b/", f"{_RAIZ}c/"),
        f"{_RAIZ}a/": _pagina(f"{_RAIZ}a/1/"),
    }

    async def traer(url: str) -> tuple[str, dict]:
        return paginas.get(url, ("", {"content-type": "text/html"}))

    servicio = ReconocimientoDeSitio(fetch_fn=traer, clock_fn=_RelojFalso())
    informe = await servicio.reconocer(_RAIZ, max_depth=3, max_pages=2, delay_seconds=0)

    assert informe.paginas_sondeadas == 2
    assert informe.urls_encontradas > 2
    assert informe.truncado is True


@pytest.mark.asyncio
async def test_la_estimacion_sale_de_lo_medido_y_no_de_una_constante():
    """El dato que responde «de golpe o por apartados».

    Medio segundo por página en el reloj falso y cuatro páginas encontradas → dos segundos. Si la
    estimación fuera una constante, cambiar la pausa no la movería, y la pausa es justo lo que hace
    que un apartado tarde minutos u horas.
    """
    paginas = {
        _RAIZ: _pagina(f"{_RAIZ}a/", f"{_RAIZ}b/", f"{_RAIZ}c/"),
        f"{_RAIZ}a/": _pagina(),
        f"{_RAIZ}b/": _pagina(),
        f"{_RAIZ}c/": _pagina(),
    }

    async def traer(url: str) -> tuple[str, dict]:
        return paginas.get(url, ("", {"content-type": "text/html"}))

    servicio = ReconocimientoDeSitio(fetch_fn=traer, clock_fn=_RelojFalso(paso=0.5))
    # Sin cortesía del rastreo real, para aislar lo medido de lo que se le suma encima.
    informe = await servicio.reconocer(
        _RAIZ, max_depth=2, max_pages=10, delay_seconds=0, pausa_del_rastreo=0
    )

    assert informe.segundos_por_pagina == pytest.approx(0.5, abs=0.4)
    assert informe.segundos_estimados == pytest.approx(
        informe.urls_encontradas * informe.segundos_por_pagina, rel=0.01
    )


@pytest.mark.asyncio
async def test_la_estimacion_cuenta_la_pausa_de_cortesia_del_rastreo_de_verdad():
    """El reconocimiento va con prisa; el rastreo, con la cortesía del sitio.

    Estimar con la latencia del sondeo rápido daría minutos donde el rastreo real tarda horas: la
    pausa que se va a usar de verdad tiene que entrar en la cuenta aunque el sondeo no la use.
    """
    paginas = {_RAIZ: _pagina(f"{_RAIZ}a/"), f"{_RAIZ}a/": _pagina()}

    async def traer(url: str) -> tuple[str, dict]:
        return paginas.get(url, ("", {"content-type": "text/html"}))

    servicio = ReconocimientoDeSitio(fetch_fn=traer, clock_fn=_RelojFalso(paso=0.1))
    informe = await servicio.reconocer(
        _RAIZ, max_depth=2, max_pages=10, delay_seconds=0, pausa_del_rastreo=2.0
    )

    assert informe.segundos_estimados >= informe.urls_encontradas * 2.0


@pytest.mark.asyncio
async def test_un_filtro_acota_el_reconocimiento_al_apartado():
    """Se reconoce un apartado, no el portal entero: es la misma decisión que `url_regex_filter`."""
    paginas = {
        _RAIZ: _pagina(f"{_RAIZ}base/", "https://www.uji.es/otro-centro/"),
        f"{_RAIZ}base/": _pagina(),
    }

    async def traer(url: str) -> tuple[str, dict]:
        return paginas.get(url, ("", {"content-type": "text/html"}))

    servicio = ReconocimientoDeSitio(fetch_fn=traer, clock_fn=_RelojFalso())
    informe = await servicio.reconocer(
        _RAIZ, max_depth=2, max_pages=10, delay_seconds=0,
        url_regex_filter=r"escola-doctorat",
    )

    assert all("escola-doctorat" in u for u in informe.urls)
