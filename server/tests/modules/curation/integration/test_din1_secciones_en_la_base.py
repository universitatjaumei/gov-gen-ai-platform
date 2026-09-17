"""DIN.1 — las dos restricciones de `hub_web_sections`, comprobadas por Postgres.

Lo que la base tiene que hacer cumplir no se puede probar leyendo el modelo: un
`CheckConstraint` declarado y no migrado pasa cualquier test de introspección y falla al
guardar. Aquí se escribe de verdad.

**Desviación documentada respecto al prompt DIN.1**: el prompt pedía estos dos tests dentro de
`unit/test_din1_secciones.py`. Ningún test de `unit/` abre sesión contra Postgres en este
repositorio, y meter el primero cambiaría lo que significa ejecutar ese directorio. Los nueve
tests puros del prompt siguen en el fichero que él nombra.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError


async def _sitio(db_session, nombre: str = "Portal"):
    from server.app.modules.curation.site_repo import WebSiteRepo

    return await WebSiteRepo(db_session).create(
        organizacion_id=uuid.uuid4(),
        name=nombre,
        root_url="https://www.uji.es",
    )


class TestHubWebSection:

    @pytest.mark.asyncio
    async def test_should_default_mode_to_manual_when_nobody_says_otherwise(self, db_session):
        from server.app.modules.curation.site_repo import WebSectionRepo

        sitio = await _sitio(db_session)
        seccion = await WebSectionRepo(db_session).create(
            site_id=sitio.id, name="Jornadas", pattern="/jornadas"
        )

        assert seccion.mode == "manual"
        assert seccion.pattern_kind == "path_prefix"
        assert seccion.is_active is True
        assert seccion.crawl_interval_hours is None
        assert seccion.criteria_json is None
        assert seccion.last_crawled_at is None

    @pytest.mark.asyncio
    async def test_should_refuse_two_sections_with_the_same_name_in_one_site(self, db_session):
        """Dos secciones homónimas en un sitio son un error de alta: quien cura no podría
        distinguirlas en la lista ni en el diario de pasadas."""
        from server.app.modules.curation.site_repo import WebSectionRepo

        sitio = await _sitio(db_session)
        repo = WebSectionRepo(db_session)
        await repo.create(site_id=sitio.id, name="Jornadas", pattern="/jornadas")

        with pytest.raises(IntegrityError):
            await repo.create(site_id=sitio.id, name="Jornadas", pattern="/jornades")

    @pytest.mark.asyncio
    async def test_should_allow_the_same_name_in_another_site(self, db_session):
        """La unicidad es por sitio: dos portales pueden tener cada uno sus «Jornadas»."""
        from server.app.modules.curation.site_repo import WebSectionRepo

        uno = await _sitio(db_session, "Portal uno")
        otro = await _sitio(db_session, "Portal otro")
        repo = WebSectionRepo(db_session)

        primera = await repo.create(site_id=uno.id, name="Jornadas", pattern="/jornadas")
        segunda = await repo.create(site_id=otro.id, name="Jornadas", pattern="/jornadas")

        assert primera.id != segunda.id

    @pytest.mark.asyncio
    async def test_should_refuse_a_mode_the_code_does_not_consume(self, db_session):
        """`mode` sí lleva `CheckConstraint`: son dos valores estables con consumidor en el
        código (DIN.4 decide por él si retira o avisa), como `nivell_acces`. Los criterios de
        juicio **no** lo llevan: son vocabulario que crecerá."""
        from server.app.modules.agents_hub.database.operational_models import HubWebSection

        sitio = await _sitio(db_session)
        db_session.add(
            HubWebSection(
                site_id=sitio.id, name="Jornadas", pattern="/jornadas", mode="semiautomatico"
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_should_list_and_deactivate_the_sections_of_a_site(self, db_session):
        from server.app.modules.curation.site_repo import WebSectionRepo

        sitio = await _sitio(db_session)
        otro = await _sitio(db_session, "Portal otro")
        repo = WebSectionRepo(db_session)
        jornadas = await repo.create(site_id=sitio.id, name="Jornadas", pattern="/jornadas")
        await repo.create(site_id=sitio.id, name="Eventos", pattern="/eventos")
        await repo.create(site_id=otro.id, name="Ajena", pattern="/ajena")

        del_sitio = await repo.list_by_site(sitio.id)
        assert {s.name for s in del_sitio} == {"Jornadas", "Eventos"}

        await repo.update(jornadas.id, is_active=False)
        activas = await repo.list_by_site(sitio.id, only_active=True)
        assert {s.name for s in activas} == {"Eventos"}
