"""
Dashboard principal del Partner.

Muestra métricas de uso y estado específicas para el Partner actual,
incluyendo el recuento de clientes bajo su gestión, licencias vigentes
y solicitudes de scripts pendientes de revisión.
"""

from nicegui import ui
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.database.models import ClientAccount, License

# BillingRecord might not be available yet if P05 wasn't run or file structure differs.
# Checking imports from instructions.. PROMPT 05 was Billing Engine.
try:
    from server.app.database.models import BillingRecord
except ImportError:
    BillingRecord = None

from server.app.ui.partner_layout import PartnerContext


def partner_dashboard_content(ctx: PartnerContext):
    """
    Renderiza el contenido del Dashboard para el Partner identificado.

    Args:
        ctx: Contexto del partner con su identificación y permisos.
    """
    t = state.i18n.t

    class DashState:
        total_clients: int = 0
        active_licenses: int = 0
        total_tokens_month: int = 0
        pending_scripts: int = 0
        loading: bool = True

    dash_state = DashState()

    async def load_kpis():
        async with AsyncSession(server_engine) as session:
            # Total clientes de este partner
            stmt = select(func.count(ClientAccount.client_id)).where(
                ClientAccount.partner_id == ctx.partner_id
            )
            try:
                result = await session.exec(stmt)
                dash_state.total_clients = result.first() or 0
            except Exception:
                dash_state.total_clients = 0

            # Licencias activas
            # Join might need explicit On clause or just rely on foreign keys
            stmt = (
                select(func.count(License.license_id))
                .join(ClientAccount, License.client_id == ClientAccount.client_id)
                .where(
                    ClientAccount.partner_id == ctx.partner_id,
                    License.status == "active",
                )
            )
            try:
                result = await session.exec(stmt)
                dash_state.active_licenses = result.first() or 0
            except Exception:
                dash_state.active_licenses = 0

            # Tokens consumidos este mes
            if BillingRecord:
                first_day = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
                # Ensure billing record has timestamp field
                stmt = select(func.sum(BillingRecord.tokens_used)).where(
                    BillingRecord.partner_id == ctx.partner_id,
                    BillingRecord.timestamp >= first_day,
                )
                try:
                    result = await session.exec(stmt)
                    dash_state.total_tokens_month = result.first() or 0
                except Exception:
                    dash_state.total_tokens_month = 0
            else:
                dash_state.total_tokens_month = 0

        dash_state.loading = False
        kpi_container.refresh()

    # --- NAVIGATION CARDS ---

    PARTNER_CARDS = [
        {
            "name": t("partner.dashboard.card_clients_title"),
            "desc": t("partner.dashboard.card_clients_desc"),
            "icon": "people",
            "color": "indigo",
            "route": "/partner/clients",
        },
        {
            "name": t("partner.dashboard.card_billing_title"),
            "desc": t("partner.dashboard.card_billing_desc"),
            "icon": "receipt",
            "color": "emerald",
            "route": "/partner/billing",
        },
        {
            "name": t("partner.dashboard.card_scripts_title"),
            "desc": t("partner.dashboard.card_scripts_desc"),
            "icon": "code",
            "color": "orange",
            "route": "/partner/scripts",
        },
    ]

    def render_card(card_data):
        color = card_data["color"]
        name = card_data["name"]
        desc = card_data["desc"]
        route = card_data["route"]

        with (
            ui.card()
            .classes(
                f"w-full h-full p-0 hover:shadow-lg transition-all border-t-4 border-{color}-500 flex flex-col cursor-pointer"
            )
            .on("click", lambda: ui.navigate.to(route))
        ):
            # Header
            with ui.row().classes(f"w-full p-4 items-center gap-3 bg-{color}-50"):
                ui.icon(card_data["icon"], size="2em").classes(f"text-{color}-600")
                ui.label(name).classes("font-bold text-lg leading-tight text-slate-800")

            # Body
            with ui.column().classes("p-4 flex-grow gap-2"):
                ui.label(desc).classes("text-sm text-gray-600 mb-2 leading-relaxed")

            # Footer
            with ui.row().classes(
                "w-full p-3 border-t border-gray-100 justify-end bg-slate-50"
            ):
                ui.button(
                    t("partner.dashboard.open"),
                    icon="arrow_forward",
                    on_click=lambda: ui.navigate.to(route),
                ).props(f"flat dense color={color}").classes("text-sm")

    @ui.refreshable
    def kpi_container():
        if dash_state.loading:
            ui.spinner("dots", size="lg")
            return

        with ui.grid().classes(
            "w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        ):
            # KPI 1: Clientes
            with ui.card().classes("p-4 bg-white"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("people", size="2em").classes("text-indigo-500")
                    with ui.column().classes("gap-0"):
                        ui.label(str(dash_state.total_clients)).classes(
                            "text-3xl font-bold"
                        )
                        ui.label(t("partner.dashboard.kpi_clients")).classes(
                            "text-xs text-gray-500 uppercase"
                        )

            # KPI 2: Licencias Activas
            with ui.card().classes("p-4 bg-white"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("verified_user", size="2em").classes("text-green-500")
                    with ui.column().classes("gap-0"):
                        ui.label(str(dash_state.active_licenses)).classes(
                            "text-3xl font-bold"
                        )
                        ui.label(t("partner.dashboard.kpi_licenses")).classes(
                            "text-xs text-gray-500 uppercase"
                        )

            # KPI 3: Tokens Mes
            with ui.card().classes("p-4 bg-white"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("token", size="2em").classes("text-orange-500")
                    with ui.column().classes("gap-0"):
                        ui.label(f"{dash_state.total_tokens_month:,}").classes(
                            "text-3xl font-bold"
                        )
                        ui.label(t("partner.dashboard.kpi_tokens")).classes(
                            "text-xs text-gray-500 uppercase"
                        )

            # KPI 4: Scripts Pendientes
            with ui.card().classes("p-4 bg-white"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("pending_actions", size="2em").classes("text-red-500")
                    with ui.column().classes("gap-0"):
                        ui.label(str(dash_state.pending_scripts)).classes(
                            "text-3xl font-bold"
                        )
                        ui.label(t("partner.dashboard.kpi_scripts")).classes(
                            "text-xs text-gray-500 uppercase"
                        )

    # --- RENDER MAIN LAYOUT ---

    ui.label(t("partner.dashboard.title")).classes(
        "text-2xl font-bold mb-6 text-slate-800"
    )

    kpi_container()

    ui.separator().classes("my-8")

    ui.label(t("partner.dashboard.subtitle")).classes(
        "text-xl font-bold mb-4 text-slate-700"
    )

    with ui.grid().classes(
        "w-full gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 items-stretch"
    ):
        for card in PARTNER_CARDS:
            render_card(card)

    # Cargar datos
    ui.timer(0.1, load_kpis, once=True)
