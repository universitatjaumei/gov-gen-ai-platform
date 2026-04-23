"""Tests de integración para rutas protegidas con JWT."""
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from server.app.api.deps import get_current_user, require_role
from server.app.core.auth import UserInfo

JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}

app = FastAPI()


@app.get("/test-protected")
async def protected_route(user: UserInfo = Depends(get_current_user)):
    return {"email": user.email, "role": user.role}


@app.get("/test-admin-only")
async def admin_only_route(user: UserInfo = Depends(require_role("admin"))):
    return {"email": user.email}


def _make_token(role: str, email: str = "test@test.com", user_id: str = "u-1") -> str:
    from server.app.core.auth import create_token
    return create_token(UserInfo(user_id=user_id, email=email, role=role))


def test_valid_jwt_returns_user_info():
    with patch.dict("os.environ", JWT_ENV, clear=False):
        token = _make_token("admin", "admin@test.com")
        client = TestClient(app)

        response = client.get("/test-protected", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["email"] == "admin@test.com"
        assert response.json()["role"] == "admin"


def test_partner_jwt_is_accepted():
    with patch.dict("os.environ", JWT_ENV, clear=False):
        token = _make_token("partner", "partner@test.com")
        client = TestClient(app)

        response = client.get("/test-protected", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["role"] == "partner"


def test_missing_authorization_header_returns_401():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-protected")
    assert response.status_code == 401


def test_invalid_token_returns_401():
    with patch.dict("os.environ", JWT_ENV, clear=False):
        client = TestClient(app)
        response = client.get("/test-protected", headers={"Authorization": "Bearer bad.token.here"})
        assert response.status_code == 401


def test_wrong_role_returns_403():
    with patch.dict("os.environ", JWT_ENV, clear=False):
        token = _make_token("partner")
        client = TestClient(app)

        response = client.get("/test-admin-only", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 403
