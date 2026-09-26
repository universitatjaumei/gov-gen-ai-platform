"""Issue #161 — cerrar la ventana del *DNS rebinding*.

**El defecto que quedaba admitido por escrito.** `red_publica.py` decía, y era verdad: «entre
resolver el nombre y abrir la conexión, httpx resuelve otra vez, y un DNS hostil puede devolver
algo distinto en esa segunda vuelta». La comprobación de APER.1 cerraba el caso fácil —un nombre
que publica una dirección privada— y dejaba abierta la carrera.

**Dónde muerde.** La superficie es el rastreador de portales, que es el único componente que
visita URLs que no elige el proyecto: las da de alta un administrador de organización. En esta VM,
alcanzar una dirección privada desde dentro llega al servidor de metadatos de GCP
(`169.254.169.254`), y ahí están las credenciales de la cuenta de servicio — que tiene
`cloudsql.client` y acceso al bucket. No es un agujero teórico, es robo de credenciales.

**Por qué no bastaba con comprobar mejor.** El problema no es qué se comprueba sino **cuándo**:
por buena que sea la comprobación, si después alguien resuelve el nombre otra vez, se conecta a lo
que diga la segunda respuesta. La única forma de cerrarlo es **conectar a la dirección que ya se
validó**, y conservar el nombre para el SNI y la cabecera `Host` para que TLS siga validándose
contra el certificado correcto.

**El test que lo demuestra** es `test_el_dns_que_cambia_de_respuesta_no_mueve_la_conexion`: un
resolvedor que devuelve una dirección pública la primera vez y `169.254.169.254` la segunda. Con
el arreglo la conexión va a la primera, porque **no hay segunda vez**.
"""

from __future__ import annotations

import httpx
import pytest

from server.app.core.red_publica import (
    DestinoNoPublico,
    fijar_destino_validado,
)


def _peticion(url: str) -> httpx.Request:
    return httpx.Request("GET", url)


def _resolvedor(*respuestas: list[str]):
    """Un DNS que va devolviendo una respuesta distinta en cada llamada."""
    llamadas = {"n": 0}

    async def resolver(host: str) -> list[str]:
        i = min(llamadas["n"], len(respuestas) - 1)
        llamadas["n"] += 1
        return respuestas[i]

    resolver.llamadas = llamadas
    return resolver


class TestLaConexionVaALaDireccionValidada:

    async def test_el_nombre_se_sustituye_por_su_direccion(self):
        peticion = _peticion("https://portal.example/seccion")

        await fijar_destino_validado(peticion, resolver=_resolvedor(["93.184.216.34"]))

        assert peticion.url.host == "93.184.216.34"

    async def test_el_nombre_sobrevive_para_el_certificado_y_la_cabecera(self):
        """Sin esto el arreglo rompería TLS y el servidor virtual del otro extremo.

        El certificado se valida contra el nombre, no contra la dirección, así que hay que pasar
        `sni_hostname`; y un servidor que aloja varios sitios decide por la cabecera `Host`.
        Cambiar la URL a secas convertiría el arreglo de seguridad en una avería.
        """
        peticion = _peticion("https://portal.example/seccion")

        await fijar_destino_validado(peticion, resolver=_resolvedor(["93.184.216.34"]))

        assert peticion.extensions.get("sni_hostname") == "portal.example"
        assert peticion.headers["Host"] == "portal.example"

    async def test_el_puerto_no_se_pierde(self):
        peticion = _peticion("https://portal.example:8443/x")

        await fijar_destino_validado(peticion, resolver=_resolvedor(["93.184.216.34"]))

        assert peticion.url.port == 8443
        assert peticion.headers["Host"] == "portal.example:8443"

    async def test_una_direccion_ipv6_se_escribe_entre_corchetes(self):
        peticion = _peticion("https://portal.example/x")

        await fijar_destino_validado(peticion, resolver=_resolvedor(["2606:2800:220:1::1"]))

        assert peticion.url.host == "2606:2800:220:1::1"
        assert "[2606:2800:220:1::1]" in str(peticion.url)


class TestLaVentanaDelRebinding:

    async def test_el_dns_que_cambia_de_respuesta_no_mueve_la_conexion(self):
        """**El defecto, reproducido.** Pública al validar, privada al conectar.

        Con la versión anterior este escenario terminaba con httpx conectando a
        `169.254.169.254`, porque la comprobación y la conexión preguntaban al DNS por separado.
        Ahora sólo se pregunta una vez y se conecta a lo que esa vez dijo.
        """
        resolver = _resolvedor(["93.184.216.34"], ["169.254.169.254"])
        peticion = _peticion("https://portal.example/seccion")

        await fijar_destino_validado(peticion, resolver=resolver)

        assert peticion.url.host == "93.184.216.34"
        assert resolver.llamadas["n"] == 1, (
            "se ha resuelto el nombre más de una vez: cada resolución de más es una ventana "
            "para que el DNS conteste otra cosa, que es exactamente el defecto."
        )

    async def test_si_alguna_direccion_es_privada_no_se_conecta_a_ninguna(self):
        """Elegir la buena de entre varias no es trabajo de quien pide la página: un nombre que
        publica una pública y una privada es el patrón del rebinding y se rechaza entero."""
        peticion = _peticion("https://portal.example/x")

        with pytest.raises(DestinoNoPublico):
            await fijar_destino_validado(
                peticion, resolver=_resolvedor(["93.184.216.34", "10.0.0.5"])
            )

    async def test_un_nombre_que_no_resuelve_no_se_pide(self):
        async def resolver(host: str) -> list[str]:
            raise OSError("no such host")

        with pytest.raises(DestinoNoPublico):
            await fijar_destino_validado(_peticion("https://portal.example/x"), resolver=resolver)


class TestLoQueNoDebeRomper:

    async def test_una_direccion_literal_no_se_resuelve(self):
        """Ya la validó `assert_forma_publica`, y resolverla no tendría sentido."""
        resolver = _resolvedor(["10.0.0.1"])
        peticion = _peticion("https://93.184.216.34/x")

        await fijar_destino_validado(peticion, resolver=resolver)

        assert peticion.url.host == "93.184.216.34"
        assert resolver.llamadas["n"] == 0

    async def test_con_la_valvula_abierta_el_portal_local_sigue_funcionando(self, monkeypatch):
        """Sin la válvula no se puede verificar curación sin salir a internet, y un guardia que
        impide trabajar acaba apagado del todo — que es peor."""
        monkeypatch.setenv("CRAWLER_ALLOW_PRIVATE_TARGETS", "true")
        resolver = _resolvedor(["127.0.0.1"])
        peticion = _peticion("http://localhost:8000/x")

        await fijar_destino_validado(peticion, resolver=resolver)

        assert peticion.url.host == "localhost"
        assert resolver.llamadas["n"] == 0
