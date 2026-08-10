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


async def get_current_user_optional(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_session),
) -> UserInfo | None:
    """Como `get_current_user`, pero devuelve `None` en vez de 401 si no hay credencial.

    SEC.8.5: los endpoints que consume el widget público admiten dos vías —sesión o
    credencial de sitio—, y con `get_current_user` la petición moría en un 401 antes de
    poder mirar la segunda. Es justamente por eso que un chatbot `public_anon` era
    inalcanzable sin token, y por lo que el widget acababa embebiendo uno privilegiado.

    **Un Authorization presente pero inválido sigue siendo 401**: sin eso, un token
    caducado degradaría a anónimo en silencio y la petición seguiría adelante como si
    nadie hubiera intentado identificarse.
    """
    if authorization is None:
        request.state.pat_scopes = None
        return None
    return await get_current_user(request, authorization, session)


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


def require_scopes_allowing_widget(*needed: str):
    """Como `require_scopes`, pero no exige credencial (SEC.8.5).

    El endpoint de chat admite dos vías: sesión/PAT, o credencial de sitio del widget. Con
    `require_scopes` a nivel de ruta la petición del widget moría en un 401 antes de que
    nadie mirara la cabecera de la credencial.

    **No relaja el filtro de scopes**: si viene un PAT, sus scopes se exigen igual. Lo que
    cambia es que la ausencia de credencial no es un rechazo aquí — quien decide si eso
    vale es el endpoint, que resuelve la credencial de sitio y aplica
    `assert_chatbot_access`, y este solo abre chatbots `public_anon`.
    """

    async def _check(
        request: Request, user: UserInfo | None = Depends(get_current_user_optional)
    ) -> UserInfo | None:
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
