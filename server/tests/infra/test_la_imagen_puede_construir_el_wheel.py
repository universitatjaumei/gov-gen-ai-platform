"""Lo que `server/pyproject.toml` necesita para construirse tiene que estar en la imagen.

**Esto lo escribió un fallo real, encontrado a un paso del despliegue.** PLG.1 añadió
`[build-system]` a `server/pyproject.toml` —sin backend de construcción no hay entry points que
descubrir, y los entry points son el mecanismo entero del bloque—. El efecto colateral es que
`uv sync` pasó a **construir el wheel del proyecto**, cosa que antes no hacía, y hatchling lee
`readme = "README.md"`. El `Dockerfile` copiaba al *builder* sólo `pyproject.toml` y `uv.lock`,
así que la construcción abortaba con `OSError: Readme file does not exist: README.md`.

**Ningún test lo vio, y no por descuido**: `ci.yml` no construye imágenes, y en local se instala
sobre un árbol completo donde el fichero siempre está. El error sólo aparece en un contexto de
construcción recortado, que es exactamente el de producción.

Esto **no sustituye a IMG.1** —construir y arrancar la imagen en CI, que es lo único que lo cubre
entero— sino que caza la clase concreta que ya mordió, y cuesta milisegundos en vez de minutos.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

_RAIZ = Path("..")
_MANIFIESTO = _RAIZ / "server" / "pyproject.toml"
_DOCKERFILE = _RAIZ / "Dockerfile"


def _copias_al_builder() -> list[str]:
    """Las rutas de `server/` que el *builder* copia antes de instalar.

    Se lee hasta el primer `FROM` posterior al inicial: lo que venga después es la imagen de
    runtime, y ahí el fichero ya no sirve para construir nada.
    """
    lineas = _DOCKERFILE.read_text(encoding="utf-8").splitlines()

    etapas = [i for i, ln in enumerate(lineas) if ln.strip().upper().startswith("FROM ")]
    fin = etapas[1] if len(etapas) > 1 else len(lineas)

    copiadas: list[str] = []
    for linea in lineas[: fin]:
        limpia = linea.strip()
        if not limpia.upper().startswith("COPY "):
            continue
        piezas = [p for p in limpia.split()[1:] if not p.startswith("--")]
        copiadas.extend(piezas[:-1])  # el ultimo es el destino
    return copiadas


def test_el_builder_copia_lo_que_hatchling_necesita_leer() -> None:
    manifiesto = tomllib.loads(_MANIFIESTO.read_text(encoding="utf-8"))

    if "build-system" not in manifiesto:
        # Sin backend de construccion, `uv sync` no construye el proyecto y nada de esto aplica.
        return

    readme = manifiesto.get("project", {}).get("readme")
    if not isinstance(readme, str):
        return

    copiadas = _copias_al_builder()
    esperada = f"server/{readme}"
    cubierto = any(
        c == esperada or re.fullmatch(r"server/?\*?", c) or c in {"server/", "."}
        for c in copiadas
    )

    assert cubierto, (
        f"`server/pyproject.toml` declara `readme = \"{readme}\"` y tiene `[build-system]`, así "
        f"que `uv sync` construye el wheel y hatchling **abre ese fichero**. El builder del "
        f"`Dockerfile` copia {sorted(copiadas)}, que no lo incluye.\n\n"
        f"La construcción de la imagen falla con `OSError: Readme file does not exist`, y no lo "
        f"ve ningún otro test: CI no construye imágenes y en local el árbol está completo.\n"
        f"Arreglo: añadir `{esperada}` al `COPY` del builder."
    )
