"""FUN.6 — ejecutar una función del catálogo por API, con PAT y rastro en el registro.

La superficie para una aplicación externa. Lo que importa comprobar aquí no es que ejecute —eso
ya lo hacen FUN.3 y FUN.5— sino que **la API no relaja nada de lo que el catálogo hace cumplir
dentro**:

* **El anclaje también rige fuera.** La versión va en el cuerpo y es obligatoria: sin ella no se
  ejecuta. Una API que ejecutara «la última» convertiría cada publicación en un cambio silencioso
  de comportamiento para todos sus consumidores externos, que es justo lo que el anclaje existe
  para evitar dentro.
* **La organización se deriva del dueño del PAT**, no del cuerpo. Si viniera en la petición, un
  token robado podría ejecutar contra cualquier organización.
* **Una versión suspendida devuelve 423 con el motivo y no toca el sandbox.** El 423 («locked»)
  y no un 404 porque la función existe y el consumidor tiene que poder distinguir «no está» de
  «está detenida, y por esto».
* **El evento de REG lleva metadatos y no payloads.** La finalidad y las categorías son las que
  la función **declaró**, no las que diga quien llama: si el llamante las eligiera, la
  declaración responsable dejaría de significar nada.
"""
from __future__ import annotations

import uuid

import pytest

from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.contracts.funciones import ContratoFuncion
from server.app.modules.redaccion.funciones_service import registrar_version

_CODE = (
    "result = {'tables': [], 'metrics': [{'name': 'filas', 'value': 2, 'unit': 'filas'}], "
    "'free_text': 'dos filas'}"
)


def _contrato(finalidad="Contar las filas del fichero de gastos"):
    return ContratoFuncion(
        slots=[],
        parametros=[
            {
                "slot_id": "umbral",
                "field_type": "number",
                "label": {"es": "Umbral"},
                "required": False,
            }
        ],
        finalidad=finalidad,
        categorias_datos=["dades_pressupostaries"],
    )


def _pat(organizacion: uuid.UUID | None, *, rol="admin") -> UserInfo:
    return UserInfo(
        user_id=f"pat-{uuid.uuid4()}",
        email="cliente@example.test",
        role=rol,
        organizacion_ids=[organizacion] if organizacion else [],
    )


async def _una_funcion(session, *, organizacion, code=_CODE, contrato=None):
    funcion, version = await registrar_version(
        session,
        nombre="Contar filas",
        organizacion_id=organizacion,
        code=code,
        contrato=contrato or _contrato(),
        declarada_por=uuid.uuid4(),
        audit_result={"approved": True, "risk_level": "SAFE", "findings": []},
    )
    await session.commit()
    await session.refresh(funcion)
    await session.refresh(version)
    return funcion, version


class _SandboxEspia:
    """Un sandbox que anota si lo llamaron. Es lo que demuestra «sin tocar el sandbox»."""

    def __init__(self):
        self.llamadas = []

    async def execute_extraction_script(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        raise AssertionError("no tendría que haberse llamado")


class TestElScopeYLaFrontera:

    def test_should_have_the_new_scope_in_the_catalogue(self):
        """Emisible por superadmin **y** por admin: ejecutar una función de la propia
        organización es una capacidad de la organización, no de la plataforma."""
        from server.app.core.auth.models import UserRole
        from server.app.core.auth.pat.scopes import (
            ALL_SCOPES,
            FUNCIONES_EXECUTE,
            allowed_scopes_for_role,
        )

        assert FUNCIONES_EXECUTE in ALL_SCOPES
        assert FUNCIONES_EXECUTE in allowed_scopes_for_role(UserRole.SUPERADMIN.value)
        assert FUNCIONES_EXECUTE in allowed_scopes_for_role(UserRole.ADMIN.value)

    def test_should_demand_a_machine_token_and_the_scope(self):
        """La guarda es `require_pat_scopes` y no `require_scopes`: esta superficie existe para
        clientes máquina, y una sesión de navegador que pudiera ejecutarla saltaría el rastro."""
        import inspect

        from server.app.routers.redaccion import funciones_run_router

        fuente = inspect.getsource(funciones_run_router)
        assert "require_pat_scopes(FUNCIONES_EXECUTE)" in fuente

    @pytest.mark.asyncio
    async def test_should_answer_404_for_an_unpublished_function_of_another_organizacion(
        self, db_session
    ):
        from fastapi import HTTPException

        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        funcion, _v = await _una_funcion(db_session, organizacion=uuid.uuid4())

        with pytest.raises(HTTPException) as fallo:
            await ejecutar_funcion_por_api(
                funcion_id=funcion.id,
                body=EjecutarRequest(version=1),
                principal=_pat(uuid.uuid4()),
                session=db_session,
            )

        assert fallo.value.status_code == 404


class TestLaVersionEsObligatoria:

    @pytest.mark.asyncio
    async def test_should_refuse_a_request_without_a_version(self, db_session):
        """El anclaje también rige fuera. Ejecutar «la última» convertiría cada publicación en un
        cambio silencioso para todos los consumidores externos."""
        from pydantic import ValidationError

        from server.app.routers.redaccion.funciones_run_router import EjecutarRequest

        with pytest.raises(ValidationError):
            EjecutarRequest()  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_should_answer_404_for_a_version_that_does_not_exist(self, db_session):
        from fastapi import HTTPException

        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion)

        with pytest.raises(HTTPException) as fallo:
            await ejecutar_funcion_por_api(
                funcion_id=funcion.id,
                body=EjecutarRequest(version=7),
                principal=_pat(organizacion),
                session=db_session,
            )

        assert fallo.value.status_code == 404


class TestLoQueNoLlegaAlSandbox:

    @pytest.mark.asyncio
    async def test_should_answer_422_for_invalid_input_without_touching_the_sandbox(
        self, db_session
    ):
        """Validar delante no es una preferencia de estilo: con la validación detrás, el
        consumidor externo recibe un error de pandas dentro de un subproceso."""
        from fastapi import HTTPException

        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion)
        espia = _SandboxEspia()

        with pytest.raises(HTTPException) as fallo:
            await ejecutar_funcion_por_api(
                funcion_id=funcion.id,
                # `umbral` es numérico y llega texto.
                body=EjecutarRequest(version=1, parametros={"umbral": "doce y medio"}),
                principal=_pat(organizacion),
                session=db_session,
                sandbox=espia,
            )

        assert fallo.value.status_code == 422
        assert espia.llamadas == []

    @pytest.mark.asyncio
    async def test_should_answer_423_with_the_reason_for_a_suspended_version(self, db_session):
        """423 y no 404: la función existe, y quien integra tiene que poder distinguir «no está»
        de «está detenida, y por esto»."""
        from fastapi import HTTPException

        from server.app.modules.redaccion.funciones_acciones import suspender
        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion = uuid.uuid4()
        funcion, version = await _una_funcion(db_session, organizacion=organizacion)
        suspender(
            version,
            motivo="lee el almacenamiento sin acotar el ámbito",
            suspendida_por=uuid.uuid4(),
        )
        await db_session.commit()
        espia = _SandboxEspia()

        with pytest.raises(HTTPException) as fallo:
            await ejecutar_funcion_por_api(
                funcion_id=funcion.id,
                body=EjecutarRequest(version=1),
                principal=_pat(organizacion),
                session=db_session,
                sandbox=espia,
            )

        assert fallo.value.status_code == 423
        assert "lee el almacenamiento sin acotar el ámbito" in str(fallo.value.detail)
        assert espia.llamadas == []

    @pytest.mark.asyncio
    async def test_should_refuse_an_input_bigger_than_the_cap(self, db_session):
        """El tope se **hereda** del que VAS.1 fijó, que lo dejó escrito esperando este bloque.
        Dos topes distintos para el mismo riesgo son dos números que divergen."""
        from fastapi import HTTPException

        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )
        from server.app.routers.verificaciones_router import MAXIMO_BYTES

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion)
        espia = _SandboxEspia()

        with pytest.raises(HTTPException) as fallo:
            await ejecutar_funcion_por_api(
                funcion_id=funcion.id,
                body=EjecutarRequest(
                    version=1, parametros={"umbral": 1, "relleno": "x" * (MAXIMO_BYTES + 1)}
                ),
                principal=_pat(organizacion),
                session=db_session,
                sandbox=espia,
            )

        assert fallo.value.status_code == 413
        assert espia.llamadas == []


class TestElCaminoBueno:

    @pytest.mark.asyncio
    async def test_should_execute_and_return_the_extraction_result(self, db_session):
        from server.app.core.sandbox_client import LocalSandboxClient
        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion)

        salida = await ejecutar_funcion_por_api(
            funcion_id=funcion.id,
            body=EjecutarRequest(version=1),
            principal=_pat(organizacion),
            session=db_session,
            sandbox=LocalSandboxClient(),
        )

        assert salida.free_text == "dos filas"
        # Lo que se ejecutó, dicho por la respuesta: sin esto, un consumidor externo no puede
        # anotar en su propio registro qué versión le contestó.
        assert salida.funcion["version"] == 1
        assert len(salida.funcion["code_sha256"]) == 64

    @pytest.mark.asyncio
    async def test_should_write_the_activity_event_with_metadata_and_no_payload(
        self, db_session
    ):
        """Los metadatos sí, el contenido no. Y la finalidad y las categorías son **las
        declaradas por la función**: si las eligiera quien llama, la declaración responsable
        dejaría de significar algo."""
        from sqlalchemy import select

        from server.app.core.sandbox_client import LocalSandboxClient
        from server.app.modules.agents_hub.database.operational_models import HubActividadIA
        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion = uuid.uuid4()
        funcion, version = await _una_funcion(db_session, organizacion=organizacion)
        sha = version.code_sha256

        await ejecutar_funcion_por_api(
            funcion_id=funcion.id,
            body=EjecutarRequest(version=1, parametros={"umbral": 3}),
            principal=_pat(organizacion),
            session=db_session,
            sandbox=LocalSandboxClient(),
        )

        eventos = (
            await db_session.execute(
                select(HubActividadIA).where(
                    HubActividadIA.organizacion_id == organizacion
                )
            )
        ).scalars().all()

        assert len(eventos) == 1
        evento = eventos[0]
        assert evento.finalidad == "Contar las filas del fichero de gastos"
        assert evento.categorias_datos == ["dades_pressupostaries"]
        # La referencia de lo ejecutado va en la herramienta, que es lo que se puede buscar.
        assert str(funcion.id) in evento.herramienta
        assert sha[:12] in evento.herramienta
        # Y ni un rastro de la entrada: el 3 del parámetro no está en ningún campo.
        for campo in (evento.finalidad, evento.herramienta, evento.agente or ""):
            assert "umbral" not in campo

    @pytest.mark.asyncio
    async def test_should_let_another_organizacion_run_a_published_function(self, db_session):
        """La misma frontera del catálogo: publicada se puede usar, no publicada no existe."""
        from datetime import datetime, timezone

        from server.app.core.sandbox_client import LocalSandboxClient
        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion_a, organizacion_b = uuid.uuid4(), uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion_a)
        funcion.publicada_en = datetime.now(timezone.utc)
        funcion.valoracion_promocion = "Revisada: no toca datos personales"
        await db_session.commit()

        salida = await ejecutar_funcion_por_api(
            funcion_id=funcion.id,
            body=EjecutarRequest(version=1),
            principal=_pat(organizacion_b),
            session=db_session,
            sandbox=LocalSandboxClient(),
        )

        assert salida.free_text == "dos filas"


class TestCuandoElSandboxNoContesta:

    @pytest.mark.asyncio
    async def test_should_answer_a_controlled_error_and_not_an_opaque_500(self, db_session):
        """Un timeout es la respuesta más probable ante un script pesado, y para quien integra
        «504 con el motivo» es accionable mientras un 500 no dice si reintentar."""
        import asyncio

        from fastapi import HTTPException

        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion)

        class _SandboxQueNoContesta:
            async def execute_extraction_script(self, *args, **kwargs):
                raise asyncio.TimeoutError()

        with pytest.raises(HTTPException) as fallo:
            await ejecutar_funcion_por_api(
                funcion_id=funcion.id,
                body=EjecutarRequest(version=1),
                principal=_pat(organizacion),
                session=db_session,
                sandbox=_SandboxQueNoContesta(),
            )

        assert fallo.value.status_code == 504
        assert "tiempo" in str(fallo.value.detail).lower()


class TestElCableado:

    def test_should_be_registered_in_main(self):
        import inspect

        from server.app import main

        fuente = inspect.getsource(main)
        assert "redaccion_funciones_run_router" in fuente


class TestCuandoElSandboxNoEstaArrancado:
    """El defecto que salió con el `curl` real: **un sandbox apagado daba un 500 opaco.**

    No es teórico ni de desarrollo: en producción el sandbox es otro servicio, y «el servicio de
    ejecución no responde» es la causa más probable de un fallo que no es culpa de quien integra.
    Un 500 le dice «algo se rompió, mira si es tuyo»; un 503 con el motivo le dice «no es tuyo,
    reintenta» — y es la diferencia entre un aviso al equipo de la plataforma y una tarde
    depurando su propio código.

    El timeout ya estaba cubierto; esto es el otro extremo del mismo camino, y se escapó porque
    los tests traen su sandbox y nunca ven uno ausente.
    """

    @pytest.mark.asyncio
    async def test_should_answer_503_when_the_sandbox_is_unreachable(self, db_session):
        from fastapi import HTTPException

        from server.app.core.sandbox_client import SandboxUnavailableError
        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion)

        class _SandboxApagado:
            async def execute_extraction_script(self, *args, **kwargs):
                raise SandboxUnavailableError(
                    "No se puede conectar al sandbox 'http://script-sandbox:5000'"
                )

        with pytest.raises(HTTPException) as fallo:
            await ejecutar_funcion_por_api(
                funcion_id=funcion.id,
                body=EjecutarRequest(version=1),
                principal=_pat(organizacion),
                session=db_session,
                sandbox=_SandboxApagado(),
            )

        assert fallo.value.status_code == 503
        detalle = str(fallo.value.detail)
        assert "sandbox" in detalle.lower()
        # Y dice que no es culpa de quien llama, que es lo que evita la tarde de depuración.
        assert "reintent" in detalle.lower()

    @pytest.mark.asyncio
    async def test_should_not_write_an_activity_event_when_it_did_not_run(self, db_session):
        """Y **no anota nada en el registro**: un evento de una ejecución que no ocurrió deja el
        registro de actividad contando usos de IA que nadie hizo."""
        from sqlalchemy import select

        from fastapi import HTTPException

        from server.app.core.sandbox_client import SandboxUnavailableError
        from server.app.modules.agents_hub.database.operational_models import HubActividadIA
        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion)

        class _SandboxApagado:
            async def execute_extraction_script(self, *args, **kwargs):
                raise SandboxUnavailableError("apagado")

        with pytest.raises(HTTPException):
            await ejecutar_funcion_por_api(
                funcion_id=funcion.id,
                body=EjecutarRequest(version=1),
                principal=_pat(organizacion),
                session=db_session,
                sandbox=_SandboxApagado(),
            )

        eventos = (
            await db_session.execute(
                select(HubActividadIA).where(
                    HubActividadIA.organizacion_id == organizacion
                )
            )
        ).scalars().all()

        assert eventos == []


class TestLaRespuestaSobreviveAlCommitDelRegistro:
    """El mismo defecto que FUN.4, en el sitio nuevo — y lo volvió a destapar un `curl` real.

    `api/deps.py::get_session` construye la sesión sin `expire_on_commit=False`, así que anotar el
    evento del registro **expira** la función y la versión, y componer la respuesta después
    dispara una recarga perezosa: `MissingGreenlet`. El evento se guarda y el consumidor recibe un
    500 sobre una ejecución que sí ocurrió — lo peor posible, porque reintentará y quedarán dos
    eventos para un solo uso.

    Los 15 tests del router pasaban porque el fixture `db_session` no reproduce
    `expire_on_commit`. Van dos veces; la lección es que **todo endpoint que commitea y luego
    compone respuesta necesita un test con la sesión de producción**, y en este módulo ya hay dos
    sitios donde mirarlo.
    """

    @pytest.fixture
    async def sesion_como_la_de_produccion(self, db_url: str):
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlmodel.ext.asyncio.session import AsyncSession

        engine = create_async_engine(db_url)
        async with AsyncSession(engine) as session:
            yield session
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_should_answer_the_result_and_not_a_500(self, sesion_como_la_de_produccion):
        from server.app.core.sandbox_client import LocalSandboxClient
        from server.app.routers.redaccion.funciones_run_router import (
            EjecutarRequest,
            ejecutar_funcion_por_api,
        )

        session = sesion_como_la_de_produccion
        organizacion = uuid.uuid4()
        funcion, version = await _una_funcion(session, organizacion=organizacion)
        funcion_id, sha = funcion.id, version.code_sha256

        salida = await ejecutar_funcion_por_api(
            funcion_id=funcion_id,
            body=EjecutarRequest(version=1),
            principal=_pat(organizacion),
            session=session,
            sandbox=LocalSandboxClient(),
        )

        assert salida.free_text == "dos filas"
        assert salida.funcion["version"] == 1
        assert salida.funcion["code_sha256"] == sha
