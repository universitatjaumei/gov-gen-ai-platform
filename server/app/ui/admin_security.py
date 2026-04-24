"""
Panel de gestión de Políticas de Seguridad para Administradores.

Permite configurar las restricciones en cascada (SYSTEM → PARTNER → CLIENT).
Controla dominios permitidos, librerías Python restringidas y límites de
recursos para la ejecución de automatizaciones.
"""

from nicegui import ui
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.database.models import PartnerAccount, ClientAccount
from server.app.services.security_policy_service import SecurityPolicyService


def admin_security_content():
    """
    Renderiza la interfaz de gestión de seguridad avanzada.

    Proporciona diálogos para la edición de políticas a nivel de sistema,
    partner y cliente, sincronizando los cambios con el SecurityPolicyService.
    """
    t = state.i18n.t

    # === STATE ===
    current_system_policy = {"data": None}
    selected_partner = {"id": None, "name": ""}

    # === DIALOGS ===
    system_policy_dialog = ui.dialog()
    partner_policy_dialog = ui.dialog()
    client_policy_dialog = ui.dialog()

    # Form state

    # === SYSTEM POLICY DIALOG ===
    with system_policy_dialog, ui.card().classes("w-full max-w-2xl"):
        ui.label(t("admin.security.system_policy")).classes("text-xl font-bold mb-4")

        with ui.column().classes("w-full gap-4"):
            # Domains
            ui.label(t("admin.security.allowed_domains")).classes(
                "font-semibold text-gray-700"
            )
            sys_allow_all = ui.checkbox(
                t("admin.security.allow_all_domains"), value=True
            )
            sys_domains_area = (
                ui.textarea(
                    placeholder="ejemplo.com\n*.midominio.es",
                )
                .props("outlined rows=3")
                .classes("w-full")
            )
            sys_domains_area.bind_visibility_from(
                sys_allow_all, "value", lambda v: not v
            )

            ui.separator()

            # Libraries
            with ui.row().classes("w-full gap-4"):
                with ui.column().classes("flex-1"):
                    ui.label(t("admin.security.allowed_libraries")).classes(
                        "font-semibold text-gray-700"
                    )
                    sys_allowed_libs = (
                        ui.textarea(
                            value="pandas\njson\nre\nmath\ndatetime\nopenpyxl\nxlrd\nnumpy",
                            placeholder="Una librería por línea",
                        )
                        .props("outlined rows=6")
                        .classes("w-full")
                    )

                with ui.column().classes("flex-1"):
                    ui.label(t("admin.security.forbidden_libraries")).classes(
                        "font-semibold text-gray-700"
                    )
                    sys_forbidden_libs = (
                        ui.textarea(
                            value="os\nsys\nsubprocess\nrequests\nsocket\nshutil\nctypes",
                            placeholder="Una librería por línea",
                        )
                        .props("outlined rows=6")
                        .classes("w-full")
                    )

            ui.separator()

            # Resource Limits
            ui.label(t("admin.security.max_execution_time")).classes(
                "font-semibold text-gray-700"
            )
            sys_max_time = ui.slider(min=30, max=1800, step=30, value=300).classes(
                "w-full"
            )
            sys_time_label = ui.label("300 segundos").classes("text-sm text-gray-500")
            sys_max_time.on(
                "update:model-value",
                lambda e: sys_time_label.set_text(f"{e.args} segundos"),
            )

            ui.label(t("admin.security.max_memory")).classes(
                "font-semibold text-gray-700"
            )
            sys_max_mem = ui.slider(min=128, max=4096, step=128, value=512).classes(
                "w-full"
            )
            sys_mem_label = ui.label("512 MB").classes("text-sm text-gray-500")
            sys_max_mem.on(
                "update:model-value", lambda e: sys_mem_label.set_text(f"{e.args} MB")
            )

            ui.separator()

            # Screenshot Policy
            ui.label("Política de Capturas de Pantalla (RPA)").classes(
                "font-semibold text-gray-700"
            )
            sys_screenshot_policy = (
                ui.radio(
                    options={
                        "BLOCK": "Bloquear Todo (Alta Seguridad)",
                        "REVIEW": "Revisión Obligatoria (Recomendado)",
                        "TRUSTED": "Dominios de Confianza",
                    },
                    value="REVIEW",
                )
                .props("inline")
                .classes("w-full")
            )

            ui.label("Dominios de Confianza (Screenshot)").classes(
                "text-sm text-gray-600 q-mt-sm"
            )
            sys_trusted_domains = (
                ui.textarea(placeholder="boe.es\n*.gob.es")
                .props("outlined rows=2")
                .classes("w-full")
            )
            # Only show if TRUSTED is selected
            sys_trusted_domains.bind_visibility_from(
                sys_screenshot_policy, "value", lambda v: v == "TRUSTED"
            )

        async def save_system_policy():
            async with AsyncSession(server_engine) as session:
                service = SecurityPolicyService(session)

                domains = (
                    ["*"]
                    if sys_allow_all.value
                    else [
                        d.strip()
                        for d in sys_domains_area.value.split("\n")
                        if d.strip()
                    ]
                )
                allowed = [
                    lib.strip()
                    for lib in sys_allowed_libs.value.split("\n")
                    if lib.strip()
                ]
                forbidden = [
                    lib.strip()
                    for lib in sys_forbidden_libs.value.split("\n")
                    if lib.strip()
                ]

                await service.save_system_policy(
                    allowed_domains=domains,
                    allowed_libraries=allowed,
                    forbidden_libraries=forbidden,
                    max_execution_time=int(sys_max_time.value),
                    max_memory_mb=int(sys_max_mem.value),
                    screenshot_policy=sys_screenshot_policy.value,
                    trusted_screenshot_domains=[
                        d.strip()
                        for d in sys_trusted_domains.value.split("\n")
                        if d.strip()
                    ],
                )

            ui.notify(t("admin.security.policy_saved"), type="positive")
            system_policy_dialog.close()
            await refresh_system_policy()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(
                t("admin.common.cancel"), on_click=system_policy_dialog.close
            ).props("flat")
            ui.button(
                t("admin.common.save"), icon="save", on_click=save_system_policy
            ).props("color=primary")

    # === PARTNER POLICY DIALOG ===
    partner_dialog_state = {"partner_id": None, "partner_name": ""}

    with partner_policy_dialog, ui.card().classes("w-full max-w-2xl"):
        partner_dialog_title = ui.label("").classes("text-xl font-bold mb-4")

        with ui.column().classes("w-full gap-4"):
            # Domains
            ui.label(t("admin.security.allowed_domains")).classes(
                "font-semibold text-gray-700"
            )
            partner_allow_all = ui.checkbox(
                t("admin.security.allow_all_domains"), value=True
            )
            partner_domains_area = (
                ui.textarea(
                    placeholder="ejemplo.com\n*.midominio.es",
                )
                .props("outlined rows=3")
                .classes("w-full")
            )
            partner_domains_area.bind_visibility_from(
                partner_allow_all, "value", lambda v: not v
            )

            ui.separator()

            # Libraries
            with ui.row().classes("w-full gap-4"):
                with ui.column().classes("flex-1"):
                    ui.label(t("admin.security.allowed_libraries")).classes(
                        "font-semibold text-gray-700"
                    )
                    partner_allowed_libs = (
                        ui.textarea(
                            value="pandas\njson\nre\nmath\ndatetime\nopenpyxl\nxlrd\nnumpy",
                            placeholder="Una librería por línea",
                        )
                        .props("outlined rows=6")
                        .classes("w-full")
                    )

                with ui.column().classes("flex-1"):
                    ui.label(t("admin.security.forbidden_libraries")).classes(
                        "font-semibold text-gray-700"
                    )
                    partner_forbidden_libs = (
                        ui.textarea(
                            value="os\nsys\nsubprocess\nrequests\nsocket\nshutil\nctypes",
                            placeholder="Una librería por línea",
                        )
                        .props("outlined rows=6")
                        .classes("w-full")
                    )

            ui.separator()

            # Resource Limits
            ui.label(t("admin.security.max_execution_time")).classes(
                "font-semibold text-gray-700"
            )
            partner_max_time = ui.slider(min=30, max=1800, step=30, value=300).classes(
                "w-full"
            )
            partner_time_label = ui.label("300 segundos").classes(
                "text-sm text-gray-500"
            )
            partner_max_time.on(
                "update:model-value",
                lambda e: partner_time_label.set_text(f"{e.args} segundos"),
            )

            ui.label(t("admin.security.max_memory")).classes(
                "font-semibold text-gray-700"
            )
            partner_max_mem = ui.slider(min=128, max=4096, step=128, value=512).classes(
                "w-full"
            )
            partner_mem_label = ui.label("512 MB").classes("text-sm text-gray-500")
            partner_max_mem.on(
                "update:model-value",
                lambda e: partner_mem_label.set_text(f"{e.args} MB"),
            )

            ui.separator()

            # Screenshot Policy
            ui.label("Política de Capturas de Pantalla (RPA)").classes(
                "font-semibold text-gray-700"
            )
            partner_screenshot_policy = (
                ui.radio(
                    options={
                        "BLOCK": "Bloquear Todo (Alta Seguridad)",
                        "REVIEW": "Revisión Obligatoria (Recomendado)",
                        "TRUSTED": "Dominios de Confianza",
                    },
                    value="REVIEW",
                )
                .props("inline")
                .classes("w-full")
            )

            ui.label("Dominios de Confianza (Screenshot)").classes(
                "text-sm text-gray-600 q-mt-sm"
            )
            partner_trusted_domains = (
                ui.textarea(placeholder="boe.es\n*.gob.es")
                .props("outlined rows=2")
                .classes("w-full")
            )
            # Only show if TRUSTED is selected
            partner_trusted_domains.bind_visibility_from(
                partner_screenshot_policy, "value", lambda v: v == "TRUSTED"
            )

        async def save_partner_policy():
            async with AsyncSession(server_engine) as session:
                service = SecurityPolicyService(session)

                domains = (
                    ["*"]
                    if partner_allow_all.value
                    else [
                        d.strip()
                        for d in partner_domains_area.value.split("\n")
                        if d.strip()
                    ]
                )
                allowed = [
                    lib.strip()
                    for lib in partner_allowed_libs.value.split("\n")
                    if lib.strip()
                ]
                forbidden = [
                    lib.strip()
                    for lib in partner_forbidden_libs.value.split("\n")
                    if lib.strip()
                ]

                await service.save_partner_policy(
                    partner_id=partner_dialog_state["partner_id"],
                    allowed_domains=domains,
                    allowed_libraries=allowed,
                    forbidden_libraries=forbidden,
                    max_execution_time=int(partner_max_time.value),
                    max_memory_mb=int(partner_max_mem.value),
                    screenshot_policy=partner_screenshot_policy.value,
                    trusted_screenshot_domains=[
                        d.strip()
                        for d in partner_trusted_domains.value.split("\n")
                        if d.strip()
                    ],
                )

            ui.notify(t("admin.security.policy_saved"), type="positive")
            partner_policy_dialog.close()
            await refresh_partners_table()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(
                t("admin.common.cancel"), on_click=partner_policy_dialog.close
            ).props("flat")
            ui.button(
                t("admin.common.save"), icon="save", on_click=save_partner_policy
            ).props("color=primary")

    # === CLIENT POLICY DIALOG ===
    client_dialog_state = {"client_id": None, "client_name": "", "partner_id": None}

    with client_policy_dialog, ui.card().classes("w-full max-w-2xl"):
        client_dialog_title = ui.label("").classes("text-xl font-bold mb-4")

        with ui.column().classes("w-full gap-4"):
            # Domains
            ui.label(t("admin.security.allowed_domains")).classes(
                "font-semibold text-gray-700"
            )
            client_allow_all = ui.checkbox(
                t("admin.security.allow_all_domains"), value=True
            )
            client_domains_area = (
                ui.textarea(
                    placeholder="ejemplo.com\n*.midominio.es",
                )
                .props("outlined rows=3")
                .classes("w-full")
            )
            client_domains_area.bind_visibility_from(
                client_allow_all, "value", lambda v: not v
            )

            ui.separator()

            # Libraries
            with ui.row().classes("w-full gap-4"):
                with ui.column().classes("flex-1"):
                    ui.label(t("admin.security.allowed_libraries")).classes(
                        "font-semibold text-gray-700"
                    )
                    client_allowed_libs = (
                        ui.textarea(
                            value="pandas\njson\nre\nmath\ndatetime\nopenpyxl\nxlrd\nnumpy",
                            placeholder="Una librería por línea",
                        )
                        .props("outlined rows=6")
                        .classes("w-full")
                    )

                with ui.column().classes("flex-1"):
                    ui.label(t("admin.security.forbidden_libraries")).classes(
                        "font-semibold text-gray-700"
                    )
                    client_forbidden_libs = (
                        ui.textarea(
                            value="os\nsys\nsubprocess\nrequests\nsocket\nshutil\nctypes",
                            placeholder="Una librería por línea",
                        )
                        .props("outlined rows=6")
                        .classes("w-full")
                    )

            ui.separator()

            # Resource Limits
            ui.label(t("admin.security.max_execution_time")).classes(
                "font-semibold text-gray-700"
            )
            client_max_time = ui.slider(min=30, max=1800, step=30, value=300).classes(
                "w-full"
            )
            client_time_label = ui.label("300 segundos").classes(
                "text-sm text-gray-500"
            )
            client_max_time.on(
                "update:model-value",
                lambda e: client_time_label.set_text(f"{e.args} segundos"),
            )

            ui.label(t("admin.security.max_memory")).classes(
                "font-semibold text-gray-700"
            )
            client_max_mem = ui.slider(min=128, max=4096, step=128, value=512).classes(
                "w-full"
            )
            client_mem_label = ui.label("512 MB").classes("text-sm text-gray-500")
            client_max_mem.on(
                "update:model-value",
                lambda e: client_mem_label.set_text(f"{e.args} MB"),
            )

            ui.separator()

            # Screenshot Policy
            ui.label("Política de Capturas de Pantalla (RPA)").classes(
                "font-semibold text-gray-700"
            )
            client_screenshot_policy = (
                ui.radio(
                    options={
                        "BLOCK": "Bloquear Todo (Alta Seguridad)",
                        "REVIEW": "Revisión Obligatoria (Recomendado)",
                        "TRUSTED": "Dominios de Confianza",
                    },
                    value="REVIEW",
                )
                .props("inline")
                .classes("w-full")
            )

            ui.label("Dominios de Confianza (Screenshot)").classes(
                "text-sm text-gray-600 q-mt-sm"
            )
            client_trusted_domains = (
                ui.textarea(placeholder="boe.es\n*.gob.es")
                .props("outlined rows=2")
                .classes("w-full")
            )
            # Only show if TRUSTED is selected
            client_trusted_domains.bind_visibility_from(
                client_screenshot_policy, "value", lambda v: v == "TRUSTED"
            )

        async def save_client_policy():
            async with AsyncSession(server_engine) as session:
                service = SecurityPolicyService(session)

                domains = (
                    ["*"]
                    if client_allow_all.value
                    else [
                        d.strip()
                        for d in client_domains_area.value.split("\n")
                        if d.strip()
                    ]
                )
                allowed = [
                    lib.strip()
                    for lib in client_allowed_libs.value.split("\n")
                    if lib.strip()
                ]
                forbidden = [
                    lib.strip()
                    for lib in client_forbidden_libs.value.split("\n")
                    if lib.strip()
                ]

                await service.save_client_policy(
                    client_id=client_dialog_state["client_id"],
                    partner_id=client_dialog_state["partner_id"],
                    allowed_domains=domains,
                    allowed_libraries=allowed,
                    forbidden_libraries=forbidden,
                    max_execution_time=int(client_max_time.value),
                    max_memory_mb=int(client_max_mem.value),
                    screenshot_policy=client_screenshot_policy.value,
                    trusted_screenshot_domains=[
                        d.strip()
                        for d in client_trusted_domains.value.split("\n")
                        if d.strip()
                    ],
                )

            ui.notify(t("admin.security.policy_saved"), type="positive")
            client_policy_dialog.close()
            await refresh_clients_table()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(
                t("admin.common.cancel"), on_click=client_policy_dialog.close
            ).props("flat")
            ui.button(
                t("admin.common.save"), icon="save", on_click=save_client_policy
            ).props("color=primary")

    # === MAIN CONTENT ===
    ui.label(t("admin.security.title")).classes(
        "text-2xl font-bold mb-6 text-slate-800"
    )

    # 1. SYSTEM POLICY CARD
    with ui.card().classes("w-full p-4 mb-4"):
        with ui.row().classes("w-full justify-between items-center mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("shield", size="md").classes("text-blue-600")
                ui.label(t("admin.security.system_policy")).classes("text-lg font-bold")
            ui.button(
                t("admin.common.edit"),
                icon="edit",
                on_click=lambda: open_system_policy_dialog(),
            ).props("flat color=primary")

        system_policy_display = ui.column().classes("w-full")

        @ui.refreshable
        def render_system_policy():
            system_policy_display.clear()
            data = current_system_policy["data"]

            if not data:
                with system_policy_display:
                    ui.label("Cargando...").classes("text-gray-500")
                return

            with system_policy_display:
                with ui.grid(columns=4).classes("w-full gap-4"):
                    with ui.card().classes("p-3 bg-blue-50"):
                        ui.label(t("admin.security.allowed_domains")).classes(
                            "text-xs text-gray-500 uppercase"
                        )
                        domains = data.get("allowed_domains", [])
                        if domains == ["*"]:
                            ui.label("Todos los dominios").classes(
                                "font-bold text-blue-700"
                            )
                        else:
                            ui.label(f"{len(domains)} dominios").classes(
                                "font-bold text-blue-700"
                            )

                    with ui.card().classes("p-3 bg-green-50"):
                        ui.label(t("admin.security.allowed_libraries")).classes(
                            "text-xs text-gray-500 uppercase"
                        )
                        ui.label(
                            f"{len(data.get('allowed_libraries', []))} librerías"
                        ).classes("font-bold text-green-700")

                    with ui.card().classes("p-3 bg-red-50"):
                        ui.label(t("admin.security.forbidden_libraries")).classes(
                            "text-xs text-gray-500 uppercase"
                        )
                        ui.label(
                            f"{len(data.get('forbidden_libraries', []))} librerías"
                        ).classes("font-bold text-red-700")

                    with ui.card().classes("p-3 bg-orange-50"):
                        ui.label("Límites").classes("text-xs text-gray-500 uppercase")
                        ui.label(
                            f"{data.get('max_execution_time', 300)}s / {data.get('max_memory_mb', 512)}MB"
                        ).classes("font-bold text-orange-700")

        render_system_policy()

    # 2. PARTNERS POLICIES
    with ui.card().classes("w-full p-4 mb-4"):
        with ui.row().classes("w-full justify-between items-center mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("business", size="md").classes("text-indigo-600")
                ui.label(t("admin.security.partner_policies")).classes(
                    "text-lg font-bold"
                )

        partners_columns = [
            {
                "name": "partner_id",
                "label": "Partner ID",
                "field": "partner_id",
                "align": "left",
            },
            {"name": "name", "label": "Nombre", "field": "name", "align": "left"},
            {
                "name": "policy_status",
                "label": t("admin.security.policy_scope"),
                "field": "policy_status",
                "align": "center",
            },
            {
                "name": "actions",
                "label": t("admin.common.actions"),
                "field": "actions",
                "align": "center",
            },
        ]

        partners_table = ui.table(
            columns=partners_columns, rows=[], row_key="partner_id"
        ).classes("w-full")

        partners_table.add_slot(
            "body-cell-policy_status",
            r"""
            <q-td :props="props">
                <q-badge :color="props.row.has_policy ? 'green' : 'grey'">
                    {{ props.row.has_policy ? 'PERSONALIZADA' : 'SISTEMA' }}
                </q-badge>
            </q-td>
        """,
        )

        partners_table.add_slot(
            "body-cell-actions",
            r"""
            <q-td :props="props">
                <q-btn size="sm" flat dense icon="edit" color="primary"
                       @click="() => $parent.$emit('edit_partner', props.row)">
                    <q-tooltip>Editar Política</q-tooltip>
                </q-btn>
                <q-btn v-if="props.row.has_policy" size="sm" flat dense icon="delete" color="red"
                       @click="() => $parent.$emit('delete_partner', props.row)">
                    <q-tooltip>Eliminar Política</q-tooltip>
                </q-btn>
            </q-td>
        """,
        )

        partners_table.on("edit_partner", lambda e: open_partner_policy_dialog(e.args))
        partners_table.on("delete_partner", lambda e: delete_partner_policy(e.args))

    # 3. CLIENTS POLICIES
    with ui.card().classes("w-full p-4"):
        with ui.row().classes("w-full justify-between items-center mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("badge", size="md").classes("text-teal-600")
                ui.label(t("admin.security.client_policies")).classes(
                    "text-lg font-bold"
                )

        # Partner filter
        with ui.row().classes("w-full mb-4"):
            partner_select = (
                ui.select(
                    options=[],
                    label="Filtrar por Partner",
                    on_change=lambda e: on_partner_filter_change(e.value),
                )
                .classes("w-64")
                .props("outlined dense clearable")
            )

        clients_columns = [
            {
                "name": "client_id",
                "label": "Client ID",
                "field": "client_id",
                "align": "left",
            },
            {
                "name": "name",
                "label": "Nombre",
                "field": "client_name",
                "align": "left",
            },
            {
                "name": "partner_name",
                "label": "Partner",
                "field": "partner_name",
                "align": "left",
            },
            {
                "name": "policy_level",
                "label": t("admin.security.effective_policy"),
                "field": "policy_level",
                "align": "center",
            },
            {
                "name": "actions",
                "label": t("admin.common.actions"),
                "field": "actions",
                "align": "center",
            },
        ]

        clients_table = ui.table(
            columns=clients_columns, rows=[], row_key="client_id"
        ).classes("w-full")

        clients_table.add_slot(
            "body-cell-policy_level",
            r"""
            <q-td :props="props">
                <q-badge :color="props.row.policy_level === 'CLIENT' ? 'green' : props.row.policy_level === 'PARTNER' ? 'blue' : 'grey'">
                    {{ props.row.policy_level }}
                </q-badge>
            </q-td>
        """,
        )

        clients_table.add_slot(
            "body-cell-actions",
            r"""
            <q-td :props="props">
                <q-btn size="sm" flat dense icon="edit" color="primary"
                       @click="() => $parent.$emit('edit_client', props.row)">
                    <q-tooltip>Editar Política</q-tooltip>
                </q-btn>
                <q-btn v-if="props.row.policy_level === 'CLIENT'" size="sm" flat dense icon="delete" color="red"
                       @click="() => $parent.$emit('delete_client', props.row)">
                    <q-tooltip>Eliminar Política</q-tooltip>
                </q-btn>
            </q-td>
        """,
        )

        clients_table.on("edit_client", lambda e: open_client_policy_dialog(e.args))
        clients_table.on("delete_client", lambda e: delete_client_policy(e.args))

    # === HELPER FUNCTIONS ===

    async def refresh_system_policy():
        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            policy = await service.get_system_policy()
            current_system_policy["data"] = service._policy_to_dict(policy, "SYSTEM")
        render_system_policy.refresh()

    async def refresh_partners_table():
        async with AsyncSession(server_engine) as session:
            # Get all partners
            result = await session.exec(
                select(PartnerAccount).where(PartnerAccount.is_active)
            )
            partners = result.all()

            service = SecurityPolicyService(session)

            rows = []
            options = []
            for p in partners:
                policy = await service.get_partner_policy(p.partner_id)
                rows.append(
                    {
                        "partner_id": p.partner_id,
                        "name": p.name,
                        "has_policy": policy is not None,
                        "policy_id": policy.id if policy else None,
                    }
                )
                options.append({"label": p.name, "value": p.partner_id})

            partners_table.rows = rows
            partners_table.update()

            # Update partner filter options
            partner_select.options = options
            partner_select.update()

    async def refresh_clients_table():
        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)

            # Get clients (filtered or all)
            if selected_partner["id"]:
                stmt = select(ClientAccount).where(
                    ClientAccount.partner_id == selected_partner["id"],
                    ClientAccount.is_active,
                )
            else:
                stmt = select(ClientAccount).where(ClientAccount.is_active)

            result = await session.exec(stmt)
            clients = result.all()

            rows = []
            for c in clients:
                # Get partner name
                partner = await session.get(PartnerAccount, c.partner_id)

                # Get effective policy level
                client_policy = await service.get_client_policy(c.client_id)
                if client_policy:
                    policy_level = "CLIENT"
                    policy_id = client_policy.id
                else:
                    partner_policy = await service.get_partner_policy(c.partner_id)
                    if partner_policy:
                        policy_level = "PARTNER"
                        policy_id = partner_policy.id
                    else:
                        policy_level = "SYSTEM"
                        system_policy = await service.get_system_policy()
                        policy_id = system_policy.id

                rows.append(
                    {
                        "client_id": c.client_id,
                        "client_name": c.name,
                        "partner_id": c.partner_id,
                        "partner_name": partner.name if partner else "Unknown",
                        "policy_level": policy_level,
                        "policy_id": policy_id,
                    }
                )

            clients_table.rows = rows
            clients_table.update()

    def on_partner_filter_change(partner_id):
        selected_partner["id"] = partner_id
        ui.timer(0.1, refresh_clients_table, once=True)

    async def open_system_policy_dialog():
        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            policy = await service.get_system_policy()

            # Populate form
            domains = service._parse_json(policy.allowed_domains)
            sys_allow_all.value = domains == ["*"]
            sys_domains_area.value = "" if domains == ["*"] else "\n".join(domains)

            sys_allowed_libs.value = "\n".join(
                service._parse_json(policy.allowed_libraries)
            )
            sys_forbidden_libs.value = "\n".join(
                service._parse_json(policy.forbidden_libraries)
            )

            sys_max_time.value = policy.max_execution_time
            sys_time_label.text = f"{policy.max_execution_time} segundos"
            sys_max_mem.value = policy.max_memory_mb
            sys_mem_label.text = f"{policy.max_memory_mb} MB"

            # Populate Screenshot Policy
            sys_screenshot_policy.value = getattr(policy, "screenshot_policy", "REVIEW")
            trusted = service._parse_json(
                getattr(policy, "trusted_screenshot_domains", "[]")
            )
            sys_trusted_domains.value = "\n".join(trusted)

        system_policy_dialog.open()

    async def open_partner_policy_dialog(row):
        partner_dialog_state["partner_id"] = row["partner_id"]
        partner_dialog_state["partner_name"] = row["name"]
        partner_dialog_title.text = f"Política del Partner: {row['name']}"

        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            policy = await service.get_partner_policy(row["partner_id"])

            if policy:
                domains = service._parse_json(policy.allowed_domains)
                partner_allow_all.value = domains == ["*"]
                partner_domains_area.value = (
                    "" if domains == ["*"] else "\n".join(domains)
                )
                partner_allowed_libs.value = "\n".join(
                    service._parse_json(policy.allowed_libraries)
                )
                partner_forbidden_libs.value = "\n".join(
                    service._parse_json(policy.forbidden_libraries)
                )
                partner_max_time.value = policy.max_execution_time
                partner_time_label.text = f"{policy.max_execution_time} segundos"
                partner_max_mem.value = policy.max_memory_mb
                partner_mem_label.text = f"{policy.max_memory_mb} MB"

                # Populate Screenshot Policy
                partner_screenshot_policy.value = getattr(
                    policy, "screenshot_policy", "REVIEW"
                )
                trusted = service._parse_json(
                    getattr(policy, "trusted_screenshot_domains", "[]")
                )
                partner_trusted_domains.value = "\n".join(trusted)
            else:
                # Load system defaults
                system_policy = await service.get_system_policy()
                domains = service._parse_json(system_policy.allowed_domains)
                partner_allow_all.value = domains == ["*"]
                partner_domains_area.value = (
                    "" if domains == ["*"] else "\n".join(domains)
                )
                partner_allowed_libs.value = "\n".join(
                    service._parse_json(system_policy.allowed_libraries)
                )
                partner_forbidden_libs.value = "\n".join(
                    service._parse_json(system_policy.forbidden_libraries)
                )
                partner_max_time.value = system_policy.max_execution_time
                partner_time_label.text = f"{system_policy.max_execution_time} segundos"
                partner_max_mem.value = system_policy.max_memory_mb
                partner_mem_label.text = f"{system_policy.max_memory_mb} MB"

                # Populate defaults
                partner_screenshot_policy.value = getattr(
                    system_policy, "screenshot_policy", "REVIEW"
                )
                trusted = service._parse_json(
                    getattr(system_policy, "trusted_screenshot_domains", "[]")
                )
                partner_trusted_domains.value = "\n".join(trusted)

        partner_policy_dialog.open()

    async def open_client_policy_dialog(row):
        client_dialog_state["client_id"] = row["client_id"]
        client_dialog_state["client_name"] = row["client_name"]
        client_dialog_state["partner_id"] = row["partner_id"]
        client_dialog_title.text = f"Política del Cliente: {row['client_name']}"

        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            policy = await service.get_client_policy(row["client_id"])

            if policy:
                domains = service._parse_json(policy.allowed_domains)
                client_allow_all.value = domains == ["*"]
                client_domains_area.value = (
                    "" if domains == ["*"] else "\n".join(domains)
                )
                client_allowed_libs.value = "\n".join(
                    service._parse_json(policy.allowed_libraries)
                )
                client_forbidden_libs.value = "\n".join(
                    service._parse_json(policy.forbidden_libraries)
                )
                client_max_time.value = policy.max_execution_time
                client_time_label.text = f"{policy.max_execution_time} segundos"
                client_max_mem.value = policy.max_memory_mb
                client_mem_label.text = f"{policy.max_memory_mb} MB"

                # Populate Screenshot Policy
                client_screenshot_policy.value = getattr(
                    policy, "screenshot_policy", "REVIEW"
                )
                trusted = service._parse_json(
                    getattr(policy, "trusted_screenshot_domains", "[]")
                )
                client_trusted_domains.value = "\n".join(trusted)
            else:
                # Load effective policy (partner or system)
                effective = await service.get_effective_policy(row["client_id"])
                domains = effective.get("allowed_domains", ["*"])
                client_allow_all.value = domains == ["*"]
                client_domains_area.value = (
                    "" if domains == ["*"] else "\n".join(domains)
                )
                client_allowed_libs.value = "\n".join(
                    effective.get("allowed_libraries", [])
                )
                client_forbidden_libs.value = "\n".join(
                    effective.get("forbidden_libraries", [])
                )
                client_max_time.value = effective.get("max_execution_time", 300)
                client_time_label.text = (
                    f"{effective.get('max_execution_time', 300)} segundos"
                )
                client_max_mem.value = effective.get("max_memory_mb", 512)
                client_mem_label.text = f"{effective.get('max_memory_mb', 512)} MB"

                # Populate defaults from effective
                client_screenshot_policy.value = effective.get(
                    "screenshot_policy", "REVIEW"
                )
                trusted = effective.get("trusted_screenshot_domains", [])
                client_trusted_domains.value = "\n".join(trusted)

        client_policy_dialog.open()

    async def delete_partner_policy(row):
        if not row.get("policy_id"):
            return

        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            await service.delete_policy(row["policy_id"])

        ui.notify(t("admin.security.policy_deleted"), type="positive")
        await refresh_partners_table()

    async def delete_client_policy(row):
        if not row.get("policy_id") or row.get("policy_level") != "CLIENT":
            return

        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            await service.delete_policy(row["policy_id"])

        ui.notify(t("admin.security.policy_deleted"), type="positive")
        await refresh_clients_table()

    # === INITIAL LOAD ===
    ui.timer(0.1, refresh_system_policy, once=True)
    ui.timer(0.2, refresh_partners_table, once=True)
    ui.timer(0.3, refresh_clients_table, once=True)
