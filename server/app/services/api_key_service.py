"""
Servicio de gestión de claves de API (Lado Servidor).

En producción, las claves de API se gestionan exclusivamente en el servidor
mediante variables de entorno. Los clientes nunca tienen acceso directo a
los secretos de los proveedores de LLM.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")


async def get_api_key(provider: str) -> Optional[str]:
    """
    Recupera una clave de API desde las variables de entorno del servidor.

    Args:
        provider: Nombre del proveedor ('google', 'openrouter', 'openai').

    Returns:
        Optional[str]: La clave de API encontrada o None.
    """
    env_mapping = {
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    env_var = env_mapping.get(provider.lower())
    if env_var:
        return os.environ.get(env_var)
    return None


def get_api_key_sync(provider: str) -> Optional[str]:
    """
    Synchronous version of get_api_key for use in non-async contexts.
    """
    env_mapping = {
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    env_var = env_mapping.get(provider.lower())
    if env_var:
        return os.environ.get(env_var)
    return None
