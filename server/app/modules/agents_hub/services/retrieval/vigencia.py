"""Advertencia de vigencia no validada (VIS.3). Deploy: edge.

El riesgo nº1 del corpus, medido en `INFORME_MATERIES_I_METADADES_AGENTS.md`: **312 de 314
fichas declaran «vigent?»**. Citar una de ellas sin decirlo es afirmar como vigente algo que
nadie ha comprobado.

Por qué el aviso no vive en el system prompt: una instruccion al modelo se cumple casi
siempre, y «casi siempre» no es una garantia cuando lo que esta en juego es si una norma
rige. El flag lo pone la capa de recuperacion —que es la que ve el dato— y el texto lo
anade el CoreGraph despues de generar la respuesta.

Un documento necesita aviso si NO ha pasado revision humana de vigencia
(`vigencia_validada_el IS NULL`) o si su estado no es exactamente 'vigent'. El catalogo real
trae valores como 'vigent?', que es precisamente el caso que hay que advertir.
"""
from __future__ import annotations

from typing import Any

ESTAT_VIGENT = "vigent"
ESTAT_DEROGAT = "derogat"

AVISO_VIGENCIA_NO_VALIDADA = (
    "Aviso: la vigencia de la normativa citada no esta validada, asi que puede haber sido "
    "modificada o derogada. Confirmalo en la fuente oficial antes de actuar."
)

CLAVE_METADATO = "vigencia_no_validada"


def vigencia_no_validada(
    estat_vigencia: str | None,
    vigencia_validada_el: Any | None,
) -> bool:
    """True si el documento no puede presentarse como vigente sin advertirlo."""
    if vigencia_validada_el is None:
        return True
    return estat_vigencia != ESTAT_VIGENT


def marca_de_vigencia(documento: Any) -> dict[str, bool]:
    """Metadato listo para incrustar en un `Source` o un `EvidenceItem`."""
    return {
        CLAVE_METADATO: vigencia_no_validada(
            getattr(documento, "estat_vigencia", None),
            getattr(documento, "vigencia_validada_el", None),
        )
    }


def aviso_para(items: list[Any]) -> str | None:
    """Bloque de aviso para la respuesta, o None si no hay nada que advertir.

    Nombra los documentos afectados: un aviso genérico no dice de qué norma se duda, y el
    usuario necesita saber cuál de las citas tiene que confirmar.
    """
    afectados = [
        (getattr(i, "title", None) or getattr(i, "source_id", "?"))
        for i in items
        if (getattr(i, "metadata", None) or {}).get(CLAVE_METADATO)
    ]
    if not afectados:
        return None
    unicos = list(dict.fromkeys(afectados))
    return f"---\n{AVISO_VIGENCIA_NO_VALIDADA}\nDocumentos afectados: {', '.join(unicos)}."
