"""Qué versión es este despliegue. Deploy: shared.

**Lo que se versiona es el despliegue, no un paquete.** Son cuatro imágenes más la cabeza de
Alembic, así que la fuente única es el fichero `VERSION` de la raíz y no el `pyproject.toml` de
ninguno de los cuatro proyectos: elegir uno dejaría a los otros tres divergiendo en silencio, que
es exactamente como llegaron a decir `0.1.0` tres y `0.0.0` el frontend.

**Dos orígenes y ningún hueco.** En la imagen llega por `GOVGENAI_VERSION`, estampada al
construir; en desarrollo se lee del fichero. Nunca devuelve vacío: una versión que a veces es
`None` obliga a tratar el caso a quien la lee y acaba mostrándose en blanco justo cuando hace
falta, que es al reportar un fallo.

**`0.x` a propósito.** En semver significa «cualquier cosa puede romperse», y eso es lo que un
proyecto experimental tiene que comunicar. El razonamiento completo —incluido por qué subir a
`1.0.0` diría lo contrario— está en `docs/VERSIONADO.md`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

#: Cuando ni la variable ni el fichero están. No es un valor plausible a propósito: si esto
#: aparece en un informe de fallo, lo que hay que arreglar es el empaquetado.
DESCONOCIDA = "0.0.0+desconocida"

_FICHERO = Path(__file__).resolve().parents[3] / "VERSION"


@lru_cache(maxsize=1)
def version() -> str:
    """La versión de este despliegue.

    Cacheada porque no cambia mientras el proceso vive, y la lee un endpoint público.
    """
    de_la_imagen = (os.getenv("GOVGENAI_VERSION") or "").strip()
    if de_la_imagen:
        return de_la_imagen
    try:
        del_fichero = _FICHERO.read_text(encoding="utf-8").strip()
    except OSError:
        return DESCONOCIDA
    return del_fichero or DESCONOCIDA
