"""Catálogo de todos los prompts, con su ámbito a la vista (REV.13).

Deploy: cloud
Módulo: plataforma — es la vista de conjunto, y quien la mira administra la plataforma.

Había dos pantallas y el usuario preguntó, con razón, por qué. La respuesta es que son **dos
modelos distintos**, no el mismo dato en dos sitios:

- `HubPromptTemplate` cuelga de **un chatbot** (`chatbot_id` NOT NULL), va por idioma y está
  versionada. Por eso vive bajo el módulo Chatbots.
- `HubActivityPrompt` va por actividad, y el catálogo de actividades lo declara el código
  (`actividades_llm.py`). **Desde MT.6 su clave es `(activity, organizacion_id)`**: la
  configuración se hereda organización → plataforma → código, así que `activity` ya no es único
  global — esta línea lo decía y dejó de ser cierto (corregido en SEC.9.5).
- Y hay un tercero que no es ninguna tabla de prompts: el **prompt base** de cada asistente,
  que es una columna de `hub_chatbots`. Es el que de verdad se ve hoy en la pantalla de
  Chatbots —las plantillas por actividad están vacías en la mayoría de despliegues—, así que
  un catálogo que lo dejara fuera no resolvería nada.

Unificar las tablas sería meter dos cosas distintas en una. Lo que faltaba era **poder verlas
juntas**, y eso es este endpoint: sólo lectura, con `ambito` explícito y con lo que hace falta
para ir a editar cada una por su camino —`template_id` para una plantilla, `clave` para una
actividad—. **La edición sigue en el router de cada uno**, que es donde vive su regla: una
plantilla se versiona al cambiar el texto y una actividad no, y esa diferencia no se puede
diluir en un endpoint común sin perder una de las dos.

**Acota por organización.** Las plantillas cuelgan de chatbots y los chatbots de organizaciones:
un catálogo que las juntara todas sin acotar sería el agujero que cerró SEC.2, servido desde una
pantalla nueva.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session, require_module
from server.app.core.auth.models import UserInfo
from server.app.core.auth.tenancy import scope_query_to_orgs
from server.app.modules.agents_hub.database.config_models import (
    HubChatbot,
    HubPromptTemplate,
)
from server.app.modules.redaccion.services.actividades_llm import (
    ActividadLLM,
    MODULO_POR_ACTIVIDAD,
    PARA_QUE_SIRVE,
)

router = APIRouter(
    prefix="/hub/prompts-catalog",
    tags=["hub-prompts-catalog"],
    # SEC.9.5 — el docstring declaraba «Módulo: plataforma» y nada lo exigía. La pantalla que
    # consume esto ya pide `plataforma` desde SEC.9.3 (los prompts de actividad), así que la
    # guarda alinea el router con la sección donde vive.
    dependencies=[Depends(require_module("plataforma"))],
)

AMBITO_PLATAFORMA = "plataforma"
AMBITO_CHATBOT_BASE = "chatbot_base"
AMBITO_CHATBOT = "chatbot"

#: La clave con la que se enseña el prompt base. No es un `slug` de la tabla de plantillas
#: —el prompt base es una columna de `hub_chatbots`—, pero la pantalla necesita llamarlo de
#: alguna manera y dejarlo en blanco sería una fila sin nombre.
CLAVE_PROMPT_BASE = "prompt_base"


class PromptDelCatalogo(BaseModel):
    """Una entrada del catálogo, sea del origen que sea.

    Los campos que sólo tiene uno de los dos van nulos en el otro **y no se rellenan con nada**:
    una actividad no tiene idioma y una plantilla no tiene módulo. Inventárselos para que las
    dos filas parezcan iguales sería mentir sobre lo que son.
    """

    ambito: str
    #: `activity` en una actividad, `slug` en una plantilla. Lo que la identifica para quien mira.
    clave: str
    descripcion: str | None = None
    #: Sólo actividades: de qué módulo de la plataforma es (REV.7).
    modulo: str | None = None
    #: Sólo plantillas: a qué asistente pertenece y en qué idioma.
    chatbot_id: uuid.UUID | None = None
    chatbot_nombre: str | None = None
    language: str | None = None
    #: Sólo plantillas: a qué recurso ir para editarla, y con qué texto llega.
    template_id: uuid.UUID | None = None
    template_text: str | None = None
    version: int | None = None


def _require_admin(user: UserInfo) -> None:
    if user.role not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get(
    "", response_model=list[PromptDelCatalogo], operation_id="listPromptsCatalog"
)
async def list_prompts_catalog(
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PromptDelCatalogo]:
    """Todos los prompts que existen, sin poder editarlos desde aquí.

    Las actividades salen del **código** —el catálogo las declara y la tabla sólo guarda la
    excepción—, así que se listan siempre, tenga o no override cada una. Las plantillas salen de
    la base y van acotadas por organización.
    """
    _require_admin(user)

    entradas: list[PromptDelCatalogo] = [
        PromptDelCatalogo(
            ambito=AMBITO_PLATAFORMA,
            clave=str(actividad),
            descripcion=PARA_QUE_SIRVE[actividad],
            modulo=MODULO_POR_ACTIVIDAD[actividad],
        )
        for actividad in ActividadLLM
    ]

    consulta = (
        select(HubPromptTemplate, HubChatbot)
        .join(HubChatbot, HubChatbot.id == HubPromptTemplate.chatbot_id)
        .order_by(HubChatbot.name, HubPromptTemplate.slug, HubPromptTemplate.language)
    )
    # La acotación va sobre el **chatbot**, que es quien tiene la organización: la plantilla no
    # la tiene, y filtrar por lo que no está es no filtrar.
    consulta = scope_query_to_orgs(consulta, user, HubChatbot)

    de_chatbots = scope_query_to_orgs(
        select(HubChatbot).order_by(HubChatbot.name), user, HubChatbot
    )
    for chatbot in (await session.execute(de_chatbots)).scalars():
        entradas.append(
            PromptDelCatalogo(
                ambito=AMBITO_CHATBOT_BASE,
                clave=CLAVE_PROMPT_BASE,
                chatbot_id=chatbot.id,
                chatbot_nombre=chatbot.name,
                template_text=chatbot.system_prompt,
            )
        )

    for plantilla, chatbot in (await session.execute(consulta)).all():
        entradas.append(
            PromptDelCatalogo(
                ambito=AMBITO_CHATBOT,
                clave=plantilla.slug,
                chatbot_id=chatbot.id,
                chatbot_nombre=chatbot.name,
                language=plantilla.language,
                template_id=plantilla.id,
                template_text=plantilla.template_text,
                version=plantilla.version,
            )
        )

    return entradas
