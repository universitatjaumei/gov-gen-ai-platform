from nicegui import ui, app
import pandas as pd
import io
import asyncio
import base64
import os
import json
import re
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime
from uuid import uuid4
from pathlib import Path

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.form_factory import FormFactory, FormContext, AtomColorScheme
from client_app.app.ui.components.privacy_indicator import render_privacy_indicator
from client_app.app.ui.components.privacy_report import render_privacy_report
from client_app.app.services.clarification_service import clarification_service, ClarificationResponse, ClarificationResult
from client_app.app.ui.components.clarification_dialog import ClarificationDialog, show_clarification_dialog
from client_app.app.services.asset_finishing_service import AssetFinishingService
from client_app.app.services.etl_service import ETLService
from client_app.app.services.flow_registry_service import FlowRegistryService
from client_app.app.database.models import ScriptLibrary, ETLJobHistory
from client_app.app.ui.components.unified_resource_card import unified_resource_card
from client_app.app.ui.components.data_source_selector import render_data_source_selector, DataSourceSelection, DataSourceSelectorState
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.models.transform_operations import (
    TransformOperation, DropColumnsOperation, RenameColumnsOperation,
    MergeColumnsOperation, FormatDatesOperation, FilterRowsOperation,
    ReplaceValuesOperation, NormalizeTextOperation, FillNullsOperation,
    RemoveDuplicatesOperation, RemoveNullRowsOperation
)
from client_app.app.utils.etl_utils import detect_potential_operations
from automatia_shared.enums import StepType
from client_app.app.services.naming_service import naming_service


# --- CONSTANTS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ETL_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads" / "etl"
ETL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- STATE CLASSES ---

class ETLState:
    """Estado global de la página de ETL."""
    def __init__(self):
        self.current_mode = 'library'  # 'library', 'design', 'execution'
        self.selected_etl_id = None
        self.saved_etls: List[ScriptLibrary] = []
        self.search_query = ""

class ETLDesignState:
    """Estado reactivo del asistente de ETL (Diseño)."""
    def __init__(self):
        self.phase = 'upload'  # upload, spec, clarification, config, preview, results
        self.execution_id = None
        self.source_file = None
        self.source_format = None
        self.source_preview = None
        self.source_info = {}
        # Fuente de datos seleccionada (DataSourceSelector)
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()
        self.filename = None
        self.target_spec_mode = 'description'
        self.target_spec = None
        self.target_format = 'csv'
        self.user_instructions = ""
        self.example_file = None
        self.example_preview = None
        self.generated_script = None
        self.result_data = None
        
        # Mode & Operations (Phase 2)
        self.transformation_mode = 'assisted'  # 'assisted' (default), 'ai'
        self.operations: List[Dict[str, Any]] = []
        self.current_operation_editor: Optional[Dict[str, Any]] = None
        
        # Intelligent Warnings
        self.suggested_ops: List[Dict[str, str]] = []
        self.show_suggestion: bool = False
        
        # UI Control
        self.is_analyzing = False
        self.is_generating = False
        self.is_sealing = False
        
        # Config
        self.clean_duplicates = False
        self.remove_nulls = False
        self.normalize_fields = False
        self.additional_instructions = ""
        
        # Anonymization
        self.enable_anonymization = False
        self.anon_mode = 'FAKER'
        self.anon_use_aepd = False
        self.anon_col_map = {}
        
        # Clarification
        self.clarification_result: Optional[ClarificationResult] = None
        self.clarification_responses: List[ClarificationResponse] = []
        self.clarification_skipped = False
        
        # Results
        self.execution_stats = {}
        self.output_file = None
        self.privacy_stats = {}
        
        # Clarification
        self.clarification_result: Optional[ClarificationResult] = None
        self.clarification_responses: List[ClarificationResponse] = []
        self.clarification_skipped = False
        self.stepper = None
        
        self.wizard_op_type = None
        self.wizard_form_container = None
        self.is_readonly = False

    def reset(self):
        self.__init__()

class ETLExecutionState:
    """Estado específico para el modo ejecución de ETL."""
    def __init__(self):
        self.script_entry: Optional[ScriptLibrary] = None
        self.source_file: Optional[pd.DataFrame] = None
        self.filename: Optional[str] = None
        self.is_running = False
        self.execution_result = None
        self.output_file_path = None


def _update_global_data_context(df: pd.DataFrame) -> None:
    """
    Actualiza el contexto de datos global para que el Copiloto conozca las columnas.
    Debe llamarse cada vez que se carga un nuevo DataFrame.
    """
    if df is None or df.empty:
        state.current_data_context = None
        return

    # Obtener valores de ejemplo (2-3 valores únicos por columna)
    sample_values = {}
    for col in df.columns:
        try:
            unique_vals = df[col].dropna().unique()[:3]
            sample_values[col] = [str(v)[:50] for v in unique_vals]
        except Exception:
            sample_values[col] = []

    state.current_data_context = {
        'columns': list(df.columns),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'row_count': len(df),
        'sample_values': sample_values
    }


# --- PAGE CONTENT ---

async def etl_page_content(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    """
    Controlador refactorizado de la página de ETL.
    Arquitectura de tres modos: Library, Design, Execution.
    Identidad Visual: Verde (📊).
    """
    from client_app.app.services.naming_service import naming_service
    t = state.i18n.t
    
    # Persistent page state
    page_state = ETLState()
    design_state = ETLDesignState()
    exec_state = ETLExecutionState()

    # --- INITIAL LAYOUT SETUP ---
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.ETL_TRANSFORM, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
            script_id = step.config.get('script_id')

            # Cargar operaciones existentes si hay script_id guardado
            if script_id:
                try:
                    async with state.db_session() as session:
                        script = await session.get(ScriptLibrary, int(script_id))
                        if script and script.source_metadata:
                            design_state.operations = script.source_metadata.get("operations", [])
                            design_state.target_format = script.source_metadata.get("target_format", 'csv')
                            design_state.transformation_mode = 'assisted'
                            design_state.phase = 'spec'
                            update_drawer_stepper()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"No se pudo cargar config ETL existente: {e}")
    elif initial_mode == 'design':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.ETL_TRANSFORM, from_flow=False)
        design_state.user_instructions = naming_service.generate_provisional_name(StepType.ETL_TRANSFORM)
        update_drawer_stepper()
    elif initial_mode == 'execution':
        page_state.current_mode = 'execution'
        if atom_id:
            page_state.selected_etl_id = atom_id
        # No drawer in execution
    else:
        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()

    # --- COPILOT ACTIVE INTEGRATION ---
    async def apply_etl_operations(ops: List[Dict]):
        """Aplica una propuesta de operaciones ETL del Copiloto."""
        # Se agregan al final de la lista de operaciones
        for op in ops:
            # Asegurar que el type en UI coincide con los keys de OP_TYPES
            # Copilot service ya envía los format correctos, pero por seguridad
            if 'type' in op:
                design_state.operations.append(op)
        
        # En diseño manual refrescamos y notificamos
        if design_state.transformation_mode != 'assisted':
            design_state.transformation_mode = 'assisted'
            
        if design_state.source_preview is None:
            if design_state.data_source and design_state.data_source.source_type in ['catalog', 'flow_step']:
                if hasattr(design_state, 'data_source_selector_state') and design_state.data_source_selector_state.preview_data:
                    design_state.source_preview = design_state.data_source_selector_state.preview_data.to_dataframe()
                    if design_state.source_preview is not None:
                        design_state.source_info = {
                            'name': design_state.data_source.step_name or design_state.data_source.atom_name or 'datos_preview',
                            'rows': len(design_state.source_preview),
                            'columns': len(design_state.source_preview.columns),
                            'column_names': list(design_state.source_preview.columns)
                        }
                        _update_global_data_context(design_state.source_preview)

        design_state.phase = 'spec'
        update_drawer_stepper()
        
        ui.notify('Operaciones ETL aplicadas desde el Copiloto', type='positive')
        render_page.refresh()

    state.on_apply_etl_proposal = apply_etl_operations

    async def apply_etl_ai_prompt(prompt: str):
        """Aplica una propuesta de prompt para el Modo IA de ETL."""
        # Cambiar al modo IA
        design_state.transformation_mode = 'ai'
        # Asegurar modo descripción natural
        design_state.target_spec_mode = 'description'
        # Rellenar las instrucciones en el campo correcto
        design_state.user_instructions = prompt

        # Asegurar que estamos en la fase de especificación
        if design_state.phase == 'upload':
            design_state.phase = 'spec'

        update_drawer_stepper()
        ui.notify('Instrucciones aplicadas. Cambiado a Modo IA.', type='positive')
        render_page.refresh()

    state.on_apply_etl_ai_prompt = apply_etl_ai_prompt

    # --- HELPERS ---

    def update_drawer_stepper():
        """Sincroniza el stepper del drawer con la fase actual de la página."""
        phase_map = {
            'upload': 0,
            'spec': 1,
            'clarification': 1,
            'config': 2,
            'preview': 3,
            'results': 3
        }
        idx = phase_map.get(design_state.phase, 0)
        layout_manager.update_step_index(idx)

    async def load_saved_etls():
        """Carga scripts de ETL desde la base de datos."""
        async with state.db_session() as session:
            from sqlalchemy import select
            stmt = select(ScriptLibrary).where(ScriptLibrary.source_module == 'etl')
            result = await session.execute(stmt)
            page_state.saved_etls = list(result.scalars().all())
            render_page.refresh()

    def go_to_library():
        from client_app.app.core.state import app_state
        # Si viene desde un flujo, volver al flujo
        flow_id = None
        if app_state.flow_context and app_state.flow_context.get('mode') == 'contextual':
            flow_id = app_state.flow_context.get('flow_id')

            # --- NUEVO: Inyectar la configuración en step.config ---
            step = app_state.flow_context.get('step')
            if step and page_state.current_mode == 'design':
                from pydantic import TypeAdapter
                from client_app.app.models.transform_operations import TransformOperation
                from client_app.app.services.deterministic_etl_service import DeterministicETLService
                
                script_content = ""
                if design_state.transformation_mode == 'ai' and design_state.generated_script:
                     script_content = design_state.generated_script
                elif design_state.transformation_mode == 'assisted' and design_state.operations:
                     try:
                         adapter = TypeAdapter(TransformOperation)
                         ops_models = [adapter.validate_python({k: v for k, v in op.items() if not k.startswith('_')}) for op in design_state.operations]
                         svc = DeterministicETLService()
                         script_content = svc.generate_script(ops_models)
                     except Exception:
                         pass
                
                if hasattr(design_state, 'is_sealing') and design_state.is_sealing:
                     pass # Ya se guardó en save_assisted_atom_dialog
                elif script_content:
                     new_config = {'script': script_content, 'target_format': design_state.target_format}
                     # Preservar IDs si el usuario ya había guardado como acción
                     if step.config.get('config_id'):
                         new_config['config_id'] = step.config.get('config_id')
                         new_config['script_id'] = step.config.get('script_id')
                     step.config = new_config
                     # Actualizar all_steps_config para que el preview refleje los cambios
                     if app_state.editing_flow and hasattr(app_state.editing_flow, 'steps'):
                         app_state.refresh_flow_context_steps(app_state.editing_flow.steps)

                if hasattr(app_state, 'on_step_change') and callable(app_state.on_step_change):
                         app_state.on_step_change()
            # --------------------------------------------------------

            # --- AUTO-GUARDAR FLUJO EN BBDD ---
            # Para evitar que los cambios del paso se pierdan al recargar flows_page.py
            if getattr(app_state, 'editing_flow', None) and flow_id:
                import asyncio
                # CAPTURAR DATOS ANTES DE LIMPIAR CONTEXTO
                current_flow_data = app_state.editing_flow
                
                async def save_flow_bg():
                    try:
                        async with app_state.db_session() as session:
                            from client_app.app.services.flow_registry_service import FlowRegistryService
                            from automatia_shared.dtos import FlowSpec
                            reg = FlowRegistryService(session)
                            
                            flow_dto = FlowSpec(
                                name=current_flow_data.name,
                                description=current_flow_data.description or "",
                                version=current_flow_data.version,
                                status=current_flow_data.status,
                                row_version=current_flow_data.row_version,
                                trigger_type=current_flow_data.trigger_type,
                                trigger_config=current_flow_data.trigger_config,
                                steps=current_flow_data.steps,
                                is_active=current_flow_data.is_active,
                                owner_scope=current_flow_data.owner_scope,
                                trigger_id=current_flow_data.trigger_id
                            )
                            await reg.update_flow(flow_id, flow_dto)
                    except Exception as e:
                        print(f"Error auto-saving flow from ETL: {e}")
                
                asyncio.create_task(save_flow_bg())
            # ----------------------------------

        elif app_state.editing_flow and app_state.flow_id:
            flow_id = app_state.flow_id

        if flow_id:
            layout_manager.exit_design_mode_to_flow()
            app_state.clear_flow_context()
            app_state.clear_atom_editing_context()
            ui.navigate.to(f'/flows/{flow_id}')
            return

        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()

    def go_to_previous_phase():
        """Navega a la fase anterior del wizard, o a la biblioteca si está en la primera fase."""
        phase_order = ['upload', 'spec', 'config', 'preview']  # privacy integrada en config
        current = design_state.phase
        # Clarification es parte de spec
        if current == 'clarification':
            current = 'spec'
        if current == 'results':
            current = 'preview'

        try:
            idx = phase_order.index(current)
            if idx == 0:
                # En la primera fase, ir a la biblioteca
                go_to_library()
            else:
                # Ir a la fase anterior
                design_state.phase = phase_order[idx - 1]
                update_drawer_stepper()
                render_page.refresh()
        except ValueError:
            # Fallback a la biblioteca si la fase no está reconocida
            go_to_library()

    def start_new_design():
        page_state.current_mode = 'design'
        design_state.reset()
        layout_manager.enter_design_mode(StepType.ETL_TRANSFORM)
        update_drawer_stepper()
        render_page.refresh()

    async def edit_etl(script: ScriptLibrary):
        if getattr(script, 'status', 'published') == 'draft':
            page_state.current_mode = 'design'
            page_state.selected_etl_id = script.id
            design_state.reset()
            design_state.user_instructions = script.user_prompt or ""
            design_state.phase = 'spec'
            layout_manager.enter_design_mode(StepType.ETL_TRANSFORM, atom_id=str(script.id))
            update_drawer_stepper()
            render_page.refresh()
        else:
            # Abrir vista de diseño en modo de sólo lectura para átomos sellados
            page_state.current_mode = 'design'
            page_state.selected_etl_id = script.id
            design_state.reset()
            design_state.user_instructions = script.description or script.name or ""
            design_state.generated_script = script.code or self._get_script_code(script) if hasattr(self, '_get_script_code') else ""
            if not design_state.generated_script and script.script_path:
                from pathlib import Path
                try:
                    p = PROJECT_ROOT / "data" / "storage" / "scripts" / "src" / Path(script.script_path).name
                    if p.exists(): design_state.generated_script = p.read_text()
                except:
                    pass
            design_state.phase = 'spec'
            design_state.is_readonly = True
            
            # Restaurar lista de operaciones si fue generada con el asistente
            if script.source_metadata:
                design_state.operations = script.source_metadata.get("operations", [])
                design_state.target_format = script.source_metadata.get("target_format", 'csv')
                
            layout_manager.enter_design_mode(StepType.ETL_TRANSFORM, atom_id=str(script.id))
            update_drawer_stepper()
            render_page.refresh()
            ui.notify('Visualizando configuración (sólo lectura)', type='info')

    async def run_etl(script: ScriptLibrary):
        page_state.current_mode = 'execution'
        exec_state.script_entry = script
        layout_manager.enter_execution_mode(str(script.id))
        render_page.refresh()

    async def delete_etl(script_id: int):
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, script_id)
            if script:
                await session.delete(script)
                await session.commit()
                ui.notify(t('common.deleted_success', name='ETL'), type='positive')
                await load_saved_etls()

    def detect_format(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        format_map = {'.csv': 'csv', '.xlsx': 'excel', '.xls': 'excel', '.json': 'json', '.xml': 'xml', '.parquet': 'parquet'}
        return format_map.get(ext, 'csv')
    
    async def read_df(file_path: str, format: str) -> pd.DataFrame:
        if format == 'csv':
            try:
                # Intento 1: sniff separator and handle varying field counts
                return pd.read_csv(file_path, sep=None, engine='python', on_bad_lines='warn')
            except Exception:
                # Intento 2: fallback to latin-1
                try:
                    return pd.read_csv(file_path, encoding='latin-1', sep=None, engine='python', on_bad_lines='warn')
                except Exception:
                    # Intento 3: standard utf-8 with comma
                    return pd.read_csv(file_path)
        if format == 'excel':
            # Leer en memoria para evitar bloqueo de archivo en Windows
            with open(file_path, 'rb') as f:
                return pd.read_excel(io.BytesIO(f.read()))
        if format == 'json': return pd.read_json(file_path)
        if format == 'xml': return pd.read_xml(file_path)
        if format == 'parquet': return pd.read_parquet(file_path)
        return pd.read_csv(file_path)

    # --- RENDERERS ---

    # Use a persistent main container for this instance
    main_container = ui.column().classes('w-full p-0')

    @ui.refreshable
    async def render_page():
        main_container.clear()
        with main_container:
            if page_state.current_mode == 'library':
                await render_library()
            elif page_state.current_mode == 'design':
                await render_design()
            elif page_state.current_mode == 'execution':
                await render_execution()

    async def toggle_favorite(resource):
        """Toggle favorito para una transformación ETL."""
        etl_id = resource.get('id')
        if etl_id:
            from client_app.app.services.script_library_service import script_library_service
            await script_library_service.toggle_favorite(etl_id)
            page_state.saved_etls = await script_library_service.search_scripts(query=None, source_module='etl')
            render_page.refresh()

    async def render_library():
        # Map ScriptLibrary objects to dicts for StandardPageLayout
        resources = []
        for etl in page_state.saved_etls:
            resources.append({
                'id': etl.id,
                'name': etl.name,
                'description': etl.description or t('etl.no_desc'),
                'status': etl.status or 'draft',
                'source_module': 'etl',
                'doc_path': etl.doc_path,
                'is_favorite': etl.is_favorite,
                'created_at': etl.created_at,
                '_original': etl
            })

        layout = StandardPageLayout(
            title=t('etl.page_title'),
            source_module='etl',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_etl(r['_original']),
            on_delete=lambda r: delete_etl(r['id']),
            on_execute=lambda r: run_etl(r['_original']),
            on_favorite_toggle=toggle_favorite,
            help_description=t('etl.help_desc'),
            input_contract=['source_file', 'target_spec', 'cleaning_options', 'anonymization_config'],
            output_contract=['output_file', 'execution_stats', 'privacy_report']
        )
        layout.render()

    async def render_design():
        # Sincronizar stepper del drawer al entrar o refrescar diseño
        update_drawer_stepper()
        
        # Contextual Header (Flow vs Standalone)
        from client_app.app.core.state import app_state
        is_flow_context = app_state.editing_flow and layout_manager.from_flow_context
        
        if is_flow_context:
            with ui.row().classes('w-full bg-slate-50 border-b p-4 items-center gap-3 mb-6'):
                ui.icon('assignment', size='md', color='primary')
                with ui.column().classes('gap-0'):
                    step_desc = design_state.user_instructions[:30] if design_state.user_instructions else 'ETL'
                    ui.label(t('etl.source_step', name=step_desc)).classes('text-blue-600 font-bold text-primary')
                    ui.label(t('flows.config_asst_subtitle', flow=app_state.flow_name or '', name='ETL')).classes('text-sm text-slate-500')
                
                ui.space()
                ui.button(t('etl.back_to_flow'), icon='arrow_back', on_click=go_to_library).props('flat color=primary')
        else:
            with ui.row().classes('w-full items-center gap-4 mb-2'):
                ui.button(icon='arrow_back', on_click=go_to_previous_phase).props('flat round color=primary')
                with ui.column().classes('gap-0'):
                    ui.label(t('etl.configurator_title')).classes('text-3xl font-bold text-primary')
                    ui.label(t('etl.configurator_desc')).classes('text-sm text-slate-500')
        
        # Phase Container (Replaces ui.stepper to avoid redundant labels on main page)
        with ui.column().classes('w-full max-w-5xl bg-white rounded-xl shadow-sm p-6 gap-6') as container:
            if design_state.phase == 'upload':
                await render_design_upload()

            elif design_state.phase == 'spec' or design_state.phase == 'clarification':
                await render_design_spec()
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button(t('common.back'), on_click=lambda: (setattr(design_state, 'phase', 'upload'), update_drawer_stepper(), render_page.refresh())).props('flat')
                    ui.button(t('common.next'), on_click=lambda: (setattr(design_state, 'privacy_phase_scanned', False), setattr(design_state, 'phase', 'config'), update_drawer_stepper(), render_page.refresh())).props('unelevated color=green-600')

            elif design_state.phase == 'config':
                await render_design_config()
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button(t('common.back'), on_click=lambda: (setattr(design_state, 'phase', 'spec'), update_drawer_stepper(), render_page.refresh())).props('flat')
                    ui.button(t('common.view_results', 'Ver resultados'), icon='visibility', on_click=lambda: (setattr(design_state, 'phase', 'preview'), update_drawer_stepper(), render_page.refresh())).props('unelevated color=green-600')

            elif design_state.phase == 'preview' or design_state.phase == 'results':
                await render_design_preview()
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button(t('common.back'), on_click=lambda: (setattr(design_state, 'phase', 'config'), update_drawer_stepper(), render_page.refresh())).props('flat')
                    if design_state.transformation_mode == 'assisted':
                        ui.button(t('etl.btn_execute', 'Ejecutar transformación'), icon='play_arrow', on_click=handle_assisted_execution).props('unelevated color=blue')
                    else:
                        ui.button(t('etl.btn_generate', 'Generar y ejecutar'), icon='play_arrow', on_click=generate_script).props('unelevated color=blue')


    async def render_design_upload():
        with ui.column().classes('w-full gap-4'):
            # Handler para selección de fuente de datos
            def handle_source_selection(selection: DataSourceSelection):
                design_state.data_source = selection
                if selection.source_type == 'manual' and selection.file_content:
                    # Procesar archivo subido (necesita contexto de cliente para ui.notify/refrescos)
                    client = ui.context.client
                    asyncio.create_task(process_uploaded_file(selection, client))
                elif selection.source_type == 'catalog':
                    ui.notify(t('etl.atom_selected', name=selection.atom_name), type='info')
                elif selection.source_type == 'flow_step':
                    ui.notify(t('etl.step_selected', name=selection.step_name), type='info')
                render_page.refresh()

            async def process_uploaded_file(selection: DataSourceSelection, client):
                """Procesa el archivo subido desde el selector."""
                with client:
                    try:
                        filename = selection.file_name or 'upload.csv'
                        filename = re.sub(r'[^a-zA-Z0-9\._-]', '_', filename)
                        f_path = ETL_UPLOAD_DIR / filename
                        with open(f_path, 'wb') as f:
                            f.write(selection.file_content)

                        design_state.source_file = str(f_path)
                        design_state.filename = filename
                        design_state.source_format = detect_format(filename)
                        df = await read_df(design_state.source_file, design_state.source_format)
                        design_state.source_preview = df.head(10)
                        design_state.source_info = {
                            'name': filename,
                            'rows': len(df),
                            'columns': len(df.columns),
                            'column_names': list(df.columns)
                        }
                        _update_global_data_context(df)
                        render_page.refresh()
                        ui.notify(f"Archivo cargado: {filename}", type='positive')
                    except Exception as ex:
                        ui.notify(f"Error carga: {ex}", type='negative')


            # Renderizar el selector unificado
            render_data_source_selector(
                consumer_type=StepType.ETL,
                on_source_selected=handle_source_selection,
                flow_context=state.flow_context,
                initial_selection=design_state.data_source,
                upload_formats_override=['csv', 'xlsx', 'json', 'xml', 'parquet'],
                selector_state_override=design_state.data_source_selector_state
            )

            # Botón Continuar antes de la vista previa
            def proceed_to_spec():
                if design_state.data_source and design_state.data_source.source_type in ['catalog', 'flow_step']:
                    if hasattr(design_state, 'data_source_selector_state') and design_state.data_source_selector_state.preview_data:
                        design_state.source_preview = design_state.data_source_selector_state.preview_data.to_dataframe()
                        if design_state.source_preview is not None:
                            design_state.source_info = {
                                'name': design_state.data_source.step_name or design_state.data_source.atom_name or 'datos_preview',
                                'rows': len(design_state.source_preview),
                                'columns': len(design_state.source_preview.columns),
                                'column_names': list(design_state.source_preview.columns)
                            }
                            _update_global_data_context(design_state.source_preview)
                # Mantenemos lógica de avanzar pasos
                design_state.phase = 'spec'
                update_drawer_stepper()
                render_page.refresh()

            with ui.row().classes('w-full justify-end mt-2'):
                can_proceed = (
                    design_state.source_file is not None or
                    (design_state.data_source and design_state.data_source.source_type in ['catalog', 'flow_step'])
                )
                ui.button(t('common.next'), on_click=proceed_to_spec).props('unelevated color=green-600').set_enabled(can_proceed)

            # Mostrar la vista previa aquí SÓLO para subida manual, ya que
            # data_source_selector ya muestra su propia previsualización para 'catalog' y 'flow_step'.
            if design_state.source_preview is not None and design_state.data_source and design_state.data_source.source_type == 'manual':
                with ui.card().classes('w-full p-2 mt-2'):
                    ui.label(t('etl.design_preview_title', 'Vista Previa Origen')).classes('text-xs font-bold text-slate-500 mb-2')
                    ui.table.from_pandas(design_state.source_preview.head(5)).classes('w-full').props('dense flat')

    async def render_design_spec():
        # Sincronizar stepper del drawer al entrar o refrescar diseño
        update_drawer_stepper()
        
        with ui.column().classes('w-full gap-4'):
            # 1. Selector de Modo de Transformación
            with ui.card().classes('w-full p-4 border rounded-xl shadow-sm'):
                with ui.row().classes('w-full items-center justify-between'):
                    ui.label(t('etl.transform_type')).classes('font-bold text-slate-800')
                    ui.radio({'assisted': t('etl.mode_assisted'), 'ai': t('etl.mode_ai')}, value=design_state.transformation_mode)\
                        .bind_value(design_state, 'transformation_mode').props('inline')
            
            # 2. Renderizado Condicional según Modo
            if design_state.transformation_mode == 'assisted':
                await render_assisted_spec()
            else:
                await render_ai_spec()

    async def render_ai_spec():
        """Renderiza la interfaz para transformaciones personalizadas con IA."""
        with ui.card().classes('w-full p-6 space-y-4'):
            ui.label(t('etl.ai_instructions_title')).classes('text-lg font-bold text-slate-700')
            
            ui.textarea(
                label=t('etl.ai_instructions_label'),
                placeholder=t('etl.ai_instructions_placeholder')
            ).bind_value(design_state, 'additional_instructions').classes('w-full').props('outlined rows=6')

            ui.separator()
            
            ui.label(t('etl.ai_output_specs')).classes('text-lg font-bold text-slate-700')
            ui.label(t('etl.ai_output_desc')).classes('text-sm text-slate-500')

            # Uploader para ejemplo
            async def handle_example_upload(e):
                design_state.example_file = e.content
                ui.notify(f"Ejemplo cargado: {e.name}", type='positive')

            ui.upload(on_upload=handle_example_upload, label=t('etl.ai_upload_example'), auto_upload=True).classes('w-full')

            ui.input(t('etl.ai_output_filename')).bind_value(design_state, 'filename').props('outlined')
            
            ui.separator()

            # Botón de Generación (Movido aquí)
            ui.button(t('etl.btn_analyze'), icon='analytics', on_click=lambda: ui.run_javascript("emit('run_etl_analysis')"))\
                .props('unelevated color=indigo-600 size=sm').classes('w-full')
            ui.button(t('etl.btn_generate_ai'), icon='auto_awesome', on_click=lambda: generate_script(False))\
                .props('unelevated color=indigo-600 size=lg').classes('w-full')

    async def render_assisted_spec():
        """Renderiza la interfaz para transformaciones deterministas (Modo Asistido)."""
        
        OP_TYPES = {
            'drop_columns': {'label': t('etl.op_drop_columns'), 'icon': 'delete_sweep'},
            'rename_columns': {'label': t('etl.op_rename_columns'), 'icon': 'drive_file_rename_outline'},
            'merge_columns': {'label': t('etl.op_merge_columns'), 'icon': 'call_merge'},
            'format_dates': {'label': t('etl.op_format_dates'), 'icon': 'calendar_today'},
            'filter_rows': {'label': t('etl.op_filter_rows'), 'icon': 'filter_alt'},
            'replace_values': {'label': t('etl.op_replace_values'), 'icon': 'find_replace'},
            'normalize_text': {'label': t('etl.op_normalize_text'), 'icon': 'text_format'},
            'fill_nulls': {'label': t('etl.op_fill_nulls'), 'icon': 'format_color_fill'},
            'remove_duplicates': {'label': t('etl.op_remove_duplicates'), 'icon': 'content_copy'},
            'remove_null_rows': {'label': t('etl.op_remove_null_rows'), 'icon': 'remove_circle_outline'},
            'reorder_columns': {'label': t('etl.op_reorder_columns'), 'icon': 'sort'}
        }

        # DEFINICIONES DEL WIZARD (Deben ir antes de su uso)
        @ui.refreshable
        def render_inline_wizard(OP_TYPES):
            """Renderiza el wizard de operaciones inline (sin dialogs)."""
            
            # 1. Selector de Tipo de Operación (Radio Grid)
            with ui.card().classes('w-full p-4 mb-4 bg-slate-50 border border-slate-200'):
                with ui.grid(columns=4).classes('w-full gap-2'):
                    for op_type, meta in OP_TYPES.items():
                        def select_op(t=op_type):
                            design_state.wizard_op_type = t
                            design_state.current_operation_editor = {'type': t}
                            render_wizard_form.refresh()

                        # Estilo visual de selección
                        is_selected = design_state.wizard_op_type == op_type
                        bg_color = 'bg-blue-100 border-blue-500' if is_selected else 'bg-white hover:bg-slate-100'
                        
                        with ui.card().classes(f'cursor-pointer p-2 flex flex-row items-center gap-2 border transition-all {bg_color}')\
                            .on('click', select_op):
                            ui.icon(meta['icon'], color='blue' if is_selected else 'slate').classes('text-xl')
                            ui.label(meta['label']).classes('text-xs font-medium')

            # 2. Formulario Dinámico
            @ui.refreshable
            def render_wizard_form():
                if not design_state.wizard_op_type:
                    return

                op_type = design_state.wizard_op_type
                with ui.card().classes('w-full p-3 border rounded-xl shadow-none bg-slate-50/50'):

                    
                    # Renderizar formulario específico
                    if op_type == 'drop_columns': render_drop_columns_form()
                    elif op_type == 'rename_columns': render_rename_columns_form()
                    elif op_type == 'merge_columns': render_merge_columns_form()
                    elif op_type == 'format_dates': render_format_dates_form()
                    elif op_type == 'filter_rows': render_filter_rows_form()
                    elif op_type == 'replace_values': render_replace_values_form()
                    elif op_type == 'normalize_text': render_normalize_text_form()
                    elif op_type == 'fill_nulls': render_fill_nulls_form()
                    elif op_type == 'remove_duplicates': render_remove_duplicates_form()
                    elif op_type == 'remove_null_rows': render_remove_null_rows_form()
                    elif op_type == 'reorder_columns': render_reorder_columns_form()
                    else: ui.label(f"Formulario para {op_type} no implementado aún").classes('text-red-500')

                    # Botones de Acción
                    with ui.row().classes('w-full items-center justify-end mt-4 gap-2'):
                        def clear():
                            design_state.wizard_op_type = None
                            design_state.current_operation_editor = None
                            render_wizard_form.refresh()
                        ui.button(t('common.cancel'), on_click=clear).props('flat text-color=slate')
                        
                        def add_to_list():
                            is_valid, error_msg = validate_operation(design_state.current_operation_editor)
                            if is_valid:
                                idx = design_state.current_operation_editor.get('_index')
                                if idx is not None:
                                    del design_state.current_operation_editor['_index']
                                    design_state.operations[idx] = design_state.current_operation_editor
                                    ui.notify(t('etl.op_updated'), type='positive')
                                else:
                                    design_state.operations.append(design_state.current_operation_editor)
                                    ui.notify(t('etl.op_added'), type='positive')
                                design_state.wizard_op_type = None
                                design_state.current_operation_editor = None
                                render_wizard_form.refresh()
                                render_inline_wizard.refresh()
                                render_page.refresh()
                            else:
                                ui.notify(error_msg, type='warning')

                        is_edit = design_state.current_operation_editor and '_index' in design_state.current_operation_editor
                        btn_label = t('common.save_changes') if is_edit else t('etl.btn_add_op')
                        btn_icon = 'save' if is_edit else 'add_circle'
                        ui.button(btn_label, icon=btn_icon, on_click=add_to_list).props('unelevated color=blue')

            render_wizard_form()

        # Data preview expander (Config phase context)
        if design_state.source_preview is not None:
            with ui.expansion(t('etl.design_preview_title'), icon='table_chart').classes('w-full bg-slate-50 border border-slate-200 mb-4'):
                ui.table.from_pandas(design_state.source_preview).classes('w-full text-xs').props('dense flat')

        with ui.card().classes('w-full p-4'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label(t('etl.ops_list_title')).classes('font-bold text-lg')

            if getattr(design_state, 'is_readonly', False):
                 ui.label('Acción Sellada de la Biblioteca').classes('text-lg font-bold text-green-700 mt-2')
                 ui.label('Esta configuración es de sólo lectura dentro del flujo actual.').classes('text-slate-500 mb-4')
                 if not design_state.operations and design_state.generated_script:
                      with ui.card().classes('w-full bg-slate-900 border overflow-hidden'):
                          ui.code(design_state.generated_script, language='python').classes('text-xs font-mono text-white p-4')
                      return 
            else:
                 # WIZARD DE OPERACIONES (Reemplazo de Dialog)
                 render_inline_wizard(OP_TYPES)

            # Lista de Operaciones
            if not design_state.operations:
                with ui.column().classes('w-full gap-2 items-center justify-center p-8 border-2 border-dashed border-slate-300 rounded-lg bg-slate-50'):
                    ui.icon('build', size='3em', color='slate-300')
                    ui.label(t('etl.no_ops')).classes('text-slate-400 font-medium')
                    ui.label(t('etl.no_ops_desc')).classes('text-xs text-slate-400')
            else:
                with ui.column().classes('w-full gap-2'):
                    for idx, op in enumerate(design_state.operations):
                        op_meta = OP_TYPES.get(op['type'], {'label': 'Desconocido', 'icon': 'help'})
                        with ui.card().classes('w-full p-3 flex flex-row items-center justify-between border hover:border-blue-300 transition-colors'):
                            with ui.row().classes('items-center gap-3'):
                                ui.label(f"{idx + 1}").classes('font-mono text-slate-400 font-bold')
                                ui.icon(op_meta['icon'], color='slate-600')
                                with ui.column().classes('gap-0'):
                                    ui.label(op_meta['label']).classes('font-bold text-sm text-slate-700')
                                    # Resumen de configuración (si existe params)
                                    summary = get_operation_summary(op)
                                    ui.label(summary).classes('text-xs text-slate-500')
                            
                            
                            with ui.row().classes('gap-1').bind_visibility_from(design_state, 'is_readonly', backward=lambda x: not x):
                                ui.button(icon='arrow_upward', on_click=lambda i=idx: move_operation(i, -1)).props('flat dense round size=sm').set_visibility(idx > 0)
                                ui.button(icon='arrow_downward', on_click=lambda i=idx: move_operation(i, 1)).props('flat dense round size=sm').set_visibility(idx < len(design_state.operations) - 1)
                                
                                def edit_op(i=idx, t=op['type']):
                                    import copy
                                    design_state.wizard_op_type = t
                                    design_state.current_operation_editor = copy.deepcopy(design_state.operations[i])
                                    design_state.current_operation_editor['_index'] = i 
                                    render_inline_wizard.refresh() # Refresh wizard to show form

                                ui.button(icon='edit', on_click=edit_op).props('flat dense round size=sm color=blue')
                                ui.button(icon='delete', on_click=lambda i=idx: delete_operation(i)).props('flat dense round size=sm color=red')


    def get_operation_summary(op: Dict[str, Any]) -> str:
        """Genera un resumen legible de la configuración de la operación."""
        op_type = op.get('type')
        if op_type == 'drop_columns':
            return f"Columnas: {', '.join(op.get('columns', []))}"
        elif op_type == 'rename_columns':
            return f"{len(op.get('mapping', {}))} cambios de nombre"
        elif op_type == 'merge_columns':
            return f"{', '.join(op.get('source_columns', []))} → {op.get('target_column')}"
        elif op_type == 'format_dates':
            return f"{op.get('column')} → {op.get('target_format')}"
        elif op_type == 'filter_rows':
            return f"{op.get('column')} {op.get('operator')} {op.get('value')}"
        elif op_type == 'replace_values':
            return f"{op.get('column')}: {len(op.get('replacements', {}))} reemplazos"
        elif op_type == 'normalize_text':
            return f"{len(op.get('columns', []))} columnas ({op.get('mode')})"
        elif op_type == 'fill_nulls':
            return f"{len(op.get('columns', []))} columnas con '{op.get('value')}'"
        elif op_type == 'remove_duplicates':
            return f"Subset: {op.get('subset') or 'Todas'}, Keep: {op.get('keep')}"
        elif op_type == 'remove_null_rows':
            return f"Subset: {op.get('subset') or 'Cualquiera'}, How: {op.get('how')}"
        elif op_type == 'reorder_columns':
            return f"{len(op.get('columns', []))} columnas reordenadas"
        return "Pendiente de configurar"

    def move_operation(index: int, direction: int):
        new_index = index + direction
        if 0 <= new_index < len(design_state.operations):
            design_state.operations[index], design_state.operations[new_index] = \
                design_state.operations[new_index], design_state.operations[index]
            render_page.refresh()

    def delete_operation(index: int):
        design_state.operations.pop(index)
        render_page.refresh()

    # open_operation_editor removed in favor of inline wizard

    # --- FORMULARIOS ESPECÍFICOS ---

    def render_drop_columns_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        current_sel = op.get('columns', [])
        
        ui.select(cols, value=current_sel, multiple=True, label=t('etl.label_drop_cols'), with_input=True)\
            .bind_value(op, 'columns').classes('w-full').props('use-chips dense')

    def render_rename_columns_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        if 'mapping' not in op: op['mapping'] = {}
        
        ui.label(t('etl.label_rename_title')).classes('text-sm text-slate-600')
        
        # Container para filas de mapeo
        container = ui.column().classes('w-full gap-2')
        
        def refresh_mapping_ui():
            container.clear()
            with container:
                for old_col, new_col in op['mapping'].items():
                    with ui.row().classes('w-full items-center gap-2'):
                        ui.label(old_col).classes('font-mono w-1/3 truncate')
                        ui.icon('arrow_forward', color='slate-400')
                        ui.label(new_col).classes('font-bold w-1/3 truncate')
                        ui.button(icon='delete', on_click=lambda c=old_col: remove_map(c)).props('flat dense round color=red')

        def remove_map(col):
            del op['mapping'][col]
            refresh_mapping_ui()

        def add_map(old, new):
            if old and new:
                op['mapping'][old] = new
                refresh_mapping_ui()

        refresh_mapping_ui()
        
        with ui.row().classes('w-full items-end gap-2 mt-2 bg-slate-50 p-2 rounded'):
            sel = ui.select(cols, label=t('etl.label_col_actual')).classes('w-1/3').props('dense')
            inp = ui.input(label=t('etl.label_col_new')).classes('w-1/3').props('dense')
            ui.button(icon='add', on_click=lambda: (add_map(sel.value, inp.value), sel.set_value(None), inp.set_value('')))\
                .props('round flat color=primary dense')

    def render_merge_columns_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        
        with ui.row().classes('w-full gap-6'):
            # Columna 1
            with ui.column().classes('flex-1 gap-2'):
                ui.select(cols, multiple=True, label=t('etl.label_cols_merge'), with_input=True)\
                    .bind_value(op, 'source_columns').classes('w-full').props('use-chips dense dark:label-color=slate-500')
                
                ui.input(label=t('etl.label_separator')).bind_value(op, 'separator').classes('w-full').props('dense')
            
            # Columna 2
            with ui.column().classes('flex-1 gap-2'):
                ui.input(label=t('etl.label_new_col')).bind_value(op, 'target_column').classes('w-full').props('dense')
                
                ui.checkbox(t('etl.label_drop_source')).bind_value(op, 'drop_source')\
                    .classes('mt-2 text-xs text-slate-600')


    def render_format_dates_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        
        with ui.row().classes('w-full gap-6'):
            with ui.column().classes('flex-1 gap-1'):
                ui.select(cols, label=t('etl.label_date_col'), with_input=True).bind_value(op, 'column').classes('w-full').props('dense')
                ui.input(label=t('etl.label_source_fmt'), placeholder='Ej: %d-%m-%Y').bind_value(op, 'source_format').classes('w-full').props('dense')
            
            with ui.column().classes('flex-1 gap-1'):
                target_formats = {
                    '%Y-%m-%d': 'ISO 8601 (YYYY-MM-DD)',
                    '%d/%m/%Y': 'ESP (DD/MM/YYYY)',
                    '%m/%d/%Y': 'USA (MM/DD/YYYY)',
                    '%d-%m-%Y': 'DD-MM-YYYY'
                }
                ui.select(target_formats, label=t('etl.label_target_fmt'), with_input=True)\
                    .bind_value(op, 'target_format').classes('w-full').props('dense')
        # Todo: permitir custom input si no está en la lista

    def render_filter_rows_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        
        with ui.row().classes('w-full gap-4'):
            ui.select(cols, label=t('etl.label_filter_col'), with_input=True).bind_value(op, 'column').classes('flex-1').props('dense')
            ops = ['==', '!=', '>', '<', '>=', '<=', 'contains', 'not_contains']
            ui.select(ops, label=t('etl.label_filter_op')).bind_value(op, 'operator').classes('w-40').props('dense')
            ui.input(label=t('etl.label_filter_val')).bind_value(op, 'value').classes('flex-1').props('dense')

    def render_replace_values_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        if 'replacements' not in op: op['replacements'] = {}
        
        ui.select(cols, label=t('etl.label_filter_col'), with_input=True).bind_value(op, 'column').classes('w-full')
        
        ui.label(t('etl.label_replace_title')).classes('text-sm text-slate-600')
        
        container = ui.column().classes('w-full gap-2')
        
        def refresh_repl_ui():
            container.clear()
            with container:
                for old_val, new_val in op['replacements'].items():
                    with ui.row().classes('w-full items-center gap-2'):
                        ui.label(str(old_val)).classes('font-mono w-1/3 truncate')
                        ui.icon('arrow_forward', color='slate-400')
                        ui.label(str(new_val)).classes('font-bold w-1/3 truncate')
                        ui.button(icon='delete', on_click=lambda v=old_val: remove_repl(v)).props('flat dense round color=red')

        def remove_repl(val):
            del op['replacements'][val]
            refresh_repl_ui()

        def add_repl(old, new):
            if old: # Permitir new vacío (eliminar contenido)
                op['replacements'][old] = new
                refresh_repl_ui()

        refresh_repl_ui()
        
        with ui.row().classes('w-full items-end gap-2 mt-2 bg-slate-50 p-2 rounded'):
            old_inp = ui.input(label=t('etl.label_curr_val')).classes('w-1/3')
            new_inp = ui.input(label=t('etl.label_new_val')).classes('w-1/3')
            ui.button(icon='add', on_click=lambda: (add_repl(old_inp.value, new_inp.value), old_inp.set_value(''), new_inp.set_value('')))\
                .props('round flat color=primary')

    def render_normalize_text_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        
        ui.select(cols, multiple=True, label='Columnas', with_input=True)\
            .bind_value(op, 'columns').classes('w-full').props('use-chips')
            
        modes = {
            'upper': 'Mayúsculas (UPPER)',
            'lower': 'Minúsculas (lower)',
            'title': 'Título (Title Case)',
            'strip': 'Eliminar espacios extra (Trim)',
            'snake_case': 'Snake Case (snake_case)'
        }
        ui.select(modes, label=t('etl.label_normalize_mode')).bind_value(op, 'mode').classes('w-full')



    def render_fill_nulls_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        
        ui.select(cols, multiple=True, label=t('etl.label_normalize_cols'), with_input=True)\
            .bind_value(op, 'columns').classes('w-full').props('use-chips')
        
        ui.input(label=t('etl.label_fill_val')).bind_value(op, 'value').classes('w-full')

    def render_remove_duplicates_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        
        ui.select(cols, multiple=True, label=t('etl.label_dup_subset'), with_input=True)\
            .bind_value(op, 'subset').classes('w-full').props('use-chips')
            
        keeps = {'first': 'Conservar Primera (first)', 'last': 'Conservar Última (last)', 'false': 'Eliminar Todas'}
        ui.select(keeps, label=t('etl.label_dup_strategy')).bind_value(op, 'keep').classes('w-full')

    def render_remove_null_rows_form():
        op = design_state.current_operation_editor
        cols = design_state.source_info.get('column_names', [])
        
        ui.select(cols, multiple=True, label=t('etl.label_null_subset'), with_input=True)\
            .bind_value(op, 'subset').classes('w-full').props('use-chips')
            
        hows = {'any': 'Si alguna columna es nula (any)', 'all': 'Si TODAS son nulas (all)'}
        ui.select(hows, label=t('etl.label_null_condition')).bind_value(op, 'how').classes('w-full')

    def render_reorder_columns_form():
        op = design_state.current_operation_editor
        all_cols = design_state.source_info.get('column_names', [])
        
        if 'columns' not in op: 
            # Initial state: all columns in current order
            op['columns'] = list(all_cols)
        
        ui.label('Arrastra o usa los botones para reordenar las columnas:').classes('text-sm text-slate-500 mb-2')
        
        container = ui.column().classes('w-full gap-1 border p-2 rounded bg-white')
        
        def refresh_reorder_ui():
            container.clear()
            with container:
                for idx, col in enumerate(op['columns']):
                    with ui.row().classes('w-full items-center gap-2 p-1 border-b last:border-0 hover:bg-slate-50'):
                        ui.label(str(idx + 1)).classes('text-xs font-mono text-slate-400 w-4')
                        ui.icon('drag_indicator', color='slate-300')
                        ui.label(col).classes('flex-1')
                        with ui.row().classes('gap-1'):
                            ui.button(icon='arrow_upward', on_click=lambda i=idx: move_col(i, -1)).props('flat dense size=sm').set_visibility(idx > 0)
                            ui.button(icon='arrow_downward', on_click=lambda i=idx: move_col(i, 1)).props('flat dense size=sm').set_visibility(idx < len(op['columns']) - 1)

        def move_col(idx, direction):
            new_idx = idx + direction
            op['columns'][idx], op['columns'][new_idx] = op['columns'][new_idx], op['columns'][idx]
            refresh_reorder_ui()

        refresh_reorder_ui()


    def validate_operation(op: Dict) -> Tuple[bool, str]:
        """Valida que la operación tenga los datos mínimos necesarios."""
        t = op.get('type')
        if t == 'drop_columns':
            if not op.get('columns'): return False, t('etl.validate_drop_cols')
        elif t == 'rename_columns':
            if not op.get('mapping'): return False, t('etl.validate_rename')
        elif t == 'merge_columns':
            if not op.get('source_columns') or len(op.get('source_columns', [])) < 2: return False, t('etl.validate_merge_cols')
            if not op.get('target_column'): return False, t('etl.validate_merge_target')
        elif t == 'format_dates':
            if not op.get('column'): return False, t('etl.validate_date_col')
            if not op.get('target_format'): return False, t('etl.validate_date_target')
        elif t == 'filter_rows':
            if not op.get('column'): return False, t('etl.validate_filter_col')
            if not op.get('operator'): return False, t('etl.validate_filter_op')
            if op.get('value') is None: return False, t('etl.validate_filter_val')
        elif t == 'replace_values':
            if not op.get('column'): return False, t('etl.validate_replace_col')
            if not op.get('replacements'): return False, t('etl.validate_replace_vals')
        elif t == 'normalize_text':
             if not op.get('columns'): return False, t('etl.validate_normalize_cols')
             if not op.get('mode'): return False, t('etl.validate_normalize_mode')
        elif t == 'fill_nulls':
             if not op.get('columns'): return False, t('etl.validate_fill_cols')
             if op.get('value') is None: return False, t('etl.validate_fill_val')
        elif t == 'remove_duplicates':
             if not op.get('keep'): return False, t('etl.validate_dup_keep')
        elif t == 'remove_null_rows':
             if not op.get('how'): return False, t('etl.validate_null_how')
        elif t == 'reorder_columns':
             if not op.get('columns'): return False, t('etl.validate_reorder_cols')
        return True, ""

    async def render_ai_spec():
        """Renderiza la interfaz para transformaciones con IA (Legado/Avanzado)."""

        def check_instructions(e):
            text = e.value
            design_state.user_instructions = text
            ops = detect_potential_operations(text)
            if len(ops) >= 1:
                design_state.suggested_ops = ops
                design_state.show_suggestion = True
            else:
                design_state.show_suggestion = False
                design_state.suggested_ops = []
            render_page.refresh()

        with ui.column().classes('w-full gap-4'):
            # Modos de especificación mejorados
            with ui.card().classes('w-full border p-4 bg-slate-50'):
                ui.label(t('etl.ai_spec_mode')).classes('text-sm font-bold text-slate-700 mb-2')
                ui.radio({'description': t('etl.ai_mode_desc'), 'example': t('etl.ai_mode_example'), 'schema': t('etl.ai_mode_schema')}, 
                         value=design_state.target_spec_mode,
                         on_change=lambda e: (setattr(design_state, 'target_spec_mode', e.value), render_page.refresh()))\
                         .props('inline dense')
            
            if design_state.target_spec_mode == 'description':
                # Intelligent Warning Banner
                if design_state.show_suggestion:
                    with ui.card().classes('w-full p-4 border-l-4 border-orange-400 bg-orange-50'):
                        with ui.row().classes('items-center gap-2 mb-2'):
                            ui.icon('lightbulb', color='orange-800')
                            ui.label(t('etl.ai_suggest_title')).classes('font-bold text-orange-900')
                        
                        ui.label(t('etl.ai_suggest_desc')).classes('text-sm text-orange-900 mb-2')
                        
                        with ui.column().classes('pl-8 gap-1 mb-3'):
                            seen_labels = set()
                            for op in design_state.suggested_ops:
                                if op['label'] not in seen_labels:
                                    ui.label(f"• {op['label']}").classes('text-xs font-bold text-slate-700')
                                    seen_labels.add(op['label'])
                                
                        with ui.row().classes('gap-4 mt-2'):
                            def switch_to_assisted():
                                design_state.transformation_mode = 'assisted'
                                design_state.show_suggestion = False
                                render_page.refresh()
                                ui.notify(t('etl.ai_suggest_switched'), type='positive')
                                
                            ui.button(t('etl.ai_suggest_btn_switch'), on_click=switch_to_assisted).props('unelevated color=orange-900 text-color=white dense')
                            ui.button(t('etl.ai_suggest_btn_ignore'), on_click=lambda: (setattr(design_state, 'show_suggestion', False), render_page.refresh())).props('flat color=orange-900 dense')

                with ui.card().classes('w-full p-4'):
                    ui.label(t('etl.ai_desc_title')).classes('font-bold mb-2')
                    ui.textarea(placeholder=t('etl.ai_desc_placeholder'))\
                        .classes('w-full').props('outlined rows=10').bind_value(design_state, 'user_instructions').on_value_change(check_instructions)
                    design_state.target_spec = design_state.user_instructions
            
            elif design_state.target_spec_mode == 'example':
                with ui.card().classes('w-full p-4'):
                    ui.label(t('etl.ai_example_title')).classes('font-bold mb-2')
                    ui.upload(on_upload=handle_example_upload, label=t('etl.ai_example_upload'), auto_upload=True).classes('w-full')
                    if design_state.example_preview is not None:
                        ui.label(t('etl.ai_example_preview')).classes('text-xs font-bold mt-4')
                        ui.table.from_pandas(design_state.example_preview.head(3)).classes('w-full').props('dense flat')
            
            elif design_state.target_spec_mode == 'schema':
                with ui.card().classes('w-full p-4'):
                    ui.label(t('etl.ai_schema_title')).classes('font-bold mb-2')
                    def on_json(e):
                        try: design_state.target_spec = json.loads(e.value)
                        except: pass
                    ui.textarea(placeholder='{\n  "nombre": "string",\n  "total": "float"\n}', value=json.dumps(design_state.target_spec, indent=2) if isinstance(design_state.target_spec, dict) else "")\
                        .classes('w-full font-mono text-sm').props('outlined rows=10').on_change(on_json)

            with ui.card().classes('w-full p-4'):
                ui.select({'csv': 'CSV', 'xlsx': 'Excel', 'json': 'JSON', 'parquet': 'Parquet'}, label=t('etl.ai_target_format'))\
                  .bind_value(design_state, 'target_format').classes('w-full').props('outlined dense')

    async def render_design_config():
        """Configuración de privacidad y anonimización - se muestra antes del preview."""
        from client_app.app.utils.pii_detector import PIIDetector
        from client_app.app.ui.components.anonymizer_field_row import AnonymizerFieldRow

        # Generar Preview Intermedio (si hay operaciones) para usarlo en el preview posterior
        if design_state.transformation_mode == 'assisted':
             if getattr(design_state, 'intermediate_preview', None) is None:
                  try:
                      if design_state.operations and design_state.source_preview is not None:
                          from client_app.app.services.deterministic_etl_service import DeterministicETLService
                          from client_app.app.models.transform_operations import TransformOperation
                          from pydantic import TypeAdapter

                          adapter = TypeAdapter(TransformOperation)
                          ops_models = [adapter.validate_python({k: v for k, v in op.items() if not k.startswith('_')}) for op in design_state.operations]

                          svc = DeterministicETLService()
                          input_df = design_state.source_preview.copy() if design_state.source_preview is not None else pd.DataFrame()
                          design_state.intermediate_preview = await svc.execute_transformation(input_df, ops_models)
                      else:
                          design_state.intermediate_preview = design_state.source_preview.copy() if design_state.source_preview is not None else None
                  except Exception as e:
                      print(f"Error generating intermediate preview: {e}")
                      design_state.intermediate_preview = None

        # Detectar PII sobre el preview intermedio (o source si no hay)
        df_to_scan = design_state.intermediate_preview if getattr(design_state, 'intermediate_preview', None) is not None else design_state.source_preview

        # Resetear y re-escanear al entrar a esta fase
        if df_to_scan is not None and not getattr(design_state, 'privacy_phase_scanned', False):
            detector = PIIDetector()
            findings = detector.scan_dataframe(df_to_scan)

            # Auto-configurar mapa de anonimización
            design_state.anon_col_map = {}
            for f in findings:
                if f['is_sensitive']:
                    design_state.anon_col_map[f['field']] = f['type']

            design_state.privacy_phase_scanned = True
            if design_state.anon_col_map:
                design_state.enable_anonymization = True

        with ui.column().classes('w-full gap-6'):
            ui.label(t('etl.privacy_phase_title', 'Configuración de Privacidad')).classes('text-xl font-bold text-slate-800')
            ui.label(t('etl.privacy_phase_desc', 'Configura las opciones de anonimización antes de ver los resultados.')).classes('text-slate-600 mb-4')

            with ui.card().classes('w-full p-4 border rounded-xl shadow-sm bg-white'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('security', color='blue').classes('text-xl')
                    ui.label(t('etl.privacy_title')).classes('font-bold text-slate-800 text-lg')

                with ui.row().classes('items-center justify-between w-full mb-4'):
                    ui.label(t('etl.privacy_desc')).classes('text-slate-600')
                    ui.switch(t('etl.privacy_switch')).bind_value(design_state, 'enable_anonymization').props('color=blue')

                if design_state.enable_anonymization:
                    with ui.column().classes('w-full gap-4 mt-2'):
                        # Tabla de Campos Detectados
                        if not design_state.anon_col_map:
                            ui.label(t('etl.privacy_no_pii')).classes('text-slate-400 italic text-sm')
                        else:
                            ui.label(t('etl.privacy_detected_fields')).classes('font-bold text-sm text-slate-700')

                            # Helper to update state from row
                            def on_row_change(field, row_state):
                                if row_state['active']:
                                    design_state.anon_col_map[field] = row_state['type']
                                    if not hasattr(design_state, 'anon_strategies'): design_state.anon_strategies = {}
                                    design_state.anon_strategies[field] = row_state['strategy']
                                else:
                                    if field in design_state.anon_col_map:
                                        del design_state.anon_col_map[field]
                                    if hasattr(design_state, 'anon_strategies') and field in design_state.anon_strategies:
                                        del design_state.anon_strategies[field]

                            # Ensure strategies dict exists
                            if not hasattr(design_state, 'anon_strategies'): design_state.anon_strategies = {}

                            for col_name in (df_to_scan.columns if df_to_scan is not None else []):
                                if col_name in design_state.anon_col_map:
                                    field_type = design_state.anon_col_map[col_name]
                                    f_info = {'field': col_name, 'type': field_type, 'is_sensitive': True}
                                    AnonymizerFieldRow(
                                        field_info=f_info,
                                        on_change=lambda s, f=col_name: on_row_change(f, s),
                                        initial_mode=None
                                    )

                        # Campos no detectados como sensibles (disponibles para añadir)
                        non_pii_columns = [col for col in (df_to_scan.columns if df_to_scan is not None else [])
                                           if col not in design_state.anon_col_map]

                        if non_pii_columns:
                            with ui.expansion(t('etl.privacy_other_fields'), icon='add_circle_outline').classes('w-full bg-slate-50'):
                                ui.label(t('etl.privacy_non_pii_desc')).classes('text-xs text-slate-500 mb-2 px-2')
                                for col_name in non_pii_columns:
                                    with ui.row().classes('w-full items-center gap-2 p-2 border-b hover:bg-slate-100'):
                                        ui.icon('text_fields', color='slate-400')
                                        ui.label(col_name).classes('flex-1 font-mono text-sm')
                                        t_sel = ui.select(
                                            {'PERSON': 'Persona', 'EMAIL': 'Email', 'ID': 'DNI/ID', 'PHONE': 'Teléfono', 'IBAN': 'IBAN', 'ADDRESS': 'Dirección'},
                                            label=t('etl.privacy_field_type')
                                        ).props('dense outlined').classes('w-36')

                                        def add_field(col=col_name, selector=t_sel):
                                            if selector.value:
                                                design_state.anon_col_map[col] = selector.value
                                                if not hasattr(design_state, 'anon_strategies'): design_state.anon_strategies = {}
                                                design_state.anon_strategies[col] = 'masking'
                                                render_page.refresh()

                                        ui.button(t('etl.privacy_btn_add'), icon='add', on_click=add_field).props('flat dense color=blue')

    async def render_design_preview():
        if design_state.transformation_mode == 'assisted':
            with ui.column().classes('w-full gap-4'):
                ui.label(t('etl.preview_title_assisted')).classes('font-bold text-lg mb-4')
                
                if not design_state.operations:
                    ui.label(t('etl.preview_no_ops')).classes('text-red-500 italic')
                else:
                    try:
                        # Importar servicio aquí para evitar ciclos
                        from client_app.app.services.deterministic_etl_service import DeterministicETLService
                        from client_app.app.models.transform_operations import TransformOperation
                        
                        from pydantic import TypeAdapter, ValidationError
                        adapter = TypeAdapter(TransformOperation)

                        ops_models = []
                        valid_ops = True
                        for op in design_state.operations:
                             # Clean up UI-only keys
                             clean_op = {k: v for k, v in op.items() if not k.startswith('_')}
                             try:
                                 ops_models.append(adapter.validate_python(clean_op))
                             except ValidationError:
                                 valid_ops = False
                                 break
                        
                        if not valid_ops:
                            ui.label(t('etl.preview_incomplete_ops')).classes('text-orange-500 font-bold')
                            return

                        ui.label(t('etl.preview_generating')).classes('text-slate-500 italic')
                        
                        svc = DeterministicETLService()
                        # Usar copia de source_preview (head)
                        # Nota: execute_transformation es async, pero aquí estamos en contexto async
                        # Sin embargo, svc.execute_transformation toma un DF y devuelve un DF.
                        # Si es CPU-bound, mejor run_in_executor, pero por 10 filas no pasa nada.
                        input_df = design_state.source_preview.copy() if design_state.source_preview is not None else pd.DataFrame()
                        preview_df = await svc.execute_transformation(input_df, ops_models)
                        
                        if preview_df is not None:
                            ui.table.from_pandas(preview_df.head(5)).classes('w-full').props('dense flat')
                            ui.label(t('etl.preview_cols_result', cols=', '.join(preview_df.columns))).classes('text-xs text-slate-400 mt-2')

                        ui.separator().classes('my-4')
                        
                        # [NEW] Output Format Selector
                        with ui.row().classes('w-full items-center gap-4 p-4 border rounded-lg bg-slate-50'):
                            ui.label(t('etl.preview_output_fmt')).classes('font-bold text-slate-700')
                            formats = {'csv': 'CSV', 'xlsx': 'Excel', 'json': 'JSON', 'parquet': 'Parquet'}
                            ui.radio(formats, value=design_state.target_format).bind_value(design_state, 'target_format').props('inline dense')

                        with ui.row().classes('w-full justify-center gap-4 mt-6'):
                             # Check contextual state to conditionally render execute component
                             from client_app.app.core.state import app_state
                             is_flow_context = app_state.editing_flow and layout_manager.from_flow_context
                             
                             if not is_flow_context:
                                 # Green button for execution
                                 ui.button(t('etl.btn_execute'), icon='play_arrow', on_click=handle_assisted_execution)\
                                     .props('unelevated color=green-600')
                             
                             # Blue button for saving as atom
                             async def save_assisted_atom_dialog():
                                 from client_app.app.models.transform_operations import TransformOperation
                                 from client_app.app.services.deterministic_etl_service import DeterministicETLService
                                 from pydantic import TypeAdapter
                                 import hashlib
                                 from uuid import uuid4
                                 from pathlib import Path
                                 from client_app.app.services.asset_finishing_service import AssetFinishingService
                                 from client_app.app.database.models import ScriptLibrary
                                 
                                 design_state.is_sealing = True
                                 try:
                                     adapter = TypeAdapter(TransformOperation)
                                     ops_models = [adapter.validate_python({k: v for k, v in op.items() if not k.startswith('_')}) for op in design_state.operations]
                                     svc = DeterministicETLService()
                                     code = svc.generate_script(ops_models)
                                     
                                     async with state.db_session() as session:
                                         code_hash = hashlib.sha256(code.encode()).hexdigest()
                         
                                         storage_root = PROJECT_ROOT / "data" / "storage" / "scripts" / "src"
                                         storage_root.mkdir(parents=True, exist_ok=True)
                                         relative_path = f"etl_assisted_{uuid4().hex[:8]}.py"
                                         full_path = storage_root / relative_path
                         
                                         with open(full_path, "w", encoding="utf-8") as f:
                                             f.write(code)
                         
                                         atom_name = design_state.user_instructions[:50] if design_state.user_instructions else "Transformacion ETL Asistida"
                                         
                                         entry = ScriptLibrary(
                                             source_module='etl',
                                             name=atom_name,
                                             description="Flujo ETL generado con modo asistido",
                                             script_path=str(full_path),
                                             code_hash=code_hash,
                                             user_prompt="[Assisted] ETL",
                                             source_metadata={"operations": design_state.operations, "target_format": design_state.target_format},
                                             status='draft'
                                         )
                                         session.add(entry)
                                         await session.flush()
                         
                                         finisher = AssetFinishingService(session)
                                         await finisher.seal_resource(entry.id)
                                         await session.commit()
                                         script_id = entry.id
                                         
                                         # Actualizar el step en el flujo actual (contextual mode)
                                         from client_app.app.core.state import app_state
                                         if app_state.flow_context and app_state.flow_context.get('mode') == 'contextual':
                                             step = app_state.flow_context.get('step')
                                             if step:
                                                 step.config['config_id'] = script_id
                                                 step.config['script_id'] = script_id
                                                 # Actualizar all_steps_config para que el preview refleje los cambios
                                                 if app_state.editing_flow and hasattr(app_state.editing_flow, 'steps'):
                                                     app_state.refresh_flow_context_steps(app_state.editing_flow.steps)
                                                 app_state.on_step_change()
                         
                                     try:
                                         if hasattr(design_state, 'source_preview') and design_state.source_preview is not None:
                                             from client_app.app.services.script_library_service import script_library_service
                                             await script_library_service.update_script_sample_data(
                                                 script_id=script_id, 
                                                 data=design_state.source_preview, 
                                                 source="auto_etl"
                                             )
                                     except Exception as e:
                                         import logging
                                         logging.getLogger(__name__).warning(f"Error guardando sample_data en ETL (assisted): {e}")

                                     ui.notify(t('atoms.saved_success', 'Acción guardada correctamente en la biblioteca'), type='positive')
                                     go_to_library()
                                     await load_saved_etls()

                                 except Exception as e:
                                     ui.notify(f"Error al preparar guardado de acción: {e}", type='negative')
                                 finally:
                                     design_state.is_sealing = False

                             ui.button(t('etl.btn_save_atom'), icon='save', on_click=save_assisted_atom_dialog)\
                                 .props('unelevated color=blue')
                             
                             # [NEW] Open results button (visible after execution)
                             if getattr(design_state, 'execution_stats', {}).get('rows', 0) > 0:
                                 def open_folder():
                                     if design_state.output_file:
                                         os.startfile(os.path.dirname(design_state.output_file))
                                 ui.button(t('etl.btn_open_folder'), icon='folder_open', on_click=open_folder)\
                                     .props('outline color=slate-600')


                    except Exception as e:
                        ui.label(t('etl.preview_error', error=str(e))).classes('text-red-500 font-bold')

        elif design_state.is_generating:
            with ui.column().classes('w-full items-center p-12'):
                ui.spinner('comment', size='lg', color='green-600')
                ui.label(t('etl.ai_generating')).classes('mt-4 text-green-600 font-bold animate-pulse')
        elif design_state.generated_script:
            # Stats (Real)
            with ui.row().classes('w-full gap-4 mb-4'):
                with ui.card().classes('flex-1 p-4 border-t-4 border-green-500'):
                    ui.label(f"{design_state.execution_stats.get('rows', 0):,}").classes('text-2xl font-bold')
                    ui.label(t('etl.stats_rows')).classes('text-xs text-slate-500')
                with ui.card().classes('flex-1 p-4 border-t-4 border-blue-500'):
                    ui.label(f"{design_state.execution_stats.get('time_ms', 0)/1000:.2f}s").classes('text-2xl font-bold')
                    ui.label(t('etl.stats_time')).classes('text-xs text-slate-500')
                with ui.card().classes('flex-1 p-4 border-t-4 border-purple-500'):
                    ui.label(f"{design_state.execution_stats.get('size_kb', 0):.1f} KB").classes('text-2xl font-bold')
                    ui.label(t('etl.stats_size')).classes('text-xs text-slate-500')
            
            # Privacy Report
            if design_state.privacy_stats:
                render_privacy_report(design_state.privacy_stats)

            # Preview Table (Real execution on first rows)
            with ui.column().classes('w-full gap-4'):
                ui.label(t('etl.preview_results_title')).classes('font-bold text-slate-700')
                p_df = execute_preview()
                if p_df is not None:
                    ui.table.from_pandas(p_df).classes('w-full').props('dense flat bordered')
                
                with ui.expansion(t('etl.view_code'), icon='code').classes('w-full bg-slate-900 text-white rounded mt-4'):
                    ui.code(design_state.generated_script, language='python').classes('text-xs font-mono')
                
                with ui.row().classes('w-full justify-center gap-4 mt-4'):
                    ui.button(t('etl.btn_regenerate'), icon='refresh', on_click=show_feedback_dialog).props('outline color=orange')
                    ui.button(t('etl.btn_save_flow'), icon='save_as', on_click=save_as_flow_dialog).props('unelevated color=blue')
                    
                    if getattr(design_state, 'execution_stats', {}).get('rows', 0) > 0:
                        def open_folder():
                            if design_state.output_file:
                                os.startfile(os.path.dirname(design_state.output_file))
                        ui.button(t('etl.btn_open_folder'), icon='folder_open', on_click=open_folder)\
                            .props('outline color=slate-600')
        else:
            # Fallback: modo AI sin script generado
            # Verificar si ya hubo un error de generación previo para no reintentar automáticamente
            generation_error = getattr(design_state, 'generation_error', None)

            if generation_error:
                # Mostrar el error y opciones para el usuario
                with ui.column().classes('w-full items-center p-8 bg-red-50 rounded-lg border border-red-200'):
                    ui.icon('error', size='xl', color='red-600')
                    ui.label(t('etl.generation_failed', 'Error al generar el script de transformación')).classes('text-red-700 font-medium text-center mt-4')
                    ui.label(str(generation_error)).classes('text-red-600 text-sm text-center mt-2 max-w-lg')

                    with ui.row().classes('gap-4 mt-6'):
                        def retry_generation():
                            design_state.generation_error = None
                            render_page.refresh()

                        ui.button(t('etl.retry_generation', 'Reintentar'), icon='refresh',
                            on_click=retry_generation).props('unelevated color=red')
                        ui.button(t('etl.go_back_to_config', 'Volver a configuración'), icon='arrow_back',
                            on_click=lambda: (setattr(design_state, 'phase', 'config'), setattr(design_state, 'generation_error', None), update_drawer_stepper(), render_page.refresh())).props('flat color=red-700')
            else:
                # Intentar cargar source_preview desde data_source_selector_state si viene de flow_step/catalog
                if design_state.source_preview is None:
                    if design_state.data_source and design_state.data_source.source_type in ['catalog', 'flow_step']:
                        if hasattr(design_state, 'data_source_selector_state') and design_state.data_source_selector_state.preview_data:
                            design_state.source_preview = design_state.data_source_selector_state.preview_data.to_dataframe()
                            if design_state.source_preview is not None:
                                design_state.source_info = {
                                    'name': design_state.data_source.step_name or design_state.data_source.atom_name or 'datos_preview',
                                    'rows': len(design_state.source_preview),
                                    'columns': len(design_state.source_preview.columns),
                                    'column_names': list(design_state.source_preview.columns)
                                }
                                _update_global_data_context(design_state.source_preview)

                # Verificar si tenemos los datos necesarios para generar
                has_source = (
                    design_state.source_file or
                    design_state.source_preview is not None or
                    (design_state.data_source and design_state.data_source.source_type in ['catalog', 'flow_step'])
                )
                has_instructions = design_state.user_instructions and len(design_state.user_instructions.strip()) > 0

                if has_source and has_instructions and not design_state.is_generating:
                    # Tenemos todo, iniciar generación automáticamente
                    design_state.is_generating = True  # Marcar como generando para evitar duplicados
                    with ui.column().classes('w-full items-center p-12'):
                        ui.spinner('dots', size='xl', color='blue-600')
                        ui.label(t('etl.ai_starting_generation', 'Iniciando generación con IA...')).classes('mt-4 text-blue-600 font-medium')
                    # Disparar generación de forma asíncrona (capturar cliente para mantener contexto)
                    client = ui.context.client
                    async def _trigger_generation():
                        with client:
                            await generate_script()
                    asyncio.create_task(_trigger_generation())
                elif design_state.is_generating:
                    # Ya está generando, mostrar spinner
                    with ui.column().classes('w-full items-center p-12'):
                        ui.spinner('dots', size='xl', color='blue-600')
                        ui.label(t('etl.ai_generating', 'Generando script con IA...')).classes('mt-4 text-blue-600 font-medium')
                else:
                    # Faltan datos necesarios - mostrar qué falta y opciones
                    with ui.column().classes('w-full items-center p-8 bg-amber-50 rounded-lg border border-amber-200'):
                        ui.icon('warning', size='xl', color='amber-600')
                        if not has_source:
                            ui.label(t('etl.error_no_source', 'No hay datos de origen seleccionados.')).classes('text-amber-700 text-center mt-4')
                        elif not has_instructions:
                            ui.label(t('etl.error_no_instructions', 'No hay instrucciones para la transformación.')).classes('text-amber-700 text-center mt-4')

                        with ui.row().classes('gap-4 mt-4'):
                            ui.button(t('etl.go_back_to_config', 'Volver a configuración'), icon='arrow_back',
                                on_click=lambda: (setattr(design_state, 'phase', 'config'), update_drawer_stepper(), render_page.refresh())).props('flat color=amber-700')
                            # Si hay source pero no instructions, ofrecer abrir el ciclo de refinamiento
                            if has_source:
                                ui.button(t('etl.btn_add_instructions', 'Añadir instrucciones'), icon='edit',
                                    on_click=lambda: (setattr(design_state, 'phase', 'spec'), update_drawer_stepper(), render_page.refresh())).props('unelevated color=blue')

    async def render_execution():
        script = exec_state.script_entry
        if not script: return
        with ui.row().classes('w-full items-center gap-4 mb-6'):
            ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
            ui.label(t('etl.exec_title_prefix', name=script.name)).classes('text-2xl font-bold text-slate-800')
        with ui.card().classes('w-full max-w-4xl mx-auto p-8 shadow-md border-t-8 border-green-600'):
            ui.label(t('etl.exec_step1')).classes('text-lg font-bold mb-4')
            ui.upload(on_upload=handle_execution_upload, label=t('etl.exec_upload_label'), auto_upload=True).classes('w-full')
                
            if exec_state.source_file is not None:
                ui.label(t('etl.file_loaded', name=exec_state.filename)).classes('text-green-600 font-bold mt-2')
                ui.label(t('etl.exec_step2')).classes('text-lg font-bold mt-8 mb-4')
                ui.button(t('etl.exec_launch'), icon='bolt', on_click=handle_execution_run)\
                    .props('unelevated color=green-600 size=lg').classes('w-full py-4')
            
            if exec_state.is_running:
                with ui.column().classes('w-full items-center mt-6'):
                    ui.spinner('gears', size='lg', color='green')
                    ui.label(t('etl.exec_processing')).classes('mt-2 text-green-700 font-bold')

            if exec_state.execution_result:
                ui.separator().classes('my-8')
                with ui.row().classes('w-full items-center justify-between p-4 bg-green-50 rounded border border-green-200'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('check_circle', color='green', size='md')
                        ui.label(t('etl.exec_success')).classes('font-bold text-green-800')
                    ui.button(t('etl.exec_download'), icon='download', on_click=lambda: ui.download(exec_state.output_file_path))\
                        .props('unelevated color=green-700')
                    
                    def open_folder():
                        if exec_state.output_file_path:
                            os.startfile(os.path.dirname(exec_state.output_file_path))
                    ui.button(t('etl.exec_open_folder'), icon='folder_open', on_click=open_folder)\
                        .props('outline color=slate-600')
                    render_page.refresh()

    # --- HANDLERS ---

    async def handle_etl_upload(e):
        try:
            # Normalization to avoid issues
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            design_state.filename = safe_name
            f_path = ETL_UPLOAD_DIR / safe_name
            
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                 return
                 
            with open(f_path, 'wb') as f: f.write(content)
            
            design_state.source_file = str(f_path)
            design_state.source_format = detect_format(design_state.filename)
            df = await read_df(design_state.source_file, design_state.source_format)
            design_state.source_preview = df.head(10)
            design_state.source_info = {'name': design_state.filename, 'rows': len(df), 'columns': len(df.columns), 'column_names': list(df.columns)}
            _update_global_data_context(df)
            # Set target format to match source
            design_state.target_format = design_state.source_format
            render_page.refresh()
            ui.notify(t('etl.file_loaded', name=design_state.filename), type='positive')
        except Exception as ex: ui.notify(t('etl.upload_error', error=str(ex)), type='negative')

    async def handle_example_upload(e):
        try:
            # Normalization to avoid issues
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            f_path = ETL_UPLOAD_DIR / f"ex_{safe_name}"
            
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                 return
                 
            with open(f_path, 'wb') as f: f.write(content)
            fmt = detect_format(safe_name)
            df = await read_df(str(f_path), fmt)
            design_state.example_file = str(f_path); design_state.example_preview = df.head(10)
            design_state.target_spec = df; design_state.target_format = fmt
            render_page.refresh(); ui.notify(t('etl.example_loaded'), type='positive')
        except Exception as ex: ui.notify(t('etl.error_example', error=str(ex)), type='negative')

    async def run_clarification_analysis():
        if design_state.target_spec_mode != 'description':
            setattr(design_state, 'phase', 'config'); update_drawer_stepper(); render_page.refresh(); return
        design_state.is_analyzing = True; render_page.refresh()
        try:
            ctx = {"files": [design_state.source_info.get('name')], "columns": design_state.source_info.get('column_names', [])}
            res = await clarification_service.analyze_for_clarification("etl", {"prompt": design_state.user_instructions}, ctx)
            design_state.clarification_result = res
            if res.needs_clarification:
                show_clarification_dialog(res, lambda r: (setattr(design_state, 'clarification_responses', r), setattr(design_state, 'phase', 'config'), update_drawer_stepper(), render_page.refresh()), 
                                          lambda: (setattr(design_state, 'phase', 'config'), update_drawer_stepper(), render_page.refresh()))
            else: setattr(design_state, 'phase', 'config'); update_drawer_stepper(); render_page.refresh()
        finally: design_state.is_analyzing = False; render_page.refresh()


    async def generate_script(is_correction: bool = False):
        import logging
        logger = logging.getLogger(__name__)
        client = ui.context.client
        try:
            design_state.is_generating = True
            if not is_correction: setattr(design_state, 'phase', 'preview'); update_drawer_stepper()
            render_page.refresh()

            full_instr = design_state.user_instructions or ""
            if design_state.additional_instructions: full_instr += f"\n{design_state.additional_instructions}"

            logger.info(f"[ETL AI] Starting generation. Mode: {design_state.transformation_mode}, Instructions length: {len(full_instr)}")
            logger.info(f"[ETL AI] Source file: {design_state.source_file}")

            # Intentar cargar source_preview desde data_source_selector_state si viene de flow_step/catalog
            if design_state.source_preview is None:
                if design_state.data_source and design_state.data_source.source_type in ['catalog', 'flow_step']:
                    if hasattr(design_state, 'data_source_selector_state') and design_state.data_source_selector_state.preview_data:
                        design_state.source_preview = design_state.data_source_selector_state.preview_data.to_dataframe()
                        logger.info(f"[ETL AI] Loaded source_preview from data_source_selector_state: {len(design_state.source_preview)} rows")

            # Si source_file es None pero tenemos source_preview (datos de flow_step o catalog),
            # guardamos el DataFrame a un archivo temporal para poder ejecutar el pipeline
            source_file_path = design_state.source_file
            if source_file_path is None and design_state.source_preview is not None:
                temp_filename = f"temp_source_{uuid4().hex[:8]}.csv"
                temp_path = ETL_UPLOAD_DIR / temp_filename
                design_state.source_preview.to_csv(temp_path, index=False)
                source_file_path = str(temp_path)
                logger.info(f"[ETL AI] Created temp file from preview: {source_file_path}")

            if source_file_path is None:
                raise ValueError("No hay archivo fuente disponible. Carga un archivo o selecciona un paso anterior.")

            anon_cfg = {}
            if design_state.enable_anonymization:
                # Ensure strategies dict exists
                if not hasattr(design_state, 'anon_strategies'): design_state.anon_strategies = {}

                for col, field_type in design_state.anon_col_map.items():
                    ui_strat = design_state.anon_strategies.get(col, 'masking')

                    # Map UI strategy to Backend mode
                    backend_mode = 'FAKER'
                    if ui_strat == 'masking': backend_mode = 'MASK'
                    elif ui_strat == 'initials': backend_mode = 'INITIALS'
                    elif ui_strat == 'aepd': backend_mode = 'AEPD'

                    anon_cfg[col] = {
                        "type": field_type,
                        "mode": backend_mode
                    }

            async with state.db_session() as session:
                etl_svc = ETLService(session)
                design_state.execution_id = str(uuid4())
                out_path = ETL_UPLOAD_DIR / f"out_{design_state.execution_id}.{design_state.target_format}"
                design_state.output_file = str(out_path)  # Guardar referencia al archivo de salida

                logger.info(f"[ETL AI] Calling run_etl_pipeline with transformation_mode='ai', source_file={source_file_path}")
                result = await etl_svc.run_etl_pipeline(
                    execution_id=design_state.execution_id,
                    source_file=source_file_path,
                    target_spec=design_state.target_spec,
                    output_file=str(out_path),
                    output_format=design_state.target_format,
                    user_instructions=full_instr,
                    is_correction=is_correction,
                    transformation_mode='ai',  # Pasar explícitamente el modo
                    anonymization_config=anon_cfg if design_state.enable_anonymization else None
                )

                logger.info(f"[ETL AI] Pipeline result status: {result.get('status')}")
                logger.info(f"[ETL AI] Result keys: {result.keys()}")

                design_state.generated_script = result.get('script', '')
                design_state.privacy_stats = result.get('metadata', {}).get('privacy_stats', {})
                if result.get('status') == 'success':
                    design_state.result_data = result.get('data')
                    design_state.execution_stats = {
                        'rows': len(design_state.result_data) if design_state.result_data is not None else 0,
                        'time_ms': result.get('metadata', {}).get('execution_time_ms', 0),
                        'size_kb': out_path.stat().st_size / 1024 if out_path.exists() else 0
                    }
                    design_state.generation_error = None  # Limpiar error previo
                    logger.info(f"[ETL AI] Success! Rows: {design_state.execution_stats['rows']}")
                    with client:
                        ui.notify(t('etl.ai_success'), type='positive')
                else:
                    error_msg = result.get('error', 'Error desconocido en la generación')
                    logger.warning(f"[ETL AI] Pipeline did not return success. Result: {result}")
                    design_state.generation_error = error_msg
                    with client:
                        ui.notify(t('etl.ai_error', error=error_msg), type='negative')

            render_page.refresh()
        except Exception as ex:
            import traceback
            logger.error(f"[ETL AI] Error during generation: {ex}")
            logger.error(traceback.format_exc())
            design_state.generation_error = str(ex)
            with client:
                ui.notify(t('etl.ai_error', error=str(ex)), type='negative')
        finally:
            design_state.is_generating = False
            render_page.refresh()

    def execute_preview():
        """Real execution on slice for preview."""
        try:
            if not design_state.generated_script or design_state.source_preview is None: return None
            df_slice = design_state.source_preview.head(5).copy()
            namespace = {'pd': pd, 'df': df_slice}
            exec(design_state.generated_script, namespace)
            if 'transform' in namespace: return namespace['transform'](df_slice)
            return None
        except: return None

    async def show_feedback_dialog():
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label(t('etl.feedback_title')).classes('text-lg font-bold mb-4')
            feedback = ui.textarea(t('etl.feedback_label'), placeholder=t('etl.ai_desc_placeholder')).classes('w-full').props('outlined')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
                async def redo():
                    dialog.close(); design_state.user_instructions += f"\n\nCorrección: {feedback.value}"
                    await generate_script(is_correction=True)
                ui.button(t('etl.btn_redo'), on_click=redo).props('unelevated color=orange')
        dialog.open()

    async def save_as_flow_dialog():
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label(t('etl.btn_save_flow')).classes('text-lg font-bold mb-4')
            name_in = ui.input(t('etl.save_flow_name')).classes('w-full').props('outlined')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
                async def save():
                    if not name_in.value: ui.notify(t('etl.error_name_required'), type='warning'); return
                    dialog.close()
                    try:
                        async with state.db_session() as session:
                            await FlowRegistryService(session).create_etl_flow(
                                execution_id=design_state.execution_id, name=name_in.value
                            )
                        ui.notify(t('etl.flow_saved'), type='positive')
                    except Exception as e: ui.notify(t('common.error_prefix', error=str(e)), type='negative')
                ui.button(t('common.save'), on_click=save).props('unelevated color=blue')
        dialog.open()

    async def handle_execution_upload(e):
        try:
            # Normalization to avoid issues
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(t('etl.error_invalid_content', type=type(content).__name__), type='negative')
                 return
                 
            # Try to catch format from filename
            if safe_name.endswith('.csv'): exec_state.source_file = pd.read_csv(io.BytesIO(content))
            elif safe_name.endswith('.xlsx') or safe_name.endswith('.xls'): exec_state.source_file = pd.read_excel(io.BytesIO(content))
            elif safe_name.endswith('.json'): exec_state.source_file = pd.read_json(io.BytesIO(content))
            elif safe_name.endswith('.parquet'): exec_state.source_file = pd.read_parquet(io.BytesIO(content))
            else: exec_state.source_file = pd.read_csv(io.BytesIO(content)) # Default
            exec_state.filename = safe_name; ui.notify(t('etl.file_loaded', name=safe_name), type='positive'); render_page.refresh()
        except Exception as ex: ui.notify(t('common.error_prefix', error=str(ex)), type='negative')

    async def handle_execution_run():
        if not exec_state.source_file or not exec_state.script_entry: return
        exec_state.is_running = True; render_page.refresh()
        try:
            script_path = Path(exec_state.script_entry.script_path)
            if not script_path.exists(): raise FileNotFoundError("El archivo del script no existe")
            code = script_path.read_text()
            namespace = {'pd': pd, 'df': exec_state.source_file}
            exec(code, namespace)
            if 'transform' in namespace:
                res_df = namespace['transform'](exec_state.source_file)
                out_p = ETL_UPLOAD_DIR / f"run_{uuid4().hex[:8]}.csv"
                res_df.to_csv(out_p, index=False)
                exec_state.output_file_path = str(out_p)
                exec_state.execution_result = "Success"
                ui.notify(t('etl.exec_success_notif'), type='positive')
        except Exception as ex: 
            ui.notify(t('etl.exec_error_notif', error=str(ex)), type='negative')
            print(f"DEBUG ETL EXEC ERROR: {ex}")
        finally: exec_state.is_running = False; render_page.refresh()

    async def handle_assisted_execution():
        """Ejecuta la transformación determinista sobre el archivo completo."""
        # Permitir ejecución si hay source_file O source_preview (datos de flow_step/catalog)
        if not design_state.operations:
            ui.notify(t('etl.preview_no_ops'), type='warning')
            return
        if not design_state.source_file and design_state.source_preview is None:
            ui.notify(t('etl.error_no_source'), type='warning')
            return

        ui.notify(t('etl.starting_exec'), type='info')

        try:
            # 1. Leer archivo completo o usar preview si no hay archivo
            if design_state.source_file:
                df = await read_df(design_state.source_file, design_state.source_format)
            else:
                # Usar source_preview cuando datos vienen de flow_step o catalog
                df = design_state.source_preview.copy() if design_state.source_preview is not None else pd.DataFrame()
            
            # 2. Ejecutar Transformación
            from pydantic import TypeAdapter
            from client_app.app.services.deterministic_etl_service import DeterministicETLService
            adapter = TypeAdapter(TransformOperation)
            ops_models = [adapter.validate_python({k: v for k, v in op.items() if not k.startswith('_')}) for op in design_state.operations]
            svc = DeterministicETLService()
            
            # Ejecutar en thread pool para no bloquear UI si es grande
            # For simplicity using asyncio.to_thread for the heavy lifting if needed, 
            # but svc operations are synchronous pandas.
            result_df = await svc.execute_transformation(df, ops_models)
            
            # [NEW] Apply Anonymization
            if design_state.enable_anonymization:
                # Construct config (same logic as generate_script)
                anon_cfg = {}
                if not hasattr(design_state, 'anon_strategies'): design_state.anon_strategies = {}
                
                for col, field_type in design_state.anon_col_map.items():
                    ui_strat = design_state.anon_strategies.get(col, 'masking')
                    backend_mode = 'FAKER'
                    if ui_strat == 'masking': backend_mode = 'MASK'
                    elif ui_strat == 'initials': backend_mode = 'INITIALS'
                    elif ui_strat == 'aepd': backend_mode = 'AEPD'
                    
                    anon_cfg[col] = {"type": field_type, "mode": backend_mode}
                
                from client_app.app.modules.privacy.anonymizer import AnonymizationContext
                anon_ctx = AnonymizationContext()
                result_df = anon_ctx.anonymize_dataframe(result_df, anon_cfg)
            
            # 3. Guardar Resultado
            filename = f"run_assisted_{uuid4().hex[:8]}.{design_state.target_format}"
            out_path = ETL_UPLOAD_DIR / filename
            
            if design_state.target_format == 'csv': result_df.to_csv(out_path, index=False)
            elif design_state.target_format == 'xlsx': result_df.to_excel(out_path, index=False)
            elif design_state.target_format == 'json': result_df.to_json(out_path, orient='records')
            elif design_state.target_format == 'parquet': result_df.to_parquet(out_path)
            else: result_df.to_csv(out_path, index=False)
            
            # 4. Actualizar estado y notificar
            design_state.output_file = str(out_path)
            design_state.execution_stats = {
                'rows': len(result_df),
                'size_kb': out_path.stat().st_size / 1024,
                'time_ms': 0 # TODO: medir tiempo
            }
            
            ui.notify(t('etl.exec_complete'), type='positive')
            ui.download(str(out_path))
            render_page.refresh()
            
        except Exception as e:
            ui.notify(t('etl.exec_error_notif', error=str(e)), type='negative')
            print(f"DEBUG ETL ASSISTED ERROR: {e}")

    async def save_assisted_action_dialog():
        """Guarda la configuración actual como una Acción reutilizable."""
        suggested_name = naming_service.generate_provisional_name(
            StepType.ETL_TRANSFORM, 
            {'filename': design_state.filename, 'operations_count': len(design_state.operations)}
        )
        
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label(t('etl.save_atom_title')).classes('text-lg font-bold mb-4')
            name_in = ui.input(t('etl.save_atom_name'), value=suggested_name).classes('w-full').props('outlined autofocus')
            
            async def save():
                if not name_in.value: ui.notify(t('etl.error_name_required'), type='warning'); return
                dialog.close()
                try:
                    # 1. Generar Script Python
                    from pydantic import TypeAdapter
                    from client_app.app.models.transform_operations import TransformOperation
                    from client_app.app.services.deterministic_etl_service import DeterministicETLService

                    adapter = TypeAdapter(TransformOperation)
                    ops_models = [adapter.validate_python({k: v for k, v in op.items() if not k.startswith('_')}) for op in design_state.operations]

                    svc = DeterministicETLService()
                    script_content = svc.generate_script(ops_models)
                    
                    # [NEW] Inject Anonymization Logic if enabled
                    if design_state.enable_anonymization:
                        # Construct config dictionary
                        anon_cfg = {}
                        if not hasattr(design_state, 'anon_strategies'): design_state.anon_strategies = {}
                        for col, field_type in design_state.anon_col_map.items():
                            ui_strat = design_state.anon_strategies.get(col, 'masking')
                            backend_mode = 'FAKER'
                            if ui_strat == 'masking': backend_mode = 'MASK'
                            elif ui_strat == 'initials': backend_mode = 'INITIALS'
                            elif ui_strat == 'aepd': backend_mode = 'AEPD'
                            anon_cfg[col] = {"type": field_type, "mode": backend_mode}
                        
                        # Generate python code block
                        anon_code = f"""
    # --- Anonymization Step ---
    try:
        from client_app.app.modules.privacy.anonymizer import AnonymizationContext
        anon_cfg = {anon_cfg}
        ctx = AnonymizationContext()
        df = ctx.anonymize_dataframe(df, anon_cfg)
    except Exception as e:
        print(f"Warning: Anonymization failed: {{e}}")
"""
                        # Insert before return df (assuming generate_script returns a function 'transform(df)')
                        if "    return df" in script_content:
                             last_return_idx = script_content.rfind("    return df")
                             script_content = script_content[:last_return_idx] + anon_code + script_content[last_return_idx:]
                        else:
                             script_content += f"\n{anon_code}"
                    
                    # 2. Guardar archivo .py
                    script_name = f"atom_etl_{uuid4().hex[:8]}.py"
                    # Usar ruta estándar de scripts del sistema
                    script_dir = PROJECT_ROOT / "data" / "storage" / "scripts" / "src"
                    script_dir.mkdir(parents=True, exist_ok=True)
                    script_path = script_dir / script_name
                    script_path.write_text(script_content)
                    
                    # 3. Crear registro en ScriptLibrary
                    async with state.db_session() as session:
                        import hashlib
                        entry = ScriptLibrary(
                            source_module='etl',
                            name=name_in.value,
                            description=t('etl.save_atom_desc', date=datetime.now().strftime('%d/%m/%Y %H:%M')),
                            script_path=str(script_path),
                            code_hash=hashlib.sha256(script_content.encode()).hexdigest(),
                            status='validated', # Las acciones asistidas son seguras por definición
                            source_metadata={
                                'type': 'etl_atom',
                                'mode': 'assisted',
                                'operations': design_state.operations,
                                'target_format': design_state.target_format
                            }
                        )
                        session.add(entry)
                        # Sellar el recurso para que esté disponible
                        await session.flush()
                        await AssetFinishingService(session).seal_resource(entry.id)
                        await session.commit()
                        script_id = entry.id
                        
                    # Fase 4: Auto-captura de Sample Data
                    try:
                        if hasattr(design_state, 'result_data') and design_state.result_data is not None:
                            from client_app.app.services.script_library_service import script_library_service
                            await script_library_service.update_script_sample_data(
                                script_id=script_id, 
                                data=design_state.result_data, 
                                source="auto_etl"
                            )
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Error auto-capturando sample_data en ETL: {e}")
                        
                    ui.notify(t('etl.atom_saved'), type='positive')
                    
                except Exception as e:
                    ui.notify(t('etl.error_save', error=str(e)), type='negative')
            
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
                ui.button(t('common.save'), on_click=save).props('unelevated color=blue')
        
        dialog.open()

    # --- INITIALIZATION ---
    
    # Singleton-like guard for the content within the same client call
    if hasattr(ui.context.client, '_etl_rendered'):
        return
    ui.context.client._etl_rendered = True

    # 2. ASYNC INITIALIZATION (data loading)
    await load_saved_etls()

    # Si hay config_id del flujo, cargar el ETL
    if flow_config_id:
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, int(flow_config_id))
            if script:
                await edit_etl(script)

    # Mode refinement (if ID was provided for execution)
    if page_state.current_mode == 'execution' and page_state.selected_etl_id:
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, int(page_state.selected_etl_id))
            if script:
                exec_state.script_entry = script
                layout_manager.enter_execution_mode(str(script.id))

    await render_page()

    # Listen for drawer events
    ui.on('run_etl_analysis', lambda: run_clarification_analysis())




