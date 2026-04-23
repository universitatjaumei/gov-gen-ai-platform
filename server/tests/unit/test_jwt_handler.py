"""Tests para el manejador de JWT - TDD RED PHASE."""
from unittest.mock import patch

import pytest


JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}


class TestJWTValidation:
    def test_valid_token_extracts_user_info(self) -> None:
        with patch.dict("os.environ", JWT_ENV, clear=False):
            from server.app.core.auth.jwt_handler import create_token, decode_token
            from server.app.core.auth.models import UserInfo

            user = UserInfo(user_id="user-123", email="test@example.com", role="admin")
            token = create_token(user)
            decoded = decode_token(token)

            assert decoded.user_id == "user-123"
            assert decoded.email == "test@example.com"
            assert decoded.role == "admin"

    def test_expired_token_raises_error(self) -> None:
        with patch.dict("os.environ", JWT_ENV, clear=False):
            from server.app.core.auth.jwt_handler import create_token, decode_token
            from server.app.core.auth.exceptions import AuthenticationError
            from server.app.core.auth.models import UserInfo

            user = UserInfo(user_id="user-123", email="test@example.com", role="user")
            token = create_token(user, expires_in_minutes=-1)

            with pytest.raises(AuthenticationError) as exc_info:
                decode_token(token)

            assert "expired" in str(exc_info.value).lower()

    def test_invalid_signature_raises_error(self) -> None:
        with patch.dict("os.environ", JWT_ENV, clear=False):
            from server.app.core.auth.jwt_handler import decode_token
            from server.app.core.auth.exceptions import AuthenticationError

            invalid_token = (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9."
                "invalid_signature_here"
            )

            with pytest.raises(AuthenticationError) as exc_info:
                decode_token(invalid_token)

            msg = str(exc_info.value).lower()
            assert "invalid" in msg or "signature" in msg

    def test_token_missing_required_claims_raises_error(self) -> None:
        with patch.dict("os.environ", JWT_ENV, clear=False):
            import jwt
            from server.app.core.auth.jwt_handler import decode_token
            from server.app.core.auth.exceptions import AuthenticationError
            from server.app.core.config import get_settings

            settings = get_settings()
            payload = {"sub": "user-123"}  # falta email
            token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

            with pytest.raises(AuthenticationError) as exc_info:
                decode_token(token)

            msg = str(exc_info.value).lower()
            assert "claim" in msg or "missing" in msg

    def test_malformed_token_raises_error(self) -> None:
        with patch.dict("os.environ", JWT_ENV, clear=False):
            from server.app.core.auth.jwt_handler import decode_token
            from server.app.core.auth.exceptions import AuthenticationError

            for bad_token in ["not.a.valid.jwt.token", "", "just_random_string"]:
                with pytest.raises(AuthenticationError):
                    decode_token(bad_token)
