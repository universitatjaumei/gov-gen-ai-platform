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
