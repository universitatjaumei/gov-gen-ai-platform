"""Limitación de peticiones (Prompt SEC.4, Parte 1).

SEC.1 puso contraseña en el login de Admin. Nada impedía probar diccionarios contra ella al
ritmo que diera la red, y el hash de descarte que protege del oráculo temporal no ayuda en
eso: hace lento cada intento, no pocos los intentos.

Este limitador **cuenta peticiones**; las cuotas de `test_quotas.py` cuentan tokens. Ninguna
sustituye a la otra: una petición puede costar mil veces más que otra, y mil peticiones
baratas tampoco son gratis.
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# Importados arriba y no dentro de cada test **a propósito**: con
# `from __future__ import annotations` las anotaciones son cadenas, y FastAPI no puede
# resolver un `Request` declarado dentro de una función anidada —no es global—, así que
# trataría el parámetro como cuerpo de la petición y devolvería 422 en vez de ejecutarse.


@pytest.fixture(autouse=True)
def _limitador_limpio():
    """Un limitador con memoria entre tests da falsos rojos y falsos verdes."""
    from server.app.core.rate_limit import limitador

    limitador.reiniciar()
    yield
    limitador.reiniciar()


class TestVentanaDeslizante:

    def test_should_not_limit_below_threshold(self):
        from server.app.core.rate_limit import limitador

        for _ in range(9):
            permitida, _espera = limitador.permitir("ip:1.2.3.4", "10/minute")
            assert permitida

    def test_should_429_after_login_attempts_exceed_limit(self):
        from server.app.core.rate_limit import limitador

        for _ in range(10):
            assert limitador.permitir("ip:1.2.3.4", "10/minute")[0]

        permitida, espera = limitador.permitir("ip:1.2.3.4", "10/minute")
        assert permitida is False
        assert espera > 0, "un 429 sin Retry-After deja al cliente adivinando"

    def test_should_reset_login_limit_after_window(self):
        """El reloj se inyecta: dormir 60 s en un test es una forma cara de no probar nada."""
        from server.app.core.rate_limit import limitador

        for i in range(10):
            limitador.permitir("ip:1.2.3.4", "10/minute", ahora=1000.0 + i)

        assert limitador.permitir("ip:1.2.3.4", "10/minute", ahora=1005.0)[0] is False
        assert limitador.permitir("ip:1.2.3.4", "10/minute", ahora=1075.0)[0] is True

    def test_should_scope_limit_per_ip_for_anonymous_widget(self):
        """Que a uno se le acabe el cupo no puede dejar fuera a los demás."""
        from server.app.core.rate_limit import limitador

        for _ in range(10):
            limitador.permitir("chat:bot-1:9.9.9.9", "10/minute")

        assert limitador.permitir("chat:bot-1:9.9.9.9", "10/minute")[0] is False
        assert limitador.permitir("chat:bot-1:8.8.8.8", "10/minute")[0] is True

    def test_should_keep_scopes_apart(self):
        """El cupo del login no se gasta conversando."""
        from server.app.core.rate_limit import limitador

        for _ in range(10):
            limitador.permitir("login:1.2.3.4", "10/minute")

        assert limitador.permitir("chat:bot-1:1.2.3.4", "10/minute")[0] is True

    def test_should_reject_an_unparseable_rule(self):
        """Una regla ilegible no se interpreta a ojo: se levanta al arrancar."""
        from server.app.core.rate_limit import limitador

        with pytest.raises(RuntimeError):
            limitador.permitir("k", "diez por minuto")


class TestEnElLogin:

    def _app_de_login(self):
        from server.app.core.rate_limit import limitar_login

        app = FastAPI()

        @app.post("/login")
        def login(request: Request):
            limitar_login(request)
            return {"ok": True}

        return app

    def test_should_429_the_eleventh_login_attempt(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "10/minute")
        cliente = TestClient(self._app_de_login())

        for _ in range(10):
            assert cliente.post("/login").status_code == 200

        respuesta = cliente.post("/login")
        assert respuesta.status_code == 429
        assert respuesta.json()["detail"]["code"] == "RATE_LIMITED"
        assert int(respuesta.headers["Retry-After"]) > 0

    def test_should_count_the_forwarded_client_and_not_the_proxy(self, monkeypatch):
        """Detrás de un balanceador, todas las peticiones traen la misma IP de socket.

        Sin mirar `X-Forwarded-For`, el primer usuario que gastara su cupo dejaría fuera a
        todo el mundo, y el límite sería un fallo de disponibilidad en vez de una defensa.

        **SEC.8.4**: la cabecera solo se mira si hay proxies de confianza declarados, y la
        IP se cuenta desde la derecha. Por eso el test declara ahora `TRUSTED_PROXY_HOPS`:
        el despliegue tiene que decir cuántos saltos son suyos, porque de lo contrario el
        valor lo elige quien llama. Cada petición trae aquí un solo elemento en la cadena,
        que es lo que añadiría un único proxy.
        """
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "2/minute")
        monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
        cliente = TestClient(self._app_de_login())

        for _ in range(2):
            cliente.post("/login", headers={"X-Forwarded-For": "10.0.0.1"})

        agotado = cliente.post("/login", headers={"X-Forwarded-For": "10.0.0.1"})
        otro = cliente.post("/login", headers={"X-Forwarded-For": "10.0.0.2"})

        assert agotado.status_code == 429
        assert otro.status_code == 200

    def test_should_not_let_a_spoofed_forwarded_for_reset_the_bucket(self, monkeypatch):
        """El agujero que cerró SEC.8.4: con la IP tomada del primer valor de la cadena,
        añadir uno falso por delante daba un cubo nuevo en cada intento y el límite de
        fuerza bruta no llegaba a aplicarse nunca."""
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "2/minute")
        monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
        cliente = TestClient(self._app_de_login())

        for numero in range(2):
            cliente.post(
                "/login", headers={"X-Forwarded-For": f"9.9.9.{numero}, 10.0.0.1"}
            )

        # Otro valor inventado por delante, misma IP real puesta por el proxy.
        respuesta = cliente.post(
            "/login", headers={"X-Forwarded-For": "1.1.1.1, 10.0.0.1"}
        )
        assert respuesta.status_code == 429


class TestEnElChat:

    def test_should_limit_by_effective_actor_not_by_credential(self, monkeypatch):
        """Un cliente de confianza atiende a cien personas con un PAT.

        Si el límite se contara por credencial, la primera persona activa se llevaría el
        cupo de las otras noventa y nueve. Es la misma razón por la que la cuota se le carga
        al actor y no al dueño del token.
        """
        from server.app.core.rate_limit import limitar_chat

        monkeypatch.setenv("RATE_LIMIT_CHAT", "2/minute")

        app = FastAPI()

        @app.post("/chat/{actor}")
        def chat(actor: str, request: Request):
            limitar_chat(request, actor_id=actor, chatbot_id="bot-1")
            return {"ok": True}

        cliente = TestClient(app)
        for _ in range(2):
            assert cliente.post("/chat/persona-1").status_code == 200

        assert cliente.post("/chat/persona-1").status_code == 429
        assert cliente.post("/chat/persona-2").status_code == 200
