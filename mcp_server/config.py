"""Configuración por entorno del servidor MCP (MCP.1).

Lee la URL base de la API y el PAT desde variables de entorno. Falla con un
mensaje claro si falta cualquiera de las dos, en lugar de arrancar a medias.

Variables:
    GOVGENAI_API_BASE_URL   URL base de la API (p. ej. http://localhost:8000)
    GOVGENAI_PAT            Personal Access Token (formato pat_<prefix>_<secret>)
    GOVGENAI_GRAPH_PROFILES_PATH
                            (opcional) ruta al markdown GRAPH_PROFILES.md.
                            Por defecto <repo_root>/docs/GRAPH_PROFILES.md.

El transporte HTTP de REG.4 lee su propia configuracion (`load_http_config`) y
**deliberadamente no admite `GOVGENAI_PAT`**: ver el docstring de `HttpConfig`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# config.py vive en <repo_root>/mcp_server/, luego el repo es el padre del paquete.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_GRAPH_PROFILES_PATH = _REPO_ROOT / "docs" / "GRAPH_PROFILES.md"


class ConfigError(RuntimeError):
    """Falta configuración obligatoria para arrancar el servidor MCP."""


@dataclass(frozen=True)
class Config:
    api_base_url: str
    pat: str
    graph_profiles_path: Path


@dataclass(frozen=True)
class HttpConfig:
    """Configuracion del transporte streamable HTTP (REG.4).

    **No tiene campo `pat`, y eso es el punto entero.** El servidor stdio lee `GOVGENAI_PAT` del
    entorno porque es mono-usuario: un proceso, una persona, un token. En un servicio remoto
    multi-cliente, un token de entorno haria que todos los que se conectaran actuaran con el
    mismo —mismos permisos, misma organizacion y mismo rastro en el registro de actividad—, y la
    trazabilidad que el bloque REG existe para dar se perderia justo en la superficie que mas la
    necesita. El token es el que presenta cada peticion.

    `allowed_hosts` es obligatorio y no tiene valor por defecto util: la proteccion contra DNS
    rebinding del SDK valida la cabecera `Host`, y detras del proxy inverso ese `Host` es el del
    dominio institucional. Si falta, el transporte responde **421 a todo** y el fallo no se
    parece en nada a su causa; asi que se exige al arrancar.
    """

    api_base_url: str
    allowed_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...] = ()


def _lista(valor: str | None) -> tuple[str, ...]:
    return tuple(parte.strip() for parte in (valor or "").split(",") if parte.strip())


def load_http_config(env: Mapping[str, str] | None = None) -> HttpConfig:
    """Construye la configuracion del transporte HTTP desde el entorno.

    Variables:
        GOVGENAI_API_BASE_URL       URL base de la API.
        GOVGENAI_MCP_ALLOWED_HOSTS  Hosts admitidos, separados por comas.
        GOVGENAI_MCP_ALLOWED_ORIGINS
                                    (opcional) origenes admitidos, separados por comas.
    """
    env = os.environ if env is None else env

    base_url = (env.get("GOVGENAI_API_BASE_URL") or "").strip()
    hosts = _lista(env.get("GOVGENAI_MCP_ALLOWED_HOSTS"))

    missing = [
        name
        for name, value in (
            ("GOVGENAI_API_BASE_URL", base_url),
            ("GOVGENAI_MCP_ALLOWED_HOSTS", hosts),
        )
        if not value
    ]
    if missing:
        raise ConfigError(
            "Faltan variables de entorno obligatorias para el MCP remoto: "
            + ", ".join(missing)
            + ". GOVGENAI_MCP_ALLOWED_HOSTS es la lista de valores admitidos de la cabecera "
            "Host (p. ej. normativa.uji.es): sin ella el transporte responde 421 a todas las "
            "peticiones. El PAT no se configura aqui: lo presenta cada cliente."
        )

    return HttpConfig(
        api_base_url=base_url,
        allowed_hosts=hosts,
        allowed_origins=_lista(env.get("GOVGENAI_MCP_ALLOWED_ORIGINS")),
    )


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Construye la configuración desde el entorno.

    Lanza ``ConfigError`` listando TODAS las variables obligatorias que falten.
    """
    env = os.environ if env is None else env

    base_url = (env.get("GOVGENAI_API_BASE_URL") or "").strip()
    pat = (env.get("GOVGENAI_PAT") or "").strip()

    missing = [
        name
        for name, value in (
            ("GOVGENAI_API_BASE_URL", base_url),
            ("GOVGENAI_PAT", pat),
        )
        if not value
    ]
    if missing:
        raise ConfigError(
            "Faltan variables de entorno obligatorias para el servidor MCP: "
            + ", ".join(missing)
            + ". Define GOVGENAI_API_BASE_URL (URL de la API) y GOVGENAI_PAT "
            "(Personal Access Token) antes de arrancar."
        )

    graph_profiles_path = Path(
        env.get("GOVGENAI_GRAPH_PROFILES_PATH") or _DEFAULT_GRAPH_PROFILES_PATH
    )

    return Config(
        api_base_url=base_url,
        pat=pat,
        graph_profiles_path=graph_profiles_path,
    )
