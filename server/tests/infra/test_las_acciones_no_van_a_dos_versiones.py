"""La misma acción no puede estar fijada a dos majors distintas en el repositorio.

**Lo que lo destapó.** Dependabot abrió una PR para subir `actions/checkout` «de la 4 a la 7», y
al mirarlo resultó que **seis de los siete usos ya estaban en v7**: los subió un commit del
2026-08-21 («las acciones a su major actual, no a v5») y `deploy.yml` se quedó atrás. Un mes
entero con el mismo repositorio ejecutando dos versiones de la misma acción según el workflow.

**Por qué importa aunque no rompa nada.** No rompió nada, y eso es justamente el problema: el
que se quedó atrás es **el del despliegue**, o sea el que menos veces corre y el que más cuesta
depurar cuando falla. Una acción que se comporta distinto según el workflow convierte «en CI
funciona» en una frase sin contenido. Y el modo de fallo es silencioso: nadie mira la versión de
una acción que lleva meses funcionando.

Lo que este fichero **no** pide es que todo esté en la última: pide que **no haya dos**. Subir es
una decisión; tener dos versiones a la vez no es una decisión, es un descuido.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
WORKFLOWS = RAIZ / ".github" / "workflows"

_USO = re.compile(r"uses:\s*([A-Za-z0-9._/-]+)@(v?[0-9][^\s]*)")


def _versiones_por_accion() -> dict[str, dict[str, list[str]]]:
    """`{accion: {major: [ficheros]}}`, agrupando por el major de la referencia."""
    encontradas: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for fichero in sorted(WORKFLOWS.glob("*.yml")):
        for accion, version in _USO.findall(fichero.read_text(encoding="utf-8")):
            major = re.match(r"v?(\d+)", version)
            if major:
                encontradas[accion][major.group(1)].append(fichero.name)
    return encontradas


def test_el_medidor_encuentra_acciones() -> None:
    """Un guardarraíl que no lee ninguna acción pasa en verde sin comprobar nada."""
    acciones = _versiones_por_accion()
    assert len(acciones) >= 5, (
        f"sólo se ven {len(acciones)} acciones en los workflows; el patrón ha dejado de "
        "reconocer la forma de `uses:`"
    )


def test_ninguna_accion_va_a_dos_majors() -> None:
    discrepantes = {
        accion: {major: sorted(set(ficheros)) for major, ficheros in majors.items()}
        for accion, majors in _versiones_por_accion().items()
        if len(majors) > 1
    }
    assert not discrepantes, (
        "Estas acciones están fijadas a dos majors distintas a la vez:\n  - "
        + "\n  - ".join(f"{a}: {v}" for a, v in discrepantes.items())
        + "\n\nNo rompe nada hasta que rompe, y el que se queda atrás suele ser el workflow que "
        "menos corre — el del despliegue, en el caso que originó esto—, que es el peor sitio "
        "para tener una diferencia que nadie mira."
    )
