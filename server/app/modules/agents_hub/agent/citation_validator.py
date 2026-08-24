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


def _url_de(evidencia) -> str | None:
    """URL de un EvidenceItem (`source_url`).

    RAG.2 unificó el contrato de evidencia en EvidenceItem; se acepta también `url`
    porque los tools de lectura y las estrategias de `services/retrieval/` siguen
    hablando ese dialecto por debajo de los pipelines.
    """
    return getattr(evidencia, "source_url", None) or getattr(evidencia, "url", None)


def _sin_fragmento(url: str) -> str:
    return url.split("#", 1)[0]


def degradar_anclas(response_text: str, allowed: set[str]) -> str:
    """Reescribe al documento las citas cuyo ancla no es la admitida.

    Medido el 2026-08-24: dos de cada ocho descartes citaban el documento correcto con otra
    ancla —`#art-1.7.a` cuando el fragmento venia anclado en `#art-1`, y `#Primer` cuando el
    fragmento no traia ancla—. Tirar la respuesta entera por eso no protege de nada: el
    documento SI se recupero y SI se leyo.

    Degradar al documento pierde precision y no veracidad: el lector aterriza en la portada
    de la norma en vez de en el articulo. Componer un ancla que nadie leyo, en cambio, seria
    fabricar un puntero, y eso es justo lo que este modulo existe para impedir.
    """
    documentos = {_sin_fragmento(u) for u in allowed}

    def _reemplazo(coincidencia: re.Match) -> str:
        titulo, url = coincidencia.group(1), coincidencia.group(2).strip()
        if url in allowed:
            return coincidencia.group(0)
        documento = _sin_fragmento(url)
        if documento in documentos:
            return f"[{titulo}]({documento})"
        return coincidencia.group(0)

    return _MD_LINK.sub(_reemplazo, response_text)


def enforce_citation_contract(
    response_text: str,
    sources: list,
    mode: str,
    no_answer_message: str | None = None,
) -> str:
    """Si hubo sources y la respuesta no cita ninguno valido, devuelve el fallback.

    Antes de darla por invalida se intenta **degradar**: una cita al documento correcto con
    un ancla equivocada se reescribe al documento. Sin ese paso el contrato dejaba de
    proteger y empezaba a destruir — nueve de veinticinco respuestas descartadas, ocho de
    ellas con la mejor recuperacion de la tanda.

    Lo que sigue atrapando, que es para lo que existe: citar un documento que nunca se
    recupero, y no citar nada.

    En modo agentic, se relaja: el agente puede decidir no leer ningun documento
    (saludo, charla); validamos solo si sources no esta vacio.
    """
    if not sources:
        return response_text
    anclas = {u for u in (_url_de(s) for s in sources) if u}
    # La URL de la norma es citable por derecho propio: es el «o la norma» del criterio
    # «el articulo si se puede, la norma si no». Sin esto, degradar produciria una URL que
    # el propio contrato rechazaria.
    allowed = anclas | {_sin_fragmento(u) for u in anclas}
    if has_valid_citations(response_text, allowed):
        return response_text

    degradada = degradar_anclas(response_text, anclas)
    if degradada != response_text and has_valid_citations(degradada, allowed):
        return degradada

    # UX.4: el mensaje es del chatbot. Esta rama lo ignoraba y devolvia el texto fijo, en
    # castellano, a preguntas hechas en valenciano.
    return no_answer_message or NO_CITATION_FALLBACK
