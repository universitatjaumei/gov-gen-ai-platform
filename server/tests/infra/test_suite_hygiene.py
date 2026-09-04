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
    hacerlo la fixture desechable; sqlite en memoria queda fuera de la regla.

    Afinado en RAG.3 a `metadata.create_all`, igual que ya lo estaba el guardarraíl de
    `drop_all` de arriba: la versión por substring marcaba un fichero que solo mencionaba
    `create_all` en su docstring —explicando por qué los índices tienen que estar en el ORM
    y no solo en la migración— y pasaba `DATABASE_URL_SYNC` a Alembic sobre una BD
    `test_fresh_install_*`. Un guardarraíl que da falsos positivos se acaba desactivando, y
    entonces deja de proteger lo que venía a proteger.

    **`metadata.create_all` y no `create_all(`**: el patrón de los infractores originales
    era `await conn.run_sync(Base.metadata.create_all)`, pasando el método como callable y
    por tanto SIN paréntesis. Filtrar por la llamada con paréntesis habría desarmado el
    guardarraíl en vez de afinarlo.
    """
    infractores = []
    for path in _ficheros_de_test():
        relativa = path.relative_to(SERVER).as_posix()
        if relativa == _FIXTURE_DESECHABLE:
            continue
        texto = path.read_text(encoding="utf-8", errors="replace")
        if "metadata.create_all" in texto and "DATABASE_URL" in texto:
            infractores.append(relativa)
    assert infractores == [], (
        "create_all sobre DATABASE_URL fuera de la fixture desechable; usa las "
        f"fixtures db_url/db_session: {infractores}"
    )


# ──────────── LEG.3: ningún test abre sesión sobre la BD del desarrollador ────────────

#: Abrir una sesión o una conexión sobre `server_engine` es escribir en la base de datos del
#: desarrollador, que es lo que hacía `tests/test_prompts.py`: pasaba aislado y fallaba en la
#: suite paralela, y el servidor sembrando al arrancar completaba la colisión. **Importar** el
#: símbolo sí se permite: hay un test-smoke que sólo comprueba que el motor existe, y prohibirlo
#: sería un falso positivo, que es como se desactivan los guardarraíles.
_SESION_SOBRE_EL_MOTOR_REAL = re.compile(
    r"(?:AsyncSession|Session)\s*\(\s*server_engine|server_engine\s*\.\s*(?:begin|connect)\s*\("
)


def test_should_have_no_test_opening_a_session_on_the_developer_database():
    infractores = []
    for path in _ficheros_de_test():
        texto = path.read_text(encoding="utf-8", errors="replace")
        for m in _SESION_SOBRE_EL_MOTOR_REAL.finditer(texto):
            linea = texto[: m.start()].count("\n") + 1
            infractores.append(f"{path.relative_to(SERVER)}:{linea}: {m.group(0).strip()}")
    assert infractores == [], (
        "tests abriendo sesión sobre `server_engine` —la BD del desarrollador—; usa las "
        "fixtures db_url/db_session, que trabajan sobre una base desechable:\n  "
        + "\n  ".join(infractores)
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


# ──────── Ningún test construye su propio motor sobre la BD del desarrollador ────────

#: El guardarraíl de arriba vigila `server_engine`, y por eso no vio venir el otro camino a la
#: misma base: leer `DATABASE_URL` del entorno y construirse un engine con ella.
#: `test_acs_issues_jwt_and_redirects` hacía exactamente eso —pedía el fixture `db`, que prepara
#: una BD desechable, y acto seguido lo ignoraba—, así que en local pasaba contra el Postgres del
#: desarrollador y le dejaba una fila de usuario real por ejecución: 97 acumuladas cuando se
#: descubrió. En CI, donde no se ejecutan las migraciones, moría con
#: `relation "superadminaccount" does not exist`.
#:
#: **`DATABASE_URL` y no `DATABASE_URL_`**: la comilla de cierre es obligatoria en el patrón.
#: Sin ella esto cazaría también `DATABASE_URL_SYNC`, que dos tests de migraciones leen con
#: motivo —Alembic necesita el DSN síncrono— y un guardarraíl con falsos positivos se desactiva.
#:
#: **Sólo la lectura.** `os.environ.setdefault("DATABASE_URL", ...)` es una escritura y queda
#: fuera a propósito: `test_openapi_export.py` la usa para no conectar a ninguna parte.
_DSN_DEL_ENTORNO = re.compile(
    r"""(?:environ\.get|getenv)\s*\(\s*["']DATABASE_URL["']"""
    r"""|environ\s*\[\s*["']DATABASE_URL["']\s*\]"""
)


#: Quién puede leerlo, y por qué. Lista explícita y no una heurística: distinguir «lo lee para
#: escribir en esa base» de «lo lee para otra cosa» exige seguir la variable, y una heurística
#: que lo intente dará los falsos positivos que desactivan el guardarraíl. Con una lista, añadir
#: un caso obliga a justificarlo en el diff, que es justo la conversación que se quiere tener.
_PUEDEN_LEER_EL_DSN = {
    # La fixture desechable: `DATABASE_URL` es su conexión de administración para crear y
    # borrar las bases `test_hub_*`. Sin leerlo no hay base desechable que dar a nadie.
    _FIXTURE_DESECHABLE,
    # Igual que la anterior, pero para su propia BD con las migraciones aplicadas: deriva el
    # DSN de administración y crea una base aparte.
    "tests/infra/test_bootstrap_seed.py",
    # Inspecciona el esquema real ya migrado —sólo lectura, y se salta si no hay BD—: es lo
    # que comprueba que el renombrado de tablas se aplicó de verdad.
    "tests/api/test_migration_rename.py",
    # Igual que la anterior, y por eso entra: censa el esquema real para comprobar que ninguna
    # tabla sobra. Sólo lectura —`information_schema` y `count(*)`— y se salta si no hay BD. No
    # puede usar la fixture desechable: una base recién creada tiene exactamente las tablas
    # declaradas, así que el censo pasaría siempre y no vigilaría nada. Lo que busca es
    # justamente la diferencia entre lo declarado y lo que se acumuló en una base de verdad
    # (BD.1: eran 36 tablas, residuo del «Brain» de AutomatIA).
    "tests/infra/test_bd1_no_sobran_tablas_sin_dueno.py",
    # Lo lee para AFIRMAR QUE NO ES ESA: es el test que vigila esta misma regla sobre la
    # suite e2e (TST.2). Prohibírselo dejaría sin guardián al guardián.
    "tests/modules/agents_hub/e2e/test_db_isolation.py",
}


def test_should_have_no_test_building_an_engine_from_the_environment_dsn():
    infractores = []
    for path in _ficheros_de_test():
        relativa = path.relative_to(SERVER).as_posix()
        if relativa in _PUEDEN_LEER_EL_DSN:
            continue
        texto = path.read_text(encoding="utf-8", errors="replace")
        for m in _DSN_DEL_ENTORNO.finditer(texto):
            linea = texto[: m.start()].count("\n") + 1
            infractores.append(f"{relativa}:{linea}: {m.group(0).strip()}")
    assert infractores == [], (
        "tests leyendo `DATABASE_URL` del entorno para construirse un motor —esa es la BD "
        "del desarrollador—; pide la fixture `db_url`, que da una base desechable:\n  "
        + "\n  ".join(infractores)
    )
