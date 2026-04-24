"""
Gestión de Partners e Integradores Tecnológicos.

Permite el alta y mantenimiento de partners, gestión de sus balances de
créditos para el consumo de IA, y monitorización agregada de sus carteras
de clientes.
"""

from datetime import datetime
from nicegui import ui
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.database.models import PartnerAccount, ClientAccount


def admin_partners_content():
    t = state.i18n.t
    ui.label(t("admin.partners.title")).classes(
        "text-2xl font-bold mb-6 text-slate-800"
    )

    with ui.card().classes("w-full p-4"):
        ui.label(t("admin.partners.title")).classes("text-lg font-bold mb-4")
        ui.label("Integradores tecnológicos del sistema B2B2B").classes(
            "text-sm text-gray-500 mb-4"
        )

        # Tabla de Partners
        columns = [
            {
                "name": "partner_id",
                "label": t("admin.partners.partner_id"),
                "field": "partner_id",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "name",
                "label": t("admin.partners.partner_name"),
                "field": "name",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "email",
                "label": t("admin.partners.partner_email"),
                "field": "email",
                "align": "left",
            },
            {
                "name": "credits",
                "label": t("admin.partners.credits_balance"),
                "field": "credits_display",
                "sortable": True,
                "align": "right",
            },
            {
                "name": "status",
                "label": t("admin.partners.partner_status"),
                "field": "status",
                "sortable": True,
                "align": "center",
            },
            {
                "name": "actions",
                "label": t("admin.common.actions"),
                "field": "actions",
                "align": "center",
            },
        ]

        partner_table = ui.table(
            columns=columns, rows=[], row_key="partner_id"
        ).classes("w-full")

        # Dialogs
        create_dialog = ui.dialog()
        edit_dialog = ui.dialog()
        credits_dialog = ui.dialog()
        consumption_dialog = ui.dialog()

        # --- CREATE DIALOG ---
        with create_dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("admin.partners.add_partner")).classes("text-xl font-bold mb-4")

            # new_partner_id removed (auto-generated)
            new_partner_name = (
                ui.input(
                    label=t("admin.partners.partner_name"),
                    placeholder="Consultora TIC SL",
                )
                .classes("w-full")
                .props("outlined dense")
            )
            new_partner_email = (
                ui.input(
                    label=t("admin.partners.partner_email"), placeholder="admin@tic.com"
                )
                .classes("w-full")
                .props("outlined dense")
            )
            new_credits = (
                ui.number(
                    label=t("admin.partners.credits_balance"), value=0, format="%d"
                )
                .classes("w-full")
                .props("outlined dense")
            )

            async def save_new_partner():
                if not new_partner_name.value:
                    ui.notify("El Nombre es obligatorio", type="negative")
                    return

                # Import here to avoid circular dependencies if any, or just convenience
                from server.app.services.partner_service import PartnerService

                async with AsyncSession(server_engine) as session:
                    service = PartnerService(session)
                    try:
                        new_partner = await service.create_partner(
                            name=new_partner_name.value,
                            email=new_partner_email.value,
                            credits_balance=int(new_credits.value or 0),
                        )
                        ui.notify(
                            f"{t('admin.partners.partner_created')} (ID: {new_partner.partner_id})",
                            type="positive",
                        )
                    except Exception as e:
                        ui.notify(f"Error: {e}", type="negative")
                        return

                create_dialog.close()
                await refresh_partners()

                # Clear form
                new_partner_name.value = ""
                new_partner_email.value = ""
                new_credits.value = 0

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button(t("admin.common.cancel"), on_click=create_dialog.close).props(
                    "flat"
                )
                ui.button(
                    t("admin.common.save"), icon="save", on_click=save_new_partner
                ).props("color=primary")

        # --- EDIT DIALOG ---
        with edit_dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("admin.common.edit")).classes("text-xl font-bold mb-4")

            edit_partner_id = (
                ui.input(label=t("admin.partners.partner_id"))
                .classes("w-full")
                .props("outlined dense readonly")
            )
            edit_partner_name = (
                ui.input(label=t("admin.partners.partner_name"))
                .classes("w-full")
                .props("outlined dense")
            )
            edit_partner_email = (
                ui.input(label=t("admin.partners.partner_email"))
                .classes("w-full")
                .props("outlined dense")
            )
            edit_status = (
                ui.select(
                    options=[True, False],
                    # value=True, # Will be set on open
                    label=t("admin.partners.partner_status"),
                    with_input=False,
                )
                .classes("w-full")
                .props("outlined dense")
            )

            async def save_edit_partner():
                async with AsyncSession(server_engine) as session:
                    partner = await session.get(PartnerAccount, edit_partner_id.value)
                    if partner:
                        partner.name = edit_partner_name.value
                        partner.email = edit_partner_email.value
                        partner.is_active = edit_status.value
                        session.add(partner)
                        await session.commit()

                ui.notify(t("admin.partners.partner_updated"), type="positive")
                edit_dialog.close()
                await refresh_partners()

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button(t("admin.common.cancel"), on_click=edit_dialog.close).props(
                    "flat"
                )
                ui.button(
                    t("admin.common.save"), icon="save", on_click=save_edit_partner
                ).props("color=primary")

        # --- CREDITS DIALOG ---
        with credits_dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("admin.partners.edit_credits")).classes("text-xl font-bold mb-4")

            credits_partner_id = ui.label().classes("text-sm text-gray-500 mb-4")
            credits_current = ui.label().classes("text-lg font-bold mb-4")

            credits_mode = (
                ui.select(
                    options={
                        "add": t("admin.partners.add_credits"),
                        "set": t("admin.partners.set_credits"),
                    },
                    value="add",
                    label="Modo",
                )
                .classes("w-full")
                .props("outlined dense")
            )

            credits_amount_input = (
                ui.number(
                    label=t("admin.partners.credits_amount"), value=0, format="%d"
                )
                .classes("w-full")
                .props("outlined dense")
            )

            async def save_credits():
                async with AsyncSession(server_engine) as session:
                    # Parse partner ID from label (e.g. "Partner: test")
                    pid = credits_partner_id.text.split(": ")[1]
                    partner = await session.get(PartnerAccount, pid)
                    if partner:
                        if credits_mode.value == "add":
                            partner.credits_balance += int(
                                credits_amount_input.value or 0
                            )
                        else:  # set
                            partner.credits_balance = int(
                                credits_amount_input.value or 0
                            )

                        session.add(partner)
                        await session.commit()

                ui.notify(t("admin.partners.credits_updated"), type="positive")
                credits_dialog.close()
                await refresh_partners()

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button(t("cancel"), on_click=credits_dialog.close).props("flat")
                ui.button(t("save"), icon="save", on_click=save_credits).props(
                    "color=primary"
                )

        # --- CONSUMPTION DIALOG ---
        consumption_state = {
            "partner_id": None,
            "partner_name": "",
            "year": datetime.utcnow().year,
            "month": datetime.utcnow().month,
            "data": None,
        }

        with consumption_dialog, ui.card().classes("w-full max-w-3xl"):
            ui.label("Consumo del Partner").classes("text-xl font-bold mb-4")

            @ui.refreshable
            def render_consumption_content():
                partner_name = consumption_state["partner_name"]
                data = consumption_state["data"]

                # Header con filtros
                with ui.row().classes("w-full items-center gap-4 mb-4"):
                    ui.label(f"Partner: {partner_name}").classes("text-lg font-bold")
                    ui.space()

                    year_select = (
                        ui.select(
                            options=[2024, 2025, 2026, 2027],
                            value=consumption_state["year"],
                            label="Año",
                        )
                        .classes("w-24")
                        .props("outlined dense")
                    )

                    month_select = (
                        ui.select(
                            options={
                                i: datetime(2000, i, 1).strftime("%B")
                                for i in range(1, 13)
                            },
                            value=consumption_state["month"],
                            label="Mes",
                        )
                        .classes("w-32")
                        .props("outlined dense")
                    )

                    async def reload_consumption():
                        consumption_state["year"] = year_select.value
                        consumption_state["month"] = month_select.value
                        await load_consumption_data()
                        render_consumption_content.refresh()

                    ui.button(icon="refresh", on_click=reload_consumption).props(
                        "flat dense"
                    )

                if not data:
                    ui.label("Cargando...").classes("text-gray-500")
                    return

                # KPI Cards
                with ui.row().classes("w-full gap-4 mb-4"):
                    with ui.card().classes("flex-1 p-4 bg-blue-50"):
                        ui.label("Tokens Totales").classes("text-sm text-gray-600")
                        ui.label(f"{data.get('total_tokens', 0):,}").classes(
                            "text-2xl font-bold text-blue-800"
                        )

                    with ui.card().classes("flex-1 p-4 bg-green-50"):
                        ui.label("Coste USD").classes("text-sm text-gray-600")
                        ui.label(f"${data.get('total_cost_usd', 0):.4f}").classes(
                            "text-2xl font-bold text-green-800"
                        )

                # Tablas por cliente y por modelo
                with ui.row().classes("w-full gap-4"):
                    # Por Cliente
                    with ui.card().classes("flex-1 p-0"):
                        ui.label("Por Cliente").classes("p-4 font-bold border-b")
                        client_columns = [
                            {
                                "name": "client_name",
                                "label": "Cliente",
                                "field": "client_name",
                                "align": "left",
                            },
                            {
                                "name": "tokens",
                                "label": "Tokens",
                                "field": "tokens",
                                "sortable": True,
                                "align": "right",
                            },
                            {
                                "name": "cost_usd",
                                "label": "USD",
                                "field": "cost_usd",
                                "sortable": True,
                                "align": "right",
                            },
                        ]
                        ui.table(
                            columns=client_columns,
                            rows=data.get("by_client", []),
                            row_key="client_id",
                        ).classes("w-full").props("dense flat")

                    # Por Modelo
                    with ui.card().classes("flex-1 p-0"):
                        ui.label("Por Modelo IA").classes("p-4 font-bold border-b")
                        model_columns = [
                            {
                                "name": "model_id",
                                "label": "Modelo",
                                "field": "model_id",
                                "align": "left",
                            },
                            {
                                "name": "tokens",
                                "label": "Tokens",
                                "field": "tokens",
                                "sortable": True,
                                "align": "right",
                            },
                            {
                                "name": "cost_usd",
                                "label": "USD",
                                "field": "cost_usd",
                                "sortable": True,
                                "align": "right",
                            },
                        ]
                        ui.table(
                            columns=model_columns,
                            rows=data.get("by_model", []),
                            row_key="model_id",
                        ).classes("w-full").props("dense flat")

            render_consumption_content()

            with ui.row().classes("w-full justify-end mt-4"):
                ui.button("Cerrar", on_click=consumption_dialog.close).props("flat")

        async def load_consumption_data():
            from server.app.services.consumption_query_service import (
                ConsumptionQueryService,
            )

            async with AsyncSession(server_engine) as session:
                service = ConsumptionQueryService(session)
                consumption_state["data"] = await service.get_partner_summary(
                    consumption_state["partner_id"],
                    consumption_state["year"],
                    consumption_state["month"],
                )

        async def open_consumption(row):
            consumption_state["partner_id"] = row["partner_id"]
            consumption_state["partner_name"] = row["name"]
            consumption_state["year"] = datetime.utcnow().year
            consumption_state["month"] = datetime.utcnow().month
            consumption_state["data"] = None
            render_consumption_content.refresh()
            consumption_dialog.open()
            await load_consumption_data()
            render_consumption_content.refresh()

        # --- TABLE ACTIONS ---
        async def open_edit(row):
            edit_partner_id.value = row["partner_id"]
            edit_partner_name.value = row["name"]
            edit_partner_email.value = row["email"]
            edit_status.value = row["is_active"]
            edit_dialog.open()

        async def open_credits(row):
            credits_partner_id.text = f"Partner: {row['partner_id']}"
            credits_current.text = f"Saldo Actual: {row['credits_display']}"
            credits_amount_input.value = 0
            credits_mode.value = "add"
            credits_dialog.open()

        async def delete_partner(row):
            async with AsyncSession(server_engine) as session:
                partner = await session.get(PartnerAccount, row["partner_id"])
                if partner:
                    # Check if has clients
                    stmt = select(ClientAccount).where(
                        ClientAccount.partner_id == partner.partner_id
                    )
                    result = await session.exec(stmt)
                    clients = result.all()

                    if clients:
                        ui.notify(
                            "No se puede eliminar: tiene clientes asociados",
                            type="warning",
                        )
                        return

                    await session.delete(partner)
                    await session.commit()

            ui.notify(t("admin.partners.partner_deleted"), type="positive")
            await refresh_partners()

        partner_table.add_slot(
            "body-cell-status",
            r"""
            <q-td :props="props">
                <q-badge :color="props.row.is_active ? 'green' : 'red'">
                    {{ props.row.is_active ? 'ACTIVO' : 'INACTIVO' }}
                </q-badge>
            </q-td>
        """,
        )

        partner_table.add_slot(
            "body-cell-actions",
            r"""
            <q-td :props="props">
                <q-btn size="sm" flat dense icon="bar_chart" color="teal"
                       @click="() => $parent.$emit('consumption', props.row)">
                    <q-tooltip>Ver Consumo</q-tooltip>
                </q-btn>
                <q-btn size="sm" flat dense icon="account_balance_wallet" color="primary"
                       @click="() => $parent.$emit('credits', props.row)">
                    <q-tooltip>Ajustar Créditos</q-tooltip>
                </q-btn>
                <q-btn size="sm" flat dense icon="edit" color="blue"
                       @click="() => $parent.$emit('edit', props.row)">
                    <q-tooltip>Editar</q-tooltip>
                </q-btn>
                <q-btn size="sm" flat dense icon="delete" color="red"
                       @click="() => $parent.$emit('delete', props.row)">
                    <q-tooltip>Eliminar</q-tooltip>
                </q-btn>
            </q-td>
        """,
        )

        partner_table.on("consumption", lambda e: open_consumption(e.args))
        partner_table.on("edit", lambda e: open_edit(e.args))
        partner_table.on("credits", lambda e: open_credits(e.args))
        partner_table.on("delete", lambda e: delete_partner(e.args))

        # --- REFRESH FUNCTION ---
        async def refresh_partners():
            async with AsyncSession(server_engine) as session:
                statement = select(PartnerAccount).order_by(
                    desc(PartnerAccount.created_at)
                )
                result = await session.exec(statement)
                partners = result.all()

                rows = []
                for p in partners:
                    rows.append(
                        {
                            "partner_id": p.partner_id,
                            "name": p.name,
                            "email": p.email or "N/A",
                            "credits_display": f"{p.credits_balance:,}",
                            "credits_raw": p.credits_balance,
                            "is_active": p.is_active,
                            "status": "ACTIVO" if p.is_active else "INACTIVO",
                        }
                    )

                partner_table.rows = rows
                partner_table.update()

        # Initial load
        ui.timer(0.1, refresh_partners, once=True)

        # Action Buttons
        with ui.row().classes("w-full justify-between mt-4"):
            ui.button(
                t("admin.partners.add_partner"), icon="add", on_click=create_dialog.open
            ).props("color=primary")
            ui.button(
                t("admin.common.update"), icon="refresh", on_click=refresh_partners
            ).props("flat dense")
