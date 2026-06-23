"""Derivación del rol del sistema a partir de los atributos SAML (AUTH.2)."""

import json

from server.app.core.auth.models import UserRole
from server.app.core.config import get_settings

# Precedencia de mayor a menor privilegio.
_ROLE_PRECEDENCE = (
    UserRole.ADMIN.value,
    UserRole.PARTNER.value,
    UserRole.INFORMER.value,
    UserRole.USER.value,
)
_VALID_ROLES = {r.value for r in UserRole}


def _parse_group_role_map() -> dict[str, str]:
    raw = get_settings().saml_group_role_map
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if v in _VALID_ROLES}


def _highest(roles: list[str]) -> str | None:
    for role in _ROLE_PRECEDENCE:
        if role in roles:
            return role
    return None


def resolve_role(attributes: dict) -> str:
    """Resuelve el rol del sistema a partir de los atributos de la aserción.

    Orden: (1) atributo de rol explícito válido; (2) mapeo de grupo→rol con precedencia
    por privilegio; (3) rol por defecto.
    """
    settings = get_settings()

    explicit = attributes.get(settings.saml_attr_role) or []
    for value in explicit:
        if value in _VALID_ROLES:
            return value

    group_map = _parse_group_role_map()
    if group_map:
        groups = attributes.get(settings.saml_attr_groups) or []
        mapped = [group_map[g] for g in groups if g in group_map]
        best = _highest(mapped)
        if best:
            return best

    return settings.saml_default_role
