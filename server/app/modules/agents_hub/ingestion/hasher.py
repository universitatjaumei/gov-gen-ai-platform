"""Hasher para detección de cambios en documentos."""
import hashlib
from pathlib import Path


def hash_content(content: str) -> str:
    """Genera hash SHA-256 del contenido.

    Args:
        content: Texto a hashear

    Returns:
        Hash hexadecimal de 64 caracteres
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def hash_file(file_path: Path) -> str:
    """Genera hash SHA-256 de un archivo.

    Args:
        file_path: Ruta al archivo

    Returns:
        Hash hexadecimal de 64 caracteres
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()
