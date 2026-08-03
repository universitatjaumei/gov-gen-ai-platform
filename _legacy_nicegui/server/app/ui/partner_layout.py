"""
Layout base para el portal de Partners (Distribuidores).

Define la navegación y el marco visual para que los Partners gestionen sus
propios clientes, licencias y políticas de seguridad, operando bajo un
esquema de multi-tenencia.
"""

from nicegui import ui, app
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from server.app.database.models import PartnerAccount

from client_app.app.core.state import state


@dataclass
class PartnerContext:
    """
    Contexto de datos del Partner para el Dashboard.

    Centraliza la identidad del Partner (ID, nombre) y proporciona métodos
    fábrica para instanciar el contexto desde diferentes modos de sesión.
    """

    partner_id: str
    partner_name: str
    role: str = "PARTNER"
    is_authenticated: bool = True
    redirect_url: str = "/partner/login"

    @classmethod
    async def from_dev_mode(
        cls, partner_id: str, db_session: AsyncSession
    ) -> Optional["PartnerContext"]:
        """
        MODO DESARROLLO: Carga partner directamente de BD sin autenticacion.

        Uso:
            ctx = await PartnerContext.from_dev_mode("partner_demo", db)
        """
        stmt = select(PartnerAccount).where(
            PartnerAccount.partner_id == partner_id, PartnerAccount.is_active
        )
        result = await db_session.exec(stmt)
        partner = result.first()

        if not partner:
            return None

        # Try to get role if it exists, otherwise default to PARTNER
        role = getattr(partner, "role", "PARTNER")

        return cls(
            partner_id=partner.partner_id,
            partner_name=partner.name,
            role=role,
            is_authenticated=True,
        )

    @classmethod
    async def from_session(
        cls, token: str, db_session: AsyncSession
    ) -> Optional["PartnerContext"]:
        """
        MODO PRODUCCION (P27): Valida sesion y carga partner.
        MODO DEV (Prompt 4): Si no hay sesión, usa cuenta dev.
        """
        # 1. Intentar obtener Partner ID de la "sesión" (cookie/storage)
        partner_id = app.storage.user.get("partner_id")

        # 2. Si no hay ID, asumir modo desarrollo (Bypass Prompt 4)
        if not partner_id:
            ui.notify(
                "DEV MODE: Usando sesión simulada (dev-partner-0000)", type="warning"
            )
            partner_id = "dev-partner-0000"

        # 3. Cargar contexto
        return await cls.from_dev_mode(partner_id, db_session)

    def get_header_text(self) -> str:
        """Texto para el header."""
        return f"Panel de Partner: {self.partner_name}"


def get_sidebar_items() -> List[Dict[str, Any]]:
    """Items del menu lateral."""
    t = state.i18n.t
    return [
        {
            "label": t("partner.menu_dashboard"),
            "icon": "dashboard",
            "route": "/partner/dashboard",
        },
        {
            "label": t("partner.menu_clients"),
            "icon": "people",
            "route": "/partner/clients",
        },
        {
            "label": t("partner.menu_licenses"),
            "icon": "verified_user",
            "route": "/partner/licenses",
        },
        {
            "label": t("partner.menu_security"),
            "icon": "security",
            "route": "/partner/security",
        },
        {"label": "Biblioteca", "icon": "library_books", "route": "/partner/library"},
        {
            "label": t("partner.menu_scripts"),
            "icon": "code",
            "route": "/partner/scripts",
        },
        {
            "label": t("partner.menu_billing"),
            "icon": "receipt_long",
            "route": "/partner/billing",
        },
    ]


def generate_breadcrumb(path: str) -> List[Dict[str, str]]:
    """Generar breadcrumb desde la ruta."""
    t = state.i18n.t
    # Remove query params if any
    clean_path = path.split("?")[0]
    segments = clean_path.strip("/").split("/")
    breadcrumb = []

    labels = {
        # "partner": "Dashboard", # Removed to avoid redundant breadcrumb
        "dashboard": t("partner.menu_dashboard"),
        "clients": t("partner.menu_clients"),
        "licenses": t("partner.menu_licenses"),
        "security": t("partner.menu_security"),
        "scripts": t("partner.menu_scripts"),
        "billing": t("partner.menu_billing"),
        "edit": t("admin.common.edit"),
        "new": "Nuevo",
    }

    current_path = ""
    for seg in segments:
        current_path += f"/{seg}"  # Always update path
        if seg in labels:
            breadcrumb.append({"label": labels[seg], "path": current_path})

    return breadcrumb


def partner_layout(content_fn: Callable, ctx: PartnerContext):
    """
    Layout wrapper para paginas del Partner.

    Uso:
        @ui.page('/partner/clients')
        def clients_page():
            ctx = PartnerContext(session_token=get_token_from_cookie())
            partner_layout(clients_content, ctx)
    """
    if not ctx.is_authenticated:
        ui.navigate.to(ctx.redirect_url)
        return

    # --- LAYOUT ---
    with ui.header().classes("bg-slate-900 text-white shadow-md items-center"):
        with ui.row().classes("w-full items-center justify-between px-4"):
            ui.label(ctx.get_header_text()).classes("text-xl font-bold tracking-tight")

            with ui.row().classes("items-center gap-4"):
                # Language Selector
                ui.select(
                    options=["es", "ca"],
                    value=state.i18n.locale,
                    on_change=lambda e: (
                        state.i18n.set_locale(e.value),
                        ui.navigate.reload(),
                    ),
                ).props("dense outlined options-dense").classes(
                    "bg-white text-black w-24 rounded px-2 text-xs"
                )

                ui.label(ctx.partner_name).classes(
                    "text-sm font-semibold truncate max-w-[150px]"
                )
                ui.button(
                    icon="logout", on_click=lambda: ui.navigate.to("/partner/logout")
                ).props("flat round color=white")

    with ui.row().classes("w-full h-[calc(100vh-64px)]"):
        # --- SIDEBAR ---
        with ui.column().classes(
            "w-64 h-full bg-slate-50 flex flex-col p-0 gap-0 border-r border-gray-200"
        ):
            ui.label("MENU PRINCIPAL").classes(
                "text-gray-500 text-xs font-bold px-4 py-2 uppercase tracking-wider mt-2"
            )

            for item in get_sidebar_items():
                # Matching main.py button style: text-slate-700 hover:bg-slate-200 rounded-none h-12
                with (
                    ui.row()
                    .classes(
                        "w-full h-12 px-4 cursor-pointer text-slate-700 hover:bg-slate-200 items-center gap-3 transition-colors"
                    )
                    .on("click", lambda r=item["route"]: ui.navigate.to(r))
                ):
                    ui.icon(item["icon"]).classes("text-slate-700")
                    ui.label(item["label"]).classes("text-sm font-medium")

            # Spacer to push any bottom content if needed (optional)
            ui.space()

        # --- MAIN CONTENT ---
        with ui.column().classes("flex-1 h-full p-6 bg-white overflow-y-auto"):
            # Breadcrumb
            with ui.row().classes("mb-4 gap-2 text-sm text-gray-500"):
                bc = generate_breadcrumb(
                    app.storage.browser.get("current_path", "/partner")
                )
                for i, crumb in enumerate(bc):
                    if i > 0:
                        ui.label("/").classes("text-gray-300")
                    ui.link(crumb["label"], crumb["path"]).classes(
                        "hover:text-indigo-600"
                    )

            # Content
            content_fn()
