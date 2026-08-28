"""Detector de idioma para mensajes.

**Devuelve el código del CORPUS, no el de `langdetect`** (ACT.2). Es el único punto donde se
produce la lengua de una pregunta, así que es donde se traduce: `langdetect` llama `ca` a lo que
el corpus llama `val`, y mientras los dos códigos convivieron **nunca coincidían**.

Ya se había tropezado con ello y la salida de entonces fue dejar de usar la lengua:
`graph_factory.py` documenta que el parámetro «se recibe y no se usa» porque «filtrar por él
dejaba la búsqueda vacía siempre». El desajuste seguía vivo en dos sitios: `prefer` metía todo en
el saco de «otra lengua» en las preguntas en valenciano, y el aviso de traducción comparaba `val`
contra `ca`, así que saltaba siempre.

Se normaliza aquí y no en el corpus porque el corpus son 60.859 fragmentos y su código lo fija
`CONTRATO_MD_CORPUS.md`; la detección es una función.
"""

from langdetect import LangDetectException, detect

#: De lo que devuelve `langdetect` a lo que dice el corpus. Explícito y no un `.replace()`:
#: quien lea esto tiene que ver que la lista de traducciones es exactamente una.
_AL_CODIGO_DEL_CORPUS = {"ca": "val"}


def detect_language(text: str, default: str = "es") -> str:
    """Detecta el idioma de un texto y lo devuelve en el código del corpus.

    Args:
        text: Texto a analizar
        default: Idioma por defecto si no se puede detectar

    Returns:
        Código de idioma del corpus (`val`, `es`, `en`...). **Nunca `ca`.**
    """
    if len(text.strip()) < 10:
        return _AL_CODIGO_DEL_CORPUS.get(default, default)

    try:
        detectado = detect(text)
    except LangDetectException:
        detectado = default
    return _AL_CODIGO_DEL_CORPUS.get(detectado, detectado)
