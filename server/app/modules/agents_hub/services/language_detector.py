"""Detector de idioma para mensajes."""

from langdetect import LangDetectException, detect


def detect_language(text: str, default: str = "es") -> str:
    """Detecta el idioma de un texto.

    Args:
        text: Texto a analizar
        default: Idioma por defecto si no se puede detectar

    Returns:
        Código de idioma (es, en, ca, etc.)
    """
    if len(text.strip()) < 10:
        return default

    try:
        return detect(text)
    except LangDetectException:
        return default
