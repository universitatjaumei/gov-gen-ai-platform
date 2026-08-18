"""Cortesía del rastreo: pausa, robots.txt, identificación y presupuesto (RAS.1).

El bucle del spider era `while queue: await self._fetch(url)`: secuencial, con `timeout` de 10 s y
**sin pausa entre peticiones ni lectura de `robots.txt`**. Contra un sitio de pruebas da igual;
contra el portal de la propia institución, miles de peticiones seguidas desde una IP figuran en los
registros del servidor web como lo que parecen.

La cortesía es el **defecto**, no una opción: un sitio dado de alta sin tocar nada rastrea despacio
y respetando `robots.txt`. Quitarla exige decirlo explícitamente en la configuración del sitio.

El reloj y la espera se inyectan porque medir una pausa de un segundo con el reloj de pared son
segundos de suite por cada test, y lo que hay que comprobar es que **se espera lo que toca**, no que
el sistema operativo duerme.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from server.app.modules.curation.cortesia import RutaProhibidaPorRobots
from server.app.modules.curation.spider import CrawlStatus, GenericSpider


@dataclass
class FakeSitio:
    root_url: str
    config_json: dict = field(default_factory=dict)


class _Reloj:
    """Reloj monótono que sólo avanza cuando alguien duerme."""

    def __init__(self) -> None:
        self.ahora = 0.0
        self.esperas: list[float] = []

    def __call__(self) -> float:
        return self.ahora

    async def dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)
        self.ahora += segundos


def _spider(paginas: dict[str, str], reloj: _Reloj, robots: str | None = None):
    """Un spider con reloj falso y un `robots.txt` opcional servido por el sitio."""
    pedidas: list[str] = []

    async def fetch(url: str) -> tuple[str, dict]:
        pedidas.append(url)
        if url.endswith("/robots.txt"):
            if robots is None:
                raise RuntimeError("404 robots.txt")
            return robots, {}
        return paginas.get(url, "<html></html>"), {}

    spider = GenericSpider(fetch_fn=fetch, sleep_fn=reloj.dormir, clock_fn=reloj)
    return spider, pedidas


# ---------------------------------------------------------------------------
# La pausa
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dos_peticiones_seguidas_al_mismo_host_van_separadas_por_la_pausa():
    reloj = _Reloj()
    spider, _ = _spider({}, reloj)

    await spider._fetch("https://www.uji.es/a")
    await spider._fetch("https://www.uji.es/b")

    # La segunda espera la pausa configurada por defecto; la primera no espera a nadie.
    assert reloj.esperas, "la segunda petición al mismo host salió sin pausa"
    assert sum(reloj.esperas) >= 1.0


@pytest.mark.asyncio
async def test_la_pausa_por_defecto_es_conservadora_sin_configurar_nada():
    """Un sitio recién dado de alta no puede rastrear a toda velocidad."""
    reloj = _Reloj()
    spider, _ = _spider({}, reloj)

    assert spider.pausa_efectiva_para("https://www.uji.es") >= 1.0


@pytest.mark.asyncio
async def test_la_pausa_se_puede_bajar_a_cero_pero_hay_que_decirlo():
    """El sitio de pruebas local es legítimo; lo que no vale es que sea el defecto."""
    reloj = _Reloj()
    spider, _ = _spider({"http://localhost:4174": "<html></html>"}, reloj)
    sitio = FakeSitio(
        root_url="http://localhost:4174",
        config_json={"crawl_depth": 0, "max_pages": 5, "delay_seconds": 0,
                     "respect_robots": False},
    )

    await spider.crawl(sitio)

    assert reloj.esperas == []


@pytest.mark.asyncio
async def test_una_pausa_no_penaliza_a_un_host_distinto():
    """La cortesía es por servidor: esperar por uno mientras se lee otro no protege a nadie."""
    reloj = _Reloj()
    spider, _ = _spider({}, reloj)

    await spider._fetch("https://www.uji.es/a")
    await spider._fetch("https://otro.example.org/a")

    assert reloj.esperas == []


# ---------------------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------------------

_ROBOTS = """User-agent: *
Disallow: /privado/
"""


@pytest.mark.asyncio
async def test_una_ruta_prohibida_por_robots_no_se_pide():
    reloj = _Reloj()
    spider, pedidas = _spider({}, reloj, robots=_ROBOTS)

    with pytest.raises(RutaProhibidaPorRobots):
        await spider._fetch("https://www.uji.es/privado/expedientes")

    assert not any("privado" in u for u in pedidas)


@pytest.mark.asyncio
async def test_una_ruta_permitida_por_robots_si_se_pide():
    reloj = _Reloj()
    spider, pedidas = _spider({}, reloj, robots=_ROBOTS)

    await spider._fetch("https://www.uji.es/estudis/doctorat")

    assert "https://www.uji.es/estudis/doctorat" in pedidas


@pytest.mark.asyncio
async def test_el_robots_se_pide_una_sola_vez_por_host():
    """Pedirlo en cada URL sería multiplicar por dos el tráfico que se quiere reducir."""
    reloj = _Reloj()
    spider, pedidas = _spider({}, reloj, robots=_ROBOTS)

    await spider._fetch("https://www.uji.es/a")
    await spider._fetch("https://www.uji.es/b")
    await spider._fetch("https://www.uji.es/c")

    assert len([u for u in pedidas if u.endswith("/robots.txt")]) == 1


@pytest.mark.asyncio
async def test_sin_robots_el_rastreo_sigue_pero_no_deja_de_ser_cortes():
    """Un 404 en robots.txt no autoriza nada: sólo significa que el sitio no dice nada."""
    reloj = _Reloj()
    spider, pedidas = _spider({}, reloj, robots=None)

    await spider._fetch("https://www.uji.es/a")

    assert "https://www.uji.es/a" in pedidas
    assert spider.pausa_efectiva_para("https://www.uji.es") >= 1.0


@pytest.mark.asyncio
async def test_un_crawl_delay_mayor_que_el_nuestro_gana():
    reloj = _Reloj()
    spider, _ = _spider({}, reloj, robots="User-agent: *\nCrawl-delay: 5\n")

    await spider._fetch("https://www.uji.es/a")

    assert spider.pausa_efectiva_para("https://www.uji.es") == 5.0


@pytest.mark.asyncio
async def test_un_crawl_delay_menor_que_el_nuestro_no_nos_acelera():
    """El sitio nos autoriza a ir más rápido; no tenemos por qué aceptarlo."""
    reloj = _Reloj()
    spider, _ = _spider({}, reloj, robots="User-agent: *\nCrawl-delay: 0.1\n")

    await spider._fetch("https://www.uji.es/a")

    assert spider.pausa_efectiva_para("https://www.uji.es") >= 1.0


@pytest.mark.asyncio
async def test_el_spider_no_encola_lo_que_robots_prohibe():
    """Si la prohibición sólo se comprobara al pedir, el rastreo se llenaría de errores."""
    reloj = _Reloj()
    paginas = {
        "https://www.uji.es/inicio": (
            '<html><a href="/privado/interno">interno</a>'
            '<a href="/publico/pagina">publico</a></html>'
        ),
    }
    spider, pedidas = _spider(paginas, reloj, robots=_ROBOTS)
    sitio = FakeSitio(
        root_url="https://www.uji.es/inicio",
        config_json={"crawl_depth": 1, "max_pages": 10, "delay_seconds": 0},
    )

    resultado = await spider.crawl(sitio)

    assert not any("privado" in u for u in resultado.crawled_urls)
    assert not any("privado" in u for u in pedidas)
    assert "https://www.uji.es/publico/pagina" in resultado.crawled_urls


# ---------------------------------------------------------------------------
# Quién es y a quién escribir
# ---------------------------------------------------------------------------


def test_el_user_agent_identifica_al_sistema_y_a_un_contacto():
    """Quien vea el tráfico en sus registros tiene que poder saber a quién escribir."""
    from server.app.modules.curation.cortesia import user_agent_de_rastreo

    agente = user_agent_de_rastreo(contacto="curacion@uji.es")

    assert "GovGenAI" in agente
    assert "curacion@uji.es" in agente


def test_sin_contacto_configurado_el_user_agent_lo_dice_en_vez_de_callarlo():
    from server.app.modules.curation.cortesia import user_agent_de_rastreo

    agente = user_agent_de_rastreo(contacto="")

    assert "GovGenAI" in agente
    assert "sin contacto" in agente.lower()


# ---------------------------------------------------------------------------
# Presupuesto
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agotado_el_presupuesto_de_tiempo_el_rastreo_para_y_dice_cuanto_dejo():
    reloj = _Reloj()
    enlaces = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(30))
    paginas = {"https://www.uji.es": f"<html>{enlaces}</html>"}
    spider, _ = _spider(paginas, reloj)
    sitio = FakeSitio(
        root_url="https://www.uji.es",
        config_json={"crawl_depth": 2, "max_pages": 500, "delay_seconds": 2,
                     "max_seconds": 6, "respect_robots": False},
    )

    resultado = await spider.crawl(sitio)

    assert resultado.status == CrawlStatus.COMPLETED_PARTIAL
    assert resultado.stop_reason == "time_budget"
    assert resultado.pages_skipped > 0
    assert resultado.pages_crawled < 30


@pytest.mark.asyncio
async def test_al_truncar_por_paginas_el_motivo_tambien_consta():
    reloj = _Reloj()
    enlaces = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(20))
    paginas = {"https://www.uji.es": f"<html>{enlaces}</html>"}
    spider, _ = _spider(paginas, reloj)
    sitio = FakeSitio(
        root_url="https://www.uji.es",
        config_json={"crawl_depth": 2, "max_pages": 3, "delay_seconds": 0,
                     "respect_robots": False},
    )

    resultado = await spider.crawl(sitio)

    assert resultado.status == CrawlStatus.COMPLETED_PARTIAL
    assert resultado.stop_reason == "max_pages"
    assert resultado.pages_skipped > 0


@pytest.mark.asyncio
async def test_un_rastreo_que_cabe_en_el_presupuesto_no_dice_que_lo_trunco_nadie():
    reloj = _Reloj()
    paginas = {"https://www.uji.es": "<html>sin enlaces</html>"}
    spider, _ = _spider(paginas, reloj)
    sitio = FakeSitio(
        root_url="https://www.uji.es",
        config_json={"crawl_depth": 1, "max_pages": 10, "delay_seconds": 0,
                     "respect_robots": False},
    )

    resultado = await spider.crawl(sitio)

    assert resultado.status == CrawlStatus.COMPLETED
    assert resultado.stop_reason is None


# ---------------------------------------------------------------------------
# Concurrencia
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_la_concurrencia_por_host_esta_acotada():
    """Nunca ilimitada: es la otra mitad de no parecer un ataque."""
    import asyncio

    en_vuelo = 0
    maximo = 0

    async def fetch(url: str) -> tuple[str, dict]:
        nonlocal en_vuelo, maximo
        en_vuelo += 1
        maximo = max(maximo, en_vuelo)
        await asyncio.sleep(0)
        en_vuelo -= 1
        return "<html></html>", {}

    spider = GenericSpider(fetch_fn=fetch, sleep_fn=_Reloj().dormir, clock_fn=_Reloj())
    spider.configurar_cortesia({"delay_seconds": 0, "respect_robots": False,
                                "max_concurrency": 2})

    await asyncio.gather(*[spider._fetch(f"https://www.uji.es/p{i}") for i in range(8)])

    assert maximo <= 2
