"""Fixtures de BD para los tests de agents_hub (integración y evaluación).

**Por qué existe este fichero (hallado el 2026-07-28).** Tres ficheros de
 creaban las tablas del hub con `create_all` sobre `DATABASE_URL` —la BD de
desarrollo— y las destruían con `drop_all` al terminar cada test. Consecuencias
verificadas:

1. **Cualquier ejecución de la suite dejaba la BD de desarrollo sin esquema del hub**,
   sellada en `head` por Alembic pero con cero tablas `hub_*`. Es el estado en el que se
   encontró la BD al arrancar ING.0.1, y el que reapareció al ejecutar la suite justo
   después de repararla.
2. **Diez tests de `test_site_model.py` fallaban en ejecución conjunta y pasaban en
   solitario**: cada test rehacía el esquema completo, así que se pisaban entre ellos.

La fixture `db_url` crea una **base de datos desechable por test** y la borra al final.
Sigue el patrón que ya usaba `tests/infra/test_migrations_fresh_install.py`. Nadie vuelve
a hacer `drop_all` sobre la BD del desarrollador.
"""
from __future__ import annotations

# ── Orden de importación obligatorio, no reordenar ─────────────────────────────
# `langchain_text_splitters` arrastra `sentence_transformers` → torch. En Windows,
# cargar torch DESPUÉS de haber abierto una conexión asyncpg aborta el proceso con
# «Windows fatal exception: access violation»; al revés funciona. Diagnosticado el
# 2026-07-29 reduciéndolo a dos líneas:
#
#     asyncpg connect  →  import langchain_text_splitters   ⇒ access violation
#     import langchain_text_splitters  →  asyncpg connect    ⇒ OK
#
# Es la causa del crash que arrastraba `test_full_pipeline.py` y que bloqueaba
# cualquier test de integración que tocara el chunker. Importarlo aquí, al cargar el
# conftest, garantiza que torch entra antes que cualquier motor de BD.
import langchain_text_splitters  # noqa: F401  ← debe ir primero

import os
import uuid
from urllib.parse import urlsplit, urlunsplit

import pytest


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
    """URL de una BD desechable, con pgvector y las tablas del hub ya creadas."""
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


@pytest.fixture
async def db_session(db_url: str):
    """Sesión sobre la BD desechable. Sin drop_all: la BD entera se borra al final."""
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )

    engine = create_async_engine(db_url)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session
    await engine.dispose()
