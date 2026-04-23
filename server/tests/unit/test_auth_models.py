"""Tests para modelos de autenticación - TDD RED PHASE."""
from dataclasses import FrozenInstanceError

import pytest


class TestUserInfoModel:
    def test_user_info_has_required_fields(self) -> None:
        from server.app.core.auth.models import UserInfo

        user = UserInfo(user_id="user-123", email="test@example.com", role="admin")

        assert user.user_id == "user-123"
        assert user.email == "test@example.com"
        assert user.role == "admin"

    def test_user_info_is_immutable(self) -> None:
        from server.app.core.auth.models import UserInfo

        user = UserInfo(user_id="user-123", email="test@example.com", role="user")

        with pytest.raises((FrozenInstanceError, AttributeError)):
            user.user_id = "other-id"  # type: ignore

    def test_user_info_serializable_to_dict(self) -> None:
        from server.app.core.auth.models import UserInfo

        user = UserInfo(user_id="user-123", email="test@example.com", role="admin")
        user_dict = user.to_dict()

        assert isinstance(user_dict, dict)
        assert user_dict["user_id"] == "user-123"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["role"] == "admin"

    def test_user_info_role_validation(self) -> None:
        from server.app.core.auth.models import UserInfo

        for role in ["user", "admin", "partner", "informer"]:
            user = UserInfo(user_id="123", email="test@test.com", role=role)
            assert user.role == role

    def test_user_info_invalid_role_raises_error(self) -> None:
        from server.app.core.auth.models import UserInfo

        with pytest.raises(ValueError):
            UserInfo(user_id="123", email="test@test.com", role="superuser")


class TestUserRole:
    def test_user_role_values(self) -> None:
        from server.app.core.auth.models import UserRole

        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.PARTNER.value == "partner"
        assert UserRole.INFORMER.value == "informer"
