"""
Deploy: cloud
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.api.deps import get_session, get_current_user
from server.app.core.auth import UserInfo, create_token
from server.app.core.auth.models import UserRole
from server.app.core.security import verify_password
from server.app.database.models import SuperAdminAccount, AdminAccount

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


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
    """Emite un JWT para un AdminAccount con email + contraseña.

    NOTA: la verificación de contraseña la añade SEC.1; aquí se mantiene el
    comportamiento previo (sin comprobar contraseña) intacto tras el renombrado.
    """
    result = await session.exec(
        select(AdminAccount).where(AdminAccount.email == body.email.lower())
    )
    admin = result.first()

    if not admin or not admin.is_active:
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


@router.get("/me", response_model=dict)
async def get_me(current_user: UserInfo = Depends(get_current_user)) -> dict:
    """Devuelve la información del usuario autenticado (validación del token)."""
    return current_user.to_dict()
