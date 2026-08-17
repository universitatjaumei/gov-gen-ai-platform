"""Biblioteca de prompts de las actividades de plataforma — PRO.2.1.

Deploy: cloud

Hasta aquí la biblioteca (`/hub/prompts`, `/hub/brain`) sólo veía prompts **de chatbot**,
porque `hub_prompt_templates.chatbot_id` es NOT NULL. Los prompts de las actividades del
módulo de Informes —escribir un script, auditarlo, y los que vengan— vivían en Python: no se
podían afinar sin desplegar ni se podía elegir con qué nivel de modelo corre cada una.

**Qué actividades existen lo dice el código**, no esta tabla: el catálogo está en
`modules/redaccion/services/actividades_llm.py`. Este router lee de ahí y guarda sólo la
excepción. Que un router cloud lea el catálogo de un módulo edge es la dirección permitida por
la frontera; lo que no puede pasar es lo contrario.

Dos reglas que la superficie hace cumplir:

- **Una actividad no se puede inventar desde la pantalla** (422 `UNKNOWN_ACTIVITY`): si no
  está en el catálogo, nada la consume, y sería configuración que parece funcionar.
- **El texto por defecto no se copia al guardar.** Se devuelve aparte (`default_template`)
  para que la pantalla lo pueda mostrar. Copiarlo congelaría el prompt: a partir de ahí,
  mejorarlo en el código no llegaría a quien ya lo abrió.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.config_models import HubActivityPrompt
from server.app.modules.redaccion.services.actividades_llm import (
    ActividadLLM,
    PARA_QUE_SIRVE,
    PROMPT_POR_ACTIVIDAD,
    TIER_POR_ACTIVIDAD,
    variables_de,
)
from server.app.routers.redaccion._actor import user_to_uuid

router = APIRouter(prefix="/hub/activity-prompts", tags=["hub-activity-prompts"])


class ActivityPromptOut(BaseModel):
    """Lo que la pantalla necesita para poder decir de dónde sale cada cosa."""

    activity: str
    purpose: str
    default_tier: int
    default_template: str
    variables: list[str]
    override_tier: int | None = None
    template_text: str | None = None
    effective_tier: int
    tier_source: str
    text_source: str


class ActivityPromptUpdate(BaseModel):
    override_tier: int | None = Field(default=None, ge=1, le=3)
    template_text: str | None = None


def _require_admin(user: UserInfo) -> None:
    if user.role not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


def _actividad_o_422(activity: str) -> ActividadLLM:
    try:
        return ActividadLLM(activity)
    except ValueError as fallo:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNKNOWN_ACTIVITY",
                "message": (
                    f"'{activity}' no está en el catálogo de actividades, así que nada la "
                    "consumiría. Las actividades las declara el código."
                ),
            },
        ) from fallo


def _salida(
    actividad: ActividadLLM,
    fila: HubActivityPrompt | None = None,
    *,
    template_text: str | None = None,
    override_tier: int | None = None,
) -> ActivityPromptOut:
    """La salida, o desde la fila o desde valores ya capturados.

    Los valores se pueden pasar sueltos porque **después de un `commit()` no se pueden leer
    los atributos de la fila**: `expire_on_commit` los deja expirados y el acceso intenta
    recargarlos, lo que fuera de contexto async es un `MissingGreenlet` —el mismo 500 que
    VER.4 encontró cinco veces en este módulo—. El doble de sesión de los tests no lo
    reproduce, así que hay un test contra base de datos real que sí.
    """
    texto_guardado = ((fila.template_text if fila else template_text) or "")
    nivel_guardado = fila.override_tier if fila else override_tier
    return ActivityPromptOut(
        activity=str(actividad),
        purpose=PARA_QUE_SIRVE[actividad],
        default_tier=TIER_POR_ACTIVIDAD[actividad],
        default_template=PROMPT_POR_ACTIVIDAD[actividad],
        variables=sorted(variables_de(actividad)),
        override_tier=nivel_guardado,
        template_text=texto_guardado or None,
        effective_tier=nivel_guardado or TIER_POR_ACTIVIDAD[actividad],
        tier_source="override" if nivel_guardado is not None else "codigo",
        text_source="override" if texto_guardado.strip() else "codigo",
    )


async def _fila(session: AsyncSession, actividad: ActividadLLM) -> HubActivityPrompt | None:
    resultado = await session.execute(
        select(HubActivityPrompt).where(HubActivityPrompt.activity == str(actividad))
    )
    return resultado.scalars().first()


@router.get("", response_model=list[ActivityPromptOut], operation_id="listActivityPrompts")
async def list_activity_prompts(
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ActivityPromptOut]:
    """Las actividades del catálogo, con su nivel y texto efectivos."""
    _require_admin(user)
    salida: list[ActivityPromptOut] = []
    for actividad in ActividadLLM:
        salida.append(_salida(actividad, await _fila(session, actividad)))
    return salida


@router.put(
    "/{activity}", response_model=ActivityPromptOut, operation_id="updateActivityPrompt"
)
async def update_activity_prompt(
    activity: str,
    body: ActivityPromptUpdate,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ActivityPromptOut:
    """Guarda el override de una actividad. Texto vacío = volver al del código."""
    _require_admin(user)
    actividad = _actividad_o_422(activity)

    texto = (body.template_text or "").strip()
    if texto:
        _validar_variables(actividad, texto)

    fila = await _fila(session, actividad)
    if fila is None:
        fila = HubActivityPrompt(id=uuid.uuid4(), activity=str(actividad))
        session.add(fila)

    fila.override_tier = body.override_tier
    # Sin texto se guarda NULL, no la plantilla del código: es lo que permite volver atrás
    # desde la pantalla sin borrar la fila por SQL.
    fila.template_text = texto or None
    fila.version = (fila.version or 0) + 1
    fila.updated_by = user_to_uuid(user.user_id)
    fila.updated_at = datetime.now(timezone.utc)
    await session.flush()
    # Capturados **antes** del commit: después están expirados y leerlos es un MissingGreenlet.
    nivel_guardado = fila.override_tier
    texto_guardado = fila.template_text
    await session.commit()

    return _salida(actividad, template_text=texto_guardado, override_tier=nivel_guardado)


@router.delete(
    "/{activity}", response_model=ActivityPromptOut, operation_id="resetActivityPrompt"
)
async def reset_activity_prompt(
    activity: str,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ActivityPromptOut:
    """Borra el override: la actividad vuelve a lo que dice el código."""
    _require_admin(user)
    actividad = _actividad_o_422(activity)

    fila = await _fila(session, actividad)
    if fila is not None:
        await session.delete(fila)
        await session.commit()

    return _salida(actividad, None)


def _validar_variables(actividad: ActividadLLM, texto: str) -> None:
    """Un `{invento}` no se puede rellenar y llegaría al modelo tal cual.

    Se avisa al guardar, que es cuando alguien lo puede corregir, en vez de dejar el hueco
    dentro del prompt de la siguiente petición.
    """
    import re

    usadas = set(re.findall(r"\{(\w+)\}", texto))
    permitidas = variables_de(actividad)
    sobran = sorted(usadas - permitidas)
    if sobran:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNKNOWN_VARIABLE",
                "message": (
                    f"Estas variables no existen para esta actividad: {sobran}. "
                    f"Las disponibles son: {sorted(permitidas)}."
                ),
            },
        )
