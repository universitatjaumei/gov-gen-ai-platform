"""Las personas de la plataforma: alta manual, edición y desactivación (IDE.3).

Deploy: cloud
Módulo: plataforma

Hasta aquí una persona solo existía si entraba por SSO, y entraba con el rol que resolviera la
aserción —por defecto `user`—. Promocionar a alguien exigía un `UPDATE` a mano en Postgres, que
es lo que no se le puede pedir a otra administración que despliegue esto: quien administra no
tiene por qué tener acceso a la base de datos, y no debería tenerlo.

**El alta no crea una credencial.** Crea la identidad y sus permisos; quien entra, entra por
SSO. Por eso `UsuarioCreate` **rechaza** un campo de contraseña en vez de ignorarlo: aceptado en
silencio haría creer que se guardó algo que no existe.

**El correo es la clave del reencuentro con el IdP**, así que se normaliza —sin espacios, en
minúsculas— al guardar y al buscar, y **no se puede editar**. Cambiarlo desde el panel
desengancharía a la persona de su identidad sin que se note hasta que intente entrar.

**Reservado a superadministrador.** Un admin que pudiera crear personas con rol podría crearse
un admin. Es la misma razón por la que `create_theme` reserva el tema de plataforma.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo, UserRole
from server.app.modules.agents_hub.database.config_models import HubModuleGrant, HubUser
from server.app.modules.agents_hub.database.connection import get_async_session

router = APIRouter(prefix="/hub/users", tags=["hub-users"])

_require_superadmin = require_role(UserRole.SUPERADMIN.value)

_ROLES = tuple(r.value for r in UserRole)


def normalizar_correo(correo: str) -> str:
    """La forma canónica de un correo, para guardarlo y para buscarlo.

    Vive aquí y la usa también el ACS de SAML: si las dos formas de normalizar se separan,
    `Fabra@UJI.es` dado de alta a mano y `fabra@uji.es` que llega del IdP dejan de ser la misma
    persona, y el alta manual se convierte en una fila muerta que nadie relaciona con nadie.
    """
    return correo.strip().lower()


# ============================================
# Contrato
# ============================================


class UsuarioRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    organizacion_id: uuid.UUID | None
    is_active: bool
    origen: str
    created_at: datetime
    created_by: str | None
    last_login_at: datetime | None
    # Si esta fila se puede borrar, y por qué no. Lo decide el servidor (REV.8): el frontend no
    # calcula qué acciones están permitidas.
    puede_borrarse: bool = False
    motivo_no_borrable: str | None = None


class UsuarioCreate(BaseModel):
    """`extra="forbid"` a propósito: es lo que convierte «no hay contraseña» en un error
    legible en vez de un campo que se traga y se pierde."""

    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = None
    role: str = UserRole.USER.value
    organizacion_id: uuid.UUID | None = None
    is_active: bool = True

    model_config = {"extra": "forbid"}

    @field_validator("email")
    @classmethod
    def _correo_normalizado(cls, valor: str) -> str:
        limpio = normalizar_correo(valor)
        if "@" not in limpio:
            raise ValueError("el correo tiene que llevar @")
        return limpio

    @field_validator("role")
    @classmethod
    def _rol_conocido(cls, valor: str) -> str:
        if valor not in _ROLES:
            raise ValueError(f"rol desconocido. Admitidos: {', '.join(_ROLES)}")
        return valor


class UsuarioUpdate(BaseModel):
    """Sin `email`: es la clave del reencuentro con el IdP y cambiarlo desengancha a la
    persona de su identidad. `extra="forbid"` lo convierte en un 422 y no en un cambio
    silenciosamente ignorado."""

    display_name: str | None = None
    role: str | None = None
    organizacion_id: uuid.UUID | None = None
    is_active: bool | None = None

    model_config = {"extra": "forbid"}

    @field_validator("role")
    @classmethod
    def _rol_conocido(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in _ROLES:
            raise ValueError(f"rol desconocido. Admitidos: {', '.join(_ROLES)}")
        return valor


#: `origen` de las filas que vienen de `superadminaccount` y no de `hub_users` (REV.8).
ORIGEN_SUPERADMIN_DE_ARRANQUE = "superadmin"

MOTIVO_YA_ENTRO = (
    "Esta persona ya ha entrado, así que tiene rastro en interacciones, informes y "
    "revisiones. Desactívala en su lugar: borrarla dejaría ese rastro sin dueño."
)
MOTIVO_OTRA_TABLA = (
    "Es la cuenta de superadministración creada al instalar y vive en otra tabla; se "
    "gestiona desde el servidor, no desde esta pantalla."
)
MOTIVO_ULTIMO_SUPERADMIN = (
    "Es el único superadministrador activo que queda. Sin él nadie podría administrar la "
    "plataforma, y no habría forma de arreglarlo desde la propia aplicación."
)


def _a_lectura(fila: HubUser, *, motivo_no_borrable: str | None = None) -> UsuarioRead:
    """El DTO de una persona, **con si se puede borrar y por qué no**.

    Lo decide el servidor y no la pantalla: es la regla de `AGENTS.md` —el frontend no calcula
    qué acciones están permitidas—. Si el React hiciera «si `last_login_at` es nulo, enseña el
    botón», esa regla viviría en dos sitios y un día dirían cosas distintas.
    """
    motivo = motivo_no_borrable or (MOTIVO_YA_ENTRO if fila.last_login_at else None)
    return UsuarioRead(
        id=fila.id,
        email=fila.email,
        display_name=fila.display_name,
        role=fila.role,
        organizacion_id=fila.organizacion_id,
        is_active=fila.is_active,
        origen=fila.origen,
        created_at=fila.created_at,
        created_by=fila.created_by,
        last_login_at=fila.last_login_at,
        puede_borrarse=motivo is None,
        motivo_no_borrable=motivo,
    )


async def _superadmins_de_arranque(session: AsyncSession) -> list[UsuarioRead]:
    """Las cuentas de `superadminaccount`, en solo lectura (REV.8).

    El listado leía sólo `hub_users`, así que **el superadministrador principal no aparecía en
    ninguna parte**: es la única cuenta real de una instalación recién creada y desde el panel
    no había forma de saber que existía.

    Se muestran, no se unifican: son cuatro tablas de identidad sin unificar y juntarlas es una
    migración de otro tamaño (IDE.2 hizo una parte). Van marcadas con su propio `origen` y sin
    poder borrarse, porque enseñarlas como una fila más haría creer que se editan desde aquí.

    El identificador es un uuid5 derivado del correo —`admin_id` es un entero y el contrato
    declara UUID—, el mismo normalizador que usan las concesiones por la misma razón.
    """
    from server.app.database.models import SuperAdminAccount
    from server.app.routers.redaccion._actor import user_to_uuid

    filas = (
        await session.execute(select(SuperAdminAccount).order_by(SuperAdminAccount.email))
    ).scalars().all()
    return [
        UsuarioRead(
            id=user_to_uuid(cuenta.email),
            email=cuenta.email,
            display_name=cuenta.name,
            role=UserRole.SUPERADMIN.value,
            organizacion_id=None,
            is_active=cuenta.is_active,
            origen=ORIGEN_SUPERADMIN_DE_ARRANQUE,
            created_at=cuenta.created_at,
            created_by=None,
            last_login_at=None,
            puede_borrarse=False,
            motivo_no_borrable=MOTIVO_OTRA_TABLA,
        )
        for cuenta in filas
    ]


async def _otro_superadmin_activo(session: AsyncSession, excluido: uuid.UUID) -> bool:
    """Si queda algún superadministrador activo **aparte** del que se va a tocar.

    Cuenta las dos tablas: si sólo mirara `hub_users`, la cuenta de arranque no valdría y la
    regla bloquearía una desactivación perfectamente segura.
    """
    from server.app.database.models import SuperAdminAccount

    otros = (
        await session.execute(
            select(HubUser).where(
                HubUser.role == UserRole.SUPERADMIN.value,
                HubUser.is_active.is_(True),
                HubUser.id != excluido,
            )
        )
    ).scalars().first()
    if otros is not None:
        return True

    de_arranque = (
        await session.execute(
            select(SuperAdminAccount).where(SuperAdminAccount.is_active.is_(True))
        )
    ).scalars().first()
    return de_arranque is not None


# ============================================
# Endpoints
# ============================================


@router.get("", response_model=list[UsuarioRead])
async def list_users(
    _: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> list[UsuarioRead]:
    """Quién existe en esta plataforma.

    **REV.8 — incluye las cuentas de `superadminaccount`**, en solo lectura. Antes el listado
    leía sólo `hub_users` y el superadministrador principal no aparecía en ninguna parte, que es
    la única cuenta real de una instalación recién creada.

    Siguen sin listarse `AdminAccount` y `ClientAccount`, que tampoco están unificadas. La
    pantalla lo dice, para que nadie lea el listado como «todas las cuentas».
    """
    filas = (
        await session.execute(select(HubUser).order_by(HubUser.email))
    ).scalars().all()
    personas = [_a_lectura(f) for f in filas]
    return await _superadmins_de_arranque(session) + personas


@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UsuarioCreate,
    user: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> UsuarioRead:
    """Da de alta a una persona con su rol, **antes** de que entre por primera vez.

    Ese es el punto: cuando entre, el ACS encuentra esta fila por correo en vez de crear una
    nueva con el rol por defecto. Con `IDENTITY_ROLE_AUTHORITY=app` (IDE.1) el rol que se pone
    aquí sobrevive a todos los inicios de sesión posteriores.
    """
    existente = (
        await session.execute(select(HubUser).where(HubUser.email == body.email))
    ).scalars().first()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya hay una persona con el correo {body.email}",
        )

    fila = HubUser(
        id=uuid.uuid4(),
        email=body.email,
        display_name=body.display_name,
        role=body.role,
        organizacion_id=body.organizacion_id,
        is_active=body.is_active,
        origen="manual",
        created_by=user.user_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return _a_lectura(fila)


@router.patch("/{user_id}", response_model=UsuarioRead)
async def update_user(
    user_id: uuid.UUID,
    body: UsuarioUpdate,
    _: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> UsuarioRead:
    """Cambia rol, nombre, organización o actividad. **Desactivar es la baja** para quien ya usó
    la plataforma; a quien nunca entró se le puede borrar (ver `delete_user`).

    Una persona que ya entró tiene rastro en interacciones, informes y concesiones; borrarla
    dejaría ese rastro sin dueño. `is_active = false` cierra la puerta, que es lo que se quiere.

    **REV.8 — y no se puede dejar la plataforma sin superadministración**: desactivar al último
    que queda activo la deja sin nadie que administre y sin forma de arreglarlo desde la propia
    aplicación. Se comprueba también al cambiar el rol, porque bajar de rol al único que hay
    llega al mismo sitio por otra puerta.
    """
    fila = await session.get(HubUser, user_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    cambios = body.model_dump(exclude_unset=True)

    deja_de_administrar = fila.role == UserRole.SUPERADMIN.value and (
        cambios.get("is_active") is False
        or (cambios.get("role") is not None and cambios["role"] != UserRole.SUPERADMIN.value)
    )
    if deja_de_administrar and not await _otro_superadmin_activo(session, fila.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=MOTIVO_ULTIMO_SUPERADMIN
        )

    for campo, valor in cambios.items():
        setattr(fila, campo, valor)

    await session.commit()
    await session.refresh(fila)
    return _a_lectura(fila)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    _: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Borra a una persona **que nunca ha entrado** (REV.8).

    IDE.4 decidió «desactivar, nunca borrar», y el razonamiento era bueno: quien ya entró tiene
    rastro en interacciones, informes y concesiones. Pero era absoluto de más — una fila creada
    a mano que nadie ha usado no tiene rastro de nada, y no había forma de quitarla, así que un
    correo mal escrito se quedaba en el listado para siempre.

    La regla es `last_login_at IS NULL`, que es exactamente «se creó a mano y no se ha usado»: si
    nunca entró, no pudo generar una interacción, un informe ni una revisión.

    **Sus concesiones se van con ella**, en la misma transacción: una concesión a alguien que ya
    no existe es una fila que ninguna pantalla enseña y que se queda ahí para siempre.
    """
    fila = await session.get(HubUser, user_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    if fila.last_login_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MOTIVO_YA_ENTRO)

    # El mismo agujero que vigila el `PATCH`, por la otra puerta.
    if fila.role == UserRole.SUPERADMIN.value and not await _otro_superadmin_activo(
        session, fila.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=MOTIVO_ULTIMO_SUPERADMIN
        )

    concesiones = (
        await session.execute(
            select(HubModuleGrant).where(
                HubModuleGrant.subject_type == "usuario",
                HubModuleGrant.subject_id == str(fila.id),
            )
        )
    ).scalars().all()
    for concesion in concesiones:
        await session.delete(concesion)

    await session.delete(fila)
    await session.commit()
