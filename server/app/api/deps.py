from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth import AuthenticationError, UserInfo, decode_token
from server.app.core.auth.models import UserRole
from server.app.core.auth.pat.service import PatInvalidError, PatService
from server.app.database.db import server_engine

_PAT_PREFIX = "pat_"


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining a database session."""
    async with AsyncSession(server_engine) as session:
        yield session


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_session),
) -> UserInfo:
    """Valida el credencial del header Authorization (JWT de sesión o PAT).

    Discrimina por prefijo: ``pat_…`` se valida contra la BD (PatService) y adjunta
    los scopes del token en ``request.state.pat_scopes``; cualquier otro Bearer se
    trata como JWT de sesión humana (``pat_scopes = None`` → sin filtrado por scope).
    """
    if authorization is None:
        raise _unauthorized("Missing Authorization header. Use: Bearer <token>")
    if not authorization.startswith("Bearer "):
        raise _unauthorized("Invalid authorization header. Use: Bearer <token>")

    token = authorization.removeprefix("Bearer ").strip()

    if token.startswith(_PAT_PREFIX):
        try:
            principal = await PatService(session).verify(token)
        except PatInvalidError as e:
            raise _unauthorized(str(e))
        request.state.pat_scopes = principal.scopes
        return principal.user_info

    request.state.pat_scopes = None
    try:
        return decode_token(token)
    except AuthenticationError as e:
        raise _unauthorized(str(e))


def require_role(*roles: str):
    """Dependency factory que exige uno de los roles dados."""

    async def _check(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not allowed. Required: {', '.join(roles)}",
            )
        return user

    return _check


# Gates nombrados con jerarquía superadmin > admin > user.
# `require_superadmin` solo acepta superadmin (plataforma global).
# `require_admin` acepta admin y superadmin (superadmin puede todo lo que un admin).
require_superadmin = require_role(UserRole.SUPERADMIN.value)
require_admin = require_role(UserRole.SUPERADMIN.value, UserRole.ADMIN.value)


def require_scopes(*needed: str):
    """Dependency factory que exige scopes a los principales PAT.

    Una sesión humana (JWT) no se filtra por scope (``pat_scopes`` es ``None``); un
    PAT debe portar todos los scopes requeridos o se rechaza con 403.
    """

    async def _check(
        request: Request, user: UserInfo = Depends(get_current_user)
    ) -> UserInfo:
        scopes = getattr(request.state, "pat_scopes", None)
        if scopes is None:
            return user
        missing = [s for s in needed if s not in scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PAT_SCOPE_MISSING", "missing": missing},
            )
        return user

    return _check
