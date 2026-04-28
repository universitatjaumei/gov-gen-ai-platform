"""Validacion post-generacion: garantiza que la respuesta cite cuando debe."""

import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

NO_CITATION_FALLBACK = (
    "No tengo informacion suficiente en los documentos disponibles para responder a "
    "esta pregunta con citas verificables. Podrias reformular o proporcionar mas contexto?"
)


def has_valid_citations(response_text: str, allowed_urls: set[str]) -> bool:
    """True si la respuesta contiene al menos una cita cuyo URL este en allowed_urls."""
    for _title, url in _MD_LINK.findall(response_text):
        if url.strip() in allowed_urls:
            return True
    return False


def enforce_citation_contract(
    response_text: str,
    sources: list,
    mode: str,
) -> str:
    """Si hubo sources y la respuesta no cita ninguno valido, devuelve el fallback.

    En modo agentic, se relaja: el agente puede decidir no leer ningun documento
    (saludo, charla); validamos solo si sources no esta vacio.
    """
    if not sources:
        return response_text
    allowed = {s.url for s in sources}
    if has_valid_citations(response_text, allowed):
        return response_text
    return NO_CITATION_FALLBACK
