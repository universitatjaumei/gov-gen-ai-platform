"""Fixtures de agents_hub: orden de importación de torch + sesión sobre la BD desechable.

La fixture `db_url` (BD desechable por test) vive en el conftest raíz `tests/conftest.py`
para que todos los directorios puedan usarla; aquí solo se añade `db_session` y el orden
de importación que exige Windows.
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

import pytest


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
