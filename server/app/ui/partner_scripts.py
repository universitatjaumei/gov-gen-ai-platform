"""
Interfaz de Soporte y Desarrollo de Scripts para Partners.

Permite a los Partners visualizar las solicitudes de escalación de sus
clientes, revisar el código original, aplicar correcciones y publicar
las versiones definitivas de los automatismos.
"""

from nicegui import ui
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.services.partner_scripts_service import PartnerScriptsService
from server.app.ui.partner_layout import PartnerContext


def partner_scripts_content(ctx: PartnerContext):
    class State:
        escalations = []
        selected_escalation = None
        new_code = ""
        reject_reason = ""
        show_reject_dialog = False

    state = State()

    # --- Actions ---
    async def load_escalations():
        async with AsyncSession(server_engine) as session:
            service = PartnerScriptsService(session, ctx.partner_id)
            state.escalations = await service.get_pending_escalations()
        list_container.refresh()

    async def select_escalation(esc):
        state.selected_escalation = esc
        state.new_code = esc.original_code
        detail_container.refresh()

    async def publish_script():
        if not state.selected_escalation:
            return

        async with AsyncSession(server_engine) as session:
            service = PartnerScriptsService(session, ctx.partner_id)
            await service.publish_script(state.selected_escalation.id, state.new_code)

        ui.notify(
            f"Script '{state.selected_escalation.script_name}' publicado correctamente",
            type="positive",
        )
        state.selected_escalation = None
        await load_escalations()
        detail_container.refresh()

    async def reject_escalation():
        if not state.selected_escalation:
            return

        async with AsyncSession(server_engine) as session:
            service = PartnerScriptsService(session, ctx.partner_id)
            await service.reject_escalation(
                state.selected_escalation.id, state.reject_reason
            )

        ui.notify("Escalacion rechazada", type="info")
        state.show_reject_dialog = False
        state.selected_escalation = None
        await load_escalations()
        detail_container.refresh()

    # --- UI Components ---

    # 1. LIST VIEW
    @ui.refreshable
    def list_container():
        with ui.row().classes("w-full items-center justify-between mb-4"):
            ui.label("Cola de soporte de scripts").classes("text-2xl font-bold")
            ui.button(icon="refresh", on_click=load_escalations).props(
                "flat round color=primary"
            )

        if not state.escalations:
            with ui.card().classes(
                "w-full p-6 bg-slate-50 border-dashed border-2 border-slate-200 items-center justify-center"
            ):
                ui.icon("assignment_turned_in", size="lg", color="slate-300")
                ui.label("No hay scripts pendientes de revisión.").classes(
                    "text-slate-400 italic mt-2"
                )
            return

        with ui.column().classes("w-full gap-2"):
            for esc in state.escalations:
                with (
                    ui.card()
                    .classes("w-full p-2 cursor-pointer hover:bg-indigo-50")
                    .on("click", lambda e=esc: select_escalation(e))
                ):
                    with ui.row().classes("items-center justify-between"):
                        with ui.column().classes("gap-0"):
                            script_name = esc.script_name or "Sin nombre"
                            ui.label(script_name).classes("font-bold")
                            ui.label(f"Cliente: {esc.client_id}").classes(
                                "text-xs text-gray-500"
                            )

                        ui.chip(esc.status, color="orange").props("dense")

    # 2. DETAIL VIEW
    @ui.refreshable
    def detail_container():
        if not state.selected_escalation:
            return

        esc = state.selected_escalation

        with ui.column().classes("w-full border-t border-slate-200 mt-2 pt-4"):
            with ui.row().classes("w-full items-center justify-between mb-4"):
                with ui.column().classes("gap-1"):
                    script_name = esc.script_name or "Sin nombre"
                    ui.label(f"Revisando: {script_name}").classes(
                        "text-xl font-bold text-slate-800"
                    )
                    with ui.row().classes("items-center gap-2"):
                        ui.badge(f"Cliente: {esc.client_id}", color="slate-500").props(
                            "outline"
                        )
                        ui.badge(esc.escalation_type, color="indigo-500").props(
                            "outline"
                        )

                    if esc.client_notes:
                        with ui.card().classes(
                            "bg-amber-50 p-3 border-l-4 border-amber-400 w-full mt-2"
                        ):
                            ui.label("Notas del cliente:").classes(
                                "text-xs font-bold text-amber-800 uppercase"
                            )
                            ui.label(esc.client_notes).classes("text-sm text-amber-900")

                with ui.row().classes("gap-3"):
                    ui.button(
                        "Rechazar",
                        color="red",
                        on_click=lambda: setattr(state, "show_reject_dialog", True),
                    ).props("flat")
                    ui.button(
                        "Publicar corrección",
                        icon="publish",
                        color="primary",
                        on_click=publish_script,
                    ).classes("px-6")

            ui.separator()

            with ui.grid().classes("w-full grid-cols-2 gap-4 h-[500px]"):
                # Original (Read-only)
                with ui.column().classes("h-full"):
                    ui.label("Original (solo lectura)").classes(
                        "font-bold text-slate-500 text-xs uppercase tracking-wider"
                    )
                    code_to_show = (
                        esc.original_code or "# No se proporcionó código original"
                    )
                    ui.codemirror(code_to_show, language="python").props(
                        "readOnly"
                    ).classes(
                        "h-full border border-slate-200 rounded-lg overflow-hidden"
                    )

                # Editor (Editable)
                with ui.column().classes("h-full"):
                    ui.label("Corrección (editar)").classes(
                        "font-bold text-primary text-xs uppercase tracking-wider"
                    )
                    ui.codemirror(
                        state.new_code,
                        language="python",
                        on_change=lambda e: setattr(state, "new_code", e.value),
                    ).classes(
                        "h-full border border-primary/30 rounded-lg overflow-hidden"
                    )

    # 3. DIALOGS
    with (
        ui.dialog().bind_visibility_from(state, "show_reject_dialog") as reject_dialog,
        ui.card().classes("w-[400px] p-6"),
    ):
        ui.label("Rechazar solicitud").classes("text-xl font-bold mb-2")
        ui.label(
            "Indica el motivo por el que no se puede procesar esta corrección:"
        ).classes("text-sm text-slate-500 mb-4")
        ui.textarea(
            label="Mensaje para el cliente",
            placeholder="Ej: No hay suficiente contexto para resolver el error...",
        ).bind_value(state, "reject_reason").classes("w-full mb-6").props("outlined")
        with ui.row().classes("justify-end w-full gap-2"):
            ui.button("Cancelar", on_click=reject_dialog.close).props(
                "flat color=slate-500"
            )
            ui.button(
                "Confirmar rechazo", color="red", on_click=reject_escalation
            ).props("unelevated")

    # --- MAIN LAYOUT ---
    with ui.row().classes("w-full h-full"):
        # Sidebar with list (30%)
        with ui.column().classes("w-1/3 h-full overflow-y-auto p-4 border-r"):
            list_container()

        # Main area (70%)
        with ui.column().classes("flex-1 h-full overflow-y-auto p-4"):
            detail_container()

    # Initial Load
    ui.timer(0.1, load_escalations, once=True)


@ui.page("/partner/scripts")
def partner_scripts_page():
    # Note: In production P27, we use from_session.
    # For now, we assume dev mode or cookie token.
    # We will simulate dev context for now based on P23B instructions.

    # We need to get the context. Since we are in an async page, we can assume
    # the middleware might have set it, or we use the dev helper.
    # For this specific page, let's look for a dev cookie or default to dev_partner
    pass
    # Actual implementation deferred to main routing or verified layout usage.
    # But wait, partner_layout handles this.

    # TODO: This wrapper is temporary until full P27 auth.
    # We try to get from header/cookie, or fallback to dev.
    pass


# We need to expose a way to mount this content.
# The actual route definition might be in main.py or a router.
# This file exports the content function.
