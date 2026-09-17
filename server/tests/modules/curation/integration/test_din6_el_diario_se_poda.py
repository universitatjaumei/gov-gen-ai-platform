"""DIN.6 — la poda del diario, contra Postgres.

La retención se comprueba aquí y no con dobles porque lo que hay que demostrar es **qué filas
sobreviven**: un doble de sesión que devuelve lo que se le guardó no puede equivocarse al filtrar
por ámbito, y equivocarse al filtrar por ámbito es justo el fallo que importa — si la poda mirara
el sitio en vez del ámbito, la sección que se rastrea cada seis horas se llevaría todas las filas
y borraría la historia de la que se mira una vez a la semana.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

AHORA = datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)


@dataclass
class _Resumen:
    pages_total: int = 0
    pages_new: int = 0
    pages_changed: int = 0
    pages_gone: int = 0
    pages_error: int = 0
    documents_auto_ingested: int = 0
    documents_reingested: int = 0
    documents_auto_retired: int = 0
    pages_blocked_by_findings: int = 0
    findings_retired: int = 0
    truncated: bool = False
    stop_reason: str | None = None
    errors: list = field(default_factory=list)


async def _sitio(db_session, nombre: str):
    from server.app.modules.curation.site_repo import WebSiteRepo

    return await WebSiteRepo(db_session).create(
        organizacion_id=uuid.uuid4(), name=nombre, root_url="https://www.uji.es"
    )


async def _seccion(db_session, site_id, nombre: str):
    from server.app.modules.curation.site_repo import WebSectionRepo

    return await WebSectionRepo(db_session).create(
        site_id=site_id, name=nombre, pattern=f"/{nombre.lower()}"
    )


def _diario(db_session, conservadas: int):
    from server.app.modules.curation.diario import DiarioDePasadas

    @asynccontextmanager
    async def _factoria():
        """La misma sesión del test: el diario abre la suya en producción, y aquí la comparte
        para que lo escrito se pueda leer sin depender del orden de dos transacciones."""
        yield db_session

    return DiarioDePasadas(_factoria, conservadas=conservadas)


async def _anotar(diario, site_id, section_id, etiqueta: str, cuantas: int):
    for i in range(cuantas):
        await diario.registrar(
            site_id=site_id,
            section_id=section_id,
            scope_label=etiqueta,
            started_at=AHORA - timedelta(hours=cuantas - i),
            finished_at=AHORA - timedelta(hours=cuantas - i) + timedelta(minutes=2),
            summary=_Resumen(pages_new=i),
        )


class TestLaPodaDelDiario:

    @pytest.mark.asyncio
    async def test_should_keep_the_last_n_of_each_scope(self, db_session):
        from server.app.modules.agents_hub.database.operational_models import HubCrawlRun

        sitio = await _sitio(db_session, "Portal")
        jornadas = await _seccion(db_session, sitio.id, "Jornadas")
        eventos = await _seccion(db_session, sitio.id, "Eventos")
        diario = _diario(db_session, conservadas=3)

        await _anotar(diario, sitio.id, jornadas.id, "Jornadas", 5)
        await _anotar(diario, sitio.id, eventos.id, "Eventos", 2)

        filas = (
            await db_session.execute(
                select(HubCrawlRun).where(HubCrawlRun.site_id == sitio.id)
            )
        ).scalars().all()

        de_jornadas = [f for f in filas if f.section_id == jornadas.id]
        de_eventos = [f for f in filas if f.section_id == eventos.id]
        assert len(de_jornadas) == 3
        # Las que sobreviven son las **últimas**, no tres cualesquiera.
        assert sorted(f.pages_new for f in de_jornadas) == [2, 3, 4]
        # Y la poda de un ámbito no toca el otro, aunque tenga menos del tope.
        assert len(de_eventos) == 2

    @pytest.mark.asyncio
    async def test_should_not_touch_the_runs_of_another_site(self, db_session):
        from server.app.modules.agents_hub.database.operational_models import HubCrawlRun

        uno = await _sitio(db_session, "Portal uno")
        otro = await _sitio(db_session, "Portal otro")
        diario = _diario(db_session, conservadas=2)

        await _anotar(diario, otro.id, None, "sitio", 2)
        await _anotar(diario, uno.id, None, "sitio", 4)

        del_otro = (
            await db_session.execute(
                select(HubCrawlRun).where(HubCrawlRun.site_id == otro.id)
            )
        ).scalars().all()
        del_uno = (
            await db_session.execute(
                select(HubCrawlRun).where(HubCrawlRun.site_id == uno.id)
            )
        ).scalars().all()

        assert len(del_otro) == 2
        assert len(del_uno) == 2

    @pytest.mark.asyncio
    async def test_should_keep_whole_site_passes_apart_from_the_sections(self, db_session):
        """El ámbito «sitio entero» es un ámbito más: sus pasadas no compiten con las de una
        sección por el mismo cupo."""
        from server.app.modules.agents_hub.database.operational_models import HubCrawlRun

        sitio = await _sitio(db_session, "Portal")
        jornadas = await _seccion(db_session, sitio.id, "Jornadas")
        diario = _diario(db_session, conservadas=2)

        await _anotar(diario, sitio.id, None, "sitio", 3)
        await _anotar(diario, sitio.id, jornadas.id, "Jornadas", 3)

        filas = (
            await db_session.execute(
                select(HubCrawlRun).where(HubCrawlRun.site_id == sitio.id)
            )
        ).scalars().all()

        assert len([f for f in filas if f.section_id is None]) == 2
        assert len([f for f in filas if f.section_id == jornadas.id]) == 2

    @pytest.mark.asyncio
    async def test_should_keep_the_diary_when_its_section_is_deleted(self, db_session):
        """**El diario es historia.** Si borrar una sección se llevara sus pasadas, la pregunta
        «¿qué pasó aquí?» se quedaría sin respuesta justo cuando alguien deshace algo. La fila
        pierde el enlace y conserva la etiqueta."""
        from server.app.modules.agents_hub.database.operational_models import HubCrawlRun
        from server.app.modules.curation.site_repo import WebSectionRepo

        sitio = await _sitio(db_session, "Portal")
        jornadas = await _seccion(db_session, sitio.id, "Jornadas")
        await _anotar(_diario(db_session, conservadas=50), sitio.id, jornadas.id, "Jornadas", 1)

        await WebSectionRepo(db_session).delete(jornadas.id)

        filas = (
            await db_session.execute(
                select(HubCrawlRun).where(HubCrawlRun.site_id == sitio.id)
            )
        ).scalars().all()

        assert len(filas) == 1
        assert filas[0].section_id is None
        assert filas[0].scope_label == "Jornadas"

    @pytest.mark.asyncio
    async def test_should_store_the_errors_as_text(self, db_session):
        from server.app.modules.agents_hub.database.operational_models import HubCrawlRun

        sitio = await _sitio(db_session, "Portal")
        diario = _diario(db_session, conservadas=50)

        await diario.registrar(
            site_id=sitio.id,
            section_id=None,
            scope_label="sitio",
            started_at=AHORA,
            finished_at=AHORA,
            summary=_Resumen(errors=["auto-ingest x: revento", "retirada y: revento"]),
        )

        fila = (
            await db_session.execute(
                select(HubCrawlRun).where(HubCrawlRun.site_id == sitio.id)
            )
        ).scalar_one()

        # Los errores, tal cual: un contador diría cuántos y no cuáles.
        assert fila.errors == ["auto-ingest x: revento", "retirada y: revento"]
