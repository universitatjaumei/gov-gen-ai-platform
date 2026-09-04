"""VAS.1 — el contrato de citas como servicio, y la paridad con el motor.

La regla que el asistente aplica a sus propias respuestas —«ninguna afirmación sin fuente
resoluble»— vale igual para una respuesta generada fuera. Este endpoint la presta.

**Lo que este fichero defiende, y es la regla dura del bloque: no hay segunda implementación.**
El endpoint envuelve `enforce_citation_contract`, la misma función que llama el grafo. El test de
paridad no compara el resultado con una expectativa escrita a mano: compara el texto que devuelve
la API con el que devuelve la función, sobre el mismo caso. Si alguien «mejora» el endpoint, ese
test se pone rojo — que es exactamente lo que se quiere, porque dos implementaciones del contrato
de citas significan dos verdades sobre qué está fundamentado.

El desglose (válidas, inválidas, degradadas, despojadas) sale de la misma pasada que produce el
texto, no de una segunda lectura: si se calculara aparte, podría describir un texto distinto del
que se devuelve.

**Y el texto no se guarda.** Es la misma regla que REG.3 para la anonimización y por el mismo
motivo: aquí llega la respuesta que alguien está verificando, con lo que contenga.
"""
from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import server.app.main  # noqa: F401

from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo

ORG = "735a5f55-7020-4c88-a374-c2b641c5b00b"

NORMA = "https://normativa.uji.es/html/reglament-permanencia.html"
ANCLA = f"{NORMA}#art-4"
AJENA = "https://example.org/otra-norma.html"

CENTINELA = "CENTINELA_DEL_TEXTO_VERIFICADO"


def _principal() -> UserInfo:
    return UserInfo(
        user_id="agente-externo",
        email="integracion@uji.es",
        role="admin",
        organizacion_ids=(ORG,),
    )


def _cliente(scopes: list[str] | None = None) -> AsyncClient:
    """Cliente cuyo principal es un PAT con los scopes dados.

    `scopes=None` es una sesión JWT, que es como el código las distingue.
    """
    from server.app.routers.verificaciones_router import router

    app = FastAPI()

    @app.middleware("http")
    async def _marca_el_pat(request, call_next):
        request.state.pat_scopes = scopes
        return await call_next(request)

    app.dependency_overrides[get_current_user] = _principal
    app.include_router(router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _con_scope() -> AsyncClient:
    return _cliente(scopes=["verificaciones:use"])


def _fuentes(*urls: str) -> list[dict]:
    return [{"url": u, "titulo": "Reglamento de permanencia"} for u in urls]


# ─────────────────────────── Quién puede usarlo ────────────────────────────


class TestQuienPuedeVerificar:

    async def test_should_accept_a_pat_with_the_scope(self):
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={"texto": f"Segun la norma [art. 4]({ANCLA}).", "fuentes_permitidas": _fuentes(ANCLA)},
            )

        assert r.status_code == 200, r.text

    async def test_should_refuse_a_pat_without_the_scope(self):
        async with _cliente(scopes=["chatbots:read"]) as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={"texto": "x", "fuentes_permitidas": []},
            )

        assert r.status_code == 403, r.text
        assert "verificaciones:use" in r.text, (
            "el 403 tiene que decir qué scope falta: quien lo recibe tiene que poder pedirlo."
        )

    async def test_should_refuse_without_any_credential(self):
        from server.app.routers.verificaciones_router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={"texto": "x", "fuentes_permitidas": []},
            )

        assert r.status_code == 401, r.text


# ─────────────────────────── El veredicto ──────────────────────────────────


class TestElVeredicto:

    async def test_should_accept_a_citation_to_an_allowed_source(self):
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={
                    "texto": f"La permanencia se regula en [el articulo 4]({ANCLA}).",
                    "fuentes_permitidas": _fuentes(ANCLA),
                },
            )

        cuerpo = r.json()
        assert cuerpo["cumple"] is True
        assert ANCLA in cuerpo["citas_validas"]

    async def test_should_refuse_a_text_with_no_valid_citation(self):
        """Y devuelve el mensaje de rendición, no el texto sin fundamento."""
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={
                    "texto": "La permanencia se pierde a los dos anyos, sin ninguna cita.",
                    "fuentes_permitidas": _fuentes(ANCLA),
                    "mensaje_sin_respuesta": "No puedo responder con citas verificables.",
                },
            )

        cuerpo = r.json()
        assert cuerpo["cumple"] is False
        assert cuerpo["texto_resultante"] == "No puedo responder con citas verificables."

    async def test_should_fall_back_to_the_engine_message_when_none_is_given(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            NO_CITATION_FALLBACK,
        )

        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={"texto": "Sin citas.", "fuentes_permitidas": _fuentes(ANCLA)},
            )

        assert r.json()["texto_resultante"] == NO_CITATION_FALLBACK

    async def test_should_report_a_citation_outside_the_allowed_set(self):
        """La remisión pierde el enlace y consta como inválida.

        Es el caso que el contrato existe para atrapar: citar algo que no se entregó. Lo que
        dijera de ese texto saldría de la memoria del modelo, no del fundamento.
        """
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={
                    "texto": (
                        f"Segun [el articulo 4]({ANCLA}) y conforme a "
                        f"[la Ley 9/2017]({AJENA})."
                    ),
                    "fuentes_permitidas": _fuentes(ANCLA),
                },
            )

        cuerpo = r.json()
        assert AJENA in cuerpo["citas_invalidas"]
        assert cuerpo["remisiones_despojadas"] == 1
        assert AJENA not in cuerpo["texto_resultante"], (
            "el puntero que no se puede respaldar se va; la mención se queda."
        )
        assert "la Ley 9/2017" in cuerpo["texto_resultante"]

    async def test_should_count_a_degraded_anchor(self):
        """Un ancla que nadie recuperó baja al documento y **sobrevive**.

        Es la mitad del contrato que protege sin destruir: el documento sí se recuperó.
        """
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={
                    "texto": f"Segun [el articulo 7]({NORMA}#art-7-b).",
                    "fuentes_permitidas": _fuentes(ANCLA),
                },
            )

        cuerpo = r.json()
        assert cuerpo["anclas_degradadas"] == 1
        assert cuerpo["cumple"] is True
        assert NORMA in cuerpo["texto_resultante"]

    async def test_should_leave_a_text_without_sources_alone(self):
        """Sin fuentes no hay nada que verificar: es el modo agéntico del motor.

        El agente puede decidir no leer ningún documento —un saludo, una charla— y el contrato
        no se aplica. Aquí igual, porque es la misma función.
        """
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={"texto": "Buenos dias.", "fuentes_permitidas": []},
            )

        cuerpo = r.json()
        assert cuerpo["cumple"] is True
        assert cuerpo["texto_resultante"] == "Buenos dias."


# ─────────────────────────── La paridad con el motor ───────────────────────


class TestParidadConElMotor:
    """La regla dura del bloque: el veredicto de la API y el del motor son el mismo.

    Se compara con `enforce_citation_contract`, que es la función que el grafo llama —no con
    una expectativa escrita a mano—. Si alguien «mejora» el endpoint por su cuenta, esto se
    pone rojo, y eso es lo que se quiere: dos implementaciones del contrato de citas son dos
    verdades sobre qué está fundamentado.
    """

    @pytest.mark.parametrize(
        "texto",
        [
            f"Segun [el articulo 4]({ANCLA}) la permanencia se pierde.",
            f"Conforme a [la Ley 9/2017]({AJENA}), procede.",
            f"Mezcla de [valida]({ANCLA}) y [ajena]({AJENA}).",
            f"Ancla equivocada: [art. 7]({NORMA}#art-7-b).",
            "Sin ninguna cita en absoluto.",
            "[Reglamento de permanencia, articulo 4] sin enlace.",
        ],
    )
    async def test_should_return_what_the_engine_returns(self, texto: str):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )
        from server.app.routers.verificaciones_router import FuenteDeVerificacion

        del_motor = enforce_citation_contract(
            texto,
            [FuenteDeVerificacion(url=ANCLA, titulo="Reglamento de permanencia")],
            "RAG",
        )

        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={"texto": texto, "fuentes_permitidas": _fuentes(ANCLA)},
            )

        assert r.json()["texto_resultante"] == del_motor

    def test_should_not_have_its_own_regex(self):
        """Un `re.compile` en el router sería la segunda implementación entrando por la puerta.

        El desglose sale de las funciones del validador; el router compone, no analiza.

        Se comprueba con `ast` y no buscando la cadena: `"import re"` es subcadena de
        `import require_pat_scopes`, así que la versión ingenua de este test daba un falso
        positivo — y un guardarraíl que salta cuando no debe se acaba silenciando.
        """
        import ast
        from pathlib import Path

        arbol = ast.parse(
            (
                Path(__file__).resolve().parents[2]
                / "app"
                / "routers"
                / "verificaciones_router.py"
            ).read_text(encoding="utf-8")
        )

        importa_re = any(
            (isinstance(n, ast.Import) and any(a.name == "re" for a in n.names))
            or (isinstance(n, ast.ImportFrom) and n.module == "re")
            for n in ast.walk(arbol)
        )
        assert not importa_re, "el router no analiza texto: compone lo que el validador decide."


# ─────────────────────────── Los límites ───────────────────────────────────


class TestLosLimites:

    async def test_should_reject_a_text_over_the_limit(self):
        """Sin tope, una petición tiene al proceso analizando megabytes de texto."""
        from server.app.routers.verificaciones_router import MAXIMO_BYTES

        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={"texto": "a" * (MAXIMO_BYTES + 1), "fuentes_permitidas": []},
            )

        assert r.status_code == 413, r.status_code

    async def test_should_reject_a_content_field_it_does_not_declare(self):
        """El contrato de entrada tampoco admite lo que no declara.

        Aquí no es por proteger datos —el texto es el objeto de la petición— sino porque un
        campo aceptado en silencio hace creer a quien integra que se tuvo en cuenta.
        """
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/verificaciones/citas",
                json={"texto": "x", "fuentes_permitidas": [], "modo_estricto": True},
            )

        assert r.status_code == 422


# ─────────────────────────── El texto no se guarda ─────────────────────────


class TestElTextoNoSeGuarda:

    async def test_should_keep_the_text_out_of_every_log_record(self, caplog):
        """La misma regla que REG.3, y por el mismo motivo.

        Lo que llega aquí es la respuesta que alguien verifica, con lo que contenga dentro. Un
        `logger.debug(texto)` de una depuración convertiría el log del servidor en un archivo
        de respuestas ajenas.
        """
        with caplog.at_level(logging.DEBUG):
            async with _con_scope() as c:
                r = await c.post(
                    "/api/v1/verificaciones/citas",
                    json={
                        "texto": f"{CENTINELA} segun [art. 4]({ANCLA}).",
                        "fuentes_permitidas": _fuentes(ANCLA),
                    },
                )

        assert r.status_code == 200, r.text
        registrado = "\n".join(
            [reg.getMessage() for reg in caplog.records]
            + [str(reg.args) for reg in caplog.records]
        )
        assert CENTINELA not in registrado

    def test_should_not_touch_the_database_at_all(self):
        """No pide sesión: es cómputo puro, como `charts_router`.

        Un espía sobre la sesión sería más débil que esto — con sesión, alguien puede añadir
        una escritura mañana. Sin sesión inyectada, no hay dónde escribir.
        """
        import inspect

        from server.app.routers import verificaciones_router

        fuente = inspect.getsource(verificaciones_router)
        assert "get_async_session" not in fuente


# ─────────────────────────── El scope y el router ──────────────────────────


class TestElScopeNuevo:

    def test_should_add_the_scope_to_the_catalogue(self):
        from server.app.core.auth.pat.scopes import ALL_SCOPES, VERIFICACIONES_USE

        assert VERIFICACIONES_USE == "verificaciones:use"
        assert VERIFICACIONES_USE in ALL_SCOPES, (
            "un scope que no está en `ALL_SCOPES` no se puede emitir."
        )

    @pytest.mark.parametrize("rol", ["superadmin", "admin"])
    def test_should_let_both_roles_issue_it(self, rol: str):
        """Los tres servicios son de lectura o de cómputo sin efecto."""
        from server.app.core.auth.pat.scopes import (
            VERIFICACIONES_USE,
            allowed_scopes_for_role,
        )

        assert VERIFICACIONES_USE in allowed_scopes_for_role(rol)


class TestElRouterEsEdgeYEstaRegistrado:

    def test_should_be_declared_as_edge(self):
        from server.app.routers import verificaciones_router

        assert "Deploy: edge" in (verificaciones_router.__doc__ or "")

    def test_should_be_registered_in_the_edge_side(self):
        import inspect

        from server.app.main import _register_edge

        assert "verificaciones_router" in inspect.getsource(_register_edge)

    def test_should_expose_the_endpoint_with_an_explicit_operation_id(self):
        from server.app.main import app

        rutas = {
            getattr(r, "path", ""): getattr(r, "operation_id", None) for r in app.routes
        }
        assert "/api/v1/verificaciones/citas" in rutas
        assert rutas["/api/v1/verificaciones/citas"]
