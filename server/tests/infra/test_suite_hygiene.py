"""Higiene de la suite de tests (TST.1) — guardarraíles contra el estado filtrado.

Origen: 10 tests de `test_site_model.py` fallaban en ejecución conjunta con `unit/` y
pasaban en solitario. Tras falsar la hipótesis del `event_loop` con instrumentación a
nivel de motor, la causa real resultó ser esto:

    WebSiteRepo.create = AsyncMock(return_value=site)     # test_hub_sites_router.py

Una asignación de mock **sobre la clase** que nadie restauraba: desde ese test en
adelante, `create` no ejecutaba ni un INSERT y devolvía siempre el mismo objeto
desanclado, y todo test posterior que insertara una página contra ese sitio fantasma
reventaba con una violación de FK. CI no lo veía porque ejecutaba `unit/` e
`integration/` en invocaciones separadas.

Estos tests hacen estructuralmente imposible la recaída. Son escaneos estáticos, como
los guardarraíles de frontera edge/cloud ya existentes en el repo.
"""
from __future__ import annotations

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent.parent
SERVER = TESTS.parent

# Asignación a atributo de CLASE (receptor con mayúscula inicial) de un Mock. Las
# asignaciones sobre instancias minúsculas (`session.flush = AsyncMock()`) son locales
# al test y se permiten.
_MOCK_SOBRE_CLASE = re.compile(
    r"^\s*[A-Z]\w*\.\w+\s*=\s*(?:mock\.)?(?:Async|Magic|NonCallable)?Mock\(", re.MULTILINE
)
_OVERRIDE_EVENT_LOOP = re.compile(
    r"^\s*def\s+event_loop\s*\(", re.MULTILINE
)


def _ficheros_de_test():
    return [p for p in TESTS.rglob("*.py") if p.name != Path(__file__).name]


def test_should_not_assign_mocks_to_class_attributes():
    """La causa real de TST.1. Un mock sobre la clase sobrevive al test que lo puso."""
    infractores = []
    for path in _ficheros_de_test():
        texto = path.read_text(encoding="utf-8", errors="replace")
        for m in _MOCK_SOBRE_CLASE.finditer(texto):
            linea = texto[: m.start()].count("\n") + 1
            infractores.append(f"{path.relative_to(SERVER)}:{linea}: {m.group(0).strip()}")
    assert infractores == [], (
        "Mock asignado a un atributo de clase; usa monkeypatch.setattr o "
        "unittest.mock.patch.object como context manager, que restauran solos:\n  "
        + "\n  ".join(infractores)
    )


def test_should_not_override_event_loop_fixture_anywhere():
    """El override de `event_loop` está deprecado en pytest-asyncio 1.x. La política de
    loops se declara en pyproject, no en una fixture."""
    infractores = []
    for path in TESTS.rglob("conftest.py"):
        texto = path.read_text(encoding="utf-8", errors="replace")
        if _OVERRIDE_EVENT_LOOP.search(texto):
            infractores.append(str(path.relative_to(SERVER)))
    assert infractores == [], f"fixture event_loop sobreescrita en: {infractores}"


def test_should_declare_asyncio_fixture_loop_scope_in_config():
    """Sin esto pytest arranca con `asyncio_default_fixture_loop_scope=None` y su
    warning de deprecación en cada ejecución."""
    pyproject = (SERVER / "pyproject.toml").read_text(encoding="utf-8")
    assert 'asyncio_default_fixture_loop_scope = "function"' in pyproject


# ───────────────────────── TST.2: la BD del desarrollador es intocable ─────────────────────────

# Único lugar autorizado para crear tablas partiendo de DATABASE_URL: la fixture de BD
# desechable. Usa DATABASE_URL solo para la conexión de administración con la que crea
# y borra bases `test_hub_*`.
_FIXTURE_DESECHABLE = "tests/conftest.py"


def test_should_have_no_test_fixture_calling_drop_all():
    """`drop_all` sobre la BD del desarrollador fue lo que la dejó sin esquema del hub
    dos veces (2026-07-28). La fixture desechable no lo necesita: borra la BD entera."""
    infractores = []
    for path in _ficheros_de_test():
        # Llamadas reales (`X.metadata.drop_all`), no menciones en docstrings.
        if "metadata.drop_all" in path.read_text(encoding="utf-8", errors="replace"):
            infractores.append(str(path.relative_to(SERVER)))
    assert infractores == [], f"drop_all en tests: {infractores}"


def test_should_have_no_test_creating_tables_on_the_dev_database():
    """TST.2: la suite e2e creaba tablas sobre DATABASE_URL —la BD del desarrollador—
    y dejó 12 chatbots residuales. Crear tablas partiendo de DATABASE_URL solo puede
    hacerlo la fixture desechable; sqlite en memoria queda fuera de la regla."""
    infractores = []
    for path in _ficheros_de_test():
        relativa = path.relative_to(SERVER).as_posix()
        if relativa == _FIXTURE_DESECHABLE:
            continue
        texto = path.read_text(encoding="utf-8", errors="replace")
        if "create_all" in texto and "DATABASE_URL" in texto:
            infractores.append(relativa)
    assert infractores == [], (
        "create_all sobre DATABASE_URL fuera de la fixture desechable; usa las "
        f"fixtures db_url/db_session: {infractores}"
    )


# ───────────────────────── TST.3: sin tests de módulos que ya no existen ─────────────────────────

_IMPORT_DE_MODULO = re.compile(
    r"(?:from|import)\s+server\.app\.modules\.(?P<paquete>[A-Za-z_][A-Za-z0-9_]*)"
)


def test_should_not_import_nonexistent_project_modules():
    """`modules/brain` se retiró y quedaron tres tests-smoke importándolo: 3 fallos que
    llevaban meses «inventariados» y que había que recordar filtrar en cada cierre. Un
    fallo que se filtra a mano deja de ser información. Esto detecta la próxima retirada
    que deje tests huérfanos."""
    modules = SERVER / "app" / "modules"
    infractores = []
    for path in _ficheros_de_test():
        texto = path.read_text(encoding="utf-8", errors="replace")
        for m in _IMPORT_DE_MODULO.finditer(texto):
            paquete = m.group("paquete")
            if not (modules / paquete).is_dir():
                linea = texto[: m.start()].count("\n") + 1
                infractores.append(
                    f"{path.relative_to(SERVER)}:{linea}: server.app.modules.{paquete}"
                )
    assert infractores == [], (
        "tests importando módulos del proyecto que no existen en disco:\n  "
        + "\n  ".join(infractores)
    )
