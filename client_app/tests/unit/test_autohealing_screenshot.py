
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


class TestPendingScreenshotModel:
    """Tests para el modelo de capturas pendientes de revisión."""

    def test_pending_screenshot_has_required_fields(self):
        """El modelo debe tener los campos necesarios."""
        from client_app.app.database.models import PendingScreenshotReview

        review = PendingScreenshotReview(
            execution_id="exec_123",
            task_id=1,
            step_index=3,
            screenshot_path="/tmp/screenshot.png",
            source_url="https://example.com",
            reason="auto_healing"
        )

        assert review.execution_id == "exec_123"
        assert review.status == "pending"  # Default
        assert review.created_at is not None

    def test_pending_screenshot_status_values(self):
        """El status debe tener valores específicos."""
        from client_app.app.database.models import PendingScreenshotReview

        # Debe poder ser: pending, approved, rejected, expired
        review = PendingScreenshotReview(
            execution_id="test",
            task_id=1,
            step_index=0,
            screenshot_path="/tmp/test.png",
            source_url="https://test.com",
            reason="test"
        )

        review.status = "approved"
        assert review.status == "approved"

        review.status = "rejected"
        assert review.status == "rejected"


class TestWorkflowEngineSuspend:
    """Tests para suspensión de workflow por revisión de captura."""

    @pytest.mark.asyncio
    async def test_suspends_on_review_required_in_background(self):
        """En ejecución background, debe suspender si requiere revisión."""
        from client_app.app.services.screenshot_guard import ScreenshotGuardAction

        with patch('client_app.app.modules.runtime.workflow_engine.screenshot_guard') as mock_guard:
            mock_guard.check_policy = AsyncMock(return_value=ScreenshotGuardAction.REQUIRE_REVIEW)

            with patch('client_app.app.modules.runtime.workflow_engine.is_interactive_session', return_value=False):
                from client_app.app.modules.runtime.workflow_engine import WorkflowEngine

                engine = WorkflowEngine(session=MagicMock())
                engine._current_execution_id = "exec_456"

                # Mock para guardar la captura pendiente
                with patch.object(engine, '_save_pending_screenshot_review', new_callable=AsyncMock) as mock_save:
                    mock_save.return_value = 1  # ID del registro
                    
                    # Mock notification to avoid import error if not implemented
                    with patch('client_app.app.modules.runtime.workflow_engine.create_dashboard_notification', new_callable=AsyncMock):
                        result = await engine._handle_screenshot_for_healing(
                            screenshot_bytes=b"fake_image",
                            url="https://example.com",
                            task_id=10,
                            step_index=2
                        )

                        # Debe guardar y retornar que se suspendió
                        mock_save.assert_called_once()
                        assert result["suspended"] is True
                        assert result["pending_review_id"] is not None

    @pytest.mark.asyncio
    async def test_proceeds_on_allow_in_background(self):
        """En background con ALLOW, debe proceder sin suspender."""
        from client_app.app.services.screenshot_guard import ScreenshotGuardAction

        with patch('client_app.app.modules.runtime.workflow_engine.screenshot_guard') as mock_guard:
            mock_guard.check_policy = AsyncMock(return_value=ScreenshotGuardAction.ALLOW)

            with patch('client_app.app.modules.runtime.workflow_engine.brain_client') as mock_brain:
                mock_brain.send_visual_request = AsyncMock(return_value={"fix": "ok"})

                from client_app.app.modules.runtime.workflow_engine import WorkflowEngine

                engine = WorkflowEngine(session=MagicMock())

                result = await engine._handle_screenshot_for_healing(
                    screenshot_bytes=b"fake",
                    url="https://trusted.com",
                    task_id=1,
                    step_index=0
                )

                assert result["suspended"] is False
                assert result["brain_response"] is not None


class TestDashboardNotification:
    """Tests para notificación en dashboard."""

    @pytest.mark.asyncio
    async def test_creates_notification_on_suspend(self):
        """Al suspender, debe crear notificación en dashboard."""
        from client_app.app.services.screenshot_guard import ScreenshotGuardAction

        with patch('client_app.app.modules.runtime.workflow_engine.screenshot_guard') as mock_guard:
            mock_guard.check_policy = AsyncMock(return_value=ScreenshotGuardAction.REQUIRE_REVIEW)

            with patch('client_app.app.modules.runtime.workflow_engine.is_interactive_session', return_value=False):
                with patch('client_app.app.modules.runtime.workflow_engine.create_dashboard_notification', new_callable=AsyncMock) as mock_notify:
                    from client_app.app.modules.runtime.workflow_engine import WorkflowEngine

                    engine = WorkflowEngine(session=MagicMock())
                    engine._current_execution_id = "exec_789"

                    with patch.object(engine, '_save_pending_screenshot_review', new_callable=AsyncMock) as mock_save:
                        mock_save.return_value = 1
                        
                        await engine._handle_screenshot_for_healing(
                            screenshot_bytes=b"fake",
                            url="https://bank.com",
                            task_id=5,
                            step_index=1
                        )

                    mock_notify.assert_called_once()
                    call_args = mock_notify.call_args
                    assert "revisión" in str(call_args).lower() or "review" in str(call_args).lower()
