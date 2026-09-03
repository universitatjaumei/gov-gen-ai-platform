"""REG.3 — la anonimización como servicio, y la regla de que el texto no se registra.

`POST /api/v1/anonimizacion/spans` detecta y `POST /api/v1/anonimizacion/replace` sustituye, sobre
el motor que ya existe en `modules/redaccion/services/anonymization/`. Son la alternativa a que
cada herramienta externa resuelva la PII por su cuenta.

**La regla del bloque, y por qué tiene un test propio.** Estos dos endpoints reciben, por
definición, el texto más sensible que pasa por la plataforma: alguien nos lo manda *precisamente
porque* lleva datos personales. Un `logger.debug(text)` puesto de buena fe durante una depuración
convertiría el registro del servidor en el archivo de PII que el servicio existe para evitar. El
test del centinela es el camino bueno de esa regla: comprueba que con `caplog` a DEBUG —el nivel
más ruidoso— el texto no aparece en ningún registro.

**Y la que no está en el prompt pero es del mismo tipo**: el motor guarda el mapa real→ficticio en
el `FakerGenerator` de su contexto, así que un detector compartido entre peticiones acumularía en
memoria la PII de todos los que llamaron. Por eso el detector es de una petición, y hay un test
que lo fija.
"""
from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

import server.app.main  # noqa: F401

from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo

CENTINELA = "SENTINELA_PII_123"
DNI = "12345678Z"
CORREO = "manuela.ferrer@example.org"

TEXTO = (
    f"{CENTINELA}. Solicitud presentada con DNI {DNI} y correo de contacto {CORREO} "
    "para el expediente de la convocatoria."
)


def _principal() -> UserInfo:
    return UserInfo(
        user_id="agente-externo",
        email="integracion@uji.es",
        role="admin",
        organizacion_ids=("735a5f55-7020-4c88-a374-c2b641c5b00b",),
    )


def _cliente(scopes: list[str] | None = None) -> AsyncClient:
    """Cliente cuyo principal es un PAT con los scopes dados.

    `scopes=None` simula una sesión JWT, que es como el código las distingue
    (`request.state.pat_scopes` a `None`).
    """
    from server.app.routers.anonimizacion_router import router

    app = FastAPI()

    @app.middleware("http")
    async def _marca_el_pat(request, call_next):
        request.state.pat_scopes = scopes
        return await call_next(request)

    app.dependency_overrides[get_current_user] = _principal
    app.include_router(router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _con_scope() -> AsyncClient:
    return _cliente(scopes=["anonimizacion:use"])


# ─────────────────────────── Detectar ──────────────────────────────────────


class TestDetectarSpans:

    async def test_should_find_the_dni_and_the_email(self):
        async with _con_scope() as c:
            r = await c.post("/api/v1/anonimizacion/spans", json={"text": TEXTO})

        assert r.status_code == 200, r.text
        spans = r.json()["spans"]
        tipos = {s["type"] for s in spans}
        assert {"DNI", "EMAIL"} <= tipos, spans

    async def test_should_point_at_the_right_slice_of_the_text(self):
        """Los offsets tienen que servir para cortar: quien integra los usa para resaltar."""
        async with _con_scope() as c:
            r = await c.post("/api/v1/anonimizacion/spans", json={"text": TEXTO})

        for span in r.json()["spans"]:
            assert TEXTO[span["start"] : span["end"]] == span["original_text"], span

    async def test_should_answer_an_empty_list_for_text_without_pii(self):
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/anonimizacion/spans",
                json={"text": "El plazo de presentación finaliza a las catorce horas."},
            )

        assert r.status_code == 200, r.text
        assert r.json()["spans"] == []


# ─────────────────────────── Sustituir ─────────────────────────────────────


class TestSustituir:

    async def test_should_return_text_without_the_original_dni(self):
        async with _con_scope() as c:
            r = await c.post("/api/v1/anonimizacion/replace", json={"text": TEXTO})

        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert DNI not in cuerpo["text_anonimizado"]
        assert CORREO not in cuerpo["text_anonimizado"]
        assert cuerpo["spans_aplicados"], "si sustituyó algo, tiene que decir qué"

    async def test_should_keep_the_text_that_is_not_pii(self):
        """La sustitución no reescribe el documento: sólo los tramos detectados."""
        async with _con_scope() as c:
            r = await c.post("/api/v1/anonimizacion/replace", json={"text": TEXTO})

        assert "convocatoria" in r.json()["text_anonimizado"]

    async def test_should_report_only_the_spans_it_actually_applied(self):
        """`spans_aplicados` describe el texto devuelto, no una detección aparte.

        Si se calculara con una segunda pasada, los `suggested_fake` serían otros —el generador
        es aleatorio— y quien integra no podría cotejar el resultado con el informe.
        """
        async with _con_scope() as c:
            r = await c.post("/api/v1/anonimizacion/replace", json={"text": TEXTO})

        cuerpo = r.json()
        for span in cuerpo["spans_aplicados"]:
            assert span["suggested_fake"] in cuerpo["text_anonimizado"], span

    async def test_should_not_share_the_pii_map_between_requests(self):
        """El mapa real→ficticio vive en el generador del contexto.

        Un detector compartido entre peticiones acumularía en memoria la PII de todos los que
        llamaron, y `deanonymize` de una petición podría deshacer la de otra. El servicio es
        stateless: cada petición trae el suyo.
        """
        from server.app.routers import anonimizacion_router

        uno = anonimizacion_router.get_detector()
        otro = anonimizacion_router.get_detector()

        assert uno is not otro
        assert uno.ctx.fakes is not otro.ctx.fakes


# ─────────────────────────── Lo que se rechaza ─────────────────────────────


class TestLosLimites:

    async def test_should_reject_text_over_the_limit(self):
        """Sin tope, una petición puede tener al proceso detectando durante minutos."""
        async with _con_scope() as c:
            r = await c.post(
                "/api/v1/anonimizacion/spans", json={"text": "a" * 200_001}
            )

        assert r.status_code == 422, r.status_code

    @pytest.mark.parametrize("ruta", ["spans", "replace"])
    async def test_should_refuse_a_pat_without_the_scope(self, ruta: str):
        async with _cliente(scopes=["chatbots:read"]) as c:
            r = await c.post(f"/api/v1/anonimizacion/{ruta}", json={"text": TEXTO})

        assert r.status_code == 403, r.text
        assert "anonimizacion:use" in r.text, (
            "el 403 tiene que decir qué scope falta: quien lo recibe tiene que poder pedirlo."
        )

    @pytest.mark.parametrize("ruta", ["spans", "replace"])
    async def test_should_refuse_without_any_credential(self, ruta: str):
        from server.app.routers.anonimizacion_router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            r = await c.post(f"/api/v1/anonimizacion/{ruta}", json={"text": TEXTO})

        assert r.status_code == 401, r.text


# ─────────────────────────── La regla de oro ───────────────────────────────


class TestElTextoNoLlegaAlRegistro:
    """La regla del bloque: ni el texto de entrada ni el anonimizado se registran."""

    @pytest.mark.parametrize("ruta", ["spans", "replace"])
    async def test_should_keep_the_sentinel_out_of_every_log_record(
        self, ruta: str, caplog
    ):
        with caplog.at_level(logging.DEBUG):
            async with _con_scope() as c:
                r = await c.post(
                    f"/api/v1/anonimizacion/{ruta}", json={"text": TEXTO}
                )

        assert r.status_code == 200, r.text
        registrado = "\n".join(
            [reg.getMessage() for reg in caplog.records]
            + [str(reg.args) for reg in caplog.records]
        )
        assert CENTINELA not in registrado, (
            "el texto que nos mandan lleva PII por definición: registrarlo convierte el log del "
            "servidor en el archivo de datos personales que este servicio existe para evitar."
        )
        assert DNI not in registrado


class TestNadaPersiste:

    async def test_should_leave_every_operational_table_as_it_was(self, db_url):
        """El servicio es stateless: ni el texto ni el resultado tocan la base.

        Se cuentan **todas** las tablas operacionales y no sólo las que se sospechan, porque lo
        que hay que descartar es que el motor —que se comparte con `redaccion`— escriba en alguna
        por su cuenta.
        """
        from server.app.modules.agents_hub.database.base import HubOperationalBase

        engine = create_async_engine(db_url)
        try:
            async with AsyncSession(engine) as session:

                async def censo() -> dict[str, int]:
                    return {
                        nombre: (
                            await session.exec(select(func.count()).select_from(tabla))
                        ).scalar_one()
                        for nombre, tabla in HubOperationalBase.metadata.tables.items()
                    }

                antes = await censo()

                async with _con_scope() as c:
                    await c.post("/api/v1/anonimizacion/spans", json={"text": TEXTO})
                    await c.post("/api/v1/anonimizacion/replace", json={"text": TEXTO})

                assert await censo() == antes
        finally:
            await engine.dispose()


# ─────────────────────────── El router ─────────────────────────────────────


class TestElRouterEsEdgeYEstaRegistrado:

    def test_should_be_declared_as_edge(self):
        from server.app.routers import anonimizacion_router

        assert "Deploy: edge" in (anonimizacion_router.__doc__ or "")

    def test_should_be_registered_in_the_edge_side(self):
        import inspect

        from server.app.main import _register_edge

        assert "anonimizacion_router" in inspect.getsource(_register_edge)

    @pytest.mark.parametrize(
        "ruta", ["/api/v1/anonimizacion/spans", "/api/v1/anonimizacion/replace"]
    )
    def test_should_expose_each_endpoint_with_an_explicit_operation_id(self, ruta: str):
        from server.app.main import app

        rutas = {
            getattr(r, "path", ""): getattr(r, "operation_id", None) for r in app.routes
        }
        assert ruta in rutas
        assert rutas[ruta], (
            "sin `operation_id` explícito el cliente generado hereda un nombre ilegible."
        )


class TestLaPoliticaPorDefectoEsUnaSola:
    """Los tipos que se sustituyen los decide el motor, no una copia en el router.

    El motor los llevaba escritos dentro de `anonymize()`; el endpoint necesita la misma lista
    para decir qué aplicó. Duplicarla habría dejado dos políticas por defecto que divergen en
    cuanto alguien añada un tipo, y la divergencia sería silenciosa: el endpoint devolvería un
    texto sustituido y un informe que no lo describe.
    """

    def test_should_read_the_default_types_from_the_engine(self):
        from server.app.modules.redaccion.services.anonymization.anonymizer import (
            TIPOS_ANONIMIZADOS_POR_DEFECTO,
        )

        assert "DNI" in TIPOS_ANONIMIZADOS_POR_DEFECTO
        assert "EMAIL" in TIPOS_ANONIMIZADOS_POR_DEFECTO

    def test_should_not_keep_a_copy_of_the_list_in_the_router(self):
        import inspect

        from server.app.routers import anonimizacion_router

        fuente = inspect.getsource(anonimizacion_router)
        assert '"PERSON_NAME"' not in fuente, (
            "la lista de tipos se importa del motor; una copia en el router divergiría."
        )
