"""REPO.4 — el repositorio deja de nombrar a su dueño anterior, y CODEOWNERS a un equipo.

**Dos cosas distintas, y la segunda es la que tiene fondo.** Retirar el nombre viejo es mecánico.
Lo que no lo es: `CODEOWNERS` asignaba **catorce entradas a una persona**, y una persona no es un
mantenedor sostenible para un repositorio institucional que va a abrirse. Si la retirada se
hiciera cambiando un nombre de persona por otro, el problema seguiría exactamente igual — por eso
hay un test que lo prohíbe, y no sólo uno que busca el nombre viejo.

**La distinción registro / activo** es la misma que usa `test_repo3_el_indice_de_docs_no_miente.py`:
`HISTORIAL.md` y los planes de fase **cuentan lo que pasó** y deben seguir nombrando al dueño
anterior — reescribirlos sería falsear el registro. Lo que no puede nombrarlo es lo que un lector
nuevo consulta como verdad presente.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_RAIZ = Path("..")

DUENO_ANTERIOR = "ModestoFabra"

#: Lo que es REGISTRO y por tanto puede —y debe— seguir nombrándolo.
#:
#: `planificacion/fase1/` entero: son los prompts tal y como se escribieron, y varios narran
#: precisamente la operación de cambio de dueño. `HISTORIAL.md` por lo mismo.
REGISTRO = (
    "planificacion/HISTORIAL.md",
    "planificacion/fase1/",
)


def _versionados() -> list[str]:
    """Se pregunta a git, no al disco.

    El disco del mantenedor tiene cosas que nadie más ve; lo que importa es lo que recibe quien
    clona. Mismo motivo y mismo remedio que en el guardarraíl de REPO.3.
    """
    salida = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=_RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in salida.split("\0") if p]


def _es_registro(ruta: str) -> bool:
    return any(ruta.startswith(r) or ruta == r for r in REGISTRO)


def _propietarios_asignados() -> list[str]:
    """Los `@algo` de las líneas de ASIGNACIÓN, saltándose los comentarios.

    Se lee como lo lee GitHub: una línea que empieza por `#` no asigna nada. Buscar `@…` en el
    fichero entero parecía más simple y era incorrecto — se puso rojo por la palabra `@usuario`
    escrita **dentro de un comentario de este mismo fichero**, que explicaba precisamente la regla
    que el test comprueba. Un guardarraíl que se dispara con su propia documentación enseña a
    desactivarlo.
    """
    texto = (_RAIZ / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    propietarios: list[str] = []
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#"):
            continue
        propietarios.extend(re.findall(r"@[\w.-]+(?:/[\w.-]+)?", limpia))
    return propietarios


def test_ningun_fichero_vivo_nombra_al_dueno_anterior() -> None:
    culpables: list[str] = []
    for ruta in _versionados():
        if _es_registro(ruta):
            continue
        fichero = _RAIZ / ruta
        try:
            texto = fichero.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binarios: no nombran a nadie
        if DUENO_ANTERIOR in texto:
            culpables.append(ruta)

    assert not culpables, (
        f"Estos ficheros VIVOS todavía nombran a '{DUENO_ANTERIOR}':\n  - "
        + "\n  - ".join(culpables)
        + f"\n\nEl repositorio es de `universitatjaumei` desde el 2026-09-10. Un fichero que "
        f"nombra al dueño anterior manda a quien lo lee a una URL que sólo funciona por "
        f"redirección, y esa redirección desaparece el día que alguien registre ese nombre.\n"
        f"Si el fichero es REGISTRO —cuenta lo que pasó— va en la lista `REGISTRO` de este "
        f"mismo test, con su razón."
    )


def test_codeowners_asigna_a_un_equipo_y_no_a_una_persona() -> None:
    """La parte que tiene fondo: un repositorio institucional no lo mantiene una persona.

    Sin este test, «retirar los anclajes» se podría hacer cambiando `@ModestoFabra` por otro
    `@usuario` y el guardarraíl de arriba pasaría en verde. El problema —un único punto de fallo
    humano en catorce rutas críticas, entre ellas `/server/migrations/` y `/.github/workflows/`—
    seguiría exactamente igual.
    """
    duenos = _propietarios_asignados()
    assert duenos, "CODEOWNERS no asigna a nadie: sin propietarios no se pide revisión a nadie."

    personas = [d for d in duenos if "/" not in d]
    assert not personas, (
        f"CODEOWNERS asigna a usuarios individuales: {sorted(set(personas))}. Tiene que "
        f"asignar a un EQUIPO de la organización (`@org/equipo`).\n\n"
        f"Una persona no es un mantenedor sostenible para un repositorio institucional que va a "
        f"abrirse: se va de vacaciones, cambia de puesto o deja la casa, y catorce rutas "
        f"críticas se quedan sin revisor sin que nadie se entere."
    )


def test_el_equipo_de_codeowners_es_de_la_organizacion_correcta() -> None:
    """Un equipo de otra organización no existe para GitHub: no pediría revisión a nadie.

    Y no daría error — CODEOWNERS con un propietario inexistente **falla en silencio**, que es la
    forma de avería que este proyecto persigue en todas partes.
    """
    equipos = [d[1:].split("/")[0] for d in _propietarios_asignados() if "/" in d]
    ajenos = sorted({o for o in equipos if o != "universitatjaumei"})

    assert not ajenos, (
        f"CODEOWNERS nombra equipos de otra organización: {ajenos}. El repositorio vive en "
        f"`universitatjaumei`, y un equipo de fuera no existe para GitHub a estos efectos: "
        f"no se pediría revisión a nadie, y sin ningún error."
    )


@pytest.mark.parametrize(
    "ruta,debe_decir",
    [
        ("CONTRIBUTING.md", "no hay fork privilegiado"),
        ("CONTRIBUTING.md", "Alojar no es"),
    ],
)
def test_la_gobernanza_sobrevive_al_cambio_de_dueno(ruta: str, debe_decir: str) -> None:
    """Lo que REPO.4 no puede romper al arreglar lo que vino a arreglar.

    El principal pasa a vivir en la organización de la UJI, y **el lugar del repositorio se lee
    como jerarquía si nadie lo desmiente**. Hasta este cambio la pregunta no se planteaba —el
    principal no estaba en ninguna institución—, así que el texto que decía «aquí no se nombra
    ninguno» bastaba. Ya no: ahora hay que decir explícitamente que alojar no es dirigir.
    """
    # Espacios normalizados: la frase puede partirse en dos líneas al reajustar el párrafo, y un
    # guardarraíl que se pone rojo por un salto de línea enseña a desactivarlo, no a arreglarlo.
    texto = " ".join((_RAIZ / ruta).read_text(encoding="utf-8").split())

    assert debe_decir in texto, (
        f"`{ruta}` ha dejado de decir «{debe_decir}». La regla de gobernanza es que **no hay "
        f"fork privilegiado, incluida la universidad donde nació**, y que el principal viva en "
        f"la organización de la UJI no se lo da. Si este texto desaparece, la gobernanza se lee "
        f"como que la UJI dirige el proyecto."
    )
