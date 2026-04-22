"""
Hardware Fingerprint Generator for Device Identification.

Generates a unique and stable identifier for the client machine
to enable multi-seat license validation (PROMPT 8H).
"""
import uuid
import hashlib
import platform
import socket
from typing import Optional

# Cache del fingerprint para evitar recalcular
_cached_fingerprint: Optional[str] = None


def _generate_fingerprint() -> str:
    """
    Genera un identificador único basado en hardware del sistema.

    Combina múltiples fuentes para crear un hash estable:
    - MAC address (uuid.getnode)
    - Hostname
    - Plataforma del sistema

    Returns:
        str: Hash hexadecimal de 64 caracteres (SHA256)
    """
    # 1. MAC Address (más estable, basado en hardware de red)
    mac = uuid.getnode()

    # 2. Hostname (puede cambiar, pero añade unicidad)
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"

    # 3. Información de plataforma
    system_info = f"{platform.system()}-{platform.machine()}"

    # Combinar elementos
    raw_fingerprint = f"{mac}|{hostname}|{system_info}"

    # Generar hash SHA256 (estable y único)
    fingerprint_hash = hashlib.sha256(raw_fingerprint.encode('utf-8')).hexdigest()

    return fingerprint_hash


def get_machine_fingerprint() -> str:
    """
    Obtiene el identificador único de la máquina.

    El fingerprint es:
    - Único por máquina (basado en hardware)
    - Estable entre ejecuciones
    - Formato hexadecimal de 64 caracteres

    Returns:
        str: Identificador único de la máquina

    Example:
        >>> fp = get_machine_fingerprint()
        >>> len(fp)
        64
        >>> fp == get_machine_fingerprint()  # Estable
        True
    """
    global _cached_fingerprint

    if _cached_fingerprint is None:
        _cached_fingerprint = _generate_fingerprint()

    return _cached_fingerprint


def get_device_name() -> str:
    """
    Obtiene un nombre descriptivo para el dispositivo.

    Returns:
        str: Nombre del host o 'Unknown Device'
    """
    try:
        return socket.gethostname()
    except Exception:
        return "Unknown Device"


def clear_fingerprint_cache():
    """
    Limpia el cache del fingerprint.
    Útil para testing.
    """
    global _cached_fingerprint
    _cached_fingerprint = None
