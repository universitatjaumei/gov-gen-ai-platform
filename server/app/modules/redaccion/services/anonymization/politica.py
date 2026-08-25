"""Qué modo de anonimización se aplica, y quién manda cuando hay dos opiniones (AIS.5).

**El ajuste vivía sólo en el informe**, y la frase que lo cambia es del usuario: el modo
«depende del contrato con el proveedor LLM y del tipo de datos». Ninguna de las dos cosas es una
decisión por informe — el contrato es de la **organización** —, así que la política se fija ahí y
el informe la hereda.

Y se hereda con una regla dura: **el informe puede endurecer, nunca relajar**. Un modo por
defecto que cualquiera puede bajar a `off` no es una política, es una sugerencia; y quien crea un
informe no tiene por qué saber qué permite el contrato de su organización con el proveedor.

La cadena es organización → código, y `None` significa «la organización no lo ha fijado», que es
la misma semántica de `core/ambito.py` para el resto de la configuración heredable. Aquí no se
usa aquella cascada porque no hay nivel de plataforma que competir: el suelo es el código, y
convertirlo en fila sería configuración que nadie ha pedido.
"""
from __future__ import annotations

from server.app.modules.redaccion.services.anonymization.run_context import AnonymizationMode

#: Lo que se aplica cuando la organización no ha fijado nada. Es el comportamiento de siempre.
MODO_POR_DEFECTO = AnonymizationMode.REPLACE

#: De menos a más protector.
#:
#: `replace_with_disposition_7` es el más protector **a propósito**, aunque «reemplazar» suene
#: más completo que «enmascarar»: enmascara DNI, NIE y pasaporte de forma **irreversible**
#: (Disposición Adicional 7ª de la LOPDGDD), así que ni quien generó el informe puede deshacerlo.
#: Un orden que lo pusiera por debajo de `replace` dejaría que un informe «endureciera» hacia
#: algo reversible.
_NIVEL: dict[AnonymizationMode, int] = {
    AnonymizationMode.OFF: 0,
    AnonymizationMode.DETECT_ONLY: 1,
    AnonymizationMode.REPLACE: 2,
    AnonymizationMode.REPLACE_WITH_DISPOSITION_7: 3,
}


def _como_modo(valor: AnonymizationMode | str | None) -> AnonymizationMode | None:
    if valor is None:
        return None
    if isinstance(valor, AnonymizationMode):
        return valor
    texto = str(valor).strip()
    if not texto:
        return None
    return AnonymizationMode(texto)


def nivel_de_proteccion(modo: AnonymizationMode | str) -> int:
    """Cuánto protege este modo, para poder compararlos."""
    resuelto = _como_modo(modo)
    if resuelto is None:
        raise ValueError("un modo vacío no tiene nivel de protección")
    return _NIVEL[resuelto]


def modo_heredado(*, de_la_organizacion: AnonymizationMode | str | None) -> AnonymizationMode:
    """El modo que hereda un informe: el de su organización, y si no lo fijó, el del código."""
    return _como_modo(de_la_organizacion) or MODO_POR_DEFECTO


def modo_efectivo(
    *, heredado: AnonymizationMode | str | None, pedido: AnonymizationMode | str | None
) -> AnonymizationMode:
    """El modo que se aplica de verdad.

    **`MODO_POR_DEFECTO` es un valor por omisión, no un suelo, y la diferencia es el prompt
    entero.** La decisión del usuario fue que la anonimización sea *configurable y no
    obligatoria*; si el valor del código actuara como mínimo, nadie podría elegir `off` ni
    `detect_only` en una instalación recién montada — o sea que sería obligatoria con otro
    nombre. **Suelo lo es sólo la política que una organización ha fijado a propósito.**

    Así que: sin política de organización manda lo que pida el informe; con política, el más
    protector de los dos. Escrito como un máximo, añadir un modo nuevo no obliga a revisar
    ninguna comparación — sólo a colocarlo en `_NIVEL`.
    """
    suelo = _como_modo(heredado)
    solicitado = _como_modo(pedido)
    if solicitado is None:
        return suelo or MODO_POR_DEFECTO
    if suelo is None:
        return solicitado
    return solicitado if _NIVEL[solicitado] >= _NIVEL[suelo] else suelo


def motivo_de_no_relajar(
    *, heredado: AnonymizationMode | str | None, pedido: AnonymizationMode | str | None
) -> str | None:
    """Por qué no se aplicó lo que se pidió, o `None` si sí se aplicó.

    Quien pide `off` y sigue viendo `replace` creerá que la pantalla está rota. Decírselo es la
    diferencia entre una política y un fallo aparente — el mismo criterio con el que SEC.9.2
    devuelve un 400 explicando qué falta en vez de elegir por el usuario.
    """
    suelo = _como_modo(heredado)
    solicitado = _como_modo(pedido)
    if suelo is None or solicitado is None or _NIVEL[solicitado] >= _NIVEL[suelo]:
        return None
    # `.value` y no el enum: `AnonymizationMode` hereda de `str, Enum`, y desde Python 3.12
    # interpolarlo imprime `AnonymizationMode.REPLACE`. Este texto lo lee una persona en la
    # pantalla, y ahí eso no significa nada.
    return (
        f"Tu organización exige al menos «{suelo.value}» para los informes, así que "
        f"«{solicitado.value}» no se aplica: se mantiene «{suelo.value}». Un informe puede "
        "endurecer la anonimización, no relajarla."
    )
