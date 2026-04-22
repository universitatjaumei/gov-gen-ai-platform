"""
Gestión de la Biblioteca de Automatizaciones para Partners.

Permite a cada Partner gestionar su propio catálogo de scripts y flujos 
maestros, sirviendo como repositorio central para sus clientes asociados.
"""
from nicegui import ui
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.services.library_service import LibraryService
from server.app.ui.partner_layout import PartnerContext
from server.app.database.models import AutomationLibrary
from automatia_shared.enums import AutomationType

def partner_library_content(ctx: PartnerContext):
    
    class State:
        items = []
        selected_item = None
        
        # Editor fields
        name = ""
        code = ""
        desc = ""
        type = "CUSTOM_SCRIPT"
        
    state = State()

    # --- Actions ---
    async def load_items():
        async with AsyncSession(server_engine) as session:
            service = LibraryService(session)
            # Filter specifically for this partner (not just visible ones, but owned ones)
            # Since get_visible_automations returns everything visible, we might want to filter in UI or add method
            # For now, we use get_visible and filter in python, but better to add specific method later
            all_visible = await service.get_visible_automations(partner_id=ctx.partner_id)
            # Only show those owned by me
            state.items = [i for i in all_visible if i.partner_id == ctx.partner_id]
        list_grid.refresh()

    async def select_item(item):
        state.selected_item = item
        state.name = item.name
        state.code = item.code_content
        state.type = item.type
        detail_container.refresh()

    async def create_new_manual():
        state.selected_item = None
        state.name = "Nuevo automatismo"
        state.code = "# Escribe tu código aquí"
        state.type = AutomationType.CUSTOM_SCRIPT
        new_dialog.close()
        detail_container.refresh()

    async def handle_import(e):
        """Maneja la importación de un archivo de automatismo."""
        try:
            import json
            content = e.content.read().decode('utf-8')
            data = json.loads(content)
            
            # Autocompletar desde el JSON (asumiendo estructura de exportación)
            state.selected_item = None
            state.name = data.get('name', 'Automatismo importado')
            state.type = data.get('type', AutomationType.CUSTOM_SCRIPT)
            
            # Si es un workflow/playbook, el contenido suele estar en 'steps' o 'actions'
            if 'code_content' in data:
                state.code = data['code_content']
            elif 'steps' in data:
                state.code = json.dumps(data['steps'], indent=2)
                state.type = "WORKFLOW"
            elif 'actions' in data:
                state.code = json.dumps(data['actions'], indent=2)
                state.type = "PLAYBOOK"
            else:
                 state.code = content # Fallback al JSON completo
            
            ui.notify(f"Importado: {state.name}", type='positive')
            new_dialog.close()
            detail_container.refresh()
        except Exception as ex:
            ui.notify(f"Error al importar: {str(ex)}", type='negative')

    async def save_item():
        async with AsyncSession(server_engine) as session:
            service = LibraryService(session)
            
            data = {
                "name": state.name,
                "code_content": state.code,
                "type": state.type,
                "partner_id": ctx.partner_id,
                "is_system_template": False # Always false for partners initially
            }
            
            if state.selected_item:
                # Update logic (would need service update method, for now using save_master logic which is "create or update")
                # Wait, save_master is specific. Let's use simple DB update for now or implement 'save_automation'
                # For Phase 2 Prototype, let's treat it as create/overwrite
                pass
                # To be fully implemented. For UI structure validation:
                ui.notify("Guardado simulado (Fase 2)", type='positive')
            else:
                 ui.notify("Creación simulada (Fase 2)", type='positive')
        
        await load_items()

    async def delete_item():
        if not state.selected_item:
            return
            
        async with AsyncSession(server_engine) as session:
            service = LibraryService(session)
            success = await service.delete_automation(state.selected_item.id, ctx.partner_id)
            
        if success:
            ui.notify("Eliminado correctamente", type='positive')
            state.selected_item = None
            await load_items()
            detail_container.refresh()
        else:
            ui.notify("Error al eliminar", type='negative')

    # --- UI Components ---

    # Dialogo de Nuevo
    with ui.dialog() as new_dialog, ui.card().classes('w-96 p-6'):
        ui.label("Nuevo automatismo").classes('text-xl font-bold mb-4')
        ui.label("Seleccione cómo desea crear el nuevo componente:").classes('text-sm text-gray-600 mb-6')
        
        with ui.column().classes('w-full gap-3'):
            with ui.row().classes('w-full items-center p-3 border rounded cursor-pointer hover:bg-slate-50').on('click', create_new_manual):
                ui.icon('edit', size='sm').classes('text-indigo-600')
                with ui.column().classes('gap-0'):
                    ui.label("Creación manual").classes('font-bold text-sm')
                    ui.label("Empezar desde un documento vacío").classes('text-xs text-gray-500')
            
            ui.label("— o —").classes('text-center w-full text-xs text-gray-400')
            
            ui.label("Importar desde diseño (.json)").classes('font-bold text-sm mb-1')
            ui.upload(on_upload=handle_import, auto_upload=True, label="Subir archivo").classes('w-full').props('accept=.json,.automatia')

    # 1. LIST (GALLERY)
    @ui.refreshable
    def list_grid():
        with ui.row().classes('w-full items-center justify-between mb-6'):
            ui.label("Mis automatismos (masters)").classes('text-2xl font-bold text-slate-800')
            ui.button("Nuevo", icon="add", on_click=new_dialog.open).props('elevated color=primary')
        
        if not state.items:
            with ui.card().classes('w-full p-12 items-center justify-center bg-slate-50 border-dashed border-2'):
                ui.icon('auto_awesome', size='3em').classes('text-slate-300 mb-2')
                ui.label("No tienes automatismos creados todavía.").classes('text-slate-400 italic')
                ui.button("Crear el primero", on_click=new_dialog.open).props('flat')
            return

        with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'):
            for item in state.items:
                # Icon mapping
                icon = 'code'
                color = 'indigo'
                # Convert string type to enums if needed or use .value
                type_val = item.type if isinstance(item.type, str) else item.type.value
                
                if 'WORKFLOW' in type_val: 
                    icon = 'account_tree'; color = 'emerald'
                elif 'PLAYBOOK' in type_val:
                    icon = 'playlist_play'; color = 'orange'
                
                with ui.card().classes(f'w-full p-0 cursor-pointer hover:shadow-md transition-shadow transition-colors overflow-hidden border-l-4 border-{color}-500').on('click', lambda i=item: select_item(i)):
                    with ui.row().classes(f'w-full p-4 items-start gap-3'):
                        ui.icon(icon, size='1.5em').classes(f'text-{color}-600 bg-{color}-50 p-2 rounded')
                        with ui.column().classes('flex-1 gap-0'):
                            ui.label(item.name).classes('font-bold text-slate-800 line-clamp-1')
                            ui.label(type_val.lower().replace('_', ' ')).classes('text-[10px] uppercase font-bold text-gray-400 tracking-wider')
                        
                    with ui.row().classes('w-full px-4 py-2 bg-slate-50 justify-between items-center'):
                        ui.label(f"v{item.version}").classes('text-xs text-gray-500')
                        ui.icon('chevron_right', size='xs').classes('text-gray-400')

    # 2. DETAIL
    @ui.refreshable
    def detail_container():
        title = "Nuevo automatismo" if not state.selected_item else f"Editando: {state.name}"
        ui.label(title).classes('text-xl font-bold mb-6 text-slate-800')
        
        with ui.card().classes('w-full p-6'):
            with ui.column().classes('w-full gap-4'):
                ui.input("Nombre").bind_value(state, 'name').classes('w-full').props('outlined dense')
                
                ui.select(
                    options=[t.value for t in AutomationType] + ["WORKFLOW", "PLAYBOOK"],
                    label="Tipo de automatismo"
                ).bind_value(state, 'type').classes('w-full').props('outlined dense')

                ui.label("Código / contenido JSON").classes('text-sm font-bold text-slate-600 mt-2')
                ui.codemirror(language='python').bind_value(state, 'code').classes('h-96 border rounded w-full border-gray-200')
                
                with ui.row().classes('w-full justify-between items-center mt-4'):
                    if state.selected_item:
                        ui.button("Eliminar", color="red", on_click=delete_item).props('flat dense')
                    else:
                        ui.label() # Spacer
                    
                    with ui.row().classes('gap-2'):
                        ui.button("Cancelar", on_click=lambda: (setattr(state, 'selected_item', None), list_grid.refresh())).props('flat')
                        ui.button("Guardar cambios", icon="save", on_click=save_item).props('elevated color=green')

    # --- LAYOUT ---
    with ui.column().classes('w-full h-full'):
        if not state.selected_item:
            list_grid()
        else:
            detail_container()

    ui.timer(0.1, load_items, once=True)
