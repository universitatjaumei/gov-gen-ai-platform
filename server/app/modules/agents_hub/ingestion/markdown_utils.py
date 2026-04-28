"""Utilidades para extraccion de metadatos de contenido Markdown."""

import re

_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def extract_title_from_markdown(content: str) -> str | None:
    """Devuelve el primer H1 del documento, sin el #."""
    m = _H1.search(content)
    return m.group(1).strip() if m else None


def estimate_tokens(content: str) -> int:
    """Aproximacion rapida (4 chars/token). Suficiente para la heuristica del modo."""
    return max(1, len(content) // 4)
