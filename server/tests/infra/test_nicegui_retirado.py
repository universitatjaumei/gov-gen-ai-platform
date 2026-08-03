"""El árbol activo del servidor no tiene NiceGUI (Prompt CAL.1).

`server/app/ui/` eran 21 módulos NiceGUI —el panel de administración y el portal de partner—
que **nadie importaba y nada servía**: `main.py` no los monta, así que eran inalcanzables por
HTTP. Lo único que los mantenía vivos eran tres tests que los importaban para probarlos.

Se movieron enteros a `_legacy_nicegui/` en vez de repartirlos entre borrado y cuarentena: 9
de los 21 se importan entre sí (comparten `admin_layout`, `partner_layout` y el JSON de
traducciones), así que separarlos habría dejado referencias rotas dentro de la propia
cuarentena. Quien migre el portal de partner en Fase 2 los quiere completos o no los quiere.

Este fichero es el guardarraíl de la retirada: sin él, el siguiente `from nicegui import ui`
entra sin que nadie se entere y la Fase 1 vuelve a tener dos interfaces.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SERVIDOR = RAIZ / "server"


def _fuentes(directorio: Path) -> list[Path]:
    if not directorio.is_dir():
        return []
    return [
        f
        for f in directorio.rglob("*.py")
        if "_legacy_nicegui" not in f.parts
        and ".venv" not in f.parts
        and "__pycache__" not in f.parts
    ]


def test_should_have_no_nicegui_imports_in_server_app() -> None:
    culpables = [
        str(f.relative_to(RAIZ))
        for f in _fuentes(SERVIDOR / "app")
        if "from nicegui" in f.read_text(encoding="utf-8", errors="ignore")
        or "import nicegui" in f.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not culpables, (
        f"estos módulos del servidor vuelven a depender de NiceGUI: {culpables}. "
        "La interfaz del servidor es el panel React; dos interfaces significan que una de "
        "las dos se queda sin mantener."
    )


def test_should_have_no_references_to_server_app_ui() -> None:
    """Ni el código ni los tests. Un test que importa código muerto lo mantiene vivo."""
    culpables = []
    for base in (SERVIDOR / "app", SERVIDOR / "tests", RAIZ / "tests"):
        for f in _fuentes(base):
            if f.name == Path(__file__).name:
                continue
            texto = f.read_text(encoding="utf-8", errors="ignore")
            if "server.app.ui" in texto or "from app.ui" in texto:
                culpables.append(str(f.relative_to(RAIZ)))
    assert not culpables, f"siguen apuntando al UI retirado: {culpables}"


def test_should_not_have_the_ui_package_in_the_active_tree() -> None:
    assert not (SERVIDOR / "app" / "ui").exists(), (
        "server/app/ui volvió al árbol activo; su sitio es _legacy_nicegui/ hasta que el "
        "usuario borre la cuarentena al cerrar la Fase 1"
    )


def test_should_keep_the_quarantine_complete() -> None:
    """La cuarentena sirve de referencia: incompleta no sirve de nada.

    Se comprueba que están los dos `layout` y el JSON de traducciones, que son justo las
    piezas compartidas que hacían inseparable el resto.
    """
    cuarentena = RAIZ / "_legacy_nicegui" / "server" / "app" / "ui"
    assert cuarentena.is_dir(), "no se movió el UI a la cuarentena"

    for pieza in ("admin_layout.py", "partner_layout.py", "admin_translations.json"):
        assert (cuarentena / pieza).is_file(), f"falta {pieza} en la cuarentena"


def test_should_have_no_generated_extractors_tracked() -> None:
    """Los extractores los ESCRIBE el runtime; estaban trackeados y volverían a colarse.

    Se comprueba sobre el disco y no con `git ls-files` para que el test no necesite git:
    lo que importa es que los directorios no estén, y el `.gitignore` impide que vuelvan.
    """
    for ruta in (
        RAIZ / "app" / "modules" / "extraccion",
        RAIZ / "client_app" / "app" / "modules" / "extraccion",
    ):
        assert not ruta.exists(), f"{ruta.relative_to(RAIZ)} volvió al árbol"

    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert ".servicios_generados/" in gitignore, (
        "sin la regla en .gitignore, el siguiente arranque del runtime los re-trackea"
    )


def test_should_have_no_legacy_ui_files_in_client_app() -> None:
    ui = RAIZ / "client_app" / "app" / "ui"
    if not ui.is_dir():
        return
    legacy = sorted(f.name for f in ui.glob("*_legacy*.py"))
    legacy += sorted(f.name for f in ui.glob("_legacy_*.py"))
    assert not legacy, (
        f"client_app conserva UI legacy: {legacy}. Son versiones sustituidas y sin "
        "importadores; el pasado lo guarda git."
    )
