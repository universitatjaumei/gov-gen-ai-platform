"""IDE.5 — el sujeto de una concesión puede ser un grupo del IdP.

`HubModuleGrant.subject_id` era siempre una persona, así que conceder módulos era insertar una
fila por cabeza. Lo que el usuario quiere para el futuro —«que el SSO se vincule a un atributo
que permita esta asignación de permisos desde el ERP de origen y no desde la aplicación»— tiene
el transporte **ya construido**: `saml_groups` viaja en el claim `groups` del JWT y el modo
`restricted` de un chatbot ya lo consume (`assert_chatbot_access`).

**El grupo entra desde el principio** (decisión del usuario, 2026-08-22): dejarlo para después
convertía el paso al modelo del ERP en una migración en vez de un cambio de pantalla.

La semántica es la que ya usa `assert_chatbot_access` —rol **o** grupo, lo que case primero— con
su trampa documentada, que aquí vale igual: **sin concesión que case no hay módulo; el vacío es
«nadie», no «todos»**.

**La comparación de grupos es insensible a mayúsculas, y es una decisión.** Los IdP no se ponen
de acuerdo, y los grupos que la UJI va a mandar son acrónimos —`PDI`, `PTGAS`— que cualquiera
teclea en minúscula al configurarlos. Se guarda lo que se escribió, para que la pantalla lo
muestre tal cual, y se compara plegado. El precio es que dos filas que solo difieran en la caja
pueden coexistir; el resolutor devuelve un conjunto, así que no conceden dos veces.
"""
from __future__ import annotations

import uuid

import pytest

MODULO = "informes"


async def _catalogo(session) -> None:
    from server.app.core.auth.modulos import MODULOS_INICIALES
    from server.app.modules.agents_hub.database.config_models import HubPlatformModule

    for codigo, etiqueta in MODULOS_INICIALES:
        session.add(HubPlatformModule(code=codigo, label=etiqueta, vigente=True))
    await session.commit()


async def _conceder(session, *, sujeto: str, tipo: str, modulo: str = MODULO) -> None:
    from server.app.modules.agents_hub.database.config_models import HubModuleGrant

    session.add(
        HubModuleGrant(
            subject_id=sujeto,
            subject_type=tipo,
            module_code=modulo,
            granted_by="test",
        )
    )
    await session.commit()


def _principal(user_id: str, *grupos: str):
    from server.app.core.auth.models import UserInfo

    return UserInfo(
        user_id=user_id, email="quien@uji.es", role="user", saml_groups=tuple(grupos)
    )


@pytest.mark.sin_guarda_de_modulos
class TestElGrupoConcedeComoLaPersona:

    @pytest.mark.asyncio
    async def test_should_grant_the_module_through_a_group(self, db_session):
        """**El test del bloque**: la persona no tiene concesión propia y obtiene el módulo."""
        from server.app.core.auth.modulos_service import modulos_del_usuario

        await _catalogo(db_session)
        await _conceder(db_session, sujeto="PDI", tipo="grupo")

        modulos = await modulos_del_usuario(db_session, _principal(str(uuid.uuid4()), "PDI"))

        assert modulos == [MODULO]

    @pytest.mark.asyncio
    async def test_should_lose_it_when_the_group_grant_is_revoked(self, db_session):
        from sqlalchemy import delete

        from server.app.core.auth.modulos_service import modulos_del_usuario
        from server.app.modules.agents_hub.database.config_models import HubModuleGrant

        await _catalogo(db_session)
        await _conceder(db_session, sujeto="PDI", tipo="grupo")
        persona = _principal(str(uuid.uuid4()), "PDI")
        assert await modulos_del_usuario(db_session, persona) == [MODULO]

        await db_session.execute(
            delete(HubModuleGrant).where(HubModuleGrant.subject_type == "grupo")
        )
        await db_session.commit()

        assert await modulos_del_usuario(db_session, persona) == []

    @pytest.mark.asyncio
    async def test_should_not_grant_through_a_group_the_person_does_not_have(self, db_session):
        from server.app.core.auth.modulos_service import modulos_del_usuario

        await _catalogo(db_session)
        await _conceder(db_session, sujeto="PTGAS", tipo="grupo")

        modulos = await modulos_del_usuario(db_session, _principal(str(uuid.uuid4()), "PDI"))

        assert modulos == []

    @pytest.mark.asyncio
    async def test_should_not_duplicate_a_module_granted_by_both_ways(self, db_session):
        from server.app.core.auth.modulos_service import modulos_del_usuario
        from server.app.routers.redaccion._actor import user_to_uuid

        await _catalogo(db_session)
        user_id = str(uuid.uuid4())
        await _conceder(db_session, sujeto=str(user_to_uuid(user_id)), tipo="usuario")
        await _conceder(db_session, sujeto="PDI", tipo="grupo")

        modulos = await modulos_del_usuario(db_session, _principal(user_id, "PDI"))

        assert modulos == [MODULO]

    @pytest.mark.asyncio
    async def test_should_compare_groups_ignoring_case(self, db_session):
        """Los grupos de la UJI son acrónimos —`PDI`, `PTGAS`— y quien los configure los va a
        teclear como le salga. Decidido y dicho: se compara plegado."""
        from server.app.core.auth.modulos_service import modulos_del_usuario

        await _catalogo(db_session)
        await _conceder(db_session, sujeto="pdi", tipo="grupo")

        modulos = await modulos_del_usuario(db_session, _principal(str(uuid.uuid4()), "PDI"))

        assert modulos == [MODULO]

    @pytest.mark.asyncio
    async def test_should_still_be_fail_closed_without_any_grant(self, db_session):
        """La regla de INF.7 no se relaja: sin fila que case, no hay módulo."""
        from server.app.core.auth.modulos_service import modulos_del_usuario

        await _catalogo(db_session)

        assert await modulos_del_usuario(db_session, _principal(str(uuid.uuid4()), "PDI")) == []

    @pytest.mark.asyncio
    async def test_should_ignore_a_group_grant_for_a_retired_module(self, db_session):
        from sqlalchemy import select

        from server.app.core.auth.modulos_service import modulos_del_usuario
        from server.app.modules.agents_hub.database.config_models import HubPlatformModule

        await _catalogo(db_session)
        await _conceder(db_session, sujeto="PDI", tipo="grupo")
        modulo = (
            await db_session.execute(
                select(HubPlatformModule).where(HubPlatformModule.code == MODULO)
            )
        ).scalar_one()
        modulo.vigente = False
        await db_session.commit()

        assert await modulos_del_usuario(db_session, _principal(str(uuid.uuid4()), "PDI")) == []

    @pytest.mark.asyncio
    async def test_should_keep_person_grants_working_after_the_change(self, db_session):
        """La compatibilidad que importa: las concesiones que ya existen siguen concediendo."""
        from server.app.core.auth.modulos_service import modulos_del_usuario
        from server.app.routers.redaccion._actor import user_to_uuid

        await _catalogo(db_session)
        user_id = str(uuid.uuid4())
        await _conceder(db_session, sujeto=str(user_to_uuid(user_id)), tipo="usuario")

        assert await modulos_del_usuario(db_session, _principal(user_id)) == [MODULO]

    @pytest.mark.asyncio
    async def test_should_not_let_a_group_named_like_a_person_cross_over(self, db_session):
        """El tipo es parte de la clave: una concesión de grupo cuyo `subject_id` coincida con
        el UUID de una persona **no** le concede nada por la vía de persona, y al revés."""
        from server.app.core.auth.modulos_service import modulos_del_usuario
        from server.app.routers.redaccion._actor import user_to_uuid

        await _catalogo(db_session)
        user_id = str(uuid.uuid4())
        sujeto = str(user_to_uuid(user_id))
        await _conceder(db_session, sujeto=sujeto, tipo="grupo")

        # La persona no declara ese grupo, así que no le toca nada.
        assert await modulos_del_usuario(db_session, _principal(user_id)) == []

    @pytest.mark.asyncio
    async def test_should_store_a_group_name_longer_than_a_uuid(self, db_session):
        """`subject_id` era `String(36)`, dimensionado para un UUID. Un nombre de grupo de un
        IdP institucional no cabe ahí de forma fiable."""
        from sqlalchemy import select

        from server.app.core.auth.modulos_service import modulos_del_usuario
        from server.app.modules.agents_hub.database.config_models import HubModuleGrant

        largo = "uji-personal-docente-e-investigador-departamento-de-derecho-publico"
        assert len(largo) > 36

        await _catalogo(db_session)
        await _conceder(db_session, sujeto=largo, tipo="grupo")

        guardado = (
            await db_session.execute(
                select(HubModuleGrant.subject_id).where(HubModuleGrant.subject_type == "grupo")
            )
        ).scalar_one()
        assert guardado == largo
        assert await modulos_del_usuario(db_session, _principal(str(uuid.uuid4()), largo)) == [
            MODULO
        ]


@pytest.mark.sin_guarda_de_modulos
class TestElOrigenDeCadaModuloSeVe:

    @pytest.mark.asyncio
    async def test_should_say_which_grant_gave_each_module(self, db_session):
        """Un permiso cuyo origen no se ve es un permiso que nadie se atreve a retirar."""
        from server.app.core.auth.modulos_service import modulos_con_origen
        from server.app.routers.redaccion._actor import user_to_uuid

        await _catalogo(db_session)
        user_id = str(uuid.uuid4())
        await _conceder(db_session, sujeto=str(user_to_uuid(user_id)), tipo="usuario")
        await _conceder(db_session, sujeto="PDI", tipo="grupo", modulo="chatbots")

        origen = await modulos_con_origen(db_session, _principal(user_id, "PDI"))

        # MT.5 — el origen dice también **dónde** vale, y estas concesiones no nombran
        # organización: valen en todas, que es lo que significan las de siempre.
        assert origen["informes"] == [
            {"tipo": "usuario", "sujeto": str(user_to_uuid(user_id)), "organizacion": ""}
        ]
        assert origen["chatbots"] == [
            {"tipo": "grupo", "sujeto": "PDI", "organizacion": ""}
        ]

    @pytest.mark.asyncio
    async def test_should_list_both_origins_when_a_module_comes_twice(self, db_session):
        from server.app.core.auth.modulos_service import modulos_con_origen
        from server.app.routers.redaccion._actor import user_to_uuid

        await _catalogo(db_session)
        user_id = str(uuid.uuid4())
        await _conceder(db_session, sujeto=str(user_to_uuid(user_id)), tipo="usuario")
        await _conceder(db_session, sujeto="PDI", tipo="grupo")

        origen = await modulos_con_origen(db_session, _principal(user_id, "PDI"))

        tipos = {o["tipo"] for o in origen[MODULO]}
        assert tipos == {"usuario", "grupo"}

    @pytest.mark.asyncio
    async def test_should_give_a_superadmin_every_module_without_a_grant(self, db_session):
        """El superadministrador entra en todo sin concesión: una instalación nueva se
        quedaría con él encerrado fuera. Y su origen tiene que decir eso, no inventar una fila."""
        from server.app.core.auth.models import UserInfo
        from server.app.core.auth.modulos_service import modulos_con_origen

        await _catalogo(db_session)
        root = UserInfo(user_id="1", email="root@uji.es", role="superadmin")

        origen = await modulos_con_origen(db_session, root)

        assert set(origen) == {"chatbots", "curacion", "informes", "plataforma"}
        # MT.5 — mismo campo que las demás filas, vacío: el superadministrador vale en todas.
        assert all(
            o == [{"tipo": "rol", "sujeto": "superadmin", "organizacion": ""}]
            for o in origen.values()
        )
