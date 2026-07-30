"""TST.2 — la suite e2e corre contra una BD desechable, nunca contra la del desarrollador.

Antes de este prompt, `e2e/conftest.py` creaba las tablas del hub sobre `DATABASE_URL` y
`setup_chatbot` dejaba organizaciones y chatbots residuales en la BD de desarrollo (12
acumulados cuando se midió).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text


def _bd_de_desarrollo() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai",
    )
    return url.rsplit("/", 1)[-1]


@pytest.mark.asyncio
async def test_should_run_e2e_against_a_disposable_database(db_engine):
    """El motor de los tests e2e apunta a una `test_hub_*`, no a `DATABASE_URL`."""
    assert db_engine.url.database != _bd_de_desarrollo(), (
        "el motor e2e apunta a la BD del desarrollador"
    )
    assert db_engine.url.database.startswith("test_hub_")

    async with db_engine.connect() as conn:
        actual = (await conn.execute(text("select current_database()"))).scalar()
    assert actual == db_engine.url.database


@pytest.mark.asyncio
async def test_should_leave_no_rows_in_the_dev_database_after_e2e(setup_chatbot, db_engine):
    """`setup_chatbot` escribe en la BD desechable: su chatbot NO existe en la de
    desarrollo. Es la versión por-test del criterio «recuento idéntico antes y
    después», que se verifica además sobre la suite completa en el cierre."""
    from server.app.modules.agents_hub.database.connection import create_async_engine

    dev = create_async_engine()  # DATABASE_URL
    try:
        async with dev.connect() as conn:
            fila = (
                await conn.execute(
                    text("select count(*) from hub_chatbots where id = :i"),
                    {"i": str(setup_chatbot.id)},
                )
            ).scalar()
    finally:
        await dev.dispose()
    assert fila == 0, "el chatbot del test e2e ha aterrizado en la BD de desarrollo"
