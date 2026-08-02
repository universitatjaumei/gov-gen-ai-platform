"""Superficie mínima y cabeceras de seguridad (Prompt SEC.7, M5).

Dos cosas pequeñas que se notan el día de una auditoría y el día de un incidente: que la
documentación interactiva no publique el mapa de la API en producción, y que toda respuesta
lleve las cuatro cabeceras que evitan clickjacking, sniffing de tipo y fugas por `Referer`.

**HSTS solo en producción**, y el test lo fija: enviarlo en desarrollo obliga al navegador a
exigir HTTPS en `localhost` durante un año, y quien se lo coma no tiene forma evidente de
deshacerlo.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.app.core.security_headers import (
    SecurityHeadersMiddleware,
    cabeceras_de_seguridad,
    urls_de_documentacion,
)


def _app(entorno: str) -> TestClient:
    app = FastAPI(**urls_de_documentacion(entorno))
    app.add_middleware(SecurityHeadersMiddleware, entorno=entorno)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


class TestDocumentacion:

    def test_should_disable_docs_in_production(self):
        cliente = _app("production")

        assert cliente.get("/docs").status_code == 404
        assert cliente.get("/redoc").status_code == 404
        assert cliente.get("/openapi.json").status_code == 404

    def test_should_expose_docs_in_development(self):
        cliente = _app("development")

        assert cliente.get("/docs").status_code == 200
        assert cliente.get("/openapi.json").status_code == 200

    def test_should_keep_the_api_working_in_production(self):
        """Apagar la documentación no apaga la API: es lo único que se retira."""
        assert _app("production").get("/ping").json() == {"ok": True}


class TestCabeceras:

    def test_should_set_nosniff_and_frame_options_headers(self):
        respuesta = _app("development").get("/ping")

        assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
        assert respuesta.headers["X-Frame-Options"] == "DENY"
        assert respuesta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "frame-ancestors 'none'" in respuesta.headers["Content-Security-Policy"]

    def test_should_set_hsts_only_in_production(self):
        desarrollo = _app("development").get("/ping")
        produccion = _app("production").get("/ping")

        assert "Strict-Transport-Security" not in desarrollo.headers
        assert "max-age=31536000" in produccion.headers["Strict-Transport-Security"]

    def test_should_add_the_headers_to_error_responses_too(self):
        """Un 404 también se sirve a un navegador, y también se le puede poner un marco."""
        respuesta = _app("production").get("/no-existe")

        assert respuesta.status_code == 404
        assert respuesta.headers["X-Content-Type-Options"] == "nosniff"

    def test_should_not_override_a_header_the_endpoint_already_set(self):
        """El widget embebible (D.1) necesitará su propia `frame-ancestors` por organización.

        Si el middleware pisara lo que pone el endpoint, esa política sería imposible sin
        tocar este módulo: se deja ganar al que sabe más.
        """
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, entorno="production")

        @app.get("/widget")
        def widget():
            from fastapi.responses import JSONResponse

            return JSONResponse(
                {"ok": True},
                headers={"Content-Security-Policy": "frame-ancestors https://uji.es"},
            )

        respuesta = TestClient(app).get("/widget")
        assert respuesta.headers["Content-Security-Policy"] == "frame-ancestors https://uji.es"


class TestLaAppReal:

    def test_should_apply_the_policy_to_the_application(self):
        from server.app.main import app

        clases = [m.cls.__name__ for m in app.user_middleware]
        assert "SecurityHeadersMiddleware" in clases

    @pytest.mark.parametrize("entorno", ["production", "staging", "development"])
    def test_should_decide_docs_and_hsts_only_by_environment(self, entorno):
        cabeceras = cabeceras_de_seguridad(entorno)
        urls = urls_de_documentacion(entorno)

        es_produccion = entorno == "production"
        assert ("Strict-Transport-Security" in cabeceras) is es_produccion
        assert (urls["docs_url"] is None) is es_produccion
