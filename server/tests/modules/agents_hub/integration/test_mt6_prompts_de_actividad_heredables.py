"""MT.6 — un municipio puede escribir su propio prompt.

`HubActivityPrompt.activity` era único **global**. Es defendible para una actividad de plataforma
y deja de serlo en cuanto un municipio quiere su propia redacción — que es exactamente lo que esta
tabla existe para permitir, sólo un escalón más arriba de lo que hacía falta.

**La cadena entera son tres niveles y hay que no perder ninguno**: organización → plataforma →
código. El último es el que PRO.2.1 dejó atado y el que más fácil se rompe: el texto del código
**no se copia** a la fila. Copiarlo congelaría el prompt, y mejorarlo en el código no llegaría a
quien ya lo abrió. Añadir un nivel por encima no puede cambiar eso.
"""
from __future__ import annotations

import uuid

import pytest

from server.app.modules.agents_hub.database.config_models import (
    HubActivityPrompt,
    HubOrganizacion,
)
from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
from server.app.modules.redaccion.services.actividades_llm import (
    PROMPT_POR_ACTIVIDAD,
    ActividadLLM,
    resolver_actividad,
)

pytestmark = pytest.mark.asyncio

ACTIVIDAD = ActividadLLM.TRANSFORMACION_ETL


async def _organizacion(session, nombre="Onda") -> HubOrganizacion:
    fila = HubOrganizacion(
        name=f"{nombre} {uuid.uuid4().hex[:6]}", partner_id=f"p-{uuid.uuid4().hex[:6]}"
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _override(session, *, organizacion=None, texto=None, nivel=None):
    fila = HubActivityPrompt(
        activity=str(ACTIVIDAD),
        organizacion_id=organizacion.id if organizacion is not None else None,
        template_text=texto,
        override_tier=nivel,
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


class TestLaCadenaDeTresNiveles:

    async def test_should_override_it_per_organisation(self, db_session):
        una = await _organizacion(db_session)
        await _override(db_session, organizacion=None, texto="El de la plataforma")
        await _override(db_session, organizacion=una, texto="El de Onda")

        resuelto = await LocalConfigProvider(db_session).get_activity_prompt(
            str(ACTIVIDAD), organizacion_id=una.id
        )

        assert resuelto.template_text == "El de Onda"

    async def test_should_inherit_the_platform_prompt(self, db_session):
        """Sin fila propia, la de plataforma. Es lo que hace que el piloto no note MT.6."""
        una = await _organizacion(db_session)
        await _override(db_session, organizacion=None, texto="El de la plataforma", nivel=3)

        resuelto = await LocalConfigProvider(db_session).get_activity_prompt(
            str(ACTIVIDAD), organizacion_id=una.id
        )

        assert resuelto.template_text == "El de la plataforma"
        assert resuelto.override_tier == 3

    async def test_should_not_take_the_prompt_of_another_organisation(self, db_session):
        """**El test que importa.** Un prompt de sistema es la instrucción con la que el modelo
        redacta para un ayuntamiento: llevarse el del vecino no es un texto equivocado, es
        redactar con las reglas de otro."""
        una = await _organizacion(db_session, "Nules")
        otra = await _organizacion(db_session, "Vinaròs")
        await _override(db_session, organizacion=otra, texto="El de Vinaròs")

        resuelto = await LocalConfigProvider(db_session).get_activity_prompt(
            str(ACTIVIDAD), organizacion_id=una.id
        )

        assert resuelto is None, "sin fila propia ni de plataforma, no hay override"

    async def test_should_keep_the_code_default_as_the_last_resort(self, db_session):
        """El tercer nivel, que es el que PRO.2.1 dejó atado y el más fácil de romper: **el
        texto del código no se copia** a ninguna fila. Copiarlo congelaría el prompt, y
        mejorarlo en el código dejaría de llegar a quien ya lo abrió."""
        una = await _organizacion(db_session)

        resuelta = await resolver_actividad(
            ACTIVIDAD, LocalConfigProvider(db_session), organizacion_id=una.id
        )

        assert resuelta.template_text == PROMPT_POR_ACTIVIDAD[ACTIVIDAD]

    async def test_should_let_an_organisation_override_only_the_tier(self, db_session):
        """Los dos campos se heredan por separado: un municipio puede querer el texto de la
        plataforma con un modelo más caro, y forzarle a copiar el texto para cambiar el nivel lo
        congelaría igual que copiarlo del código."""
        una = await _organizacion(db_session)
        await _override(db_session, organizacion=None, texto="El de la plataforma")
        await _override(db_session, organizacion=una, texto=None, nivel=3)

        resuelta = await resolver_actividad(
            ACTIVIDAD, LocalConfigProvider(db_session), organizacion_id=una.id
        )

        assert resuelta.tier == 3
        assert resuelta.template_text == "El de la plataforma"


class TestLaClaveDejaDeSerGlobal:

    async def test_should_let_two_organisations_override_the_same_activity(self, db_session):
        """Con `activity` único global, la segunda organización que quisiera su prompt chocaba
        con la primera."""
        una = await _organizacion(db_session, "Onda")
        otra = await _organizacion(db_session, "Nules")

        await _override(db_session, organizacion=una, texto="El de Onda")
        await _override(db_session, organizacion=otra, texto="El de Nules")

    async def test_should_still_refuse_two_overrides_for_the_same_scope(self, db_session):
        """Lo que la clave protegía sigue protegido, **y en el nivel de plataforma también**: en
        Postgres `NULL != NULL`, así que sin `NULLS NOT DISTINCT` dos filas de plataforma para
        la misma actividad pasarían — y ése es el nivel de las que existen hoy. Dos overrides
        del mismo ámbito serían dos respuestas a una pregunta con una sola."""
        from sqlalchemy.exc import IntegrityError

        await _override(db_session, organizacion=None, texto="Uno")

        with pytest.raises(IntegrityError):
            await _override(db_session, organizacion=None, texto="Otro")
        await db_session.rollback()

    async def test_should_keep_answering_without_an_organisation(self, db_session):
        """Preguntar sin nombrar organización sigue devolviendo el nivel de plataforma, que es
        cómo preguntan los sitios que aún no saben la organización."""
        await _override(db_session, organizacion=None, texto="El de la plataforma")

        resuelto = await LocalConfigProvider(db_session).get_activity_prompt(str(ACTIVIDAD))

        assert resuelto.template_text == "El de la plataforma"
