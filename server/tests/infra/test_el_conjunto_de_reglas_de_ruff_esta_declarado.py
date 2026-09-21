"""El conjunto de reglas de `ruff` se declara, no se hereda.

**Lo que lo destapó.** Al subir `ruff` de 0.14.13 a 0.16.8 dentro de una tanda de dependencias,
`ruff check app tests` pasó de **0 a 2.312 errores** sin que cambiara una línea de código. No es
que el código empeorara: es que **no había ninguna configuración de `ruff` en todo el
repositorio** —ni sección en un manifiesto ni `ruff.toml`— y el proyecto vivía del conjunto de
reglas **por omisión** de la herramienta. Cuando ese conjunto creció, el linter se convirtió en
otra herramienta sin que nadie lo decidiera.

Comprobado: con `--select E4,E7,E9,F`, que es lo que 0.14 aplicaba por omisión, la 0.16 vuelve a
pasar limpio. O sea que declararlo **no cambia lo que se exige**; hace explícito lo que era
implícito.

**Por qué esto importa más que el número.** Una herramienta de calidad que cambia de criterio
sola tiene dos finales, y los dos son malos: o pone el trabajo en rojo un lunes por la mañana y
alguien la desactiva, o —peor— **deja de exigir algo que exigía** y nadie se entera, porque un
verde no se investiga. La misma razón por la que la comprobación de tipos declara su alcance en
`[tool.pyright]` en vez de mirarlo todo.

**Ampliar sigue siendo posible y deseable**, sólo que como decisión: la medida está en el
comentario de la configuración —2.312 avisos, 1.526 autoarreglables— y es trabajo del mismo tipo
que la issue #48, con su prompt y su commit.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
MANIFIESTO = RAIZ / "server" / "pyproject.toml"

#: Lo que `ruff` 0.14 aplicaba por omisión, y lo que por tanto se venía exigiendo de verdad.
MINIMO = {"E4", "E7", "E9", "F"}


def _seleccion() -> list[str]:
    datos = tomllib.loads(MANIFIESTO.read_text(encoding="utf-8"))
    return datos.get("tool", {}).get("ruff", {}).get("lint", {}).get("select", [])


def test_hay_seleccion_declarada() -> None:
    seleccion = _seleccion()
    assert seleccion, (
        "`server/pyproject.toml` no declara `[tool.ruff.lint] select`. Sin eso, lo que el "
        "linter exige lo decide la versión de la herramienta: al pasar de 0.14 a 0.16 el "
        "proyecto pasó de 0 a 2.312 errores sin tocar una línea de código."
    )


def test_no_se_pierde_lo_que_ya_se_exigia() -> None:
    """Declarar el conjunto no puede ser la puerta para exigir **menos** que antes."""
    faltan = sorted(MINIMO - set(_seleccion()))
    assert not faltan, (
        f"la selección ha dejado fuera {faltan}, que son parte de lo que `ruff` venía exigiendo "
        "por omisión. Declarar el conjunto sirve para que no cambie solo, no para recortarlo "
        "sin decirlo."
    )
