"""Retirar los hallazgos que ya no son ciertos (CUR.9).

Deploy: edge.

Del usuario, tras las pruebas manuales del Bloque CUR: «debería añadirse la pasada de reconciliación
al analizar. No tiene sentido que haya filas que ya no sean ciertas». Medido antes de arreglarlo:
**241 hallazgos `stale` guardados donde el detector de hoy emite 207** — la diferencia son páginas
que pasaron a agruparse como serie por curso académico (CUR.7) y dejaron de producir aviso, con su
fila vieja siguiendo ahí. Cada mejora del detector dejaba un sedimento de acusaciones caducadas, y
una lista de trabajo con filas falsas se deja de usar entera.

El detector sólo sabía **añadir** (`upsert`): afirmaba, y nunca dejaba de afirmar. Esto es la otra
mitad.

Tres reglas, y las tres están para que la reconciliación no borre nada que no deba:

1. **Sólo se retira lo que este pase podía volver a afirmar.** Cada detector declara sus tipos y se
   reconcilian los de los detectores que **han corrido**. Reconciliar lo que no se ha mirado sería
   retirar por no haber buscado.
2. **`duplicate` lo emiten los dos detectores** —el determinista por `content_hash` exacto y el
   semántico por significado—, así que se reconcilia sólo cuando los dos han pasado. Con el
   semántico apagado, un pase determinista habría resuelto los duplicados semánticos.
3. **Lo que una persona decidió no se toca**: `dismissed` es un juicio humano y `resolved` está
   cerrado. Sólo se retiran `new` y `confirmed`.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import select

from server.app.modules.agents_hub.database.operational_models import HubContentFinding

#: Lo que se escribe al retirar. Un `resolved` a secas se lee como «alguien lo arregló», y aquí
#: nadie lo ha mirado: lo único cierto es que el detector ya no lo afirma.
NOTA_DE_RETIRADA = "Retirado por la reconciliación: ya no se detecta en el último análisis."

#: Los estados sobre los que la reconciliación puede actuar.
_RETIRABLES = frozenset({"new", "confirmed"})


def identidad_del_hallazgo(hallazgo: Any) -> tuple[str, Any, Any]:
    """Qué hace que dos hallazgos sean **el mismo**.

    Es a propósito la misma clave que usa `ContentFindingRepo.upsert` para decidir si actualiza o
    crea. Si divergieran, el `upsert` crearía una fila nueva y la reconciliación retiraría la vieja:
    el mismo hallazgo parpadearía en cada pase.
    """
    return (
        hallazgo.finding_type,
        getattr(hallazgo, "page_id", None),
        getattr(hallazgo, "related_page_id", None),
    )


def tipos_a_reconciliar(*, ejecutados: Iterable[Any], omitidos: Iterable[Any]) -> set[str]:
    """Los tipos de hallazgo que este pase puede retirar.

    Un tipo que también emite un detector que no ha corrido queda fuera: no se puede distinguir
    «el detector ya no lo afirma» de «ese detector no ha pasado».
    """
    cubiertos: set[str] = set()
    for detector in ejecutados:
        cubiertos |= set(getattr(detector, "finding_types", ()) or ())

    for detector in omitidos:
        cubiertos -= set(getattr(detector, "finding_types", ()) or ())

    return cubiertos


async def reconciliar_hallazgos(
    session: Any,
    site_id: uuid.UUID,
    *,
    tipos: set[str],
    emitidos: Iterable[Any],
    now: datetime,
) -> int:
    """Retira los hallazgos abiertos del sitio que este pase no ha vuelto a emitir.

    Devuelve cuántos se han retirado. No pasa por `ContentFindingRepo.transition`, que valida las
    transiciones **humanas** (`new` sólo puede ir a `confirmed` o `dismissed`): esto no es una
    persona resolviendo un hallazgo, es el sistema retirando una afirmación que ya no sostiene. La
    nota lo dice, para que en la auditoría se distingan las dos cosas.
    """
    if not tipos:
        return 0

    vistos = {identidad_del_hallazgo(f) for f in emitidos}

    filas = (
        await session.execute(
            select(HubContentFinding).where(
                HubContentFinding.site_id == site_id,
                HubContentFinding.finding_type.in_(tipos),
                HubContentFinding.status.in_(_RETIRABLES),
            )
        )
    ).scalars().all()

    retirados = 0
    for fila in filas:
        # El filtro de la consulta ya acota tipo y estado, pero los dobles de los tests devuelven
        # todo lo que tienen: comprobarlo aquí mantiene la regla en un solo sitio.
        if fila.finding_type not in tipos or fila.status not in _RETIRABLES:
            continue
        if identidad_del_hallazgo(fila) in vistos:
            continue

        fila.status = "resolved"
        fila.reviewed_at = now
        fila.resolution_note = NOTA_DE_RETIRADA
        retirados += 1

    if retirados:
        await session.flush()
    return retirados
