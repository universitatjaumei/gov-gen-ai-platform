"""
Pure utility functions for AutomatIA platform.
No I/O, no database access - just stateless transformations.
"""

import json
import hashlib
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


def generate_code_hash(code: str) -> str:
    """
    Generates a SHA256 hash of code for integrity verification.

    Args:
        code: The code string to hash

    Returns:
        SHA256 hash string
    """
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def normalize_whitespace(text: str) -> str:
    """
    Normalizes whitespace in text (replaces multiple spaces/newlines with single space).

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    return ' '.join(text.split())


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string, returning default on failure.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely serialize object to JSON string.

    Args:
        obj: Object to serialize
        default: Default string if serialization fails

    Returns:
        JSON string or default
    """
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncates text to max_length, adding suffix if truncated.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extrae un objeto JSON de un texto que puede contener bloques de código markdown.

    Busca patrones de bloques ```json ... ```, ``` ... ``` o simplemente llaves { ... }.
    Es útil para procesar respuestas de LLMs.

    Args:
        text (str): Texto que potencialmente contiene una cadena JSON.

    Returns:
        Optional[Dict[str, Any]]: Diccionario parseado si se encuentra JSON válido,
            None en caso contrario.
    """
    # Try to find JSON in code blocks
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*\}'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            json_str = match.group(1) if match.lastindex else match.group(0)
            result = safe_json_loads(json_str.strip())
            if result is not None:
                return result

    return None


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Aplana un diccionario anidado.

    Convierte un diccionario con niveles en un diccionario de un solo nivel
    usando un separador para las claves anidadas.

    Args:
        d (Dict[str, Any]): Diccionario a aplanar.
        parent_key (str): Prefijo para las claves (usado en recursión).
        sep (str): Separador entre claves anidadas (por defecto '.').

    Returns:
        Dict[str, Any]: Diccionario aplanado.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def estimate_tokens(text: str) -> int:
    """
    Estimates the number of tokens in text.
    Approximate rule: 1 token ~ 4 characters.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


def format_currency(amount: float, currency: str = "EUR", locale: str = "es") -> str:
    """
    Formats a number as currency string.

    Args:
        amount: Numeric amount
        currency: Currency code
        locale: Locale for formatting

    Returns:
        Formatted currency string
    """
    if locale == "es":
        # Spanish format: 1.234,56 €
        formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} {currency}"
    else:
        # Default format: €1,234.56
        return f"{currency}{amount:,.2f}"


def parse_iso_datetime(date_str: str) -> Optional[datetime]:
    """
    Parses ISO format datetime string.

    Args:
        date_str: ISO datetime string

    Returns:
        datetime object or None
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


__all__ = [
    "generate_code_hash",
    "normalize_whitespace",
    "safe_json_loads",
    "safe_json_dumps",
    "truncate_text",
    "extract_json_from_text",
    "flatten_dict",
    "estimate_tokens",
    "format_currency",
    "parse_iso_datetime",
]
