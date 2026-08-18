"""Qué bloques se pintan y en qué sección (SEG.5).

La vista previa y el ensamblado final recorren las **secciones** y pintan los bloques que cada
sección enumera en `block_ids`. Un bloque que no aparece en ninguna sección existe, se ejecuta,
extrae sus datos, pasa la revisión... y no sale en el informe. Sin error y sin aviso.

Es el fallo que produjo un informe de seguimiento con las dos secciones vacías después de que
las nueve tablas se extrajeran y las nueve valoraciones se aprobaran. Aquí vive la comprobación
para que ni el borrador que propone el modelo ni la plantilla que se publica puedan quedarse así.

Deploy: edge
"""
from __future__ import annotations

from typing import Any, Iterable

#: Bloques que no se imprimen: producen datos para que otro los pinte, o frenan el flujo.
#: Un `DETERMINISTIC_DATA` puesto en una sección además duplicaría la tabla, porque el
#: `TABLE` que lo referencia ya la pinta. Que estén fuera de toda sección es lo normal.
_NO_SE_IMPRIMEN = frozenset({"DETERMINISTIC_DATA", "DATA_TRANSFORM", "REVIEW_GATE"})


def bloques_sin_seccion(sections: Iterable[Any], blocks: Iterable[Any]) -> list[str]:
    """Los ids de bloque **imprimibles** que ninguna sección enumera, en orden de declaración.

    Al revés no se comprueba: una sección que referencia un bloque inexistente no rompe el
    informe —la vista previa se lo salta— y en cambio la plantilla se construye por pasos, así
    que una referencia adelantada es un estado de trabajo legítimo.
    """
    asignados: set[str] = set()
    for seccion in sections:
        for bid in getattr(seccion, "block_ids", None) or []:
            asignados.add(str(bid))

    return [
        str(bloque.id)
        for bloque in blocks
        if str(getattr(bloque, "id", "")) not in asignados
        and str(getattr(bloque, "kind", "")) not in _NO_SE_IMPRIMEN
    ]
