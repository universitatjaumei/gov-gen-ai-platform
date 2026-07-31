"""Fixtures de public_graphs: orden de importación de torch + sesión sobre la BD desechable.

Mismo par que el conftest de `tests/modules/agents_hub/`, y por las mismas dos razones:
`db_url` (BD desechable por test) vive en el conftest raíz y aquí solo se añade la sesión.

El import de `langchain_text_splitters` **debe ir primero**: arrastra torch, y en Windows
cargar torch DESPUÉS de abrir una conexión asyncpg aborta el proceso con «Windows fatal
exception: access violation». Diagnosticado en ING.0.5; no reordenar.
"""
from __future__ import annotations

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
