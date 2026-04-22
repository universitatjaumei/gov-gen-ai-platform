
import pytest
import base64
from unittest.mock import AsyncMock, patch, MagicMock


class TestRPAScreenshotIntegration:
    """Tests de integración para screenshot guard en RPA."""

    @pytest.fixture
    def mock_screenshot_bytes(self):
        """Imagen de prueba."""
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return base64.b64decode(png_b64)

    @pytest.mark.asyncio
    async def test_screenshot_blocked_raises_exception(self, mock_screenshot_bytes):
        """Cuando la política es BLOCK, debe lanzar excepción."""
        from client_app.app.services.screenshot_guard import ScreenshotGuardAction

        # Mock del guard retornando BLOCK
        with patch('client_app.app.modules.rpa.rpa_service.screenshot_guard') as mock_guard:
            mock_guard.check_policy = AsyncMock(return_value=ScreenshotGuardAction.BLOCK)

            from client_app.app.modules.rpa.rpa_service import RPAService

            service = RPAService()

            with pytest.raises(Exception) as exc_info:
                await service.send_screenshot_to_brain(
                    screenshot=mock_screenshot_bytes,
                    url="https://example.com",
                    prompt="Ayúdame a encontrar el botón"
                )

            assert "bloqueado" in str(exc_info.value).lower() or "blocked" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_screenshot_review_approved_proceeds(self, mock_screenshot_bytes):
        """Cuando REVIEW y usuario aprueba, debe enviar al Brain."""
        from client_app.app.services.screenshot_guard import ScreenshotGuardAction

        with patch('client_app.app.modules.rpa.rpa_service.screenshot_guard') as mock_guard:
            mock_guard.check_policy = AsyncMock(return_value=ScreenshotGuardAction.REQUIRE_REVIEW)

            with patch('client_app.app.modules.rpa.rpa_service.request_screenshot_approval') as mock_approval:
                mock_approval.return_value = True  # Usuario aprueba

                with patch('client_app.app.modules.rpa.rpa_service.brain_client') as mock_brain:
                    mock_brain.send_visual_request = AsyncMock(return_value={"selector": "#btn"})

                    from client_app.app.modules.rpa.rpa_service import RPAService
                    service = RPAService()

                    result = await service.send_screenshot_to_brain(
                        screenshot=mock_screenshot_bytes,
                        url="https://example.com",
                        prompt="Encuentra el botón"
                    )

                    # Verificar que se llamó al Brain
                    mock_brain.send_visual_request.assert_called_once()
                    assert result is not None

    @pytest.mark.asyncio
    async def test_screenshot_review_rejected_returns_none(self, mock_screenshot_bytes):
        """Cuando REVIEW y usuario rechaza, no debe enviar y retornar None."""
        from client_app.app.services.screenshot_guard import ScreenshotGuardAction

        with patch('client_app.app.modules.rpa.rpa_service.screenshot_guard') as mock_guard:
            mock_guard.check_policy = AsyncMock(return_value=ScreenshotGuardAction.REQUIRE_REVIEW)

            with patch('client_app.app.modules.rpa.rpa_service.request_screenshot_approval') as mock_approval:
                mock_approval.return_value = False  # Usuario rechaza

                with patch('client_app.app.modules.rpa.rpa_service.brain_client') as mock_brain:
                    from client_app.app.modules.rpa.rpa_service import RPAService
                    service = RPAService()

                    result = await service.send_screenshot_to_brain(
                        screenshot=mock_screenshot_bytes,
                        url="https://example.com",
                        prompt="Encuentra el botón"
                    )

                    # NO debe llamar al Brain
                    mock_brain.send_visual_request.assert_not_called()
                    assert result is None

    @pytest.mark.asyncio
    async def test_trusted_domain_skips_review(self, mock_screenshot_bytes):
        """Cuando ALLOW (trusted), debe enviar sin pedir aprobación."""
        from client_app.app.services.screenshot_guard import ScreenshotGuardAction

        with patch('client_app.app.modules.rpa.rpa_service.screenshot_guard') as mock_guard:
            mock_guard.check_policy = AsyncMock(return_value=ScreenshotGuardAction.ALLOW)

            with patch('client_app.app.modules.rpa.rpa_service.request_screenshot_approval') as mock_approval:
                with patch('client_app.app.modules.rpa.rpa_service.brain_client') as mock_brain:
                    mock_brain.send_visual_request = AsyncMock(return_value={"result": "ok"})

                    from client_app.app.modules.rpa.rpa_service import RPAService
                    service = RPAService()

                    await service.send_screenshot_to_brain(
                        screenshot=mock_screenshot_bytes,
                        url="https://boe.es/doc",
                        prompt="Prompt"
                    )

                    # NO debe pedir aprobación
                    mock_approval.assert_not_called()
                    # SÍ debe enviar al Brain
                    mock_brain.send_visual_request.assert_called_once()
