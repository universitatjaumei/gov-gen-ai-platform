"""
Gestión de la Biblioteca Global de Automatizaciones.

Permite a los administradores del sistema gestionar el catálogo de
templates globales y componentes predefinidos disponibles para todos
los partners y clientes de la plataforma.
"""

from nicegui import ui
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.services.library_service import LibraryService
from server.app.ui.admin_layout import AdminContext
from automatia_shared.enums import AutomationType


def admin_library_content(ctx: AdminContext):
    class State:
        items = []
        selected_item = None

        # Editor fields
        name = ""
        code = ""
        type = "CUSTOM_SCRIPT"
        is_workflow = False

    state = State()

    # --- Actions ---
    async def load_items():
        async with AsyncSession(server_engine) as session:
            service = LibraryService(session)
            # Admin sees all. We filter UI to show mostly system/global templates or all
            # For "Global Library" page, let's focus on system templates management
            # But the requirement is "Superadmin can manage any", so listing all is fine,
            # maybe with filtering tabs. For MVP, just list all system templates first.
            all_items = await service.get_visible_automations(is_superadmin=True)
            # Filter for system templates mainly, but show others if needed
            state.items = [i for i in all_items if i.is_system_template]
        list_container.refresh()

    async def select_item(item):
        state.selected_item = item
        state.name = item.name
        state.code = item.code_content
        state.type = item.type
        state.is_workflow = item.is_workflow
        detail_container.refresh()

    async def create_new():
        state.selected_item = None
        state.name = "Nuevo Template Global"
        state.code = "# System Template"
        state.type = AutomationType.CUSTOM_SCRIPT
        state.is_workflow = False
        detail_container.refresh()

    async def save_item():
        async with AsyncSession(server_engine) as session:
            service = LibraryService(session)

            data = {
                "name": state.name,
                "code_content": state.code,
                "type": state.type,
                "is_workflow": state.is_workflow,
                "is_system_template": True,  # Global template
                "signature": "SYSTEM-SIG-AUTO",  # Mock signature for system
            }

            if state.selected_item:
                data["id"] = state.selected_item.id
                # Logic to update
                await service.save_master(data)
                ui.notify("Template actualizado", type="positive")
            else:
                import uuid

                data["id"] = f"sys-{uuid.uuid4().hex[:8]}"
                await service.save_master(data)
                ui.notify("Template global creado", type="positive")

        await load_items()

    async def delete_item():
        if not state.selected_item:
            return

        async with AsyncSession(server_engine) as session:
            service = LibraryService(session)
            # Superadmin deletion
            success = await service.delete_automation(
                state.selected_item.id, "system", is_superadmin=True
            )

        if success:
            ui.notify("Eliminado (Admin Override)", type="warning")
            state.selected_item = None
            await load_items()
            detail_container.refresh()
        else:
            ui.notify("Error al eliminar", type="negative")

    # --- UI Components ---

    # 1. LIST
    @ui.refreshable
    def list_container():
        ui.label("Biblioteca Global (System Templates)").classes(
            "text-2xl font-bold mb-4"
        )
        ui.button("Nuevo Template", icon="add", on_click=create_new).classes(
            "mb-4 bg-slate-800 text-white"
        )

        if not state.items:
            ui.label("No hay templates globales.").classes("text-gray-500 italic")
            return

        with ui.column().classes("w-full gap-2"):
            for item in state.items:
                with (
                    ui.card()
                    .classes(
                        "w-full p-2 cursor-pointer hover:bg-slate-50 border-l-4 border-slate-500"
                    )
                    .on("click", lambda i=item: select_item(i))
                ):
                    ui.label(item.name).classes("font-bold")
                    with ui.row().classes("gap-2"):
                        ui.chip(item.type, color="slate").props("dense")
                        if item.is_workflow:
                            ui.chip("WORKFLOW", color="purple").props("dense")

    # 2. DETAIL
    @ui.refreshable
    def detail_container():
        ui.label("Editor Global").classes("text-xl font-bold mb-4")

        with ui.column().classes("w-full gap-4"):
            ui.input("Nombre del Template").bind_value(state, "name").classes("w-full")

            with ui.row().classes("w-full gap-4"):
                ui.select(
                    options=[t.value for t in AutomationType], label="Tipo"
                ).bind_value(state, "type").classes("w-1/2")

                ui.checkbox("Es Workflow?").bind_value(state, "is_workflow")

            ui.label("Definición (Python/JSON)").classes(
                "text-sm font-bold text-gray-600"
            )
            ui.codemirror(language="python").bind_value(state, "code").classes(
                "h-96 border shadow-inner"
            )

            with ui.row().classes("w-full justify-end gap-2"):
                if state.selected_item:
                    ui.button(
                        "Eliminar (Forzar)", color="red", on_click=delete_item
                    ).props("outline")
                ui.button("Guardar y Firmar", color="green", on_click=save_item)

    # --- LAYOUT ---
    with ui.row().classes("w-full h-full"):
        with ui.column().classes("w-1/3 h-full p-4 border-r overflow-y-auto"):
            list_container()

        with ui.column().classes("w-2/3 h-full p-4 overflow-y-auto"):
            detail_container()

    ui.timer(0.1, load_items, once=True)
