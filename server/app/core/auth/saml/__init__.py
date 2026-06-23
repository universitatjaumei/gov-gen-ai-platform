"""Service Provider SAML 2.0 (AUTH.1).

Construye la configuración de python3-saml a partir de variables de entorno y adapta
el ``Request`` de FastAPI al formato que espera la librería OneLogin.
"""

from server.app.core.auth.saml.settings import (
    InvalidSamlConfigError,
    build_saml_settings,
)
from server.app.core.auth.saml.request_adapter import prepare_saml_request

__all__ = [
    "InvalidSamlConfigError",
    "build_saml_settings",
    "prepare_saml_request",
]
