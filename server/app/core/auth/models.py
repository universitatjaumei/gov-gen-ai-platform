"""Modelos de autenticación y usuario."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    """Roles de usuario disponibles.

    - ADMIN: gestiona la plataforma global (proveedores LLM, partners, config sistema).
    - PARTNER: crea y configura chatbots/agentes para sus clientes.
    - INFORMER: supervisa y valida respuestas de la IA.
    - USER: usuario final del chatbot/agente.
    """

    USER = "user"
    ADMIN = "admin"
    PARTNER = "partner"
    INFORMER = "informer"


def _validate_role(role: str) -> str:
    valid_roles = {r.value for r in UserRole}
    if role not in valid_roles:
        raise ValueError(
            f"Invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}"
        )
    return role


@dataclass(frozen=True)
class UserInfo:
    """Información del usuario autenticado, extraída del JWT.

    Inmutable (frozen) para garantizar que no se modifique durante el request.
    """

    user_id: str
    email: str
    role: str = field(default="user")

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _validate_role(self.role))

    def to_dict(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "email": self.email, "role": self.role}

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    @property
    def is_partner(self) -> bool:
        return self.role == UserRole.PARTNER.value

    @property
    def is_informer(self) -> bool:
        return self.role == UserRole.INFORMER.value
