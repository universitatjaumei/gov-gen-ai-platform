"""Tests para la dependencia get_current_user (JWT)."""
from unittest.mock import patch

import pytest
from fastapi import HTTPException

JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}


@pytest.mark.asyncio
async def test_valid_jwt_returns_user_info():
    with patch.dict("os.environ", JWT_ENV, clear=False):
        from server.app.core.auth import UserInfo, create_token
        from server.app.api.deps import get_current_user

        user = UserInfo(user_id="u-1", email="admin@test.com", role="admin")
        token = create_token(user)

        result = await get_current_user(authorization=f"Bearer {token}")

        assert result.user_id == "u-1"
        assert result.email == "admin@test.com"
        assert result.role == "admin"


@pytest.mark.asyncio
async def test_invalid_jwt_raises_401():
    with patch.dict("os.environ", JWT_ENV, clear=False):
        from server.app.api.deps import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer not.a.real.token")

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_bearer_prefix_raises_401():
    with patch.dict("os.environ", JWT_ENV, clear=False):
        from server.app.api.deps import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="just-a-token")

        assert exc_info.value.status_code == 401
