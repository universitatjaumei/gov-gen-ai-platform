"""Router para gestión de temas del chatbot.

Deploy: cloud
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session

router = APIRouter(prefix="/hub/themes", tags=["hub-themes"])

_require_partner = require_role("admin", "partner")
_require_admin = require_role("admin")


# ============================================
# Modelos Pydantic
# ============================================

class ThemeColors(BaseModel):
    primary: str = "#0066cc"
    primaryHover: str = "#0052a3"
    primaryLight: str = "#e6f0fa"
    secondary: str = "#6c757d"
    background: str = "#ffffff"
    surface: str = "#f8f9fa"
    text: str = "#212529"
    textSecondary: str = "#6c757d"
    border: str = "#dee2e6"
    error: str = "#dc3545"
    success: str = "#28a745"
    warning: str = "#ffc107"
    botMessage: str = "#f1f3f4"
    botMessageText: str = "#212529"
    userMessage: str = "#0066cc"
    userMessageText: str = "#ffffff"

    model_config = {"extra": "allow"}


class ThemeTypography(BaseModel):
    fontFamily: str = "'Inter', sans-serif"
    fontSize: str = "1rem"
    fontSizeSmall: str = "0.875rem"
    fontSizeLarge: str = "1.125rem"
    fontWeight: int = 400
    fontWeightBold: int = 600
    lineHeight: float = 1.5


class ThemeSpacing(BaseModel):
    xs: str = "0.25rem"
    sm: str = "0.5rem"
    md: str = "1rem"
    lg: str = "1.5rem"
    xl: str = "2rem"


class ThemeConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    version: str = "1.0.0"
    colors: ThemeColors = Field(default_factory=ThemeColors)
    typography: ThemeTypography = Field(default_factory=ThemeTypography)
    spacing: ThemeSpacing = Field(default_factory=ThemeSpacing)
    customCSS: str | None = None

    model_config = {"extra": "allow"}


class ThemeCreate(BaseModel):
    """Sistema de cascada visual:
    - client_id solo: tema nivel cliente (hereda plataforma).
    - chatbot_id: tema nivel chatbot (hereda cliente → plataforma).
    - ninguno: tema de plataforma (solo Admin).
    """
    name: str = Field(..., min_length=1, max_length=100)
    client_id: str | None = None
    chatbot_id: str | None = None
    config: ThemeConfig


class ThemeUpdate(BaseModel):
    config: ThemeConfig


class ThemeResponse(BaseModel):
    id: str
    name: str
    client_id: str | None
    chatbot_id: str | None
    config: dict
    is_default: bool
    created_at: str
    updated_at: str


# ============================================
# Almacenamiento simplificado (en producción usar BD)
# ============================================

THEMES_DIR = Path("data/themes")
THEMES_DIR.mkdir(parents=True, exist_ok=True)


def _theme_path(theme_id: str) -> Path:
    return THEMES_DIR / f"{theme_id}.json"


def _load_theme(theme_id: str) -> dict | None:
    path = _theme_path(theme_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _save_theme(theme_id: str, data: dict) -> None:
    _theme_path(theme_id).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _list_themes() -> list[dict]:
    themes = []
    for path in THEMES_DIR.glob("*.json"):
        try:
            themes.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, IOError):
            continue
    return themes


# ============================================
# Endpoints
# ============================================

@router.get("/presets")
async def get_preset_themes() -> list[dict]:
    """Obtiene los temas predefinidos (no requiere auth)."""
    return [
        {"name": "default", "label": "Predeterminado"},
        {"name": "dark", "label": "Oscuro"},
        {"name": "university", "label": "Universitario"},
        {"name": "high-contrast", "label": "Alto Contraste"},
    ]


@router.get("", response_model=list[ThemeResponse])
async def get_themes(
    client_id: str | None = None,
    chatbot_id: str | None = None,
    user: UserInfo = Depends(_require_partner),
) -> list[dict]:
    """Lista los temas disponibles para el partner.

    Cascada de resolución: plataforma (defaults) → cliente → chatbot.
    """
    themes = _list_themes()
    if chatbot_id:
        themes = [
            t for t in themes
            if t.get("chatbot_id") == chatbot_id
            or t.get("client_id") == client_id
            or t.get("is_default")
        ]
    elif client_id:
        themes = [t for t in themes if t.get("client_id") == client_id or t.get("is_default")]
    return themes


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(theme_id: str) -> dict:
    """Obtiene un tema específico por ID."""
    theme = _load_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    return theme


@router.post("", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
    data: ThemeCreate,
    user: UserInfo = Depends(_require_partner),
) -> dict:
    """Crea un nuevo tema para un cliente o chatbot del partner."""
    theme_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    theme = {
        "id": theme_id,
        "name": data.name,
        "client_id": data.client_id,
        "chatbot_id": data.chatbot_id,
        "config": data.config.model_dump(),
        "is_default": False,
        "created_at": now,
        "updated_at": now,
        "created_by": user.user_id,
    }
    _save_theme(theme_id, theme)
    return theme


@router.put("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    theme_id: str,
    data: ThemeUpdate,
    user: UserInfo = Depends(_require_admin),
) -> dict:
    """Actualiza un tema existente."""
    theme = _load_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    if theme.get("is_default"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify default themes")
    theme["config"] = data.config.model_dump()
    theme["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_theme(theme_id, theme)
    return theme


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(
    theme_id: str,
    user: UserInfo = Depends(_require_admin),
) -> None:
    """Elimina un tema personalizado."""
    theme = _load_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    if theme.get("is_default"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default themes")
    _theme_path(theme_id).unlink()


@router.post("/{theme_id}/apply/{chatbot_id}")
async def apply_theme_to_chatbot(
    theme_id: str,
    chatbot_id: str,
    user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Aplica un tema a un chatbot específico."""
    theme = _load_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    # TODO: actualizar configuración del chatbot en BD cuando se implemente
    return {"message": f"Theme {theme_id} applied to chatbot {chatbot_id}", "theme_name": theme["name"]}
