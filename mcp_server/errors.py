"""Errores del cliente HTTP del servidor MCP (MCP.1).

Cada respuesta de error del backend se traduce a una excepción legible. Las tools
y resources NUNCA silencian estos errores: el SDK MCP los reporta al cliente
(Claude Code), que es quien aprueba/reacciona. El cuerpo de la respuesta se
preserva en ``detail`` para que el mensaje al usuario sea accionable.
"""
from __future__ import annotations

from typing import Any


class ApiError(RuntimeError):
    """Error genérico al llamar a la API de Gov Gen AI Platform."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        detail: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - trivial
        base = super().__str__()
        if self.detail is not None:
            return f"{base} (detail={self.detail!r})"
        return base


class AuthError(ApiError):
    """401 — el PAT es inválido, está revocado o ha expirado."""


class ScopeError(ApiError):
    """403 — el PAT no porta el scope necesario para la operación."""


class ValidationError(ApiError):
    """422 — el cuerpo enviado no valida; ``detail`` lleva el error del servidor."""


class ServerError(ApiError):
    """5xx — fallo del servidor remoto."""
