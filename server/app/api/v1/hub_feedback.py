"""Endpoint de feedback para interacciones del Hub.

POST /api/v1/hub/feedback/{interaction_id}
  Registra la valoración del usuario (1-5 estrellas + comentario opcional).
  Sincroniza automáticamente con LangFuse si está configurado.

GET /api/v1/hub/feedback/{chatbot_id}/review
  Devuelve interacciones para revisión humana (solo admin).


Deploy: edge
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.core.auth.tenancy import assert_chatbot_org_access, assert_org_access
from server.app.modules.agents_hub.database.config_models import HubChatbot
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import HubInteraction
from server.app.modules.agents_hub.services.feedback_service import FeedbackService

router = APIRouter(prefix="/hub/feedback", tags=["hub-feedback"])


class FeedbackRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)


class InteractionReviewOut(BaseModel):
    """Interacción servida a la revisión humana (CAL.2).

    El endpoint devolvía `list[dict]`, que en el contrato es una lista de objetos sin
    forma; `ReportsPage` se veía obligada a redeclarar los siete campos a mano. Lo que
    la pantalla tabula y exporta a CSV sale de aquí.
    """

    id: uuid.UUID
    user_message: str
    assistant_message: str
    feedback_score: int | None = None
    feedback_text: str | None = None
    run_id: str | None = None
    created_at: datetime


@router.post("/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def submit_feedback(
    interaction_id: uuid.UUID,
    request: FeedbackRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    # SEC.8.1: el GET de revisión comprobaba la organización desde SEC.2; este POST no
    # comprobaba nada y el servicio hace `UPDATE ... WHERE id = :id` a ciegas, así que
    # cualquier usuario autenticado —de cualquier organización— escribía sobre la
    # valoración de una conversación ajena, y de ahí pasaba a LangFuse.
    interaccion = await session.get(HubInteraction, interaction_id)
    if interaccion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found"
        )
    if interaccion.user_id != user.user_id:
        await assert_chatbot_org_access(session, interaccion.chatbot_id, user)

    service = FeedbackService(session)
    await service.submit_feedback(
        interaction_id=interaction_id,
        score=request.score,
        comment=request.comment,
    )


@router.get("/{chatbot_id}/review", response_model=list[InteractionReviewOut])
async def get_interactions_for_review(
    chatbot_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    only_low_scores: bool = Query(False),
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    if user.role not in ("superadmin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or superadmin can access interaction reviews",
        )
    # SEC.2: tener rol de admin no basta. Estas interacciones son conversaciones de
    # ciudadanos con el asistente de OTRA administración; leerlas sin ser de su organización
    # es el caso más grave del hallazgo A2, porque el dato es personal y de un tercero.
    chatbot = await session.get(HubChatbot, chatbot_id)
    if chatbot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")
    assert_org_access(user, chatbot.organizacion_id)

    service = FeedbackService(session)
    interactions = await service.get_interactions_for_review(
        chatbot_id=chatbot_id,
        limit=limit,
        only_low_scores=only_low_scores,
    )
    return [
        {
            "id": str(i.id),
            "user_message": i.user_message,
            "assistant_message": i.assistant_message,
            "feedback_score": i.feedback_score,
            "feedback_text": i.feedback_text,
            "run_id": str(i.run_id) if i.run_id else None,
            "created_at": i.created_at.isoformat(),
        }
        for i in interactions
    ]
