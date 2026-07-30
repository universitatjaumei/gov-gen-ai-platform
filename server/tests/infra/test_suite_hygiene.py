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
