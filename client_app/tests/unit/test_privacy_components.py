import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from client_app.app.ui.components.privacy_indicator import render_privacy_indicator
from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

# --- PrivacyIndicator Tests ---

@patch('client_app.app.ui.components.privacy_indicator.ui')
def test_privacy_indicator_calls_ui_methods(mock_ui):
    """Verifica que render_privacy_indicator llama a métodos UI esperados."""
    # Mock state.i18n.t
    with patch('client_app.app.ui.components.privacy_indicator.state') as mock_state:
        mock_state.i18n.t = lambda x: x # Identity function for translation
        
        render_privacy_indicator()
        
        # Verify card creation
        mock_ui.card.assert_called()
        # Verify icon for privacy
        mock_ui.icon.assert_any_call('verified_user', color='green', size='md')
        # Verify labels
        mock_ui.label.assert_called()

# --- ScreenshotReviewDialog Tests ---

class TestScreenshotReviewDialog:
    """Tests para el diálogo de revisión de screenshots."""

    def test_init_sets_attributes(self):
        """Inicialización correcta de atributos."""
        image_data = "base64data"
        dialog = ScreenshotReviewDialog(image_data=image_data, source_url="http://test.com")
        
        assert dialog.image_base64 == "base64data"
        assert dialog.source_url == "http://test.com"
        assert dialog.result is None

    @pytest.mark.asyncio
    async def test_approve_sets_true(self):
        """Aprobar establece result=True y cierra diálogo."""
        dialog = ScreenshotReviewDialog(image_data="test")
        dialog._dialog = Mock()
        
        # Trigger approve
        dialog._on_approve()
        
        assert dialog.result is True
        dialog._dialog.close.assert_called_once()
        assert dialog._result_event.is_set()

    @pytest.mark.asyncio
    async def test_reject_sets_false(self):
        """Rechazar establece result=False."""
        dialog = ScreenshotReviewDialog(image_data="test")
        dialog._dialog = Mock()
        
        dialog._on_reject()
        
        assert dialog.result is False
        dialog._dialog.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_result_returns_decision(self):
        """Testear flujo de espera."""
        dialog = ScreenshotReviewDialog(image_data="test")
        
        # Simulate interaction in background
        async def simulate_user():
            await asyncio.sleep(0.1)
            dialog._on_approve()

        import asyncio
        task = asyncio.create_task(simulate_user())
        result = await dialog.wait_for_result()
        
        await task
        assert result is True
