"""Issue #5 — la tabla de planes no puede dar por pendiente lo que el historial dice cerrado.

`PROJECT_STATE.md` es lo primero que lee quien llega, y la regla del proyecto es que se actualiza
al cerrar cada prompt **precisamente para que no haya que interpretarlo**. Un fichero de estado
que hay que contrastar con `HISTORIAL.md` para saber qué es verdad no es un punto de entrada: es
una trampa para quien llega.

**Al medirlo salió peor de lo que decía la issue, y en otro sitio.** La issue contaba tres
mentiras: PLG dado por pendiente, IMG sin fila y «REPO.1 pendiente». La primera ya estaba
corregida. Lo que nadie había contado es que **cinco bloques más figuraban pendientes estando
cerrados** —REG (9 prompts), VAS (4), NIC (4), DIN (7) y FUN (9), todos con su fila en el
historial— y que **cinco prompts de APER no tienen fila** pese a estar commiteados en `main`:
APER.14 a APER.18. O sea que la deriva va en los dos sentidos, y por eso este guardarraíl mira
las dos.

**Cómo se mide, y por qué así.** La prueba de que un prompt se cerró es **su fila** en
`HISTORIAL.md`, no que su identificador aparezca por ahí: una mención dentro de la prosa de otra
fila significa justamente lo contrario —que alguien lo nombró al contar otra cosa—. Así que se
busca el patrón de columna `| fecha | ID — …`, que es lo que la regla de cierre obliga a escribir.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
HISTORIAL = RAIZ / "planificacion" / "HISTORIAL.md"
ESTADO = RAIZ / "planificacion" / "PROJECT_STATE.md"

_FILA_HISTORIAL = re.compile(
    r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*([A-ZÑ]+)\.(\d+[a-z]?)\b", re.MULTILINE
)
#: Una fila de la tabla de planes: `| 6 ▶ | **REPO** | …` o tachada `| ~~7~~ ✅ | ~~**DEP**~~ |`.
_FILA_PLAN = re.compile(r"^\|\s*(~~\d+~~\s*✅|\d+\s*▶?|—)\s*\|\s*(~~)?\*\*([A-ZÑ]+)\*\*", re.MULTILINE)


def _prompts_cerrados() -> dict[str, set[str]]:
    texto = HISTORIAL.read_text(encoding="utf-8")
    cerrados: dict[str, set[str]] = defaultdict(set)
    for bloque, numero in _FILA_HISTORIAL.findall(texto):
        cerrados[bloque].add(numero)
    return cerrados


def _filas_del_plan() -> dict[str, str]:
    """`{bloque: estado}` según la tabla, con tres estados y no dos.

    La diferencia entre «en curso» y «sin empezar» es la que hace útil este guardarraíl. Un
    bloque marcado `▶` **declara** que va por la mitad, y que tenga prompts cerrados es
    justamente lo que se espera; el que miente es el que no dice nada y sin embargo los tiene.
    """
    texto = ESTADO.read_text(encoding="utf-8")
    filas: dict[str, str] = {}
    for marca, tachado, bloque in _FILA_PLAN.findall(texto):
        if "✅" in marca or tachado:
            filas[bloque] = "completo"
        elif "▶" in marca:
            filas[bloque] = "en curso"
        else:
            filas[bloque] = "sin empezar"
    return filas


def test_el_medidor_encuentra_las_dos_tablas() -> None:
    """Un guardarraíl que lee cero filas pasa en verde sin comprobar nada."""
    cerrados = _prompts_cerrados()
    filas = _filas_del_plan()
    assert len(cerrados) >= 10, (
        f"sólo se ven {len(cerrados)} bloques en `HISTORIAL.md`; el patrón de fila ha dejado de "
        "reconocer el formato"
    )
    assert len(filas) >= 8, (
        f"sólo se ven {len(filas)} filas en la tabla de planes de `PROJECT_STATE.md`"
    )


def test_ningun_bloque_cerrado_figura_pendiente() -> None:
    """La mentira que la issue #5 vino a cerrar, medida en vez de listada.

    Un bloque cuyos prompts tienen todos fila en el historial y que la tabla sigue marcando
    pendiente manda a quien llega a trabajar en algo que ya está hecho.
    """
    cerrados = _prompts_cerrados()
    filas = _filas_del_plan()

    # `▶` queda fuera: ese bloque **dice** que va por la mitad, y tener prompts cerrados es lo
    # que se espera de él. `REPO` es el caso: cinco cerrados y `REPO.2` pendiente de verdad.
    # Y `PRC` no tiene ninguno cerrado, así que su «pendiente» tampoco miente: espera datos de
    # terceros que no dependen de nadie de aquí.
    mentirosos = [
        bloque
        for bloque, estado in filas.items()
        if estado == "sin empezar" and len(cerrados.get(bloque, ())) >= 4
    ]
    assert not mentirosos, (
        f"La tabla de planes da por pendientes bloques con prompts cerrados: {mentirosos}. "
        "Cada uno tiene al menos cuatro filas propias en `HISTORIAL.md`, que es la prueba de "
        "cierre que exige la regla. Un punto de entrada que hay que contrastar con el historial "
        "para saber qué es verdad no es un punto de entrada."
    )


def test_los_prompts_de_aper_tienen_su_fila() -> None:
    """La deriva en el otro sentido: código cerrado sin dejar rastro en el historial.

    APER.14 a APER.18 se commitearon en `main` y ninguno dejó fila. Se nota sólo cuando alguien
    va a buscar por qué se hizo algo y no encuentra nada, que es meses después.
    """
    cerrados = _prompts_cerrados().get("APER", set())
    numeros = {int(re.sub(r"\D", "", n)) for n in cerrados}
    faltan = sorted(set(range(1, max(numeros) + 1)) - numeros) if numeros else []
    assert not faltan, (
        f"Estos prompts de APER no tienen fila en `HISTORIAL.md`: {faltan}. Están cerrados y "
        "commiteados, así que el historial dice menos de lo que pasó."
    )
