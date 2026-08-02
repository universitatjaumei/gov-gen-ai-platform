"""Router para gestión de temas del chatbot.

Deploy: cloud
"""
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo
from server.app.core.auth.tenancy import assert_org_access, puede_acceder
from server.app.modules.agents_hub.database.connection import get_async_session

router = APIRouter(prefix="/hub/themes", tags=["hub-themes"])

_require_admin = require_role("superadmin", "admin")
_require_superadmin = require_role("superadmin")


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
    - organizacion_id solo: tema nivel cliente (hereda plataforma).
    - chatbot_id: tema nivel chatbot (hereda cliente → plataforma).
    - ninguno: tema de plataforma (solo Admin).
    """
    name: str = Field(..., min_length=1, max_length=100)
    organizacion_id: str | None = None
    chatbot_id: str | None = None
    config: ThemeConfig


class ThemeUpdate(BaseModel):
    config: ThemeConfig


class ThemeResponse(BaseModel):
    id: str
    name: str
    organizacion_id: str | None
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


_ID_DE_TEMA = re.compile(r"^[a-z0-9-]{1,64}$")


def _theme_path(theme_id: str) -> Path:
    """La ruta del fichero del tema, o 400 si el identificador no es un identificador.

    SEC.5: esto construía una ruta concatenando lo que llegara en la URL. Con `../` bastaba
    para leer —y con DELETE, para borrar— cualquier `.json` del servidor. Dos cierres, y los
    dos hacen falta:

    - **La forma**: solo minúsculas, dígitos y guiones. Los identificadores reales son UUID,
      así que la regla no aprieta nada; deja fuera `..`, `/`, `%2f` decodificado y las rutas
      absolutas de Windows de una vez.
    - **El destino resuelto**: aunque la forma pase, la ruta final tiene que caer dentro de
      `THEMES_DIR`. Comprobar solo la cadena es apostar a que uno ha pensado en todas las
      codificaciones posibles; comprobar el destino es no tener que acertar.
    """
    if not _ID_DE_TEMA.match(theme_id or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de tema inválido",
        )

    destino = (THEMES_DIR / f"{theme_id}.json").resolve()
    if not destino.is_relative_to(THEMES_DIR.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de tema inválido",
        )
    return destino


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
    organizacion_id: str | None = None,
    chatbot_id: str | None = None,
    user: UserInfo = Depends(_require_admin),
) -> list[dict]:
    """Lista los temas disponibles para el partner.

    Cascada de resolución: plataforma (defaults) → cliente → chatbot.
    """
    themes = _list_themes()
    # SEC.2: el listado se acota a lo que el principal gestiona. Los temas de
    # plataforma (`is_default`) los ve todo el mundo: son la base de la cascada.
    themes = [
        t for t in themes
        if t.get("is_default") or puede_acceder(user, t.get("organizacion_id"))
    ]
    if chatbot_id:
        themes = [
            t for t in themes
            if t.get("chatbot_id") == chatbot_id
            or t.get("organizacion_id") == organizacion_id
            or t.get("is_default")
        ]
    elif organizacion_id:
        themes = [t for t in themes if t.get("organizacion_id") == organizacion_id or t.get("is_default")]
    return themes


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(
    theme_id: str,
    user: UserInfo = Depends(_require_admin),
) -> dict:
    """Obtiene un tema específico por ID.

    SEC.5: hasta aquí era **público**. Un tema no es un secreto de estado, pero lleva los
    colores, el logotipo y el nombre de la organización a la que pertenece, así que la lista
    de temas es un censo de clientes servido sin pedir nada.

    Los temas de plataforma (`is_default`) los ve cualquier administrador: son la base de la
    cascada y no pertenecen a nadie. Los de una organización, solo quien la gestiona.
    """
    theme = _load_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    if not theme.get("is_default") and theme.get("organizacion_id"):
        assert_org_access(user, theme["organizacion_id"])
    return theme


@router.post("", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
    data: ThemeCreate,
    user: UserInfo = Depends(_require_admin),
) -> dict:
    """Crea un nuevo tema para un cliente o chatbot del partner."""
    # SEC.2: la organización viene del CUERPO de la petición, así que sin esto un admin
    # podía crear un tema en la organización que escribiera. Se comprueba contra el
    # token: el cliente propone, el token dispone.
    #
    # Sin organización, el tema es **de plataforma** y lo ven todas: eso es un superadmin.
    # Antes de SEC.2 cualquier admin podía crear uno, y un tema de plataforma se cuela en la
    # cascada de todas las organizaciones.
    if data.organizacion_id is None:
        if not user.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Un tema sin organización es de plataforma y lo hereda todo el mundo: "
                    "solo un superadministrador puede crearlo. Indica `organizacion_id`."
                ),
            )
    else:
        assert_org_access(user, data.organizacion_id)
    theme_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    theme = {
        "id": theme_id,
        "name": data.name,
        "organizacion_id": data.organizacion_id,
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
    user: UserInfo = Depends(_require_superadmin),
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
    user: UserInfo = Depends(_require_superadmin),
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
    user: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Aplica un tema a un chatbot específico."""
    theme = _load_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    # TODO: actualizar configuración del chatbot en BD cuando se implemente
    return {"message": f"Theme {theme_id} applied to chatbot {chatbot_id}", "theme_name": theme["name"]}
