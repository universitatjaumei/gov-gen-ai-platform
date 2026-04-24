"""Servicio de feedback para interacciones del Hub."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubInteraction
from server.app.modules.agents_hub.services.observability import get_langfuse_client


class FeedbackService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def submit_feedback(
        self,
        interaction_id: uuid.UUID,
        score: int,
        comment: str | None = None,
    ) -> None:
        await self.session.execute(
            update(HubInteraction)
            .where(HubInteraction.id == interaction_id)
            .values(feedback_score=score, feedback_text=comment)
        )
        await self.session.commit()

        client = get_langfuse_client()
        if client:
            interaction = await self.session.get(HubInteraction, interaction_id)
            if interaction and interaction.run_id:
                client.score(
                    trace_id=str(interaction.run_id),
                    name="user_feedback",
                    value=score,
                    comment=comment,
                )

    async def get_interactions_for_review(
        self,
        chatbot_id: uuid.UUID,
        limit: int = 50,
        only_low_scores: bool = False,
    ) -> list[HubInteraction]:
        query = (
            select(HubInteraction)
            .where(HubInteraction.chatbot_id == chatbot_id)
            .order_by(HubInteraction.created_at.desc())
            .limit(limit)
        )
        if only_low_scores:
            query = query.where(HubInteraction.feedback_score <= 2)

        result = await self.session.execute(query)
        return list(result.scalars().all())
