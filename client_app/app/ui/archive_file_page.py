"""
ArchiveFilePage - Configuración del Átomo de Archivado de Archivos

Página para configurar el átomo ARCHIVE_FILE que mueve o copia archivos
a una ruta destino con soporte para variables.

Parte de la Fase 2 del Plan de Refactorización de Taxonomía.
"""
import os
from typing import Optional, List, Dict, Any
from nicegui import ui

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme
from client_app.app.ui.components.page_header import page_header
import asyncio


# --- STATE ---

class ArchiveFilePageState:
    def __init__(self):
        self.current_mode: str = 'library'  # library, design, test
        self.saved_configs: List[Dict[str, Any]] = []
        self.is_loading: bool = False


class DesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.source_path: str = ""  # Puede ser variable {{archivo}} de paso anterior
        self.destination_path: str = ""
        self.operation: str = "copy"  # copy, move
        self.create_dirs: bool = True
        self.overwrite: bool = False
        self.prefix: str = ""
        self.suffix: str = ""
        self.is_saving: bool = False



# --- PAGE IMPLEMENTATION ---

async def archive_file_page():
    """Página principal del átomo ArchiveFile."""
    page_state = ArchiveFilePageState()
    design_state = DesignState()
    colors = AtomColorScheme.get_colors(StepType.ARCHIVE_FILE)
    t = state.i18n.t

    # --- LOGIC ---

    async def load_configs():
        import json
        from client_app.app.services.atom_service import atom_service
        page_state.is_loading = True
        render_page.refresh()
        atoms = await atom_service.list_atoms(atom_type=StepType.ARCHIVE_FILE)
        page_state.saved_configs = [
            {
                'id': a.id, 'name': a.name, 'atom_type': a.atom_type,
                'config': json.loads(a.default_config) if a.default_config else {},
                'updated_at': a.updated_at, 'status': a.status,
                'created_at': a.created_at,
                'is_favorite': False,
                'source_module': 'archive_file',
            }
            for a in atoms
        ]
        page_state.is_loading = False
        render_page.refresh()

    def go_to_library():
        layout_manager.exit_focus_mode()
        page_state.current_mode = 'library'
        render_page.refresh()

    async def start_new_design():
        design_state.__init__()
        layout_manager.enter_design_mode(StepType.ARCHIVE_FILE)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def edit_atom(atom):
        design_state.__init__()
        design_state.config_id = atom.get('id') if isinstance(atom, dict) else atom.id
        design_state.name = atom.get('name') if isinstance(atom, dict) else atom.name
        config = atom.get('config') if isinstance(atom, dict) else {}
        if config:
            design_state.source_path = config.get('source_path', '')
            design_state.destination_path = config.get('destination_path', '')
            design_state.operation = config.get('operation', 'copy')
            design_state.create_dirs = config.get('create_dirs', True)
            design_state.overwrite = config.get('overwrite', False)
            design_state.prefix = config.get('prefix', '')
            design_state.suffix = config.get('suffix', '')

        layout_manager.enter_design_mode(StepType.ARCHIVE_FILE, atom_id=design_state.config_id)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def delete_atom(atom):
        from client_app.app.services.atom_service import atom_service
        atom_id = atom.get('id') if isinstance(atom, dict) else atom.id
        await atom_service.delete_atom(atom_id)
        ui.notify("Configuración eliminada", type='positive')
        await load_configs()

    async def handle_save():
        if not design_state.name:
            ui.notify("El nombre es obligatorio", type='warning')
            return
        if not design_state.destination_path:
            ui.notify("La ruta destino es obligatoria", type='warning')
            return
        
        if design_state.is_saving:
            return

        design_state.is_saving = True
        render_page.refresh()

        try:
            import json
            from client_app.app.services.atom_service import atom_service
            # Auto-format dynamic variables
            def format_var(val):
                v = (val or "").strip()
                if not v: return ""
                if (v.startswith('{{') and v.endswith('}}')) or '\\' in v or '/' in v or ':' in v:
                    return v
                clean = v.replace('{', '').replace('}', '').strip()
                return f"{{{{{clean}}}}}" if clean else ""

            design_state.source_path = format_var(design_state.source_path)
            design_state.prefix = format_var(design_state.prefix)
            design_state.suffix = format_var(design_state.suffix)

            config = {
                'source_path': design_state.source_path,
                'destination_path': design_state.destination_path,
                'operation': design_state.operation,
                'create_dirs': design_state.create_dirs,
                'overwrite': design_state.overwrite,
                'prefix': design_state.prefix,
                'suffix': design_state.suffix,
            }

            # Define schema for Flow Editor visibility
            schema = {
                "type": "object",
                "properties": {
                    "source_path": { "type": "string", "title": "Archivo origen", "description": "Variable {{archivo}} o ruta completa" },
                    "destination_path": { "type": "string", "title": "Carpeta destino", "description": "Ruta donde se guardará" },
                    "operation": { "type": "string", "title": "Operación", "enum": ["copy", "move"], "description": "Copiar o Mover" },
                    "prefix": { "type": "string", "title": "Prefijo", "description": "Añadir al inicio del nombre" },
                    "suffix": { "type": "string", "title": "Sufijo", "description": "Añadir al final del nombre" },
                    "create_dirs": { "type": "boolean", "title": "Crear carpetas", "description": "Si no existen" },
                    "overwrite": { "type": "boolean", "title": "Sobrescribir", "description": "Si ya existe el destino" }
                }
            }

            if design_state.config_id:
                await atom_service.update_atom(
                    atom_id=design_state.config_id,
                    name=design_state.name,
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config),
                    status='PUBLISHED'
                )
                ui.notify("Configuración actualizada", type='positive')
            else:
                new_atom = await atom_service.create_atom(
                    name=design_state.name,
                    atom_type=StepType.ARCHIVE_FILE,
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config),
                    status='PUBLISHED'
                )
                design_state.config_id = new_atom.id if new_atom else None
                # Sync contextual flow step
                if state.flow_context and state.flow_context.get('mode') == 'contextual':
                    step = state.flow_context.get('step')
                    if step and design_state.config_id:
                        step.config['config_id'] = design_state.config_id
                ui.notify("Configuración guardada", type='positive')
            
            go_to_library()
            await load_configs()
        except Exception as e:
            ui.notify(f"Error al guardar: {e}", type='negative')
        finally:
            design_state.is_saving = False
            render_page.refresh()

    # Eliminada lógica de prueba manual (no aplicable a este contexto)
 
    async def pick_folder(target_attr: str):
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
            setattr(design_state, target_attr, path.replace('/', '\\'))
            render_page.refresh()

    def format_size(size_bytes: int) -> str:
        """Formatea bytes a una cadena legible."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    # --- RENDERERS ---

    @ui.refreshable
    def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library':
                render_library()
            elif page_state.current_mode == 'design':
                render_design()

    def render_library():
        resources = page_state.saved_configs

        layout = StandardPageLayout(
            title='Gestión y archivado de archivos',
            source_module='archive_file',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_atom(r),
            on_delete=lambda r: delete_atom(r),
            on_execute=lambda r: None,
            help_description='Define reglas para mover, copiar y organizar tus archivos finales en directorios locales o de red.',
            input_contract=['source_path', 'destination_path', 'operation', 'prefix', 'suffix'],
            output_contract=['success', 'destination_path', 'file_size_bytes']
        )
        layout.render()

    def render_design():
        with ui.column().classes('w-full max-w-5xl mx-auto gap-4'):
            page_header(
                "Configuración de archivo",
                "Define origen, destino y opciones de archivado para tus flujos."
            )
 
            with ui.grid(columns=2).classes('w-full gap-4'):
                # Columna 1: Configuración de Flujo
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label('Configuración').classes('text-base font-bold mb-2')
                        ui.input('Nombre de la tarea', placeholder='Ej: Archivar reportes').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'name')
                        
                        with ui.input('Archivo origen (variable o ruta)', placeholder='{{archivos}} o C:\\...').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'source_path') as src_input:
                            with src_input.add_slot('append'):
                                ui.button(icon='folder', on_click=lambda: pick_folder('source_path')).props('flat round dense color=primary').tooltip('Abrir selector')

                        with ui.input('Carpeta destino', placeholder='C:\\Procesados\\...').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'destination_path') as dst_input:
                            with dst_input.add_slot('append'):
                                ui.button(icon='folder', on_click=lambda: pick_folder('destination_path')).props('flat round dense color=primary').tooltip('Abrir selector')

                # Columna 2: Operaciones y Resultado
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label('Operaciones y opciones').classes('text-base font-bold mb-2')
                        with ui.row().classes('w-full gap-4 items-center mb-2'):
                            ui.radio({'copy': 'Copiar', 'move': 'Mover'}, value='copy').props('inline dense overflow-hidden').bind_value(design_state, 'operation').classes('text-sm')
                        
                        ui.checkbox('Crear directorios si no existen').classes('text-xs').bind_value(design_state, 'create_dirs')
                        ui.checkbox('Sobrescribir si existe').classes('text-xs').bind_value(design_state, 'overwrite')

                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        with ui.row().classes('items-center gap-2 mb-2'):
                            ui.label('Renombrado').classes('text-base font-bold')
                            ui.icon('help_outline', size='xs').classes('text-slate-400 cursor-pointer').tooltip('Añade prefijos o sufijos automáticamente al guardar. Soportan {{variables}} como fechas o metadatos.')
                        
                        ui.input('Prefijo', placeholder='Ej: {{date}}_o_').classes('w-full text-sm mb-2').props('dense outlined').bind_value(design_state, 'prefix')
                        ui.input('Sufijo', placeholder='Ej: _PROCESADO').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'suffix')

                    with ui.row().classes('w-full justify-end gap-2 mt-4 items-center'):
                        ui.button('CANCELAR', on_click=go_to_library).props('flat color=slate text-sm')
                        ui.button('GUARDAR ACCIÓN', icon='save', on_click=handle_save).props('unelevated color=primary shadow text-sm square')\
                            .bind_enabled_from(design_state, 'is_saving', backward=lambda x: not x)

    # --- INITIALIZATION ---
    await load_configs()

    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
            if flow_config_id:
                matching = next((c for c in page_state.saved_configs if c['id'] == flow_config_id), None)
                if matching:
                    await edit_atom(matching)
        layout_manager.enter_design_mode(StepType.ARCHIVE_FILE, from_flow=True)

    render_page()

    return render_page
