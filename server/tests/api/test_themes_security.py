"""Temas: autenticación en la lectura y rutas que no salen del directorio (SEC.5, M2).

Dos agujeros, y el primero es de manual: `_theme_path` concatenaba lo que llegara en la URL
con el directorio de temas. Con `../` se leía cualquier `.json` del servidor, y como
`DELETE` usa la misma función, también se borraba.

El segundo es menos aparatoso y más incómodo de explicar: `GET /hub/themes/{id}` era
**público**. Un tema no es un secreto de estado, pero lleva los colores, el logotipo y el
nombre de la organización a la que pertenece, así que servía un censo de clientes sin pedir
nada a cambio.

**La validación es doble a propósito**: la forma del identificador *y* el destino resuelto.
Comprobar solo la cadena es apostar a haber pensado en todas las codificaciones —`..%2f`,
`....//`, rutas absolutas de Windows—; comprobar dónde acaba la ruta es no tener que
acertar.
"""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import server.app.main  # noqa: F401 — fija el orden de carga; ver test_chatbot_availability
from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo
from server.app.routers.hub_themes_router import THEMES_DIR, router

ORG_A = str(uuid.UUID("00000000-0000-0000-0000-0000000000a1"))
ORG_B = str(uuid.UUID("00000000-0000-0000-0000-0000000000b2"))


def _app(rol: str = "admin", orgs: tuple[str, ...] = (ORG_A,), anonimo: bool = False):
    app = FastAPI()
    if not anonimo:
        app.dependency_overrides[get_current_user] = lambda: UserInfo(
            user_id="admin-1", email="a@uji.es", role=rol, organizacion_ids=orgs
        )
    app.include_router(router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def tema_de_org_b():
    """Un tema real en disco, de una organización ajena. Se borra al terminar."""
    theme_id = str(uuid.uuid4())
    ruta = THEMES_DIR / f"{theme_id}.json"
    ruta.write_text(
        json.dumps(
            {
                "id": theme_id,
                "name": "Tema ajeno",
                "organizacion_id": ORG_B,
                "chatbot_id": None,
                "is_default": False,
                "config": {"name": "ajeno", "version": "1.0.0"},
                "created_at": "2026-08-02T00:00:00+00:00",
                "updated_at": "2026-08-02T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    yield theme_id
    ruta.unlink(missing_ok=True)


class TestRutasQueNoSalenDelDirectorio:

    @pytest.mark.parametrize(
        "identificador",
        [
            "../secretos",
            "..%2Fsecretos",
            "....//secretos",
            "/etc/passwd",
            "C:/Windows/win",
            "tema.json",
            "TEMA",
            "tema con espacios",
        ],
    )
    def test_should_reject_theme_id_with_path_traversal(self, identificador):
        from server.app.routers.hub_themes_router import _theme_path

        with pytest.raises(HTTPException) as exc:
            _theme_path(identificador)
        assert exc.value.status_code == 400

    def test_should_accept_a_uuid_shaped_identifier(self):
        from server.app.routers.hub_themes_router import _theme_path

        destino = _theme_path(str(uuid.uuid4()))
        assert destino.is_relative_to(THEMES_DIR.resolve())

    def test_should_not_read_files_outside_themes_dir(self, tmp_path):
        """Aunque exista el fichero, la ruta que sale del directorio no se abre."""
        from server.app.routers.hub_themes_router import _load_theme

        senuelo = THEMES_DIR.parent / "senuelo.json"
        senuelo.write_text(json.dumps({"secreto": True}), encoding="utf-8")
        try:
            with pytest.raises(HTTPException) as exc:
                _load_theme("../senuelo")
            assert exc.value.status_code == 400
        finally:
            senuelo.unlink(missing_ok=True)

    def test_should_reject_traversal_over_http_on_every_verb(self):
        cliente = _app(rol="superadmin")

        for respuesta in (
            cliente.get("/api/v1/hub/themes/..%2Fsenuelo"),
            cliente.put(
                "/api/v1/hub/themes/..%2Fsenuelo",
                json={"config": {"name": "x", "version": "1.0.0"}},
            ),
            cliente.delete("/api/v1/hub/themes/..%2Fsenuelo"),
        ):
            assert respuesta.status_code in (400, 404), respuesta.text
            assert respuesta.status_code != 500


class TestAutenticacionEnLaLectura:

    def test_should_require_auth_on_get_theme(self, tema_de_org_b):
        anonimo = _app(anonimo=True)

        respuesta = anonimo.get(f"/api/v1/hub/themes/{tema_de_org_b}")

        assert respuesta.status_code == 401

    def test_should_forbid_reading_a_theme_of_another_org(self, tema_de_org_b):
        """SEC.2 llega también aquí: el tema lleva el nombre de su organización."""
        cliente = _app(orgs=(ORG_A,))

        respuesta = cliente.get(f"/api/v1/hub/themes/{tema_de_org_b}")

        assert respuesta.status_code == 403

    def test_should_allow_reading_a_theme_of_your_own_org(self, tema_de_org_b):
        cliente = _app(orgs=(ORG_B,))

        respuesta = cliente.get(f"/api/v1/hub/themes/{tema_de_org_b}")

        assert respuesta.status_code == 200
        assert respuesta.json()["name"] == "Tema ajeno"

    def test_should_let_any_admin_read_a_platform_theme(self):
        """Los temas de plataforma son la base de la cascada: no son de nadie."""
        cliente = _app(orgs=(ORG_A,))
        presets = cliente.get("/api/v1/hub/themes/presets")

        # Los presets siguen siendo públicos: son cuatro nombres, no configuración de nadie.
        assert presets.status_code == 200
