"""CORS por entorno (Prompt SEC.3, hallazgo A4).

`allow_origins=["*"]` estaba escrito a mano en `main.py` desde el primer día. Con
`allow_credentials=False` no entrega cookies, así que no es el agujero de libro; lo que sí
hace es dejar que **cualquier** página lea las respuestas de la API usando el token que su
propio JavaScript consiga —y el panel guarda el JWT en `localStorage`, que es alcanzable
desde el mismo origen que ejecute un script inyectado—. En una API de administración
pública el comodín además dice, a quien lo mire, que nadie ha decidido quién puede llamar.

Lo que estos tests fijan:

- **En producción no hay comodín**, ni escrito ni por omisión. Sin lista configurada la
  política queda vacía: el navegador rechaza, que es lo que debe pasar cuando nadie ha dicho
  quién entra.
- **Fuera de producción el comodín se conserva**, porque un desarrollador arranca el front en
  el puerto que le toca ese día y pelearse con CORS en local no protege de nada.
- **Los métodos y las cabeceras se acotan a los que se usan**, `X-GovGenAI-Actor` incluida:
  SEC.2.1 la introdujo y sin declararla aquí el preflight la tumbaría.
"""
from __future__ import annotations

import pytest


def _politica(entorno: str, origenes: str | None = None):
    from server.app.core.cors import politica_cors

    return politica_cors(entorno=entorno, origenes_csv=origenes)


class TestPoliticaPorEntorno:

    def test_should_default_to_no_wildcard_when_env_is_production(self):
        """Sin lista y en producción: cerrado. Nunca `*` por omisión."""
        politica = _politica("production")

        assert politica["allow_origins"] == []
        assert "*" not in politica["allow_origins"]

    def test_should_allow_configured_origin(self):
        politica = _politica(
            "production", "https://panel.uji.es, https://seu.uji.es"
        )

        assert politica["allow_origins"] == ["https://panel.uji.es", "https://seu.uji.es"]

    def test_should_reject_disallowed_origin_in_production_config(self):
        politica = _politica("production", "https://panel.uji.es")

        assert "https://atacante.example" not in politica["allow_origins"]

    def test_should_ignore_a_wildcard_written_in_the_production_config(self):
        """Poner `*` en la variable de entorno no es configurar: es rendirse.

        Se descarta en vez de aceptarse porque el fallo que esto evita —copiar el `.env` de
        desarrollo a producción— es justo el que más veces ocurre.
        """
        politica = _politica("production", "*, https://panel.uji.es")

        assert politica["allow_origins"] == ["https://panel.uji.es"]

    def test_should_keep_the_wildcard_in_development(self):
        politica = _politica("development")

        assert politica["allow_origins"] == ["*"]

    def test_should_honour_an_explicit_list_in_development_too(self):
        """Si alguien se molesta en escribir la lista en local, se respeta."""
        politica = _politica("development", "http://localhost:5173")

        assert politica["allow_origins"] == ["http://localhost:5173"]

    def test_should_never_allow_credentials(self):
        """Con comodín sería ilegal, y sin comodín tampoco hace falta: el token va en la
        cabecera `Authorization`, no en una cookie."""
        for entorno in ("development", "production"):
            assert _politica(entorno)["allow_credentials"] is False


class TestMetodosYCabeceras:

    def test_should_narrow_methods_to_the_ones_actually_used(self):
        politica = _politica("production", "https://panel.uji.es")

        assert set(politica["allow_methods"]) == {
            "GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"
        }
        assert "*" not in politica["allow_methods"]

    def test_should_declare_the_delegated_actor_header(self):
        """SEC.2.1: sin declararla, el preflight tumba la identidad delegada."""
        politica = _politica("production", "https://panel.uji.es")

        cabeceras = {h.lower() for h in politica["allow_headers"]}
        assert "authorization" in cabeceras
        assert "content-type" in cabeceras
        assert "x-govgenai-actor" in cabeceras
        assert "*" not in politica["allow_headers"]

    def test_should_declare_the_widget_key_header(self):
        """SEC.8.5: el widget público vive por definición en el origen de un tercero --
        el mismo `localhost:5173` del panel no cuenta como prueba, porque Vite lo sirve
        por proxy y el navegador nunca ve una petición cruzada de verdad. Sin declarar
        `X-Widget-Key` aquí, el preflight real (`Origin` distinto del backend) responde
        400 "Disallowed CORS headers" y el widget no puede hablar con la API desde
        ninguna página que lo incruste, que es su único caso de uso."""
        politica = _politica("production", "https://panel.uji.es")

        cabeceras = {h.lower() for h in politica["allow_headers"]}
        assert "x-widget-key" in cabeceras


class TestLaAppRealLaUsa:

    def test_should_not_hardcode_a_wildcard_in_main(self):
        """El comodín ya no se escribe en `main.py`: sale de la política."""
        from pathlib import Path

        texto = Path("app/main.py").read_text(encoding="utf-8")
        assert 'allow_origins=["*"]' not in texto
        assert "politica_cors" in texto

    def test_should_apply_the_policy_to_the_application(self):
        from starlette.middleware.cors import CORSMiddleware

        from server.app.main import app

        cors = [m for m in app.user_middleware if m.cls is CORSMiddleware]
        assert cors, "la app perdió el middleware de CORS"

        opciones = cors[0].kwargs
        assert opciones["allow_credentials"] is False
        assert "*" not in opciones["allow_methods"]

    @pytest.mark.parametrize("origen", ["https://atacante.example"])
    def test_should_not_echo_an_unlisted_origin_in_production(self, origen, monkeypatch):
        """La comprobación de extremo a extremo: el navegador no ve el permiso.

        Se construye una app mínima con la misma política en vez de reimportar `main`, que
        aplica el middleware al importarse y no admite reconfiguración a mitad de sesión.
        """
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from starlette.middleware.cors import CORSMiddleware

        from server.app.core.cors import politica_cors

        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            **politica_cors(entorno="production", origenes_csv="https://panel.uji.es"),
        )

        @app.get("/ping")
        def ping():
            return {"ok": True}

        cliente = TestClient(app)
        ajeno = cliente.get("/ping", headers={"Origin": origen})
        propio = cliente.get("/ping", headers={"Origin": "https://panel.uji.es"})

        assert "access-control-allow-origin" not in ajeno.headers
        assert propio.headers["access-control-allow-origin"] == "https://panel.uji.es"
