"""Biblioteca de prompts de las actividades de plataforma — PRO.2.1.

Deploy: cloud
Módulo: plataforma — actividades que no cuelgan de ningún chatbot (PRO.2.1).

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
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session, require_module
from server.app.core.auth.models import UserInfo
from server.app.core.auth.tenancy import assert_org_access, organizacion_unica_de
from server.app.modules.agents_hub.database.config_models import HubActivityPrompt
from server.app.modules.redaccion.services.actividades_llm import (
    ActividadLLM,
    MODULO_POR_ACTIVIDAD,
    PARA_QUE_SIRVE,
    PROMPT_POR_ACTIVIDAD,
    TIER_POR_ACTIVIDAD,
    variables_de,
)
from server.app.routers.redaccion._actor import user_to_uuid

router = APIRouter(
    prefix="/hub/activity-prompts",
    tags=["hub-activity-prompts"],
    # SEC.9.3 — el módulo se exige a nivel de router. El docstring ya declaraba «Módulo:
    # plataforma» y no había ninguna dependencia que lo hiciera cumplir: el mismo desajuste que
    # PLAT.5 cerró en otros tres routers, y el que dejó este abierto a cualquier administrador.
    dependencies=[Depends(require_module("plataforma"))],
)


class ActivityPromptOut(BaseModel):
    """Lo que la pantalla necesita para poder decir de dónde sale cada cosa."""

    activity: str
    purpose: str
    # De qué módulo es (REV.7). Va en el contrato porque la pantalla agrupa y filtra por él,
    # y deducirlo del nombre de la actividad en el React sería inventarlo.
    modulo: str
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
        modulo=MODULO_POR_ACTIVIDAD[actividad],
        default_tier=TIER_POR_ACTIVIDAD[actividad],
        default_template=PROMPT_POR_ACTIVIDAD[actividad],
        variables=sorted(variables_de(actividad)),
        override_tier=nivel_guardado,
        template_text=texto_guardado or None,
        effective_tier=nivel_guardado or TIER_POR_ACTIVIDAD[actividad],
        tier_source="override" if nivel_guardado is not None else "codigo",
        text_source="override" if texto_guardado.strip() else "codigo",
    )


def _organizacion_objetivo(user: UserInfo, pedida: uuid.UUID | None) -> uuid.UUID | None:
    """De qué organización es el override que se está mirando o tocando (SEC.9.3).

    Sigue el patrón de REV.12 (`/hub/themes/resolved`): el cliente **puede nombrarla** —es la
    del selector de la cabecera— y se comprueba con `assert_org_access`. Si no la nombra, se usa
    la suya cuando gestiona una sola.

    **Nulo es el nivel de plataforma**, el que heredan todas, y sólo lo alcanza el
    superadministrador. Un administrador que gestiona varias organizaciones recibe un 400
    pidiéndosela: elegir por él escribiría en una que no ha nombrado, y caer a plataforma
    convertiría un despiste en un cambio para todo el mundo — que es justo el agujero.
    """
    if pedida is not None:
        assert_org_access(user, pedida)
        return pedida
    if getattr(user, "is_superadmin", False):
        return None
    propia = organizacion_unica_de(user)
    if propia is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "ORGANIZACION_REQUERIDA",
                "message": (
                    "Indica la organización: tu cuenta gestiona varias, y el prompt sin "
                    "organización es el de plataforma, que heredan todas."
                ),
            },
        )
    return propia


def _es_de(fila: HubActivityPrompt, organizacion_id: uuid.UUID | None) -> bool:
    if organizacion_id is None:
        return fila.organizacion_id is None
    return str(fila.organizacion_id) == str(organizacion_id)


async def _candidatas(
    session: AsyncSession, actividad: ActividadLLM, organizacion_id: uuid.UUID | None
) -> list[HubActivityPrompt]:
    """Las filas que pueden participar en la cadena: la de la organización y la de plataforma.

    `or_` y no `IN`, por lo mismo que en `config_provider`: `NULL IN (...)` es nulo en SQL, así
    que un `IN` no traería la fila de plataforma y la herencia no ocurriría.
    """
    condiciones = [HubActivityPrompt.activity == str(actividad)]
    if organizacion_id is None:
        condiciones.append(HubActivityPrompt.organizacion_id.is_(None))
    else:
        condiciones.append(
            or_(
                HubActivityPrompt.organizacion_id == organizacion_id,
                HubActivityPrompt.organizacion_id.is_(None),
            )
        )
    resultado = await session.execute(select(HubActivityPrompt).where(*condiciones))
    return list(resultado.scalars().all())


async def _fila(
    session: AsyncSession, actividad: ActividadLLM, organizacion_id: uuid.UUID | None
) -> HubActivityPrompt | None:
    """La fila que **gana** para esta organización: la suya y, si no tiene, la de plataforma.

    La pertenencia se vuelve a comprobar en Python y no sólo en el `WHERE`. Parece redundante y
    no lo es: es lo que impide que un `WHERE` mal construido mañana devuelva la fila de otra
    organización y este endpoint la sirva como propia.
    """
    filas = await _candidatas(session, actividad, organizacion_id)
    propia = next((f for f in filas if _es_de(f, organizacion_id)), None)
    if propia is not None:
        return propia
    return next((f for f in filas if f.organizacion_id is None), None)


async def _fila_propia(
    session: AsyncSession, actividad: ActividadLLM, organizacion_id: uuid.UUID | None
) -> HubActivityPrompt | None:
    """Sólo la fila de **esta** organización: sin herencia, porque escribir no se hereda.

    Es la diferencia que faltaba. Con la búsqueda de lectura, guardar el override de un
    municipio sobrescribía la fila de plataforma que le llegaba por herencia — y con ella el
    prompt de todos los demás.
    """
    filas = await _candidatas(session, actividad, organizacion_id)
    return next((f for f in filas if _es_de(f, organizacion_id)), None)


@router.get("", response_model=list[ActivityPromptOut], operation_id="listActivityPrompts")
async def list_activity_prompts(
    organizacion_id: Annotated[
        uuid.UUID | None,
        Query(
            description=(
                "Organización cuyos overrides se consultan. Si no se indica, la del actor "
                "cuando gestiona una sola; en un superadministrador, el nivel de plataforma."
            ),
        ),
    ] = None,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ActivityPromptOut]:
    """Las actividades del catálogo, con su nivel y texto efectivos para esa organización."""
    _require_admin(user)
    objetivo = _organizacion_objetivo(user, organizacion_id)
    salida: list[ActivityPromptOut] = []
    for actividad in ActividadLLM:
        salida.append(_salida(actividad, await _fila(session, actividad, objetivo)))
    return salida


@router.put(
    "/{activity}", response_model=ActivityPromptOut, operation_id="updateActivityPrompt"
)
async def update_activity_prompt(
    activity: str,
    body: ActivityPromptUpdate,
    # `Annotated` y no `= Query(...)`: así el valor por omisión en Python es `None` de verdad.
    # Con `= Query(default=None)`, llamar a la función directamente —como hacen los tests contra
    # base de datos real— le pasaba el objeto `Query` a la consulta, y asyncpg reventaba con un
    # «'Query' object has no attribute 'bytes'» que no se parece en nada a su causa.
    organizacion_id: Annotated[uuid.UUID | None, Query()] = None,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ActivityPromptOut:
    """Guarda el override de una actividad **en su organización**. Texto vacío = el del código."""
    _require_admin(user)
    objetivo = _organizacion_objetivo(user, organizacion_id)
    actividad = _actividad_o_422(activity)

    texto = (body.template_text or "").strip()
    if texto:
        _validar_variables(actividad, texto)

    # `_fila_propia` y no `_fila`: la herencia sirve para leer, no para escribir. Con la búsqueda
    # de lectura, guardar el override de un municipio sobrescribía la fila de plataforma que le
    # llegaba heredada, y con ella el prompt de todas las demás organizaciones.
    fila = await _fila_propia(session, actividad, objetivo)
    if fila is None:
        fila = HubActivityPrompt(
            id=uuid.uuid4(), activity=str(actividad), organizacion_id=objetivo
        )
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
    # `Annotated` y no `= Query(...)`: así el valor por omisión en Python es `None` de verdad.
    # Con `= Query(default=None)`, llamar a la función directamente —como hacen los tests contra
    # base de datos real— le pasaba el objeto `Query` a la consulta, y asyncpg reventaba con un
    # «'Query' object has no attribute 'bytes'» que no se parece en nada a su causa.
    organizacion_id: Annotated[uuid.UUID | None, Query()] = None,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ActivityPromptOut:
    """Borra el override **de su organización**: la actividad vuelve a lo heredado o al código."""
    _require_admin(user)
    objetivo = _organizacion_objetivo(user, organizacion_id)
    actividad = _actividad_o_422(activity)

    # Sólo la propia: borrar lo heredado sería borrarle la configuración a otra organización.
    fila = await _fila_propia(session, actividad, objetivo)
    if fila is not None:
        await session.delete(fila)
        await session.commit()

    return _salida(actividad, await _fila(session, actividad, objetivo))


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
