"""
Deploy: cloud
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.api.deps import get_session, get_current_user
from server.app.core.auth import UserInfo, create_token
from server.app.core.auth.models import UserRole
from server.app.core.security import hash_password, verify_password
from server.app.database.models import SuperAdminAccount, AdminAccount

router = APIRouter(prefix="/auth", tags=["auth"])

# SEC.1: hash contra el que comparar cuando la cuenta no existe o no tiene contraseña, para
# que el tiempo de respuesta no delate cuáles de los correos probados son administradores.
# Se calcula una vez al importar; corresponde a una contraseña que nadie puede escribir.
_HASH_SENUELO = hash_password(uuid.uuid4().hex)


class LoginRequest(BaseModel):
    email: str
    password: str


class SetPasswordRequest(BaseModel):
    password: str = PydanticField(min_length=12)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/superadmin/login", response_model=TokenResponse)
async def login_superadmin(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Emite un JWT para un SuperAdminAccount con email + contraseña."""
    result = await session.exec(
        select(SuperAdminAccount).where(SuperAdminAccount.email == body.email.lower())
    )
    superadmin = result.first()

    if (
        not superadmin
        or not superadmin.is_active
        or not verify_password(body.password, superadmin.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = UserInfo(
        user_id=str(superadmin.admin_id),
        email=superadmin.email,
        role=UserRole.SUPERADMIN.value,
    )
    return TokenResponse(access_token=create_token(user_info))


@router.post("/admin/login", response_model=TokenResponse)
async def login_admin(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Emite un JWT para un AdminAccount con email + contraseña (SEC.1, hallazgo A1).

    Hasta SEC.1 esto emitía el token comprobando solo que el email existiera: cualquiera que
    conociera un correo de administrador entraba con la contraseña que quisiera.

    **Una cuenta sin hash no entra.** El backfill de la migración deja NULL, y NULL es «login
    local deshabilitado» —SSO, PAT, o que un superadmin le fije contraseña—, jamás «pasa sin
    comprobar».

    **El error es el mismo en los tres casos** —cuenta inexistente, sin hash y contraseña
    incorrecta— y se paga siempre el coste de un `verify_password`: distinguirlos convertiría
    el formulario de login en un oráculo para enumerar administradores, y responder antes
    cuando el email no existe lo convierte en el mismo oráculo medido con un cronómetro.
    """
    result = await session.exec(
        select(AdminAccount).where(AdminAccount.email == body.email.lower())
    )
    admin = result.first()

    hash_almacenado = getattr(admin, "hashed_password", None) if admin else None
    # Hash de descarte: sin esto, una cuenta inexistente responde sin hacer bcrypt y el
    # tiempo de respuesta delata qué correos son de administrador.
    contrasena_valida = verify_password(body.password, hash_almacenado or _HASH_SENUELO)

    if not admin or not admin.is_active or not hash_almacenado or not contrasena_valida:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = UserInfo(
        user_id=admin.partner_id,
        email=admin.email,
        role=UserRole.ADMIN.value,
    )
    return TokenResponse(access_token=create_token(user_info))


@router.patch(
    "/admins/{partner_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="setAdminPassword",
)
async def set_admin_password(
    partner_id: str,
    body: SetPasswordRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Fija o restablece la contraseña de un Admin. **Solo superadmin** (SEC.1).

    Es la contrapartida obligatoria de que el backfill deje los hashes en NULL: sin esta vía,
    las cuentas que ya existían se quedarían sin forma de entrar y el arreglo de A1 sería una
    puerta cerrada con la llave dentro.

    No lo puede hacer un admin, ni siquiera sobre su propia cuenta: cambiar la contraseña
    propia exige conocer la anterior, y ese flujo no es este prompt.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un superadministrador puede fijar la contraseña de un Admin",
        )

    admin = await session.get(AdminAccount, partner_id)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    admin.hashed_password = hash_password(body.password)
    session.add(admin)
    await session.commit()


@router.get("/me", response_model=dict)
async def get_me(current_user: UserInfo = Depends(get_current_user)) -> dict:
    """Devuelve la información del usuario autenticado (validación del token)."""
    return current_user.to_dict()
