"""FUN.4 — la revisión posterior, por la superficie HTTP y contra una sesión real.

El fichero hermano (`test_fun4_revision_posterior.py`) fija la máquina de estados. Aquí se
comprueba lo que sólo se ve al atravesar el router, que es donde históricamente se han colado los
defectos de este proyecto:

* que **estar en la cola no impide ejecutar** — la versión que la cola devuelve como
  `sin_revisar` la resuelve el resolutor a la vez. Es el nivel 2 de la Instrucció 02/2026, y es
  la única forma de demostrarlo sin ambigüedad: preguntando a las dos superficies por la misma
  fila;
* que `acciones_permitidas` y la autorización del endpoint **son la misma lista** — si un botón
  aparece, su endpoint no responde 403;
* que una organización no ve las funciones no publicadas de otra;
* y con sesión real y no `AsyncMock`, porque `expire_on_commit` sobre `AsyncSession` es lo que
  reventaba en ocho endpoints de `scripts_router` sin que ningún test mockeado lo cazara.
"""
from __future__ import annotations

import uuid

import pytest

from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.contracts.funciones import ContratoFuncion
from server.app.modules.redaccion.funciones_service import registrar_version
from server.app.routers.redaccion.funciones_router import (
    PromoverRequest,
    RevisarRequest,
    SolicitarPromocionRequest,
    SuspenderRequest,
    cola_de_revision as _cola_de_revision,
    listar_funciones as _listar_funciones,
    promover_funcion as _promover_funcion,
    reactivar_version as _reactivar_version,
    revisar_version as _revisar_version,
    solicitar_promocion as _solicitar_promocion,
    suspender_version as _suspender_version,
    ver_funcion as _ver_funcion,
)

_CODE = "result = {'tables': [], 'metrics': [], 'free_text': 'ok'}"


def _contrato() -> ContratoFuncion:
    return ContratoFuncion(
        slots=[],
        parametros=[],
        finalidad="Contar las filas del fichero de gastos",
        categorias_datos=["sin_datos_personales"],
    )


def _principal(
    *, organizacion: uuid.UUID | None, superadmin: bool = False, admin: bool = False,
    user_id: str | None = None,
) -> UserInfo:
    return UserInfo(
        user_id=user_id or str(uuid.uuid4()),
        email="quien@uji.es",
        role="superadmin" if superadmin else ("admin" if admin else "user"),
        organizacion_ids=[organizacion] if organizacion else [],
    )


async def _una_funcion(session, *, organizacion: uuid.UUID, autor: uuid.UUID, nombre="Contar"):
    funcion, version = await registrar_version(
        session,
        nombre=nombre,
        organizacion_id=organizacion,
        code=_CODE,
        contrato=_contrato(),
        declarada_por=autor,
        audit_result={"approved": True, "risk_level": "SAFE", "findings": []},
    )
    await session.commit()
    # Recarga explícita: con `expire_on_commit=True` —lo que usa la sesión de producción— leer
    # `funcion.id` aquí dispararía la misma recarga perezosa que el defecto que este fichero
    # cubre, y el test moriría en el andamio en vez de en lo que mide.
    await session.refresh(funcion)
    await session.refresh(version)
    return funcion, version


class TestRevisarNoBloqueaUsar:
    """El corazón del nivel 2, comprobado sobre la misma fila desde las dos superficies."""

    @pytest.mark.asyncio
    async def test_should_be_in_the_queue_and_executable_at_the_same_time(self, db_session):
        from server.app.modules.redaccion.funciones_resolver import ResolvedorDeFuncion

        organizacion, autor = uuid.uuid4(), uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion, autor=autor)
        revisor = _principal(organizacion=organizacion, admin=True)

        cola = await _cola_de_revision(
            estado="sin_revisar", muestra=None, principal=revisor, session=db_session
        )
        en_cola = [f for f in cola if f.funcion_id == funcion.id]

        assert en_cola, "la versión recién registrada tiene que estar en la cola"
        # Y a la vez se ejecuta: nadie ha aprobado nada.
        ejecutable = await ResolvedorDeFuncion(db_session).resolver(funcion.id, 1)
        assert ejecutable.code == _CODE

    @pytest.mark.asyncio
    async def test_should_stay_executable_after_asking_for_corrections(self, db_session):
        """`correcciones` es una petición al autor, no un freno: la versión sigue en uso."""
        from server.app.modules.redaccion.funciones_resolver import ResolvedorDeFuncion

        organizacion, autor = uuid.uuid4(), uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion, autor=autor)
        revisor = _principal(organizacion=organizacion, admin=True)

        vista = await _revisar_version(
            funcion_id=funcion.id,
            numero=1,
            body=RevisarRequest(resultado="correcciones", nota="falta acotar la ruta"),
            principal=revisor,
            session=db_session,
        )

        assert (vista.estado, vista.revision_resultado) == ("registrada", "correcciones")
        assert (await ResolvedorDeFuncion(db_session).resolver(funcion.id, 1)).code == _CODE

    @pytest.mark.asyncio
    async def test_should_leave_the_queue_once_reviewed(self, db_session):
        organizacion, autor = uuid.uuid4(), uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion, autor=autor)
        revisor = _principal(organizacion=organizacion, admin=True)

        await _revisar_version(
            funcion_id=funcion.id, numero=1,
            body=RevisarRequest(resultado="conforme", nota=None),
            principal=revisor, session=db_session,
        )

        sin_revisar = await _cola_de_revision(
            estado="sin_revisar", muestra=None, principal=revisor, session=db_session
        )
        todas = await _cola_de_revision(
            estado="todas", muestra=None, principal=revisor, session=db_session
        )

        assert funcion.id not in [f.funcion_id for f in sin_revisar]
        assert funcion.id in [f.funcion_id for f in todas]


class TestElBotonYElEndpointDicenLoMismo:
    """Regla maestra 2, comprobada en los dos sentidos."""

    @pytest.mark.asyncio
    async def test_should_refuse_the_action_it_does_not_offer(self, db_session):
        """La autora no puede revisar su propia versión, y el endpoint tampoco se lo deja."""
        from fastapi import HTTPException

        organizacion = uuid.uuid4()
        autor = uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion, autor=autor)
        # `creada_por` guarda el uuid5 del user_id, así que la autora se reconoce por él.
        from server.app.routers.redaccion._actor import user_to_uuid

        yo = str(uuid.uuid4())
        funcion.creada_por = user_to_uuid(yo)
        await db_session.commit()
        la_autora = _principal(organizacion=organizacion, admin=True, user_id=yo)

        vista = await _ver_funcion(
            funcion_id=funcion.id, principal=la_autora, session=db_session
        )
        assert "revisar" not in vista.versiones[0].acciones_permitidas

        with pytest.raises(HTTPException) as fallo:
            await _revisar_version(
                funcion_id=funcion.id, numero=1,
                body=RevisarRequest(resultado="conforme", nota=None),
                principal=la_autora, session=db_session,
            )
        assert fallo.value.status_code == 403

    @pytest.mark.asyncio
    async def test_should_honour_every_action_it_offers(self, db_session):
        """Y al revés, que es la mitad que se olvida: cada acción ofrecida se puede pedir."""
        organizacion, autor = uuid.uuid4(), uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion, autor=autor)
        revisor = _principal(organizacion=organizacion, admin=True)

        vista = await _ver_funcion(
            funcion_id=funcion.id, principal=revisor, session=db_session
        )
        ofrecidas = set(vista.versiones[0].acciones_permitidas)

        assert {"revisar", "suspender"} <= ofrecidas
        # Suspender, que es la que tiene cuerpo obligatorio, se acepta tal cual.
        suspendida = await _suspender_version(
            funcion_id=funcion.id, numero=1,
            body=SuspenderRequest(motivo="escribe en una ruta absoluta"),
            principal=revisor, session=db_session,
        )
        assert suspendida.estado == "suspendida"
        assert "reactivar" in suspendida.acciones_permitidas

        reactivada = await _reactivar_version(
            funcion_id=funcion.id, numero=1, principal=revisor, session=db_session
        )
        assert reactivada.estado == "registrada"
        # El motivo se conserva: es historia de por qué estuvo suspendida.
        assert reactivada.motivo_suspension == "escribe en una ruta absoluta"

    @pytest.mark.asyncio
    async def test_should_refuse_to_suspend_without_a_reason(self, db_session):
        """El bloque anclado va a fallar en alto: tiene que poder decir por qué."""
        from fastapi import HTTPException

        organizacion, autor = uuid.uuid4(), uuid.uuid4()
        funcion, _v = await _una_funcion(db_session, organizacion=organizacion, autor=autor)
        revisor = _principal(organizacion=organizacion, admin=True)

        with pytest.raises(HTTPException) as fallo:
            await _suspender_version(
                funcion_id=funcion.id, numero=1,
                body=SuspenderRequest(motivo="   "),
                principal=revisor, session=db_session,
            )

        assert fallo.value.status_code == 422
        assert "motivo" in str(fallo.value.detail)


class TestLaFronteraEntreOrganizaciones:

    @pytest.mark.asyncio
    async def test_should_not_show_another_organizations_unpublished_function(self, db_session):
        organizacion_a, organizacion_b = uuid.uuid4(), uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion_a, autor=uuid.uuid4()
        )

        catalogo = await _listar_funciones(
            principal=_principal(organizacion=organizacion_b), session=db_session
        )

        assert funcion.id not in [f.id for f in catalogo]

    @pytest.mark.asyncio
    async def test_should_answer_404_and_not_403_for_a_function_it_cannot_see(self, db_session):
        """404 y no 403: un 403 ya cuenta que esa función existe."""
        from fastapi import HTTPException

        funcion, _v = await _una_funcion(
            db_session, organizacion=uuid.uuid4(), autor=uuid.uuid4()
        )

        with pytest.raises(HTTPException) as fallo:
            await _ver_funcion(
                funcion_id=funcion.id,
                principal=_principal(organizacion=uuid.uuid4()),
                session=db_session,
            )

        assert fallo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_show_a_published_function_to_everyone(self, db_session):
        organizacion_a, organizacion_b = uuid.uuid4(), uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion_a, autor=uuid.uuid4()
        )

        funcion.promocion_solicitada_en = _ahora()
        funcion.motivo_promocion = "la usan tres servicios"
        await db_session.commit()
        await _promover_funcion(
            funcion_id=funcion.id,
            body=PromoverRequest(valoracion="Revisada: no toca datos personales"),
            principal=_principal(organizacion=None, superadmin=True),
            session=db_session,
        )

        catalogo = await _listar_funciones(
            principal=_principal(organizacion=organizacion_b), session=db_session
        )
        vista = [f for f in catalogo if f.id == funcion.id]

        assert vista, "una función publicada la ve cualquier organización"
        # Nivel 3, y la organización autora se conserva como atribución.
        assert vista[0].nivel == 3
        assert vista[0].organizacion_id == organizacion_a
        # Y lo único que puede hacer con ella es anclar una versión.
        assert vista[0].versiones[0].acciones_permitidas == ["adoptar_version"]


class TestElPasoANivel3:

    @pytest.mark.asyncio
    async def test_should_need_the_request_before_the_superadmin_can_promote(self, db_session):
        from fastapi import HTTPException

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion, autor=uuid.uuid4()
        )
        superadmin = _principal(organizacion=None, superadmin=True)

        vista = await _ver_funcion(
            funcion_id=funcion.id, principal=superadmin, session=db_session
        )
        assert not vista.candidata_nivel_3
        with pytest.raises(HTTPException) as fallo:
            await _promover_funcion(
                funcion_id=funcion.id,
                body=PromoverRequest(valoracion="me parece bien"),
                principal=superadmin, session=db_session,
            )
        assert fallo.value.status_code == 403

        await _solicitar_promocion(
            funcion_id=funcion.id,
            body=SolicitarPromocionRequest(motivo="la usan tres servicios"),
            principal=_principal(organizacion=organizacion, admin=True),
            session=db_session,
        )

        vista = await _ver_funcion(
            funcion_id=funcion.id, principal=superadmin, session=db_session
        )
        assert vista.candidata_nivel_3
        assert vista.motivos_nivel_3 == ["su organización ha solicitado la promoción"]

    @pytest.mark.asyncio
    async def test_should_refuse_to_promote_without_a_written_valuation(self, db_session):
        """La única aprobación previa del catálogo, y por eso tiene que quedar escrita."""
        from fastapi import HTTPException

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion, autor=uuid.uuid4()
        )
        funcion.promocion_solicitada_en = _ahora()
        await db_session.commit()

        with pytest.raises(HTTPException) as fallo:
            await _promover_funcion(
                funcion_id=funcion.id,
                body=PromoverRequest(valoracion="  "),
                principal=_principal(organizacion=None, superadmin=True),
                session=db_session,
            )

        assert fallo.value.status_code == 422
        assert "valoración" in str(fallo.value.detail)


class TestLaColaDiceSiRevisarEsUrgente:

    @pytest.mark.asyncio
    async def test_should_count_the_templates_that_anchor_the_version(self, db_session):
        """Cuántas plantillas la usan sale del spec, y **el par función+versión tiene que
        coincidir**: una plantilla que cite la función en un bloque y el número en otro no
        cuenta."""
        from server.app.modules.redaccion.database.models import (
            HubReportTemplate,
            HubReportTemplateVersion,
        )

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion, autor=uuid.uuid4()
        )

        plantilla = HubReportTemplate(
            name="Con la función", report_profile="GENERIC_REPORT", owner_kind="platform"
        )
        db_session.add(plantilla)
        await db_session.flush()
        db_session.add(
            HubReportTemplateVersion(
                template_id=plantilla.id, version=1, created_by=uuid.uuid4(),
                spec_json={
                    "blocks": [
                        {
                            "id": "b1",
                            "kind": "DETERMINISTIC_DATA",
                            "funcion_ref": {"funcion_id": str(funcion.id), "version": 1},
                        }
                    ]
                },
            )
        )
        # La trampa: cita la función, pero anclada a la versión 2.
        db_session.add(
            HubReportTemplateVersion(
                template_id=plantilla.id, version=2, created_by=uuid.uuid4(),
                spec_json={
                    "blocks": [
                        {
                            "id": "b1",
                            "kind": "DETERMINISTIC_DATA",
                            "funcion_ref": {"funcion_id": str(funcion.id), "version": 2},
                        }
                    ]
                },
            )
        )
        await db_session.commit()

        cola = await _cola_de_revision(
            estado="sin_revisar", muestra=None,
            principal=_principal(organizacion=organizacion, admin=True),
            session=db_session,
        )
        fila = [f for f in cola if f.funcion_id == funcion.id][0]

        assert fila.plantillas_que_la_usan == 1

    @pytest.mark.asyncio
    async def test_should_sample_at_most_what_it_is_asked_for(self, db_session):
        organizacion = uuid.uuid4()
        for i in range(4):
            await _una_funcion(
                db_session, organizacion=organizacion, autor=uuid.uuid4(),
                nombre=f"Función {i}",
            )

        cola = await _cola_de_revision(
            estado="sin_revisar", muestra=2,
            principal=_principal(organizacion=organizacion, admin=True),
            session=db_session,
        )

        assert len(cola) == 2


class TestLaSuspensionLlegaHastaElBloque:
    """La cadena entera, que es donde el motivo justifica su existencia.

    Suspender no sirve de nada si el informe que usa la función sigue saliendo. Y si falla sin
    decir por qué, quien recibe el error no puede hacer nada: por eso el motivo es obligatorio en
    el endpoint y por eso tiene que aparecer **aquí**, en el fallo del resolutor.
    """

    @pytest.mark.asyncio
    async def test_should_make_the_anchored_block_fail_out_loud_with_the_reason(self, db_session):
        from server.app.modules.redaccion.funciones_resolver import (
            FuncionNoEjecutable,
            ResolvedorDeFuncion,
        )

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion, autor=uuid.uuid4()
        )
        revisor = _principal(organizacion=organizacion, admin=True)

        # Antes: se ejecuta.
        assert (await ResolvedorDeFuncion(db_session).resolver(funcion.id, 1)).code == _CODE

        await _suspender_version(
            funcion_id=funcion.id, numero=1,
            body=SuspenderRequest(motivo="escribe en una ruta absoluta del servidor"),
            principal=revisor, session=db_session,
        )

        with pytest.raises(FuncionNoEjecutable) as fallo:
            await ResolvedorDeFuncion(db_session).resolver(funcion.id, 1)
        assert "escribe en una ruta absoluta del servidor" in str(fallo.value)

        # Y al reactivarla vuelve a ejecutarse: la suspensión es reversible, la retirada no.
        await _reactivar_version(
            funcion_id=funcion.id, numero=1, principal=revisor, session=db_session
        )
        assert (await ResolvedorDeFuncion(db_session).resolver(funcion.id, 1)).code == _CODE

    @pytest.mark.asyncio
    async def test_should_not_let_the_author_undo_someone_elses_suspension(self, db_session):
        """Dos responsabilidades (§9): si la autora pudiera reactivar, suspender no sería una
        decisión, sería una sugerencia."""
        from fastapi import HTTPException

        from server.app.routers.redaccion._actor import user_to_uuid

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion, autor=uuid.uuid4()
        )
        yo = str(uuid.uuid4())
        funcion.creada_por = user_to_uuid(yo)
        await db_session.commit()

        await _suspender_version(
            funcion_id=funcion.id, numero=1,
            body=SuspenderRequest(motivo="lee un fichero del escritorio"),
            principal=_principal(organizacion=organizacion, admin=True),
            session=db_session,
        )

        with pytest.raises(HTTPException) as fallo:
            await _reactivar_version(
                funcion_id=funcion.id, numero=1,
                principal=_principal(organizacion=organizacion, admin=True, user_id=yo),
                session=db_session,
            )

        assert fallo.value.status_code == 403


class TestElNivel3PorLaSuperficie:

    @pytest.mark.asyncio
    async def test_should_refuse_to_let_the_organizacion_admin_promote(self, db_session):
        """Promover es del superadministrador. Un admin de organización que pudiera promover
        estaría decidiendo el alcance de la plataforma entera."""
        from fastapi import HTTPException

        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion, autor=uuid.uuid4()
        )
        admin = _principal(organizacion=organizacion, admin=True)

        await _solicitar_promocion(
            funcion_id=funcion.id,
            body=SolicitarPromocionRequest(motivo="la usan tres servicios"),
            principal=admin, session=db_session,
        )

        with pytest.raises(HTTPException) as fallo:
            await _promover_funcion(
                funcion_id=funcion.id,
                body=PromoverRequest(valoracion="me vale"),
                principal=admin, session=db_session,
            )

        assert fallo.value.status_code == 403

    @pytest.mark.asyncio
    async def test_should_mark_the_candidacy_when_a_review_reclassifies_the_scope(self, db_session):
        """`reclasificada` no frena la versión: lo que hace es señalar que su alcance excede el
        nivel 2, y eso llega al DTO como candidatura."""
        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            db_session, organizacion=organizacion, autor=uuid.uuid4()
        )
        revisor = _principal(organizacion=organizacion, admin=True)

        vista = await _revisar_version(
            funcion_id=funcion.id, numero=1,
            body=RevisarRequest(resultado="reclasificada", nota="afecta a toda la universidad"),
            principal=revisor, session=db_session,
        )
        assert vista.estado == "registrada"

        ficha = await _ver_funcion(
            funcion_id=funcion.id, principal=revisor, session=db_session
        )
        assert ficha.candidata_nivel_3
        assert ficha.motivos_nivel_3 == [
            "una revisión la reclasificó: su alcance excede el nivel 2"
        ]

    @pytest.mark.asyncio
    async def test_should_not_touch_any_code_hash_when_promoting(self, db_session):
        """Promover es una decisión sobre el alcance, no sobre el código. Si tocara el hash, el
        manifiesto de un informe anterior dejaría de cuadrar."""
        organizacion = uuid.uuid4()
        funcion, version = await _una_funcion(
            db_session, organizacion=organizacion, autor=uuid.uuid4()
        )
        sha_antes = version.code_sha256

        funcion.promocion_solicitada_en = _ahora()
        await db_session.commit()
        await _promover_funcion(
            funcion_id=funcion.id,
            body=PromoverRequest(valoracion="Revisada: no toca datos personales"),
            principal=_principal(organizacion=None, superadmin=True),
            session=db_session,
        )

        ficha = await _ver_funcion(
            funcion_id=funcion.id,
            principal=_principal(organizacion=None, superadmin=True),
            session=db_session,
        )

        assert ficha.versiones[0].code_sha256 == sha_antes
        assert ficha.versiones[0].estado == "registrada"


class TestLaRespuestaSobreviveAlCommit:
    """El defecto que destapó la pantalla: escribía bien y respondía 500.

    `api/deps.py::get_session` construye la sesión sobre el motor del servidor a pelo —sin pasar
    por ningún `sessionmaker`—, y ahí `expire_on_commit` vale **`True`** —el `expire_on_commit=False` está en el `sessionmaker` de
    `database/db.py`, que es otro `get_session` distinto—. Así que todo endpoint que hace
    `commit()` y **luego** lee un atributo del objeto ORM dispara una recarga perezosa síncrona y
    revienta con `MissingGreenlet`.

    La suspensión se guardaba con su motivo y la respuesta era un 500: lo peor de los dos mundos,
    porque quien revisa ve un error y cree que no ha pasado nada sobre una versión que acaba de
    quedar detenida.

    El fixture `db_session` **no lo reproduce** —su factoría pone `expire_on_commit=False`—, que
    es exactamente por lo que los 18 tests del router pasaban en verde. Por eso este test trae su
    propia sesión, con la configuración de la aplicación.
    """

    @pytest.fixture
    async def sesion_como_la_de_produccion(self, db_url: str):
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlmodel.ext.asyncio.session import AsyncSession

        engine = create_async_engine(db_url)
        # Sin `expire_on_commit=False`: tal cual la construye `api/deps.py::get_session`, que
        # es lo que hace aparecer el defecto. (Y sobre `db_url`, la base desechable: aquí no
        # se toca la del desarrollador.)
        async with AsyncSession(engine) as session:
            yield session
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_should_answer_the_view_and_not_a_500_after_committing(
        self, sesion_como_la_de_produccion
    ):
        session = sesion_como_la_de_produccion
        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            session, organizacion=organizacion, autor=uuid.uuid4()
        )
        revisor = _principal(organizacion=organizacion, admin=True)

        vista = await _revisar_version(
            funcion_id=funcion.id, numero=1,
            body=RevisarRequest(resultado="conforme", nota="mirada"),
            principal=revisor, session=session,
        )

        assert (vista.version, vista.estado) == (1, "registrada")
        assert vista.revision_resultado == "conforme"

    @pytest.mark.asyncio
    async def test_should_do_the_same_on_every_endpoint_that_commits(
        self, sesion_como_la_de_produccion
    ):
        """Los cinco, y no sólo el que se probó a mano: el defecto era del patrón, no de uno."""
        session = sesion_como_la_de_produccion
        organizacion = uuid.uuid4()
        funcion, _v = await _una_funcion(
            session, organizacion=organizacion, autor=uuid.uuid4()
        )
        admin = _principal(organizacion=organizacion, admin=True)
        # El id se guarda una vez, como hace la ruta: cada petición real lo trae en la URL y no
        # lo relee de un objeto ORM que el commit anterior ha expirado.
        funcion_id = funcion.id

        suspendida = await _suspender_version(
            funcion_id=funcion_id, numero=1,
            body=SuspenderRequest(motivo="lee fuera de su ámbito"),
            principal=admin, session=session,
        )
        assert suspendida.estado == "suspendida"

        reactivada = await _reactivar_version(
            funcion_id=funcion_id, numero=1, principal=admin, session=session
        )
        assert reactivada.estado == "registrada"

        pedida = await _solicitar_promocion(
            funcion_id=funcion_id,
            body=SolicitarPromocionRequest(motivo="la usan tres servicios"),
            principal=admin, session=session,
        )
        assert pedida.candidata_nivel_3

        promovida = await _promover_funcion(
            funcion_id=funcion_id,
            body=PromoverRequest(valoracion="Revisada: no toca datos personales"),
            principal=_principal(organizacion=None, superadmin=True),
            session=session,
        )
        assert promovida.nivel == 3
        assert promovida.versiones[0].version == 1


class TestElCatalogoTieneUnOrden:
    """DET.1 sobre el catálogo, y no por doctrina: pasó.

    Durante la verificación, la misma lista devolvió las funciones en **otro orden** después de
    una mutación, porque `listar_funciones` no llevaba `ORDER BY` y Postgres no promete ninguno.
    Lo noté porque la ficha que estaba leyendo se movió de sitio; en una pantalla con botones de
    suspender, moverse de sitio significa pulsar sobre otra fila.

    El desempate por `id` es la otra mitad: sin él, dos funciones creadas en el mismo segundo
    —las que crea una migración, por ejemplo— pueden alternarse entre dos consultas idénticas.
    """

    @pytest.mark.asyncio
    async def test_should_return_the_catalogue_in_a_stable_order(self, db_session):
        organizacion = uuid.uuid4()
        for i in range(6):
            await _una_funcion(
                db_session, organizacion=organizacion, autor=uuid.uuid4(),
                nombre=f"Función {i}",
            )
        principal = _principal(organizacion=organizacion, admin=True)

        primera = await _listar_funciones(principal=principal, session=db_session)
        segunda = await _listar_funciones(principal=principal, session=db_session)

        assert [f.id for f in primera] == [f.id for f in segunda]

    @pytest.mark.asyncio
    async def test_should_break_the_tie_by_id_when_created_at_matches(self, db_session):
        """Y el desempate se comprueba con el mismo instante en las dos, que es el caso real de
        una migración: sin `id` en el `ORDER BY`, el orden queda al azar del plan de consulta."""
        from datetime import datetime, timezone

        organizacion = uuid.uuid4()
        mismo_instante = datetime.now(timezone.utc)
        for i in range(6):
            funcion, _v = await _una_funcion(
                db_session, organizacion=organizacion, autor=uuid.uuid4(),
                nombre=f"Gemela {i}",
            )
            funcion.created_at = mismo_instante
        await db_session.commit()

        principal = _principal(organizacion=organizacion, admin=True)
        ids = [
            [f.id for f in await _listar_funciones(principal=principal, session=db_session)]
            for _ in range(3)
        ]

        assert ids[0] == ids[1] == ids[2]
        # Y el orden es el del desempate, no uno cualquiera que coincida tres veces.
        assert ids[0] == sorted(ids[0], key=str)


def _ahora():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
