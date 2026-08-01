"""Conftest raíz: ruta del proyecto + la fixture de BD desechable.

`db_url` vive aquí —y no en `tests/modules/agents_hub/`— para que **cualquier** directorio
de tests pueda usarla: es el único lugar autorizado para crear tablas partiendo de
`DATABASE_URL` (lo vigila `tests/infra/test_suite_hygiene.py`). Historia: los tests que
creaban tablas sobre la BD del desarrollador la dejaron dos veces sin esquema del hub y
acumularon organizaciones y chatbots residuales (TST.1/TST.2 en `PROJECT_STATE.md`).

La política de event loops se declara en pyproject.toml
(`asyncio_default_fixture_loop_scope = "function"`), no aquí: el override de la fixture
`event_loop` está deprecado en pytest-asyncio 1.x.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

# __file__ is server/tests/conftest.py → parent.parent.parent is the repo root
sys.path.append(str(Path(__file__).parent.parent.parent))


def _base_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai",
    )


def _psycopg_url(async_url: str, dbname: str) -> str:
    parts = urlsplit(async_url.replace("postgresql+asyncpg", "postgresql"))
    return urlunsplit(parts._replace(path=f"/{dbname}"))


def _sync_url() -> str:
    """DSN síncrono para Alembic. `DATABASE_URL_SYNC` si está, derivado del async si no."""
    url = os.getenv("DATABASE_URL_SYNC")
    if url:
        return url
    return _base_url().replace("postgresql+asyncpg", "postgresql+psycopg2")


@pytest.fixture
def fresh_database():
    """BD vacía con pgvector, para probar la cadena de migraciones con `alembic upgrade`.

    Hermana de `db_url` y aquí por el mismo motivo (TST.2): la usan `tests/infra` y
    `tests/modules/agents_hub/integration`, e importar una fixture de otro módulo de test
    hace que el parámetro del test redefina el nombre importado. Devuelve una URL
    **síncrona**, que es la que consume Alembic.
    """
    import psycopg2

    sync_url = _sync_url()
    admin_dsn = _psycopg_url(sync_url.replace("postgresql+psycopg2", "postgresql"), "postgres")

    try:
        admin = psycopg2.connect(admin_dsn)
    except Exception:  # pragma: no cover - entorno sin BD
        pytest.skip("BD Postgres no disponible")
    admin.autocommit = True

    db_name = f"test_fresh_install_{uuid.uuid4().hex[:12]}"
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{db_name}"')

    fresh_url = urlunsplit(urlsplit(sync_url)._replace(path=f"/{db_name}"))

    # pgvector es requisito de hub_schema (a1b2c3d4e5f6): replicar lo que hace
    # scripts/postgres/init.sql en el contenedor real.
    conn = psycopg2.connect(fresh_url.replace("postgresql+psycopg2", "postgresql"))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.close()

    try:
        yield fresh_url
    finally:
        with admin.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (db_name,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        admin.close()


def _conexion_admin():
    """Conexión a `postgres` para crear y borrar bases. Salta si no hay servidor."""
    import psycopg2

    try:
        admin = psycopg2.connect(_psycopg_url(_base_url(), "postgres"))
    except Exception:  # pragma: no cover - entorno sin BD
        pytest.skip("BD Postgres no disponible")
    admin.autocommit = True
    return admin


@pytest.fixture(scope="session")
def _plantilla_hub() -> str:
    """Nombre de una BD **plantilla** con pgvector y el esquema del hub ya creado (TST.4).

    El esquema se construye UNA vez por sesión de pytest; cada test copia la plantilla con
    `CREATE DATABASE ... TEMPLATE`, que en Postgres es una copia de ficheros y cuesta
    centésimas. Antes cada test ejecutaba `create_all` de 79 tablas más sus índices: **1,3 s
    de setup por test**, que sobre los ~140 tests de integración era prácticamente todo el
    tiempo de ese directorio.

    Con `-n auto` cada worker de xdist tiene su propia sesión y por tanto su propia
    plantilla; los nombres llevan uuid, así que no colisionan.

    La plantilla no puede tener conexiones abiertas cuando alguien la copia: por eso el
    motor se cierra aquí dentro, antes de ceder el nombre.
    """
    import psycopg2

    from server.app.modules.agents_hub.database.base import (
        HubConfigBase,
        HubOperationalBase,
    )

    import server.app.modules.agents_hub.database.config_models  # noqa: F401
    import server.app.modules.agents_hub.database.operational_models  # noqa: F401

    from sqlalchemy import create_engine

    admin = _conexion_admin()
    nombre = f"test_hub_tpl_{uuid.uuid4().hex[:12]}"
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{nombre}"')

    conn = psycopg2.connect(_psycopg_url(_base_url(), nombre))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.close()

    # Motor síncrono a propósito: esta fixture es de sesión y no puede depender del event
    # loop de un test concreto (pytest-asyncio los crea por función).
    sync = create_engine(
        _psycopg_url(_base_url(), nombre).replace("postgresql://", "postgresql+psycopg2://")
    )
    HubConfigBase.metadata.create_all(sync)
    HubOperationalBase.metadata.create_all(sync)
    sync.dispose()

    try:
        yield nombre
    finally:
        with admin.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (nombre,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{nombre}"')
        admin.close()


@pytest.fixture
async def db_url(_plantilla_hub: str):
    """URL de una BD desechable por test, copiada de la plantilla del hub.

    `DATABASE_URL` se usa solo para la conexión de administración que crea y borra la
    BD `test_hub_*`; ningún test escribe en la BD del desarrollador.
    """
    admin = _conexion_admin()

    db_name = f"test_hub_{uuid.uuid4().hex[:12]}"
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{db_name}" TEMPLATE "{_plantilla_hub}"')

    async_url = urlunsplit(urlsplit(_base_url())._replace(path=f"/{db_name}"))

    try:
        yield async_url
    finally:
        with admin.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (db_name,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        admin.close()
        admin.close()
