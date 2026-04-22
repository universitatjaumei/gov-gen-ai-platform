"""
Página de configuración de acciones PDF Tools y Utilidades PDF.
Permite:
1. Crear y editar acciones que unen, dividen u optimizan PDFs (Modo Acción).
2. Ejecutar herramientas PDF directamente (Modo Utilidad).
"""
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import asyncio

from nicegui import ui, events

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.atom_service import atom_service
from client_app.app.services.naming_service import naming_service
from client_app.app.services.pdf_tools_service import pdf_tools_service
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.unified_resource_card import unified_resource_card
from client_app.app.ui.components.page_header import page_header
from client_app.app.ui.components.data_source_selector import (
    render_data_source_selector,
    DataSourceSelection, DataSourceSelectorState
)
from client_app.app.ui.components.pdf_file_list import PDFFileList
from client_app.app.ui.main_layout import main_layout
from client_app.app.database.models import AtomRegistry
from automatia_shared.enums import StepType


# ============================================================================
# STATE CLASSES
# ============================================================================

class LibraryState:
    """Estado de la vista de biblioteca (listado de átomos)."""
    def __init__(self):
        self.current_mode = 'library'  # 'library', 'design', 'utility'
        self.selected_atom_id: Optional[int] = None
        self.saved_atoms: List[AtomRegistry] = []
        self.search_query = ""


class DesignState:
    """Estado del wizard de diseño (Configuración de Átomo)."""
    def __init__(self):
        # Metadata del átomo
        self.atom_name = ""
        self.atom_id: Optional[int] = None
        
        # Wizard state
        self.current_step = 0  # 0: Origen, 1: Operación, 2: Resultado
        
        # Paso 1: Origen
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()
        self.files_to_process: List[str] = []
        
        # Paso 2: Operación
        self.operation = 'merge'  # 'merge', 'split', 'optimize'
        self.optimize = True
        self.split_mode = 'ranges'  # 'ranges', 'pages', 'all'
        self.ranges: List[Dict[str, int]] = []  # [{'start': 1, 'end': 5}, ...]
        self.pages: List[int] = []  # [1, 3, 5, ...]
        self.optimization_level = 3  # 1-4
        self.output_name = "merged.pdf"
        
        # UI containers
        self.step_container = None
        self.operation_config_container = None
    
    def reset(self):
        """Resetea el estado para nuevo diseño."""
        self.__init__()
    
    def to_config(self) -> Dict[str, Any]:
        """Convierte el estado a configuración de acción."""
        config = {
            'operation': self.operation,
            'optimize': self.optimize,
        }
        
        if self.operation == 'merge':
            config['output_name'] = self.output_name
        elif self.operation == 'split':
            config['split_mode'] = self.split_mode
            if self.split_mode == 'ranges':
                config['ranges'] = self.ranges
            elif self.split_mode == 'pages':
                config['pages'] = self.pages
        elif self.operation == 'optimize':
            config['optimization_level'] = self.optimization_level
        
        return config


class UtilityState:
    """Estado del modo utilidad (Ejecución directa)."""
    def __init__(self):
        # Operación seleccionada: 'merge', 'split', 'optimize'
        self.operation: str = 'merge'

        # Archivos cargados
        self.files: List[Dict] = []

        # Configuración de unión
        self.merge_optimize: bool = True
        self.merge_output_name: str = 'documento_unido.pdf'

        # Configuración de división
        self.split_mode: str = 'custom'  # 'custom', 'fixed'
        self.split_custom_input: str = '1-1' # "1-3, 7, 8-10"
        self.split_fixed_size: int = 1
        self.split_optimize: bool = True
        self.selected_file_index: int = 0  # Para dividir solo se usa 1 archivo

        # Configuración de optimización
        self.optimize_level: int = 3

        # Estado de procesamiento
        self.is_processing: bool = False
        self.results: Optional[Dict] = None


# ============================================================================
# MAIN PAGE FUNCTION
# ============================================================================

async def pdf_tools_atom_page_content(atom_id: Optional[int] = None, mode: str = 'atom', initial_mode: Optional[str] = None):
    
    # Estados
    t = state.i18n.t
    library_state = LibraryState()
    design_state = DesignState()
    utility_state = UtilityState()
    
    # Contenedor principal
    main_container = ui.column().classes('w-full')

    # --- INITIAL LAYOUT SETUP ---
    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        library_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.PDF_TOOLS, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif mode == 'utility' or initial_mode == 'execution':
        library_state.current_mode = 'utility'
        layout_manager.exit_focus_mode()
    elif atom_id:
        library_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.PDF_TOOLS, atom_id=atom_id)
    elif mode == 'atom' and getattr(ui.context.client.page, 'path', '').endswith('/new'):
        library_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.PDF_TOOLS)
    else:
        library_state.current_mode = 'library'
        layout_manager.exit_focus_mode()
    
    # Referencia al componente de lista de archivos (para modo utilidad)
    file_list_component: Optional[PDFFileList] = None

    # --- FUNCIONES COMUNES ---

    def go_to_library():
        """Vuelve a la vista de biblioteca, menú principal o flujo."""
        from client_app.app.core.state import app_state

        # 1. Volver al flujo si estamos editando un paso
        flow_id = None
        if app_state.flow_context and app_state.flow_context.get('mode') == 'contextual':
            flow_id = app_state.flow_context.get('flow_id')
        elif app_state.editing_flow and app_state.flow_id:
            flow_id = app_state.flow_id

        if flow_id:
            layout_manager.exit_design_mode_to_flow()
            app_state.clear_flow_context()
            app_state.clear_atom_editing_context()
            ui.navigate.to(f'/flows/{flow_id}')
            return

        # 2. Volver al menú principal si estamos en modo utilidad
        if mode == 'utility' or library_state.current_mode == 'utility':
            ui.navigate.to('/')
            return

        # 3. Volver a la biblioteca de acciones
        library_state.current_mode = 'library'
        design_state.reset()
        render_page()

    # --- FUNCIONES MODO LIBRARY/DESIGN (ATOM) ---

    async def load_saved_atoms():
        """Carga átomos guardados de tipo PDF_TOOLS."""
        library_state.saved_atoms = await atom_service.list_atoms(
            atom_type=StepType.PDF_TOOLS,
            search=library_state.search_query if library_state.search_query else None
        )

    def start_new_design():
        """Inicia nuevo diseño de átomo."""
        library_state.current_mode = 'design'
        design_state.reset()
        design_state.atom_name = naming_service.generate_provisional_name(StepType.PDF_TOOLS)
        layout_manager.enter_design_mode(
            atom_id=None,
            atom_type=StepType.PDF_TOOLS
        )
        render_page()
    
    def edit_atom(atom: AtomRegistry):
        """Edita un átomo existente."""
        library_state.current_mode = 'design'
        library_state.selected_atom_id = atom.id
        design_state.atom_id = atom.id
        design_state.atom_name = atom.name
        
        if atom.config:
            design_state.operation = atom.config.get('operation', 'merge')
            design_state.optimize = atom.config.get('optimize', True)
            design_state.split_mode = atom.config.get('split_mode', 'ranges')
            design_state.ranges = atom.config.get('ranges', [])
            design_state.pages = atom.config.get('pages', [])
            design_state.optimization_level = atom.config.get('optimization_level', 3)
            design_state.output_name = atom.config.get('output_name', 'merged.pdf')
        
        layout_manager.enter_design_mode(
            atom_id=atom.id,
            atom_type=StepType.PDF_TOOLS
        )
        render_page()

    async def delete_atom(atom: AtomRegistry):
        """Elimina un átomo."""
        await atom_service.delete_atom(atom.id)
        ui.notify(t('atoms.deleted', 'Acción eliminada'), type='positive')
        render_page()

    # --- LÓGICA WIZARD DISEÑO ---
    
    def render_current_step_design_refresh():
        if design_state.step_container:
            design_state.step_container.clear()
            with design_state.step_container:
                render_current_step_design()
    
    def update_range_design(index: int, field: str, value: int):
        design_state.ranges[index][field] = value

    def add_range_design():
        design_state.ranges.append({'start': 1, 'end': 1})
        render_current_step_design_refresh()
    
    def remove_range_design(index: int):
        design_state.ranges.pop(index)
        render_current_step_design_refresh()

    def render_ranges_config_design():
        ui.label(t('pdf_tools.define_ranges_title')).classes('text-sm text-slate-600 mb-2')
        for i, rng in enumerate(design_state.ranges):
            with ui.row().classes('w-full items-center gap-2 mb-2'):
                ui.number(label=t('pdf_tools.range_from'), value=rng['start'], min=1,
                    on_change=lambda e, idx=i: update_range_design(idx, 'start', int(e.value))).props('outlined dense').classes('w-24')
                ui.number(label=t('pdf_tools.range_to'), value=rng['end'], min=1,
                    on_change=lambda e, idx=i: update_range_design(idx, 'end', int(e.value))).props('outlined dense').classes('w-24')
                ui.button(icon='delete', on_click=lambda idx=i: remove_range_design(idx)).props('flat dense color=negative')
        ui.button(t('pdf_tools.add_range'), icon='add', on_click=add_range_design).props('outline').classes('mt-2')

    def render_operation_config_design():
        # Lógica simplificada de renderizado de configuración para diseño
        # (Similar al código original de DesignState)
        if design_state.operation == 'merge':
             with ui.card().classes('w-full p-4 bg-slate-50'):
                ui.input(label=t('pdf_tools.output_name'), placeholder='merged.pdf', value=design_state.output_name,
                    on_change=lambda e: setattr(design_state, 'output_name', e.value)).props('outlined dense').classes('w-full mb-3')
                ui.switch(t('pdf_tools.merge_optimize_hint'), value=design_state.optimize,
                    on_change=lambda e: setattr(design_state, 'optimize', e.value)).classes('mb-2')

        elif design_state.operation == 'split':
            with ui.card().classes('w-full p-4 bg-slate-50'):
                 ui.select(label=t('pdf_tools.split_mode'), 
                    options={'ranges': t('pdf_tools.split_ranges_desc'), 'pages': t('pdf_tools.split_pages_desc'), 'all': t('pdf_tools.split_all_desc')},
                    value=design_state.split_mode,
                    on_change=lambda e: setattr(design_state, 'split_mode', e.value) or render_operation_config_design_refresh()
                 ).props('outlined dense').classes('w-full mb-3')
                 
                 # Render dynamic split config
                 if design_state.split_mode == 'ranges':
                     render_ranges_config_design()
                 elif design_state.split_mode == 'pages':
                     ui.input(label=t('pdf_tools.pages_label'), placeholder='1, 3, 5', 
                        value=', '.join(map(str, design_state.pages)),
                        on_change=lambda e: setattr(design_state, 'pages', [int(p) for p in e.value.split(',') if p.strip().isdigit()])
                     ).props('outlined dense').classes('w-full')

                 ui.switch(t('pdf_tools.split_optimize_hint'), value=design_state.optimize,
                    on_change=lambda e: setattr(design_state, 'optimize', e.value)).classes('mt-3')

        elif design_state.operation == 'optimize':
            with ui.card().classes('w-full p-4 bg-slate-50'):
                 ui.select(label=t('pdf_tools.optimize_level'),
                    options={1: 'Nivel 1', 2: 'Nivel 2', 3: 'Nivel 3', 4: 'Nivel 4'},
                    value=design_state.optimization_level,
                    on_change=lambda e: setattr(design_state, 'optimization_level', e.value)
                 ).props('outlined dense').classes('w-full')

    def render_operation_config_design_refresh():
        if design_state.operation_config_container:
            design_state.operation_config_container.clear()
            with design_state.operation_config_container:
                render_operation_config_design()

    def render_current_step_design():
        if design_state.current_step == 0:
             # Origen
             with ui.card().classes('w-full p-6'):
                ui.label(t('pdf_tools.select_source_title')).classes('text-lg font-semibold text-primary mb-2')
                
                async def handle_source_selection(selection: DataSourceSelection):
                    design_state.data_source = selection
                    if selection.source_type == 'manual':
                        if selection.file_content and selection.file_name:
                            # Creamos un temp file o solo mostramos el nombre
                            import tempfile
                            import os
                            # Por ahora solo guardamos el nombre para feedback visual
                            design_state.files_to_process = [selection.file_name]
                    render_current_step_design_wrapper.refresh()

                def extract_files_from_source() -> List[str]:
                    files = []
                    if design_state.data_source:
                        if design_state.data_source.source_type == 'manual':
                            files = design_state.files_to_process
                        elif design_state.data_source.source_type in ['flow_step', 'catalog']:
                            selector_state = design_state.data_source_selector_state
                            if selector_state.preview_data:
                                if 'path' in getattr(selector_state.preview_data, 'columns', []):
                                    for row in getattr(selector_state.preview_data, 'rows', []):
                                        file_path = row.get('path', '')
                                        if file_path and file_path.lower().endswith('.pdf'):
                                            files.append(file_path)
                    return files

                render_data_source_selector(
                    consumer_type=StepType.PDF_TOOLS, 
                    on_source_selected=handle_source_selection, 
                    flow_context=state.flow_context,
                    initial_selection=design_state.data_source,
                    selector_state_override=design_state.data_source_selector_state,
                    upload_formats_override=['pdf']
                )

                # Mostrar archivos seleccionados
                preview_files = extract_files_from_source()
                if preview_files:
                    with ui.card().classes('w-full p-3 bg-green-50 border border-green-200 mt-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('check_circle', color='green')
                            source_label = "del paso anterior" if design_state.data_source and design_state.data_source.source_type == 'flow_step' else ""
                            ui.label(f'{len(preview_files)} archivo(s) PDF {source_label} detectados').classes('font-medium text-green-800')

        
        elif design_state.current_step == 1:
             # Operación
             with ui.card().classes('w-full p-6'):
                ui.label(t('pdf_tools.config_operation_title')).classes('text-lg font-semibold text-primary mb-2')
                with ui.row().classes('w-full gap-2 mb-6'):
                    for op in ['merge', 'split', 'optimize']:
                        ui.button(op, on_click=lambda o=op: setattr(design_state, 'operation', o) or render_operation_config_design_refresh()).props('outline' if design_state.operation != op else 'unelevated color=primary')
                design_state.operation_config_container = ui.column().classes('w-full')
                with design_state.operation_config_container:
                    render_operation_config_design()
        
        elif design_state.current_step == 2:
             # Resultado
             with ui.card().classes('w-full p-6'):
                ui.label(t('pdf_tools.review_config_title')).classes('text-lg font-semibold text-primary mb-2')
                ui.input(label=t('pdf_tools.atom_name_label'), value=design_state.atom_name, on_change=lambda e: setattr(design_state, 'atom_name', e.value)).props('outlined').classes('w-full mt-4')

    async def save_atom_design():
        if not design_state.atom_name.strip():
            ui.notify(t('atoms.name_required'), type='warning')
            return
        config = design_state.to_config()
        # Define schema for Flow Editor visibility
        schema = {
            "type": "object",
            "properties": {
                "operation": { "type": "string", "title": "Operación", "enum": ["merge", "split", "optimize"], "description": "Acción a realizar" },
                "output_name": { "type": "string", "title": "Nombre del archivo", "description": "Nombre del archivo resultante (con .pdf)" },
                "split_mode": { "type": "string", "title": "Modo de división", "enum": ["pages", "ranges"], "description": "Dividir por páginas o rangos" },
                "optimization_level": { "type": "integer", "title": "Nivel de optimización", "minimum": 1, "maximum": 4, "description": "1: mínimo, 4: máximo" }
            }
        }
        try:
            if design_state.atom_id:
                await atom_service.update_atom(
                    atom_id=design_state.atom_id, 
                    name=design_state.atom_name, 
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config)
                )
                ui.notify(f'Acción actualizada', type='positive')
            else:
                new_atom = await atom_service.create_atom(
                    name=design_state.atom_name, 
                    atom_type=StepType.PDF_TOOLS, 
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config)
                )
                design_state.atom_id = new_atom.id if new_atom else None
                ui.notify(f'Acción creada', type='positive')
            
            # Recargar la lista de la biblioteca local
            await load_saved_atoms()
            
            await asyncio.sleep(0.5)
            flow_id = None
            if state.flow_context and state.flow_context.get('mode') == 'contextual':
                flow_id = state.flow_context.get('flow_id')
            elif state.editing_flow and state.flow_id:
                flow_id = state.flow_id

            if flow_id:
                go_to_library()
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')

    
    # --- FUNCIONES MODO UTILITY (EJECUCIÓN DIRECTA) ---

    @ui.refreshable
    def render_utility_content():
        # Referencia al componente de lista de archivos
        nonlocal file_list_component
        
        # Timer compartido para debounce de refresh
        refresh_timer = None

        async def handle_upload_utility(e):
            nonlocal refresh_timer
            try:
                # En esta versión de NiceGUI, el evento tiene un atributo 'file' en lugar de 'name' y 'content'
                file_obj = e.file
                file_name = file_obj.name
                
                input_path = pdf_tools_service.INPUT_DIR / file_name
                # file_obj.read() es una coroutine, necesita await
                content = await file_obj.read()
                with open(input_path, 'wb') as f:
                    f.write(content)
                
                file_info = pdf_tools_service.get_file_info(str(input_path))
                if file_info:
                    utility_state.files.append(file_info)
                    
                    # Debounce: cancelar timer anterior si existe
                    if refresh_timer is not None:
                        refresh_timer.cancel()
                    
                    # Crear nuevo timer que se ejecutará solo si no llegan más archivos en 0.3s
                    refresh_timer = ui.timer(0.3, lambda: (render_files_area.refresh(), render_config_area.refresh()), once=True)
                    ui.notify(f'Archivo cargado: {file_name}', type='positive')
                else:
                    ui.notify(f'Error: {file_name} no es válido', type='negative')
            except Exception as ex:
                ui.notify(f'Error carga: {ex}', type='negative')
                print(f"DEBUG Upload error: {ex}")
                import traceback
                traceback.print_exc()

        async def load_from_input_folder_utility():
            files = pdf_tools_service.list_input_files()
            if files:
                utility_state.files = files
                render_files_area.refresh()
                render_config_area.refresh()
                ui.notify(f'{len(files)} cargados', type='positive')
            else:
                ui.notify('Carpeta vacía', type='info')

        def on_files_order_change_utility(files):
            utility_state.files = files

        def on_operation_change_utility(e):
            utility_state.operation = e.value
            utility_state.results = None
            render_files_area.refresh()
            render_config_area.refresh()

        def clear_all_files_utility():
            utility_state.files = []
            render_results_area.refresh()
            render_files_area.refresh()
            ui.notify(t('pdf_tools.files_cleared', 'Lista de archivos limpia'), type='info')

        def on_file_removed_utility(idx):
            # NO llamar a pop aquí, PDFFileList ya lo hace internamente
            render_files_area.refresh()
            # Si era el último, refrescar resultados por si acaso
            if not utility_state.files:
                render_results_area.refresh()

        # Operaciones de UI para rangos (Utility)
        def add_range_utility():
            utility_state.split_ranges.append((1, 1))
            render_config_area.refresh()
        
        def remove_range_utility(idx):
             if idx < len(utility_state.split_ranges):
                 utility_state.split_ranges.pop(idx)
                 render_config_area.refresh()

        def update_range_utility(idx, start, end):
             if idx < len(utility_state.split_ranges):
                 utility_state.split_ranges[idx] = (start, end)

        # Process logic
        async def process_utility():
            if not utility_state.files:
                ui.notify(t('pdf_tools.no_files'), type='warning')
                return
            
            utility_state.is_processing = True
            utility_state.results = None
            render_config_area.refresh()
            
            try:
                result = {'success': False}
                paths = [f['path'] for f in utility_state.files]

                if utility_state.operation == 'merge':
                    result = await pdf_tools_service.merge(
                        files=paths,
                        output_name=utility_state.merge_output_name,
                        optimize=utility_state.merge_optimize
                    )
                elif utility_state.operation == 'split':
                     file_path = utility_state.files[utility_state.selected_file_index]['path']
                     total_pages = utility_state.files[utility_state.selected_file_index].get('pages', 1)
                     
                     ranges_to_process = []
                     if utility_state.split_mode == 'custom':
                         # Parsear "1-3, 7, 10-12"
                         parts = [p.strip() for p in utility_state.split_custom_input.split(',') if p.strip()]
                         for part in parts:
                             if '-' in part:
                                 try:
                                     s_str, e_str = part.split('-', 1)
                                     s, e = int(s_str), int(e_str)
                                     ranges_to_process.append((s, e))
                                 except ValueError:
                                     continue
                             elif part.isdigit():
                                 p = int(part)
                                 ranges_to_process.append((p, p))
                         
                         if not ranges_to_process:
                             ui.notify('Formato de rangos no válido. Ej: 1-3, 7', type='warning')
                             return
                             
                         result = await pdf_tools_service.split(file_path, 'ranges', ranges=ranges_to_process, optimize=utility_state.split_optimize)
                         
                     elif utility_state.split_mode == 'fixed':
                         # Generar rangos fijos: Cada N páginas
                         chunk = utility_state.split_fixed_size
                         if chunk < 1: chunk = 1
                         
                         fixed_ranges = []
                         for start in range(1, total_pages + 1, chunk):
                             end = min(start + chunk - 1, total_pages)
                             fixed_ranges.append((start, end))
                             
                         result = await pdf_tools_service.split(file_path, 'ranges', ranges=fixed_ranges, optimize=utility_state.split_optimize)
                elif utility_state.operation == 'optimize':
                    result = await pdf_tools_service.optimize(files=paths, level=utility_state.optimize_level)

                utility_state.results = result
                render_results_area.refresh()
                if result.get('success'):
                    ui.notify('Proceso completado', type='positive')
                else:
                    ui.notify(f"Error: {result.get('error')}", type='negative')
            
            except Exception as e:
                ui.notify(f"Excepción: {e}", type='negative')
            finally:
                utility_state.is_processing = False
                render_config_area.refresh()

        @ui.refreshable
        def render_files_area():
            nonlocal file_list_component
            with ui.column().classes('w-full gap-4'):
                with ui.card().classes('w-full p-5'):
                     with ui.row().classes('w-full justify-between items-center mb-3'):
                         ui.label(t('pdf_tools.files', 'Archivos')).classes('text-base font-bold')
                         if utility_state.files:
                             ui.button(t('pdf_tools.clear_all', 'Borrar todo'), icon='delete_sweep', on_click=clear_all_files_utility).props('flat dense color=negative').classes('text-xs')
                     
                     ui.upload(label=t('pdf_tools.upload_hint'), multiple=True, auto_upload=True, on_upload=handle_upload_utility).props('accept=.pdf flat bordered').classes('w-full')
                     
                     # Carpeta de entrada comprimida
                     with ui.expansion(t('pdf_tools.input_folder', 'Carpeta de entrada'), icon='folder').classes('w-full text-xs bg-slate-50 rounded mt-2').props('dense'):
                         with ui.row().classes('w-full items-center gap-2 p-2'):
                             with ui.column().classes('flex-grow min-w-0'):
                                 ui.label(pdf_tools_service.get_input_dir_path()).classes('text-[10px] text-slate-500 truncate')
                             ui.button(icon='refresh', on_click=load_from_input_folder_utility).props('flat dense round')
                             ui.button(icon='folder_open', on_click=lambda: pdf_tools_service.open_folder(pdf_tools_service.get_input_dir_path())).props('flat dense round')

                     # Lista de archivos
                     show_arrows = (utility_state.operation == 'merge')
                     if show_arrows:
                         ui.label(t('pdf_tools.reorder_hint')).classes('text-xs text-slate-400 mb-2')
                     
                     # Recrear el componente con el estado actual
                     file_list_component = PDFFileList(
                         files=utility_state.files,
                         on_order_change=on_files_order_change_utility,
                         on_remove=on_file_removed_utility,
                         show_reorder=show_arrows
                     )
                     file_list_component.render()

        @ui.refreshable
        def render_config_area():
            with ui.column().classes('w-full gap-4'):
                with ui.card().classes('w-full p-5'):
                    if utility_state.operation == 'merge':
                        ui.label(t('pdf_tools.merge_settings')).classes('font-bold mb-3')
                        ui.input(label=t('pdf_tools.output_name'), value=utility_state.merge_output_name,
                            on_change=lambda e: setattr(utility_state, 'merge_output_name', e.value)).props('outlined dense').classes('w-full mb-3')
                        ui.switch(t('pdf_tools.merge_optimize'), value=utility_state.merge_optimize,
                            on_change=lambda e: setattr(utility_state, 'merge_optimize', e.value))
                    
                    elif utility_state.operation == 'split':
                         ui.label(t('pdf_tools.split_settings')).classes('font-bold mb-3')
                         if len(utility_state.files) > 1:
                             ui.select({i: f['name'] for i, f in enumerate(utility_state.files)}, label=t('pdf_tools.select_file'),
                                value=utility_state.selected_file_index, on_change=lambda e: setattr(utility_state, 'selected_file_index', e.value)).props('outlined dense').classes('w-full')
                         
                         ui.radio({'custom': t('pdf_tools.split_custom', 'Por rangos y páginas'), 'fixed': t('pdf_tools.split_fixed', 'Por rangos fijos')},
                            value=utility_state.split_mode, on_change=lambda e: setattr(utility_state, 'split_mode', e.value) or render_config_area.refresh()).props('dense')
                         
                         if utility_state.split_mode == 'custom':
                             ui.input(label=t('pdf_tools.custom_ranges_label', 'Especificar (ej: 1-3, 7, 10-15)'), 
                                     value=utility_state.split_custom_input,
                                     on_change=lambda e: setattr(utility_state, 'split_custom_input', e.value)).props('outlined dense').classes('w-full mt-2')
                             ui.label(t('pdf_tools.custom_ranges_hint', 'Usa guiones para rangos y comas para separar archivos de salida.')).classes('text-[10px] text-slate-500 italic mt-1')
                         
                         elif utility_state.split_mode == 'fixed':
                             with ui.row().classes('items-center gap-2 mt-2'):
                                 ui.label(t('pdf_tools.fixed_size_prefix', 'Cada')).classes('text-sm')
                                 ui.number(value=utility_state.split_fixed_size, min=1, precision=0,
                                         on_change=lambda e: setattr(utility_state, 'split_fixed_size', int(e.value or 1))).props('dense outlined').classes('w-20')
                                 ui.label(t('pdf_tools.fixed_size_suffix', 'páginas')).classes('text-sm')
                         
                         elif utility_state.split_mode == 'pages':
                             ui.input(label=t('pdf_tools.pages_input', 'Páginas (ej: 1, 5)'), value=utility_state.split_pages, on_change=lambda e: setattr(utility_state, 'split_pages', e.value)).props('outlined dense').classes('w-full')

                         ui.switch(t('pdf_tools.merge_optimize', 'Optimizar archivos resultantes'), value=utility_state.split_optimize,
                            on_change=lambda e: setattr(utility_state, 'split_optimize', e.value)).classes('mt-2')

                    elif utility_state.operation == 'optimize':
                        ui.label(t('pdf_tools.optimize_settings', 'Configuración de optimización')).classes('font-bold mb-3')
                        
                        with ui.column().classes('w-full gap-2'):
                            for level in range(1, 5):
                                selected = utility_state.optimize_level == level
                                bg_color = 'bg-blue-50 border-blue-200' if selected else 'bg-slate-50 border-slate-100 shadow-sm'
                                
                                # Card compacto seleccionable
                                with ui.row().classes(f'w-full items-center gap-2 p-2 px-3 rounded-lg border transition-all cursor-pointer {bg_color}')\
                                    .on('click', lambda _, lv=level: (setattr(utility_state, 'optimize_level', lv), render_config_area.refresh())):
                                    
                                    ui.icon('radio_button_checked' if selected else 'radio_button_unchecked', color='primary' if selected else 'slate-400')\
                                        .classes('text-lg')
                                        
                                    ui.label(t(f'pdf_tools.level_{level}')).classes('font-bold text-sm flex-grow whitespace-nowrap')
                                    
                                    with ui.icon('help_outline', size='16px').classes('text-slate-400 ml-auto'):
                                        ui.tooltip(t(f'pdf_tools.lvl{level}_help')).classes('bg-slate-800 text-xs')

                # Botón Procesar
                with ui.row().classes('w-full justify-end'):
                     ui.button(t('pdf_tools.processing') if utility_state.is_processing else t('pdf_tools.process'),
                        icon='play_arrow', on_click=process_utility
                     ).props('unelevated color=primary').set_enabled(not utility_state.is_processing and len(utility_state.files) > 0)
                
                render_results_area()

        @ui.refreshable
        def render_results_area():
            if utility_state.results and utility_state.results.get('success'):
                 with ui.card().classes('w-full p-2 px-4 bg-green-50 border border-green-100 shadow-none mb-4'):
                     with ui.row().classes('w-full items-center justify-between no-wrap'):
                         with ui.column().classes('gap-0'):
                             if utility_state.operation == 'merge':
                                 count = utility_state.results.get('files_merged', 0)
                                 msg = t('pdf_tools.files_merged', 'Se han unido {count} archivos').format(count=count)
                             elif utility_state.operation == 'split':
                                 count = utility_state.results.get('files_generated', 0)
                                 msg = t('pdf_tools.files_generated', 'Se han generado {count} archivos').format(count=count)
                             elif utility_state.operation == 'optimize':
                                 original = utility_state.results.get('total_original_mb', 0)
                                 saved = utility_state.results.get('total_saved_mb', 0)
                                 final = round(original - saved, 2)
                                 pct = round((final / original * 100), 1) if original > 0 else 0
                                 msg = t('pdf_tools.optimization_result', 'El tamaño del archivo es {size} MB ({pct}%)').format(size=final, pct=pct)
                             else:
                                 msg = "Proceso completado"
                             
                             ui.label(msg).classes('text-green-800 text-xs font-medium')
                         
                         ui.button(t('pdf_tools.open_results_short', 'Abrir carpeta'), icon='folder_open',
                            on_click=lambda: pdf_tools_service.open_folder(utility_state.results.get('output_dir')))\
                            .props('flat dense size=sm color=green-7').classes('text-xs')

        # --- RENDERIZADO UI DE UTILIDAD ---
        with ui.column().classes('w-full max-w-4xl mx-auto gap-6'):
            page_header(t('pdf_tools.title'), t('pdf_tools.subtitle'))
            
            # Selector Operación
            with ui.row().classes('w-full justify-center gap-2'):
                ui.toggle(
                    {'merge': t('pdf_tools.operation_merge'), 'split': t('pdf_tools.operation_split'), 'optimize': t('pdf_tools.operation_optimize')},
                    value=utility_state.operation, on_change=on_operation_change_utility
                ).props('no-caps unelevated toggle-color=primary')

            # Grid Principal
            with ui.grid(columns=2).classes('w-full gap-6'):
                render_files_area()
                render_config_area()

    # --- RENDERIZADORES PRINCIPALES ---

    def render_library():
        """Renderiza la vista de biblioteca (Modo Átomo)."""
        resources = [
            {
                'id': atom.id,
                'name': atom.name,
                'description': atom.description or 'Sin descripción',
                'status': atom.status or 'draft',
                'source_module': 'pdf_tools',
                'created_at': atom.created_at,
                'is_favorite': False,
                '_original': atom
            }
            for atom in library_state.saved_atoms
        ]

        layout = StandardPageLayout(
            title=t('pdf_tools.title'),
            source_module='pdf_tools',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_atom(r.get('_original', r)),
            on_delete=lambda r: delete_atom(r.get('_original', r)),
            on_execute=None,
            help_description=t('pdf_tools.atom_subtitle'),
            input_contract=['data_source', 'operation'],
            output_contract=['processed_pdf']
        )
        layout.render()

    def render_design():
        """Renderiza el wizard de configuración de átomo."""
        from client_app.app.core.state import app_state
        is_flow_context = app_state.editing_flow and layout_manager.from_flow_context

        if is_flow_context:
            with ui.row().classes('w-full bg-primary text-white p-3 items-center gap-3 mb-6 rounded shadow-md'):
                ui.icon('assignment', size='md')
                ui.label(f'Configurando paso {app_state.flow_step_index + 1}: {design_state.atom_name}').classes('font-bold')
                ui.space()
                ui.button('VOLVER', icon='arrow_back', on_click=go_to_library).props('flat text-color=white')

        with ui.column().classes('w-full max-w-5xl mx-auto gap-4'):
            # Header con flecha de navegación junto al título
            if not is_flow_context:
                with ui.row().classes('w-full items-start gap-4'):
                    ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
                    page_header(design_state.atom_name or t('pdf_tools.new_atom'), t('pdf_tools.config_operation_desc'))
            else:
                page_header(design_state.atom_name or t('pdf_tools.new_atom'), t('pdf_tools.config_operation_desc'))

            design_state.step_container = ui.column().classes('w-full mt-6')
            with design_state.step_container:
                render_current_step_design()

            with ui.row().classes('w-full justify-between mt-6'):
                if design_state.current_step > 0:
                    ui.button(t('common.back'), on_click=lambda: setattr(design_state, 'current_step', design_state.current_step - 1) or render_current_step_design_refresh()).props('flat')
                else:
                    ui.element('div')
                
                if design_state.current_step < 2:
                    ui.button(t('common.next'), on_click=lambda: setattr(design_state, 'current_step', design_state.current_step + 1) or render_current_step_design_refresh()).props('unelevated color=primary')
                else:
                    ui.button(t('atoms.save_config', 'Guardar Configuración'), icon='save', on_click=save_atom_design).props('unelevated color=positive')

    def render_utility_mode():
        """Renderiza el modo de utilidad (ejecución directa)."""
        render_utility_content()

    def render_page():
        """Renderiza la página según el modo actual."""
        main_container.clear()
        with main_container:
            if library_state.current_mode == 'utility' or mode == 'utility':
                render_utility_mode()
            elif library_state.current_mode == 'design' or mode == 'atom' and not library_state.current_mode == 'library': # Design forced
                render_design()
            else:
                render_library()

    # --- INICIALIZACIÓN ---
    # Determinamos el modo inicial
    if mode == 'utility':
        library_state.current_mode = 'utility' 

    if atom_id:
        action = await atom_service.get_atom(atom_id)
        if action:
            # Pre-load for edit
            library_state.current_mode = 'design'
            design_state.atom_id = action.id
            design_state.atom_name = action.name
            if atom.config:
                design_state.operation = atom.config.get('operation', 'merge')
                # ... load other config ...
                design_state.optimize = atom.config.get('optimize', True)
    elif mode == 'atom' and getattr(ui.context.client.page, 'path', '').endswith('/new'):
        # New Action
        library_state.current_mode = 'design'
        design_state.atom_name = naming_service.generate_provisional_name(StepType.PDF_TOOLS)

    if library_state.current_mode == 'library':
        await load_saved_atoms()

    render_page()
    
# ============================================================================
# ROUTE REGISTRATION
# ============================================================================

@ui.page('/atoms/pdf-tools/new')
async def pdf_tools_new_route(initial_mode: Optional[str] = None):
    main_layout()
    await pdf_tools_atom_page_content(mode='atom', initial_mode=initial_mode)

@ui.page('/atoms/pdf-tools/{atom_id}')
async def pdf_tools_edit_route(atom_id: int, initial_mode: Optional[str] = None):
    main_layout()
    await pdf_tools_atom_page_content(atom_id=atom_id, initial_mode=initial_mode)

@ui.page('/utilities/pdf-tools')
async def pdf_tools_utility_route(initial_mode: Optional[str] = None):
    main_layout()
    await pdf_tools_atom_page_content(mode='utility', initial_mode=initial_mode)
