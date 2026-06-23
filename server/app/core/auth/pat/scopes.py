"""Catálogo de scopes de PAT y techo de scopes por rol (AUTH.3)."""

from server.app.core.auth.models import UserRole

# Scopes de recurso que un PAT puede portar.
REDACCION_TEMPLATES_READ = "redaccion:templates:read"
REDACCION_TEMPLATES_WRITE = "redaccion:templates:write"
CHATBOTS_READ = "chatbots:read"
CHATBOTS_WRITE = "chatbots:write"
CHAT_TEST = "chat:test"

ALL_SCOPES: frozenset[str] = frozenset(
    {
        REDACCION_TEMPLATES_READ,
        REDACCION_TEMPLATES_WRITE,
        CHATBOTS_READ,
        CHATBOTS_WRITE,
        CHAT_TEST,
    }
)

# Techo de scopes que cada rol puede EMITIR en un PAT (los demás roles no pueden
# emitir PAT). Un partner queda excluido de `chatbots:write` vía token máquina: la
# mutación in-place de un chatbot en producción es el riesgo dominante (ver
# docs/mcp.md, valoración 2), así que se reserva a admin; el partner sigue
# configurando chatbots de forma interactiva (sesión JWT, no acotada por scopes).
_ROLE_SCOPES: dict[str, frozenset[str]] = {
    UserRole.ADMIN.value: ALL_SCOPES,
    UserRole.PARTNER.value: ALL_SCOPES - {CHATBOTS_WRITE},
}


class UnknownScopeError(ValueError):
    """Se solicitó un scope que no existe en el catálogo."""


def validate_scopes(scopes: list[str]) -> None:
    """Lanza ``UnknownScopeError`` si algún scope no pertenece al catálogo."""
    unknown = [s for s in scopes if s not in ALL_SCOPES]
    if unknown:
        raise UnknownScopeError(f"Unknown scopes: {', '.join(sorted(unknown))}")


def allowed_scopes_for_role(role: str) -> frozenset[str]:
    """Scopes que un rol puede emitir en un PAT (vacío si el rol no puede emitir)."""
    return _ROLE_SCOPES.get(role, frozenset())
