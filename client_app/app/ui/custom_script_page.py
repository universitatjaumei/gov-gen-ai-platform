from nicegui import ui, app
from typing import Optional, Dict, Any, List
from pathlib import Path
import asyncio
import uuid
import os
from datetime import datetime

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.form_factory import FormFactory, FormContext, AtomColorScheme
from client_app.app.services.custom_script_service import custom_script_service
from client_app.app.services.doc_generator_service import doc_generator
from client_app.app.ui.components.dynamic_form import DynamicExecutorForm
from client_app.app.ui.components.markdown_viewer import MarkdownViewer
from client_app.app.ui.components.escalation_dialog import show_escalation_dialog
from client_app.app.ui.components.clarification_dialog import show_clarification_dialog
from automatia_shared.contracts.ui_contract import UIContract
from client_app.app.services.sandbox_service import SandboxExecutionService
from shared.automatia_shared.core.execution_manager import ExecutionPathManager
from client_app.app.database.models import ScriptLibrary
from client_app.app.ui.components.unified_resource_card import unified_resource_card
from client_app.app.ui.components.data_source_selector import render_data_source_selector, DataSourceSelection, DataSourceSelectorState
from automatia_shared.enums import StepType
from client_app.app.services.script_library_service import script_library_service
from client_app.app.services.clarification_service import clarification_service, ClarificationResponse
from client_app.app.services.naming_service import naming_service
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.unified_resource_card import unified_resource_card

# Docs base path
DOCS_BASE_PATH = Path("data/storage/scripts/docs")

# --- STATE CLASSES ---

class CustomScriptPageState:
    def __init__(self):
        self.current_mode = 'library'
        self.selected_script_id: Optional[int] = None
        self.saved_scripts: List[ScriptLibrary] = []
        self.search_query = ""
        self.filter_status = 'all'

class ImportState:
    def __init__(self):
        self.file_content = None
        self.filename = ""
        self.audit_result = None
        self.auto_adapt = False
        self.target_type = "etl_transform"
        self.working = False

class DesignState:
    def __init__(self):
        self.script_name = ""
        self.user_prompt = ""
        self.generated_code = "# Python Code will appear here"
        self.is_generating = False
        self.creation_mode = 'ai' # 'ai', 'import'
        self.phase = 'definition' # 'definition', 'clarification', 'generation', 'testing'

        # Nombre provisional y descripción (nuevo patrón)
        self.provisional_name = ""
        self.description = ""
        self.editing_id: Optional[int] = None

        # Clarification
        self.clarification_result = None
        self.clarification_responses: List[ClarificationResponse] = []

        # Testing/Refinement
        self.iteration_count = 0
        self.test_input_file = ""
        self.execution_result = None
        self.execution_error = ""
        self.feedback_text = ""
        # Fuente de datos para prueba
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()

        # Import
        self.import_state = ImportState()

    def reset(self):
        self.__init__()

    def get_phase_index(self) -> int:
        """Retorna el índice de la fase actual para el stepper."""
        phases = ['definition', 'generation', 'testing']
        return phases.index(self.phase) if self.phase in phases else 0

class ExecutionState:
    def __init__(self):
        self.script_entry: Optional[ScriptLibrary] = None
        self.contract: Optional[UIContract] = None
        self.form_values: Dict[str, Any] = {}
        self.is_executing: bool = False
        self.execution_result: Optional[Dict] = None
        self.samples: List[Path] = []
        self.log_area = None

# --- PAGE CONTENT ---

async def custom_script_page_content(script_id: Optional[int] = None, initial_mode: Optional[str] = None):
    page_state = CustomScriptPageState()
    design_state = DesignState()
    exec_state = ExecutionState()
    path_manager = ExecutionPathManager()
    
    # --- HELPERS ---

    async def load_saved_scripts():
        query = page_state.search_query if page_state.search_query else None
        results = await script_library_service.search_scripts(query=query, source_module='custom')
        if page_state.filter_status != 'all':
            results = [s for s in results if s.status == page_state.filter_status]
        page_state.saved_scripts = results
        render_page.refresh()

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

        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()

    def start_new_design():
        page_state.current_mode = 'design'
        design_state.reset()
        # Generar nombre provisional
        design_state.provisional_name = naming_service.generate_provisional_name(
            StepType.CUSTOM_SCRIPT,
            config=None,
            index=len(page_state.saved_scripts) + 1
        )
        layout_manager.enter_design_mode(StepType.CUSTOM_SCRIPT)
        layout_manager.update_step_index(0)
        render_page.refresh()

    async def edit_script(script: ScriptLibrary):
        """Edita un script existente."""
        page_state.current_mode = 'design'
        design_state.reset()
        design_state.editing_id = script.id
        design_state.provisional_name = script.name
        design_state.description = script.description or ""
        design_state.user_prompt = script.user_prompt or ""
        design_state.generated_code = script.code or ""
        design_state.phase = 'generation'  # Skip definition ya que tiene código
        layout_manager.enter_design_mode(StepType.CUSTOM_SCRIPT, atom_id=str(script.id))
        layout_manager.update_step_index(design_state.get_phase_index())
        render_page.refresh()

    async def run_script(script: ScriptLibrary):
        page_state.current_mode = 'execution'
        exec_state.script_entry = script
        await load_execution_context(script.id)
        layout_manager.enter_execution_mode(str(script.id))
        render_page.refresh()

    async def load_execution_context(s_id: int):
        script = await custom_script_service.get_script(s_id)
        if script and script.ui_contract:
            try: exec_state.contract = UIContract(**script.ui_contract)
            except: exec_state.contract = UIContract(inputs=[])
        else: exec_state.contract = UIContract(inputs=[])
        sandbox_dir = path_manager.get_sandbox_dir(str(s_id))
        exec_state.samples = [f for f in sandbox_dir.iterdir() if f.is_file()] if sandbox_dir.exists() else []

    # --- RENDERERS ---

    @ui.refreshable
    async def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library': await render_library()
            elif page_state.current_mode == 'design': await render_design()
            elif page_state.current_mode == 'execution': await render_execution()

    async def toggle_favorite(resource):
        """Toggle favorito para un script."""
        script_id = resource.get('id')
        if script_id:
            await script_library_service.toggle_favorite(script_id)
            page_state.saved_scripts = await script_library_service.search_scripts(query=None, source_module='custom')
            render_page.refresh()

    async def render_library():
        # Ensure scripts are loaded
        if not page_state.saved_scripts:
            # We load all to let standard layout filter
            page_state.saved_scripts = await script_library_service.search_scripts(query=None, source_module='custom')

        # Map to resources
        resources = []
        for s in page_state.saved_scripts:
            resources.append({
                'id': s.id,
                'name': s.name,
                'description': s.description or 'Sin descripción',
                'status': s.status or 'draft',
                'source_module': 'custom',
                'doc_path': s.doc_path,
                'is_favorite': s.is_favorite,
                'created_at': s.created_at,
                '_original': s
            })

        layout = StandardPageLayout(
            title='Desarrollo de scripts Python',
            source_module='custom',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_script(r['_original']),
            on_delete=lambda r: delete_script(r['_original']),
            on_execute=lambda r: run_script(r['_original']),
            on_favorite_toggle=toggle_favorite,
            help_description='Crea, importa y valida lógica de procesamiento personalizada con ejecución en entornos seguros.',
            input_contract=['user_prompt', 'python_code', 'test_data'],
            output_contract=['execution_result', 'logs', 'generated_docs']
        )
        layout.render()

    async def render_design():
        t = state.i18n.t
        title = design_state.provisional_name if design_state.provisional_name else t('custom_script.new_script', 'Nuevo Script')

        with ui.row().classes('w-full items-center gap-4 mb-4'):
            ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
            ui.label(title).classes('text-2xl font-bold')
            ui.toggle({'ai': '✨ IA', 'import': '📂 Importar'}, value=design_state.creation_mode,
                      on_change=lambda e: (setattr(design_state, 'creation_mode', e.value), render_page.refresh())).props('unelevated rounded')

        if design_state.creation_mode == 'ai':
            await render_ai_design()
        else:
            await render_import_design()

    async def render_ai_design():
        # Nombres de los pasos para navegación
        STEP_DESCRIPTION = 'Descripción'
        STEP_GENERATION = 'Generación'
        STEP_VALIDATION = 'Validación y Sello'

        with ui.stepper().props('vertical').classes('w-full max-w-4xl') as stepper:
            with ui.step(STEP_DESCRIPTION):
                ui.textarea('Describe qué debe hacer el script').classes('w-full').props('outlined').bind_value(design_state, 'user_prompt')
                with ui.row().classes('w-full mt-4 justify-between'):
                    ui.button('Analizar con IA', on_click=handle_analysis).props('unelevated color=indigo')

            with ui.step(STEP_GENERATION):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('Código Generado').classes('font-bold')
                    ui.button('Regenerar', icon='refresh', on_click=handle_ai_generation).props('flat')
                if design_state.is_generating: ui.linear_progress(value=None).props('indeterminate')
                ui.codemirror(language='python').classes('h-64 border rounded').bind_value(design_state, 'generated_code')
                def go_to_testing():
                    design_state.phase = 'testing'
                    layout_manager.update_step_index(2)
                    stepper.set_value(STEP_VALIDATION)

                def go_to_definition():
                    design_state.phase = 'definition'
                    layout_manager.update_step_index(0)
                    stepper.set_value(STEP_DESCRIPTION)

                with ui.row().classes('w-full mt-4 justify-end gap-2'):
                    ui.button('Atrás', on_click=go_to_definition).props('flat')
                    ui.button('Probar Script', on_click=go_to_testing).props('unelevated color=indigo')

            with ui.step(STEP_VALIDATION):
                ui.label('Prueba tu script antes de sellarlo').classes('text-slate-500 mb-4')

                # Selector de fuente de datos para prueba
                with ui.expansion('Datos de Prueba (opcional)', icon='folder_open').classes('w-full bg-slate-50 rounded mb-4'):
                    def handle_test_source_selection(selection: DataSourceSelection):
                        design_state.data_source = selection
                        if selection.source_type == 'manual' and selection.file_path:
                            design_state.test_input_file = selection.file_path
                            ui.notify(f'Archivo seleccionado: {selection.file_name}', type='info')
                        elif selection.source_type == 'catalog':
                            ui.notify(state.i18n.t('etl.source_atom', name=selection.atom_name), type='info')
                        elif selection.source_type == 'flow_step':
                            ui.notify(f'Datos del paso: {selection.step_name}', type='info')

                    render_data_source_selector(
                        consumer_type=StepType.CUSTOM_SCRIPT,
                        on_source_selected=handle_test_source_selection,
                        flow_context=state.flow_context,
                        initial_selection=design_state.data_source,
                        selector_state_override=design_state.data_source_selector_state,
                        compact=True,
                        upload_formats_override=['csv', 'xlsx', 'json', 'xml', 'parquet']
                    )

                with ui.row().classes('w-full gap-2 my-4'):
                    ui.button('Ejecutar Prueba', icon='play_circle', on_click=handle_design_test).props('unelevated color=green-600').bind_enabled_from(design_state, 'is_generating', backward=lambda x: not x)
                    ui.button('Escalar Ayuda', icon='support_agent', on_click=handle_design_escalation).props('flat color=orange')

                if design_state.execution_error:
                    ui.label(f"Error: {design_state.execution_error}").classes('text-red-500 font-mono text-xs p-2 bg-red-50 rounded')

                if design_state.execution_result:
                    ui.label("Resultado de prueba:").classes('text-xs font-bold')
                    ui.json_editor({'content': {'json': design_state.execution_result}}).classes('h-32')

                if design_state.execution_result or design_state.execution_error:
                    with ui.expansion('No es correcto, Refinar', icon='edit').classes('w-full bg-orange-50 border border-orange-200 mt-4 rounded-lg'):
                        ui.textarea('Describe qué falla o que quieres cambiar...').classes('w-full bg-white').props('outlined')\
                            .bind_value(design_state, 'feedback_text')

                        with ui.row().classes('w-full mt-2 justify-between items-center'):
                            ui.label(f'Iteración: {design_state.iteration_count}/5').classes('text-[10px] text-orange-700 font-bold')
                            ui.button('Refinar Script', icon='refresh', on_click=handle_refine)\
                                .props('unelevated color=orange-600')\
                                .bind_enabled_from(design_state, 'is_generating', backward=lambda x: not x)

                def go_back_to_generation():
                    design_state.phase = 'generation'
                    layout_manager.update_step_index(1)
                    stepper.set_value(STEP_GENERATION)

                with ui.row().classes('w-full mt-6 justify-end gap-2 items-center'):
                    ui.button('ATRÁS', on_click=go_back_to_generation).props('flat color=slate')
                    ui.button('GUARDAR Y SELLAR', icon='check_circle', on_click=handle_seal).props('unelevated color=primary shadow')

    async def render_import_design():
        istate = design_state.import_state
        with ui.card().classes('w-full p-6'):
            if not istate.file_content:
                ui.upload(on_upload=handle_import_upload, label="Subir script .py", auto_upload=True).props('accept=.py').classes('w-full')
            else:
                with ui.row().classes('w-full gap-6'):
                    with ui.column().classes('w-1/2'):
                        ui.input('Nombre').bind_value(istate, 'filename').classes('w-full')
                        ui.checkbox('Adaptar con IA').bind_value(istate, 'auto_adapt')
                        ui.button('Importar Script', on_click=handle_import_confirm, icon='download').props('unelevated color=green').classes('w-full mt-4')
                    with ui.column().classes('w-1/2'):
                        ui.label('Auditoría de Seguridad').classes('font-bold')
                        if istate.audit_result:
                            color = 'green' if istate.audit_result.is_safe else ('red' if not istate.audit_result.can_proceed_with_review else 'orange')
                            ui.label(istate.audit_result.summary).classes(f'text-{color}-600 text-xs p-2 bg-{color}-50 rounded')
                        ui.code(istate.file_content).classes('w-full h-64 border rounded overflow-auto')

    async def render_execution():
        script = exec_state.script_entry
        with ui.row().classes('w-full items-center gap-4 mb-6'):
            ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
            ui.label(script.name).classes('text-2xl font-bold text-slate-800')
            ui.chip(script.status.upper(), icon='verified').props('outline color=indigo')

        with ui.row().classes('w-full gap-6'):
            with ui.column().classes('w-1/3 gap-4'):
                with ui.card().classes('w-full p-4'):
                    ui.label('Configuración').classes('text-lg font-bold mb-4')
                    form = DynamicExecutorForm(exec_state.contract, on_submit=handle_execution_run)
                    ui.button('Ejecutar Script', icon='play_arrow', on_click=lambda: form.handle_submit()).props('unelevated color=green-600').classes('w-full mt-4').bind_enabled_from(exec_state, 'is_executing', backward=lambda x: not x)

                with ui.card().classes('w-full p-4'):
                    ui.label('Muestras (Sandbox)').classes('font-bold text-xs text-slate-400')
                    ui.upload(on_upload=handle_sample_upload, auto_upload=True).props('dense flat')
                    for s in exec_state.samples:
                        with ui.row().classes('w-full items-center justify-between p-1 border-b'):
                            ui.label(s.name).classes('text-[10px] truncate')
                            ui.button(icon='delete', on_click=lambda f=s: (f.unlink(), load_execution_context(script.id), render_page.refresh())).props('flat dense size=xs color=red')

                with ui.expansion('Documentación', icon='description').classes('w-full border rounded'):
                    MarkdownViewer(file_path=DOCS_BASE_PATH / f"{script.id}.md", script_id=script.id, allow_generation=True).render()

            with ui.column().classes('w-2/3 gap-4'):
                with ui.card().classes('w-full h-80 bg-slate-900 text-green-400 p-0 overflow-hidden flex flex-col'):
                    ui.label('Log de Salida').classes('text-[10px] font-bold text-slate-500 p-2 bg-slate-800')
                    exec_state.log_area = ui.log(max_lines=1000).classes('w-full flex-grow font-mono text-xs p-2')
                
                if exec_state.execution_result:
                    with ui.card().classes('w-full p-4'):
                        ui.label('Resultados').classes('font-bold mb-2')
                        res = exec_state.execution_result
                        if 'table' in res:
                            cols = [{"name": c, "label": c, "field": c} for c in res['table'][0].keys()] if res['table'] else []
                            ui.table(columns=cols, rows=res['table'], pagination=5).classes('w-full dense')
                        elif 'file' in res:
                            ui.button('Descargar', icon='download', on_click=lambda: ui.download(res['file'])).props('outline color=indigo')
                        else:
                            ui.json_editor({'content': {'json': res}}).classes('h-48')

    # --- HANDLERS ---

    async def handle_analysis():
        if not design_state.user_prompt or len(design_state.user_prompt) < 20:
            return ui.notify("Describe con más detalle (mín 20 chars)", type='warning')
        try:
            res = await clarification_service.analyze_for_clarification(module_type="custom_script", user_input={"prompt": design_state.user_prompt})
            if res.needs_clarification:
                show_clarification_dialog(res, on_submit=lambda r: (setattr(design_state, 'clarification_responses', r), handle_ai_generation()), on_skip=handle_ai_generation)
            else:
                await handle_ai_generation()
        except Exception as e: ui.notify(f"Error análisis: {e}", type='negative')

    async def handle_ai_generation():
        design_state.is_generating = True; render_page.refresh()
        try:
            from client_app.app.services.script_generator_service import script_generator_service
            from client_app.app.modules.privacy.anonymizer import AnonymizationContext

            anonymizer = AnonymizationContext(locale="es_ES")
            prompt_anon = anonymizer.anonymize(design_state.user_prompt)

            clarifs = {r.question_id: r.answer for r in design_state.clarification_responses} if design_state.clarification_responses else None
            res = await script_generator_service.generate_script(prompt_anon, output_type="file", clarifications=clarifs)
            if res.get('success'):
                # Rehydrate code to restore original values
                code = anonymizer.deanonymize(res.get('code', ""))
                design_state.generated_code = code
                design_state.phase = 'generation'
                # Actualizar nombre provisional basado en el prompt
                if design_state.user_prompt and not design_state.editing_id:
                    preview = design_state.user_prompt[:35].strip()
                    design_state.provisional_name = f"Script: {preview}..."
                layout_manager.update_step_index(design_state.get_phase_index())
                render_page.refresh()
            else: ui.notify(f"IA Error: {res.get('error')}", type='negative')
        except Exception as e: ui.notify(str(e), type='negative')
        finally: design_state.is_generating = False; render_page.refresh()

    async def handle_design_test():
        design_state.is_generating = True; render_page.refresh()
        try:
            import tempfile
            import pathlib
            test_files = []
            
            if design_state.data_source:
                sel = design_state.data_source
                if sel.source_type == 'manual':
                    if getattr(sel, 'file_path', None):
                        test_files.append(sel.file_path)
                    elif sel.file_content:
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{sel.file_name}" if sel.file_name else ".bin")
                        tmp.write(sel.file_content)
                        tmp.close()
                        test_files.append(tmp.name)
                elif sel.source_type in ['flow_step', 'catalog']:
                    selector_state = getattr(design_state, 'data_source_selector_state', None)
                    if selector_state and hasattr(selector_state, 'preview_data') and selector_state.preview_data:
                        preview = selector_state.preview_data
                        if 'path' in getattr(preview, 'columns', []):
                            for row in getattr(preview, 'rows', []):
                                p = row.get('path', '')
                                if p and pathlib.Path(p).is_file():
                                    test_files.append(p)
                        else:
                            try:
                                df = preview.to_dataframe()
                                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
                                df.to_csv(tmp.name, index=False)
                                test_files.append(tmp.name)
                            except Exception as e:
                                pass

            sandbox = SandboxExecutionService(path_manager)
            res = await sandbox.execute_in_sandbox(code=design_state.generated_code, file_paths=test_files, execution_id=str(uuid.uuid4()))
            design_state.execution_result = res.get('data')
            design_state.execution_error = res.get('error') or ""
        except Exception as e: design_state.execution_error = str(e)
        finally: design_state.is_generating = False; render_page.refresh()

    def show_save_dialog():
        """Muestra el diálogo de guardado con nombre editable."""
        t = state.i18n.t

        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label(t('custom_script.save_title', 'Guardar Script Python')).classes('text-xl font-bold mb-4')

            # Campo de nombre editable
            name_input = ui.input(
                label=t('custom_script.name', 'Nombre'),
                value=design_state.provisional_name
            ).classes('w-full mb-3').props('outlined')

            # Campo de descripción
            desc_input = ui.textarea(
                label=t('custom_script.description', 'Descripción (opcional)'),
                value=design_state.description
            ).classes('w-full mb-4').props('outlined rows=2')

            # Preview del código
            with ui.expansion(t('custom_script.code_preview', 'Vista previa del código'), icon='code').classes('w-full mb-4'):
                ui.code(design_state.generated_code[:500] + ('...' if len(design_state.generated_code) > 500 else '')).classes('text-xs')

            # Contrato de salida
            with ui.expansion(t('custom_script.output_contract', 'Contrato de salida'), icon='output').classes('w-full mb-4'):
                output_fields = [
                    {'name': 'execution_result', 'type': 'object'},
                    {'name': 'logs', 'type': 'array'},
                    {'name': 'execution_time_ms', 'type': 'integer'},
                    {'name': 'success', 'type': 'boolean'},
                ]
                for field in output_fields:
                    with ui.row().classes('items-center gap-2'):
                        ui.chip(field['name'], icon='data_object').props('dense size=sm outline')
                        ui.label(f": {field['type']}").classes('text-xs text-slate-500')

            # Botones
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel', 'Cancelar'), on_click=dialog.close).props('flat')
                ui.button(
                    t('custom_script.save_and_seal', 'Guardar y Sellar'),
                    icon='check_circle',
                    on_click=lambda: handle_save_confirmed(name_input.value, desc_input.value, dialog)
                ).props('unelevated color=primary')

        dialog.open()

    async def handle_seal():
        """Muestra el diálogo de guardado."""
        show_save_dialog()

    async def handle_save_confirmed(name: str, description: str, dialog):
        """Guarda el script con el nombre y descripción proporcionados."""
        if not name.strip():
            ui.notify("El nombre es obligatorio", type='warning')
            return

        dialog.close()

        # Mostrar spinner mientras guarda
        with ui.dialog() as spinner_dialog, ui.card().classes('p-6 items-center'):
            ui.spinner(size='lg')
            ui.label('Guardando...').classes('text-lg font-bold mt-4')
        spinner_dialog.open()

        try:
            if design_state.editing_id:
                # Actualizar existente via script_library_service
                await script_library_service.update_script(
                    script_id=design_state.editing_id,
                    name=name,
                    description=description,
                    user_prompt=design_state.user_prompt,
                    code=design_state.generated_code
                )
                script_id = design_state.editing_id
            else:
                # Crear nuevo via custom_script_service
                script = await custom_script_service.create_script(
                    name=name,
                    user_prompt=design_state.user_prompt,
                    code=design_state.generated_code,
                    description=description
                )
                script_id = script.id if script else None

            # Actualizar step.config si estamos en modo contextual de flujo
            is_flow = state.flow_context and state.flow_context.get('mode') == 'contextual'
            if is_flow and script_id:
                step = state.flow_context.get('step')
                if step:
                    step.config['config_id'] = script_id
                    step.config['script_id'] = script_id
                    if state.editing_flow and hasattr(state.editing_flow, 'steps'):
                        state.refresh_flow_context_steps(state.editing_flow.steps)
                    if hasattr(state, 'on_step_change') and callable(state.on_step_change):
                        state.on_step_change()

            ui.notify("Script guardado correctamente", type='positive')
            spinner_dialog.close()
            await load_saved_scripts()
            if is_flow or (state.editing_flow and getattr(state, 'flow_id', None)):
                go_to_library()
        except Exception as e:
            spinner_dialog.close()
            ui.notify(f"Error: {e}", type='negative')

    async def handle_refine():
        if design_state.iteration_count >= 5:
            # Auto-escalate instead of just notifying
            ui.notify("Límite de iteraciones alcanzado. Escalando al soporte...", type='warning')
            await handle_design_escalation()
            return
        if not design_state.feedback_text:
            return ui.notify("Escribe qué quieres refinar", type='warning')

        design_state.is_generating = True
        render_page.refresh()
        try:
            from client_app.app.services.script_generator_service import script_generator_service
            from client_app.app.modules.privacy.anonymizer import AnonymizationContext

            # Anonymize feedback before sending to LLM
            anonymizer = AnonymizationContext(locale="es_ES")
            feedback_anon = anonymizer.anonymize(design_state.feedback_text)
            error_anon = anonymizer.anonymize(design_state.execution_error) if design_state.execution_error else None
            code_anon = anonymizer.anonymize(design_state.generated_code)

            res = await script_generator_service.refine_script(
                original_code=code_anon,
                user_feedback=feedback_anon,
                error_message=error_anon,
                execution_result=str(design_state.execution_result) if design_state.execution_result else None
            )
            if res.get('success'):
                # Rehydrate refined code
                refined_code = anonymizer.deanonymize(res.get('code', ""))
                design_state.generated_code = refined_code
                design_state.iteration_count += 1
                design_state.execution_error = ""
                design_state.execution_result = None
                design_state.feedback_text = ""
                ui.notify("Script refinado", type='positive')
            else:
                ui.notify(f"Error refinando: {res.get('error')}", type='negative')
        except Exception as e:
            ui.notify(str(e), type='negative')
        finally:
            design_state.is_generating = False
            render_page.refresh()

    async def handle_import_upload(e):
        try:
            # Normalization to avoid issues
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            
            content_raw = await e.file.read()
            if not isinstance(content_raw, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content_raw).__name__}).", type='negative')
                 return
            
            content = content_raw.decode('utf-8')
            istate = design_state.import_state
            
            istate.file_content = content; istate.filename = safe_name; istate.description = f"Importado: {e.name}"
            from client_app.app.services.external_script_audit_service import external_script_audit_service
            istate.audit_result = external_script_audit_service.audit_script(content)
            render_page.refresh()
            ui.notify(f"Script importado: {safe_name}", type='positive')
        except Exception as ex: ui.notify(str(ex), type='negative')

    async def handle_import_confirm():
        istate = design_state.import_state
        if istate.audit_result and not istate.audit_result.can_proceed_with_review:
            return ui.notify("Bloqueado por seguridad: El script contiene código peligroso.", type='negative')
            
        try:
            from client_app.app.services.custom_script_service import custom_script_service
            res = await custom_script_service.import_script(istate.file_content, istate.filename)
            is_flow = state.flow_context and state.flow_context.get('mode') == 'contextual'
            if res.success: 
                ui.notify("Importado", type='positive')
                await load_saved_scripts()
                if is_flow or (state.editing_flow and getattr(state, 'flow_id', None)):
                    go_to_library()
            else: ui.notify(res.message, type='negative')
        except Exception as e: ui.notify(str(e), type='negative')

    async def handle_execution_run(values):
        exec_state.is_executing = True; render_page.refresh()
        try:
            sandbox = SandboxExecutionService(path_manager)
            exec_state.log_area.push(f"--- Ejecución {datetime.now().strftime('%H:%M:%S')} ---")
            sandbox_dir = path_manager.get_sandbox_dir(str(exec_state.script_entry.id))
            samples = [str(f.resolve()) for f in sandbox_dir.iterdir() if f.is_file()] if sandbox_dir.exists() else []
            res = await sandbox.execute_in_sandbox(code=exec_state.script_entry.code, file_paths=samples, execution_id=str(uuid.uuid4()))
            exec_state.execution_result = res.get('data')
            if res.get('error'): exec_state.log_area.push(f"ERROR: {res.get('error')}")
            else: exec_state.log_area.push("Síncrono completado con éxito.")
        except Exception as e: ui.notify(str(e), type='negative')
        finally: exec_state.is_executing = False; render_page.refresh()

    async def handle_sample_upload(e):
        try:
            sandbox_dir = path_manager.get_sandbox_dir(str(exec_state.script_entry.id))
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            
            # Normalization to avoid issues
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            
            target = sandbox_dir / safe_name
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                 return
                 
            target.write_bytes(content)
            ui.notify(f"Subido: {safe_name}", type='positive')
            await load_execution_context(exec_state.script_entry.id)
            render_page.refresh()
        except Exception as ex: ui.notify(f"Error: {ex}", type='negative')

    async def delete_script(s):
        try:
            await script_library_service.delete_script(s.id, force=True)
            ui.notify("Script eliminado")
            await load_saved_scripts()
        except Exception as e: ui.notify(str(e), type='negative')

    async def handle_design_escalation():
        await show_escalation_dialog(asset_id=None, asset_type="custom_script_wizard", details={"prompt": design_state.user_prompt})

    # --- INITIAL LAYOUT SETUP ---
    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        design_state.reset()
        layout_manager.enter_design_mode(StepType.CUSTOM_SCRIPT, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif script_id:
        script_obj = await custom_script_service.get_script(int(script_id))
        if script_obj: await run_script(script_obj)
    elif initial_mode == 'design':
        start_new_design()
    else:
        layout_manager.exit_focus_mode()

    await load_saved_scripts()

    # Si hay config_id del flujo, cargar el script
    if flow_config_id:
        script_obj = await custom_script_service.get_script(int(flow_config_id))
        if script_obj:
            await edit_script(script_obj)

    await render_page()
