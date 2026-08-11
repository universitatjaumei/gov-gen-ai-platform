"""Servicio de feedback para interacciones del Hub."""

import uuid
from datetime import datetime, timezone

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
        review_status: str = "pending",
        verdict: str | None = None,
    ) -> list[HubInteraction]:
        """Conversaciones para revisar (REV.1).

        `review_status` por defecto **pending**: la cola de revisión es lo que falta por
        mirar, no todo el historial. Quien quiera el historial completo lo pide con `all`.

        Los filtros viajan a la base y no se aplican en Python a propósito: filtrar después
        del `LIMIT` daría el mismo resultado con 50 filas y ninguno con 50.000, que es el
        tipo de error que solo aparece cuando el piloto lleva meses funcionando.
        """
        query = (
            select(HubInteraction)
            .where(HubInteraction.chatbot_id == chatbot_id)
            .order_by(HubInteraction.created_at.desc())
            .limit(limit)
        )
        if only_low_scores:
            query = query.where(HubInteraction.feedback_score <= 2)

        if review_status == "pending":
            query = query.where(HubInteraction.review_verdict.is_(None))
        elif review_status == "reviewed":
            query = query.where(HubInteraction.review_verdict.is_not(None))

        if verdict is not None:
            query = query.where(HubInteraction.review_verdict == verdict)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def record_review(
        self,
        interaction: HubInteraction,
        verdict: str,
        note: str | None,
        reviewer: str,
    ) -> HubInteraction:
        """Anota el veredicto sobre la interacción ya cargada y comprobada.

        Recibe la interacción y no su identificador: quien llama ya la ha cargado para
        resolver su organización y comprobar la tenencia (SEC.8.1), y volver a buscarla aquí
        abriría la puerta a escribir sobre una fila distinta de la que se autorizó.
        """
        interaction.review_verdict = verdict
        interaction.review_note = note
        interaction.review_by = reviewer
        interaction.review_at = datetime.now(timezone.utc)
        await self.session.commit()
        return interaction
