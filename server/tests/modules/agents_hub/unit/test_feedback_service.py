"""Tests para FeedbackService."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSubmitFeedback:

    @pytest.mark.asyncio
    async def test_updates_score_and_commits(self) -> None:
        from server.app.modules.agents_hub.services.feedback_service import FeedbackService

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        service = FeedbackService(mock_session)
        await service.submit_feedback(
            interaction_id=uuid.uuid4(),
            score=5,
            comment="Excelente respuesta",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_accepts_score_without_comment(self) -> None:
        from server.app.modules.agents_hub.services.feedback_service import FeedbackService

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        service = FeedbackService(mock_session)
        await service.submit_feedback(interaction_id=uuid.uuid4(), score=3)

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sends_score_to_langfuse_when_run_id_present(self) -> None:
        """`spec=Langfuse` y no un `MagicMock()` a pelo: un mock sin spec inventa
        cualquier atributo que se le pida, así que `client.score(...)` pasaba el test
        aunque el SDK instalado (4.5.0) hubiera renombrado el método a `create_score` --
        en producción reventaba con AttributeError en cuanto alguien puntuaba una
        respuesta, y ningún test lo vio nunca."""
        from langfuse import Langfuse

        from server.app.modules.agents_hub.services.feedback_service import FeedbackService

        interaction_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_interaction = MagicMock()
        mock_interaction.run_id = run_id

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_interaction)

        mock_client = MagicMock(spec=Langfuse)

        with patch(
            "server.app.modules.agents_hub.services.feedback_service.get_langfuse_client",
            return_value=mock_client,
        ):
            service = FeedbackService(mock_session)
            await service.submit_feedback(
                interaction_id=interaction_id,
                score=4,
                comment="Buena respuesta",
            )

        mock_client.create_score.assert_called_once_with(
            trace_id=str(run_id),
            name="user_feedback",
            value=4,
            comment="Buena respuesta",
        )

    @pytest.mark.asyncio
    async def test_skips_langfuse_when_client_unavailable(self) -> None:
        from server.app.modules.agents_hub.services.feedback_service import FeedbackService

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        with patch(
            "server.app.modules.agents_hub.services.feedback_service.get_langfuse_client",
            return_value=None,
        ):
            service = FeedbackService(mock_session)
            await service.submit_feedback(interaction_id=uuid.uuid4(), score=2)

        mock_session.commit.assert_called_once()


class TestGetInteractionsForReview:

    @pytest.mark.asyncio
    async def test_returns_list(self) -> None:
        from server.app.modules.agents_hub.services.feedback_service import FeedbackService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = FeedbackService(mock_session)
        result = await service.get_interactions_for_review(chatbot_id=uuid.uuid4())

        assert isinstance(result, list)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_low_scores(self) -> None:
        from server.app.modules.agents_hub.services.feedback_service import FeedbackService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = FeedbackService(mock_session)
        result = await service.get_interactions_for_review(
            chatbot_id=uuid.uuid4(), only_low_scores=True
        )

        assert isinstance(result, list)
        mock_session.execute.assert_called_once()
