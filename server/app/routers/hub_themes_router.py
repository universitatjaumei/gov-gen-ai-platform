"""Router para gestión de temas del chatbot.

Deploy: cloud

`get_theme_for_chatbot` es la excepción: la consume el widget público, que es tráfico
edge (mismo consumidor que `hub_chat_router`). Se queda aquí porque hoy `DEPLOY_MODE=all`
registra los dos bloques igual. **Pendiente si se llega a desplegar `edge` sin `cloud`**:
hoy ese endpoint 404earía porque este router no se registra en `_register_edge`. Desde
SEC.8.6 el obstáculo es menor de lo que era —los temas viven en `hub_themes`, una tabla de
`HubConfigBase` que se sincroniza cloud→edge, y no en un almacén propiedad de este módulo—.
"""
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import (
    get_current_user,
    get_current_user_optional,
    require_role,
)
from server.app.core.auth.chatbot_access import VIA_WIDGET, assert_chatbot_access
from server.app.core.auth.widget_key import (
    CABECERA as CABECERA_WIDGET,
    resolver_widget_key,
)
from server.app.core.auth.delegated_actor import resolve_effective_actor
from server.app.core.auth.models import UserInfo
from server.app.core.auth.tenancy import assert_org_access, puede_acceder
from server.app.modules.agents_hub.database.config_models import HubChatbot, HubTheme
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


class ChatbotThemeOut(BaseModel):
    """Solo `config` -- sin owner_id/theme_id/name: ver `get_theme_for_chatbot`."""

    config: dict = Field(default_factory=dict)


# ============================================
# Almacenamiento en base de datos (SEC.8.6)
# ============================================
#
# Antes eran ficheros `.json` bajo `data/themes`, una ruta relativa al directorio de
# trabajo. En Cloud Run el contenedor es efímero y hay varias instancias, así que el tema
# creado en una no existía para las demás y desaparecía al reciclarse — arrastrando al
# widget, que resuelve su contenido desde el puntero `theme_config`.
#
# La validación de forma del identificador se conserva: ya no protege una ruta, pero un
# `theme_id` que no es un UUID no puede corresponder a ningún tema, y rechazarlo antes de
# consultar es más claro que un 404 desde la capa de datos.

_ID_DE_TEMA = re.compile(r"^[a-z0-9-]{1,64}$")


def _assert_id_de_tema(theme_id: str) -> uuid.UUID:
    if not _ID_DE_TEMA.match(theme_id or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de tema inválido",
        )
    try:
        return uuid.UUID(theme_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de tema inválido",
        ) from None


def _a_dict(tema: HubTheme) -> dict:
    """La forma que ya devolvía el router, para no tocar el contrato de la API."""
    return {
        "id": str(tema.id),
        "name": tema.name,
        # Cadenas y no UUID: es lo que declara `ThemeResponse` y con lo que comparan los
        # filtros del listado, que reciben el id por query.
        "organizacion_id": str(tema.organizacion_id) if tema.organizacion_id else None,
        "chatbot_id": str(tema.chatbot_id) if tema.chatbot_id else None,
        "config": tema.config or {},
        "is_default": tema.is_default,
        "created_at": tema.created_at.isoformat() if tema.created_at else None,
        "updated_at": tema.updated_at.isoformat() if tema.updated_at else None,
        "created_by": tema.created_by,
    }


async def _load_theme(session, theme_id: str) -> dict | None:
    tema = await session.get(HubTheme, _assert_id_de_tema(theme_id))
    return _a_dict(tema) if tema is not None else None


async def _list_themes(session) -> list[dict]:
    filas = (await session.execute(select(HubTheme))).scalars().all()
    return [_a_dict(t) for t in filas]


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
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """Lista los temas disponibles para el partner.

    Cascada de resolución: plataforma (defaults) → cliente → chatbot.
    """
    themes = await _list_themes(session)
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


@router.get("/for-chatbot/{chatbot_id}", response_model=ChatbotThemeOut)
async def get_theme_for_chatbot(
    chatbot_id: uuid.UUID,
    http_request: Request,
    user: UserInfo | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_async_session),
) -> ChatbotThemeOut:
    """Tema resuelto de un chatbot, para pintar el widget público.

    SEC.5 cerró `GET /{theme_id}` porque un tema lleva `organizacion_id`: servido sin más
    era un censo de qué organizaciones existen. Este endpoint no reabre ese hueco -- solo
    devuelve `config` (colores/tipografía), nunca el `theme_id`, el `organizacion_id` ni el
    nombre del tema -- y exige el mismo acceso que conversar con el chatbot (SEC.2.1): quien
    no podría abrir el chat tampoco ve de qué color lo pintarían.
    """
    chatbot = await session.get(HubChatbot, chatbot_id)
    if chatbot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")

    # SEC.8.5: dos vías, y la diferencia la marca `via`. Con sesión decide la identidad;
    # con credencial de sitio no hay identidad ninguna, así que `assert_chatbot_access`
    # solo deja pasar `public_anon`. Antes el widget mandaba un Bearer privilegiado por
    # esta misma ruta, que es lo que se viene a quitar.
    clave = await resolver_widget_key(session, http_request.headers.get(CABECERA_WIDGET))
    if clave is not None and clave.chatbot_id == chatbot_id:
        assert_chatbot_access(None, chatbot, via=VIA_WIDGET)
    else:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
        actor = resolve_effective_actor(http_request, user)
        assert_chatbot_access(actor, chatbot, via="session")

    theme_id = (chatbot.theme_config or {}).get("theme_id")
    if theme_id:
        theme = await _load_theme(session, theme_id)
        if theme:
            return ChatbotThemeOut(config=theme.get("config", {}))
    return ChatbotThemeOut(config={})


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(
    theme_id: str,
    user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Obtiene un tema específico por ID.

    SEC.5: hasta aquí era **público**. Un tema no es un secreto de estado, pero lleva los
    colores, el logotipo y el nombre de la organización a la que pertenece, así que la lista
    de temas es un censo de clientes servido sin pedir nada.

    Los temas de plataforma (`is_default`) los ve cualquier administrador: son la base de la
    cascada y no pertenecen a nadie. Los de una organización, solo quien la gestiona.
    """
    theme = await _load_theme(session, theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    if not theme.get("is_default") and theme.get("organizacion_id"):
        assert_org_access(user, theme["organizacion_id"])
    return theme


@router.post("", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
    data: ThemeCreate,
    user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
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
    ahora = datetime.now(timezone.utc)
    tema = HubTheme(
        id=uuid.uuid4(),
        name=data.name,
        organizacion_id=uuid.UUID(data.organizacion_id) if data.organizacion_id else None,
        chatbot_id=uuid.UUID(data.chatbot_id) if data.chatbot_id else None,
        config=data.config.model_dump(),
        is_default=False,
        created_by=user.user_id,
        # Explícitas y no delegadas al default de la columna: el objeto queda completo
        # antes del INSERT, así que la respuesta no depende de que el `refresh` recargue.
        created_at=ahora,
        updated_at=ahora,
    )
    session.add(tema)
    await session.commit()
    await session.refresh(tema)
    return _a_dict(tema)


@router.put("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    theme_id: str,
    data: ThemeUpdate,
    user: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Actualiza un tema existente."""
    tema = await session.get(HubTheme, _assert_id_de_tema(theme_id))
    if tema is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    if tema.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify default themes")
    tema.config = data.config.model_dump()
    tema.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(tema)
    return _a_dict(tema)


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(
    theme_id: str,
    user: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Elimina un tema personalizado."""
    tema = await session.get(HubTheme, _assert_id_de_tema(theme_id))
    if tema is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    if tema.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default themes")
    await session.delete(tema)
    await session.commit()


@router.post("/{theme_id}/apply/{chatbot_id}")
async def apply_theme_to_chatbot(
    theme_id: str,
    chatbot_id: uuid.UUID,
    user: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Aplica un tema a un chatbot específico.

    `HubChatbot.theme_config` no llevaba lector ni escritor en ningún sitio: se reutiliza
    como puntero (`{"theme_id": ...}`) a la fila de `hub_themes`, en vez de duplicar la
    configuración de colores en dos sitios. `get_theme_for_chatbot` es quien lo resuelve.
    """
    theme = await _load_theme(session, theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Theme {theme_id} not found")
    chatbot = await session.get(HubChatbot, chatbot_id)
    if not chatbot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")
    chatbot.theme_config = {"theme_id": theme_id}
    await session.commit()
    return {"message": f"Theme {theme_id} applied to chatbot {chatbot_id}", "theme_name": theme["name"]}
