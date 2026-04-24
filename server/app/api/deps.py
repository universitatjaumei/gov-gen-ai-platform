from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.database.db import server_engine
from server.app.core.auth import AuthenticationError, UserInfo, decode_token


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining a database session."""
    async with AsyncSession(server_engine) as session:
        yield session


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> UserInfo:
    """Valida el JWT del header Authorization y devuelve el UserInfo."""
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        return decode_token(token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


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
