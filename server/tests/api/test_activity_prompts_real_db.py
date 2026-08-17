"""PRO.2.1 contra base de datos real: el override se guarda y se lee.

El doble de sesión de `test_activity_prompts_router.py` no reproduce `expire_on_commit`, y
justo por eso el primer intento de guardar desde la pantalla dio un **500 con
`MissingGreenlet`**: el endpoint leía `fila.template_text` **después** del `commit()`, con los
atributos ya expirados. Es el mismo patrón que VER.4 encontró cinco veces en este módulo, y
sólo se ve con una sesión de verdad.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from server.app.core.auth.models import UserInfo
from server.app.routers.hub_activity_prompts_router import (
    ActivityPromptUpdate,
    list_activity_prompts,
    reset_activity_prompt,
    update_activity_prompt,
)

pytestmark = pytest.mark.asyncio

_ADMIN = UserInfo(user_id="1", email="fabra@uji.es", role="superadmin")


async def test_should_guardar_y_leer_el_override_con_sesion_real(db_url) -> None:
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            await session.execute(
                text("DELETE FROM hub_activity_prompts WHERE activity = :a"),
                {"a": "propuesta_de_script"},
            )
            await session.commit()

            guardado = await update_activity_prompt(
                activity="propuesta_de_script",
                body=ActivityPromptUpdate(override_tier=3, template_text=None),
                user=_ADMIN,
                session=session,
            )

            # Lo que rompía: leer la fila después del commit.
            assert guardado.effective_tier == 3
            assert guardado.tier_source == "override"
            assert guardado.template_text is None
            assert guardado.text_source == "codigo"

            listado = await list_activity_prompts(user=_ADMIN, session=session)
            propuesta = next(a for a in listado if a.activity == "propuesta_de_script")
            assert propuesta.effective_tier == 3

            vuelta = await reset_activity_prompt(
                activity="propuesta_de_script", user=_ADMIN, session=session
            )
            assert vuelta.effective_tier == 2
            assert vuelta.tier_source == "codigo"
    finally:
        await engine.dispose()


async def test_should_guardar_un_texto_propio_y_volver_atras(db_url) -> None:
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            await session.execute(
                text("DELETE FROM hub_activity_prompts WHERE activity = :a"),
                {"a": "auditoria_de_script"},
            )
            await session.commit()

            con_texto = await update_activity_prompt(
                activity="auditoria_de_script",
                body=ActivityPromptUpdate(
                    override_tier=None, template_text="Di sólo si el script hace lo pedido."
                ),
                user=_ADMIN,
                session=session,
            )
            assert con_texto.text_source == "override"
            assert con_texto.template_text == "Di sólo si el script hace lo pedido."
            assert con_texto.effective_tier == 3, "el nivel sigue siendo el del código"

            # Un texto en blanco significa «usa el del código», no «prompt vacío».
            en_blanco = await update_activity_prompt(
                activity="auditoria_de_script",
                body=ActivityPromptUpdate(override_tier=None, template_text="   "),
                user=_ADMIN,
                session=session,
            )
            assert en_blanco.text_source == "codigo"
            assert en_blanco.template_text is None

            await reset_activity_prompt(
                activity="auditoria_de_script", user=_ADMIN, session=session
            )
    finally:
        await engine.dispose()


async def test_should_resolver_el_servicio_con_el_override_guardado(db_url) -> None:
    """La prueba que cierra el círculo: lo guardado cambia lo que se resuelve."""
    from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
    from server.app.modules.redaccion.services.actividades_llm import (
        ActividadLLM,
        resolver_actividad,
    )

    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            await update_activity_prompt(
                activity="propuesta_de_script",
                body=ActivityPromptUpdate(override_tier=1, template_text="Escribe y calla."),
                user=_ADMIN,
                session=session,
            )

            resuelta = await resolver_actividad(
                ActividadLLM.PROPUESTA_DE_SCRIPT, LocalConfigProvider(session)
            )

            assert resuelta.tier == 1
            assert resuelta.template_text == "Escribe y calla."

            await reset_activity_prompt(
                activity="propuesta_de_script", user=_ADMIN, session=session
            )
            de_vuelta = await resolver_actividad(
                ActividadLLM.PROPUESTA_DE_SCRIPT, LocalConfigProvider(session)
            )
            assert de_vuelta.tier == 2
            assert de_vuelta.origen_del_texto == "codigo"
    finally:
        await engine.dispose()


async def test_should_tener_la_actividad_una_sola_fila(db_url) -> None:
    """Una actividad, un override: guardar dos veces actualiza, no duplica."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            for nivel in (2, 3):
                await update_activity_prompt(
                    activity="propuesta_de_script",
                    body=ActivityPromptUpdate(override_tier=nivel, template_text=None),
                    user=_ADMIN,
                    session=session,
                )

            cuantas = await session.execute(
                text(
                    "SELECT count(*) FROM hub_activity_prompts WHERE activity = :a"
                ),
                {"a": "propuesta_de_script"},
            )
            assert cuantas.scalar() == 1

            await reset_activity_prompt(
                activity="propuesta_de_script", user=_ADMIN, session=session
            )
    finally:
        await engine.dispose()
