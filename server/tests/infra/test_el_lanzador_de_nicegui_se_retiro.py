"""El lanzador de la aplicación NiceGUI sale del árbol activo (LEG.5).

El `main.py` de la raíz eran 705 líneas que importaban `nicegui`, las páginas de `client_app`,
`ExtractionService` y `RPAExecutor`: el lanzador de la aplicación de escritorio. LEG.5 lo movió a
la cuarentena `_legacy_nicegui/`, y **NIC.3 la retiró completa el 2026-09-04** junto con
`client_app/`, así que hoy no está en ningún sitio del árbol. Se lee en el historial de git.

**Y `arranque.bat` todavía lo ejecutaba** (`uv run main.py`, opción 3 del menú), así que moverlo sin
tocar el script habría dejado un arranque roto: exactamente el tipo de retirada a medias que
CLAUDE.md prohíbe.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def test_el_main_de_la_raiz_ya_no_esta_en_el_arbol_activo():
    assert not (RAIZ / "main.py").exists()


def test_tampoco_esta_en_una_cuarentena():
    """Este test decía lo contrario: que `_legacy_nicegui/main.py` **tenía** que existir.

    Era correcto mientras la cuarentena fuese la referencia. NIC.3 la retiró, y la referencia pasó
    a ser el historial de git —que viaja con el repositorio y no se puede perder—, así que la
    afirmación se invierte: lo que hay que vigilar ahora es que no vuelva a aparecer un directorio
    de código muerto dentro del árbol.
    """
    assert not (RAIZ / "_legacy_nicegui").exists()


def test_el_script_de_arranque_no_lo_invoca():
    """Un `.bat` que lanza un fichero que no está es peor que un `.bat` sin esa opción."""
    arranque = (RAIZ / "arranque.bat").read_text(encoding="latin-1")

    assert "main.py" not in arranque


def test_el_script_de_arranque_conserva_lo_que_se_usa():
    arranque = (RAIZ / "arranque.bat").read_text(encoding="latin-1")

    assert "uvicorn server.app.main:app" in arranque
    assert "npm run dev" in arranque


#: `import main` o `from main import ...` **al principio de línea**. Un patrón por substring cazaba
#: `from .cli import main` de media docena de librerías del entorno virtual: un guardarraíl con
#: falsos positivos se acaba desactivando, así que se afina en vez de relajarse.
_IMPORTA_EL_LANZADOR = re.compile(r"^\s*(?:import\s+main\b|from\s+main\s+import\b)", re.MULTILINE)


def test_nada_del_arbol_activo_lo_importa():
    """El `grep -r` a cero de CLAUDE.md, como test para que no vuelva por la puerta de atrás."""
    culpables: list[str] = []
    for carpeta in ("server/app", "server/tests", "client_app"):
        raiz = RAIZ / carpeta
        if not raiz.exists():
            continue
        for fichero in raiz.rglob("*.py"):
            ruta = str(fichero)
            if "__pycache__" in ruta or "_legacy" in ruta or ".venv" in ruta:
                continue
            if fichero.name == Path(__file__).name:
                continue  # este test contiene el patrón que busca
            if _IMPORTA_EL_LANZADOR.search(fichero.read_text(encoding="utf-8", errors="ignore")):
                culpables.append(str(fichero.relative_to(RAIZ)))

    assert culpables == [], f"quedan imports del lanzador retirado: {culpables}"
