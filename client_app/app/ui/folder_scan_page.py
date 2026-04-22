"""
FolderScanPage - Configuración del Átomo de Escaneo de Carpeta

Página para configurar el átomo FOLDER_SCAN que realiza escaneo pasivo
de carpetas (a diferencia de FOLDER_WATCHER que monitorea en tiempo real).

Parte de la Fase 2 del Plan de Refactorización de Taxonomía.
"""
import os
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from nicegui import ui, context
from sqlmodel import select

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.file_system_service import (
    file_system_service,
    ScanResult,
    FileInfo,
)
from client_app.app.database.models import FlowRegistry
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.page_header import page_header


# --- STATE ---

class FolderScanPageState:
    def __init__(self):
        self.current_mode: str = 'library'  # library, design, test
        self.saved_configs: List[Dict[str, Any]] = []
        self.is_loading: bool = False


class DesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.scan_path: str = ""
        self.file_pattern: str = "*"
        self.recursive: bool = False
        self.max_files: int = 100
        self.include_directories: bool = False
        self.is_saving: bool = False
        self.file_extensions: List[str] = []  # Filtro de tipos de archivo


class TestState:
    def __init__(self):
        self.is_running: bool = False
        self.result: Optional[ScanResult] = None
        self.error: Optional[str] = None


# --- PAGE IMPLEMENTATION ---

async def folder_scan_page():
    """Página principal del átomo FolderScan."""
    page_state = FolderScanPageState()
    design_state = DesignState()
    test_state = TestState()
    colors = AtomColorScheme.get_colors(StepType.FOLDER_SCAN)
    t = state.i18n.t

    # --- LOGIC ---

    async def load_configs():
        """Carga las configuraciones guardadas (si las hubiera)."""
        import json
        from client_app.app.services.atom_service import atom_service
        page_state.is_loading = True
        render_page.refresh()
        atoms = await atom_service.list_atoms(atom_type=StepType.FOLDER_SCAN)
        page_state.saved_configs = [
            {
                'id': a.id, 'name': a.name, 'atom_type': a.atom_type,
                'config': json.loads(a.default_config) if a.default_config else {},
                'updated_at': a.updated_at, 'status': a.status,
                'created_at': a.created_at,
                'is_favorite': False,
                'source_module': 'folder',
            }
            for a in atoms
        ]
        page_state.is_loading = False
        render_page.refresh()

    def edit_atom(atom):
        import json
        design_state.config_id = atom.get('id') if isinstance(atom, dict) else atom.id
        design_state.name = atom.get('name') if isinstance(atom, dict) else atom.name
        
        config = atom.get('config') if isinstance(atom, dict) else {}
        if config:
            design_state.scan_path = config.get('scan_path', "")
            design_state.file_pattern = config.get('file_pattern', "*")
            design_state.recursive = config.get('recursive', False)
            design_state.max_files = config.get('max_files', 100)
            design_state.include_directories = config.get('include_directories', False)
        
        atom_id = atom.get('id') if isinstance(atom, dict) else atom.id
        layout_manager.enter_design_mode(StepType.FOLDER_SCAN, atom_id=atom_id)
        layout_manager.page_design_config = design_state.__dict__
        page_state.current_mode = 'design'
        render_page.refresh()

    async def delete_atom(atom):
        from client_app.app.services.atom_service import atom_service
        atom_id = atom.get('id') if isinstance(atom, dict) else atom.id
        await atom_service.delete_atom(atom_id)
        ui.notify(t('atoms.deleted', 'Acción eliminada'), type='positive')
        await load_configs()

    def go_to_library():
        layout_manager.page_design_config = None  # Limpiar config del drawer

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

    async def start_new_design():
        design_state.__init__()
        layout_manager.enter_design_mode(StepType.FOLDER_SCAN)
        # Conectar config de la página con el drawer
        layout_manager.page_design_config = design_state.__dict__
        page_state.current_mode = 'design'
        render_page.refresh()

    async def handle_test_scan():
        """Ejecuta un escaneo de prueba con los parámetros actuales."""
        if not design_state.scan_path:
            ui.notify("Ingresa una ruta para escanear", type='warning')
            return

        # Capturar el cliente antes del refresh para poder notificar después
        client = context.client

        test_state.is_running = True
        test_state.result = None
        test_state.error = None
        render_page.refresh()

        try:
            result = await file_system_service.scan_folder(
                path=design_state.scan_path,
                pattern=design_state.file_pattern or "*",
                recursive=design_state.recursive,
                include_directories=design_state.include_directories,
                max_files=design_state.max_files,
            )

            test_state.result = result

            if result.success:
                with client:
                    ui.notify(
                        f"Encontrados {result.total_count} archivos",
                        type='positive'
                    )
            else:
                test_state.error = result.error
                with client:
                    ui.notify(f"Error: {result.error}", type='negative')

        except Exception as e:
            test_state.error = str(e)
            with client:
                ui.notify(f"Error: {e}", type='negative')
        finally:
            test_state.is_running = False
            render_page.refresh()

    async def handle_save():
        """Guarda la configuración como átomo publicado."""
        if not design_state.name:
            ui.notify("Ingresa un nombre para la configuración", type='warning')
            return

        # Guard against double-submissions
        if design_state.is_saving:
            return

        # Capturar el cliente antes del refresh
        client = context.client

        design_state.is_saving = True
        render_page.refresh()

        try:
            # Auto-format dynamic variables
            def format_var(val):
                v = (val or "").strip()
                if not v: return ""
                if (v.startswith('{{') and v.endswith('}}')) or '\\' in v or '/' in v or ':' in v:
                    return v
                clean = v.replace('{', '').replace('}', '').strip()
                return f"{{{{{clean}}}}}" if clean else ""

            design_state.scan_path = format_var(design_state.scan_path)

            config = {
                'scan_path': design_state.scan_path,
                'file_pattern': design_state.file_pattern,
                'recursive': design_state.recursive,
                'max_files': design_state.max_files,
                'include_directories': design_state.include_directories
            }

            # Define schema for Flow Editor visibility
            schema = {
                "type": "object",
                "properties": {
                    "scan_path": { "type": "string", "title": "Ruta de escaneo", "description": "Carpeta o variable {{ruta}}" },
                    "file_pattern": { "type": "string", "title": "Patrón de archivos", "description": "Ej: *.pdf o *" },
                    "recursive": { "type": "boolean", "title": "Escaneo recursivo", "description": "Incluir subcarpetas" },
                    "max_files": { "type": "integer", "title": "Límite de archivos", "minimum": 1, "maximum": 1000 },
                    "include_directories": { "type": "boolean", "title": "Incluir carpetas", "description": "Listar también directorios" }
                }
            }
            import json
            from client_app.app.services.atom_service import atom_service
            if design_state.config_id:
                await atom_service.update_atom(
                    atom_id=design_state.config_id, 
                    name=design_state.name, 
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config),
                    status='PUBLISHED'
                )
                with client:
                    ui.notify(f'Configuración actualizada correctamente', type='positive')
            else:
                new_atom = await atom_service.create_atom(
                    name=design_state.name, 
                    atom_type=StepType.FOLDER_SCAN, 
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config),
                    status='PUBLISHED'
                )
                design_state.config_id = new_atom.id if new_atom else None
                with client:
                    ui.notify(f'Configuración guardada correctamente', type='positive')
            
            await load_configs()
            
            # Redirigir siempre a la biblioteca para acciones solo configurables
            go_to_library()

        except Exception as e:
            with client:
                ui.notify(f"Error: {e}", type='negative')
        finally:
            design_state.is_saving = False
            render_page.refresh()
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
            design_state.scan_path = path.replace('/', '\\')
            render_page.refresh()

    def format_size(size_bytes: int) -> str:
        """Formatea bytes a una cadena legible."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    # --- RENDERERS ---

    @ui.refreshable
    def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library':
                render_library()
            elif page_state.current_mode == 'design':
                render_design()

    def render_library():
        # currently no saved configs for folder scan
        resources = page_state.saved_configs
        
        layout = StandardPageLayout(
            title=t('folder_scan.title'),
            source_module='folder',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_atom(r),
            on_delete=lambda r: delete_atom(r),
            help_description=t('folder_scan.subtitle'),
            input_contract=['folder_path', 'pattern', 'recursive', 'max_files'],
            output_contract=['files_list', 'total_count', 'total_size']
        )
        layout.render()

    def render_design():
        with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
            page_header(
                t('folder_scan.designer_title'),
                t('folder_scan.designer_subtitle')
            )

            with ui.grid(columns=2).classes('w-full gap-4'):
                # Columna 1: Ubicación
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('common.configuration')).classes('text-base font-bold mb-2')
                        ui.input(t('common.atom_name'), placeholder='Ej: Escaneo de facturas').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'name')
                        
                        with ui.input(t('folder_scan.path_label'), placeholder='C:\\Users\\...').classes('w-full text-sm font-mono').props('dense outlined').bind_value(design_state, 'scan_path') as path_input:
                            with path_input.add_slot('append'):
                                ui.button(icon='folder', on_click=pick_folder).props('flat round dense color=primary').tooltip('Abrir selector')

                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('common.diagnostics')).classes('text-base font-bold mb-2')
                        ui.button(t('folder_scan.test_scan'), icon='science', on_click=handle_test_scan).props('unelevated color=emerald-600 text-sm')\
                            .bind_enabled_from(test_state, 'is_running', backward=lambda x: not x).classes('w-full')
                        
                        if test_state.result and test_state.result.success:
                            with ui.card().classes('w-full p-3 mt-3 shadow-none border bg-amber-50 border-amber-100 text-amber-900'):
                                with ui.row().classes('w-full justify-around'):
                                    with ui.column().classes('items-center'):
                                        ui.label(str(test_state.result.total_count)).classes('text-xl font-bold')
                                        ui.label(t('folder_scan.files_count')).classes('text-[10px] uppercase')
                                    with ui.column().classes('items-center'):
                                        ui.label(format_size(test_state.result.total_size_bytes)).classes('text-xl font-bold')
                                        ui.label(t('folder_scan.total_size')).classes('text-[10px] uppercase')
                                
                                ui.separator().classes('my-2')
                                with ui.scroll_area().classes('w-full h-32'):
                                    for f in test_state.result.files[:10]:
                                        ui.label(f"• {f.name}").classes('text-[10px] truncate opacity-70')

                # Columna 2: Filtros y Parámetros
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('email_scan.filters')).classes('text-base font-bold mb-2')
                        ui.input(t('folder_scan.pattern'), placeholder='*').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'file_pattern')
                        ui.number(t('folder_scan.max_files'), value=100).classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'max_files')
                        
                        ui.checkbox(t('folder_scan.recursive')).classes('text-xs').bind_value(design_state, 'recursive')
                        ui.checkbox(t('folder_scan.include_dirs')).classes('text-xs').bind_value(design_state, 'include_directories')

                    with ui.row().classes('w-full justify-end gap-2 mt-4 items-center'):
                        ui.button(t('common.cancel'), on_click=go_to_library).props('flat color=slate text-sm')
                        ui.button(t('common.validate'), icon='check', on_click=handle_save).props('unelevated color=primary shadow text-sm')\
                            .bind_enabled_from(design_state, 'is_saving', backward=lambda x: not x)

    # --- INITIALIZATION ---
    await load_configs()

    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
            if flow_config_id:
                from client_app.app.services.atom_service import atom_service
                atom = await atom_service.get_atom(flow_config_id)
                if atom:
                    design_state.config_id = atom.id
                    design_state.name = atom.name
                    if atom.config:
                        design_state.scan_path = atom.config.get('scan_path', "")
                        design_state.file_pattern = atom.config.get('file_pattern', "*")
                        design_state.recursive = atom.config.get('recursive', False)
                        design_state.max_files = atom.config.get('max_files', 100)
                        design_state.include_directories = atom.config.get('include_directories', False)
        layout_manager.enter_design_mode(StepType.FOLDER_SCAN, from_flow=True, atom_id=flow_config_id)

    render_page()

    return render_page
