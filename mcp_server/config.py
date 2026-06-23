"""Configuración por entorno del servidor MCP (MCP.1).

Lee la URL base de la API y el PAT desde variables de entorno. Falla con un
mensaje claro si falta cualquiera de las dos, en lugar de arrancar a medias.

Variables:
    GOVGENAI_API_BASE_URL   URL base de la API (p. ej. http://localhost:8000)
    GOVGENAI_PAT            Personal Access Token (formato pat_<prefix>_<secret>)
    GOVGENAI_GRAPH_PROFILES_PATH
                            (opcional) ruta al markdown GRAPH_PROFILES.md.
                            Por defecto <repo_root>/docs/GRAPH_PROFILES.md.
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
