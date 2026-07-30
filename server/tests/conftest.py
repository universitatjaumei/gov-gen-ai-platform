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


@pytest.fixture
async def db_url():
    """URL de una BD desechable por test, con pgvector y las tablas del hub creadas.

    `DATABASE_URL` se usa solo para la conexión de administración que crea y borra la
    BD `test_hub_*`; ningún test escribe en la BD del desarrollador.
    """
    import psycopg2

    from server.app.modules.agents_hub.database.base import (
        HubConfigBase,
        HubOperationalBase,
    )
    from server.app.modules.agents_hub.database.connection import create_async_engine

    import server.app.modules.agents_hub.database.config_models  # noqa: F401
    import server.app.modules.agents_hub.database.operational_models  # noqa: F401

    base = _base_url()
    admin_dsn = _psycopg_url(base, "postgres")
    try:
        admin = psycopg2.connect(admin_dsn)
    except Exception:  # pragma: no cover - entorno sin BD
        pytest.skip("BD Postgres no disponible")
    admin.autocommit = True

    db_name = f"test_hub_{uuid.uuid4().hex[:12]}"
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{db_name}"')

    conn = psycopg2.connect(_psycopg_url(base, db_name))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.close()

    async_url = urlunsplit(urlsplit(base)._replace(path=f"/{db_name}"))
    engine = create_async_engine(async_url)
    async with engine.begin() as db:
        await db.run_sync(HubConfigBase.metadata.create_all)
        await db.run_sync(HubOperationalBase.metadata.create_all)
    await engine.dispose()

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
