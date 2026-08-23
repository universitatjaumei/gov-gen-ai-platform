"""PRO.2.1 — la superficie de la biblioteca de prompts de actividad.

La pantalla necesita tres cosas que no puede deducir: **qué actividades existen** (las dice el
código), **qué nivel y qué texto se están usando** y **de dónde sale cada uno**. Sin lo
tercero, un tier vacío en el formulario no se puede interpretar: ¿no hay nada, o hay un
defecto que no se ve?

Y una regla que este fichero defiende: **el texto por defecto no se copia a la base de datos**.
Se devuelve aparte (`default_template`) para que la pantalla lo pueda mostrar; si se copiara al
guardar, mejorar el prompt en el código dejaría de llegar a quien ya lo abrió.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def api(monkeypatch):
    from server.app.api.deps import get_current_user, get_session
    from server.app.core.auth.models import UserInfo
    from server.app.routers.hub_activity_prompts_router import router

    filas: dict[str, object] = {}

    class _FakeResult:
        def __init__(self, valor):
            self._valor = valor

        def scalars(self):
            return self

        def first(self):
            return self._valor

        def all(self):
            return list(filas.values())

    class _FakeSession:
        def add(self, obj) -> None:
            filas[obj.activity] = obj

        async def delete(self, obj) -> None:
            filas.pop(obj.activity, None)

        async def flush(self) -> None:
            return None

        async def commit(self) -> None:
            return None

        async def execute(self, stmt):
            # La clave pedida sale de los parámetros compilados del WHERE: así el doble no
            # obliga al código de producción a llevar ninguna pista para los tests.
            parametros = list(stmt.compile().params.values())
            clave = parametros[0] if parametros else None
            return _FakeResult(filas.get(clave))

    sesion = _FakeSession()

    app = FastAPI()
    app.dependency_overrides[get_session] = lambda: sesion
    app.dependency_overrides[get_current_user] = lambda: UserInfo(
        user_id=str(uuid.uuid4()), email="admin@t.com", role="superadmin"
    )
    app.include_router(router, prefix="/api/v1")
    return TestClient(app), filas


class TestListado:
    def test_should_listar_las_actividades_del_catalogo_sin_filas_en_bd(self, api) -> None:
        client, _filas = api

        respuesta = client.get("/api/v1/hub/activity-prompts")

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        claves = {a["activity"] for a in cuerpo}
        assert {"propuesta_de_script", "auditoria_de_script"} <= claves

    def test_should_decir_de_donde_sale_cada_cosa(self, api) -> None:
        client, _filas = api

        cuerpo = client.get("/api/v1/hub/activity-prompts").json()
        propuesta = next(a for a in cuerpo if a["activity"] == "propuesta_de_script")

        assert propuesta["default_tier"] == 2
        assert propuesta["effective_tier"] == 2
        assert propuesta["tier_source"] == "codigo"
        assert propuesta["text_source"] == "codigo"
        assert propuesta["override_tier"] is None
        assert propuesta["template_text"] is None, (
            "sin override no hay texto guardado: el de por defecto va aparte"
        )

    def test_should_devolver_el_texto_por_defecto_y_sus_variables(self, api) -> None:
        client, _filas = api

        cuerpo = client.get("/api/v1/hub/activity-prompts").json()
        propuesta = next(a for a in cuerpo if a["activity"] == "propuesta_de_script")

        assert "lista blanca" in propuesta["default_template"].lower()
        assert "lista_blanca" in propuesta["variables"]
        assert propuesta["purpose"]


class TestGuardado:
    def test_should_guardar_el_nivel_y_reflejarlo_en_el_listado(self, api) -> None:
        client, filas = api

        respuesta = client.put(
            "/api/v1/hub/activity-prompts/propuesta_de_script",
            json={"override_tier": 3, "template_text": None},
        )

        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["effective_tier"] == 3
        assert cuerpo["tier_source"] == "override"
        assert filas["propuesta_de_script"].override_tier == 3

    def test_should_no_copiar_el_texto_por_defecto_al_guardar_solo_el_nivel(self, api) -> None:
        """Copiarlo congelaría el prompt: mejorarlo en el código ya no llegaría."""
        client, filas = api

        client.put(
            "/api/v1/hub/activity-prompts/propuesta_de_script",
            json={"override_tier": 3, "template_text": None},
        )

        assert filas["propuesta_de_script"].template_text in (None, "")

    def test_should_rechazar_una_actividad_que_no_esta_en_el_catalogo(self, api) -> None:
        """Una actividad inventada no la consume nadie: sería configuración muerta."""
        client, _filas = api

        respuesta = client.put(
            "/api/v1/hub/activity-prompts/invento_mio",
            json={"override_tier": 2, "template_text": None},
        )

        assert respuesta.status_code == 422
        assert respuesta.json()["detail"]["code"] == "UNKNOWN_ACTIVITY"

    def test_should_rechazar_un_nivel_fuera_de_rango(self, api) -> None:
        client, _filas = api

        respuesta = client.put(
            "/api/v1/hub/activity-prompts/propuesta_de_script",
            json={"override_tier": 9, "template_text": None},
        )

        assert respuesta.status_code == 422

    def test_should_avisar_de_una_variable_inventada_en_el_texto(self, api) -> None:
        """Un `{invento}` no se puede rellenar y llegaría al modelo tal cual."""
        client, _filas = api

        respuesta = client.put(
            "/api/v1/hub/activity-prompts/propuesta_de_script",
            json={"override_tier": None, "template_text": "Usa {invento} y ya."},
        )

        assert respuesta.status_code == 422
        assert respuesta.json()["detail"]["code"] == "UNKNOWN_VARIABLE"
        assert "invento" in str(respuesta.json()["detail"])


class TestPermisos:
    def test_should_prohibir_a_un_usuario_normal(self, api, monkeypatch) -> None:
        from server.app.api.deps import get_current_user
        from server.app.core.auth.models import UserInfo
        from server.app.routers.hub_activity_prompts_router import router  # noqa: F401

        client, _filas = api
        client.app.dependency_overrides[get_current_user] = lambda: UserInfo(
            user_id=str(uuid.uuid4()), email="u@t.com", role="user"
        )

        assert client.get("/api/v1/hub/activity-prompts").status_code == 403
        assert client.put(
            "/api/v1/hub/activity-prompts/propuesta_de_script",
            json={"override_tier": 3, "template_text": None},
        ).status_code == 403


class TestElModuloViajaEnElContrato:
    """REV.7 — la pantalla agrupa y filtra por módulo, así que el módulo tiene que llegar.

    Deducirlo en el React a partir del nombre de la actividad sería inventarlo: el catálogo es
    del servidor y crece cuando se cablea un consumidor nuevo.
    """

    def test_should_expose_the_module_of_each_activity(self, api) -> None:
        client, _filas = api

        cuerpo = client.get("/api/v1/hub/activity-prompts").json()

        assert all(a.get("modulo") for a in cuerpo), (
            "toda actividad tiene que decir de qué módulo es"
        )
        propuesta = next(a for a in cuerpo if a["activity"] == "propuesta_de_script")
        assert propuesta["modulo"] == "informes"
