"""PLAT.1 — la concesión de `plataforma` llega hasta lo que decide.

La migración inserta filas; lo que importa es que `modulos_del_usuario` las devuelva, porque es
esa lista la que alimenta el menú del panel y la guarda `require_module` del backend. Una
concesión que la resolución no ve es una fila decorativa.

Se prueba aparte de la migración a propósito: la migración se verifica sobre una base recreada
con `alembic` (`tests/infra/test_plat1_concesion_de_plataforma.py`), y esto se verifica sobre el
esquema del ORM, que es donde vive la resolución.
"""
from __future__ import annotations

import uuid

import pytest


async def _catalogo_completo(session) -> None:
    """El catálogo, que en la BD de plantilla se crea vacío (`create_all`, sin semillas)."""
    from server.app.modules.agents_hub.database.config_models import HubPlatformModule
    from server.app.core.auth.modulos import MODULOS_INICIALES

    for codigo, etiqueta in MODULOS_INICIALES:
        session.add(HubPlatformModule(code=codigo, label=etiqueta, vigente=True))
    await session.commit()


async def _conceder(session, sujeto: uuid.UUID, *codigos: str) -> None:
    from server.app.modules.agents_hub.database.config_models import HubModuleGrant

    for codigo in codigos:
        session.add(
            HubModuleGrant(
                subject_id=str(sujeto),
                module_code=codigo,
                granted_by="migracion:plat1",
            )
        )
    await session.commit()


def _principal(user_id: str):
    from server.app.core.auth.models import UserInfo

    return UserInfo(user_id=user_id, email="admin@test.com", role="admin")


# El conftest raíz sustituye `modulos_del_usuario` por un doble que concede todo, para que
# los tests que no van de permisos no mueran en la guarda. Aquí se prueba justamente esa
# función, así que hace falta la de verdad: es lo que marca `sin_guarda_de_modulos`.
@pytest.mark.sin_guarda_de_modulos
class TestLaConcesionLlegaALaResolucion:

    @pytest.mark.asyncio
    async def test_should_return_plataforma_once_it_is_granted(self, db_session):
        from server.app.core.auth.modulos_service import modulos_del_usuario

        await _catalogo_completo(db_session)
        sujeto = uuid.uuid4()
        await _conceder(db_session, sujeto, "chatbots", "plataforma")

        modulos = await modulos_del_usuario(db_session, _principal(str(sujeto)))

        assert modulos == ["chatbots", "plataforma"]

    @pytest.mark.asyncio
    async def test_should_not_invent_plataforma_for_someone_without_the_grant(self, db_session):
        """La regla de INF.7: sin fila no hay acceso. El relleno de PLAT.1 no la relaja."""
        from server.app.core.auth.modulos_service import modulos_del_usuario

        await _catalogo_completo(db_session)
        sujeto = uuid.uuid4()
        await _conceder(db_session, sujeto, "informes")

        modulos = await modulos_del_usuario(db_session, _principal(str(sujeto)))

        assert modulos == ["informes"]

    @pytest.mark.asyncio
    async def test_should_ignore_the_grant_if_the_module_is_retired(self, db_session):
        """Si alguien retira `plataforma` del catálogo, la fila deja de conceder: es el
        histórico de quién tuvo acceso, no un permiso vivo."""
        from server.app.core.auth.modulos_service import modulos_del_usuario
        from server.app.modules.agents_hub.database.config_models import HubPlatformModule
        from sqlalchemy import select

        await _catalogo_completo(db_session)
        sujeto = uuid.uuid4()
        await _conceder(db_session, sujeto, "chatbots", "plataforma")

        modulo = (
            await db_session.execute(
                select(HubPlatformModule).where(HubPlatformModule.code == "plataforma")
            )
        ).scalar_one()
        modulo.vigente = False
        await db_session.commit()

        modulos = await modulos_del_usuario(db_session, _principal(str(sujeto)))

        assert modulos == ["chatbots"]
