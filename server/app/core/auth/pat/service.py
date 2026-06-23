"""Emisión, validación y revocación de Personal Access Tokens (AUTH.3)."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from server.app.core.auth.models import UserInfo
from server.app.core.auth.pat.scopes import (
    allowed_scopes_for_role,
    validate_scopes,
)
from server.app.modules.agents_hub.database.config_models import (
    HubPersonalAccessToken,
)

_TOKEN_NS = "pat"
_PREFIX_BYTES = 4  # → 8 hex chars
_SECRET_BYTES = 32


class PatForbiddenError(Exception):
    """El rol no puede emitir el PAT o los scopes exceden su techo."""


class PatInvalidError(Exception):
    """El token es inválido, está revocado o ha expirado."""


@dataclass(frozen=True)
class PatPrincipal:
    """Resultado de validar un PAT: identidad + scopes del token."""

    user_info: UserInfo
    scopes: list[str]


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_prefix(token: str) -> str | None:
    parts = token.split("_", 2)
    if len(parts) != 3 or parts[0] != _TOKEN_NS or not parts[1]:
        return None
    return parts[1]


class PatService:
    """Gestiona el ciclo de vida de los PAT."""

    def __init__(self, session) -> None:
        self.session = session

    async def create(
        self,
        owner: UserInfo,
        name: str,
        scopes: list[str],
        expires_at: datetime | None = None,
    ) -> tuple[HubPersonalAccessToken, str]:
        """Crea un PAT y devuelve (fila, token_plano). El plano se ve UNA vez."""
        validate_scopes(scopes)

        allowed = allowed_scopes_for_role(owner.role)
        if not allowed:
            raise PatForbiddenError(
                f"Role '{owner.role}' is not allowed to issue access tokens"
            )
        if not set(scopes).issubset(allowed):
            raise PatForbiddenError(
                f"Role '{owner.role}' cannot grant scopes outside its ceiling: "
                f"{', '.join(sorted(set(scopes) - allowed))}"
            )

        prefix = secrets.token_hex(_PREFIX_BYTES)
        secret = secrets.token_urlsafe(_SECRET_BYTES)
        token = f"{_TOKEN_NS}_{prefix}_{secret}"

        pat = HubPersonalAccessToken(
            owner_id=owner.user_id,
            owner_email=owner.email,
            owner_role=owner.role,
            name=name,
            token_prefix=prefix,
            token_hash=_hash_token(token),
            scopes=list(scopes),
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        self.session.add(pat)
        await self.session.commit()
        await self.session.refresh(pat)
        return pat, token

    async def verify(self, token: str) -> PatPrincipal:
        """Valida un token y devuelve el principal; actualiza last_used_at."""
        prefix = _parse_prefix(token)
        if prefix is None:
            raise PatInvalidError("Malformed access token")

        rows = (
            await self.session.execute(
                select(HubPersonalAccessToken).where(
                    HubPersonalAccessToken.token_prefix == prefix
                )
            )
        ).scalars().all()

        token_hash = _hash_token(token)
        pat = next(
            (r for r in rows if hmac.compare_digest(r.token_hash, token_hash)),
            None,
        )
        if pat is None:
            raise PatInvalidError("Unknown access token")
        if pat.revoked_at is not None:
            raise PatInvalidError("Access token has been revoked")
        if pat.expires_at is not None and pat.expires_at <= datetime.now(timezone.utc):
            raise PatInvalidError("Access token has expired")

        # Capturar los valores ANTES del commit: expire_on_commit los invalidaría y un
        # acceso posterior dispararía un lazy-load síncrono (MissingGreenlet).
        principal = PatPrincipal(
            user_info=UserInfo(
                user_id=pat.owner_id, email=pat.owner_email, role=pat.owner_role
            ),
            scopes=list(pat.scopes),
        )
        pat.last_used_at = datetime.now(timezone.utc)
        await self.session.commit()
        return principal

    async def list_for(self, owner: UserInfo) -> list[HubPersonalAccessToken]:
        """Lista los PAT del owner (metadatos; nunca el plano ni el hash)."""
        return list(
            (
                await self.session.execute(
                    select(HubPersonalAccessToken)
                    .where(HubPersonalAccessToken.owner_id == owner.user_id)
                    .order_by(HubPersonalAccessToken.created_at.desc())
                )
            ).scalars().all()
        )

    async def revoke(self, owner: UserInfo, pat_id) -> None:
        """Revoca un PAT del owner. Lanza ``PatInvalidError`` si no es suyo."""
        pat = (
            await self.session.execute(
                select(HubPersonalAccessToken).where(
                    HubPersonalAccessToken.id == pat_id,
                    HubPersonalAccessToken.owner_id == owner.user_id,
                )
            )
        ).scalars().first()
        if pat is None:
            raise PatInvalidError("Access token not found")
        if pat.revoked_at is None:
            pat.revoked_at = datetime.now(timezone.utc)
            await self.session.commit()
