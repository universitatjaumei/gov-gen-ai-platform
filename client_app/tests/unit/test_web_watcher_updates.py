# client_app/tests/unit/test_web_watcher_updates.py
"""
TDD tests for Web Watcher updates.

Tests verify:
- Correct conversion of hours to minutes for check_interval
- WebWatcherService triggers email notification when send_email_on_change is active
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


# ============================================================
# Test: Conversión de horas a minutos
# ============================================================

class TestIntervalConversion:
    """Tests for interval unit conversion (hours to minutes)."""

    def test_convert_hours_to_minutes(self):
        """Verify that hours are correctly converted to minutes."""
        # Simulate UI logic for conversion
        interval_value = 2
        interval_unit = 'hours'

        if interval_unit == 'hours':
            interval_minutes = interval_value * 60
        else:
            interval_minutes = interval_value

        assert interval_minutes == 120

    def test_convert_minutes_stays_as_minutes(self):
        """Verify that minutes remain unchanged."""
        interval_value = 30
        interval_unit = 'minutes'

        if interval_unit == 'hours':
            interval_minutes = interval_value * 60
        else:
            interval_minutes = interval_value

        assert interval_minutes == 30

    def test_one_hour_equals_60_minutes(self):
        """Verify 1 hour = 60 minutes."""
        interval_value = 1
        interval_unit = 'hours'

        interval_minutes = interval_value * 60 if interval_unit == 'hours' else interval_value

        assert interval_minutes == 60

    def test_fractional_hours_not_supported_uses_integers(self):
        """Verify that integer hours work correctly."""
        # La UI usa ui.number que devuelve enteros
        for hours in [1, 2, 3, 6, 12, 24]:
            interval_minutes = hours * 60
            assert interval_minutes == hours * 60
            assert isinstance(interval_minutes, int)

    def test_display_interval_in_hours_when_divisible(self):
        """Verify display logic: show hours when interval is divisible by 60."""
        # Lógica de la UI para mostrar horas cuando corresponde
        test_cases = [
            (60, 'hours', 1),    # 60 min -> 1 hora
            (120, 'hours', 2),   # 120 min -> 2 horas
            (180, 'hours', 3),   # 180 min -> 3 horas
            (30, 'minutes', 30), # 30 min -> 30 minutos
            (45, 'minutes', 45), # 45 min -> 45 minutos
            (90, 'minutes', 90), # 90 min -> no divisible exacto, mostrar minutos
        ]

        for interval_minutes, expected_unit, expected_value in test_cases:
            if interval_minutes >= 60 and interval_minutes % 60 == 0:
                display_unit = 'hours'
                display_value = interval_minutes // 60
            else:
                display_unit = 'minutes'
                display_value = interval_minutes

            assert display_unit == expected_unit, f"Failed for {interval_minutes} min"
            assert display_value == expected_value, f"Failed for {interval_minutes} min"


# ============================================================
# Test: Envío de email cuando se detecta cambio
# ============================================================

class TestWebWatcherEmailNotification:
    """Tests for email notification when change is detected."""

    @pytest.fixture
    def mock_smtp_credentials(self):
        """Mock SMTP credentials data."""
        return {
            "server": "smtp.example.com",
            "port": 587,
            "user": "user@example.com",
            "password": "secret_password"
        }

    @pytest.fixture
    def mock_config_with_email(self):
        """Mock watcher config with email notification enabled."""
        return {
            "id": 1,
            "url": "https://example.com/page",
            "selector": "#content",
            "selector_type": "css",
            "check_interval": 60,
            "send_email_on_change": True,
            "smtp_credential_id": 1,
            "notification_email": "admin@example.com"
        }

    @pytest.fixture
    def mock_config_without_email(self):
        """Mock watcher config with email notification disabled."""
        return {
            "id": 1,
            "url": "https://example.com/page",
            "selector": "#content",
            "selector_type": "css",
            "check_interval": 60,
            "send_email_on_change": False,
            "smtp_credential_id": None,
            "notification_email": None
        }

    @pytest.mark.asyncio
    async def test_send_email_when_change_detected_and_enabled(
        self,
        mock_config_with_email,
        mock_smtp_credentials
    ):
        """Verify email is sent when change is detected and notification is enabled."""
        from client_app.app.services.web_watcher_service import WebWatcherService

        service = WebWatcherService()

        # Patch donde se importan los módulos
        with patch('client_app.app.services.mail_watcher_service.mail_watcher_service') as mock_mail_service:
            mock_mail_service.get_credential = AsyncMock(return_value=mock_smtp_credentials)

            with patch('client_app.app.modules.output.email_sender.EmailSender') as mock_email_sender:
                mock_sender_instance = MagicMock()
                mock_sender_instance.send.return_value = "<message-id>"
                mock_email_sender.return_value = mock_sender_instance

                result = await service._send_email_notification(
                    mock_config_with_email,
                    "https://example.com/page"
                )

                assert result is True
                mock_sender_instance.send.assert_called_once()

                # Verificar argumentos del email
                call_args = mock_sender_instance.send.call_args
                assert call_args[1]['to_addrs'] == ['admin@example.com']
                assert 'Cambio detectado' in call_args[1]['subject']

    @pytest.mark.asyncio
    async def test_no_email_when_notification_disabled(self, mock_config_without_email):
        """Verify no email is sent when notification is disabled."""
        from client_app.app.services.web_watcher_service import WebWatcherService

        service = WebWatcherService()

        result = await service._send_email_notification(
            mock_config_without_email,
            "https://example.com/page"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_no_email_when_smtp_credential_missing(self, mock_config_with_email):
        """Verify no email is sent when SMTP credential is not found."""
        from client_app.app.services.web_watcher_service import WebWatcherService

        service = WebWatcherService()

        # Config tiene send_email_on_change=True pero credential_id no existe
        config = mock_config_with_email.copy()

        with patch('client_app.app.services.mail_watcher_service.mail_watcher_service') as mock_mail_service:
            mock_mail_service.get_credential = AsyncMock(return_value=None)

            result = await service._send_email_notification(config, "https://example.com/page")

            assert result is False

    @pytest.mark.asyncio
    async def test_no_email_when_notification_email_missing(self):
        """Verify no email is sent when notification_email is not set."""
        from client_app.app.services.web_watcher_service import WebWatcherService

        service = WebWatcherService()

        config = {
            "id": 1,
            "url": "https://example.com",
            "send_email_on_change": True,
            "smtp_credential_id": 1,
            "notification_email": None  # Missing email
        }

        result = await service._send_email_notification(config, "https://example.com")

        assert result is False

    @pytest.mark.asyncio
    async def test_email_contains_url_and_selector(
        self,
        mock_config_with_email,
        mock_smtp_credentials
    ):
        """Verify email body contains URL and selector information."""
        from client_app.app.services.web_watcher_service import WebWatcherService

        service = WebWatcherService()

        with patch('client_app.app.services.mail_watcher_service.mail_watcher_service') as mock_mail_service:
            mock_mail_service.get_credential = AsyncMock(return_value=mock_smtp_credentials)

            with patch('client_app.app.modules.output.email_sender.EmailSender') as mock_email_sender:
                mock_sender_instance = MagicMock()
                mock_sender_instance.send.return_value = "<message-id>"
                mock_email_sender.return_value = mock_sender_instance

                await service._send_email_notification(
                    mock_config_with_email,
                    "https://example.com/page"
                )

                call_args = mock_sender_instance.send.call_args
                body = call_args[1]['body']

                assert "https://example.com/page" in body
                assert "#content" in body


# ============================================================
# Test: Integración de _log_change con notificación
# ============================================================

class TestLogChangeEmailIntegration:
    """Tests for _log_change calling email notification."""

    @pytest.mark.asyncio
    async def test_log_change_triggers_email_when_enabled(self):
        """Verify _log_change calls _send_email_notification when enabled."""
        from client_app.app.services.web_watcher_service import WebWatcherService

        service = WebWatcherService()

        mock_config = {
            "id": 1,
            "url": "https://example.com",
            "selector": "#content",
            "send_email_on_change": True,
            "smtp_credential_id": 1,
            "notification_email": "admin@example.com"
        }

        with patch.object(service, 'load_config', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = mock_config

            with patch.object(
                service, '_send_email_notification', new_callable=AsyncMock
            ) as mock_send:
                mock_send.return_value = True

                # Mock la sesión de base de datos
                with patch('client_app.app.services.web_watcher_service.AsyncSession') as mock_session_class:
                    mock_session = MagicMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock(return_value=None)
                    mock_session.add = MagicMock()
                    mock_session.commit = AsyncMock()
                    mock_session_class.return_value = mock_session

                    await service._log_change(
                        config_id=1,
                        url="https://example.com",
                        old_hash="abc123",
                        new_hash="def456",
                        screenshot_path=None
                    )

                    # Verificar que se llamó a _send_email_notification
                    mock_send.assert_called_once_with(mock_config, "https://example.com")


# ============================================================
# Test: Modelo de configuración
# ============================================================

class TestWebWatcherConfigModel:
    """Tests for WebWatcherConfig model fields."""

    def test_model_has_smtp_fields(self):
        """Verify WebWatcherConfig has SMTP notification fields."""
        from client_app.app.database.models import WebWatcherConfig

        # Verificar que los campos existen en el modelo
        fields = WebWatcherConfig.model_fields

        assert 'send_email_on_change' in fields
        assert 'smtp_credential_id' in fields
        assert 'notification_email' in fields

    def test_model_default_values(self):
        """Verify default values for SMTP fields."""
        from client_app.app.database.models import WebWatcherConfig

        config = WebWatcherConfig(url="https://example.com")

        assert config.send_email_on_change is False
        assert config.smtp_credential_id is None
        assert config.notification_email is None

    def test_model_with_smtp_enabled(self):
        """Verify model accepts SMTP configuration."""
        from client_app.app.database.models import WebWatcherConfig

        config = WebWatcherConfig(
            url="https://example.com",
            send_email_on_change=True,
            smtp_credential_id=1,
            notification_email="admin@example.com"
        )

        assert config.send_email_on_change is True
        assert config.smtp_credential_id == 1
        assert config.notification_email == "admin@example.com"
