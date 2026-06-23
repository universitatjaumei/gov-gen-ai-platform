"""Personal Access Tokens (PAT) para clientes máquina (AUTH.3).

Tokens revocables de larga duración con *scopes*, usados por el servidor MCP (Bloque
MCP) para llamar a la API. La emisión/gestión es cloud; la validación vive aquí
(compartida) y se enchufa en la dependencia de auth.
"""

from server.app.core.auth.pat.scopes import (
    ALL_SCOPES,
    UnknownScopeError,
    allowed_scopes_for_role,
    validate_scopes,
)
from server.app.core.auth.pat.service import (
    PatForbiddenError,
    PatInvalidError,
    PatPrincipal,
    PatService,
)

__all__ = [
    "ALL_SCOPES",
    "UnknownScopeError",
    "allowed_scopes_for_role",
    "validate_scopes",
    "PatForbiddenError",
    "PatInvalidError",
    "PatPrincipal",
    "PatService",
]
