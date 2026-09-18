"""APER.2 — los dos stubs de la sync edge exigen identidad, aunque todavía no hagan nada.

**Hallazgo M2 de la auditoría previa a abrir el repositorio.** `GET /api/v1/edge/config` y
`POST /api/v1/edge/telemetry` estaban registrados en `main.py` y no llevaban **ninguna**
dependencia: levantaban `HTTPException(501)` a cualquiera. El riesgo no es lo que hacen hoy
—nada—, son dos cosas:

1. Es superficie sin guardia en un repositorio que va a ser público, y la marcará el primer
   escáner que pase.
2. **Nace abierto si nadie mira**, que es literalmente lo que decía la exención del inventario de
   routers desde SEC.9.5. `GET /edge/config` está diseñado para servir una instantánea de la
   configuración del cloud; el día que alguien la implemente, la dependencia ya está puesta y no
   hay que acordarse de añadirla. Acordarse es exactamente lo que falla.

**Por qué se guardan y no se retiran.** La otra opción era borrarlos por la regla de «sin código
muerto especulativo», y se descartó con lo que hay escrito delante: `AGENTS.md` declara
`edge_sync_router` como la única superficie que ve los dos mundos, `Plan_TDD_Fase3.md` diseña la
sync sobre estas dos rutas, y `EdgeConfigSnapshot` **está haciendo trabajo hoy** — el guardarraíl
de USR.1 comprueba sobre él que la instantánea no declara ningún campo de contraseña. Borrar el
fichero se llevaría esa comprobación por delante.

**La credencial definitiva es de Fase 3, y esto no la decide.** El plan habla de una
`edge_api_key` por nodo; hasta que exista, lo que se exige es la identidad que ya existe. Lo que
este test fija es la frontera: sin credencial no se entra.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _cliente(*, autenticado: bool):
    """App mínima con el router de sync. Sin principal, la dependencia real mide el 401."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.app.api.deps import get_current_user, get_session
    from server.app.api.v1.edge_sync import router as edge_sync_router
    from server.app.core.auth.models import UserInfo

    app = FastAPI()

    async def _sesion():
        yield MagicMock()

    app.dependency_overrides[get_session] = _sesion
    if autenticado:
        app.dependency_overrides[get_current_user] = lambda: UserInfo(
            user_id="nodo-edge", email="edge@example.org", role="admin"
        )
    app.include_router(edge_sync_router, prefix="/api/v1")
    return TestClient(app)


class TestSinCredencialNoSeEntra:

    def test_la_configuracion_no_se_sirve_a_un_anonimo(self) -> None:
        assert _cliente(autenticado=False).get("/api/v1/edge/config").status_code == 401

    def test_la_telemetria_no_se_acepta_de_un_anonimo(self) -> None:
        respuesta = _cliente(autenticado=False).post("/api/v1/edge/telemetry", json={})
        assert respuesta.status_code == 401

    def test_el_401_llega_antes_que_el_422_del_cuerpo(self) -> None:
        """Un cuerpo inválido no puede revelar que la ruta existe ni qué forma tiene.

        Con la guarda declarada como dependencia del endpoint, FastAPI la resuelve antes de
        validar el cuerpo. Sin ella, un anónimo aprendía el esquema de `EdgeTelemetryBatch`
        mandando `{}` y leyendo el 422.
        """
        respuesta = _cliente(autenticado=False).post(
            "/api/v1/edge/telemetry", json={"edge_node_id": 12345}
        )
        assert respuesta.status_code == 401


class TestConCredencialSigueSinImplementarse:
    """La guarda no puede haber cambiado lo que los stubs dicen de sí mismos."""

    def test_la_configuracion_sigue_diciendo_501(self) -> None:
        assert _cliente(autenticado=True).get("/api/v1/edge/config").status_code == 501

    def test_la_telemetria_sigue_diciendo_501(self) -> None:
        cuerpo = {
            "edge_node_id": "nodo-1",
            "interactions_count": 3,
            "avg_latency_ms": 120.5,
            "window_start": "2026-09-18T00:00:00Z",
            "window_end": "2026-09-18T01:00:00Z",
        }
        respuesta = _cliente(autenticado=True).post("/api/v1/edge/telemetry", json=cuerpo)
        assert respuesta.status_code == 501


class TestLaGuardaEstaDeclarada:
    """No basta el comportamiento: la guarda tiene que ser dependencia real de las dos rutas.

    Es la lección de `library_router`, que declaraba su módulo en el docstring mientras estaba
    abierto de par en par: un docstring no autoriza nada, y un 501 tampoco protege nada.
    """

    @pytest.mark.parametrize("ruta", ["/edge/config", "/edge/telemetry"])
    def test_cada_ruta_depende_de_la_identidad(self, ruta: str) -> None:
        from server.app.api.deps import get_current_user
        from server.app.api.v1.edge_sync import router as edge_sync_router

        destino = next(r for r in edge_sync_router.routes if r.path == ruta)
        dependencias = [d.call for d in destino.dependant.dependencies]
        assert get_current_user in dependencias, (
            f"{ruta} no declara `get_current_user` como dependencia: es superficie anónima."
        )
