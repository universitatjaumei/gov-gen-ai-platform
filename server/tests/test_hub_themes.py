"""Tests para el sistema de temas (hub_themes_router)."""
import pytest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from server.app.core.auth.models import UserInfo
from server.app.api.deps import get_current_user


@pytest.fixture
def sample_theme_config():
    return {
        "name": "test-theme",
        "version": "1.0.0",
        "colors": {
            "primary": "#ff0000",
            "primaryHover": "#cc0000",
            "primaryLight": "#ffcccc",
            "secondary": "#00ff00",
            "background": "#ffffff",
            "surface": "#f0f0f0",
            "text": "#000000",
            "textSecondary": "#666666",
            "border": "#cccccc",
            "error": "#ff0000",
            "success": "#00ff00",
            "warning": "#ffff00",
            "botMessage": "#e0e0e0",
            "botMessageText": "#000000",
            "userMessage": "#0066cc",
            "userMessageText": "#ffffff",
        },
        "typography": {
            "fontFamily": "'Arial', sans-serif",
            "fontSize": "16px",
            "fontSizeSmall": "14px",
            "fontSizeLarge": "18px",
            "fontWeight": 400,
            "fontWeightBold": 700,
            "lineHeight": 1.6,
        },
        "spacing": {
            "xs": "4px",
            "sm": "8px",
            "md": "16px",
            "lg": "24px",
            "xl": "32px",
        },
    }


@pytest.fixture
def test_app():
    from server.app.routers.hub_themes_router import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


class TestThemeValidation:
    """Tests para validación del modelo ThemeConfig."""

    def test_valid_theme_passes_validation(self, sample_theme_config):
        from server.app.routers.hub_themes_router import ThemeConfig

        theme = ThemeConfig(**sample_theme_config)
        assert theme.name == "test-theme"
        assert theme.colors.primary == "#ff0000"

    def test_invalid_theme_name_fails(self):
        from server.app.routers.hub_themes_router import ThemeConfig
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ThemeConfig(name="", version="1.0.0")

    def test_extra_fields_allowed(self, sample_theme_config):
        from server.app.routers.hub_themes_router import ThemeConfig

        sample_theme_config["customField"] = "custom-value"
        theme = ThemeConfig(**sample_theme_config)
        assert theme.name == "test-theme"


class TestThemeAPI:
    """Tests de integración para los endpoints de la API de temas."""

    @pytest.mark.asyncio
    async def test_get_presets(self, test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/hub/themes/presets")

        assert response.status_code == 200
        presets = response.json()
        assert len(presets) >= 3
        preset_names = [p["name"] for p in presets]
        assert "default" in preset_names
        assert "dark" in preset_names

    @pytest.mark.asyncio
    async def test_create_theme_requires_auth(self, test_app, sample_theme_config):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/hub/themes",
                json={"name": "new-theme", "config": sample_theme_config},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_theme_success(self, test_app, sample_theme_config, tmp_path):
        def mock_user():
            return UserInfo(user_id="test-user", email="test@example.com", role="partner")

        test_app.dependency_overrides[get_current_user] = mock_user

        try:
            with patch("server.app.routers.hub_themes_router.THEMES_DIR", tmp_path):
                async with AsyncClient(
                    transport=ASGITransport(app=test_app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/v1/hub/themes",
                        json={"name": "new-theme", "config": sample_theme_config},
                    )
        finally:
            test_app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new-theme"
        assert "id" in data


class TestThemeStorage:
    """Tests para las funciones de almacenamiento de temas."""

    def test_save_and_load_theme(self, sample_theme_config, tmp_path):
        from server.app.routers.hub_themes_router import _save_theme, _load_theme

        theme_id = "test-theme-123"
        theme_data = {
            "id": theme_id,
            "name": "Test Theme",
            "config": sample_theme_config,
        }

        with patch("server.app.routers.hub_themes_router.THEMES_DIR", tmp_path):
            _save_theme(theme_id, theme_data)
            loaded = _load_theme(theme_id)

        assert loaded is not None
        assert loaded["name"] == "Test Theme"
        assert loaded["config"]["colors"]["primary"] == "#ff0000"
