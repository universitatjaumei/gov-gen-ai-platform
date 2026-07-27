"""Regresión 11.2 — `alembic upgrade head` debe completar sobre una BD vacía.

Reproduce exactamente lo que hace el servicio `migrate` de docker-compose.prod.yml
en una instalación nueva. Antes de este fix, la cadena fallaba en
d4e5f6a7b8c9_hub_ingestion_language (ALTER TABLE sobre `hub_ingestion_sources`,
una tabla que ninguna migración crea — ver PROJECT_STATE.md 2026-07-15).

Requiere un servidor Postgres accesible (usa las mismas credenciales que
DATABASE_URL_SYNC) con permiso CREATEDB; si no está disponible, se salta.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import pytest

_SERVER_ROOT = Path(__file__).parent.parent.parent


def _sync_url() -> str:
    url = os.environ.get("DATABASE_URL_SYNC")
    if url:
        return url
    async_url = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai"
    )
    return async_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


def _admin_dsn_and_dbname(sync_url: str) -> tuple[str, str]:
    """DSN psycopg2 (sin el prefijo SQLAlchemy) apuntando a `postgres`, + el nombre de BD original."""
    parts = urlsplit(sync_url.replace("postgresql+psycopg2", "postgresql"))
    dbname = parts.path.lstrip("/")
    admin_parts = parts._replace(path="/postgres")
    return urlunsplit(admin_parts), dbname


@pytest.fixture
def fresh_database():
    sync_url = _sync_url()
    admin_dsn, _ = _admin_dsn_and_dbname(sync_url)

    try:
        admin_conn = psycopg2.connect(admin_dsn)
    except Exception:  # pragma: no cover - entorno sin BD
        pytest.skip("BD Postgres no disponible")

    admin_conn.autocommit = True
    db_name = f"test_fresh_install_{uuid.uuid4().hex[:12]}"

    with admin_conn.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{db_name}"')

    parts = urlsplit(sync_url)
    fresh_url = urlunsplit(parts._replace(path=f"/{db_name}"))

    # pgvector es requisito de hub_schema (a1b2c3d4e5f6); replicar lo que hace
    # scripts/postgres/init.sql en el contenedor real.
    fresh_conn = psycopg2.connect(fresh_url.replace("postgresql+psycopg2", "postgresql"))
    fresh_conn.autocommit = True
    with fresh_conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    fresh_conn.close()

    yield fresh_url

    with admin_conn.cursor() as cur:
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (db_name,),
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    admin_conn.close()


def test_alembic_upgrade_head_succeeds_on_empty_database(fresh_database: str) -> None:
    env = {**os.environ, "DATABASE_URL_SYNC": fresh_database}

    # `python -m alembic` y no `alembic`: el ejecutable de consola solo está en
    # el PATH con el venv activado, y en Windows sin activar el test moría con
    # FileNotFoundError en lugar de comprobar las migraciones.
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_SERVER_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        "alembic upgrade head falló sobre una BD vacía (regresión 11.2):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
