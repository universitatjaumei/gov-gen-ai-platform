
import pytest
import asyncio
import base64
from unittest.mock import MagicMock, patch, AsyncMock


class TestScreenshotReviewDialog:
    """Tests para el componente de revisión de capturas."""

    @pytest.fixture
    def sample_image_bytes(self):
        """Imagen PNG mínima válida (1x1 pixel transparente)."""
        # PNG 1x1 transparente en base64
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return base64.b64decode(png_b64)

    @pytest.fixture
    def sample_image_base64(self, sample_image_bytes):
        """Imagen en formato base64 string."""
        return base64.b64encode(sample_image_bytes).decode()

    def test_dialog_accepts_bytes_input(self, sample_image_bytes):
        """El diálogo debe aceptar imagen como bytes."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        dialog = ScreenshotReviewDialog(image_data=sample_image_bytes)
        assert dialog.image_base64 is not None
        assert isinstance(dialog.image_base64, str)

    def test_dialog_accepts_base64_input(self, sample_image_base64):
        """El diálogo debe aceptar imagen como base64 string."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        dialog = ScreenshotReviewDialog(image_data=sample_image_base64)
        assert dialog.image_base64 == sample_image_base64

    def test_dialog_has_required_properties(self, sample_image_bytes):
        """El diálogo debe exponer las propiedades necesarias."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        dialog = ScreenshotReviewDialog(
            image_data=sample_image_bytes,
            source_url="https://example.com/page"
        )

        assert hasattr(dialog, 'image_base64')
        assert hasattr(dialog, 'source_url')
        assert hasattr(dialog, 'result')
        assert dialog.source_url == "https://example.com/page"

    def test_dialog_result_starts_as_none(self, sample_image_bytes):
        """El resultado debe ser None hasta que el usuario actúe."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        dialog = ScreenshotReviewDialog(image_data=sample_image_bytes)
        assert dialog.result is None

    def test_approve_sets_result_true(self, sample_image_bytes):
        """Aprobar debe establecer result=True."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        dialog = ScreenshotReviewDialog(image_data=sample_image_bytes)
        dialog._on_approve()
        assert dialog.result is True

    def test_reject_sets_result_false(self, sample_image_bytes):
        """Rechazar debe establecer result=False."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        dialog = ScreenshotReviewDialog(image_data=sample_image_bytes)
        dialog._on_reject()
        assert dialog.result is False

    def test_dialog_includes_warning_text(self, sample_image_bytes):
        """El diálogo debe incluir texto de advertencia."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        # Patch state.i18n.t to return None, forcing default text
        with patch('client_app.app.ui.components.screenshot_review.state') as mock_state:
            mock_state.i18n.t.return_value = None

            dialog = ScreenshotReviewDialog(image_data=sample_image_bytes)
            # El warning_text debe existir y no estar vacío
            assert hasattr(dialog, 'warning_text')
            assert len(dialog.warning_text) > 0
            # Test default spanish text
            assert "confidencial" in dialog.warning_text.lower() or "sensible" in dialog.warning_text.lower()



class TestScreenshotReviewDialogAsync:
    """Tests para el flujo asíncrono del diálogo."""

    @pytest.fixture
    def sample_image_bytes(self):
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return base64.b64decode(png_b64)

    @pytest.mark.asyncio
    async def test_wait_for_result_returns_on_approve(self, sample_image_bytes):
        """wait_for_result debe retornar True cuando se aprueba."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        dialog = ScreenshotReviewDialog(image_data=sample_image_bytes)

        # Simular aprobación después de un delay
        async def approve_later():
            await asyncio.sleep(0.1)
            dialog._on_approve()

        asyncio.create_task(approve_later())
        result = await asyncio.wait_for(dialog.wait_for_result(), timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_result_returns_on_reject(self, sample_image_bytes):
        """wait_for_result debe retornar False cuando se rechaza."""
        from client_app.app.ui.components.screenshot_review import ScreenshotReviewDialog

        dialog = ScreenshotReviewDialog(image_data=sample_image_bytes)

        async def reject_later():
            await asyncio.sleep(0.1)
            dialog._on_reject()

        asyncio.create_task(reject_later())
        result = await asyncio.wait_for(dialog.wait_for_result(), timeout=1.0)
        assert result is False
