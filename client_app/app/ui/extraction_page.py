"""
Página de extracción refactorizada con arquitectura de tres modos.
Preserva toda la funcionalidad del wizard original mientras implementa
la separación Library/Design/Execution.

Backup del original: extraction_page_legacy.py
"""

from nicegui import ui, events, app
import os
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import re

from client_app.app.core.state import state
from client_app.app.ui.components.privacy_indicator import render_privacy_indicator
from client_app.app.ui.components.privacy_report import render_privacy_report
from client_app.app.ui.ui_utils import ui_emit
from client_app.app.services.asset_finishing_service import AssetFinishingService
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.form_factory import AtomColorScheme, FormContext, FormFactory
from client_app.app.ui.components.unified_resource_card import unified_resource_card
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.page_header import page_header
from client_app.app.ui.components.data_source_selector import (
    render_data_source_selector,
    DataSourceSelection,
    DataSourceSelectorState
)
from automatia_shared.enums import StepType
from client_app.app.services.extraction_service import FieldDef, validate_execution_results
from client_app.app.services.naming_service import naming_service

# Temp dir for uploads
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# PROGRESS SYSTEM - Sequential phases that never go backwards
# ============================================================================

PHASE_RANGES = {
    'preparation': (0, 10),      # Carga de archivos, inicialización
    'generation': (10, 30),      # LLM genera código
    'execution': (30, 50),       # Primera ejecución en sandbox
    'validation': (50, 60),      # Validación de resultados
    'refinement': (60, 80),      # LLM corrige código (si necesario)
    're_execution': (80, 90),    # Re-ejecución después de refinamiento
    'finalization': (90, 100)    # Listo para guardar
}

def map_progress(phase: str, internal_percent: float) -> int:
    """
    Mapea el progreso interno de una fase (0-100) al rango global asignado.

    Args:
        phase: Nombre de la fase (key en PHASE_RANGES)
        internal_percent: Progreso dentro de la fase (0-100)

    Returns:
        Progreso global mapeado al rango de la fase

    Example:
        map_progress('execution', 50) -> 40  (mitad del rango 30-50)
        map_progress('refinement', 0) -> 60  (inicio del rango 60-80)
    """
    start, end = PHASE_RANGES.get(phase, (0, 100))
    clamped = max(0, min(100, internal_percent))
    return int(start + (end - start) * (clamped / 100))


# ============================================================================
# STATE CLASSES
# ============================================================================

class ExtractionState:
    """Estado global de la página de extracción."""
    def __init__(self):
        self.current_mode = 'library'  # 'library', 'design', 'execution'
        self.selected_service_id = None  # ID del servicio seleccionado
        self.editing_service = None  # Servicio en edición
        self.deterministic_services = []  # Lista de servicios del usuario


class DesignState:
    """Estado del wizard de diseño (preserva WizardState original)."""
    def __init__(self):
        # Modo de creación
        self.creation_mode = '__NEW_DETERMINISTIC__'  # 'GENERIC_LLM' o '__NEW_DETERMINISTIC__'

        # Archivos y configuración
        self.files_to_process = []
        self.user_instructions = ""
        self.execution_id = None

        # Fuente de datos seleccionada (DataSourceSelector)
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()
        
        # Definición de campos (determinista)
        self.field_definitions = []
        self.intent = 'DEFAULT'
        self._last_script = ''

        # Opción de auto-descubrimiento via LLM
        self.auto_discover_fields = False
        
        # Configuraciones preservadas del original
        self.calibration_config = {
            'model': 'gemini-2.0-flash',
            'detect_tables': True,
            'system_prompt': ''
        }
        self.policy_config = {
            'fallback_policy': 'on_fail',
            'qa_level': 'light'
        }
        self.execution_options = {
            'fallback_mode': 'synchronous',
            'max_llm_fields': 5,
            'min_confidence': 0.6
        }
        
        # Estado del wizard
        self.phase = 'files'  # 'files', 'definition', 'run', 'results', 'summary'
        self.stepper_step = 0
        
    @property
    def mode(self):
        if self.creation_mode == 'GENERIC_LLM':
            return 'generic'
        return 'factory'  # factory/deterministic mode
    
    def ensure_context(self):
        """Asegura que exista un contexto de ejecución único."""
        if not self.execution_id:
            self.execution_id = state.extractor.path_manager.create_execution_context(task_type='PDF_EXTRACTION')
        return self.execution_id


class ExecutionState:
    """Estado de ejecución de extractor."""
    def __init__(self):
        self.service_id = None
        self.files_to_process = []
        self.execution_id = None
        self.results = {}
        self.batch_results = {}
        self.validation_report = {}
        self.privacy_stats = {}
        self.logs = []
        self.current_status = ""

        # Estado de progreso
        self.working = False
        self.percent = 0
        self.done = False
        self.error = None
        self.subphase_title = ''
        self.last_messages = []
        self.progress_phase = 'preparation'  # Fase actual para mapeo de progreso
        
        # Fuente de datos seleccionada (DataSourceSelector)
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()
        
        # Refinamiento y Auditoría
        self.refinements_count = 0
        self.refinement_feedback = ""
        self.audit_report = ""
        self.partial_results = {}
        self.is_validation_error = False
        self.validation_errors = {}


class EtaEstimator:
    """Estimador de tiempo restante (preservado del original)."""
    def __init__(self, alpha=0.3, window=10):
        self.alpha = alpha
        self.window = window
        self.last_tick = {}
        self.rates = []
        self.start_time = None
        
    def start(self, subphase, percent, _current_index=0, _total_docs=0):
        self.start_time = datetime.now()
        self.last_tick = {'sub': subphase, 'pct': percent, 'time': self.start_time}
        
    def update(self, subphase, percent, elapsed_sec):
        if percent <= 0 or percent >= 100: return 0
        if not self.start_time: return 60
        rate = elapsed_sec / percent
        self.rates.append(rate)
        if len(self.rates) > self.window: self.rates.pop(0)
        avg_rate = sum(self.rates) / len(self.rates)
        remaining = 100 - percent
        return remaining * avg_rate


# ============================================================================
# MAIN PAGE FUNCTION
# ============================================================================

async def extraction_page_content(initial_mode: str = 'library', atom_id: Optional[int] = None):
    """
    Controlador principal de la página de extracción.
    Implementa arquitectura de tres modos: Library, Design, Execution.
    """
    
    t = state.i18n.t
    
    # Estados
    page_state = ExtractionState()
    design_state = DesignState()
    exec_state = ExecutionState()
    
    # Contenedores para campos genéricos (preservado del original)
    class StateContainer:
        def __init__(self, initial): self.value = initial
    
    generic_fields = StateContainer([])
    generic_options = StateContainer({'recognize_all': False, 'top_k': 15})
    
    # ========================================================================
    # HELPERS (Preservados del original)
    # ========================================================================
    
    async def show_extraction_seal_success(metadata: Dict[str, Any], is_flow: bool, excel_path: Optional[str] = None):
        """Transition to the summary phase instead of showing a dialog."""
        print(f"[UI] show_extraction_seal_success (redirected to summary): excel_path={excel_path}")
        design_state.phase = 'summary'
        design_state.summary_metadata = metadata
        design_state.summary_excel_path = excel_path
        
        # Actualizar stepper si aplica
        layout_manager.update_step_index(4) # Nueva fase final
        render_design.refresh()
    
    async def open_file_natively(path: str):
        """Abre un archivo usando el visor nativo del sistema operativo."""
        try:
            import os
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                os.startfile(abs_path)
            else:
                ui.notify(f"Archivo no encontrado: {abs_path}", type='negative')
        except Exception as e:
            ui.notify(f"Error abriendo archivo: {str(e)}", type='negative')

    async def open_folder_natively(path_or_file: str):
        """Abre la carpeta contenedora usando el explorador nativo."""
        try:
            import os
            target = os.path.abspath(path_or_file)
            if not os.path.isdir(target):
                target = os.path.dirname(target)
            
            if os.path.exists(target):
                os.startfile(target)
            else:
                ui.notify(f"Carpeta no encontrada: {target}", type='negative')
        except Exception as e:
            ui.notify(f"Error abriendo carpeta: {str(e)}", type='negative')
    
    def show_documentation_modal(readme_path: str, script_name: str):
        """Show README.md in a modal dialog."""
        with ui.dialog() as doc_dialog, ui.card().classes('p-6 min-w-[700px] max-w-[900px]'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label(f'Documentación: {script_name}').classes('text-xl font-bold')
                ui.button(icon='close', on_click=doc_dialog.close).props('flat round dense')
            
            try:
                readme_file = Path(readme_path)
                if readme_file.exists():
                    content = readme_file.read_text(encoding='utf-8')
                    ui.markdown(content).classes('w-full max-h-[600px] overflow-y-auto prose prose-sm')
                else:
                    ui.label('Documentación no disponible').classes('text-slate-500 italic')
            except Exception as e:
                ui.label(f'Error cargando documentación: {str(e)}').classes('text-red-500 text-sm')
        
        doc_dialog.open()
    
    async def load_deterministic_services(refresh_ui: bool = True):
        """Carga servicios deterministas del usuario.

        Args:
            refresh_ui: Si True, refresca la UI después de cargar.
                       Pasar False cuando se llama durante operaciones que manejan su propia UI.
        """
        services = await state.extractor.get_all_user_configs()

        # Obtener is_favorite de ScriptLibrary para los que tienen entrada vinculada
        from client_app.app.database.models import ScriptLibrary
        from sqlmodel import select, cast, String
        favorites_map = {}
        script_lib_ids = {}  # Mapa service_id -> script_library_id
        async with state.db_session() as session:
            for s in services:
                stmt = select(ScriptLibrary).where(
                    cast(ScriptLibrary.source_automation_id, String) == str(s['service_id']),
                    ScriptLibrary.source_module == 'extraction'
                )
                result = await session.execute(stmt)
                script_lib = result.scalars().first()
                if script_lib:
                    favorites_map[s['service_id']] = script_lib.is_favorite
                    script_lib_ids[s['service_id']] = script_lib.id

        page_state.deterministic_services = [
            {
                'service_id': s['service_id'],
                'name': s['name'],
                'description': s['description'],
                'status': s.get('status', 'draft'),
                'created_at': s.get('created_at'),
                'is_favorite': favorites_map.get(s['service_id'], False),
                'script_library_id': script_lib_ids.get(s['service_id'])
            }
            for s in services
        ]
        if refresh_ui:
            render_page.refresh()
            
    # Cargar servicios existentes al iniciar
    await load_deterministic_services(refresh_ui=False)
    
    # ========================================================================
    # NAVIGATION ACTIONS
    # ========================================================================
    
    def go_to_library():
        """Vuelve a la vista de biblioteca o al flujo si está en modo contextual."""
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

        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()

    def create_new_extractor(mode='deterministic'):
        """Crea un nuevo extractor."""
        page_state.current_mode = 'design'
        design_state.creation_mode = 'GENERIC_LLM' if mode == 'generic' else '__NEW_DETERMINISTIC__'
        design_state.phase = 'files'
        design_state.files_to_process = []
        design_state.field_definitions = []
        layout_manager.update_step_index(0)
        layout_manager.enter_design_mode(StepType.EXTRACTION)
        render_page.refresh()
    
    async def edit_extractor(service_id: str):
        """Edita un extractor existente cargando su configuración o abriendo sus propiedades si ya está sellado."""
        
        # Buscamos en ScriptLibrary para obtener la información unificada
        from client_app.app.database.models import ScriptLibrary
        from sqlmodel import select, cast, String
        async with state.db_session() as session:
            stmt = select(ScriptLibrary).where(
                cast(ScriptLibrary.source_automation_id, String) == str(service_id),
                ScriptLibrary.source_module == 'extraction'
            )
            result = await session.execute(stmt)
            script_lib = result.scalars().first()
            
        if script_lib:
            # Script sellado: abrir panel de metadatos/documentación (igual que otros átomos)
            layout_manager.enter_documentation_mode(
                atom_name=script_lib.name,
                doc_path=script_lib.doc_path,
                input_contract=script_lib.ui_contract,
                output_contract=script_lib.data_contract,
                status=script_lib.status,
                description=script_lib.description,
                resource_id=script_lib.id,
                record_type='library'
            )
            ui.notify("Abriendo edición de metadatos", type='info')
            return

        # Si no está en ScriptLibrary o es draft (actualmente no hay drafts en extraction_page así), abrimos el editor
        config = await state.extractor.get_user_config(service_id)
        if not config:
            ui.notify(t('extraction.config_load_error', 'No se pudo cargar la configuración'), type='negative')
            return
            
        page_state.current_mode = 'design'
        page_state.selected_service_id = service_id
        
        # Poblar design_state desde config
        design_state.creation_mode = '__NEW_DETERMINISTIC__'
        design_state.phase = 'definition' # Ir directo a definición
        layout_manager.update_step_index(1)
        
        # Cargar campos
        schema = config.get('expected_schema', {})
        fields_raw = schema.get('fields', [])
        design_state.field_definitions = [
            FieldDef(
                name=f.get('name', ''),
                description=f.get('description', ''),
                example_value=f.get('example_value', f.get('example', '')),
                page_hint='',
                is_optional=f.get('is_optional', f.get('nullable', False))
            ) for f in fields_raw
        ]
        
        layout_manager.enter_design_mode(StepType.EXTRACTION, atom_id=service_id)
        render_page.refresh()
    
    def execute_extractor(service_id: int):
        """Ejecuta un extractor."""
        page_state.current_mode = 'execution'
        exec_state.service_id = service_id
        exec_state.files_to_process = []
        layout_manager.enter_execution_mode(service_id)
        render_page.refresh()
    
    def delete_extractor_with_validation(service_id: str):
        """Elimina un extractor con validación de dependencias."""
        with ui.dialog() as dialog, ui.card().classes('p-6'):
            ui.label('¿Confirmar eliminación?').classes('text-xl font-bold mb-4 text-red-600')
            ui.label(f'Se eliminará el extractor "{service_id}" de forma permanente. Esta acción no se puede deshacer.').classes('mb-6')
            
            with ui.row().classes('w-full justify-end gap-3'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                async def confirm_delete():
                    try:
                        from client_app.app.database.models import UserExtractionConfig, ScriptLibrary
                        from sqlmodel import delete
                        
                        async with state.db_session() as session:
                            # 1. Borrar de UserExtractionConfig
                            stmt1 = delete(UserExtractionConfig).where(UserExtractionConfig.service_id == service_id)
                            await session.execute(stmt1)
                            
                            # 2. Borrar de ScriptLibrary si existe vinculación
                            stmt2 = delete(ScriptLibrary).where(ScriptLibrary.source_automation_id == service_id)
                            await session.execute(stmt2)
                            
                            await session.commit()
                        
                        ui.notify('Extractor eliminado correctamente', type='positive')
                        dialog.close()
                        await load_deterministic_services()
                    except Exception as e:
                        ui.notify(f'Error al eliminar: {str(e)}', type='negative')
                
                ui.button('Eliminar Permanente', icon='delete_forever', on_click=confirm_delete).props('color=red unelevated')
        dialog.open()
    
    # ========================================================================
    # LIBRARY MODE
    # ========================================================================
    
    
    # ========================================================================
    # LIBRARY MODE
    # ========================================================================
    
    async def toggle_favorite(resource):
        """Toggle favorito para un extractor."""
        script_lib_id = resource.get('script_library_id')
        if not script_lib_id:
            ui.notify(t('extraction.favorite_requires_publish', 'Publica el extractor para marcarlo como favorito'), type='info')
            return
        from client_app.app.services.script_library_service import script_library_service
        await script_library_service.toggle_favorite(script_lib_id)
        await load_deterministic_services()

    @ui.refreshable
    def render_library():
        """Renderiza la vista de biblioteca de extractores con StandardPageLayout."""

        # Map resources
        resources = []
        for extractor in page_state.deterministic_services:
            resources.append({
                'id': extractor['service_id'],
                'name': extractor['name'],
                'description': extractor.get('description', 'Sin descripción'),
                'source_module': 'extraction',
                'status': extractor.get('status', 'draft'),
                'created_at': extractor.get('created_at'),
                'is_favorite': extractor.get('is_favorite', False),
                'script_library_id': extractor.get('script_library_id'),
            })

        # Logic for Creation Dialog (since we have 2 options)
        def open_creation_dialog():
            with ui.dialog() as d, ui.card():
                ui.label(t('extraction.create_dialog_title', 'Crear nuevo extractor')).classes('text-xl font-bold mb-4')
                with ui.row().classes('gap-4'):
                    with ui.column().classes('items-center gap-2 p-4 border rounded hover:bg-slate-50 cursor-pointer').on('click', lambda: (d.close(), create_new_extractor('generic'))):
                        ui.icon('chat', size='xl', color='blue')
                        ui.label(t('extraction.generic_llm', 'Genérico (LLM)')).classes('font-bold')
                        ui.label(t('extraction.generic_desc', 'Extrae datos sin esquema fijo')).classes('text-xs text-slate-500')

                    with ui.column().classes('items-center gap-2 p-4 border rounded hover:bg-slate-50 cursor-pointer').on('click', lambda: (d.close(), create_new_extractor('deterministic'))):
                        ui.icon('assignment', size='xl', color='green')
                        ui.label(t('extraction.structured', 'Estructurado')).classes('font-bold')
                        ui.label(t('extraction.structured_desc', 'Esquema fijo y validación')).classes('text-xs text-slate-500')
            d.open()

        layout = StandardPageLayout(
            title=t('extraction.title', 'Extracción inteligente de documentos'),
            source_module='extraction',
            resources=resources,
            on_create=open_creation_dialog,
            on_edit=lambda r: edit_extractor(r['id']),
            on_delete=lambda r: delete_extractor_with_validation(r['id']),
            on_execute=lambda r: execute_extractor(r['id']),
            on_favorite_toggle=toggle_favorite,
            help_description=t('extraction.subtitle', 'Programa y ejecuta automatizaciones con IA para extraer datos estructurados de documentos PDF'),
            input_contract=['files', 'field_definitions', 'system_prompt'],
            output_contract=['extracted_data', 'validation_report', 'confidence_score']
        )
        layout.render()
    
    # ========================================================================
    # DESIGN MODE (Continuará en siguiente parte...)
    # ========================================================================
    
    # --- PHASE RUNNER HELPER (Shared with Execution) ---
    @ui.refreshable
    def render_phase_runner(state_obj):
        with ui.card().classes('w-full p-6 shadow-lg border-t-4 border-blue-600'):
            p_val = getattr(state_obj, 'phase', getattr(state_obj, 'run_phase', 'PROCESSING'))
            fallback_title = 'Ejecutando lote...' if p_val.lower() == 'running' else 'Procesando...'
            title = t(f'extraction.phase_{p_val.lower()}', fallback_title) if p_val != 'PROCESSING' else t('extraction.extraction_title', 'Extracción')
            ui.label(title).classes('text-2xl font-bold text-slate-800 mb-4')
            sub = state_obj.subphase_title or t('extraction.initializing', 'Iniciando...')
            with ui.column().classes('w-full items-center justify-center py-4 bg-slate-50 rounded-lg mb-4'):
                if state_obj.working and not state_obj.done:
                    ui.spinner(size='lg', color='blue-600', thickness=2)
                ui.label(sub).classes('text-lg text-blue-800 font-semibold mt-4 text-center')
            percent = state_obj.percent
            ui.linear_progress(value=percent/100, show_value=False).classes('w-full h-3 rounded-full').props('color=blue-600 stripe')
            ui.label(f"{percent}%").classes('text-right text-xs font-bold text-blue-600 mt-1 w-full')
            if state_obj.working and not state_obj.done:
                 with ui.row().classes('w-full justify-center mt-4'):
                    ui.label(t('extraction.long_process_warning', 'Este proceso puede tardar varios minutos. Por favor, permanezca en esta pantalla sin cerrarla ni abandonarla.')).classes('text-sm text-slate-500 text-center max-w-md mb-2')
                    ui.button(t('common.cancel'), on_click=lambda: state.extractor.request_cancel_current_run()).props('color=red-100 text-color=red-700 flat dense rounded').classes('px-4 py-1 text-sm font-bold uppercase tracking-wider w-full')
            if state_obj.error:
                ui.label(f"Error: {state_obj.error}").classes('text-red-600 text-sm mt-2 font-bold')

    def update_progress(ev, state_obj):
        if ev is None:
            return  # Ignorar pulsos vacíos para evitar AttributeError
        if isinstance(ev, str): ev = {'message': ev}
        msg = ev.get('message', '')
        p = ev.get('percent', state_obj.percent)
        if msg:
            ts = datetime.now().strftime("%H:%M:%S")
            state_obj.last_messages.append(f"[{ts}] {msg}")
        
        state_obj.working = (ev.get('error') is None) and (not ev.get('done', False))
        state_obj.subphase_title = msg
        state_obj.percent = int(p)
        state_obj.done = bool(ev.get('done', False))
        state_obj.error = ev.get('error')
        
        render_phase_runner.refresh()

    # --- SHARED FUNCTIONS ---
    def extract_files_from_preview(state_obj=None):
        """Extrae lista de archivos del preview_data (funciona con flow_step y catalog como folder_scan)."""
        state_to_use = state_obj if state_obj else design_state
        selector_state = state_to_use.data_source_selector_state
        if not selector_state.preview_data:
            return []

        # El preview de folder_scan tiene columnas como 'path', 'name', etc.
        preview = selector_state.preview_data
        files = []

        # Buscar columna 'path' que contiene las rutas de archivos
        if hasattr(preview, 'columns') and 'path' in preview.columns:
            for row in preview.rows:
                file_path = row.get('path', '')
                # Filtrar solo archivos PDF para extracción
                if file_path and file_path.lower().endswith('.pdf'):
                    files.append(file_path)

        # Ordenar alfabéticamente por nombre de archivo (igual que el uploader)
        # Esto garantiza que el documento guía sea predecible
        files.sort(key=lambda p: p.split('\\')[-1].split('/')[-1].lower())

        return files

    @ui.refreshable
    def render_design():
        """
        Renderiza el modo de diseño completo (wizard de creación/edición).
        Preserva todas las fases del asistente original.
        """
        
        # --- SUB-ROUTING ---
        phase = design_state.phase
        mode = design_state.mode

        # Función de actualización de progreso mejorada con mapeo por fases
        def update_run_progress(ev):
            if isinstance(ev, str):
                ev = {'message': ev}
            msg = ev.get('message', '')
            internal_percent = ev.get('percent', 50)  # Porcentaje interno de la fase

            exec_state.subphase_msg = msg

            # Mapear el porcentaje interno al rango global de la fase actual
            phase_name = getattr(exec_state, 'progress_phase', 'execution')
            mapped_percent = map_progress(phase_name, internal_percent)

            # Nunca retroceder el progreso
            exec_state.percent = max(exec_state.percent, mapped_percent)

            exec_state.working = not ev.get('done', False) and ev.get('error') is None
            exec_state.done = ev.get('done', False)
            if ev.get('error'):
                exec_state.error_msg = ev.get('error')

            render_progress_panel.refresh()

        # Componente de progreso refreshable
        @ui.refreshable
        def render_progress_panel():
            with ui.card().classes('w-full p-8 items-center border-t-4 border-t-primary'):
                ref_count = getattr(exec_state, 'refinements_count', 0)
                title_text = "Refinando algoritmo inteligente" if ref_count > 0 and exec_state.working else t('extraction.generating_script', 'Generando script de extracción')
                
                ui.label(title_text).classes('text-2xl font-bold text-slate-800 mb-6')

                # Mensaje de subfase actual
                sub_msg = getattr(exec_state, 'subphase_msg', 'Iniciando...')
                with ui.column().classes('w-full items-center justify-center py-6 bg-slate-50 rounded-lg mb-4'):
                    if exec_state.working and not exec_state.done:
                        ui.spinner(size='xl', color='primary', thickness=3)
                    ui.label(sub_msg).classes('text-lg text-primary font-semibold mt-4 text-center')
                    if exec_state.working and not exec_state.done:
                        ui.label(t('extraction.long_process_warning', 'Este proceso puede tardar varios minutos. Por favor, permanezca en esta pantalla sin cerrarla ni abandonarla.')).classes('text-sm text-slate-500 mt-2 text-center max-w-md')

                # Barra de progreso
                percent = exec_state.percent or 0
                ui.linear_progress(value=percent/100, show_value=False).classes('w-full h-3 rounded-full').props('color=primary stripe')
                ui.label(f"{percent}%").classes('text-right text-sm font-bold text-primary mt-1 w-full')

                # Botón cancelar (si está trabajando)
                if exec_state.working and not exec_state.done:
                    with ui.row().classes('w-full justify-center mt-4'):
                        async def cancel_run():
                            exec_state.working = False
                            exec_state.done = True
                            design_state.phase = 'definition'
                            layout_manager.update_step_index(1)
                            render_design.refresh()
                        ui.button(t('common.cancel', 'Cancelar'), icon='close', on_click=cancel_run).props('flat color=red')

                # Mensaje de error mult-opción
                if hasattr(exec_state, 'error_msg') and exec_state.error_msg:
                    is_validation_error = getattr(exec_state, 'is_validation_error', False)
                    validation_errors = getattr(exec_state, 'validation_errors', {})

                    # Calcular porcentaje de éxito para errores de validación
                    total_fields = len(design_state.field_definitions) if design_state.field_definitions else 1
                    failed_fields = len(validation_errors) if validation_errors else 0
                    success_rate = ((total_fields - failed_fields) / total_fields) * 100 if total_fields > 0 else 0

                    # Card con fondo blanco y borde según tipo de error
                    card_classes = 'w-full p-6 bg-white border mt-4 '
                    card_classes += 'border-amber-300' if is_validation_error else 'border-red-300'

                    with ui.card().classes(card_classes):
                        if is_validation_error:
                            # UI para errores de VALIDACIÓN (ANCHOR_MISMATCH)
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('warning', color='amber').classes('text-2xl')
                                ui.label(t('extraction.validation_mismatch', 'Discrepancias en la validación')).classes('text-amber-700 text-lg font-bold')
                                ui.badge(f'{success_rate:.0f}% coincidencia', color='amber').classes('ml-auto')

                            ui.label(t('extraction.validation_desc', 'El script se ejecutó pero algunos campos no coinciden exactamente con los ejemplos esperados. Revisa la tabla y decide si el resultado es aceptable o si deseas refinarlo.')).classes('text-sm text-slate-600 mb-4')

                            # Tabla comparativa de errores
                            with ui.card().classes('w-full bg-slate-50 p-4 mb-4'):
                                ui.label('Comparación de resultados').classes('font-bold text-slate-700 mb-2')

                                # Construir datos para la tabla y truncar largos en Python
                                table_rows = []
                                for field_name, error_detail in validation_errors.items():
                                    expected = ''
                                    obtained = ''
                                    error_str = str(error_detail)
                                    if 'esperado≈' in error_str and 'obtenido=' in error_str:
                                        import re
                                        match = re.search(r'esperado≈"([^"]*)".*obtenido="([^"]*)"', error_str)
                                        if match:
                                            expected = match.group(1)
                                            obtained = match.group(2)
                                    else:
                                        expected = error_str
                                        obtained = '(ver detalle)'
                                        
                                    # Truncar textos largos de forma segura en Python
                                    expected_trunc = expected[:80] + '...' if len(expected) > 80 else expected
                                    obtained_trunc = obtained[:80] + '...' if len(obtained) > 80 else obtained

                                    table_rows.append({
                                        'campo': field_name,
                                        'esperado': expected_trunc,
                                        'obtenido': obtained_trunc
                                    })

                                columns = [
                                    {'name': 'campo', 'label': 'Campo', 'field': 'campo', 'align': 'left'},
                                    {'name': 'esperado', 'label': 'Esperado', 'field': 'esperado', 'align': 'left'},
                                    {'name': 'obtenido', 'label': 'Obtenido', 'field': 'obtenido', 'align': 'left'},
                                ]
                                    
                                ui.table(columns=columns, rows=table_rows, row_key='campo').classes('w-full').props('dense flat bordered')
                                
                                # Añadir expander con el JSON completo
                                import json as _json
                                with ui.expansion('Ver datos completos de validación (JSON)', icon='data_object').classes('w-full mt-2 bg-white border border-slate-200'):
                                    ui.code(_json.dumps(validation_errors, indent=2, ensure_ascii=False), language='json').classes('w-full text-xs')

                            # Input para feedback de refinamiento
                            feedback_input = ui.textarea(
                                label=t('extraction.refinement_feedback', 'Instrucciones adicionales para refinar'),
                                placeholder='Ej: "El nombre completo incluye dos apellidos, no solo el nombre de pila"'
                            ).classes('w-full mb-4').props('outlined rows=2')

                            # Funciones para las acciones
                            async def retry_with_feedback():
                                feedback_text = feedback_input.value
                                if not feedback_text.strip():
                                    ui.notify('Por favor, proporciona instrucciones de refinamiento', type='warning')
                                    return
                                # Guardar feedback y reiniciar calibración
                                exec_state.refinement_feedback = feedback_text
                                exec_state.error_msg = None
                                exec_state.validation_errors = {}
                                exec_state.working = True
                                
                                # Llamada síncrona/awaitable directa para no perder contexto de NiceGUI
                                await run_refinement()

                            def accept_results():
                                # Usar los resultados parciales aunque no sea 100%
                                partial = getattr(exec_state, 'partial_results', {})
                                exec_state.results = partial
                                exec_state.validation_report = {'accepted_with_warnings': True, 'validation_errors': validation_errors}
                                exec_state.error_msg = None
                                exec_state.validation_errors = {}
                                exec_state.is_validation_error = False
                                exec_state.done = True
                                design_state.phase = 'results'
                                layout_manager.update_step_index(3)
                                render_design.refresh()

                            async def trigger_escalation(with_fallback=False):
                                client, license_key = await state.extractor._get_brain_client()
                                script_code = getattr(design_state, '_last_script', '')
                                
                                # Better default name
                                default_name = "Extractor PDF"
                                if design_state.files_to_process:
                                    first_fname = design_state.files_to_process[0].split('\\')[-1].split('/')[-1]
                                    default_name = f"Extractor: {first_fname}"
                                
                                script_name = getattr(design_state, 'user_instructions', '') or default_name
                                
                                # Contextual notes
                                notes = f"El usuario solicita ayuda con este extractor.\n"
                                if exec_state.error_msg:
                                    notes += f"\nError detectado: {exec_state.error_msg}"
                                
                                fields_str = ", ".join([f.name for f in design_state.field_definitions if f.name])
                                if fields_str:
                                    notes += f"\nCampos objetivo: {fields_str}"
                                    
                                if not script_code:
                                    notes += "\n\nNota: No se pudo generar código original (fallo previo a generación)."
                                else:
                                    notes += "\n\nNota: Se incluye el código que falló en la ejecución."
                                
                                try:
                                    await client.escalate_script(
                                        script_name=script_name,
                                        original_code=script_code or "# No se pudo generar código original",
                                        client_notes=notes,
                                        license_key=license_key
                                    )
                                    ui.notify(t('extraction.escalate_success', 'Problema escalado al Partner correctamente.'), type='positive')
                                except Exception as e_esc:
                                    ui.notify(f"Error al escalar: {e_esc}", type='negative')

                                if with_fallback:
                                    await try_llm_fallback()
                                else:
                                    exec_state.working = False
                                    exec_state.done = True
                                    design_state.phase = 'definition'
                                    layout_manager.update_step_index(1)
                                    render_design.refresh()

                            # Botones de acción en modo Validación Fallida (Naranja)
                            with ui.row().classes('w-full gap-2 flex-wrap'):
                                ui.button(
                                    t('extraction.retry_with_feedback', 'Refinar con instrucciones'),
                                    icon='refresh',
                                    on_click=retry_with_feedback
                                ).props('color=primary text-color=white')

                        else:
                            # UI para errores de SEGURIDAD u otros errores críticos
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('error', color='red').classes('text-2xl')
                                ui.label(t('extraction.error_detected', 'Error detectado en la generación')).classes('text-red-700 text-lg font-bold')

                            ui.label(t('extraction.error_desc', 'El modelo no ha podido aislar un script válido tras varios intentos. Puedes escalar el problema a tu Partner para que lo resuelva de forma manual.')).classes('text-sm text-slate-700 mb-4')

                            with ui.expansion("Ver detalles técnicos", icon="bug_report").classes('w-full mb-4 bg-slate-50'):
                                ui.label(exec_state.error_msg).classes('text-xs text-slate-600 break-all font-mono')

                            with ui.column().classes('w-full gap-2'):
                                ui.button(t('extraction.escalate_partner', 'Elevar a soporte (Partner)'), icon='support_agent', on_click=lambda: trigger_escalation(False)).props('color=red text-color=white')
                                ui.button(t('extraction.fallback_llm', 'Ejecutar extraccion LLM (1 vez)'), icon='psychology', on_click=try_llm_fallback).props('color=orange text-color=white')
                                ui.button(t('extraction.escalate_and_fallback', 'Elevar a soporte Y Ejecutar LLM'), icon='call_split', on_click=lambda: trigger_escalation(True)).props('color=primary text-color=white')

        # Ejecutar calibración
        async def run_calibration():
            import shutil as _shutil
            from pathlib import Path as _Path
            try:
                exec_state.working = True
                exec_state.progress_phase = 'preparation'
                exec_state.percent = map_progress('preparation', 0)
                exec_state.subphase_msg = 'Preparando archivos...'
                exec_state.error_msg = None
                render_progress_panel.refresh()

                # Asegurar que existe un execution_id antes de ejecutar
                eid = design_state.ensure_context()

                # Copiar archivos al directorio de inputs del execution context
                input_dir = state.extractor.path_manager.get_input_dir(eid)
                if not input_dir.exists():
                    input_dir.mkdir(parents=True, exist_ok=True)

                # Obtener archivos a procesar (pueden venir del uploader o del folder_scan)
                files_to_copy = design_state.files_to_process
                if not files_to_copy:
                    files_to_copy = extract_files_from_preview()

                exec_state.subphase_msg = f'Copiando {len(files_to_copy)} archivo(s)...'
                exec_state.percent = map_progress('preparation', 100)
                render_progress_panel.refresh()

                # Cambiar a fase de ejecución para el pipeline
                exec_state.progress_phase = 'execution'

                # Copiar archivos externos al directorio de inputs
                for file_path in files_to_copy:
                    src = _Path(file_path)
                    if src.exists() and src.parent != input_dir:
                        dst = input_dir / src.name
                        if not dst.exists():
                            _shutil.copy2(str(src), str(dst))

                # Recuperar feedback de refinamiento si existe
                feedback_val = getattr(exec_state, 'refinement_feedback', "")

                res = await state.extractor.run_factory_pipeline(
                    execution_id=eid,
                    user_feedback=feedback_val,
                    field_definitions=design_state.field_definitions,
                    on_progress=update_run_progress,
                    force_discovery=design_state.auto_discover_fields
                )

                # Limpiar feedback tras el intento
                if hasattr(exec_state, 'refinement_feedback'):
                    exec_state.refinement_feedback = ""

                # Extraer resultados del pipeline
                if res.get('status') == 'error':
                    # Distinguir entre error de validación y error de seguridad
                    validation_errors = res.get('meta', {}).get('validation_errors', {})
                    script_code = res.get('code', '')

                    if validation_errors and script_code:
                        # Error de validación: el script existe pero los resultados no coinciden
                        exec_state.validation_errors = validation_errors
                        exec_state.is_validation_error = True
                        design_state._last_script = script_code
                        # Guardar resultados parciales para poder aceptarlos
                        exec_state.partial_results = res.get('result', res.get('data', {}))
                        exec_state.error_msg = res.get('error', 'Error de validación')
                        exec_state.working = False
                        exec_state.docs_text_list_anon = res.get('docs_text_list_anon', getattr(exec_state, 'docs_text_list_anon', None))
                        exec_state.anon_mappings = res.get('anon_mappings', getattr(exec_state, 'anon_mappings', None))
                        render_progress_panel.refresh()
                    else:
                        # Error de seguridad u otro error crítico
                        exec_state.is_validation_error = False
                        raise Exception(res.get('error', 'Error en el pipeline'))
                else:
                    exec_state.results = res.get('result', res.get('data', {}))
                    exec_state.validation_report = res.get('validation_report', {})
                    design_state._last_script = res.get('code', '')
                    
                    exec_state.batch_results = res.get('batch_results', [])
                    exec_state.audit_report = res.get('audit', '')
                    exec_state.docs_text_list_anon = res.get('docs_text_list_anon', getattr(exec_state, 'docs_text_list_anon', None))
                    exec_state.anon_mappings = res.get('anon_mappings', getattr(exec_state, 'anon_mappings', None))

                    exec_state.progress_phase = 'finalization'
                    update_run_progress({'message': 'Completado', 'percent': 100, 'done': True})
                    await asyncio.sleep(0.5)

                    design_state.phase = 'results'
                    exec_state.working = False
                    exec_state.done = True
                    exec_state.is_validation_error = False
                    layout_manager.update_step_index(3)
                    render_design.refresh()

            except Exception as e_cal:
                exec_state.working = False
                exec_state.is_validation_error = False
                exec_state.error_msg = str(e_cal)
                render_progress_panel.refresh()

        async def run_refinement():
            try:
                # Cambiar de fase para que se vea el spinner/progreso
                # CRITICAL: For factory mode, NEVER set phase='run' because the 'run' phase
                # renders a ui.timer(0.1, run_calibration) that re-reads all documents and
                # restarts the full factory pipeline. Use 'PROCESSING' for both modes.
                design_state.phase = 'PROCESSING'
                if design_state.mode == 'factory':
                    layout_manager.update_step_index(2)
                
                render_design.refresh()

                exec_state.working = True
                exec_state.progress_phase = 'refinement'
                exec_state.percent = map_progress('refinement', 0)
                # Actualizar tanto subphase_msg como subphase_title para consistencia en diferentes renderers
                msg = 'Reparando con las indicaciones adicionales...' if design_state.mode == 'factory' else 'Refinando lógica de extracción (Tier 2)...'
                exec_state.subphase_msg = msg
                exec_state.subphase_title = msg
                exec_state.error_msg = None
                render_progress_panel.refresh()

                eid = design_state.ensure_context()
                
                # Copy files to execution context for fallback OCR
                import shutil as _shutil
                from pathlib import Path as _Path
                input_dir = state.extractor.path_manager.get_input_dir(eid)
                files_to_copy = design_state.files_to_process or extract_files_from_preview()
                for file_path in files_to_copy:
                    src = _Path(file_path)
                    if src.exists() and src.parent != input_dir:
                        dst = input_dir / src.name
                        if not dst.exists():
                            _shutil.copy2(str(src), str(dst))

                feedback_val = getattr(exec_state, 'refinement_feedback', "")
                prev_code = getattr(design_state, '_last_script', "")
                
                # Consolidar reporte de auditoría (errores técnicos + reporte forense si existe)
                import json as _json
                validation_data = getattr(exec_state, 'validation_errors', {})
                forensic_data = getattr(exec_state, 'audit_report', "")
                
                full_audit_context = f"## Errores de Validación (Doc 1 vs Ejemplos):\n{_json.dumps(validation_data, indent=2, ensure_ascii=False)}\n\n"
                if forensic_data:
                    if isinstance(forensic_data, dict):
                        forensic_data = forensic_data.get('report', str(forensic_data))
                    full_audit_context += f"## Análisis de Calidad y Consistencia (Multi-Doc):\n{forensic_data}"
                
                if design_state.mode == 'factory':
                    res = await state.extractor.refine_factory_pipeline(
                        execution_id=eid,
                        user_feedback=feedback_val,
                        previous_code=prev_code,
                        audit_report=full_audit_context,
                        field_definitions=design_state.field_definitions,
                        docs_text_list_anon=getattr(exec_state, 'docs_text_list_anon', None),
                        anon_mappings=getattr(exec_state, 'anon_mappings', None)
                    )
                else:
                    # Modo Genérico - Tier 2 Refinement
                    exec_state.subphase_msg = 'Refinando lógica de extracción (Tier 2)...'
                    if design_state.mode == 'generic':
                        render_design.refresh()
                    else:
                        render_progress_panel.refresh()
                    
                    res = await state.extractor.refine_generic_pipeline(
                        execution_id=eid,
                        user_feedback=feedback_val,
                        previous_data=exec_state.results,
                        docs_text_list_anon=getattr(exec_state, 'docs_text_list_anon', None),
                        anon_mappings=getattr(exec_state, 'anon_mappings', None)
                    )
                    
                    # Acumular feedback para persistencia de instrucciones
                    if res.get('status') == 'success':
                        design_state._accumulated_feedback = (getattr(design_state, '_accumulated_feedback', "") + "\n" + feedback_val).strip()

                if hasattr(exec_state, 'refinement_feedback'):
                    exec_state.refinement_feedback = ""
                
                exec_state.refinements_count = getattr(exec_state, 'refinements_count', 0) + 1

                if res.get('status') == 'error':
                    v_errors = res.get('meta', {}).get('validation_errors', {})
                    s_code = res.get('code', '')

                    if v_errors and s_code:
                        exec_state.validation_errors = v_errors
                        exec_state.is_validation_error = True
                        design_state._last_script = s_code
                        exec_state.partial_results = res.get('result', {})
                        exec_state.error_msg = res.get('error', 'El refinado no resolvió todas las discrepancias.')
                        exec_state.working = False
                        exec_state.docs_text_list_anon = res.get('docs_text_list_anon', getattr(exec_state, 'docs_text_list_anon', None))
                        exec_state.anon_mappings = res.get('anon_mappings', getattr(exec_state, 'anon_mappings', None))
                        if design_state.mode == 'generic':
                            render_design.refresh()
                        else:
                            render_progress_panel.refresh()
                    else:
                        exec_state.is_validation_error = False
                        raise Exception(res.get('error', 'Error crítico en el refinamiento T3'))
                else:
                    exec_state.results = res.get('result', {})
                    exec_state.validation_report = res.get('validation_report', {})
                    design_state._last_script = res.get('code', '')
                    exec_state.batch_results = res.get('batch_results', getattr(exec_state, 'batch_results', []))

                    exec_state.progress_phase = 'finalization'
                    update_run_progress({'message': 'Refinado con éxito', 'percent': 100, 'done': True})
                    await asyncio.sleep(0.5)

                    design_state.phase = 'results'
                    exec_state.working = False
                    exec_state.done = True
                    exec_state.is_validation_error = False
                    layout_manager.update_step_index(3)
                    render_design.refresh()

            except Exception as e_ref:
                exec_state.working = False
                exec_state.is_validation_error = False
                exec_state.error_msg = str(e_ref)
                exec_state.error = str(e_ref)
                if design_state.mode == 'generic':
                    render_design.refresh()
                else:
                    render_progress_panel.refresh()
        
        async def try_llm_fallback():
            """Ejecuta extracción usando LLM como fallback."""
            import shutil
            from pathlib import Path
            try:
                exec_state.error_msg = None
                exec_state.validation_errors = {}
                exec_state.is_validation_error = False
                exec_state.working = True
                exec_state.progress_phase = 'preparation'
                exec_state.percent = map_progress('preparation', 50)

                # Switch to run phase to view progress
                design_state.phase = 'run'
                layout_manager.update_step_index(2)
                
                render_design.refresh()

                # Obtener archivos
                eid = design_state.ensure_context()
                input_dir = state.extractor.path_manager.get_input_dir(eid)
                files_to_process = design_state.files_to_process or extract_files_from_preview()

                # Asegurar que los archivos están en el directorio de inputs
                for file_path in files_to_process:
                    src = Path(file_path)
                    if src.exists() and src.parent != input_dir:
                        dst = input_dir / src.name
                        if not dst.exists():
                            shutil.copy2(str(src), str(dst))

                # Obtener lista de archivos en input_dir
                pdf_files = [str(f) for f in input_dir.iterdir() if f.suffix.lower() == '.pdf']
                if not pdf_files:
                    pdf_files = files_to_process

                # Obtener campos a extraer
                target_fields = [fd.name for fd in design_state.field_definitions]

                # Ejecutar extracción genérica con LLM
                res = await state.extractor.process_files_generic(
                    file_paths=pdf_files[:1],  # Solo el primer archivo para validación
                    on_progress=lambda e: update_progress(e, exec_state),
                    target_fields=target_fields,
                    recognize_all=False,
                    top_k=len(target_fields)
                )

                # Actualizar resultados
                exec_state.results = res.get('data', {})
                metadata = res.get('metadata', {})
                exec_state.privacy_stats = metadata.get('privacy_stats', {})
                exec_state.docs_text_list_anon = metadata.get('_docs_text_anon', getattr(exec_state, 'docs_text_list_anon', None))

                # Generar validation_report desde los resultados LLM
                llm_data = exec_state.results
                if isinstance(llm_data, list) and llm_data:
                    llm_data = llm_data[0] if isinstance(llm_data[0], dict) else {}

                new_report = {}
                for fd in design_state.field_definitions:
                    extracted_val = llm_data.get(fd.name, '')
                    # Comparar con el valor esperado (simplificado)
                    is_valid = bool(extracted_val)
                    new_report[fd.name] = {
                        'valid': is_valid,
                        'value': extracted_val,
                        'source': 'LLM'
                    }
                exec_state.validation_report = new_report

                exec_state.working = False
                exec_state.done = True
                
                # Switch to results phase explicitly
                design_state.phase = 'results'
                layout_manager.update_step_index(3)
                
                ui.notify('Extracción LLM completada', type='positive')
                render_design.refresh()

            except Exception as e:
                exec_state.working = False
                ui.notify(f'Error en fallback LLM: {str(e)}', type='negative')
                render_design.refresh()

        # --- DESIGN UI ---
        with ui.column().classes('w-full p-0 max-w-5xl mx-auto'):
            # Contextual Header (Flow vs Standalone)
            from client_app.app.core.state import app_state
            
            if app_state.editing_flow and layout_manager.from_flow_context:
                # Banner azul contextual (SOLO si viene de flujo)
                with ui.row().classes('w-full bg-primary text-white p-3 items-center gap-3 mb-6 rounded-b shadow-md'):
                    ui.icon('assignment', size='md')
                    ui.label(f'Configurando paso {app_state.flow_step_index + 1}: {app_state.editing_step.name if app_state.editing_step else "Extractor"}').classes('font-bold')
                    ui.label(f'Flujo: {app_state.flow_name}').classes('text-xs opacity-80')
                    
                    ui.space()
                    
                    async def back_to_flow():
                        layout_manager.exit_design_mode_to_flow()
                        app_state.clear_atom_editing_context()
                        ui.navigate.to(f'/flows/{app_state.flow_id}')
                    
                    ui.button('VOLVER AL FLUJO', icon='arrow_back', on_click=back_to_flow).props('flat text-color=white')
            else:
                with ui.row().classes('w-full items-center gap-4 mb-6 mt-4 px-4 bg-white sticky top-0 z-10 py-2 border-b'):
                    ui.button(icon='arrow_back', on_click=go_to_library).props('flat round').classes('text-gray-600')
                    with ui.column().classes('gap-0'):
                        ui.label(t('extraction.design_title', 'Diseño de extractor')).classes('text-2xl font-bold text-primary')
                        ui.label(t('extraction.design_subtitle', 'Define los campos a extraer y calibra el modelo con documentos de ejemplo')).classes('text-sm text-slate-500')

            # Content container with padding
            with ui.column().classes('w-full px-4'):
                # Content based on Phase
                if phase == 'files':
                    # Generic Fields Config (Legacy logic)
                    # Bloque Indigo eliminado: se unifican las fases y la definición se hace en la fase 2

                    # ================================================================
                    # DATA SOURCE SELECTOR (Unified approach from naming.md)
                    # ================================================================
                    async def handle_source_selection(selection: DataSourceSelection):
                        """Maneja la selección de fuente de datos."""
                        design_state.data_source = selection

                        if selection.source_type == 'manual':
                            # Archivo cargado manualmente - guardar en contexto de ejecución
                            eid = design_state.ensure_context()
                            if selection.file_content and selection.file_name:
                                file_path = state.extractor.path_manager.get_input_dir(eid) / selection.file_name
                                with open(file_path, 'wb') as f:
                                    f.write(selection.file_content)
                                
                                if str(file_path) not in design_state.files_to_process:
                                    design_state.files_to_process.append(str(file_path))
                        elif selection.source_type == 'catalog':
                            pass # Acción del catálogo seleccionada
                        elif selection.source_type == 'flow_step':
                            pass # Paso de flujo seleccionado
                            # Los archivos se extraerán del preview_data al continuar

                        render_design.refresh()

                    def auto_load_excel_schema_from_preview():
                        """Busca un Excel en la carpeta del folder_scan y precarga los campos automáticamente."""
                        import re
                        import unicodedata
                        from pathlib import Path
                        selector_state = design_state.data_source_selector_state
                        if not selector_state.preview_data:
                            return

                        preview = selector_state.preview_data
                        excel_path = None

                        # Buscar archivo Excel en el preview (por si el folder_scan lo incluye)
                        if hasattr(preview, 'columns') and 'path' in preview.columns:
                            for row in preview.rows:
                                file_path = row.get('path', '')
                                if file_path and file_path.lower().endswith(('.xlsx', '.xls')):
                                    excel_path = file_path
                                    break

                        # Si no hay Excel en el preview, buscar en la misma carpeta que los PDFs
                        if not excel_path and hasattr(preview, 'rows') and preview.rows:
                            # Obtener la carpeta del primer archivo
                            first_file = None
                            for row in preview.rows:
                                fp = row.get('path', '')
                                if fp:
                                    first_file = fp
                                    break

                            if first_file:
                                folder = Path(first_file).parent
                                # Buscar Excel en esa carpeta
                                for ext in ['*.xlsx', '*.xls']:
                                    excel_files = list(folder.glob(ext))
                                    if excel_files:
                                        excel_path = str(excel_files[0])
                                        break

                        if not excel_path:
                            return

                        try:
                            import pandas as pd
                            df = pd.read_excel(excel_path)

                            # Normalización y búsqueda de columnas (misma lógica que el uploader)
                            def normalize(text):
                                """Normaliza texto: minúsculas, sin acentos, sin espacios extra."""
                                text = str(text).lower().strip()
                                text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
                                text = re.sub(r'\s+', ' ', text)
                                return text

                            def match_column(columns, patterns):
                                for col in columns:
                                    col_norm = normalize(col)
                                    for pattern in patterns:
                                        if pattern in col_norm:
                                            return col
                                return None

                            name_patterns = ['nombre de campo', 'nombre del campo', 'nombre', 'campo', 'name', 'field', 'variable']
                            desc_patterns = ['instrucciones', 'instruccion', 'descripcion', 'descripción', 'description', 'instruction']
                            example_patterns = ['ejemplo en texto', 'ejemplo', 'example', 'valor', 'value', 'muestra']
                            page_patterns = ['pagina', 'page', 'num_pag', 'num pag', 'no pag', 'pag']

                            name_col = match_column(df.columns, name_patterns)
                            desc_col = match_column(df.columns, desc_patterns)
                            ex_col = match_column(df.columns, example_patterns)
                            page_col = match_column(df.columns, page_patterns)

                            # Debug logging
                            import logging
                            logging.info(f"[auto_load_excel] Columnas Excel: {list(df.columns)}")
                            logging.info(f"[auto_load_excel] Columnas normalizadas: {[normalize(c) for c in df.columns]}")
                            logging.info(f"[auto_load_excel] name_col={name_col}, desc_col={desc_col}, ex_col={ex_col}, page_col={page_col}")

                            if not name_col:
                                return  # No es un Excel de esquema válido

                            # Limpiar campos existentes si solo hay la fila vacía por defecto
                            if len(design_state.field_definitions) == 1 and not design_state.field_definitions[0].name.strip():
                                design_state.field_definitions.clear()

                            # Agregar campos desde el Excel
                            added = 0
                            for _, row in df.iterrows():
                                name_val = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
                                if not name_val:
                                    continue

                                desc_val = str(row[desc_col]).strip() if desc_col and pd.notna(row[desc_col]) else ""
                                ex_val = str(row[ex_col]).strip() if ex_col and pd.notna(row[ex_col]) else ""

                                # Manejar page_val - puede venir como número desde Excel
                                page_val = ""
                                if page_col and pd.notna(row[page_col]):
                                    raw_page = row[page_col]
                                    # Si es número (int o float), convertir apropiadamente
                                    if isinstance(raw_page, (int, float)):
                                        # Si es entero o float sin decimales, quitar el .0
                                        page_val = str(int(raw_page)) if raw_page == int(raw_page) else str(raw_page)
                                    else:
                                        page_val = str(raw_page).strip()

                                logging.info(f"[auto_load_excel] Campo: {name_val}, page_col={page_col}, raw={row[page_col] if page_col else 'N/A'}, page_val='{page_val}'")

                                # Evitar duplicados
                                if not any(f.name == name_val for f in design_state.field_definitions):
                                    design_state.field_definitions.append(FieldDef(
                                        name=name_val,
                                        description=desc_val,
                                        example_value=ex_val,
                                        page_hint=page_val,
                                        is_optional=True
                                    ))
                                    added += 1

                            if added > 0:
                                excel_name = excel_path.split('\\')[-1].split('/')[-1]
                                try:
                                    ui.notify(f'Se cargaron {added} campos desde "{excel_name}"', type='positive')
                                except RuntimeError:
                                    logging.info(f"[auto_load_excel] Cargados {added} campos silenciosamente (sin UI context).")

                        except Exception as e:
                            # Log de errores para depuración
                            import logging
                            logging.warning(f"[auto_load_excel] Error procesando Excel: {e}")

                    def on_preview_loaded_callback():
                        """Callback cuando el preview se carga: refresca UI y busca Excel de esquema."""
                        try:
                            # Intentar obtener el cliente de la UI actual
                            client = ui.context.client
                            def do_refresh():
                                auto_load_excel_schema_from_preview()
                                render_design.refresh()
                            
                            if client:
                                # Ejecutar dentro del contexto del cliente
                                with client:
                                    do_refresh()
                            else:
                                do_refresh()
                        except RuntimeError:
                            # Fallback si no hay contexto disponible
                            auto_load_excel_schema_from_preview()
                            render_design.refresh()

                    # Configurar callback para refrescar la vista cuando el preview se cargue
                    design_state.data_source_selector_state.on_preview_loaded = on_preview_loaded_callback

                    # Renderizar el selector unificado
                    # Para Extractor PDF, limitamos formatos a PDF (sin OCR de imagen actualmente)
                    render_data_source_selector(
                        consumer_type=StepType.EXTRACTION,
                        on_source_selected=handle_source_selection,
                        flow_context=state.flow_context,
                        initial_selection=design_state.data_source,
                        upload_formats_override=['pdf'],
                        selector_state_override=design_state.data_source_selector_state
                    )

                    # Mostrar archivos seleccionados (manual, flow_step, o catalog como folder_scan)
                    # Extraer archivos del preview si ya se cargó
                    preview_files = []
                    if design_state.data_source and design_state.data_source.source_type in ('flow_step', 'catalog'):
                        preview_files = extract_files_from_preview()

                    files_to_show = design_state.files_to_process or preview_files
                    if files_to_show:
                        # Mostrar lista detallada de archivos con indicador del documento de muestra
                        with ui.card().classes('w-full p-4 border border-slate-200 mt-4'):
                            with ui.row().classes('items-center gap-2 mb-3'):
                                ui.icon('folder_open', color='primary')
                                source_label = design_state.data_source.atom_name if (design_state.data_source and design_state.data_source.atom_name) else "fuente seleccionada"
                                ui.label(f'{len(files_to_show)} archivo(s) PDF de {source_label}').classes('font-bold text-slate-800')

                            # Lista de archivos (mostrar máximo 8, con scroll si hay más)
                            with ui.column().classes('w-full gap-1 max-h-64 overflow-y-auto'):
                                for i, file_path in enumerate(files_to_show[:8]):
                                    is_sample = (i == 0)
                                    file_name = file_path.split('\\')[-1].split('/')[-1] if isinstance(file_path, str) else str(file_path)

                                    bg_class = 'bg-blue-50 border-blue-300 border-2' if is_sample else 'bg-slate-50 border-slate-200 border'
                                    icon_name = 'stars' if is_sample else 'picture_as_pdf'
                                    icon_color = 'blue' if is_sample else 'red'

                                    with ui.card().classes(f'w-full p-2 {bg_class} shadow-none'):
                                        with ui.row().classes('items-center gap-3 w-full'):
                                            ui.icon(icon_name, color=icon_color, size='sm')
                                            with ui.column().classes('flex-1 gap-0'):
                                                ui.label(file_name).classes('font-medium text-slate-800 text-sm truncate')
                                                if is_sample:
                                                    ui.label('Documento guía (muestra para la programación)').classes('text-xs font-bold text-blue-700')

                                if len(files_to_show) > 8:
                                    ui.label(f'... y {len(files_to_show) - 8} archivo(s) más').classes('text-xs text-slate-500 italic mt-1 pl-2')

                    # Next Action
                    with ui.row().classes('w-full justify-end mt-6'):
                        # Determinar si se puede continuar
                        can_proceed = (
                            len(design_state.files_to_process) > 0 or
                            len(preview_files) > 0 or
                            (design_state.data_source and design_state.data_source.source_type in ('flow_step', 'catalog')
                             and design_state.data_source_selector_state.preview_data is None)  # Permitir si aún no se cargó preview
                        )

                        def proceed_to_definition():
                            # Extraer archivos antes de continuar si vienen del preview (flow_step o catalog)
                            if not design_state.files_to_process and design_state.data_source and design_state.data_source.source_type in ('flow_step', 'catalog'):
                                files = extract_files_from_preview()
                                if files:
                                    design_state.files_to_process = files
                            
                            # Intentar auto-cargar esquema desde Excel si hay archivos
                            if design_state.files_to_process:
                                auto_load_excel_schema_from_preview()

                            setattr(design_state, 'phase', 'definition')
                            layout_manager.update_step_index(1)
                            render_design.refresh()
                        
                        ui.button(t('extraction.define_fields', 'Definir campos'), icon='arrow_forward', on_click=proceed_to_definition).set_enabled(can_proceed)

                elif phase == 'definition':
                    # Asegurar al menos una fila vacía por defecto
                    if not design_state.field_definitions:
                        design_state.field_definitions.append(FieldDef(name='', description='', example_value='', page_hint='', is_optional=True))

                    with ui.card().classes('w-full p-6 shadow-sm'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label(t('extraction.extraction_vars', 'Variables de extracción')).classes('text-xl font-bold text-slate-800')

                        # Header de la tabla de variables
                        if design_state.field_definitions:
                            with ui.row().classes('w-full font-bold text-sm text-gray-600 pb-2 border-b mb-2 gap-2'):
                                ui.label(t('extraction.field_name', 'Nombre de campo')).classes('w-2/12')
                                ui.label(t('extraction.field_instructions', 'Instrucciones (opcional)')).classes('flex-1')
                                ui.label(t('extraction.field_example', 'Ejemplo en texto')).classes('w-3/12')
                                ui.label(t('extraction.field_page', 'Página(s)')).classes('w-1/12').tooltip(t('extraction.field_page_tooltip', 'Ej: 1 o 1,3,5 (Opcional)'))
                                ui.label(t('extraction.actions', 'Acciones')).classes('w-16 text-center')
                        
                        # Filas de variables
                        with ui.column().classes('w-full gap-2 border rounded p-2 bg-slate-50'):
                            for idx, row in enumerate(design_state.field_definitions):
                                with ui.row().classes('w-full items-center gap-2'):
                                    ui.input(value=row.name, on_change=lambda e, r=row: setattr(r, 'name', e.value)).classes('w-2/12').props('dense outlined hide-bottom-space')
                                    ui.input(value=row.description, on_change=lambda e, r=row: setattr(r, 'description', e.value)).classes('flex-1').props('dense outlined hide-bottom-space')
                                    ui.input(value=row.example_value, on_change=lambda e, r=row: setattr(r, 'example_value', e.value)).classes('w-3/12').props('dense outlined hide-bottom-space placeholder="Texto a encontrar"')
                                    ui.input(value=row.page_hint, on_change=lambda e, r=row: setattr(r, 'page_hint', e.value)).classes('w-1/12').props('dense outlined hide-bottom-space placeholder="Ej: 1"')
                                    with ui.row().classes('w-16 justify-center'):
                                        ui.button(icon='delete', on_click=lambda i=idx: (design_state.field_definitions.pop(i), render_design.refresh())).props('flat dense color=red size=sm')
                            
                            with ui.row().classes('w-full justify-start mt-2'):
                                ui.button('+ Añadir fila', on_click=lambda: (design_state.field_definitions.append(FieldDef(name='', description='', example_value='', page_hint='', is_optional=True)), render_design.refresh())).props('flat dense text-primary')

                        # Expander para carga masiva por Excel
                        with ui.expansion('Importar esquema desde Excel', icon='file_upload').classes('w-full mt-4 bg-slate-50 border rounded'):
                            with ui.row().classes('w-full items-center gap-4 p-4'):
                                async def handle_excel_upload(e):
                                    try:
                                        content = await e.file.read()
                                        import pandas as pd
                                        import io
                                        df = pd.read_excel(io.BytesIO(content))
                                        
                                        # Buscar columnas por nombres comunes (soporta variaciones)
                                        import unicodedata
                                        import re
                                        def normalize(text):
                                            """Normaliza texto: minúsculas, sin acentos, sin espacios extra, sin caracteres especiales."""
                                            text = str(text).lower().strip()
                                            text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
                                            text = re.sub(r'\s+', ' ', text)  # Espacios múltiples a uno
                                            return text

                                        def match_column(columns, patterns):
                                            """Busca una columna que contenga alguno de los patrones."""
                                            for col in columns:
                                                col_norm = normalize(col)
                                                for pattern in patterns:
                                                    if pattern in col_norm:
                                                        return col
                                            return None

                                        # Patrones para cada tipo de columna (busca si contiene el patrón)
                                        name_patterns = ['nombre de campo', 'nombre del campo', 'nombre', 'campo', 'name', 'field', 'variable']
                                        desc_patterns = ['instrucciones', 'instruccion', 'descripcion', 'description', 'instruction']
                                        example_patterns = ['ejemplo en texto', 'ejemplo', 'example', 'valor', 'value', 'muestra']
                                        page_patterns = ['pagina', 'page', 'num_pag', 'num pag', 'no pag', 'pag']

                                        name_col = match_column(df.columns, name_patterns)
                                        desc_col = match_column(df.columns, desc_patterns)
                                        ex_col = match_column(df.columns, example_patterns)
                                        page_col = match_column(df.columns, page_patterns)

                                        if not name_col:
                                            # Mostrar columnas detectadas para ayudar al usuario
                                            cols_found = ', '.join([f'"{c}"' for c in df.columns[:5]])
                                            ui.notify(f'No se encontró columna "Nombre de campo". Columnas detectadas: {cols_found}', type='warning')
                                            return
                                            
                                        # Agregar campos
                                        added = 0
                                        for _, row in df.iterrows():
                                            name_val = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
                                            if not name_val:
                                                continue
                                                
                                            desc_val = str(row[desc_col]).strip() if desc_col and pd.notna(row[desc_col]) else ""
                                            ex_val = str(row[ex_col]).strip() if ex_col and pd.notna(row[ex_col]) else ""
                                            page_val = str(row[page_col]).strip() if page_col and pd.notna(row[page_col]) else ""
                                            
                                            # Check if already exists to avoid duplicates
                                            if not any(f.name == name_val for f in design_state.field_definitions):
                                                if not ex_val:
                                                    ui.notify(f'Aviso: el campo "{name_val}" no tiene ejemplo. Es muy recomendable incluirlo.', type='warning')
                                                
                                                # Si la única fila es la primera vacía por defecto, la sobrescribimos
                                                if len(design_state.field_definitions) == 1 and not design_state.field_definitions[0].name.strip():
                                                    design_state.field_definitions[0].name = name_val
                                                    design_state.field_definitions[0].description = desc_val
                                                    design_state.field_definitions[0].example_value = ex_val
                                                    design_state.field_definitions[0].page_hint = page_val
                                                else:
                                                    design_state.field_definitions.append(FieldDef(
                                                        name=name_val,
                                                        description=desc_val,
                                                        example_value=ex_val,
                                                        page_hint=page_val,
                                                        is_optional=True
                                                    ))
                                                added += 1
                                                
                                        ui.notify(f'Se insertaron {added} campos desde el Excel', type='positive')
                                        render_design.refresh()
                                    except Exception as ex:
                                        ui.notify(f'Error al procesar Excel: {str(ex)}', type='negative')
                                
                                ui.upload(on_upload=handle_excel_upload, auto_upload=True).props('accept=".xlsx" flat bordered dense size=sm max-files="1"').classes('w-full').tooltip(t('extraction.excel_tooltip', 'El Excel debe contener las columnas: Campo, Instrucciones y Ejemplo.'))
                                ui.label(t('extraction.excel_help', 'Opcional: Sube un Excel para cargar múltiples campos a la vez.')).classes('text-sm text-gray-500')

                        # Opción avanzada: Auto-descubrimiento de campos via LLM
                        with ui.expansion(t('extraction.advanced_options', 'Opciones avanzadas'), icon='tune').classes('w-full mt-4 bg-slate-50 border rounded'):
                            with ui.column().classes('w-full p-4 gap-4'):
                                # Opciones específicas para LLM (modo genérico)
                                if mode == 'generic':
                                    with ui.row().classes('items-center gap-4 p-2 bg-indigo-50/50 rounded border border-indigo-100 w-full mb-2'):
                                        ui.icon('auto_awesome', color='indigo')
                                        ui.checkbox(t('extraction.autodiscovery', 'Autodescubrimiento inteligente'), 
                                                   value=generic_options.value['recognize_all'], 
                                                   on_change=lambda e: generic_options.value.update({'recognize_all': e.value})).classes('font-medium')
                                        ui.space()
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label('Top-K:').classes('text-xs font-bold')
                                            ui.number(value=generic_options.value['top_k'], 
                                                     on_change=lambda e: generic_options.value.update({'top_k': int(e.value or 15)})).props('dense outlined style="max-width: 60px"').classes('bg-white font-bold')
                                        ui.label('(Nº de campos a detectar)').classes('text-xs text-slate-500')

                                ui.label(
                                    t('extraction.auto_discover_help',
                                      'Analiza el documento guía usando IA para descubrir automáticamente los campos disponibles '
                                      'y los añade a la tabla superior. No se generará el script hasta que continúes.')
                                ).classes('text-sm text-gray-600 mb-2')
                                
                                # Variables de estado locales para el progreso del descubrimiento
                                class DiscoveryState:
                                    def __init__(self):
                                        self.working = False
                                        self.percent = 0
                                        self.message = ""
                                        
                                d_state = DiscoveryState()
                                
                                @ui.refreshable
                                def render_discovery_progress():
                                    if d_state.working:
                                        with ui.column().classes('w-full mt-4 p-4 bg-blue-50 border border-blue-200 rounded'):
                                            with ui.row().classes('w-full items-center gap-3 mb-2'):
                                                ui.spinner('dots', size='sm', color='primary')
                                                ui.label(d_state.message or 'Analizando documento...').classes('text-sm font-semibold text-blue-800')
                                            ui.linear_progress(value=d_state.percent/100, show_value=False).props('color=primary stripe').classes('h-2 rounded-full')
                                            
                                render_discovery_progress()
                                
                                async def run_discovery(btn):
                                    btn.props('loading')
                                    d_state.working = True
                                    d_state.percent = 5
                                    d_state.message = "Preparando archivos..."
                                    render_discovery_progress.refresh()
                                    
                                    # Función de callback para recibir actualizaciones de progress
                                    def on_discovery_progress(ev):
                                        if isinstance(ev, str): ev = {'message': ev, 'percent': d_state.percent + 10}
                                        d_state.message = ev.get('message', 'Analizando...')
                                        d_state.percent = int(ev.get('percent', d_state.percent))
                                        render_discovery_progress.refresh()
                                        
                                    try:
                                        files = design_state.files_to_process
                                        if not files and design_state.data_source and design_state.data_source.source_type in ('flow_step', 'catalog'):
                                            files = extract_files_from_preview()
                                            
                                        if not files:
                                            ui.notify(t('extraction.no_files_for_discovery', 'No hay archivos PDF para analizar. Verifique que subió un documento.'), type='warning')
                                            return
                                            
                                        doc1_path = str(files[0])
                                        
                                        # Llama a la Fase 0 (Discovery) en el backend pasando el callback de progreso
                                        result = await state.extractor.suggest_fields_from_doc1(
                                            doc1_path, 
                                            top_k=20, 
                                            on_progress=on_discovery_progress
                                        )
                                        
                                        if result.get('status') == 'ok':
                                            new_fields = result.get('fields', [])
                                            added = 0
                                            
                                            # Limpiar la fila vacía por defecto
                                            if len(design_state.field_definitions) == 1 and not design_state.field_definitions[0].name.strip():
                                                design_state.field_definitions.clear()
                                                
                                            for f in new_fields:
                                                fname = f.get('name', '')
                                                if fname and not any(fd.name.lower() == fname.lower() for fd in design_state.field_definitions):
                                                    design_state.field_definitions.append(FieldDef(
                                                        name=fname,
                                                        description="",
                                                        example_value="",  # Se deja vacío intencionadamente
                                                        page_hint="",
                                                        is_optional=True
                                                    ))
                                                    added += 1
                                            
                                            ui.notify(f'Se descubrieron {added} campos nuevos y se añadieron a la lista.', type='positive')
                                            design_state.auto_discover_fields = False
                                        else:
                                            error_msg = result.get('error', 'Error desconocido')
                                            ui.notify(f'Fallo en descubrimiento: {error_msg}', type='negative')
                                            
                                    except Exception as ex:
                                        ui.notify(f'Error interno: {ex}', type='negative')
                                    finally:
                                        d_state.working = False
                                        btn.props(remove='loading')
                                        render_discovery_progress.refresh()
                                        render_design.refresh()

                                discover_btn = ui.button(
                                    t('extraction.run_discovery_btn', 'Descubrir campos ahora'), 
                                    icon='psychology', 
                                    on_click=lambda e: run_discovery(e.sender)
                                ).props('outline color=primary') 

                        with ui.row().classes('w-full justify-between mt-6 pt-4 border-t'):
                            def _can_calibrate():
                                if not design_state.field_definitions: return False
                                return all(f.name.strip() and f.example_value.strip() for f in design_state.field_definitions)

                            ui.button(t('common.back', 'Atrás'), icon='arrow_back', on_click=lambda: (setattr(design_state, 'phase', 'files'), layout_manager.update_step_index(0), render_design.refresh())).props('flat')
                            
                            if mode == 'generic':
                                async def run_generic():
                                    files = design_state.files_to_process
                                    if not files:
                                        ui.notify('No hay archivos para procesar.', type='warning')
                                        return
                                    
                                    exec_state.working = True
                                    exec_state.percent = 0
                                    exec_state.subphase_title = 'Iniciando extracción inteligente...'
                                    exec_state.error = None
                                    design_state.phase = 'PROCESSING'
                                    render_design.refresh()
                                    
                                    res = await state.extractor.process_files_generic(
                                        file_paths=files,
                                        on_progress=lambda e: update_progress(e, exec_state),
                                        target_fields=[f.name for f in design_state.field_definitions if f.name.strip()],
                                        recognize_all=generic_options.value['recognize_all'],
                                        top_k=generic_options.value['top_k']
                                    )
                                    exec_state.results = res.get('data', {})
                                    metadata = res.get('metadata', {})
                                    exec_state.privacy_stats = metadata.get('privacy_stats', {})
                                    exec_state.docs_text_list_anon = metadata.get('_docs_text_anon', getattr(exec_state, 'docs_text_list_anon', None))
                                    design_state.phase = 'results'
                                    render_design.refresh()
                                
                                ui.button(t('extraction.start_extraction', 'Comenzar extracción'), icon='rocket_launch', on_click=run_generic).props('color=primary').bind_enabled_from(design_state, 'field_definitions', backward=lambda x: any(f.name.strip() for f in x) or generic_options.value['recognize_all'])
                            else:
                                ui.button(t('extraction.calibrate_run', 'Programar script'), icon='code', on_click=lambda: (setattr(design_state, 'phase', 'run'), layout_manager.update_step_index(2), render_design.refresh())).props('color=primary').bind_enabled_from(design_state, 'field_definitions', backward=lambda x: _can_calibrate())

                elif phase == 'run':
                    # Renderizar panel de progreso
                    render_progress_panel()

                    # Ejecutar calibración
                    ui.timer(0.1, run_calibration, once=True)

                elif phase == 'PROCESSING':
                    # Renderizar panel de progreso para modo genérico (LLM)
                    render_phase_runner(exec_state)

                elif phase == 'summary':
                    # --- SUMMARY PHASE (Final step of wizard) ---
                    metadata = getattr(design_state, 'summary_metadata', {})
                    excel_path = getattr(design_state, 'summary_excel_path', None)
                    
                    fields_count = metadata.get('contract_fields_count', 0)
                    fields = metadata.get('contract_fields', [])
                    script_id = metadata.get('script_id')
                    readme_path = metadata.get('readme_path')
                    script_name = metadata.get('script_name', 'Robot de Extracción')
                    processed_count = metadata.get('processed_count', 0)
                    errors_count = metadata.get('errors', 0)
                    
                    if fields_count > 0:
                        fields_preview = ', '.join(fields[:3])
                        if fields_count > 3:
                            fields_preview += f', ... (+{fields_count - 3} más)'
                        contract_msg = t('extraction.detected_vars', 'Detectadas {count} variables: {preview}').format(count=fields_count, preview=fields_preview)
                    else:
                        contract_msg = t('extraction.no_input_vars', 'Sin variables de entrada detectadas')

                    with ui.card().classes('w-full p-8 items-center bg-white shadow-lg rounded-xl border border-slate-100 animate-fade-in'):
                        ui.icon('check_circle', size='80px', color='green').classes('mb-4')
                        ui.label(t('extraction.seal_applied', 'Script guardado con éxito')).classes('text-3xl font-black text-slate-800 text-center')
                        ui.label(t('extraction.save_success', '"{script_name}" guardado con éxito').format(script_name=script_name)).classes('text-lg text-slate-500 text-center mb-8')
                        
                        with ui.row().classes('w-full max-w-2xl gap-4'):
                            # Stats Card
                            with ui.card().classes('flex-1 p-4 bg-blue-50 border border-blue-100'):
                                ui.label(t('extraction.certified_schema', 'Esquema de extracción certificado:')).classes('text-xs font-bold text-blue-900 uppercase tracking-wider mb-2')
                                ui.label(contract_msg).classes('text-sm text-blue-800 font-medium')
                            
                            # Processing Card
                            if processed_count > 0:
                                with ui.card().classes('flex-1 p-4 bg-green-50 border border-green-100'):
                                    ui.label(t('extraction.processing_complete', 'Procesamiento completado')).classes('text-xs font-bold text-green-900 uppercase tracking-wider mb-2')
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('description', color='green', size='xs')
                                        ui.label(f'{processed_count} archivos procesados').classes('text-sm text-green-800 font-medium')
                                    if errors_count > 0:
                                        ui.label(t('extraction.errors_found', '({count} con errores)').format(count=errors_count)).classes('text-xs text-orange-600')

                        # Discreet LLM Warning (placed under stats)
                        ui.label("Los datos han sido generados mediante IA (LLM) y pueden contener errores. Se recomienda su revisión manual.").classes('text-xs text-slate-400 italic mt-2 text-center')

                        # Exported Results
                        if excel_path:
                            with ui.row().classes('w-full max-w-2xl items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200 mt-6'):
                                with ui.row().classes('items-center gap-3'):
                                    ui.icon('table_chart', color='green', size='md')
                                    with ui.column().classes('gap-0'):
                                        ui.label(t('extraction.results_exported', 'Resultados exportados:')).classes('text-xs font-bold text-slate-500 uppercase')
                                        ui.label(os.path.basename(excel_path)).classes('text-sm font-medium text-slate-800')
                                
                                with ui.row().classes('gap-2'):
                                    ui.button(t('extraction.open_excel', 'Abrir Excel'), on_click=lambda: open_file_natively(excel_path)).props('flat dense color=green icon=launch').classes('text-xs font-bold')
                                    ui.button(t('extraction.open_folder', 'Abrir carpeta'), on_click=lambda: open_folder_natively(excel_path)).props('flat dense color=blue icon=folder_open').classes('text-xs font-bold')

                        with ui.row().classes('w-full max-w-2xl justify-center gap-6 mt-10 pt-6 border-t border-slate-100'):
                            if readme_path:
                                ui.button(t('extraction.view_docs', 'Ver Documentación / Contrato'), icon='description', on_click=lambda: show_documentation_modal(readme_path, script_name)).props('outline color=blue').classes('px-6 py-2')
                            
                            is_flow = state.flow_context is not None and state.flow_context.get('mode') == 'contextual'
                            if is_flow:
                                async def on_continue_summary():
                                    from client_app.app.core.state import app_state
                                    if app_state.flow_context and app_state.flow_context.get('mode') == 'contextual':
                                        step = app_state.flow_context.get('step')
                                        if step and script_id:
                                            step.config['config_id'] = script_id
                                            step.config['script_id'] = script_id
                                            if app_state.editing_flow and hasattr(app_state.editing_flow, 'steps'):
                                                app_state.refresh_flow_context_steps(app_state.editing_flow.steps)
                                            if hasattr(app_state, 'on_step_change') and callable(app_state.on_step_change):
                                                app_state.on_step_change()
                                    ui_emit('atom_created', {'id': script_id})
                                    ui_emit('refresh_flow_step', script_id)
                                    go_to_library()
                                
                                ui.button(t('extraction.continue_flow', 'Continuar al Flujo'), icon='check', on_click=on_continue_summary).props('color=primary').classes('px-8 py-2 font-bold')
                            else:
                                ui.button(t('extraction.test_robot', 'Ejecutar script sobre nuevo lote'), icon='play_arrow', on_click=lambda: ui.navigate.to(f'/execution/{script_id}')).props('color=primary').classes('px-8 py-2 font-bold')

                elif phase == 'results':
                    # Results and Seal (Original lines 534-678)
                    with ui.column().classes('w-full gap-4'):
                        ui.label(t('extraction.calibration_results', 'Resultados de calibración')).classes('text-2xl font-bold text-primary')

                        # Privacy Report if generic
                        if mode == 'generic':
                            render_privacy_report(exec_state.privacy_stats)

                        # Validation Report Table with Expected vs Obtained comparison
                        if exec_state.validation_report:
                            # Filter only dict values (skip metadata like 'accepted_with_warnings')
                            field_reports = {k: v for k, v in exec_state.validation_report.items() if isinstance(v, dict)}
                            total = len(field_reports) if field_reports else 0
                            valid_count = sum(1 for v in field_reports.values() if v.get('valid')) if field_reports else 0
                            all_valid = valid_count == total and total > 0

                            border_color = 'border-green-500' if all_valid else 'border-orange-500'
                            with ui.card().classes(f'w-full p-4 mb-4 border-l-4 {border_color}'):
                                with ui.row().classes('w-full justify-between items-center mb-3'):
                                    ui.label(t('extraction.validation_report', 'Informe de validación')).classes('text-lg font-bold text-slate-800')
                                    status_class = 'text-green-700 bg-green-100' if all_valid else 'text-orange-700 bg-orange-100'
                                    ui.label(f'{valid_count}/{total} campos válidos').classes(f'text-sm font-semibold px-3 py-1 rounded-full {status_class}')

                                # Tabla comparativa: Esperado vs Obtenido
                                rows = []
                                has_doc2 = hasattr(exec_state, 'batch_results') and len(exec_state.batch_results) > 1
                                for fd in design_state.field_definitions:
                                    report = field_reports.get(fd.name, {})
                                    expected = fd.example_value[:80] + '...' if len(fd.example_value) > 80 else fd.example_value
                                    obtained = str(report.get('value', '')) if isinstance(report, dict) else ''
                                    obtained_display = obtained[:80] + '...' if len(obtained) > 80 else obtained
                                    is_valid = report.get('valid', False) if isinstance(report, dict) else False
                                    
                                    row_data = {
                                        'field': fd.name,
                                        'expected': expected,
                                        'obtained': obtained_display,
                                        'status': '✓' if is_valid else '✗'
                                    }
                                    
                                    if has_doc2:
                                        doc2_raw = str(exec_state.batch_results[1].get(fd.name, ''))
                                        row_data['doc2_obtained'] = doc2_raw[:80] + '...' if len(doc2_raw) > 80 else doc2_raw
                                        
                                    rows.append(row_data)

                                table_cols = [
                                    {'name': 'field', 'label': t('common.field', 'Campo'), 'field': 'field', 'align': 'left'},
                                    {'name': 'expected', 'label': 'Esperado (Doc 1)', 'field': 'expected', 'align': 'left'},
                                    {'name': 'obtained', 'label': 'Obtenido (Doc 1)', 'field': 'obtained', 'align': 'left'},
                                    {'name': 'status', 'label': 'Val. 1', 'field': 'status', 'align': 'center'}
                                ]
                                
                                if has_doc2:
                                    table_cols.append({'name': 'doc2_obtained', 'label': 'Obtenido (Doc 2)', 'field': 'doc2_obtained', 'align': 'left'})

                                ui.table(
                                    columns=table_cols,
                                    rows=rows,
                                    pagination={'rowsPerPage': 0}
                                ).classes('w-full sticky-header').props('dense flat bordered')

                        with ui.expansion(t('extraction.view_json', 'Ver datos JSON completos'), icon='code').classes('w-full'):
                            # Mostrar todos los resultados si es un lote (batch_results)
                            json_to_show = exec_state.results
                            if has_doc2 and exec_state.batch_results:
                                # Si hay múltiples resultados, mostramos la lista completa de resultados exitosos
                                if isinstance(exec_state.batch_results, list):
                                    json_to_show = exec_state.batch_results
                                elif isinstance(exec_state.batch_results, dict) and 'batch_results' in exec_state.batch_results:
                                    json_to_show = exec_state.batch_results['batch_results']
                            
                            ui.json_editor({'content': {'json': json_to_show}}).classes('w-full h-64')

                        # Resultados limpios en tabla (solo para modo genérico o cuando no hay informe de validación)
                        # En modo factory, la tabla de validación con Esperado/Obtenido ya muestra toda la info necesaria.
                        _show_results_table = mode == 'generic' or not exec_state.validation_report
                        results_data = exec_state.results
                        # Si es una lista (modo lote), tomamos el primero para previsualización
                        if isinstance(results_data, list) and len(results_data) > 0:
                            results_data = results_data[0]
                        
                        if _show_results_table and isinstance(results_data, dict) and results_data:
                            with ui.expansion(t('extraction.results_table', 'Tabla de resultados extraídos'), icon='table_view', value=True).classes('w-full bg-slate-50 border border-slate-200 rounded'):
                                generic_rows = []
                                for k, v in results_data.items():
                                    # Limpiar valor si es un diccionario (ej: {'valor': '...', 'pagina': 1})
                                    display_val = v
                                    if isinstance(v, dict):
                                        display_val = v.get('valor', str(v))
                                    generic_rows.append({'campo': k, 'valor': str(display_val)})
                                
                                ui.table(
                                    columns=[
                                        {'name': 'campo', 'label': t('common.field', 'Campo'), 'field': 'campo', 'align': 'left', 'classes': 'font-bold'},
                                        {'name': 'valor', 'label': t('common.value', 'Valor'), 'field': 'valor', 'align': 'left'}
                                    ],
                                    rows=generic_rows,
                                    pagination={'rowsPerPage': 0}
                                ).classes('w-full sticky-header').props('dense flat')

                        # Discreet LLM Warning (placed under results table)
                        ui.label("Los datos han sido generados mediante IA (LLM) y pueden contener errores. Se recomienda su revisión manual.").classes('text-xs text-slate-400 italic mt-4 text-center')

                        # Forensic Audit (Análisis de Calidad y Consistencia)
                        if exec_state.audit_report:
                            with ui.expansion(t('extraction.forensic_audit', 'Análisis de Calidad y Consistencia'), icon='fact_check').classes('w-full bg-blue-50 border border-blue-100 rounded'):
                                report = exec_state.audit_report
                                if isinstance(report, dict):
                                    report = report.get('report', str(report))
                                ui.markdown(report).classes('p-4 text-sm text-slate-800')

                        # === LÓGICA DE BOTONES SEGÚN NIVEL DE ÉXITO ===
                        # Calcular porcentaje de éxito
                        # Filter only dict values to get actual field validations
                        _field_reports = {k: v for k, v in exec_state.validation_report.items() if isinstance(v, dict)} if exec_state.validation_report else {}

                        # Si validation_report está vacío pero tenemos resultados, generarlo dinámicamente
                        if not _field_reports and exec_state.results and design_state.field_definitions:
                            for fd in design_state.field_definitions:
                                extracted_val = exec_state.results.get(fd.name, '')
                                # Validar: tiene valor y no está vacío
                                has_value = bool(extracted_val) and str(extracted_val).strip() != ''
                                _field_reports[fd.name] = {
                                    'valid': has_value,
                                    'value': extracted_val,
                                    'source': 'auto-generated'
                                }

                        total_fields = len(_field_reports) if _field_reports else len(design_state.field_definitions or [])
                        valid_fields = sum(1 for v in _field_reports.values() if v.get('valid'))
                        success_rate = (valid_fields / total_fields * 100) if total_fields > 0 else 100  # Default 100% si no hay campos

                        # Determinar nivel de éxito (solo informativo, no bloquea)
                        is_partial = success_rate < 100
                        is_perfect = success_rate == 100

                        # Generar nombre provisional
                        prov_name = naming_service.provisional_name(
                            StepType.EXTRACTION,
                            {'fields': [fd.name for fd in design_state.field_definitions]}
                        )

                        # Dialog de guardar (solo se usa si success_rate >= 60%)
                        with ui.dialog() as save_dialog, ui.card().classes('p-6 min-w-[300px]'):
                            ui.label(t('extraction.save_as_action', 'Guardar como Acción')).classes('text-lg font-bold mb-4')
                            save_name_input = ui.input(t('extraction.action_name', 'Nombre de la acción'), value=prov_name).props('outlined autofocus').classes('w-full mb-4')

                            # Advertencia si no es 100%
                            if is_partial:
                                with ui.row().classes('w-full items-center gap-2 p-3 bg-orange-50 rounded mb-4'):
                                    ui.icon('warning', color='orange').classes('text-xl')
                                    ui.label(f'El script tiene {valid_fields}/{total_fields} campos válidos ({success_rate:.0f}%). Algunos datos pueden requerir revisión manual.').classes('text-sm text-orange-800')

                            async def confirm_save(btn):
                                if getattr(save_dialog, '_is_saving', False): return
                                save_dialog._is_saving = True
                                btn.props('loading')
                                try:
                                    # Resolver archivos desde el directorio inputs del execution context
                                    valid_files = []
                                    if design_state.execution_id:
                                        input_dir = state.extractor.path_manager.get_input_dir(design_state.execution_id)
                                        if input_dir.exists():
                                            valid_files = [str(f) for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']

                                    if not valid_files:
                                        valid_files = [f for f in design_state.files_to_process if Path(f).exists()]

                                    if not valid_files:
                                        ui.notify("No se encontraron archivos válidos para procesar", type='negative')
                                        save_dialog.close()
                                        render_design.refresh()
                                        return

                                    print(f"[UI] Calling deploy_and_execute_batch with {len(valid_files)} files")
                                    print(f"[UI] execution_id={design_state.execution_id}, service_name={save_name_input.value}")
                                    print(f"[UI] first_file_result keys: {exec_state.results.keys() if exec_state.results else 'None'}")

                                    if design_state.mode == 'generic':
                                        # Hacemos transición de UI para mostrar el progreso, al igual que en la rama 'run'
                                        design_state.phase = 'PROCESSING'
                                        exec_state.working = True
                                        save_dialog.close()
                                        render_design.refresh()

                                        # Para batch execution en generic mode, 'deploy_and_execute_batch'
                                        # detecta que no hay script_code y llama a 'deploy_generic_action'
                                        # y luego 'process_batch_with_llm' automáticamente.
                                        res = await state.extractor.deploy_and_execute_batch(
                                            execution_id=design_state.execution_id,
                                            service_name=save_name_input.value,
                                            script_code="", # No script needed for Generic Action
                                            all_files=valid_files,
                                            first_file_result=exec_state.results,
                                            description=getattr(design_state, '_accumulated_feedback', "Acción Genérica"),
                                            field_definitions=design_state.field_definitions,
                                            on_progress=lambda e: update_progress(e, exec_state)
                                        )
                                    else:
                                        res = await state.extractor.deploy_and_execute_batch(
                                            execution_id=design_state.execution_id,
                                            service_name=save_name_input.value,
                                            script_code=design_state._last_script,
                                            all_files=valid_files,
                                            first_file_result=exec_state.results,
                                            field_definitions=design_state.field_definitions,
                                            on_progress=lambda e: update_progress(e, exec_state)
                                        )
                                    print(f"[UI] deploy_and_execute_batch returned: status={res.get('status')}, processed={res.get('processed_count')}, excel={res.get('excel_path')}")

                                    if res.get('status') == 'success':
                                        ui.notify(t('extraction.service_sealed', 'Servicio sellado'), type='positive')

                                        # Cargar servicios sin refrescar la página (para no interferir con el diálogo)
                                        print("[UI] Loading deterministic services (without page refresh)...")
                                        services = await state.extractor.get_all_user_configs()
                                        page_state.deterministic_services = [
                                            {'service_id': s['service_id'], 'name': s['name'], 'description': s['description'], 'status': s.get('status', 'published'), 'created_at': s.get('created_at')}
                                            for s in services
                                        ]
                                        print(f"[UI] Loaded {len(page_state.deterministic_services)} services")

                                        # Mostrar diálogo de éxito con Excel y documentación
                                        library_script_id = res.get('library_script_id')
                                        print(f"[UI] library_script_id={library_script_id}")

                                        # Advertir si no se registró en la biblioteca
                                        if not library_script_id:
                                            ui.notify('⚠️ El script se guardó localmente pero no se registró en la biblioteca. Revisa los logs.', type='warning', timeout=8000)

                                        is_flow = state.flow_context is not None and state.flow_context.get('mode') == 'contextual'
                                        print(f"[UI] is_flow={is_flow}")

                                        # Construir metadata para el diálogo de éxito
                                        seal_metadata = {
                                            'script_id': library_script_id,
                                            'script_name': save_name_input.value,
                                            'contract_fields_count': len(design_state.field_definitions) if design_state.field_definitions else 0,
                                            'contract_fields': [fd.name for fd in design_state.field_definitions] if design_state.field_definitions else [],
                                            'readme_path': res.get('readme_path'),
                                            'processed_count': res.get('processed_count', 0),
                                            'errors': res.get('errors', 0)
                                        }
                                        print(f"[UI] Calling show_extraction_seal_success with metadata: {seal_metadata}")
                                        print(f"[UI] excel_path: {res.get('excel_path')}")
                                        save_dialog.close()
                                        await show_extraction_seal_success(seal_metadata, is_flow, res.get('excel_path'))
                                        print("[UI] show_extraction_seal_success completed")

                                        # NOTA: No navegamos automáticamente - el diálogo tiene botones para eso
                                        # El usuario decidirá cuándo continuar
                                    else:
                                        save_dialog.close()
                                        ui.notify(f"Error procesando lote: {res.get('error')}", type='negative')
                                        render_design.refresh()
                                except Exception as e:
                                    save_dialog.close()
                                    import traceback
                                    print(f"[UI] Exception in confirm_save: {e}")
                                    traceback.print_exc()
                                    ui.notify(f"Excepción en lote: {e}", type='negative')
                                    render_design.refresh()
                                finally:
                                    save_dialog._is_saving = False
                                    btn.props(remove='loading')

                            with ui.row().classes('w-full justify-end gap-2'):
                                ui.button(t('common.cancel', 'Cancelar'), on_click=save_dialog.close).props('flat')
                                seal_btn = ui.button(t('extraction.seal_action', 'Aprobar y sellar'), on_click=lambda e: confirm_save(e.sender)).props('color=primary')

                        # === RENDERIZAR BOTONES (siempre permite guardar) ===
                        # Mensaje informativo según nivel de éxito
                        if is_partial:
                            bg_color = 'bg-orange-50' if success_rate >= 60 else 'bg-yellow-50'
                            border_color = 'border-orange-200' if success_rate >= 60 else 'border-yellow-200'
                            text_color = 'text-orange-800' if success_rate >= 60 else 'text-yellow-800'
                            with ui.card().classes(f'w-full p-4 {bg_color} border {border_color} mb-4'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('info', color='orange').classes('text-2xl')
                                    ui.label(f'Éxito parcial ({success_rate:.0f}%)').classes(f'text-lg font-bold {text_color}')
                                ui.label('Puedes guardar el script o intentar mejorarlo con las opciones disponibles.').classes(f'text-sm {text_color} mt-2')

                        # Instrucciones adicionales de refinamiento (Siempre visible)
                        with ui.card().classes('w-full p-4 bg-slate-50 border border-slate-200 mb-2'):
                            ui.label(t('extraction.refine_instructions', 'Instrucciones para mejorar el resultado (HITL)')).classes('text-sm font-bold text-slate-700 mb-2')
                            refine_feedback_input = ui.textarea(
                                placeholder='Ej: "El nombre completo incluye dos apellidos", "Ignora el texto en mayúsculas"...'
                            ).classes('w-full').props('outlined rows=2').bind_value(exec_state, 'refinement_feedback')
                            ui.label('Indique qué aspectos no son correctos o cómo mejorar la lógica para otros documentos.').classes('text-xs text-slate-500 mt-1')

                        # Botones de acción
                        with ui.row().classes('w-full justify-center gap-4 p-4 rounded'):
                            ui.button(t('extraction.save_as_action', 'Guardar como Acción'), icon='verified', on_click=save_dialog.open).props('color=primary')
                            
                            # Refinar/Regenerar siempre visibles a petición del usuario
                            ui.button(t('extraction.refine_with_feedback', 'Refinar con instrucciones adicionales'), icon='auto_fix_high', on_click=run_refinement).props('outline color=orange')
                            ui.button(t('extraction.regenerate', 'Reintentar la programación'), icon='refresh', on_click=lambda: (setattr(design_state, 'phase', 'run'), layout_manager.update_step_index(2), render_design.refresh())).props('outline color=primary')
                            
                            if is_partial:
                                ui.button(t('extraction.try_llm', 'Extraer mediante LLM (fallback)'), icon='psychology', on_click=try_llm_fallback).props('outline color=primary')
                            
                            ui.button(t('extraction.back_to_definition', 'Regresar a definición'), icon='edit', on_click=lambda: (setattr(design_state, 'phase', 'definition'), layout_manager.update_step_index(1), render_design.refresh())).props('flat')
    
    # ========================================================================
    # EXECUTION MODE (Continuará en siguiente parte...)
    # ========================================================================
    
    @ui.refreshable
    def render_execution():
        """Renderiza el modo de ejecución (Batch Runner)."""
        with ui.column().classes('w-full p-0 max-w-5xl mx-auto'):
            # Header with Back Arrow next to title
            with ui.row().classes('w-full items-center gap-4 mb-6 mt-4 px-4 bg-white sticky top-0 z-10 py-2 border-b'):
                ui.button(icon='arrow_back', on_click=go_to_library).props('flat round').classes('text-gray-600')
                with ui.column().classes('gap-0'):
                    ui.label(t('extraction.execution_title', 'Ejecutor de extractor')).classes('text-2xl font-bold text-primary')
                    ui.label(t('extraction.execution_subtitle', 'Procesa documentos en lote utilizando el extractor configurado')).classes('text-sm text-slate-500')
            
            # Sub-phases: 'upload' -> 'running' -> 'results'
            if not getattr(exec_state, 'run_phase', None): exec_state.run_phase = 'upload'
            
            with ui.column().classes('w-full px-4 items-center'):
                if exec_state.run_phase == 'upload':
                    with ui.card().classes('w-full max-w-4xl p-6'):
                        ui.label(t('extraction.select_files', 'Seleccione archivos para procesar')).classes('font-bold mb-4')
                        
                        async def handle_source_selection(selection: DataSourceSelection):
                            """Maneja la selección de fuente de datos."""
                            exec_state.data_source = selection
                            
                            if selection.source_type == 'manual':
                                if not exec_state.execution_id:
                                    exec_state.execution_id = state.extractor.path_manager.create_execution_context(task_type='PDF_EXTRACTION')
                                
                                if selection.file_content and selection.file_name:
                                    file_path = state.extractor.path_manager.get_input_dir(exec_state.execution_id) / selection.file_name
                                    with open(file_path, 'wb') as f:
                                        f.write(selection.file_content)
                                    
                                    if str(file_path) not in exec_state.files_to_process:
                                        exec_state.files_to_process.append(str(file_path))
                            
                            render_execution.refresh()
                            
                        # Configurar callback para que UI se refresque cuando los datos del preview lleguen desde la BBDD o el catálogo
                        exec_state.data_source_selector_state.on_preview_loaded = render_execution.refresh

                        render_data_source_selector(
                            consumer_type=StepType.EXTRACTION,
                            on_source_selected=handle_source_selection,
                            flow_context=state.flow_context,
                            initial_selection=exec_state.data_source,
                            upload_formats_override=['pdf'],
                            selector_state_override=exec_state.data_source_selector_state
                        )
                        
                        preview_files = []
                        if exec_state.data_source and exec_state.data_source.source_type in ('flow_step', 'catalog'):
                            preview_files = extract_files_from_preview(exec_state)

                        files_to_show = exec_state.files_to_process or preview_files
                        
                        if files_to_show:
                            with ui.card().classes('w-full p-4 border border-slate-200 mt-4'):
                                with ui.row().classes('items-center gap-2 mb-3'):
                                    ui.icon('folder_open', color='primary')
                                    source_label = exec_state.data_source.atom_name if (exec_state.data_source and getattr(exec_state.data_source, 'atom_name', None)) else "fuente seleccionada"
                                    ui.label(f'{len(files_to_show)} archivo(s) PDF de {source_label}').classes('font-bold text-slate-800')

                                with ui.column().classes('w-full gap-1 max-h-64 overflow-y-auto'):
                                    for file_path in files_to_show[:8]:
                                        file_name = file_path.split('\\')[-1].split('/')[-1] if isinstance(file_path, str) else str(file_path)
                                        with ui.row().classes('w-full items-center justify-between p-2 rounded bg-slate-50 border-slate-200 border'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon('picture_as_pdf', color='red')
                                                ui.label(file_name).classes('text-sm font-semibold truncate max-w-[300px]')
                                                
                                    if len(files_to_show) > 8:
                                        ui.label(f'... y {len(files_to_show) - 8} archivos más').classes('text-xs text-slate-500 italic ml-8 mt-1')

                        with ui.row().classes('w-full justify-end mt-6'):
                            async def start_batch():
                                exec_state.run_phase = 'running'
                                final_files = exec_state.files_to_process
                                if not final_files and exec_state.data_source and exec_state.data_source.source_type in ('flow_step', 'catalog'):
                                    final_files = extract_files_from_preview(exec_state)
                                
                                render_execution.refresh()
                                res = await state.extractor.execute_batch_background(
                                    service_id=exec_state.service_id,
                                    files=final_files,
                                    on_progress=lambda e: update_progress(e, exec_state)
                                )
                                exec_state.batch_results = res
                                exec_state.run_phase = 'results'
                                render_execution.refresh()
                                
                            ui.button(t('extraction.run_batch', 'Ejecutar lote'), icon='play_arrow', on_click=start_batch).props('color=primary').set_enabled(len(files_to_show) > 0)
            
                elif exec_state.run_phase == 'running':
                    # Use phase runner defined in Design
                    render_phase_runner(exec_state)
                    
                elif exec_state.run_phase == 'results':
                    results_data = exec_state.batch_results or {}
                    if results_data.get('status') == 'error':
                        with ui.card().classes('w-full p-8 items-center bg-white shadow-lg rounded-xl border border-red-100 animate-fade-in'):
                            ui.icon('error', size='80px', color='red').classes('mb-4')
                            ui.label(t('extraction.processing_error', 'Error en el procesamiento')).classes('text-2xl font-bold text-red-700 mb-2')
                            ui.label(results_data.get('error', 'Error desconocido')).classes('text-red-600 text-center')
                            ui.button(t('common.back', 'Volver'), on_click=lambda: setattr(exec_state, 'run_phase', 'upload')).props('flat')
                    else:
                        # Rich Results UI (Mirrors summary phase from design)
                        batch_list = results_data.get('batch_results', [])
                        processed_count = len(batch_list)
                        success_count = sum(1 for r in batch_list if r.get('status') == 'OK')
                        errors_count = processed_count - success_count
                        excel_path = results_data.get('excel_path')
                        
                        # Get service name for the banner
                        services = page_state.deterministic_services or []
                        service_name = next((s['name'] for s in services if str(s['service_id']) == str(exec_state.service_id)), 'Extractor')

                        with ui.card().classes('w-full p-4 items-center bg-white shadow-md rounded-xl border border-slate-100 animate-fade-in'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('check_circle', size='32px', color='green')
                                ui.label(t('extraction.processing_complete', 'Procesamiento completado')).classes('text-xl font-bold text-slate-800')
                            
                            ui.label(t('extraction.batch_success_msg', 'El lote se ha procesado utilizando "{name}"').format(name=service_name)).classes('text-sm text-slate-500 text-center mb-4')
                            
                            with ui.row().classes('w-full max-w-2xl gap-3'):
                                # Service/Extractor Card
                                with ui.card().classes('flex-1 p-3 bg-blue-50 border border-blue-100 shadow-none'):
                                    ui.label(t('extraction.extractor_used', 'Extractor utilizado')).classes('text-[10px] font-bold text-blue-900 uppercase tracking-wider mb-1')
                                    ui.label(service_name).classes('text-sm text-blue-800 font-medium')
                                
                                # Processing Card
                                with ui.card().classes('flex-1 p-3 bg-green-50 border border-green-100 shadow-none'):
                                    ui.label(t('extraction.execution_summary', 'Resumen de ejecución')).classes('text-[10px] font-bold text-green-900 uppercase tracking-wider mb-1')
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('description', color='green', size='xs')
                                        ui.label(f'{processed_count} archivos').classes('text-sm text-green-800 font-medium')
                                    if errors_count > 0:
                                        ui.label(f'({errors_count} con errores)').classes('text-[10px] text-orange-600')

                            # Discreet LLM Warning
                            ui.label("Los datos han sido generados mediante IA (LLM) y pueden contener errores. Se recomienda su revisión manual.").classes('text-xs text-slate-400 italic mt-2 text-center')

                            # Exported Results
                            if excel_path:
                                with ui.row().classes('w-full max-w-2xl items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 mt-4'):
                                    with ui.row().classes('items-center gap-3'):
                                        ui.icon('table_chart', color='green', size='sm')
                                        with ui.column().classes('gap-0'):
                                            ui.label(t('extraction.results_exported', 'Resultados exportados:')).classes('text-[10px] font-bold text-slate-500 uppercase')
                                            ui.label(os.path.basename(excel_path)).classes('text-xs font-medium text-slate-800 truncate max-w-[300px]')
                                    
                                    with ui.row().classes('gap-2'):
                                        ui.button(t('extraction.open_excel', 'Abrir Excel'), on_click=lambda: open_file_natively(excel_path)).props('flat dense color=green icon=launch').classes('text-[11px] font-bold')
                                        ui.button(t('extraction.open_folder', 'Abrir carpeta'), on_click=lambda: open_folder_natively(excel_path)).props('flat dense color=blue icon=folder_open').classes('text-[11px] font-bold')
                            else:
                                with ui.card().classes('w-full max-w-2xl p-3 bg-yellow-50 border border-yellow-200 mt-4 items-center shadow-none'):
                                    ui.label("No se generó archivo de resultados.").classes('text-xs text-yellow-800 italic')

                            # Footer Actions
                            with ui.row().classes('w-full max-w-2xl justify-center mt-6 pt-4 border-t border-slate-100'):
                                ui.button(t('common.finish', 'Finalizar'), icon='done_all', on_click=go_to_library).props('color=primary outline size=sm').classes('px-6 py-1 font-bold')
    
    # ========================================================================
    # MAIN RENDER
    # ========================================================================
    
    def render_flow_context_banner():
        """Muestra banner cuando se está configurando un paso desde un flujo."""
        if not state.flow_context or state.flow_context.get('mode') != 'contextual':
            return

        flow_name = state.flow_context.get('flow_name', 'Flujo')
        step = state.flow_context.get('step')
        step_name = step.name if step else 'Paso'
        step_index = state.flow_context.get('step_index', 0) + 1
        available_vars = state.flow_context.get('available_variables', [])

        with ui.card().classes('w-full bg-gradient-to-r from-blue-500 to-blue-600 text-white p-3 mb-4 shadow-md'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('account_tree', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label(f'Configurando paso {step_index}: {step_name}').classes('font-bold text-sm')
                        ui.label(f'Flujo: {flow_name}').classes('text-xs opacity-80')

                with ui.row().classes('items-center gap-2'):
                    if available_vars:
                        with ui.button(icon='data_object').props('flat dense text-color=white').classes('text-xs'):
                            ui.tooltip(f'{len(available_vars)} variables disponibles de pasos anteriores')
                    ui.button('Volver al Flujo', icon='arrow_back', on_click=go_to_library).props('flat text-color=white')

    @ui.refreshable
    def render_page():
        """Renderiza la página según el modo actual."""
    # --- INITIALIZATION ---

    # 1. IMMEDIATE LAYOUT SETUP (sync) to avoid flicker/leakage
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.EXTRACTION, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif initial_mode == 'design':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.EXTRACTION, from_flow=False)
        design_state.user_instructions = naming_service.generate_provisional_name(StepType.EXTRACTION)
    elif initial_mode == 'execution' and atom_id:
        page_state.current_mode = 'execution'
        exec_state.service_id = atom_id
        layout_manager.enter_execution_mode(atom_id)
    else:
        # Default to library: EXPLICITLY exit focus mode to clear leakage from other pages
        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()

    # Singleton-like guard for the content within the same client call
    if hasattr(ui.context.client, '_extraction_rendered'):
        return
    ui.context.client._extraction_rendered = True

    # Si hay config_id del flujo, cargar el extractor
    if flow_config_id:
        await edit_extractor(str(flow_config_id))

    # Use a persistent main container for this instance
    main_container = ui.column().classes('w-full p-6')

    @ui.refreshable
    def render_page():
        main_container.clear()
        with main_container:
            if page_state.current_mode == 'library':
                render_library()
            elif page_state.current_mode == 'design':
                render_design()
            elif page_state.current_mode == 'execution':
                render_execution()

    render_page()
