"""Tests para el servicio de observabilidad LangFuse."""
import pytest
from unittest.mock import patch, MagicMock


class TestObservabilityClient:

    def setup_method(self):
        from server.app.modules.agents_hub.services import observability
        observability.get_langfuse_client.cache_clear()

    def teardown_method(self):
        from server.app.modules.agents_hub.services import observability
        observability.get_langfuse_client.cache_clear()

    def test_returns_none_when_secret_key_missing(self) -> None:
        from server.app.modules.agents_hub.services.observability import get_langfuse_client

        with patch.dict("os.environ", {}, clear=True):
            client = get_langfuse_client()

        assert client is None

    def test_returns_client_when_configured(self) -> None:
        from server.app.modules.agents_hub.services.observability import get_langfuse_client

        env = {
            "LANGFUSE_PUBLIC_KEY": "lf-pk-test",
            "LANGFUSE_SECRET_KEY": "lf-sk-test",
            "LANGFUSE_HOST": "http://localhost:3000",
        }
        with patch.dict("os.environ", env):
            with patch("server.app.modules.agents_hub.services.observability.Langfuse") as mock_cls:
                mock_cls.return_value = MagicMock()
                client = get_langfuse_client()

        assert client is not None


class TestCallbackHandler:

    def test_returns_none_when_not_configured(self) -> None:
        from server.app.modules.agents_hub.services.observability import create_callback_handler

        with patch.dict("os.environ", {}, clear=True):
            handler = create_callback_handler(session_id="sess-1", user_id="user-1")

        assert handler is None

    def test_returns_handler_when_configured(self) -> None:
        from server.app.modules.agents_hub.services.observability import create_callback_handler

        env = {
            "LANGFUSE_PUBLIC_KEY": "lf-pk-test",
            "LANGFUSE_SECRET_KEY": "lf-sk-test",
            "LANGFUSE_HOST": "http://localhost:3000",
        }
        with patch.dict("os.environ", env):
            with patch(
                "server.app.modules.agents_hub.services.observability.CallbackHandler"
            ) as mock_cls:
                mock_instance = MagicMock()
                mock_cls.return_value = mock_instance
                handler = create_callback_handler(session_id="sess-1", user_id="user-1")
                mock_cls.assert_called_once_with()

        assert handler is not None
