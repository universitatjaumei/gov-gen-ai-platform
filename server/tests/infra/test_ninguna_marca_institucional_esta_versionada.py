"""Ninguna marca institucional viaja en el repositorio — y esta vez en TODO el árbol.

Ya había dos guardarraíles de esto y **los dos miraban sólo el frontend**:
`frontend/src/__tests__/marcaNoViajaEnElRepo.test.ts` saca las imágenes del *bundle* y
`paletaDelPanelNoEsDeNadie.test.ts` saca la marca de los tokens de color. Entre los dos dejaban
fuera el resto del árbol, y ahí sobrevivió el defecto: **`docs/chatbots-publicos/marcauji.png`
llevaba versionado desde el 2026-08-21** —junto con `uji-theme.css` y `demo-uji.html`— y nada
avisaba.

Lo instructivo es **por qué** entró: lo puso el arreglo de
`test_los_html_de_docs_no_apuntan_a_imagenes_fantasma.py`. Aquel guardarraíl detectó que
`demo-uji.html` apuntaba a un logotipo que la regla `*.png` de `.gitignore` mantenía fuera del
repositorio, así que la página se veía en el disco del desarrollador y en ningún otro sitio; el
arreglo correcto para *ese* problema era versionar la imagen. Un guardarraíl exigió lo que otro
—el que faltaba— habría prohibido, y la contradicción no se vio porque el segundo no existía.

**La resolución no es aflojar ninguno de los dos, es que el trío salga junto.** Si `demo-uji.html`
no está, nada referencia `marcauji.png` y los dos guardarraíles quedan satisfechos a la vez. Los
tres se conservan en `_local/docs_operacion/`, que está ignorada, y su sede definitiva es el
repositorio privado de operación.

**Por qué se busca por subcadena y no con `\\b`.** `marcauji.png` pega el nombre de la institución
a otra palabra, así que una frontera de palabra **no lo ve** — el mismo defecto que dejó pasar
`UjiMergeStrategy` en `test_ais2_nada_institucional_en_el_principal.py`. En rutas de fichero la
subcadena no da falsos positivos: medido el 2026-09-07 sobre `git ls-files` completo, caza
**exactamente tres ficheros y ninguno más**.

Y se pregunta a **git**, no al disco: lo que importa es qué recibe quien clona, no qué hay en la
máquina del mantenedor. Es la misma lección que ya llevan escrita el guardarraíl de imágenes
fantasma y `test_repo3_el_indice_de_docs_no_miente.py`.
"""

from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path

_RAIZ = Path("..")

#: Instituciones concretas, **sin fronteras de palabra** porque los nombres de fichero las pegan
#: a otras (`marcauji.png`). Misma lista que AIS.2: `generalitat` está para que el patrón sirva a
#: cualquiera y no sólo a la de esta casa.
_INSTITUCIONES_EN_RUTAS = re.compile(
    r"(uji|jaume|castell[oó]n?|innovap|generalitat)", re.IGNORECASE
)

#: Rutas que pueden nombrar una institución porque son REGISTRO del pasado o material del corpus
#: y no marca. Vacía a propósito: hoy no hace falta ninguna excepción, y que siga vacía es la
#: señal de que el árbol está limpio. Si algún día entra algo aquí, va con su justificación.
_EXCEPCIONES: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _versionados() -> tuple[str, ...]:
    salida = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=_RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return tuple(p for p in salida.split("\0") if p)


class TestNingunaRutaVersionadaNombraUnaInstitucion:

    def test_should_not_version_any_file_named_after_an_institution(self):
        culpables = [
            ruta
            for ruta in _versionados()
            if _INSTITUCIONES_EN_RUTAS.search(ruta) and ruta not in _EXCEPCIONES
        ]

        assert culpables == [], (
            "ficheros versionados que nombran una institución en su ruta:\n  "
            + "\n  ".join(culpables)
            + "\n\nLa marca de una organización llega por la cascada del servidor "
            "(plataforma → organización → asistente), no viajando en el árbol. Si es "
            "material de operación de una instalación concreta, su sede es el repositorio "
            "privado de operación."
        )


class TestNingunaImagenNuevaEntraEnDocs:
    """`docs/` es documentación de la plataforma, no un directorio de recursos de marca.

    Hermano del test de arriba pero por otra vía: una imagen puede no llevar el nombre de la
    institución en el fichero y ser su logotipo igualmente. Se permite lo que ya hay —diagramas
    genéricos— y se exige que cualquier imagen nueva pase por aquí a propósito.
    """

    #: Extensiones de imagen. `svg` incluido: un logotipo en vectorial es igual de institucional.
    _IMAGENES = re.compile(r"\.(png|jpe?g|gif|webp|avif|ico|svg)$", re.IGNORECASE)

    def test_should_not_version_images_under_docs(self):
        imagenes = [
            ruta
            for ruta in _versionados()
            if ruta.startswith("docs/") and self._IMAGENES.search(ruta)
        ]

        assert imagenes == [], (
            "imágenes versionadas bajo `docs/`:\n  "
            + "\n  ".join(imagenes)
            + "\n\nSi es un diagrama de la plataforma, su sitio es `frontend/public/`. Si es "
            "marca de una organización, no va en el repositorio."
        )
