"""FUN.4 — la revisión posterior, la suspensión y el paso a nivel 3.

Aquí la Instrucció 02/2026 se convierte en máquina de estados y en acciones por rol. Lo que
gobierna todo el fichero es una idea: **el control es proporcional al alcance**.

* **Nivel 2** (compartir dentro del servicio): el filtro es automático y la persona entra
  después. Revisar **no bloquea usar** — una versión recién registrada está en la cola de
  revisión *y* funcionando a la vez. Eso no es un descuido: es lo que la Instrucció exige (§5),
  porque la aprobación previa es lo que empuja al *Shadow IT*.
* **El muestreo existe para que revisar no exija leerlo todo** (§8.4). Sin él, «revisión
  posterior» se convierte en una cola que nadie mira.
* **Suspender es de quien revisa; retirar es de quien escribe.** Dos responsabilidades distintas
  de la matriz de roles (§9), y por eso el autor no puede reactivar lo que otro suspendió.
* **Nivel 3** (alcance superior al servicio) sí lleva aprobación **previa**: la promoción la
  valora el superadministrador, con motivo escrito. Es la única del bloque, y es previa porque
  el nivel 3 lo es.

Y una regla de la casa: **`acciones_permitidas` las calcula el servidor** (regla maestra 2). El
test de una persona sin permisos recibiendo la lista vacía es obligatorio.
"""
from __future__ import annotations

import uuid

import pytest


# ──────────────────────────── Dobles ────────────────────────────


def _version(**kw):
    """Una versión del catálogo, con lo justo para decidir acciones."""
    from types import SimpleNamespace

    datos = {
        "id": uuid.uuid4(),
        "version": 1,
        "estado": "registrada",
        "revisada_por": None,
        "revision_resultado": None,
        "motivo_suspension": None,
        "suspendida_por": None,
        "autoria": "ia",
    }
    datos.update(kw)
    return SimpleNamespace(**datos)


def _funcion(**kw):
    from types import SimpleNamespace

    datos = {
        "id": uuid.uuid4(),
        "nombre": "Extraer gastos",
        "organizacion_id": uuid.uuid4(),
        "origen": "autoservicio",
        "publicada_en": None,
        "promocion_solicitada_en": None,
        "creada_por": uuid.uuid4(),
    }
    datos.update(kw)
    ns = SimpleNamespace(**datos)
    ns.nivel = 3 if (ns.origen == "paquete" or ns.publicada_en is not None) else 2
    return ns


def _principal(*, rol="user", organizacion=None, user_id=None):
    from server.app.core.auth.models import UserInfo

    return UserInfo(
        user_id=str(user_id or uuid.uuid4()),
        email="quien@ejemplo.test",
        role=rol,
        organizacion_ids=(str(organizacion),) if organizacion else (),
    )


# ──────────────────────────── Quién puede qué ────────────────────────────


class TestAccionesPermitidas:
    """La lista la calcula el servidor, y es un **subconjunto** de lo posible: si una acción
    aparece, su endpoint no puede responder 403 ni 422 por estado."""

    def test_should_offer_nothing_to_someone_with_no_permissions(self):
        """Test obligatorio de la regla maestra 2. Y no es teórico: una lista vacía es lo que
        hace que la pantalla no pinte un botón que iba a dar 403."""
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        de_otra = _funcion(organizacion_id=uuid.uuid4())

        acciones = acciones_permitidas(
            de_otra,
            _version(),
            principal=_principal(rol="user", organizacion=uuid.uuid4()),
        )

        assert acciones == []

    def test_should_let_the_author_version_and_withdraw(self):
        """Retirar es de quien escribe: es su función."""
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        organizacion = uuid.uuid4()
        autora = uuid.uuid4()
        funcion = _funcion(organizacion_id=organizacion, creada_por=autora)

        acciones = acciones_permitidas(
            funcion,
            _version(),
            principal=_principal(rol="user", organizacion=organizacion, user_id=autora),
        )

        assert "versionar" in acciones
        assert "retirar" in acciones
        # Y no puede revisarse a sí misma: revisar es de otra persona.
        assert "revisar" not in acciones
        assert "suspender" not in acciones

    def test_should_let_the_organizacion_admin_review_and_suspend(self):
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        organizacion = uuid.uuid4()
        funcion = _funcion(organizacion_id=organizacion)

        acciones = acciones_permitidas(
            funcion,
            _version(),
            principal=_principal(rol="admin", organizacion=organizacion),
        )

        assert "revisar" in acciones
        assert "suspender" in acciones
        assert "solicitar_promocion" in acciones
        # Promover es del superadministrador: el nivel 3 excede el servicio.
        assert "promover" not in acciones

    def test_should_let_only_the_superadmin_promote(self):
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        funcion = _funcion(promocion_solicitada_en="2026-09-18T00:00:00Z")

        del_admin = acciones_permitidas(
            funcion, _version(), principal=_principal(rol="admin", organizacion=funcion.organizacion_id)
        )
        del_super = acciones_permitidas(
            funcion, _version(), principal=_principal(rol="superadmin")
        )

        assert "promover" not in del_admin
        assert "promover" in del_super

    def test_should_offer_reactivate_instead_of_suspend_when_suspended(self):
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        organizacion = uuid.uuid4()
        funcion = _funcion(organizacion_id=organizacion)

        acciones = acciones_permitidas(
            funcion,
            _version(estado="suspendida", suspendida_por=uuid.uuid4()),
            principal=_principal(rol="admin", organizacion=organizacion),
        )

        assert "reactivar" in acciones
        assert "suspender" not in acciones

    def test_should_not_let_the_author_reactivate_what_someone_else_suspended(self):
        """Dos responsabilidades distintas (§9): si el autor pudiera reactivar, suspender no
        sería una decisión de quien revisa, sería una sugerencia."""
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        organizacion = uuid.uuid4()
        autora = uuid.uuid4()
        funcion = _funcion(organizacion_id=organizacion, creada_por=autora)

        acciones = acciones_permitidas(
            funcion,
            _version(estado="suspendida", suspendida_por=uuid.uuid4()),
            principal=_principal(rol="user", organizacion=organizacion, user_id=autora),
        )

        assert "reactivar" not in acciones

    def test_should_offer_nothing_that_changes_a_withdrawn_version(self):
        """`retirada` es terminal: ofrecer «suspender» sobre ella sería un botón que da 422."""
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        organizacion = uuid.uuid4()
        funcion = _funcion(organizacion_id=organizacion)

        acciones = acciones_permitidas(
            funcion,
            _version(estado="retirada"),
            principal=_principal(rol="superadmin"),
        )

        assert "suspender" not in acciones
        assert "reactivar" not in acciones
        assert "retirar" not in acciones

    def test_should_not_offer_versioning_or_promoting_a_packaged_function(self):
        """Una función empaquetada se versiona con `pip` y ya es de plataforma. Lo que sí se
        puede es **retirarla**: el superadministrador puede vetar una instalada."""
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        funcion = _funcion(origen="paquete", organizacion_id=None, publicada_en="2026-09-18")

        acciones = acciones_permitidas(
            funcion, _version(), principal=_principal(rol="superadmin")
        )

        assert "versionar" not in acciones
        assert "promover" not in acciones
        assert "retirar" in acciones

    def test_should_let_another_organizacion_reference_a_published_function(self):
        """La organización B puede usar lo publicado por A, y no puede tocarlo."""
        from server.app.modules.redaccion.funciones_acciones import acciones_permitidas

        de_a = _funcion(publicada_en="2026-09-18T00:00:00Z")

        acciones = acciones_permitidas(
            de_a, _version(), principal=_principal(rol="admin", organizacion=uuid.uuid4())
        )

        assert "adoptar_version" in acciones
        assert "versionar" not in acciones
        assert "suspender" not in acciones


# ──────────────────────────── El circuito de la revisión ────────────────────────────


class TestLaRevisionNoBloqueaElUso:

    def test_should_not_change_the_state_when_the_result_is_corrections(self):
        """`correcciones` **no** cambia el estado: la versión sigue usable y la corrección es una
        versión nueva del autor. Si bloqueara, la revisión posterior sería aprobación previa con
        otro nombre."""
        from server.app.modules.redaccion.funciones_acciones import aplicar_revision

        version = _version()

        aplicar_revision(
            version,
            resultado="correcciones",
            nota="usa una ruta absoluta",
            revisada_por=uuid.uuid4(),
        )

        assert version.estado == "registrada"
        assert version.revision_resultado == "correcciones"

    def test_should_mark_the_function_as_a_level_three_candidate_when_reclassified(self):
        """`reclasificada` tampoco cambia el estado: anota que el alcance excede el nivel 2 y
        **señala**. La Instrucció deja la valoración a personas; la plataforma sólo la marca."""
        from server.app.modules.redaccion.funciones_acciones import (
            aplicar_revision,
            candidata_a_nivel_3,
        )

        funcion = _funcion()
        version = _version()

        aplicar_revision(
            version, resultado="reclasificada", nota="lo usa otro servicio",
            revisada_por=uuid.uuid4(),
        )

        assert version.estado == "registrada"
        candidata, motivos = candidata_a_nivel_3(funcion, [version])
        assert candidata is True
        assert any("reclasific" in m for m in motivos)

    def test_should_not_invent_candidacy_out_of_anything_else(self):
        """No se infiere nada más: ni por antigüedad, ni por cuántas plantillas la usan."""
        from server.app.modules.redaccion.funciones_acciones import candidata_a_nivel_3

        candidata, motivos = candidata_a_nivel_3(_funcion(), [_version()])

        assert candidata is False
        assert motivos == []

    def test_should_count_a_requested_promotion_as_candidacy(self):
        from server.app.modules.redaccion.funciones_acciones import candidata_a_nivel_3

        candidata, motivos = candidata_a_nivel_3(
            _funcion(promocion_solicitada_en="2026-09-18T00:00:00Z"), [_version()]
        )

        assert candidata is True
        assert any("promoci" in m for m in motivos)

    def test_should_refuse_a_review_result_it_does_not_know(self):
        from server.app.modules.redaccion.funciones_acciones import (
            RevisionInvalida,
            aplicar_revision,
        )

        with pytest.raises(RevisionInvalida) as fallo:
            aplicar_revision(
                _version(), resultado="aprobada", nota="", revisada_por=uuid.uuid4()
            )

        # «aprobada» no existe a propósito: aprobar no es un resultado de la revisión posterior.
        assert "aprobada" in str(fallo.value)


class TestLaMuestraAleatoria:
    """El muestreo de §8.4: existe para que revisar no exija leerlo todo."""

    def test_should_return_only_unreviewed_versions(self):
        from server.app.modules.redaccion.funciones_acciones import muestra_para_revisar

        sin_revisar = [_version(version=n) for n in range(1, 6)]
        revisadas = [
            _version(version=n, revisada_por=uuid.uuid4(), revision_resultado="conforme")
            for n in range(6, 9)
        ]

        muestra = muestra_para_revisar([*sin_revisar, *revisadas], cuantas=3)

        assert len(muestra) == 3
        assert all(v.revisada_por is None for v in muestra)

    def test_should_return_everything_it_has_when_there_is_less_than_asked(self):
        from server.app.modules.redaccion.funciones_acciones import muestra_para_revisar

        muestra = muestra_para_revisar([_version(), _version()], cuantas=10)

        assert len(muestra) == 2

    def test_should_be_a_sample_and_not_the_first_n(self):
        """Si devolviera siempre las N primeras, el muestreo sería un orden y las últimas de la
        cola no se revisarían nunca."""
        from server.app.modules.redaccion.funciones_acciones import muestra_para_revisar

        cola = [_version(version=n) for n in range(1, 31)]

        muestras = {
            tuple(v.version for v in muestra_para_revisar(cola, cuantas=5))
            for _ in range(12)
        }

        assert len(muestras) > 1


class TestLaSuspension:

    def test_should_suspend_with_a_reason_and_stop_the_execution(self):
        from server.app.modules.redaccion.funciones_acciones import suspender

        version = _version()
        quien = uuid.uuid4()

        suspender(version, motivo="lee una ruta absoluta", suspendida_por=quien)

        assert version.estado == "suspendida"
        assert version.motivo_suspension == "lee una ruta absoluta"
        assert version.suspendida_por == quien

    def test_should_refuse_to_suspend_without_a_reason(self):
        from server.app.modules.redaccion.funciones_service import FuncionIncoherente
        from server.app.modules.redaccion.funciones_acciones import suspender

        with pytest.raises(FuncionIncoherente):
            suspender(_version(), motivo="   ", suspendida_por=uuid.uuid4())

    def test_should_bring_it_back_to_registered_when_reactivated(self):
        from server.app.modules.redaccion.funciones_acciones import reactivar, suspender

        version = _version()
        suspender(version, motivo="por revisar", suspendida_por=uuid.uuid4())

        reactivar(version)

        assert version.estado == "registrada"
        # El motivo **se conserva**: es historia de por qué estuvo suspendida.
        assert version.motivo_suspension == "por revisar"


class TestLaPromocionANivel3:

    def test_should_require_a_written_valuation(self):
        """La única aprobación previa del bloque, y lleva motivo escrito: es lo que la hace
        auditable."""
        from server.app.modules.redaccion.funciones_acciones import (
            PromocionInvalida,
            promover,
        )

        with pytest.raises(PromocionInvalida) as fallo:
            promover(_funcion(), valoracion="", publicada_por=uuid.uuid4())

        assert "valoraci" in str(fallo.value).lower()

    def test_should_publish_without_touching_the_code_or_the_authorship(self):
        """Promover no muta código ni versiones, y la organización autora **se conserva** como
        atribución: la plataforma no se apropia de lo que hizo un servicio."""
        from server.app.modules.redaccion.funciones_acciones import promover

        funcion = _funcion()
        organizacion_autora = funcion.organizacion_id
        quien = uuid.uuid4()

        promover(funcion, valoracion="Útil para las cuatro organizaciones", publicada_por=quien)

        assert funcion.publicada_en is not None
        assert funcion.publicada_por == quien
        assert funcion.organizacion_id == organizacion_autora

    def test_should_refuse_to_promote_a_packaged_function(self):
        """Ya es de plataforma: promoverla no significaría nada."""
        from server.app.modules.redaccion.funciones_acciones import (
            PromocionInvalida,
            promover,
        )

        with pytest.raises(PromocionInvalida):
            promover(
                _funcion(origen="paquete", organizacion_id=None),
                valoracion="la instala quien opera",
                publicada_por=uuid.uuid4(),
            )


class TestElNivelDeUnaFuncionSinOrganizacion:
    """El defecto que destapó la pantalla del catálogo.

    Una función con `organizacion_id` nulo es de la plataforma: `consulta_de_catalogo` la sirve a
    todo el mundo y `acciones_permitidas` la trata como publicada. Pero `nivel` sólo miraba
    `publicada_en` y el origen, así que la pintaba **«Nivel 2»** — «de mi organización y sin
    publicar»— justo sobre algo que ve cualquiera.

    Y las de la migración de FUN.3 son exactamente ese caso: el script de una plantilla global no
    tiene organización, porque su plantilla no la tenía. Con cuatro en la base de desarrollo, la
    etiqueta mentía en las cuatro.

    Un nivel que dice 2 sobre algo de alcance corporativo no es un detalle de pantalla: el nivel
    **es** lo que la Instrucció usa para decidir cuánto control hace falta.
    """

    def test_should_be_level_three_when_it_belongs_to_no_organizacion(self):
        from server.app.modules.redaccion.database.models import HubFuncion

        de_la_plataforma = HubFuncion(
            nombre="Script de una plantilla global",
            descripcion="",
            organizacion_id=None,
            origen="autoservicio",
        )

        assert de_la_plataforma.nivel == 3

    def test_should_agree_with_what_the_authorization_thinks(self):
        """Los dos sitios que responden «¿es de la plataforma?» tienen que decir lo mismo.

        Si discrepan, la pantalla enseña un nivel y la lista de acciones otro, y no hay forma de
        saber cuál manda.
        """
        from server.app.modules.redaccion.database.models import HubFuncion
        from datetime import datetime, timezone

        from server.app.modules.redaccion.funciones_acciones import _publicada

        for organizacion, publicada_en in (
            (None, None),
            (uuid.uuid4(), None),
            (uuid.uuid4(), datetime.now(timezone.utc)),
        ):
            funcion = HubFuncion(
                nombre="Una", descripcion="", organizacion_id=organizacion,
                origen="autoservicio", publicada_en=publicada_en,
            )
            assert _publicada(funcion) == (funcion.nivel == 3), (
                organizacion, publicada_en, funcion.nivel
            )

    def test_should_say_level_three_in_sql_too(self):
        """Y en SQL igual: la expresión y la propiedad son el mismo hecho escrito dos veces, que
        es donde este tipo de divergencia se esconde mejor."""
        from server.app.modules.redaccion.database.models import HubFuncion

        from sqlalchemy import select

        sql = str(
            select(HubFuncion.nivel).compile(compile_kwargs={"literal_binds": True})
        )
        assert "organizacion_id IS NULL" in sql
