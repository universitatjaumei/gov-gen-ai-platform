"""
Gestión de Clientes y licenciamiento (Multitenancy).

Proporciona herramientas para la creación de cuentas de cliente, generación
segura de claves de licencia hasheadas y monitorización del estado de
activación y cumplimiento de cuotas.
"""

from nicegui import ui
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.database.models import ClientAccount, License, PartnerAccount
from automatia_shared.enums import LicenseStatus
import secrets
from automatia_shared.validators import hash_license_key
from datetime import datetime, timedelta


# Helper para status color (copiado de admin_page.py)
# Helper para status color (copiado de admin_page.py)
def get_status_color(license_obj: License) -> str:
    if license_obj.status != LicenseStatus.ACTIVE.value:
        return "red"
    if license_obj.consumed_tokens >= license_obj.quota_tokens:
        return "red"
    if license_obj.valid_until:
        # Compare dates only to ensure inclusive validity for the whole day
        days_left = (license_obj.valid_until.date() - datetime.utcnow().date()).days
        if days_left < 0:
            return "red"
        if days_left < 15:
            return "orange"
    return "green"


def get_status_label(license_obj: License) -> str:
    if license_obj.status != LicenseStatus.ACTIVE.value:
        return license_obj.status
    if license_obj.consumed_tokens >= license_obj.quota_tokens:
        return "QUOTA_EXCEEDED"
    if (
        license_obj.valid_until
        and datetime.utcnow().date() > license_obj.valid_until.date()
    ):
        return "EXPIRED"

    if license_obj.valid_until:
        days_left = (license_obj.valid_until.date() - datetime.utcnow().date()).days
        if days_left < 15:
            return f"EXPIRING_SOON ({days_left}d)"

    return "ACTIVE"


def admin_clients_content():
    t = state.i18n.t
    ui.label(t("admin.clients.title")).classes("text-2xl font-bold mb-6 text-slate-800")

    # Estado de filtros
    filter_state = {"partner_id": None, "search_query": ""}

    with ui.card().classes("w-full p-4"):
        ui.label(t("admin.clients.title")).classes("text-lg font-bold mb-4")
        ui.label("Vista jerárquica Partner → Cliente → Licencia").classes(
            "text-sm text-gray-500 mb-4"
        )

        # --- BARRA DE FILTROS ---
        with ui.row().classes("w-full gap-4 mb-4 items-end"):
            # Filtro por Partner
            partner_filter_options = {"": "Todos los Partners"}
            partner_filter = (
                ui.select(
                    options=partner_filter_options,
                    value="",
                    label="Filtrar por Partner",
                )
                .classes("w-64")
                .props("outlined dense")
            )

            # Búsqueda por nombre
            search_input = (
                ui.input(
                    label="Buscar por nombre", placeholder="Escribe para buscar..."
                )
                .classes("w-64")
                .props("outlined dense clearable")
            )

            async def apply_filters():
                filter_state["partner_id"] = (
                    partner_filter.value if partner_filter.value else None
                )
                filter_state["search_query"] = search_input.value or ""
                await refresh_clients()

            partner_filter.on("update:model-value", lambda e: apply_filters())
            search_input.on("update:model-value", lambda e: apply_filters())

            ui.button(icon="search", on_click=apply_filters).props("flat dense")

        # Cargar opciones de partners para el filtro
        async def load_partner_filter_options():
            async with AsyncSession(server_engine) as session:
                stmt = select(PartnerAccount)
                result = await session.exec(stmt)
                partners = result.all()

                partner_filter_options.clear()
                partner_filter_options[""] = "Todos los Partners"
                for p in partners:
                    partner_filter_options[p.partner_id] = f"{p.name}"
                partner_filter.options = partner_filter_options
                partner_filter.update()

        ui.timer(0.1, load_partner_filter_options, once=True)

        # Tabla de Clientes
        columns = [
            {
                "name": "client_id",
                "label": t("admin.clients.client_id"),
                "field": "client_id",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "name",
                "label": t("admin.clients.client_name"),
                "field": "name",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "partner",
                "label": t("admin.clients.associated_partner"),
                "field": "partner_name",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "status",
                "label": t("admin.partners.partner_status"),
                "field": "license_status",
                "sortable": True,
                "align": "center",
            },
            {
                "name": "quota",
                "label": t("admin.clients.quota_tokens"),
                "field": "quota_display",
                "align": "right",
            },
            {
                "name": "actions",
                "label": t("common.actions"),
                "field": "actions",
                "align": "center",
            },
        ]

        client_table = ui.table(columns=columns, rows=[], row_key="client_id").classes(
            "w-full"
        )

        # Dialogs
        create_client_dialog = ui.dialog()

        # --- CREATE CLIENT DIALOG ---
        with create_client_dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label(t("admin.clients.add_client")).classes("text-xl font-bold mb-4")

            with ui.stepper().props("vertical").classes("w-full") as stepper:
                # STEP 1: Datos básicos
                with ui.step("Datos Básicos"):
                    new_client_id = (
                        ui.input(
                            label=t("admin.clients.client_id"), placeholder="client_001"
                        )
                        .classes("w-full")
                        .props("outlined dense")
                    )
                    new_client_name = (
                        ui.input(
                            label=t("admin.clients.client_name"),
                            placeholder="Ayuntamiento de Valencia",
                        )
                        .classes("w-full")
                        .props("outlined dense")
                    )

                    # Select Partner
                    partner_options = {}
                    partner_select = (
                        ui.select(
                            options=partner_options,
                            label=t("admin.clients.select_partner"),
                            with_input=True,
                        )
                        .classes("w-full")
                        .props("outlined dense")
                    )

                    async def load_partners():
                        async with AsyncSession(server_engine) as session:
                            stmt = select(PartnerAccount).where(
                                PartnerAccount.is_active
                            )
                            result = await session.exec(stmt)
                            partners = result.all()

                            partner_options.clear()
                            for p in partners:
                                partner_options[p.partner_id] = (
                                    f"{p.name} ({p.partner_id})"
                                )
                            partner_select.update()

                    ui.timer(0.1, load_partners, once=True)

                    with ui.stepper_navigation():
                        ui.button("Siguiente", on_click=stepper.next).props(
                            "color=primary"
                        )
                        ui.button(
                            t("common.cancel"), on_click=create_client_dialog.close
                        ).props("flat")

                # STEP 2: License Key
                with ui.step("License Key"):
                    ui.markdown("### Generación de License Key").classes("mb-2")
                    ui.label(
                        "La key se mostrará UNA SOLA VEZ. Guárdala de forma segura."
                    ).classes("text-sm text-orange-600 mb-4")

                    generated_key_display = (
                        ui.input(
                            label=t("admin.clients.license_key"),
                            placeholder='Presiona "Generar Key"',
                        )
                        .classes("w-full")
                        .props("outlined dense readonly")
                    )

                    generated_key_value = {"key": None}  # Closure para almacenar key

                    def generate_license_key():
                        # Formato: LIC-XXXXXXXX-XXXXXXXX-XXXXXXXX
                        raw_key = f"LIC-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
                        generated_key_display.value = raw_key
                        generated_key_value["key"] = raw_key
                        ui.notify("Key generada. Cópiala ahora.", type="warning")

                    with ui.row().classes("w-full gap-2"):
                        ui.button(
                            t("admin.clients.generate_key"),
                            icon="vpn_key",
                            on_click=generate_license_key,
                        ).props("color=primary")

                        def copy_key():
                            if generated_key_display.value:
                                ui.run_javascript(
                                    f'navigator.clipboard.writeText("{generated_key_display.value}")'
                                )
                                ui.notify(
                                    t("admin.clients.key_copied"), type="positive"
                                )

                        ui.button(
                            t("admin.clients.copy_to_clipboard"),
                            icon="content_copy",
                            on_click=copy_key,
                        ).props("flat")

                    # Warning Box
                    with ui.card().classes(
                        "w-full bg-yellow-50 border border-yellow-300 p-4 mt-4"
                    ):
                        ui.label(t("admin.clients.key_warning")).classes(
                            "text-yellow-800 font-bold"
                        )
                        ui.label(
                            "Esta clave se guardará hasheada (SHA256) en la base de datos y no será recuperable."
                        ).classes("text-sm text-yellow-700")

                    with ui.stepper_navigation():
                        ui.button("Anterior", on_click=stepper.previous).props("flat")
                        ui.button("Siguiente", on_click=stepper.next).props(
                            "color=primary"
                        )

                # STEP 3: Configuración Licencia
                with ui.step("Configuración Licencia"):
                    new_license_id = (
                        ui.input(
                            label=t("admin.clients.license_id"), placeholder="lic_001"
                        )
                        .classes("w-full")
                        .props("outlined dense")
                    )

                    new_quota = (
                        ui.number(
                            label=t("admin.clients.quota_tokens"),
                            value=1000000,
                            format="%d",
                            step=100000,
                        )
                        .classes("w-full")
                        .props("outlined dense")
                    )

                    default_date = (datetime.now() + timedelta(days=365)).strftime(
                        "%Y-%m-%d"
                    )

                    new_valid_until = (
                        ui.input(
                            label=t("admin.clients.valid_until"), value=default_date
                        )
                        .classes("w-full")
                        .props("outlined dense type=date")
                    )

                    with ui.stepper_navigation():
                        ui.button("Anterior", on_click=stepper.previous).props("flat")

                        async def save_client_and_license():
                            # Validations
                            if not new_client_id.value or not new_client_name.value:
                                ui.notify(
                                    "ID y Nombre son obligatorios", type="negative"
                                )
                                return

                            if not partner_select.value:
                                ui.notify(
                                    "Debes seleccionar un Partner", type="negative"
                                )
                                return

                            if not generated_key_value["key"]:
                                ui.notify(
                                    "Debes generar una License Key", type="negative"
                                )
                                return

                            if not new_license_id.value:
                                ui.notify(
                                    "ID de Licencia es obligatorio", type="negative"
                                )
                                return

                            # Hash the key
                            hashed_key = hash_license_key(generated_key_value["key"])

                            async with AsyncSession(server_engine) as session:
                                # Check duplicates
                                existing_client = await session.get(
                                    ClientAccount, new_client_id.value
                                )
                                if existing_client:
                                    ui.notify(
                                        "Ya existe un cliente con ese ID",
                                        type="negative",
                                    )
                                    return

                                existing_license = await session.get(
                                    License, new_license_id.value
                                )
                                if existing_license:
                                    ui.notify(
                                        "Ya existe una licencia con ese ID",
                                        type="negative",
                                    )
                                    return

                                # Create Client
                                client = ClientAccount(
                                    client_id=new_client_id.value,
                                    name=new_client_name.value,
                                    partner_id=partner_select.value,
                                    license_key=hashed_key,
                                    is_active=True,
                                )
                                session.add(client)

                                # Create License
                                license = License(
                                    license_id=new_license_id.value,
                                    client_id=client.client_id,
                                    quota_tokens=int(new_quota.value),
                                    consumed_tokens=0,
                                    valid_until=datetime.strptime(
                                        new_valid_until.value, "%Y-%m-%d"
                                    ),
                                    status=LicenseStatus.ACTIVE.value,
                                )
                                session.add(license)

                                await session.commit()

                            ui.notify(
                                t("admin.clients.client_created"), type="positive"
                            )
                            create_client_dialog.close()
                            await refresh_clients()

                            # Reset form
                            stepper.value = stepper.props["model-value"] = (
                                "Datos Básicos"
                            )
                            new_client_id.value = ""
                            new_client_name.value = ""
                            partner_select.value = None
                            generated_key_display.value = ""
                            generated_key_value["key"] = None
                            new_license_id.value = ""
                            new_quota.value = 1000000

                        ui.button(
                            "Crear Cliente",
                            icon="save",
                            on_click=save_client_and_license,
                        ).props("color=primary")

        # --- TABLE ACTIONS ---
        client_table.add_slot(
            "body-cell-status",
            r"""
            <q-td :props="props">
                <q-badge :color="props.row.status_color">
                    {{ props.row.license_status }}
                </q-badge>
            </q-td>
        """,
        )

        client_table.add_slot(
            "body-cell-actions",
            r"""
            <q-td :props="props">
                <q-btn size="sm" flat dense icon="visibility" color="blue" 
                       @click="() => $parent.$emit('view', props.row)">
                    <q-tooltip>Ver Detalles</q-tooltip>
                </q-btn>
            </q-td>
        """,
        )

        # --- DETAIL DIALOG ---
        detail_dialog = ui.dialog()
        detail_state = {"client": None, "license": None, "consumption": None}

        with detail_dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label("Detalles del Cliente").classes("text-xl font-bold mb-4")

            @ui.refreshable
            def render_detail_content():
                if not detail_state["client"]:
                    ui.label("Cargando...")
                    return

                client = detail_state["client"]
                license = detail_state["license"]
                consumption = detail_state["consumption"]

                # Info básica
                with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                    with ui.column():
                        ui.label("Cliente").classes("text-sm text-gray-500")
                        ui.label(f"{client['name']} ({client['client_id']})").classes(
                            "font-bold"
                        )
                    with ui.column():
                        ui.label("Partner").classes("text-sm text-gray-500")
                        ui.label(client["partner_name"]).classes("font-bold")

                ui.separator().classes("my-4")

                # Licencia
                ui.label("Licencia").classes("text-lg font-bold mb-2")
                with ui.grid(columns=3).classes("w-full gap-4 mb-4"):
                    with ui.column():
                        ui.label("ID").classes("text-sm text-gray-500")
                        ui.label(license["license_id"]).classes("font-bold")
                    with ui.column():
                        ui.label("Estado").classes("text-sm text-gray-500")
                        ui.badge(license["status"], color=license["status_color"])
                    with ui.column():
                        ui.label("Válida hasta").classes("text-sm text-gray-500")
                        ui.label(license["valid_until"]).classes("font-bold")

                # Barra de progreso de cuota
                usage_pct = (
                    (license["consumed"] / license["quota"] * 100)
                    if license["quota"] > 0
                    else 0
                )
                ui.label(
                    f"Uso de Cuota: {license['consumed']:,} / {license['quota']:,} tokens ({usage_pct:.1f}%)"
                ).classes("text-sm mt-2")
                ui.linear_progress(value=usage_pct / 100, show_value=False).props(
                    f"color={'red' if usage_pct > 90 else 'orange' if usage_pct > 70 else 'green'}"
                )

                ui.separator().classes("my-4")

                # Consumo
                ui.label("Consumo Este Mes").classes("text-lg font-bold mb-2")
                if consumption:
                    with ui.row().classes("w-full gap-8 mb-4"):
                        with ui.card().classes("p-4 bg-blue-50"):
                            ui.label("Tokens").classes("text-sm text-gray-600")
                            ui.label(f"{consumption.get('total_tokens', 0):,}").classes(
                                "text-2xl font-bold text-blue-800"
                            )
                        with ui.card().classes("p-4 bg-green-50"):
                            ui.label("Coste USD").classes("text-sm text-gray-600")
                            ui.label(
                                f"${consumption.get('total_cost_usd', 0):.4f}"
                            ).classes("text-2xl font-bold text-green-800")

                    # Últimas operaciones
                    if consumption.get("recent_operations"):
                        ui.label("Últimas Operaciones").classes("font-bold mt-4 mb-2")
                        op_columns = [
                            {
                                "name": "timestamp",
                                "label": "Fecha",
                                "field": "timestamp",
                                "align": "left",
                            },
                            {
                                "name": "model_id",
                                "label": "Modelo",
                                "field": "model_id",
                                "align": "left",
                            },
                            {
                                "name": "tokens_used",
                                "label": "Tokens",
                                "field": "tokens_used",
                                "align": "right",
                            },
                            {
                                "name": "cost_usd",
                                "label": "USD",
                                "field": "cost_usd",
                                "align": "right",
                            },
                        ]
                        ui.table(
                            columns=op_columns,
                            rows=consumption["recent_operations"],
                            row_key="timestamp",
                        ).classes("w-full").props("dense flat")
                else:
                    ui.label("Sin datos de consumo disponibles").classes(
                        "text-gray-500"
                    )

            render_detail_content()

            with ui.row().classes("w-full justify-end mt-4"):
                ui.button("Cerrar", on_click=detail_dialog.close).props("flat")

        async def show_client_detail(row):
            detail_state["client"] = row
            detail_state["license"] = None
            detail_state["consumption"] = None

            async with AsyncSession(server_engine) as session:
                # Obtener licencia completa
                license = await session.get(License, row["license_id"])
                if license:
                    detail_state["license"] = {
                        "license_id": license.license_id,
                        "status": get_status_label(license),
                        "status_color": get_status_color(license),
                        "quota": license.quota_tokens,
                        "consumed": license.consumed_tokens,
                        "valid_until": license.valid_until.strftime("%Y-%m-%d")
                        if license.valid_until
                        else "N/A",
                    }

                # Obtener consumo
                from server.app.services.consumption_query_service import (
                    ConsumptionQueryService,
                )

                service = ConsumptionQueryService(session)
                now = datetime.utcnow()
                detail_state["consumption"] = await service.get_client_summary(
                    row["client_id"], now.year, now.month
                )

            render_detail_content.refresh()
            detail_dialog.open()

        client_table.on("view", lambda e: show_client_detail(e.args))

        # --- REFRESH FUNCTION ---
        async def refresh_clients():
            async with AsyncSession(server_engine) as session:
                statement = (
                    select(ClientAccount, License, PartnerAccount)
                    .join(License, ClientAccount.client_id == License.client_id)
                    .join(
                        PartnerAccount,
                        ClientAccount.partner_id == PartnerAccount.partner_id,
                    )
                )

                # Aplicar filtro por partner
                if filter_state["partner_id"]:
                    statement = statement.where(
                        ClientAccount.partner_id == filter_state["partner_id"]
                    )

                results = await session.exec(statement)
                data = results.all()

                rows = []
                for client, license, partner in data:
                    # Aplicar filtro de búsqueda
                    if filter_state["search_query"]:
                        search_lower = filter_state["search_query"].lower()
                        if (
                            search_lower not in client.name.lower()
                            and search_lower not in client.client_id.lower()
                        ):
                            continue

                    status_color = get_status_color(license)
                    status_label = get_status_label(license)

                    rows.append(
                        {
                            "client_id": client.client_id,
                            "name": client.name,
                            "partner_name": partner.name,
                            "partner_id": partner.partner_id,
                            "license_id": license.license_id,
                            "license_status": status_label,
                            "status_color": status_color,
                            "quota_display": f"{license.consumed_tokens:,} / {license.quota_tokens:,}",
                        }
                    )

                client_table.rows = rows
                client_table.update()

        # Initial load
        ui.timer(0.1, refresh_clients, once=True)

        # Action Buttons
        with ui.row().classes("w-full justify-between mt-4"):
            ui.button(
                t("admin.clients.add_client"),
                icon="add",
                on_click=create_client_dialog.open,
            ).props("color=primary")
            ui.button(
                t("common.update"), icon="refresh", on_click=refresh_clients
            ).props("flat dense")
