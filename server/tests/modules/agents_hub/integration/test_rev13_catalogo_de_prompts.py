"""REV.13 — todos los prompts en un sitio, con su ámbito a la vista.

Hay dos pantallas y el usuario preguntó, con razón, por qué. La respuesta es que son **dos
modelos distintos**, no el mismo dato en dos sitios:

- `HubPromptTemplate` cuelga de **un chatbot** (`chatbot_id` NOT NULL), va por idioma y está
  versionada. Por eso vive bajo el módulo Chatbots.
- `HubActivityPrompt` tiene `activity` **único global**, sin organización ni chatbot. Es
  configuración de plataforma.

Lo que faltaba no era unificar las tablas —serían dos cosas distintas metidas en una— sino
**poder verlas juntas**: un catálogo de sólo lectura que diga de qué es cada prompt, y desde el
que se llegue a editar cada uno por su camino.

**El catálogo acota por organización**, que es lo que hace que este endpoint no sea un agujero:
las plantillas cuelgan de chatbots, los chatbots de organizaciones, y un administrador no puede
ver las de otra.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import server.app.main  # noqa: F401

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.config_models import (
    HubChatbot,
    HubLLMConfig,
    HubOrganizacion,
    HubProvider,
    HubPromptTemplate,
)
from server.app.routers.hub_prompts_catalog_router import router


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def _cliente(session, principal: UserInfo) -> AsyncClient:
    async def _sesion():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: principal
    app.dependency_overrides[get_session] = _sesion
    app.include_router(router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _principal(role="superadmin", organizacion_ids=()) -> UserInfo:
    return UserInfo(
        user_id="u-1",
        email="admin@test.com",
        role=role,
        organizacion_ids=tuple(str(o) for o in organizacion_ids),
    )


async def _organizacion(session) -> HubOrganizacion:
    fila = HubOrganizacion(name=f"Org {_uid()}", partner_id=f"p-{_uid()}")
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _chatbot_con_plantilla(session, organizacion, *, idioma="es") -> HubChatbot:
    await session.merge(
        HubProvider(id="google", name="Google", provider_type="google_genai")
    )
    await session.commit()
    llm = HubLLMConfig(provider="google", model_name="gemini-flash")
    session.add(llm)
    await session.commit()
    await session.refresh(llm)

    bot = HubChatbot(
        name=f"Asistente {_uid()}",
        organizacion_id=organizacion.id,
        llm_config_id=llm.id,
        system_prompt="Eres útil.",
        sources=[],
    )
    session.add(bot)
    await session.commit()
    await session.refresh(bot)

    session.add(
        HubPromptTemplate(
            chatbot_id=bot.id,
            slug="system_base",
            language=idioma,
            template_text="Eres un asistente institucional.",
            version=1,
        )
    )
    await session.commit()
    return bot


class TestElCatalogoEnsenaLosDosOrigenes:

    @pytest.mark.asyncio
    async def test_should_list_both_kinds_with_their_scope(self, db_session):
        org = await _organizacion(db_session)
        bot = await _chatbot_con_plantilla(db_session, org)

        async with _cliente(db_session, _principal()) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/prompts-catalog")).json()

        ambitos = {e["ambito"] for e in cuerpo}
        assert ambitos == {"plataforma", "chatbot_base", "chatbot"}, cuerpo
        de_chatbot = [e for e in cuerpo if e["ambito"] == "chatbot"]
        assert any(e["chatbot_id"] == str(bot.id) for e in de_chatbot)

    @pytest.mark.asyncio
    async def test_should_say_which_assistant_a_template_belongs_to(self, db_session):
        """Sin el nombre, «system_base» aparece repetido una vez por asistente y no hay forma
        de saber cuál se está tocando."""
        org = await _organizacion(db_session)
        bot = await _chatbot_con_plantilla(db_session, org)

        async with _cliente(db_session, _principal()) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/prompts-catalog")).json()

        fila = next(
            e
            for e in cuerpo
            if e["chatbot_id"] == str(bot.id) and e["ambito"] == "chatbot"
        )
        assert fila["chatbot_nombre"] == bot.name

    @pytest.mark.asyncio
    async def test_should_not_invent_a_language_for_an_activity(self, db_session):
        """Una actividad no tiene idioma y una plantilla sí. Juntar las dos vistas no puede
        significar inventarle campos a una de ellas."""
        org = await _organizacion(db_session)
        await _chatbot_con_plantilla(db_session, org, idioma="va")

        async with _cliente(db_session, _principal()) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/prompts-catalog")).json()

        actividad = next(e for e in cuerpo if e["ambito"] == "plataforma")
        plantilla = next(e for e in cuerpo if e["ambito"] == "chatbot")
        assert actividad["language"] is None
        assert actividad["modulo"]
        assert plantilla["language"] == "va"
        assert plantilla["modulo"] is None

    @pytest.mark.asyncio
    async def test_should_carry_what_it_takes_to_go_and_edit_it(self, db_session):
        """El catálogo es de sólo lectura **a propósito**: editar sigue yendo al router de cada
        uno, que es donde vive la regla. Pero tiene que decir a qué recurso ir, o la pantalla
        unificada sería un listado que no deja tocar la mitad de lo que enseña."""
        org = await _organizacion(db_session)
        await _chatbot_con_plantilla(db_session, org)

        async with _cliente(db_session, _principal()) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/prompts-catalog")).json()

        plantilla = next(e for e in cuerpo if e["ambito"] == "chatbot")
        assert plantilla["template_id"]
        # Y con el texto: sin él la pantalla tendría que pedir la plantilla una a una para
        # poder abrirla, que es una petición por fila.
        assert plantilla["template_text"] == "Eres un asistente institucional."
        actividad = next(e for e in cuerpo if e["ambito"] == "plataforma")
        assert actividad["clave"]
        assert actividad["template_id"] is None


    @pytest.mark.asyncio
    async def test_should_include_the_assistants_base_prompt(self, db_session):
        """El prompt base no está en ninguna tabla de prompts: es una columna de
        `hub_chatbots`. Y es **el que de verdad se ve** en la pantalla de Chatbots, porque las
        plantillas por actividad están vacías en la mayoría de despliegues. Un catálogo que lo
        dejara fuera enseñaría lo que casi nadie tiene y escondería lo que todos tienen."""
        org = await _organizacion(db_session)
        bot = await _chatbot_con_plantilla(db_session, org)

        async with _cliente(db_session, _principal()) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/prompts-catalog")).json()

        base = next(
            e
            for e in cuerpo
            if e["ambito"] == "chatbot_base" and e["chatbot_id"] == str(bot.id)
        )
        assert base["template_text"] == bot.system_prompt
        # Sin `template_id`: no hay plantilla que editar, se edita el chatbot.
        assert base["template_id"] is None


class TestElCatalogoNoEsUnAgujero:

    @pytest.mark.asyncio
    async def test_should_not_show_templates_of_another_organisation(self, db_session):
        """**El test del prompt.** Las plantillas cuelgan de chatbots y los chatbots de
        organizaciones: un catálogo que las junte todas sin acotar sería exactamente el
        agujero que cerró SEC.2, servido desde una pantalla nueva."""
        ajena = await _organizacion(db_session)
        propia = await _organizacion(db_session)
        de_otro = await _chatbot_con_plantilla(db_session, ajena)
        mio = await _chatbot_con_plantilla(db_session, propia)

        async with _cliente(
            db_session, _principal(role="admin", organizacion_ids=[propia.id])
        ) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/prompts-catalog")).json()

        vistos = {e["chatbot_id"] for e in cuerpo if e["chatbot_id"]}
        assert str(mio.id) in vistos
        # Ni la plantilla ni el prompt base del chatbot ajeno.
        assert str(de_otro.id) not in vistos

    @pytest.mark.asyncio
    async def test_should_show_every_organisation_to_a_superadmin(self, db_session):
        una = await _organizacion(db_session)
        otra = await _organizacion(db_session)
        bot_a = await _chatbot_con_plantilla(db_session, una)
        bot_b = await _chatbot_con_plantilla(db_session, otra)

        async with _cliente(db_session, _principal()) as cliente:
            cuerpo = (await cliente.get("/api/v1/hub/prompts-catalog")).json()

        vistos = {e["chatbot_id"] for e in cuerpo if e["ambito"] == "chatbot"}
        assert {str(bot_a.id), str(bot_b.id)} <= vistos

    @pytest.mark.asyncio
    async def test_should_be_reserved_to_administration(self, db_session):
        async with _cliente(db_session, _principal(role="user")) as cliente:
            respuesta = await cliente.get("/api/v1/hub/prompts-catalog")

        assert respuesta.status_code == 403, respuesta.text
