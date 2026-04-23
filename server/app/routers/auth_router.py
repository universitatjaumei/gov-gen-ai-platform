from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.api.deps import get_session, get_current_user
from server.app.core.auth import UserInfo, create_token
from server.app.core.auth.models import UserRole
from server.app.core.security import verify_password
from server.app.database.models import AdminAccount, PartnerAccount

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token/admin", response_model=TokenResponse)
async def login_admin(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Emite un JWT para un AdminAccount con email + contraseña."""
    result = await session.exec(
        select(AdminAccount).where(AdminAccount.email == body.email.lower())
    )
    admin = result.first()

    if not admin or not admin.is_active or not verify_password(body.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = UserInfo(
        user_id=str(admin.admin_id),
        email=admin.email,
        role=UserRole.ADMIN.value,
    )
    return TokenResponse(access_token=create_token(user_info))


@router.post("/token/partner", response_model=TokenResponse)
async def login_partner(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Emite un JWT para un PartnerAccount con email + contraseña."""
    result = await session.exec(
        select(PartnerAccount).where(PartnerAccount.email == body.email.lower())
    )
    partner = result.first()

    if not partner or not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = UserInfo(
        user_id=partner.partner_id,
        email=partner.email,
        role=UserRole.PARTNER.value,
    )
    return TokenResponse(access_token=create_token(user_info))


@router.get("/me", response_model=dict)
async def get_me(current_user: UserInfo = Depends(get_current_user)) -> dict:
    """Devuelve la información del usuario autenticado (validación del token)."""
    return current_user.to_dict()
