"""APER.1 — el rastreador de curación, que es el único que pide una URL que elige quien llama.

Los otros cinco clientes HTTP del servidor —precios, catálogo de modelos, sandbox, reranker y la
publicación del corpus— piden URL que salen de la **configuración**, no del cuerpo de una
petición. El spider es el que recibe `root_url` de `POST /hub/sites` y de
`POST /hub/site-reconnaissance`, y por eso es el único que necesita guardia.

Dos niveles, y hacen falta los dos:

- **La forma, en el contrato de entrada**: quien da de alta un sitio con una dirección privada
  recibe un 422 con el motivo, no un rastreo que devuelve cero páginas sin decir por qué.
- **El destino, en cada petición**: es lo que cierra la redirección, y es donde el defecto vivía
  de verdad. El contrato no puede verla, porque la redirección la decide el servidor remoto.
"""

import httpx
import pytest
from pydantic import ValidationError

from server.app.core import red_publica
from server.app.core.red_publica import DestinoNoPublico
from server.app.modules.curation import spider as spider_module
from server.app.modules.curation.selection_contracts import (
    ReconnaissanceRequest,
    SiteCreate,
    SitePatch,
)
from server.app.modules.curation.spider import GenericSpider, cliente_de_rastreo

METADATOS = "http://169.254.169.254/computeMetadata/v1/"


def _resolver_fijo(mapa: dict[str, list[str]]):
    async def resolver(host: str) -> list[str]:
        if host not in mapa:
            raise OSError(f"no resuelve: {host}")
        return mapa[host]

    return resolver


class TestElContratoDeEntrada:
    """Lo que se rechaza al dar de alta el sitio, sin preguntar al DNS."""

    @pytest.mark.parametrize(
        "root_url",
        [METADATOS, "http://127.0.0.1:8000/", "http://10.0.0.5/", "file:///etc/passwd"],
    )
    def test_crear_un_sitio_con_destino_no_publico_es_422(self, root_url: str) -> None:
        with pytest.raises(ValidationError):
            SiteCreate(name="intento", root_url=root_url)

    def test_el_sitemap_tambien_se_comprueba(self) -> None:
        """Se pide igual que la raíz, así que se valida igual. Era la puerta de al lado."""
        with pytest.raises(ValidationError):
            SiteCreate(
                name="intento",
                root_url="https://www.uji.es/",
                sitemap_url="http://127.0.0.1/sitemap.xml",
            )

    def test_un_portal_publico_se_crea(self) -> None:
        sitio = SiteCreate(
            name="UJI",
            root_url="https://www.uji.es/base/calendari",
            sitemap_url="https://www.uji.es/sitemap.xml",
        )
        assert sitio.root_url.endswith("/calendari")

    def test_modificar_un_sitio_tampoco_deja_meterlo(self) -> None:
        """Si sólo se validara al crear, el `PATCH` sería el rodeo obvio."""
        with pytest.raises(ValidationError):
            SitePatch(root_url=METADATOS)

    def test_un_patch_que_no_toca_la_url_sigue_valiendo(self) -> None:
        assert SitePatch(name="otro nombre").root_url is None

    def test_el_reconocimiento_tampoco(self) -> None:
        """Es el que devuelve el texto leído, así que era el más rentable de los dos."""
        with pytest.raises(ValidationError):
            ReconnaissanceRequest(root_url=METADATOS)

    def test_el_motivo_del_422_explica_que_hacer(self) -> None:
        with pytest.raises(ValidationError) as exc:
            SiteCreate(name="intento", root_url=METADATOS)
        assert "red pública" in str(exc.value)


class TestLaDescargaDelSpider:
    """El guardia en la petición: lo que cierra la redirección."""

    async def test_no_pide_una_direccion_de_su_propia_red(self) -> None:
        spider = GenericSpider()
        spider.configurar_cortesia({})
        with pytest.raises(DestinoNoPublico):
            await spider._descargar("http://127.0.0.1:8000/admin")

    async def test_no_sigue_una_redireccion_a_la_red_interna(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """El defecto entero, por donde de verdad se escapaba.

        Se monta con el cliente **de verdad** —`cliente_de_rastreo`, con su hook— y sólo se
        sustituye el transporte, así que lo que se prueba es la protección y no el doble. El
        primer salto tiene que pasar: si el resolvedor falso no diera `portal.example` por
        pública, este test se pondría verde por la razón equivocada, y por eso se comprueba que
        el motivo nombra la **dirección del segundo salto**.
        """
        monkeypatch.setattr(
            red_publica,
            "_resolver_por_dns",
            _resolver_fijo({"portal.example": ["93.184.216.34"]}),
        )

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "portal.example":
                return httpx.Response(302, headers={"Location": METADATOS})
            return httpx.Response(200, text="EL-TOKEN-DE-LA-CUENTA-DE-SERVICIO")

        monkeypatch.setattr(
            spider_module,
            "cliente_de_rastreo",
            lambda ua, **kw: cliente_de_rastreo(
                ua, transport=httpx.MockTransport(handler)
            ),
        )

        spider = GenericSpider()
        spider.configurar_cortesia({})
        with pytest.raises(DestinoNoPublico) as exc:
            await spider._descargar("http://portal.example/")
        assert "169.254.169.254" in str(exc.value), (
            "Se ha parado en el primer salto, no en la redirección: este test no está "
            "midiendo lo que dice medir."
        )

    async def test_una_pagina_publica_se_descarga(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """El camino bueno: el guardia no puede estar cerrando el rastreo de verdad."""
        monkeypatch.setattr(
            red_publica,
            "_resolver_por_dns",
            _resolver_fijo({"www.uji.es": ["150.128.81.10"]}),
        )
        monkeypatch.setattr(
            spider_module,
            "cliente_de_rastreo",
            lambda ua, **kw: cliente_de_rastreo(
                ua,
                transport=httpx.MockTransport(
                    lambda _r: httpx.Response(
                        200,
                        text="<html>calendari</html>",
                        headers={"content-type": "text/html"},
                    )
                ),
            ),
        )

        spider = GenericSpider()
        spider.configurar_cortesia({})
        html, cabeceras = await spider._descargar("https://www.uji.es/base/calendari")
        assert "calendari" in html
        assert cabeceras["x-final-url"] == "https://www.uji.es/base/calendari"


class TestElRastreoNoSeCae:
    """Un destino prohibido se cuenta como fallo de esa página, no tumba la ejecución."""

    async def test_una_raiz_privada_devuelve_cero_paginas_y_lo_dice(self) -> None:
        class _Fuente:
            root_url = "http://10.0.0.5/portal"
            config_json: dict = {"crawl_depth": 0, "max_pages": 5, "respect_robots": False}
            crawl_frontier = None

        resultado = await GenericSpider().crawl(_Fuente())

        assert resultado.crawled_urls == []
        assert resultado.fallos, "el rastreo no ha registrado por qué no leyó nada"
        assert "red pública" in resultado.fallos[0]["message"]


class TestNoHayOtraPuerta:
    """El guardarraíl: si mañana alguien construye otro cliente aquí, la protección se esquiva."""

    def test_el_unico_cliente_http_del_modulo_es_el_de_rastreo(self) -> None:
        from pathlib import Path

        modulo = Path(spider_module.__file__).parent
        culpables: list[str] = []
        for fichero in sorted(modulo.glob("*.py")):
            texto = fichero.read_text(encoding="utf-8")
            if "httpx.AsyncClient(" not in texto:
                continue
            # El único permitido es la fábrica que instala el hook.
            if fichero.name == "spider.py" and "def cliente_de_rastreo" in texto:
                continue
            culpables.append(fichero.name)

        assert not culpables, (
            "Estos ficheros de curación construyen su propio cliente HTTP y se saltan el "
            f"guardia de APER.1: {culpables}. Usa `cliente_de_rastreo`."
        )

    def test_la_fabrica_instala_el_hook(self) -> None:
        """Que exista la fábrica no basta: tiene que llevar el hook puesto."""
        cliente = cliente_de_rastreo("GovGenAI-Curacion/test")
        hooks = cliente.event_hooks["request"]
        assert hooks, "el cliente de rastreo no lleva ningún hook de petición"
