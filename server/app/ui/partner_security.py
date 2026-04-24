"""
Panel de políticas de seguridad para el portal de Partners.

Permite a un Partner definir sus propias restricciones de seguridad o
personalizar las de sus clientes, heredando por defecto la política del
sistema si no se especifica una propia.
"""

from nicegui import ui
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.database.models import ClientAccount
from server.app.services.security_policy_service import SecurityPolicyService
from server.app.ui.partner_layout import PartnerContext


def partner_security_content(ctx: PartnerContext):
    """
    Renderiza la interfaz de seguridad para el Partner actual.

    Args:
        ctx: Contexto del partner que realiza la gestión.
    """
    t = state.i18n.t

    # === STATE ===
    current_partner_policy = {"data": None, "using_system": True}

    # === DIALOGS ===
    partner_policy_dialog = ui.dialog()
    client_policy_dialog = ui.dialog()

    # === PARTNER POLICY DIALOG ===
    with partner_policy_dialog, ui.card().classes("w-full max-w-2xl"):
        ui.label(t("partner.security.general_policy")).classes("text-xl font-bold mb-4")
        ui.label(f"Partner: {ctx.partner_name}").classes("text-sm text-gray-500 mb-4")

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
                    partner_id=ctx.partner_id,
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
            await refresh_partner_policy()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(
                t("admin.common.cancel"), on_click=partner_policy_dialog.close
            ).props("flat")
            ui.button(
                t("admin.common.save"), icon="save", on_click=save_partner_policy
            ).props("color=primary")

    # === CLIENT POLICY DIALOG ===
    client_dialog_state = {"client_id": None, "client_name": ""}

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
                    partner_id=ctx.partner_id,
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
    ui.label(t("partner.security.title")).classes(
        "text-2xl font-bold mb-6 text-slate-800"
    )

    # 1. PARTNER'S OWN POLICY CARD
    with ui.card().classes("w-full p-4 mb-4"):
        with ui.row().classes("w-full justify-between items-center mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("shield", size="md").classes("text-indigo-600")
                ui.label(t("partner.security.general_policy")).classes(
                    "text-lg font-bold"
                )
            ui.button(
                t("admin.common.edit"),
                icon="edit",
                on_click=lambda: open_partner_policy_dialog(),
            ).props("flat color=primary")

        partner_policy_display = ui.column().classes("w-full")

        @ui.refreshable
        def render_partner_policy():
            partner_policy_display.clear()
            data = current_partner_policy["data"]
            using_system = current_partner_policy["using_system"]

            with partner_policy_display:
                if using_system:
                    with ui.row().classes("items-center gap-2 mb-4"):
                        ui.icon("info", size="sm").classes("text-blue-500")
                        ui.label(t("admin.security.using_system")).classes(
                            "text-sm text-blue-600 italic"
                        )

                if not data:
                    ui.label("Cargando...").classes("text-gray-500")
                    return

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

        render_partner_policy()

    # 2. CLIENTS POLICIES
    with ui.card().classes("w-full p-4"):
        with ui.row().classes("w-full justify-between items-center mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("people", size="md").classes("text-teal-600")
                ui.label(t("partner.security.client_policies")).classes(
                    "text-lg font-bold"
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
                    {{ props.row.policy_level === 'CLIENT' ? 'PERSONALIZADA' : props.row.policy_level === 'PARTNER' ? 'PARTNER' : 'SISTEMA' }}
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
                    <q-tooltip>Eliminar Política (usar heredada)</q-tooltip>
                </q-btn>
            </q-td>
        """,
        )

        clients_table.on("edit_client", lambda e: open_client_policy_dialog(e.args))
        clients_table.on("delete_client", lambda e: delete_client_policy(e.args))

    # === HELPER FUNCTIONS ===

    async def refresh_partner_policy():
        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            policy = await service.get_partner_policy(ctx.partner_id)

            if policy:
                current_partner_policy["data"] = service._policy_to_dict(
                    policy, "PARTNER"
                )
                current_partner_policy["using_system"] = False
            else:
                # Show system policy as reference
                system_policy = await service.get_system_policy()
                current_partner_policy["data"] = service._policy_to_dict(
                    system_policy, "SYSTEM"
                )
                current_partner_policy["using_system"] = True

        render_partner_policy.refresh()

    async def refresh_clients_table():
        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)

            # Get all clients of this partner
            stmt = select(ClientAccount).where(
                ClientAccount.partner_id == ctx.partner_id, ClientAccount.is_active
            )
            result = await session.exec(stmt)
            clients = result.all()

            rows = []
            for c in clients:
                # Get effective policy level
                client_policy = await service.get_client_policy(c.client_id)
                if client_policy:
                    policy_level = "CLIENT"
                    policy_id = client_policy.id
                else:
                    partner_policy = await service.get_partner_policy(ctx.partner_id)
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
                        "policy_level": policy_level,
                        "policy_id": policy_id,
                    }
                )

            clients_table.rows = rows
            clients_table.update()

    async def open_partner_policy_dialog():
        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            policy = await service.get_partner_policy(ctx.partner_id)

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

    async def delete_client_policy(row):
        if not row.get("policy_id") or row.get("policy_level") != "CLIENT":
            return

        async with AsyncSession(server_engine) as session:
            service = SecurityPolicyService(session)
            await service.delete_policy(row["policy_id"])

        ui.notify(t("admin.security.policy_deleted"), type="positive")
        await refresh_clients_table()

    # === INITIAL LOAD ===
    ui.timer(0.1, refresh_partner_policy, once=True)
    ui.timer(0.2, refresh_clients_table, once=True)
