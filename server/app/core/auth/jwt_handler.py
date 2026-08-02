"""Manejador de tokens JWT."""

from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidSignatureError

from server.app.core.auth.exceptions import AuthenticationError
from server.app.core.auth.models import UserInfo
from server.app.core.config import get_settings


def create_token(user: UserInfo, expires_in_minutes: int | None = None) -> str:
    """Crea un token JWT firmado para el usuario."""
    settings = get_settings()

    if expires_in_minutes is None:
        expires_in_minutes = settings.jwt_expiration_minutes

    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)

    payload = {
        "sub": user.user_id,
        "email": user.email,
        "role": user.role,
        # SEC.2: sin este claim el servidor no sabe de quien es el que pregunta, y por
        # eso los endpoints no filtraban. Se emite en TODAS las vias: login local, ACS
        # de SAML y PAT, porque una sola que lo omita reabre el acceso horizontal.
        "orgs": list(user.organizacion_ids),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> UserInfo:
    """Decodifica y valida un token JWT. Lanza AuthenticationError si es inválido."""
    settings = get_settings()

    if not token or not isinstance(token, str):
        raise AuthenticationError("Invalid token format")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except InvalidSignatureError:
        raise AuthenticationError("Invalid token signature")
    except DecodeError:
        raise AuthenticationError("Invalid token format")
    except Exception as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")

    missing = [c for c in ("sub", "email") if c not in payload]
    if missing:
        raise AuthenticationError(
            f"Token missing required claims: {', '.join(missing)}"
        )

    return UserInfo(
        user_id=payload["sub"],
        email=payload["email"],
        role=payload.get("role", "user"),
        # Un token emitido antes de SEC.2 no trae el claim. Se lee como SIN acceso, no
        # como acceso total: lo contrario convertiria un token viejo en una llave maestra.
        organizacion_ids=tuple(payload.get("orgs") or ()),
    )
