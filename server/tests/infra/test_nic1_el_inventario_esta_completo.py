"""NIC.1 — el inventario de la retirada tiene una fila por fichero, o no sirve.

**Por qué este guardarraíl y no confiar en el documento.** La regla de retirada de legacy exige
que nada se borre antes de estar cubierto, y el inventario es lo que sostiene esa afirmación para
187 ficheros. Un inventario **incompleto** es peor que ninguno: da la impresión de haberse hecho
el cruce y deja fuera precisamente los ficheros que nadie miró — que son los que se borran sin
enterarse.

Así que se compara contra `git ls-files`: si mañana alguien añade un fichero a `client_app/app/ui`
sin inventariarlo, o el documento se queda a medias, esto se pone rojo.

**Qué no comprueba, y conviene decirlo**: que la etiqueta sea *correcta*. Que `anonymizer_page.py`
esté de verdad cubierto por `WorkspaceAnonymizationPanel.tsx` lo decide una persona leyendo las
dos cosas; un test sólo puede exigir que la afirmación exista y esté justificada. Lo que sí caza
es la etiqueta que falta y la justificación vacía, que es por donde se cuela un borrado.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
INVENTARIO = RAIZ / "docs" / "INVENTARIO_RETIRADA_LEGACY.md"

#: Los dos directorios que NIC.1 cruza. `app/ui` es la interfaz NiceGUI y `app/services` la lógica
#: que arrastra; el resto de `client_app/` lo decide NIC.3.
DIRECTORIOS = ("client_app/app/ui", "client_app/app/services")

ETIQUETAS = ("cubierto", "parcial", "no cubierto", "no aplica")


def _fila_de(texto: str, ruta: str) -> str | None:
    """La fila de la tabla, no cualquier línea que mencione la ruta.

    La primera versión buscaba `ruta in linea`, y la prosa de la cabecera nombra tres ficheros
    —`ui_translations.json`, `extraction_service.py` y `design_sandbox_service.py`— para explicar
    por qué están etiquetados así. El test cogía esa línea en vez de la fila y daba un falso
    positivo. Una fila de tabla empieza por `` | `ruta` ``.
    """
    prefijo = f"| `{ruta}` |"
    return next((l for l in texto.splitlines() if l.startswith(prefijo)), None)


def _versionados() -> list[str]:
    """Los ficheros que git conoce, que es la lista que no se puede discutir.

    Se usa `git ls-files` y no un `rglob`: un `.pyc` o un directorio de caché no son ficheros del
    proyecto, y contarlos haría el inventario imposible de cerrar.
    """
    salida = subprocess.run(
        ["git", "ls-files", *DIRECTORIOS],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    return [linea for linea in salida.stdout.splitlines() if linea.strip()]


@pytest.fixture(scope="module")
def texto() -> str:
    assert INVENTARIO.is_file(), (
        f"Falta {INVENTARIO.relative_to(RAIZ).as_posix()}. Es lo que sostiene que nada se borre "
        "sin estar cubierto."
    )
    return INVENTARIO.read_text(encoding="utf-8")


class TestElInventarioNoSeQuedaAMedias:

    def test_should_have_a_row_for_every_versioned_file(self, texto: str):
        """Uno por uno, y contra `git ls-files`: un fichero sin fila es un fichero que nadie miró."""
        faltan = [ruta for ruta in _versionados() if _fila_de(texto, ruta) is None]

        assert faltan == [], (
            f"{len(faltan)} ficheros sin fila en el inventario. Los primeros: {faltan[:10]}"
        )

    def test_should_label_every_row(self, texto: str):
        """Cada fila lleva una de las cuatro etiquetas, escrita como el documento declara."""
        sin_etiqueta = []
        for ruta in _versionados():
            fila = _fila_de(texto, ruta)
            if fila is None or not any(f"**{e}**" in fila for e in ETIQUETAS):
                sin_etiqueta.append(ruta)

        assert sin_etiqueta == [], (
            f"{len(sin_etiqueta)} filas sin una de {ETIQUETAS}: {sin_etiqueta[:10]}"
        )

    def test_should_justify_every_row(self, texto: str):
        """Y una justificación, porque «cubierto» sin equivalente concreto no es un cruce.

        El criterio del prompt: las etiquetas «cubierto» citan el equivalente concreto, no «está
        en automation». Se exige una columna final con contenido; que ese contenido sea el
        equivalente correcto lo lee una persona.
        """
        sin_razon = []
        for ruta in _versionados():
            fila = _fila_de(texto, ruta) or ""
            columnas = [c.strip() for c in fila.strip().strip("|").split("|")]
            if len(columnas) < 3 or len(columnas[-1]) < 15:
                sin_razon.append(ruta)

        assert sin_razon == [], (
            f"{len(sin_razon)} filas sin justificación de al menos 15 caracteres: "
            f"{sin_razon[:10]}"
        )

    def test_should_count_what_it_found(self, texto: str):
        """El informe de cierre dice cuántos caen en cada etiqueta, así que el documento también.

        Sin el recuento, «casi todo está cubierto» es una impresión. Con él, es una cifra que se
        puede discutir — y que el siguiente prompt usa para decidir qué mueve.
        """
        for etiqueta in ETIQUETAS:
            assert re.search(
                rf"\*\*{re.escape(etiqueta)}\*\*\s*\|\s*\d+", texto
            ) or re.search(rf"\|\s*\d+\s*\|.*{re.escape(etiqueta)}", texto), (
                f"el inventario no dice cuántos ficheros son «{etiqueta}»"
            )

    def test_should_not_have_moved_anything_yet(self):
        """NIC.1 sólo mira. Si `client_app/app/ui` se hubiera vaciado, el cruce sería sobre nada.

        Es el test que impide que este prompt se convierta en el siguiente por accidente.
        """
        ui = [r for r in _versionados() if r.startswith("client_app/app/ui")]
        servicios = [r for r in _versionados() if r.startswith("client_app/app/services")]

        assert len(ui) > 90, f"sólo quedan {len(ui)} ficheros en app/ui: ¿se movió algo?"
        assert len(servicios) > 70, f"sólo quedan {len(servicios)} en app/services"
