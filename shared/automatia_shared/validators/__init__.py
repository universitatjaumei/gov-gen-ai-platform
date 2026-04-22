"""
Pure validation functions for AutomatIA platform.
No I/O, no database access - just validation logic.
"""

import re
import hashlib
from typing import Tuple, List, Optional


def validate_license_key_format(license_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validates the format of a license key.

    Expected format: XXXXX-XXXXX-XXXXX-XXXXX (alphanumeric groups separated by dashes)

    Args:
        license_key: The license key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not license_key:
        return False, "License key cannot be empty"

    pattern = r'^[A-Z0-9]{5}(-[A-Z0-9]{5}){3}$'
    if not re.match(pattern, license_key.upper()):
        return False, "Invalid license key format. Expected: XXXXX-XXXXX-XXXXX-XXXXX"

    return True, None


def hash_license_key(license_key: str) -> str:
    """
    Creates a SHA256 hash of a license key for secure storage.

    Args:
        license_key: The plain text license key

    Returns:
        SHA256 hash of the key
    """
    return hashlib.sha256(license_key.encode()).hexdigest()


def validate_dni_format(dni: str, locale: str = "es") -> Tuple[bool, Optional[str]]:
    """
    Validates Spanish DNI/NIE format.

    Args:
        dni: The DNI/NIE to validate
        locale: Country locale (currently only 'es' supported)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if locale != "es":
        return True, None  # Skip validation for other locales

    if not dni:
        return False, "DNI cannot be empty"

    dni = dni.upper().replace(" ", "").replace("-", "")

    # DNI: 8 digits + 1 letter
    dni_pattern = r'^[0-9]{8}[A-Z]$'
    # NIE: X/Y/Z + 7 digits + 1 letter
    nie_pattern = r'^[XYZ][0-9]{7}[A-Z]$'

    if not (re.match(dni_pattern, dni) or re.match(nie_pattern, dni)):
        return False, "Invalid DNI/NIE format"

    return True, None


def validate_iban_format(iban: str) -> Tuple[bool, Optional[str]]:
    """
    Basic IBAN format validation.

    Args:
        iban: The IBAN to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not iban:
        return False, "IBAN cannot be empty"

    iban = iban.upper().replace(" ", "").replace("-", "")

    # Basic format: 2 letters + 2 digits + up to 30 alphanumeric
    pattern = r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$'
    if not re.match(pattern, iban):
        return False, "Invalid IBAN format"

    return True, None


def validate_email_format(email: str) -> Tuple[bool, Optional[str]]:
    """
    Basic email format validation.

    Args:
        email: The email to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"

    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename by removing potentially dangerous characters.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove path separators and null bytes
    sanitized = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
    # Remove other potentially dangerous characters
    sanitized = re.sub(r'[<>:"|?*]', '_', sanitized)
    # Limit length
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = name[:250] + ('.' + ext if ext else '')
    return sanitized


def validate_script_imports(imports: List[str], allowed_imports: set) -> Tuple[bool, List[str]]:
    """
    Validates that script imports are within the allowed whitelist.

    Args:
        imports: List of import names found in script
        allowed_imports: Set of allowed import names

    Returns:
        Tuple of (all_valid, list_of_violations)
    """
    violations = []
    for imp in imports:
        # Get base module name (e.g., 'pandas' from 'pandas.DataFrame')
        base_module = imp.split('.')[0]
        if base_module not in allowed_imports:
            violations.append(f"Forbidden import: {imp}")

    return len(violations) == 0, violations


__all__ = [
    "validate_license_key_format",
    "hash_license_key",
    "validate_dni_format",
    "validate_iban_format",
    "validate_email_format",
    "sanitize_filename",
    "validate_script_imports",
]
