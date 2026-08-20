"""Qué módulos tiene concedidos quien pregunta (INF.7).

Deploy: cloud

El servidor decide y el cliente itera: el menú y las rutas del frontend se generan desde esta
lista, no de un `role ===` escrito en React. Es la misma regla que `acciones_permitidas` en los
bloques y en expedientes.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.core.auth.modulos import ROL_CON_ACCESO_TOTAL
from server.app.modules.agents_hub.database.config_models import (
    HubModuleGrant as ModuleGrant,
    HubPlatformModule as PlatformModule,
)
from server.app.routers.redaccion._actor import user_to_uuid


async def modulos_del_usuario(session: AsyncSession, user: UserInfo) -> list[str]:
    """Los códigos de módulo que este usuario puede usar, en orden estable.

    El superadmin entra en todos los módulos vigentes **sin concesión explícita**: es el rol de
    la plataforma, y hacerlo depender de una fila deja una instalación recién creada con un
    superadmin encerrado fuera de todo —`bootstrap` crea la cuenta, no sus permisos—. Para
    cualquier otro rol, sin fila no hay acceso.

    Un módulo retirado del catálogo (`vigente = false`) no se concede a nadie aunque la fila de
    la concesión siga ahí: la fila es el histórico de quién tuvo acceso, no un permiso vivo.
    """
    vigentes = set(
        (await session.execute(
            select(PlatformModule.code).where(PlatformModule.vigente.is_(True))
        )).scalars().all()
    )

    if user.role == ROL_CON_ACCESO_TOTAL:
        return sorted(vigentes)

    concedidos = set(
        (await session.execute(
            select(ModuleGrant.module_code).where(
                ModuleGrant.subject_id == str(user_to_uuid(user.user_id))
            )
        )).scalars().all()
    )
    return sorted(concedidos & vigentes)


async def tiene_modulo(session: AsyncSession, user: UserInfo, codigo: str) -> bool:
    return codigo in await modulos_del_usuario(session, user)
