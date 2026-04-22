import asyncio
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from nicegui import ui
from sqlmodel import select

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.folder_watcher_service import folder_watcher_service
# Models imported via folder_watcher_service
from automatia_shared.enums import StepType
from client_app.app.ui.components.page_header import page_header
from client_app.app.ui.components.form_factory import AtomColorScheme

# --- MODELS & STATE ---

class FolderWatcherPageState:
    def __init__(self):
        self.current_mode: str = 'library' # library, design, execution
        self.watchers: List[Dict] = []
        self.is_loading: bool = False

class DesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.watch_path: str = ""
        self.file_patterns: str = "*"
        self.recursive: bool = False
        self.stabilization_seconds: float = 2.0

class ExecutionState:
    def __init__(self):
        self.config_entry: Optional[Dict] = None
        self.is_loading: bool = False

# --- PAGE IMPLEMENTATION ---

async def folder_watcher_page(mode: str = 'library', config_id: Optional[int] = None):
    page_state = FolderWatcherPageState()
    design_state = DesignState()
    exec_state = ExecutionState()
    colors = AtomColorScheme.get_colors(StepType.CONNECTION) # Folder Watcher usa CONNECTION/yellow-600
    t = state.i18n.t
    save_btn: Optional[ui.button] = None

    # --- LOGIC ---

    async def load_watchers():
        page_state.is_loading = True
        try:
            render_page.refresh()
        except:
            pass
        page_state.watchers = await folder_watcher_service.list_configs()
        page_state.is_loading = False
        try:
            render_page.refresh()
        except:
            pass



    def go_to_library():
        # Si viene desde un flujo, volver al flujo
        flow_id = None
        if state.flow_context and state.flow_context.get('mode') == 'contextual':
            flow_id = state.flow_context.get('flow_id')
        elif state.editing_flow and state.flow_id:
            flow_id = state.flow_id

        if flow_id:
            layout_manager.exit_design_mode_to_flow()
            state.clear_flow_context()
            state.clear_atom_editing_context()
            ui.navigate.to(f'/flows/{flow_id}')
            return

        layout_manager.exit_focus_mode()
        page_state.current_mode = 'library'
        render_page.refresh()

    async def load_design_data(config_id: Optional[int] = None):
        """Carga los datos para el modo diseño."""
        if config_id:
            config = await folder_watcher_service.get_config(config_id)
            if config:
                design_state.config_id = config['id']
                design_state.name = config['name']
                design_state.watch_path = config['watch_path']
                design_state.file_patterns = config['file_patterns']
                design_state.recursive = config['recursive']
                design_state.stabilization_seconds = config['stabilization_seconds']

    async def start_new_design():
        design_state.__init__()
        layout_manager.enter_design_mode(StepType.FOLDER_WATCHER)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def edit_config(config_id: int):
        await load_design_data(config_id)
        layout_manager.enter_design_mode(StepType.FOLDER_WATCHER, atom_id=config_id)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def handle_toggle(config_id: int, currently_active: bool):
        if currently_active:
            success, msg = await folder_watcher_service.stop_watcher(config_id)
        else:
            success, msg = await folder_watcher_service.start_watcher(config_id)
        
        ui.notify(msg, type='positive' if success else 'negative')
        await load_watchers()

    async def handle_save():
        # Validar consistencia final
        if not design_state.name or not design_state.watch_path:
            ui.notify(t('folder_watcher.error_required'), type='warning')
            return

        # Validar ruta
        if not os.path.isdir(design_state.watch_path):
            ui.notify(t('folder_watcher.error_path'), type='warning')
            return

        try:
            data = {
                "name": design_state.name,
                "watch_path": design_state.watch_path,
                "file_patterns": design_state.file_patterns,
                "recursive": design_state.recursive,
                "stabilization_seconds": design_state.stabilization_seconds,
            }

            if design_state.config_id:
                success = await folder_watcher_service.update_config(design_state.config_id, data)
                config_id = design_state.config_id
            else:
                config_id = await folder_watcher_service.create_config(data)
                success = True

            if success:
                # Sello Atómico
                async with state.db_session() as session:
                    from client_app.app.services.asset_finishing_service import AssetFinishingService
                    finisher = AssetFinishingService(session)
                    await finisher.seal_resource(config_id, StepType.CONNECTION)
                    await session.commit()

                ui.notify(t('folder_watcher.saved'), type='positive')
                go_to_index()
            else:
                ui.notify(t('folder_watcher.error_save'), type='negative')
        except Exception as e:
            ui.notify(f"Error: {e}", type='negative')

    def go_to_index():
        ui.navigate.to('/triggers')

    async def pick_folder():
        """Abre un selector de carpetas nativo sin bloquear el loop."""
        import tkinter as tk
        from tkinter import filedialog
        
        def _pick():
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True) # Asegurar que aparezca encima
            path = filedialog.askdirectory()
            root.destroy()
            return path

        path = await asyncio.get_event_loop().run_in_executor(None, _pick)
        if path:
            design_state.watch_path = path.replace('/', '\\')
            update_save_button()

    def check_validity():
        """Verifica si el formulario es válido para guardar."""
        is_valid = bool(design_state.name and design_state.watch_path)
        return is_valid

    # --- RENDERERS ---

    @ui.refreshable
    def render_preview():
        """Muestra una vista previa compacta de la configuración."""
        with ui.expansion(t('folder_watcher.preview'), icon='preview').classes('w-full border rounded-lg text-sm').props('header-class=text-slate-500'):
            with ui.card().classes('w-full p-4 bg-slate-50 border-none shadow-none'):
                if design_state.watch_path:
                    ui.label(t('folder_watcher.path')).classes('text-[10px] font-bold text-slate-400 uppercase')
                    ui.label(design_state.watch_path).classes('text-xs font-mono mb-2 truncate')
                    
                    ui.label(t('folder_watcher.patterns')).classes('text-[10px] font-bold text-slate-400 uppercase')
                    ui.label(design_state.file_patterns or "*").classes('text-xs mb-2')
                    

                else:
                    ui.label(t('folder_watcher.config_hint', 'Configura una ruta para ver el resumen.')).classes('text-slate-400 italic text-xs')

    @ui.refreshable
    def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library': render_library()
            elif page_state.current_mode == 'design': render_design()

    def render_library():
        with ui.row().classes('w-full justify-between items-center mb-6'):
            with ui.column():
                with ui.row().classes('items-center gap-2'):
                    ui.label(t('folder_watcher.title')).classes('text-3xl font-bold text-slate-800')
                ui.label(t('folder_watcher.subtitle')).classes('text-slate-500')
            ui.button(t('folder_watcher.new'), icon='add', on_click=start_new_design).props('unelevated color=yellow-700')

        if page_state.is_loading:
            ui.skeleton().classes('w-full h-32')
            return

        for config in page_state.watchers:
            with ui.card().classes('w-full p-0 overflow-hidden mb-4 border-l-4 border-yellow-500 shadow-sm'):
                with ui.row().classes('w-full items-center p-4 bg-white'):
                    # Status Icon
                    is_active = config['is_active']
                    status_color = 'text-green-500' if is_active else 'text-slate-200'
                    ui.icon('radio_button_checked', size='2rem').classes(status_color)
                    
                    with ui.column().classes('flex-grow ml-4'):
                        ui.label(config['name']).classes('text-lg font-bold')
                        ui.label(config['watch_path']).classes('text-xs font-mono text-slate-400')
                    
                    with ui.row().classes('items-center gap-6 mr-4'):
                        # Metrics
                        with ui.column().classes('items-center'):
                            ui.label(str(config['trigger_count'])).classes('text-xl font-bold')
                            ui.label(t('dashboard.metrics_executions', 'EJECUCIONES')).classes('text-[8px] font-bold opacity-40')
                        
                        # Toggle
                        ui.switch(value=is_active, on_change=lambda e, cid=config['id'], val=is_active: handle_toggle(cid, val)).props('color=green')

                    with ui.row().classes('gap-2 border-l pl-4'):
                        ui.button(icon='edit', on_click=lambda c=config: edit_config(c['id'])).props('flat round dense color=blue').tooltip(t('common.edit'))
                        ui.button(icon='delete', on_click=lambda c=config: delete_config_confirm(c)).props('flat round dense color=red').tooltip(t('common.delete'))

    def delete_config_confirm(config):
        with ui.dialog() as d, ui.card():
            ui.label(t('folder_watcher.delete_confirm', name=config['name'])).classes('text-lg font-bold')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel'), on_click=d.close).props('flat')
                async def do_delete():
                    await folder_watcher_service.delete_config(config['id'])
                    ui.notify(t('folder_watcher.deleted'))
                    d.close()
                    await load_watchers()
                ui.button(t('common.delete'), on_click=do_delete).props('unelevated color=red')
        d.open()

    def update_save_button():
        """Actualiza el estado del botón de guardar."""
        nonlocal save_btn
        if save_btn:
            is_valid = bool(design_state.name and design_state.watch_path)
            save_btn.set_visibility(True) # Asegurar que sea visible
            save_btn.enable() if is_valid else save_btn.disable()

    def render_design():
        nonlocal save_btn # Para acceder desde update_save_button

        with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
            page_header(
                t('folder_watcher.create_title'),
                t('folder_watcher.create_subtitle')
            )

            with ui.grid(columns=2).classes('w-full gap-4'):
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('folder_watcher.config')).classes('text-base font-bold mb-2')
                        ui.input(t('folder_watcher.name'), on_change=update_save_button).classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'name')
                        
                        # Input de ruta con botón de selector
                        with ui.input(t('folder_watcher.path'), on_change=update_save_button).classes('w-full font-mono text-sm').props('dense outlined').bind_value(design_state, 'watch_path') as path_input:
                            with path_input.add_slot('append'):
                                ui.button(icon='folder', on_click=pick_folder).props('flat round dense color=primary').tooltip(t('folder_watcher.pick_folder', 'Abrir selector'))

                        ui.input(t('folder_watcher.patterns')).classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'file_patterns')
                        ui.checkbox(t('folder_watcher.recursive')).classes('text-xs').bind_value(design_state, 'recursive')

                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('folder_watcher.advanced_config', 'Configuración Avanzada')).classes('text-base font-bold mb-2')

                        ui.number(t('folder_watcher.stabilization'), value=2.0, step=0.5).classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'stabilization_seconds').tooltip(t('folder_watcher.stabilization_hint', 'Espera tras la escritura antes de disparar el flujo'))

                    # Vista Previa dentro de Expander
                    render_preview()

                    with ui.row().classes('w-full justify-end gap-2 mt-4 items-center'):
                        ui.button(t('common.cancel'), on_click=go_to_index).props('flat color=slate text-sm')
                        
                        save_btn = ui.button(t('common.save'), icon='save', on_click=handle_save)\
                            .props('unelevated color=primary shadow text-sm')
                        
                        # Estado inicial
                        update_save_button()

    # --- INITIALIZATION ---
    await load_watchers()

    # Manejar modo inicial antes del primer renderizado
    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
        # Cargar config del flujo o del URL
        effective_config_id = flow_config_id or config_id
        if effective_config_id:
            await load_design_data(effective_config_id)
        layout_manager.enter_design_mode(StepType.FOLDER_WATCHER, from_flow=True)
    elif mode == 'design':
        page_state.current_mode = 'design'
        if config_id:
            await load_design_data(config_id)
        layout_manager.enter_design_mode(StepType.FOLDER_WATCHER, atom_id=config_id)
    else:
        layout_manager.exit_focus_mode()

    render_page()
