"""
Panel de Observabilidad y Telemetría del Sistema.

Muestra estadísticas en tiempo real sobre el uso de la plataforma,
incluyendo registros de tokens, costes acumulados por modelo y estado
global de partners y clientes.
"""

from datetime import datetime, timedelta
from nicegui import ui
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.ui.admin_layout import AdminContext
from server.app.database.models import (
    TokenLog,
    ModelPricing,
    PartnerAccount,
    ClientAccount,
    AutomationLibrary,
    ClientTelemetryLog,
)


def admin_analytics_content(ctx: AdminContext):
    # --- Data Fetching Global ---
    async def get_global_stats():
        async with AsyncSession(server_engine) as session:
            # 1. Counts
            partners = (
                await session.exec(select(func.count(PartnerAccount.partner_id)))
            ).one()
            clients = (
                await session.exec(select(func.count(ClientAccount.client_id)))
            ).one()
            automations = (
                await session.exec(select(func.count(AutomationLibrary.id)))
            ).one()

            # 2. Recent Token Logs
            recent_logs = (
                await session.exec(
                    select(TokenLog).order_by(TokenLog.timestamp.desc()).limit(10)
                )
            ).all()

            # 3. Model Pricing
            prices = (await session.exec(select(ModelPricing))).all()

            return {
                "partners": partners,
                "clients": clients,
                "automations": automations,
                "logs": recent_logs,
                "prices": prices,
            }

    # --- Data Fetching Telemetry ---
    async def get_telemetry_logs(
        client_filter: str = None, status_filter: str = "ALL", days_filter: int = 7
    ):
        async with AsyncSession(server_engine) as session:
            query = (
                select(ClientTelemetryLog)
                .order_by(ClientTelemetryLog.timestamp_client.desc())
                .limit(100)
            )

            if client_filter:
                query = query.where(
                    col(ClientTelemetryLog.client_id).contains(client_filter)
                )

            if status_filter != "ALL":
                query = query.where(ClientTelemetryLog.status == status_filter)

            if days_filter:
                date_limit = datetime.utcnow() - timedelta(days=days_filter)
                query = query.where(ClientTelemetryLog.timestamp_client >= date_limit)

            logs = (await session.exec(query)).all()
            return logs

    # --- UI Rendering ---
    container = ui.column().classes("w-full")

    # State for Telemetry Filters
    filter_client = (
        ui.input("Buscar Cliente ID").classes("w-48").props("clearable dense")
    )
    filter_status = (
        ui.select(["ALL", "success", "error"], value="ALL", label="Estado")
        .classes("w-32")
        .props("dense options-dense")
    )
    filter_days = (
        ui.number(label="Días", value=7, min=1, max=30).classes("w-20").props("dense")
    )

    async def render_dashboard():
        container.clear()

        with container:
            ui.label("Panel de Observabilidad Check").classes(
                "text-2xl font-bold mb-4 text-primary"
            )

            with ui.tabs().classes("w-full text-indigo-800") as tabs:
                tab_global = ui.tab("Globales", icon="analytics")
                tab_telemetry = ui.tab("Telemetría Clientes", icon="query_stats")

            with ui.tab_panels(tabs, value=tab_global).classes("w-full bg-transparent"):
                # --- TAB 1: GLOBALES ---
                with ui.tab_panel(tab_global):
                    await render_global_tab()

                # --- TAB 2: TELEMETRIA ---
                with ui.tab_panel(tab_telemetry):
                    await render_telemetry_tab()

    async def render_global_tab():
        data = await get_global_stats()

        # 1. KPI Cards
        with ui.row().classes("w-full gap-4 mb-6"):

            def kpi_card(title, value, icon, color):
                with ui.card().classes(f"w-64 p-4 border-l-4 border-{color}-500"):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.column().classes("gap-0"):
                            ui.label(title).classes(
                                "text-gray-500 text-sm font-bold uppercase"
                            )
                            ui.label(str(value)).classes("text-3xl font-bold")
                        ui.icon(icon).classes(f"text-4xl text-{color}-200")

            kpi_card("Partners", data["partners"], "business", "blue")
            kpi_card("Clientes Activos", data["clients"], "badge", "green")
            kpi_card("Automatismos", data["automations"], "library_books", "purple")
            kpi_card("Modelos AI", len(data["prices"]), "psychology", "orange")

        # 2. Recent Token Activity (Table)
        with ui.card().classes("w-full p-4 mb-6"):
            ui.label("Actividad Reciente de Tokens (TokenLog)").classes(
                "text-lg font-bold mb-4"
            )

            rows = [
                {
                    "time": log.timestamp.strftime("%H:%M:%S"),
                    "provider": log.provider,
                    "model": log.model,
                    "input": log.input_tokens,
                    "output": log.output_tokens,
                    "cost": f"${log.cost:.4f}",
                }
                for log in data["logs"]
            ]

            ui.table(
                columns=[
                    {"name": "time", "label": "Hora", "field": "time"},
                    {"name": "provider", "label": "Proveedor", "field": "provider"},
                    {"name": "model", "label": "Modelo", "field": "model"},
                    {"name": "input", "label": "Input", "field": "input"},
                    {"name": "output", "label": "Output", "field": "output"},
                    {"name": "cost", "label": "Coste (Est.)", "field": "cost"},
                ],
                rows=rows,
                pagination=5,
            ).classes("w-full")

    async def render_telemetry_tab():
        with ui.card().classes("w-full p-4"):
            # Filters
            with ui.row().classes("w-full items-center gap-4 mb-4"):
                filter_client.move(ui.row())  # Move global state elements here
                filter_status.move(ui.row())
                filter_days.move(ui.row())

                async def refresh_click():
                    await update_telemetry_table()

                ui.button(icon="refresh", on_click=refresh_click).props(
                    "flat round color=primary"
                )

            # Table Container
            table_container = ui.column().classes("w-full")

            async def update_telemetry_table():
                table_container.clear()
                logs = await get_telemetry_logs(
                    client_filter=filter_client.value,
                    status_filter=filter_status.value,
                    days_filter=int(filter_days.value or 7),
                )

                rows = [
                    {
                        "time": log.timestamp_client.strftime("%Y-%m-%d %H:%M"),
                        "client": log.client_id,
                        "service": log.script_hash or log.manifest_id[:8],
                        "status": log.status,
                        "duration": f"{log.execution_time_ms}ms",
                        "tokens": log.total_tokens,
                        "error": log.error_message or "",
                    }
                    for log in logs
                ]

                with table_container:
                    if not rows:
                        ui.label("No se encontraron registros.").classes(
                            "text-gray-500 italic"
                        )
                        return

                    ui.table(
                        columns=[
                            {
                                "name": "time",
                                "label": "Fecha/Hora",
                                "field": "time",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "client",
                                "label": "Cliente",
                                "field": "client",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "service",
                                "label": "Servicio",
                                "field": "service",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "status",
                                "label": "Estado",
                                "field": "status",
                                "sortable": True,
                                "align": "center",
                            },
                            {
                                "name": "duration",
                                "label": "Tiempo",
                                "field": "duration",
                                "sortable": True,
                                "align": "right",
                            },
                            {
                                "name": "tokens",
                                "label": "Tokens",
                                "field": "tokens",
                                "sortable": True,
                                "align": "right",
                            },
                            {
                                "name": "error",
                                "label": "Error",
                                "field": "error",
                                "align": "left",
                            },
                        ],
                        rows=rows,
                        pagination=10,
                    ).classes("w-full").props("flat bordered dense")

            await update_telemetry_table()

    # Initial Render
    ui.timer(0.1, render_dashboard, once=True)
