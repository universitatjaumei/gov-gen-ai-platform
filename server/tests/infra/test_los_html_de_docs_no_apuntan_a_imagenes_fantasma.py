"""Las páginas HTML de `docs/` no pueden referenciar imágenes que no estén versionadas.

Encontrado al revisar el repositorio antes de abrirlo: `docs/chatbots-publicos/demo-uji.html`
apuntaba a `../../Diseño/marcauji.png`, y la regla general `*.png` de `.gitignore` —pensada para
capturas de pantalla— mantenía ese fichero fuera del repositorio. En el disco del desarrollador la
página se veía con su logotipo; para cualquiera que clonase, no.

Y fallaba **en silencio**: el `<img>` llevaba `onerror="this.style.display='none'"`, así que la
imagen simplemente no aparecía. Nadie iba a darse cuenta.

Es el mismo fallo que ya cazó `frontend/src/__tests__/assetsVersionados.test.ts`, pero ese
guardarraíl sólo mira `frontend/src` y los imports con alias `@/`. Las páginas de `docs/` quedaban
en tierra de nadie, que es justo donde el defecto sobrevivió.

Como antes: no basta comprobar que el fichero existe en el disco —ahí está—, hay que comprobar que
**está versionado**.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DOCS = RAIZ / "docs"

# Atributos que cargan un recurso local en una página estática.
_REFERENCIA = re.compile(r"""(?:src|href)\s*=\s*["']([^"'#?]+)["']""", re.IGNORECASE)
_IMAGEN = re.compile(r"\.(png|jpe?g|gif|webp|svg|avif|ico)$", re.IGNORECASE)


def _ficheros_versionados() -> set[str]:
    salida = subprocess.run(
        ["git", "ls-files", "docs"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {linea for linea in salida.splitlines() if linea}


def _imagenes_referenciadas() -> list[tuple[Path, str]]:
    referencias: list[tuple[Path, str]] = []
    for pagina in sorted(DOCS.rglob("*.html")):
        contenido = pagina.read_text(encoding="utf-8", errors="replace")
        for destino in _REFERENCIA.findall(contenido):
            if destino.startswith(("http://", "https://", "data:", "//", "mailto:")):
                continue
            if _IMAGEN.search(destino):
                referencias.append((pagina, destino))
    return referencias


def test_las_imagenes_de_los_html_de_docs_existen_en_el_disco() -> None:
    inexistentes = [
        f"{pagina.relative_to(RAIZ).as_posix()} -> {destino}"
        for pagina, destino in _imagenes_referenciadas()
        if not (pagina.parent / destino).resolve().is_file()
    ]
    assert inexistentes == [], (
        "estas páginas apuntan a imágenes que no están en el disco: " f"{inexistentes}"
    )


def test_las_imagenes_de_los_html_de_docs_estan_versionadas() -> None:
    versionados = _ficheros_versionados()
    sin_versionar: list[str] = []

    for pagina, destino in _imagenes_referenciadas():
        absoluta = (pagina.parent / destino).resolve()
        try:
            relativa = absoluta.relative_to(RAIZ).as_posix()
        except ValueError:
            # Apunta fuera del repositorio: nadie que clone lo tendrá.
            sin_versionar.append(f"{pagina.relative_to(RAIZ).as_posix()} -> {destino} (fuera del repositorio)")
            continue
        if relativa not in versionados:
            sin_versionar.append(f"{pagina.relative_to(RAIZ).as_posix()} -> {relativa}")

    assert sin_versionar == [], (
        "estas imágenes no están en git: quien clone el repositorio verá la página sin ellas, "
        f"y sin ningún error visible. {sin_versionar}"
    )
