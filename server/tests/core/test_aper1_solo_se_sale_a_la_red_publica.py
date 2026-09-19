"""APER.1 — el servidor no pide una URL que apunte a su propia red.

**El agujero, medido antes de escribir esto.** `POST /api/v1/hub/sites` y
`POST /api/v1/hub/site-reconnaissance` aceptan `root_url` como `str` sin validar, y el spider
descargaba con `httpx.AsyncClient(follow_redirects=True, …)`. Cualquier **administrador de
organización** —no hace falta superadministrador— podía hacer que el servidor pidiera
`http://169.254.169.254/…`, los otros contenedores del compose o cualquier servicio HTTP sin
autenticación de la red interna, y leer de vuelta el texto por el informe de reconocimiento.

La redirección es la mitad importante del defecto, y la que hace inútil comprobar sólo la URL de
entrada: un portal público que redirige a una dirección privada la alcanza igual. Comprobado con
`MockTransport` antes de arreglar nada: el cuerpo de la segunda petición llegaba.

**Por qué la comprobación va en dos piezas.** La **forma** (esquema y dirección literal) no
necesita DNS, así que la hacen los contratos de entrada y devuelve 422 con motivo. El **destino**
resuelve el nombre y se aplica **en cada salto** —el hook de `httpx` se dispara también en las
redirecciones, verificado con la versión instalada—, y ahí es donde el defecto se cierra de verdad.

**Y la válvula.** Verificar curación sin salir a internet se hace con un `http.server` en
`127.0.0.1`, que es exactamente lo que esto bloquea. `CRAWLER_ALLOW_PRIVATE_TARGETS=true` lo
permite, y **producción se niega a arrancar con ella puesta**, como con `SANDBOX_MODE=local`. Sin
la válvula, el guardia se acabaría apagando entero para poder trabajar.
"""

import httpx
import pytest

from server.app.core.red_publica import (
    DestinoNoPublico,
    assert_destino_publico,
    assert_forma_publica,
    hook_de_destino_publico,
)


def _resolver_fijo(mapa: dict[str, list[str]]):
    """Un resolvedor de mentira: la suite no pregunta al DNS de nadie."""

    async def resolver(host: str) -> list[str]:
        if host not in mapa:
            raise OSError(f"no resuelve: {host}")
        return mapa[host]

    return resolver


class TestLaFormaDeLaUrl:
    """Lo que se puede decidir sin preguntar al DNS. Es lo que valida la entrada de la API."""

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://interno/_",
            "ftp://interno/",
            "data:text/html,<h1>",
        ],
    )
    def test_solo_http_y_https(self, url: str) -> None:
        with pytest.raises(DestinoNoPublico):
            assert_forma_publica(url)

    @pytest.mark.parametrize("url", ["", "   ", "no-es-una-url", "//sin-esquema/ruta"])
    def test_sin_esquema_o_sin_host_no_se_adivina(self, url: str) -> None:
        with pytest.raises(DestinoNoPublico):
            assert_forma_publica(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8000/admin",
            "http://127.1/",
            "http://0.0.0.0/",
            "http://10.0.0.5/",
            "http://192.168.1.10/",
            "http://172.16.0.1/",
            "http://[::1]/",
            "http://[fe80::1]/",
        ],
    )
    def test_una_direccion_literal_no_publica_se_rechaza(self, url: str) -> None:
        with pytest.raises(DestinoNoPublico):
            assert_forma_publica(url)

    def test_el_servidor_de_metadatos_de_la_nube(self) -> None:
        """El caso que da el premio gordo: el token de la cuenta de servicio.

        Que GCP exija la cabecera `Metadata-Flavor: Google` —y el spider no la mande— es una
        mitigación de GCP, no nuestra. No se apoya el arreglo en ella.
        """
        with pytest.raises(DestinoNoPublico):
            assert_forma_publica(
                "http://169.254.169.254/computeMetadata/v1/instance/"
                "service-accounts/default/token"
            )

    def test_una_direccion_ipv4_disfrazada_de_ipv6(self) -> None:
        """`::ffff:127.0.0.1` es 127.0.0.1 con otra ropa, y es el rodeo clásico."""
        with pytest.raises(DestinoNoPublico):
            assert_forma_publica("http://[::ffff:127.0.0.1]/")

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.uji.es/",
            "http://www.uji.es/base/calendari",
            "https://normativa.uji.es/",
            "https://93.184.216.34/",
        ],
    )
    def test_un_portal_publico_pasa_sin_preguntar_al_dns(self, url: str) -> None:
        assert_forma_publica(url)


class TestElDestinoResuelto:
    """Con el nombre resuelto. Es lo que se aplica en cada petición, y en cada redirección."""

    async def test_un_nombre_que_resuelve_a_privada_se_rechaza(self) -> None:
        """El nombre de un servicio del compose: `db`, `minio`, `script-sandbox`."""
        with pytest.raises(DestinoNoPublico):
            await assert_destino_publico(
                "http://db:5432/", resolver=_resolver_fijo({"db": ["172.18.0.2"]})
            )

    async def test_un_nombre_publico_pasa(self) -> None:
        await assert_destino_publico(
            "https://www.uji.es/",
            resolver=_resolver_fijo({"www.uji.es": ["150.128.81.10"]}),
        )

    async def test_si_resuelve_a_publica_y_a_privada_se_rechaza(self) -> None:
        """Conservador a propósito: un nombre con las dos cosas es el patrón del rebinding.

        Esto **no** cierra el DNS rebinding —para eso habría que conectar a la dirección ya
        resuelta, y eso es rehacer el transporte—, pero sí el caso fácil de un nombre que
        publica las dos y confía en que se elija la buena.
        """
        with pytest.raises(DestinoNoPublico):
            await assert_destino_publico(
                "http://mixto.example/",
                resolver=_resolver_fijo({"mixto.example": ["93.184.216.34", "10.0.0.7"]}),
            )

    async def test_un_nombre_que_no_resuelve_se_rechaza(self) -> None:
        """No se adivina. Un nombre que no resuelve tampoco se puede rastrear."""
        with pytest.raises(DestinoNoPublico):
            await assert_destino_publico(
                "http://no-existe.example/", resolver=_resolver_fijo({})
            )

    async def test_la_direccion_resuelta_aparece_en_el_motivo(self) -> None:
        """Quien lea el error tiene que poder arreglarlo sin leer este código."""
        with pytest.raises(DestinoNoPublico) as exc:
            await assert_destino_publico(
                "http://db:5432/", resolver=_resolver_fijo({"db": ["172.18.0.2"]})
            )
        assert "172.18.0.2" in str(exc.value)
        assert "db" in str(exc.value)


class TestElHookDeHttpx:
    """La pieza que cierra la redirección, que es por donde se escapaba."""

    @staticmethod
    def _transporte_que_redirige_a_los_metadatos() -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "portal.example":
                return httpx.Response(
                    302,
                    headers={"Location": "http://169.254.169.254/computeMetadata/v1/"},
                )
            return httpx.Response(200, text="EL-SECRETO-DE-LA-RED-INTERNA")

        return httpx.MockTransport(handler)

    async def test_una_redireccion_a_la_red_interna_no_se_sigue(self) -> None:
        resolver = _resolver_fijo({"portal.example": ["93.184.216.34"]})
        async with httpx.AsyncClient(
            transport=self._transporte_que_redirige_a_los_metadatos(),
            follow_redirects=True,
            event_hooks={"request": [hook_de_destino_publico(resolver=resolver)]},
        ) as cliente:
            with pytest.raises(DestinoNoPublico):
                await cliente.get("http://portal.example/")

    async def test_sin_el_hook_el_cuerpo_llegaba(self) -> None:
        """El defecto, reproducido. Si este test se pone rojo es que ya no hay nada que arreglar."""
        async with httpx.AsyncClient(
            transport=self._transporte_que_redirige_a_los_metadatos(),
            follow_redirects=True,
        ) as cliente:
            respuesta = await cliente.get("http://portal.example/")
        assert respuesta.text == "EL-SECRETO-DE-LA-RED-INTERNA"

    async def test_una_peticion_publica_pasa(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>pagina</html>")

        resolver = _resolver_fijo({"portal.example": ["93.184.216.34"]})
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
            event_hooks={"request": [hook_de_destino_publico(resolver=resolver)]},
        ) as cliente:
            respuesta = await cliente.get("http://portal.example/")
        assert respuesta.status_code == 200


class TestLaValvulaDeDesarrollo:
    """`CRAWLER_ALLOW_PRIVATE_TARGETS`: el portal de pruebas en 127.0.0.1 tiene que seguir yendo."""

    def test_apagada_por_defecto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CRAWLER_ALLOW_PRIVATE_TARGETS", raising=False)
        with pytest.raises(DestinoNoPublico):
            assert_forma_publica("http://127.0.0.1:8001/portal/")

    def test_encendida_permite_el_portal_local(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CRAWLER_ALLOW_PRIVATE_TARGETS", "true")
        assert_forma_publica("http://127.0.0.1:8001/portal/")

    async def test_encendida_permite_el_destino_resuelto(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CRAWLER_ALLOW_PRIVATE_TARGETS", "true")
        await assert_destino_publico(
            "http://db:5432/", resolver=_resolver_fijo({"db": ["172.18.0.2"]})
        )

    def test_encendida_no_abre_la_puerta_a_otros_esquemas(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """La válvula es sobre **direcciones**, no sobre `file://`. Nada necesita eso."""
        monkeypatch.setenv("CRAWLER_ALLOW_PRIVATE_TARGETS", "true")
        with pytest.raises(DestinoNoPublico):
            assert_forma_publica("file:///etc/passwd")

    def test_produccion_no_arranca_con_la_valvula_puesta(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """El mismo trato que `SANDBOX_MODE=local`: en producción no es una opción, es un fallo.

        Sin este gate la válvula es peor que no tener guardia, porque da la impresión de haberlo.
        """
        from server.app.core.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "un-secreto-de-verdad-de-treinta-y-dos-o-mas")
        monkeypatch.setenv("SANDBOX_MODE", "http")
        monkeypatch.delenv("TESTING", raising=False)
        monkeypatch.setenv("CRAWLER_ALLOW_PRIVATE_TARGETS", "true")

        with pytest.raises(RuntimeError, match="CRAWLER_ALLOW_PRIVATE_TARGETS"):
            get_settings()
