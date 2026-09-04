import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))


@pytest.fixture(scope="session")
def event_loop():
    """Loop de eventos para tests async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_server_db():
    """BBDD del Brain en memoria para tests (SQLite en memoria)"""
    from sqlmodel import SQLModel
    from sqlalchemy.ext.asyncio import create_async_engine

    from sqlalchemy.pool import StaticPool

    # Crear engine en memoria para tests (aislado de la BD real)
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )

    # Importar modelos para registrar metadata
    import server.app.database.models  # noqa: F401

    # Crear todas las tablas
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Parchear el engine global en TODOS los módulos que lo usan
    import server.app.database.db as db_module
    import server.app.services.ai_brain as brain_module

    original_db_engine = db_module.server_engine
    original_brain_engine = brain_module.server_engine

    db_module.server_engine = test_engine
    brain_module.server_engine = test_engine

    yield test_engine

    # Restaurar engines originales y limpiar
    db_module.server_engine = original_db_engine
    brain_module.server_engine = original_brain_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await test_engine.dispose()


# `test_client_db` y `db_session` construían la BD SQLite del cliente NiceGUI a partir de
# `client_app.app.database.db.client_engine`. NIC.3 retiró `client_app/` completo, así que las dos
# fixtures se fueron con él. Los cinco ficheros de `tests/unit/` que pedían `db_session`
# —licencias, partners, escalado de scripts, semillas— ya estaban en rojo antes de esta retirada:
# importan `server.app.services.ai_brain`, que tampoco existe. **Su destino lo decide NIC.4**, que
# es el prompt que mide el entorno legacy de la raíz entero; aquí no se inventa un sustituto,
# porque una fixture que finge una BD que no existe esconde que esos tests no prueban nada.


@pytest.fixture(scope="function")
async def server_db_session(test_server_db):
    """Session for Server DB (Brain)"""
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(
        test_server_db, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session



@pytest.fixture
def temp_execution_dir(tmp_path: Path) -> Path:
    """Directorio temporal para ejecuciones de test"""
    exec_dir = tmp_path / "executions" / "test_001"
    (exec_dir / "input").mkdir(parents=True)
    (exec_dir / "scripts").mkdir(parents=True)
    (exec_dir / "output").mkdir(parents=True)
    return exec_dir
