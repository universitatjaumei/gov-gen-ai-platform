"""El registro de actividad IA: lo que ocurre fuera de la plataforma (REG.2).

Deploy: edge
Módulo: —

**Por qué existe.** La plataforma sabe todo de las conversaciones que pasan por ella y nada de las
que no. Una organización que use además asistentes de escritorio, agentes de código o
integraciones propias no puede responder «qué IA se usó aquí» sin ir a preguntar a cada
herramienta. Este endpoint le da un sitio donde esas herramientas lo declaren.

Sirve a la conservación de registros del AI Act y al registro de actividades de tratamiento del
RGPD. **No** es trazado técnico: metadatos de gobernanza, y el detalle de cada conversación se
queda en la herramienta que la tuvo.

**Dos decisiones que condicionan la forma del endpoint:**

**La organización se deriva del token, no viaja en el payload.** Un agente externo no elige en
nombre de qué organización registra. Si lo eligiera, un token de una organización podría escribir
en el registro de otra, y entonces el registro no daría cuenta de nada.

**Escribe un PAT, no una sesión.** Por eso `require_pat_scopes` y no `require_scopes`: aquélla
deja pasar a los principales humanos, y una sesión de navegador con permiso de escritura aquí
permitiría fabricar entradas del registro desde el panel. La lectura, que sí es para personas, va
por sesión y llega en REG.5.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import require_pat_scopes
from server.app.core.auth.models import UserInfo
from server.app.core.auth.pat.scopes import ACTIVIDAD_WRITE
from server.app.core.auth.tenancy import organizacion_unica_de
from server.app.modules.agents_hub.contracts.actividad import ActividadIAEvent
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import HubActividadIA

router = APIRouter(prefix="/actividad", tags=["actividad"])


class ActividadRegistrada(BaseModel):
    """El acuse: qué id tiene el evento y cuándo quedó registrado.

    Se devuelve `registrado_en` y no sólo el id porque es el dato que quien integra necesita para
    conciliar: su reloj y el nuestro no son el mismo, y la marca que vale en una auditoría es la
    nuestra.
    """

    id: uuid.UUID
    registrado_en: datetime


@router.post(
    "",
    response_model=ActividadRegistrada,
    status_code=status.HTTP_201_CREATED,
    operation_id="registrarActividad",
)
async def registrar_actividad(
    evento: ActividadIAEvent,
    user: UserInfo = Depends(require_pat_scopes(ACTIVIDAD_WRITE)),
    session: AsyncSession = Depends(get_async_session),
) -> ActividadRegistrada:
    """Registra un uso de IA declarado por una herramienta externa.

    El contrato rechaza los campos que no declara, así que un intento de colar el contenido
    —`payload`, `prompt`, `content`— llega aquí como 422 y no como una fila con datos personales
    dentro.
    """
    organizacion_id = organizacion_unica_de(user)
    if organizacion_id is None:
        # Un principal sin organización única no tiene dónde registrar: puede ser un
        # superadministrador (lista vacía = «todas») o un token con varias. En los dos casos la
        # respuesta honesta es pedir un token de organización, no elegir una por él.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZACION_INDETERMINADA",
                "message": (
                    "El token tiene que pertenecer a una sola organización: el registro se "
                    "acota por ella y no se puede elegir en la petición."
                ),
            },
        )

    fila = HubActividadIA(
        organizacion_id=organizacion_id,
        ocurrido_en=evento.ocurrido_en,
        actor=evento.actor,
        herramienta=evento.herramienta,
        agente=evento.agente,
        finalidad=evento.finalidad,
        modelo_usado=evento.modelo_usado,
        categorias_datos=evento.categorias_datos,
        payload_hash=evento.payload_hash,
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)

    return ActividadRegistrada(id=fila.id, registrado_en=fila.registrado_en)
