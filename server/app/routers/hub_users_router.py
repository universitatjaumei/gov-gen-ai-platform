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
from server.app.modules.agents_hub.database.config_models import HubUser
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


def _a_lectura(fila: HubUser) -> UsuarioRead:
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
    )


# ============================================
# Endpoints
# ============================================


@router.get("", response_model=list[UsuarioRead])
async def list_users(
    _: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> list[UsuarioRead]:
    """Quién existe en esta plataforma.

    **No lista las otras tres tablas de identidad** (`SuperAdminAccount`, `AdminAccount`,
    `ClientAccount`), que siguen sin unificar. La pantalla de IDE.4 lo dice, para que nadie lea
    el listado como «todas las cuentas».
    """
    filas = (
        await session.execute(select(HubUser).order_by(HubUser.email))
    ).scalars().all()
    return [_a_lectura(f) for f in filas]


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
    """Cambia rol, nombre, organización o actividad. **Desactivar es la baja**: no hay borrado.

    Una persona que ya entró tiene rastro en interacciones, informes y concesiones; borrarla
    dejaría ese rastro sin dueño. `is_active = false` cierra la puerta, que es lo que se quiere.
    """
    fila = await session.get(HubUser, user_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    cambios = body.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(fila, campo, valor)

    await session.commit()
    await session.refresh(fila)
    return _a_lectura(fila)
