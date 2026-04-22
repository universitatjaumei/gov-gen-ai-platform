from nicegui import ui
from pathlib import Path
from typing import Optional, List
from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.script_library_service import script_library_service
from client_app.app.ui.components.form_factory import AtomColorScheme, FormContext, FormFactory
from automatia_shared.enums import StepType

# Mock models for prototype
class ExtractionAtom:
    def __init__(self, id: int, name: str, doc_type: str, last_run: Optional[str] = None):
        self.id = id
        self.name = name
        self.config = {'doc_type': doc_type, 'ocr_enabled': True}
        self.step_type = StepType.EXTRACTION
        self.last_run = last_run or "Nunca"

async def extraction_page_content():
    """
    Página de extracción refactorizada con tres modos:
    - Library: Vista de biblioteca de extractores.
    - Design: Diseño/edición de extractor.
    - Execution: Ejecución de extractor.
    """
    
    # Estado de la página
    current_mode = 'library'  # 'library', 'design', 'execution'
    current_atom_id = None
    current_atom = None
    
    # --- LIBRARY MODE ---
    @ui.refreshable
    def render_extraction_library():
        """Biblioteca de extractores con identidad visual."""
        colors = AtomColorScheme.get_colors(StepType.EXTRACTION)
        
        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-6'):
                with ui.row().classes('items-center gap-2'):
                    ui.label(colors['icon']).classes('text-3xl')
                    ui.label('Extractores de Documentos').classes(f'{colors["text"]} text-2xl font-bold')
                ui.input('Buscar...', placeholder='Buscar extractor...').classes('w-64').props('outlined dense')
                ui.button('+ Crear Nuevo', icon='add', on_click=lambda: create_new_extractor()).props('color=primary')
            
            # Mock data
            extractors = [
                ExtractionAtom(1, "Extractor Facturas Endesa", "Factura", "2026-02-09"),
                ExtractionAtom(2, "Extractor DNI", "DNI", "2026-02-08"),
                ExtractionAtom(3, "Extractor Contratos", "Contrato", "Nunca")
            ]
            
            # Lista de extractores
            with ui.column().classes('w-full gap-4'):
                for extractor in extractors:
                    with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 shadow-sm hover:shadow-md transition-shadow'):
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.column().classes('flex-1'):
                                with ui.row().classes('items-center gap-2 mb-2'):
                                    ui.label(colors['icon']).classes('text-xl')
                                    ui.label(extractor.name).classes(f'{colors["text"]} font-semibold text-lg')
                                ui.label(f'Tipo: {extractor.config["doc_type"]}').classes('text-sm text-gray-600')
                                ui.label(f'Última ejecución: {extractor.last_run}').classes('text-xs text-gray-500')
                            
                            with ui.row().classes('gap-2'):
                                ui.button('▶️ Ejecutar', on_click=lambda e=extractor: execute_extractor(e.id)).props('flat dense color=green')
                                ui.button('✏️ Editar', on_click=lambda e=extractor: edit_extractor(e.id)).props('flat dense color=blue')
                                ui.button('🗑️ Borrar', on_click=lambda e=extractor: delete_with_validation(e.id)).props('flat dense color=red')
    
    # --- DESIGN MODE ---
    @ui.refreshable
    def render_extraction_designer():
        """Diseñador de extractor con FormFactory."""
        nonlocal current_atom
        
        if not current_atom:
            current_atom = ExtractionAtom(0, "Nuevo Extractor", "Factura")
        
        context = FormContext(mode='standalone')
        
        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-6'):
                ui.label('Diseño de Extractor').classes('text-2xl font-bold text-slate-800')
                with ui.row().classes('gap-2'):
                    ui.button('Cancelar', icon='close', on_click=lambda: cancel_design()).props('flat')
                    ui.button('Guardar', icon='save', on_click=lambda: save_extractor()).props('color=primary')
            
            # Formulario usando FormFactory
            FormFactory.render_extraction_form(current_atom, context)
    
    # --- EXECUTION STATE ---
    exec_state = {
        'working': False,
        'percent': 0,
        'done': False,
        'error': None,
        'results': [],
        'uploaded_files': [],
        'current_file': '',
        'progress_log': []
    }

    # --- EXECUTION MODE ---
    @ui.refreshable
    def render_extraction_executor():
        """Ejecutor minimalista de extractor."""
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            ui.label('Ejecutar Extractor').classes('text-2xl font-bold mb-6')

            if current_atom:
                with ui.card().classes('w-full p-4 mb-4'):
                    ui.label(f'Extractor: {current_atom.name}').classes('font-bold')
                    ui.label(f'Tipo de documento: {current_atom.config["doc_type"]}').classes('text-sm text-gray-600')

                # Estado de ejecución
                if exec_state['working']:
                    with ui.card().classes('w-full p-6 bg-blue-50'):
                        with ui.row().classes('items-center gap-4'):
                            ui.spinner('dots', size='lg', color='primary')
                            with ui.column().classes('flex-1'):
                                ui.label('Procesando documentos...').classes('font-semibold')
                                if exec_state['current_file']:
                                    ui.label(f'Archivo actual: {exec_state["current_file"]}').classes('text-sm text-gray-600')
                        ui.linear_progress(value=exec_state['percent'] / 100).classes('mt-4')
                        ui.label(f'{exec_state["percent"]}% completado').classes('text-xs text-gray-500 mt-1')

                        # Log de progreso
                        if exec_state['progress_log']:
                            with ui.expansion('Ver detalles', icon='list').classes('w-full mt-4'):
                                for log_entry in exec_state['progress_log'][-10:]:
                                    status_color = 'green' if log_entry.get('status') == 'OK' else 'red' if log_entry.get('status') == 'ERROR' else 'blue'
                                    ui.label(f"[{log_entry.get('status', 'INFO')}] {log_entry.get('filename', '')} - {log_entry.get('duration', '')}").classes(f'text-xs text-{status_color}-600')

                elif exec_state['done']:
                    with ui.card().classes('w-full p-6 bg-green-50'):
                        with ui.row().classes('items-center gap-4'):
                            ui.icon('check_circle', size='xl', color='green')
                            ui.label('Extracción completada con éxito').classes('font-semibold text-green-700')

                        if exec_state['results']:
                            with ui.expansion('Ver resultados', icon='table_chart').classes('w-full mt-4'):
                                for i, result in enumerate(exec_state['results'][:5]):
                                    ui.label(f'Documento {i+1}: {result.get("filename", "N/A")}').classes('font-semibold text-sm')
                                    ui.json_editor({'content': {'json': result.get('data', {})}}).classes('w-full mb-2')

                        with ui.row().classes('w-full justify-end mt-4'):
                            ui.button('Nueva extracción', icon='replay', on_click=lambda: reset_execution()).props('color=primary')

                elif exec_state['error']:
                    with ui.card().classes('w-full p-6 bg-red-50'):
                        with ui.row().classes('items-center gap-4'):
                            ui.icon('error', size='xl', color='red')
                            ui.label('Error en la extracción').classes('font-semibold text-red-700')
                        ui.label(exec_state['error']).classes('text-sm text-red-600 mt-2')
                        with ui.row().classes('w-full justify-end mt-4'):
                            ui.button('Reintentar', icon='replay', on_click=lambda: reset_execution()).props('color=red')

                else:
                    # Uploader con almacenamiento de archivos
                    def handle_upload(e):
                        for file in e.files:
                            if file.name not in [f['name'] for f in exec_state['uploaded_files']]:
                                exec_state['uploaded_files'].append({
                                    'name': file.name,
                                    'path': file.path if hasattr(file, 'path') else None,
                                    'content': file.content if hasattr(file, 'content') else None
                                })
                        render_extraction_executor.refresh()

                    with ui.card().classes('w-full p-6 border-2 border-dashed border-blue-300'):
                        ui.label('Arrastra archivos PDF aquí').classes('text-center text-gray-500 mb-4')
                        ui.upload(on_upload=handle_upload, auto_upload=True, multiple=True).props('accept=.pdf').classes('w-full')

                        if exec_state['uploaded_files']:
                            ui.separator().classes('my-4')
                            ui.label(f'{len(exec_state["uploaded_files"])} archivo(s) listos:').classes('font-semibold')
                            for f in exec_state['uploaded_files']:
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('description', color='blue')
                                    ui.label(f['name']).classes('text-sm')

                    with ui.row().classes('w-full justify-end mt-4 gap-2'):
                        ui.button('Volver', icon='arrow_back', on_click=lambda: back_to_library()).props('flat')
                        run_btn = ui.button('Ejecutar', icon='play_arrow', on_click=lambda: run_extraction()).props('color=primary size=lg')
                        run_btn.bind_enabled_from(exec_state, 'uploaded_files', backward=lambda files: len(files) > 0)
    
    # --- ACTIONS ---
    def create_new_extractor():
        nonlocal current_mode, current_atom_id, current_atom
        current_mode = 'design'
        current_atom_id = None
        current_atom = ExtractionAtom(0, "", "Factura")
        layout_manager.enter_design_mode(StepType.EXTRACTION)
        render_page.refresh()
    
    def edit_extractor(atom_id: int):
        nonlocal current_mode, current_atom_id, current_atom
        current_mode = 'design'
        current_atom_id = atom_id
        # Mock: cargar átomo
        current_atom = ExtractionAtom(atom_id, f"Extractor {atom_id}", "Factura")
        layout_manager.enter_design_mode(StepType.EXTRACTION, atom_id=atom_id)
        render_page.refresh()
    
    def execute_extractor(atom_id: int):
        nonlocal current_mode, current_atom_id, current_atom
        current_mode = 'execution'
        current_atom_id = atom_id
        current_atom = ExtractionAtom(atom_id, f"Extractor {atom_id}", "Factura")
        layout_manager.enter_execution_mode(atom_id)
        render_page.refresh()
    
    async def check_dependencies(service_id: int) -> dict:
        """
        Implementación real de validación de dependencias para extracción.
        Verifica que las conexiones requeridas existan y estén validadas.
        """
        deps = await script_library_service.get_atom_dependencies(service_id)
        return deps

    def delete_with_validation(atom_id: int):
        """Borrado con validación de dependencias."""

        async def perform_delete_check():
            ui.notify(f'Validando dependencias del extractor {atom_id}...', type='info')

            # Verificar dependencias reales
            deps = await check_dependencies(atom_id)

            if deps['count'] > 0:
                # Hay dependencias - mostrar advertencia
                flow_names = [f"'{f['name']}'" for f in deps['flows']]
                with ui.dialog() as warn_dialog, ui.card().classes('p-6'):
                    ui.label('⚠️ Dependencias encontradas').classes('text-lg font-bold mb-4 text-orange-600')
                    ui.label(f'Este extractor está siendo usado en {deps["count"]} flujo(s):').classes('mb-2')
                    for flow in deps['flows']:
                        with ui.row().classes('items-center gap-2 ml-4'):
                            ui.icon('account_tree', color='orange')
                            ui.label(f'{flow["name"]} - pasos: {", ".join(flow["step_names"])}').classes('text-sm')
                    ui.separator().classes('my-4')
                    ui.label('¿Desea eliminarlo de todas formas?').classes('text-red-600 font-semibold')
                    with ui.row().classes('gap-2 mt-4 justify-end'):
                        ui.button('Cancelar', on_click=warn_dialog.close).props('flat')
                        ui.button('Eliminar (Forzar)', on_click=lambda: force_delete(atom_id, warn_dialog)).props('color=red')
                warn_dialog.open()
            else:
                # Sin dependencias - mostrar confirmación normal
                with ui.dialog() as dialog, ui.card().classes('p-6'):
                    ui.label('¿Confirmar eliminación?').classes('text-lg font-bold mb-4')
                    ui.label(f'Se eliminará el extractor {atom_id}').classes('mb-4')
                    with ui.row().classes('gap-2 justify-end'):
                        ui.button('Cancelar', on_click=dialog.close).props('flat')
                        ui.button('Eliminar', on_click=lambda: confirm_delete(atom_id, dialog)).props('color=red')
                dialog.open()

        async def confirm_delete(atom_id: int, dialog):
            """Elimina el átomo sin forzar."""
            try:
                await script_library_service.delete_script(atom_id, force=False)
                ui.notify('Extractor eliminado exitosamente', type='positive')
            except Exception as e:
                ui.notify(f'Error al eliminar: {e}', type='negative')
            finally:
                dialog.close()
                render_page.refresh()

        async def force_delete(atom_id: int, dialog):
            """Elimina el átomo forzando (ignora dependencias)."""
            try:
                await script_library_service.delete_script(atom_id, force=True)
                ui.notify('Extractor eliminado (forzado)', type='warning')
            except Exception as e:
                ui.notify(f'Error al eliminar: {e}', type='negative')
            finally:
                dialog.close()
                render_page.refresh()

        # Ejecutar verificación async
        ui.timer(0.1, lambda: perform_delete_check(), once=True)
    
    def save_extractor():
        nonlocal current_mode
        ui.notify(f'Extractor "{current_atom.name}" guardado', type='positive')
        current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()
    
    def cancel_design():
        nonlocal current_mode
        current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()
    
    def back_to_library():
        nonlocal current_mode
        current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()
    
    def reset_execution():
        """Reinicia el estado de ejecución."""
        exec_state['working'] = False
        exec_state['percent'] = 0
        exec_state['done'] = False
        exec_state['error'] = None
        exec_state['results'] = []
        exec_state['uploaded_files'] = []
        exec_state['current_file'] = ''
        exec_state['progress_log'] = []
        render_extraction_executor.refresh()

    def run_extraction():
        """Lógica de ejecución real usando el pipeline de extracción."""

        def update_progress(event: dict):
            """Callback para actualizar progreso desde el servicio."""
            exec_state['current_file'] = event.get('filename', '')
            exec_state['percent'] = event.get('percent', exec_state['percent'])
            exec_state['progress_log'].append(event)
            render_extraction_executor.refresh()

        async def run_extraction_logic():
            # Notificar inicio
            exec_state['working'] = True
            exec_state['percent'] = 10
            render_extraction_executor.refresh()

            try:
                # Preparar lista de rutas de archivos
                file_paths = []
                for f in exec_state['uploaded_files']:
                    if f.get('path'):
                        file_paths.append(f['path'])

                if not file_paths:
                    raise ValueError("No hay archivos válidos para procesar")

                # Generar ID de ejecución basado en el átomo
                execution_id = f"exec_{current_atom_id}_{int(__import__('time').time())}"

                # Llamada al servicio real que orquesta el Sandbox y la IA
                if state.extractor:
                    result = await state.extractor.run_batch_execution(
                        execution_id=execution_id,
                        file_paths=file_paths,
                        on_progress=update_progress
                    )

                    if result.get('status') == 'success' or result.get('batch_results'):
                        exec_state['done'] = True
                        exec_state['results'] = result.get('batch_results', result.get('data', []))
                        ui.notify("Extracción completada con éxito", type='positive')
                    else:
                        exec_state['error'] = result.get('error', 'Error desconocido en la extracción')
                        ui.notify(f"Fallo en la ejecución: {exec_state['error']}", type='negative')
                else:
                    # Modo demo si no hay extractor configurado
                    ui.notify("Modo demo: Extractor no configurado", type='warning')
                    exec_state['done'] = True
                    exec_state['results'] = [
                        {'filename': f['name'], 'data': {'demo': True, 'fields_extracted': 5}}
                        for f in exec_state['uploaded_files']
                    ]

            except Exception as e:
                exec_state['error'] = str(e)
                ui.notify(f"Error crítico: {e}", type='negative')
            finally:
                exec_state['working'] = False
                render_extraction_executor.refresh()

        ui.notify('Iniciando extracción...', type='info')
        ui.timer(0.1, lambda: run_extraction_logic(), once=True)
    
    # --- MAIN RENDER ---
    @ui.refreshable
    def render_page():
        if current_mode == 'library':
            render_extraction_library()
        elif current_mode == 'design':
            render_extraction_designer()
        elif current_mode == 'execution':
            render_extraction_executor()
    
    # Initial render
    render_page()
