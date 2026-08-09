"""Fixtures de curation: orden de importación de torch + sesión sobre la BD desechable.

Copia deliberada de `tests/modules/agents_hub/conftest.py`: los tests de integración de
curation siguen usando el motor de conexión de `agents_hub.database` (las entidades ORM
—`HubWebSite`, `HubCrawledPage`, `HubCorpusSelection`, `HubContentFinding`— se quedan en
`operational_models.py`, CUR.1 no toca el esquema), así que necesitan la misma fixture
`db_session` y el mismo orden de importación que exige Windows.
"""
from __future__ import annotations

# ── Orden de importación obligatorio, no reordenar ─────────────────────────────
# Ver tests/modules/agents_hub/conftest.py: cargar torch después de abrir una conexión
# asyncpg aborta el proceso en Windows con «access violation».
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
