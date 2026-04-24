"""
Panel de Facturación y Consumo para Partners.

Proporciona una vista consolidada de los costes generados por sus clientes,
alertas de consumo anómalo y herramientas de exportación para procesos
administrativos.
"""

from datetime import datetime
from nicegui import ui
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.services.partner_billing_service import PartnerBillingService
from server.app.ui.partner_layout import PartnerContext


def partner_billing_content(ctx: PartnerContext):
    t = state.i18n.t

    class BillingState:
        summary = {}
        trend = []
        alerts = []
        selected_month = datetime.utcnow().month
        selected_year = datetime.utcnow().year

    page_state = BillingState()

    async def load_data():
        async with AsyncSession(server_engine) as session:
            service = PartnerBillingService(session, ctx.partner_id)
            page_state.summary = await service.get_monthly_summary(
                page_state.selected_year, page_state.selected_month
            )
            page_state.trend = await service.get_consumption_trend(6)
            page_state.alerts = await service.get_high_consumption_alerts()

        render_dashboard()

    async def export_csv():
        async with AsyncSession(server_engine) as session:
            service = PartnerBillingService(session, ctx.partner_id)
            csv_data = await service.export_to_csv(
                page_state.selected_year, page_state.selected_month
            )

        ui.download(
            csv_data.encode(),
            f"billing_{page_state.selected_year}_{page_state.selected_month}.csv",
        )

    @ui.refreshable
    def render_dashboard():
        ui.label(t("partner.billing.title")).classes("text-2xl font-bold mb-4")

        # Filters
        with ui.row().classes("items-center gap-4 mb-6"):
            ui.select(
                options=[2025, 2026, 2027],
                value=page_state.selected_year,
                label=t("partner.billing.year"),
                on_change=lambda e: setattr(page_state, "selected_year", e.value),
            ).bind_value(page_state, "selected_year")

            ui.select(
                options={i: datetime(2000, i, 1).strftime("%B") for i in range(1, 13)},
                value=page_state.selected_month,
                label=t("partner.billing.month"),
                on_change=lambda e: setattr(page_state, "selected_month", e.value),
            ).bind_value(page_state, "selected_month")

            ui.button(
                t("partner.billing.refresh"), icon="refresh", on_click=load_data
            ).props("flat")
            ui.button(
                t("partner.billing.export_csv"), icon="download", on_click=export_csv
            ).props("color=green")

        # KPI Cards
        with ui.row().classes("w-full gap-4 mb-6"):
            with ui.card().classes("flex-1 p-4 bg-blue-50"):
                ui.label(t("partner.billing.total_tokens")).classes("text-gray-600")
                ui.label(f"{page_state.summary.get('total_tokens', 0):,}").classes(
                    "text-3xl font-bold text-blue-800"
                )

            with ui.card().classes("flex-1 p-4 bg-green-50"):
                ui.label(t("partner.billing.estimated_cost")).classes("text-gray-600")
                ui.label(f"${page_state.summary.get('total_cost_usd', 0):.2f}").classes(
                    "text-3xl font-bold text-green-800"
                )

        # Alerts
        if page_state.alerts:
            with ui.expansion(
                t("partner.billing.alerts_title"), icon="warning", value=True
            ).classes("w-full bg-red-50 mb-6 text-red-800"):
                for alert in page_state.alerts:
                    msg = t("partner.billing.alert_msg").format(
                        client=alert["client_name"],
                        percent=alert["percent_increase"],
                        current=alert["current_consumption"],
                        avg=alert["average_consumption"],
                    )
                    ui.label(f"⚠️ {msg}").classes("ml-8")

        # Detailed Tables
        with ui.grid(columns="1fr 1fr").classes("w-full gap-6"):
            # By Client
            with ui.card().classes("p-0"):
                ui.label(t("partner.billing.by_client")).classes(
                    "p-4 font-bold border-b"
                )

                columns = [
                    {
                        "name": "client_name",
                        "label": t("partner.billing.col_client"),
                        "field": "client_name",
                        "align": "left",
                    },
                    {
                        "name": "tokens",
                        "label": t("partner.billing.col_tokens"),
                        "field": "tokens",
                        "sortable": True,
                    },
                    {
                        "name": "cost_usd",
                        "label": t("partner.billing.col_cost"),
                        "field": "cost_usd",
                        "sortable": True,
                    },
                ]
                ui.table(
                    columns=columns,
                    rows=page_state.summary.get("by_client", []),
                    row_key="client_id",
                ).classes("w-full no-shadow")

            # By Model
            with ui.card().classes("p-0"):
                ui.label(t("partner.billing.by_model")).classes(
                    "p-4 font-bold border-b"
                )

                columns_model = [
                    {
                        "name": "model_id",
                        "label": t("partner.billing.col_model"),
                        "field": "model_id",
                        "align": "left",
                    },
                    {
                        "name": "tokens",
                        "label": t("partner.billing.col_tokens"),
                        "field": "tokens",
                        "sortable": True,
                    },
                    {
                        "name": "cost_usd",
                        "label": t("partner.billing.col_cost"),
                        "field": "cost_usd",
                        "sortable": True,
                    },
                ]
                ui.table(
                    columns=columns_model,
                    rows=page_state.summary.get("by_model", []),
                    row_key="model_id",
                ).classes("w-full no-shadow")

    # Initial Load
    ui.timer(0.1, load_data, once=True)
