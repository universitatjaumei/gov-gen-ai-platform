"""Endpoint de feedback para interacciones del Hub.

POST /api/v1/hub/feedback/{interaction_id}
  Registra la valoración del usuario (1-5 estrellas + comentario opcional).
  Sincroniza automáticamente con LangFuse si está configurado.

GET /api/v1/hub/feedback/{chatbot_id}/review
  Devuelve interacciones para revisión humana (solo admin).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.services.feedback_service import FeedbackService

router = APIRouter(prefix="/hub/feedback", tags=["hub-feedback"])


class FeedbackRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)


@router.post("/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def submit_feedback(
    interaction_id: uuid.UUID,
    request: FeedbackRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    service = FeedbackService(session)
    await service.submit_feedback(
        interaction_id=interaction_id,
        score=request.score,
        comment=request.comment,
    )


@router.get("/{chatbot_id}/review")
async def get_interactions_for_review(
    chatbot_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    only_low_scores: bool = Query(False),
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    if user.role not in ("admin", "partner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or partner can access interaction reviews",
        )
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
