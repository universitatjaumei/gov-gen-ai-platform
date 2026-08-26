"""Validacion post-generacion: garantiza que la respuesta cite cuando debe."""

import re
import unicodedata

_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# Un corchete que NO va seguido de parentesis: la forma en la que el modelo cita cuando se
# deja la URL. Se excluye el salto de linea para no tragarse dos citas de parrafos distintos.
_CORCHETE_SIN_ENLACE = re.compile(r"\[([^\]\n]+)\](?!\()")

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


def _normalizar(texto: str) -> str:
    """Minusculas, sin tildes y con los espacios colapsados, para comparar titulos.

    El corpus escribe «creditos» sin tilde y «máster» con ella en el mismo titulo, asi que
    comparar en crudo fallaria por como se transcribio el original, que no es lo que se
    quiere medir.
    """
    sin_tildes = (
        unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def enlazar_citas_en_prosa(response_text: str, sources: list) -> str:
    """Pone la URL a las citas que nombran bien una norma recuperada pero no la enlazan.

    HIB.0. Medido con la sonda el 2026-08-26 sobre SGE-01: el modelo respondio correcto y con
    detalle y cito asi —«[Reglamento sobre reconocimiento y transferencia de creditos...,
    ANEXO II, apartado 3]»—, corchetes sin URL. No es un enlace markdown, el contrato no
    encontraba ninguna cita valida y **tiraba la respuesta entera**. RES.5 previo esta forma y
    aplazo el enlazado determinista porque midio cero casos en 85 respuestas; ese cero caduco.

    **Esto no amplia lo citable, que es la garantia del contrato.** El titulo se busca
    unicamente entre los documentos RECUPERADOS: una norma que el texto menciona pero que no
    se entrego al modelo no se enlaza aqui ni en ningun sitio. Y el enlace lo escribe el
    codigo desde `source_url`, no el modelo: no hay puntero que se pueda inventar.

    El detalle que va detras del titulo —«ANEXO II, apartado 3»— se conserva dentro del texto
    del enlace: es informacion que el lector necesita y que el ancla del documento no da.
    """
    candidatos = [
        (_normalizar(titulo), url)
        for titulo, url in (
            (getattr(s, "title", None), _url_de(s)) for s in sources
        )
        if titulo and url
    ]
    if not candidatos:
        return response_text
    # El mas especifico primero: dos normas cuyo titulo empieza igual —«Reglament de
    # permanencia» y «Reglament de permanencia per als estudis de grau i master»— se
    # resolverian a la corta si se mirara en el orden de llegada.
    candidatos.sort(key=lambda c: len(c[0]), reverse=True)

    def _reemplazo(coincidencia: re.Match) -> str:
        dentro = coincidencia.group(1)
        normalizado = _normalizar(dentro)
        for titulo, url in candidatos:
            if normalizado.startswith(titulo):
                return f"[{dentro}]({url})"
        return coincidencia.group(0)

    return _CORCHETE_SIN_ENLACE.sub(_reemplazo, response_text)


def despojar_remisiones(response_text: str, allowed: set[str]) -> str:
    """Deja en texto plano las referencias que apuntan fuera del conjunto recuperado.

    HIB.0. La regla, tal como la fijó el usuario el 2026-08-26: la respuesta cita la norma
    principal y, en su caso, las otras normas recuperadas y utilizadas para redactarla, pero
    **no las normas citadas por esas normas**.

    Con `parent_child` el fragmento inyectado es el artículo entero, que trae dentro sus
    remisiones —«conforme al artículo 118 de la Ley 9/2017»—. El modelo las enlaza, y ese
    enlace apunta a un texto que **no se le ha entregado**: lo que dijera sobre él saldría de
    su memoria, no del fundamento. La mención se conserva porque es información legítima y
    útil; lo que se va es el puntero, que es lo que no podemos respaldar.
    """

    def _reemplazo(coincidencia: re.Match) -> str:
        titulo, url = coincidencia.group(1), coincidencia.group(2).strip()
        return coincidencia.group(0) if url in allowed else titulo

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

    # HIB.0: el orden de estos dos pasos es el contrato.
    #
    # 1. DEGRADAR primero: una cita al documento correcto con un ancla que no es la
    #    recuperada baja al documento y **sobrevive**. Si se despojara antes, esa cita —que
    #    es fundamento legitimo— se convertiria en texto plano y la respuesta se quedaria
    #    sin apoyo por un ancla mal compuesta.
    # 2. DESPOJAR despues: lo que sigue apuntando fuera del conjunto recuperado pierde el
    #    enlace, no la mencion.
    #
    # Y la comprobacion va LA ULTIMA, sobre el texto ya despojado: al reves, una remision
    # enlazada contaria como cita valida y el contrato dejaria de proteger justo de lo que
    # existe para proteger.
    texto = degradar_anclas(response_text, anclas)
    texto = enlazar_citas_en_prosa(texto, sources)
    texto = despojar_remisiones(texto, allowed)
    if has_valid_citations(texto, allowed):
        return texto

    # UX.4: el mensaje es del chatbot. Esta rama lo ignoraba y devolvia el texto fijo, en
    # castellano, a preguntas hechas en valenciano.
    return no_answer_message or NO_CITATION_FALLBACK
