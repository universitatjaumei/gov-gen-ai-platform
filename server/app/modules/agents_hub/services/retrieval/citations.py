"""Construcción de la URL de cita (ING.0.4). Deploy: edge.

El corpus trae ancla estable por unidad citable (`docs/CONTRATO_MD_CORPUS.md`), y el
chunker la deja en `chunk_metadata['ancora']`. Aquí se convierte en el fragmento de la
URL, que es lo que hace la cita verificable: el usuario abre exactamente el artículo del
que sale la respuesta, no el documento de 40 páginas.
"""
from __future__ import annotations


def with_anchor(url: str | None, metadata: dict | None) -> str | None:
    """Añade el fragmento del ancla a la URL, si el fragmento existe.

    Sustituye un fragmento previo en lugar de acumularlo: la URL canónica del documento
    puede traer uno y el del fragmento recuperado es el que manda.
    """
    if not url:
        return url
    ancora = (metadata or {}).get("ancora")
    if not ancora:
        return url
    return f"{url.split('#', 1)[0]}#{ancora}"


# ─────────────────── Autoridad del fragmento (FAQ.2) ───────────────────
#
# Una respuesta de preguntas frecuentes **no es una norma**. Si se cita con la misma forma que
# un artículo, se publica una respuesta no revisada con la autoridad de la normativa, y eso no
# se ve leyendo la respuesta.
#
# `content_class` ya distingue `regulation | faq | generic` desde el contrato del corpus; esto
# es lo que la convierte en algo visible para quien pregunta.

ORIENTATIVA = "orientativa"

_AVISO = (
    "[Respuesta orientativa de preguntas frecuentes: no es el texto de la norma. "
    "Cítala como tal y remite a la norma que la sostiene si la hay.]"
)


def etiqueta_de_autoridad(metadata: dict | None) -> str | None:
    """`"orientativa"` si el fragmento sale de una FAQ; `None` en cualquier otro caso.

    Devuelve `None` y no `"normativa"` a propósito: lo que hay que marcar es la excepción.
    Etiquetar también las normas obligaría a que todo el corpus antiguo declarara su clase
    para no parecer sospechoso, cuando el default (`generic`) no dice nada malo de él.
    """
    if (metadata or {}).get("content_class") == "faq":
        return ORIENTATIVA
    return None


def marcar_autoridad(texto: str, metadata: dict | None) -> str:
    """Antepone el aviso al fragmento cuando viene de una FAQ.

    Va en el texto que ve el **modelo**, no solo en el JSON: si el aviso solo viajara en la
    carga útil, la respuesta redactada podría presentar la sugerencia como si fuera la norma
    y el frontend pintaría una etiqueta que contradice lo que se lee.

    Es la misma razón por la que la nota de vigencia del §8.13 del contrato va DENTRO del
    cuerpo del artículo y no en la cabecera del documento: lo que no viaja con el fragmento
    no llega al que responde.
    """
    if etiqueta_de_autoridad(metadata) is None:
        return texto
    return f"{_AVISO}\n{texto}"
