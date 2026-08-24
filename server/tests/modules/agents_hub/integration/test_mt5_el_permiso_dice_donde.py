"""MT.5 — el permiso dice dónde.

Una concesión dice «informes», no «informes en el ayuntamiento de X». Con una organización da
igual; con veinte, conceder un módulo a un grupo del IdP se lo concede **en todas**, y en el
modelo Diputación→municipios eso es dar acceso a los informes de veinte ayuntamientos a la vez.
Lo mismo con los tokens: `hub_personal_access_tokens` va por dueño y no dice sobre qué
organización puede actuar.

**Lo que ya existe y hay que respetar**: `subject_type` distingue `usuario` de `grupo` desde
IDE.5, y ese eje no se toca. MT.5 añade otro perpendicular —en qué organización vale—, no
sustituye ninguno.

**Y una regla que es la mitad del prompt: nulo sigue significando «en todas».** Las concesiones
de hoy no nombran organización, y eso es exactamente lo que significan ahora. Reinterpretarlas en
silencio como «en ninguna» sería quitarle los permisos a todo el mundo en una migración; como «en
la primera» sería inventárselo. Nulo = en todas, y quien quiera acotar lo dice.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from server.app.core.auth.models import UserInfo
from server.app.core.auth.modulos_service import modulos_con_origen, modulos_del_usuario
from server.app.modules.agents_hub.database.config_models import (
    HubModuleGrant,
    HubOrganizacion,
    HubPersonalAccessToken,
    HubPlatformModule,
)
from server.app.routers.redaccion._actor import user_to_uuid

pytestmark = pytest.mark.asyncio


async def _organizacion(session, nombre="Onda") -> HubOrganizacion:
    fila = HubOrganizacion(
        name=f"{nombre} {uuid.uuid4().hex[:6]}", partner_id=f"p-{uuid.uuid4().hex[:6]}"
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _modulo(session, codigo: str) -> HubPlatformModule:
    fila = await session.get(HubPlatformModule, codigo)
    if fila is None:
        fila = HubPlatformModule(code=codigo, label=codigo.title(), vigente=True)
        session.add(fila)
        await session.commit()
    return fila


def _persona(organizacion_ids=()) -> UserInfo:
    return UserInfo(
        user_id=f"u-{uuid.uuid4().hex[:8]}",
        email="tecnico@ayuntamiento.es",
        role="user",
        organizacion_ids=tuple(str(o) for o in organizacion_ids),
    )


async def _conceder(session, user, codigo, *, organizacion=None) -> HubModuleGrant:
    fila = HubModuleGrant(
        subject_id=str(user_to_uuid(user.user_id)),
        subject_type="usuario",
        module_code=codigo,
        organizacion_id=organizacion.id if organizacion is not None else None,
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


class TestUnaConcesionPuedeDecirDonde:

    async def test_should_grant_a_module_only_in_one_organisation(self, db_session):
        una = await _organizacion(db_session, "Onda")
        otra = await _organizacion(db_session, "Nules")
        await _modulo(db_session, "informes")
        quien = _persona([una.id, otra.id])
        await _conceder(db_session, quien, "informes", organizacion=una)

        en_una = await modulos_del_usuario(db_session, quien, organizacion_id=una.id)
        en_otra = await modulos_del_usuario(db_session, quien, organizacion_id=otra.id)

        assert "informes" in en_una
        assert "informes" not in en_otra, (
            "una concesión acotada a Onda no puede dar acceso en Nules"
        )

    async def test_should_keep_a_null_organisation_meaning_everywhere(self, db_session):
        """**La mitad del prompt.** Las concesiones de hoy no nombran organización, y eso es lo
        que significan: en todas. Reinterpretarlas en silencio le cambiaría los permisos a todo
        el mundo en una migración, sin decírselo a nadie."""
        una = await _organizacion(db_session, "Vila-real")
        otra = await _organizacion(db_session, "Borriana")
        await _modulo(db_session, "informes")
        quien = _persona([una.id, otra.id])
        await _conceder(db_session, quien, "informes", organizacion=None)

        assert "informes" in await modulos_del_usuario(
            db_session, quien, organizacion_id=una.id
        )
        assert "informes" in await modulos_del_usuario(
            db_session, quien, organizacion_id=otra.id
        )

    async def test_should_keep_answering_without_an_organisation_at_all(self, db_session):
        """Preguntar «qué módulos tiene» sin nombrar organización sigue valiendo, y responde
        todo lo que tiene en cualquiera. Es lo que hace que MT.5 no cambie comportamiento: los
        sitios que aún no saben la organización preguntan como siempre."""
        una = await _organizacion(db_session)
        await _modulo(db_session, "informes")
        quien = _persona([una.id])
        await _conceder(db_session, quien, "informes", organizacion=una)

        assert "informes" in await modulos_del_usuario(db_session, quien)

    async def test_should_let_the_same_person_have_different_modules_per_organisation(
        self, db_session
    ):
        """El caso que justifica el eje: alguien que trabaja para dos ayuntamientos y no hace lo
        mismo en los dos."""
        una = await _organizacion(db_session, "Onda")
        otra = await _organizacion(db_session, "Nules")
        await _modulo(db_session, "informes")
        await _modulo(db_session, "curacion")
        quien = _persona([una.id, otra.id])
        await _conceder(db_session, quien, "informes", organizacion=una)
        await _conceder(db_session, quien, "curacion", organizacion=otra)

        assert await modulos_del_usuario(db_session, quien, organizacion_id=una.id) == [
            "informes"
        ]
        assert await modulos_del_usuario(db_session, quien, organizacion_id=otra.id) == [
            "curacion"
        ]

    async def test_should_say_the_scope_in_the_origin(self, db_session):
        """El origen ya decía **de dónde** viene un permiso (IDE.5), porque un permiso cuyo
        origen no se ve es un permiso que nadie se atreve a retirar. Con dos ejes tiene que
        decir también **dónde** vale, o «informes por ser PDI» seguiría sin poder retirarse
        sabiendo a quién afecta."""
        una = await _organizacion(db_session, "Alcora")
        await _modulo(db_session, "informes")
        quien = _persona([una.id])
        await _conceder(db_session, quien, "informes", organizacion=una)

        origen = await modulos_con_origen(db_session, quien, organizacion_id=una.id)

        assert origen["informes"][0]["organizacion"] == str(una.id)

    async def test_should_not_let_two_grants_collide_across_organisations(self, db_session):
        """La unicidad tenía tres columnas y ahora tiene cuatro: la misma persona con el mismo
        módulo en dos organizaciones son **dos** concesiones legítimas, y con la clave antigua
        la segunda habría chocado."""
        una = await _organizacion(db_session, "Onda")
        otra = await _organizacion(db_session, "Nules")
        await _modulo(db_session, "informes")
        quien = _persona([una.id, otra.id])

        await _conceder(db_session, quien, "informes", organizacion=una)
        await _conceder(db_session, quien, "informes", organizacion=otra)

    async def test_should_still_refuse_a_true_duplicate(self, db_session):
        """Lo que la clave protegía sigue protegido, **y en el nivel nulo también**: en Postgres
        `NULL != NULL`, así que sin `NULLS NOT DISTINCT` dos concesiones «en todas» idénticas
        pasarían — y ése es el nivel de todas las filas de hoy."""
        from sqlalchemy.exc import IntegrityError

        await _modulo(db_session, "informes")
        quien = _persona()
        await _conceder(db_session, quien, "informes", organizacion=None)

        with pytest.raises(IntegrityError):
            await _conceder(db_session, quien, "informes", organizacion=None)
        await db_session.rollback()


class TestElSuperadministradorNoCambia:

    async def test_should_keep_giving_a_superadmin_every_module(self, db_session):
        """Sin concesión explícita y en cualquier organización: es el rol de la plataforma, y
        hacerlo depender de una fila deja una instalación recién creada con el superadmin
        encerrado fuera. No se toca."""
        una = await _organizacion(db_session)
        await _modulo(db_session, "informes")
        root = UserInfo(
            user_id="root", email="root@uji.es", role="superadmin", organizacion_ids=()
        )

        assert "informes" in await modulos_del_usuario(
            db_session, root, organizacion_id=una.id
        )


class TestUnTokenDiceSobreQueActua:

    async def test_should_scope_a_token_to_an_organisation(self, db_session):
        una = await _organizacion(db_session)
        token = HubPersonalAccessToken(
            owner_id="u-1",
            owner_email="maquina@uji.es",
            owner_role="admin",
            name="Integración del ERP",
            token_prefix="ggp_abcd",
            token_hash="x" * 64,
            scopes=["chat:completions"],
            organizacion_id=una.id,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)

        assert token.organizacion_id == una.id

    async def test_should_refuse_a_token_acting_outside_its_organisation(self, db_session):
        """**El test que importa**, y va contra el resolvedor real y no contra el DTO: un token
        acotado a un ayuntamiento no puede operar sobre otro. Un token es una credencial de
        máquina que vive meses en un fichero de configuración; si su alcance no se comprueba
        donde se usa, el campo es decorativo."""
        from server.app.core.auth.pat.principal import acota_a_la_organizacion

        una = await _organizacion(db_session, "Onda")
        otra = await _organizacion(db_session, "Nules")
        token = HubPersonalAccessToken(
            owner_id="u-1",
            owner_email="maquina@uji.es",
            owner_role="admin",
            name="ERP de Onda",
            token_prefix="ggp_efgh",
            token_hash="y" * 64,
            scopes=["chat:completions"],
            organizacion_id=una.id,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)

        principal = acota_a_la_organizacion(
            UserInfo(
                user_id="u-1",
                email="maquina@uji.es",
                role="admin",
                organizacion_ids=(str(una.id), str(otra.id)),
            ),
            token,
        )

        # El token acota: aunque su dueño gestione las dos, el token sólo alcanza la suya.
        assert principal.organizacion_ids == (str(una.id),)

    async def test_should_leave_an_unscoped_token_as_wide_as_its_owner(self, db_session):
        """Un token sin organización sigue valiendo donde valga su dueño, que es lo que
        significan los que ya existen. Acotarlos en la migración sería romper integraciones que
        funcionan sin avisar a nadie."""
        from server.app.core.auth.pat.principal import acota_a_la_organizacion

        una = await _organizacion(db_session)
        token = HubPersonalAccessToken(
            owner_id="u-1",
            owner_email="maquina@uji.es",
            owner_role="admin",
            name="El de siempre",
            token_prefix="ggp_ijkl",
            token_hash="z" * 64,
            scopes=[],
            organizacion_id=None,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(token)
        await db_session.commit()

        dueno = UserInfo(
            user_id="u-1", email="maquina@uji.es", role="admin",
            organizacion_ids=(str(una.id),),
        )

        assert acota_a_la_organizacion(dueno, token).organizacion_ids == (str(una.id),)
