"""La aplicación confía en el proxy para el esquema, y **sólo** en él (issue #99).

**Lo que pasaba.** Uvicorn honra `X-Forwarded-Proto` sólo si quien conecta está en
`forwarded_allow_ips`, cuyo defecto es `127.0.0.1,::1`. Caddy conecta desde la red de Docker
(`reverse_proxy app:8000`), así que la cabecera llegaba y **no se honraba**: toda URL deducida de
la petición salía con esquema `http://` aunque el cliente hubiera entrado por `https://`.

**Ya mordió una vez.** La primera versión del login con Google construía el `redirect_uri` con
`request.url_for()`, lo que habría dado `http://normativa.uji.es/...`. Google rechaza un
`redirect_uri` sin TLS fuera de `localhost`, así que habría sido un `redirect_uri_mismatch` con el
fallo en un sitio que ese mensaje no señala. Se resolvió declarando la URL.

**Y el siguiente en morder es el SAML**, que está apagado. `saml/request_adapter.py` hace
`"https": "on" if url.scheme == "https" else "off"`, y con eso OneLogin reconstruye la URL actual
para **validar el `Destination` y el `Recipient` de la aserción**. Con el esquema deducido como
`http`, esa reconstrucción no coincide con el ACS declarado —que es `https://…`— y la aserción se
rechaza. El día que llegue el IdP, esto es lo primero que falla, con un mensaje de validación SAML
que no menciona proxies.

**Por qué no `*`, que es el arreglo fácil y equivocado.** Confiar en `X-Forwarded-Proto` de
cualquiera deja que un cliente decida el esquema que la aplicación cree estar sirviendo, y de ahí
salen suplantaciones y enlaces envenenados. El test de la IP no admitida está justamente para que
ese atajo no pase.
"""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
COMPOSE = RAIZ / "deploy" / "vm" / "docker-compose.vm.yml"

_VARIABLE = "FORWARDED_ALLOW_IPS"


def _esquema_visto(cliente: str, confiados: str) -> str:
    """El esquema que vería la aplicación para una petición con `X-Forwarded-Proto: https`.

    Se ejercita el middleware real de uvicorn, no una imitación: lo que se quiere comprobar es
    su decisión, y una imitación comprobaría la mía.
    """
    import asyncio

    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    visto: dict[str, str] = {}

    async def _app(scope, receive, send):
        visto["scheme"] = scope["scheme"]

    envuelta = ProxyHeadersMiddleware(_app, trusted_hosts=confiados)
    scope = {
        "type": "http",
        "scheme": "http",
        "client": (cliente, 54321),
        "headers": [
            (b"x-forwarded-proto", b"https"),
            (b"x-forwarded-for", cliente.encode()),
        ],
    }

    async def _receive():  # pragma: no cover - no se consume
        return {"type": "http.request"}

    async def _send(mensaje):  # pragma: no cover - no se envía nada
        return None

    asyncio.run(envuelta(scope, _receive, _send))
    return visto["scheme"]


class TestElMiddlewareDecideComoEsperamos:
    """La premisa, medida sobre uvicorn y no supuesta."""

    def test_con_el_defecto_de_uvicorn_la_cabecera_de_docker_se_ignora(self) -> None:
        """El defecto es `127.0.0.1`, y Caddy no conecta desde ahí. Éste es el defecto."""
        assert _esquema_visto("172.18.0.5", "127.0.0.1") == "http"

    def test_desde_una_ip_admitida_el_esquema_es_el_del_proxy(self) -> None:
        assert _esquema_visto("172.18.0.5", "172.16.0.0/12") == "https"

    def test_desde_una_ip_no_admitida_la_cabecera_se_ignora(self) -> None:
        """**El test que impide que el arreglo sea `*`.**

        Si alguien cambia el valor por `*` para «que funcione», esto se pone rojo: con `*`
        cualquiera decide el esquema que la aplicación cree estar sirviendo.
        """
        assert _esquema_visto("203.0.113.7", "172.16.0.0/12") == "http"


def _entorno_de_la_aplicacion() -> dict:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    entorno = compose["services"]["app"].get("environment") or {}
    if isinstance(entorno, dict):
        return entorno
    return dict(e.split("=", 1) for e in entorno if "=" in str(e))


class TestElDespliegueLoDejaPuesto:
    def test_el_compose_declara_la_variable(self) -> None:
        assert _VARIABLE in _entorno_de_la_aplicacion(), (
            f"el servicio `app` no declara `{_VARIABLE}`, así que uvicorn se queda con su "
            "defecto `127.0.0.1` y **ignora** lo que diga Caddy"
        )

    def test_no_confia_en_cualquiera(self) -> None:
        valor = str(_entorno_de_la_aplicacion().get(_VARIABLE, ""))
        assert "*" not in valor, (
            f"`{_VARIABLE}` vale «{valor}»: con `*` cualquier cliente decide el esquema que la "
            "aplicación cree estar sirviendo. Acótalo a la red desde la que conecta Caddy."
        )

    def test_el_valor_es_una_red_privada(self) -> None:
        """Que lo acotado sea de verdad privado, y no un rango cualquiera escrito con prisa."""
        import ipaddress

        valor = str(_entorno_de_la_aplicacion().get(_VARIABLE, ""))
        trozos = [t.strip() for t in valor.split(",") if t.strip()]
        assert trozos, f"`{_VARIABLE}` está vacía"
        for trozo in trozos:
            red = ipaddress.ip_network(trozo, strict=False)
            assert red.is_private or red.is_loopback, (
                f"«{trozo}» no es una red privada: confiar en direcciones públicas para el "
                "esquema es lo que este guardarraíl viene a impedir"
            )
