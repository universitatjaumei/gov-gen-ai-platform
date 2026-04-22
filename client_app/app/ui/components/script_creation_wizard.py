from nicegui import ui
from typing import List, Optional, Callable
import uuid
import asyncio

from client_app.app.core.state import state
from client_app.app.services.script_generator_service import script_generator_service
from client_app.app.services.custom_script_service import custom_script_service
from client_app.app.services.clarification_service import clarification_service, ClarificationResponse
from client_app.app.modules.privacy.anonymizer import AnonymizationContext
from client_app.app.ui.components.clarification_dialog import show_clarification_dialog
from client_app.app.ui.components.escalation_dialog import show_escalation_dialog
from client_app.app.database.models import WizardDraft
from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.db import client_engine
from datetime import datetime

# --- LOGIC HELPERS ---

async def execute_test_logic(wizard, input_file: str, refresh):
    """Executes the generated script in sandbox."""
    wizard.is_executing = True
    refresh()
    
    try:
        from client_app.app.services.sandbox_service import SandboxExecutionService
        from shared.automatia_shared.core.execution_manager import ExecutionPathManager
        sandbox = SandboxExecutionService(ExecutionPathManager())

        execution_id = str(uuid.uuid4())
        result = await sandbox.execute_in_sandbox(
            code=wizard.generated_script['code'],
            file_paths=[input_file] if input_file else [],
            execution_id=execution_id
        )
        
        wizard.execution_result = result
        wizard.execution_status = 'success' if result.get('success') else 'error'
        wizard.execution_error = result.get('error')
        
    except Exception as e:
        wizard.execution_status = 'error'
        wizard.execution_error = str(e)
    finally:
        wizard.is_executing = False
        refresh()

async def refine_logic(wizard, feedback: str, refresh):
    """Refines script based on feedback."""
    if wizard.iteration_count >= 5:
        ui.notify('Max iterations reached, please escalate.', type='warning')
        return

    wizard.is_generating = True
    refresh()
    
    result = await script_generator_service.refine_script(
        original_code=wizard.generated_script['code'],
        user_feedback=feedback,
        error_message=wizard.execution_error,
        execution_result=str(wizard.execution_result.get('data')) if wizard.execution_result else None
    )
    
    if result.get('success'):
        wizard.generated_script = result
        # PROMPT 7: Auto-infer minimal UI Contract from script metadata if possible
        # For now we init empty or use what generator provides
        if 'ui_contract' not in wizard.generated_script:
             wizard.generated_script['ui_contract'] = {"inputs": [], "outputs": []}
        
        wizard.iteration_count += 1
        wizard.execution_result = None
        wizard.execution_status = None
        wizard.execution_error = None
        
    wizard.is_generating = False
    refresh()

async def escalate_logic(wizard, refresh):
    """Escalates the script to partner."""
    # Mock ID for prototype since script isn't saved yet
    script_id = 999 
    
    try:
        await custom_script_service.escalate_script(script_id, reason="User Request", client_notes=wizard.feedback_text)
        ui.notify('Script escalado al Partner', type='positive')
    except Exception as e:
        ui.notify(f'Error al escalar: {e}', type='negative')


# --- STATES ---

class WizardState:
    def __init__(self):
        self.phase = 'description'
        self.mode = 'ai' # 'ai', 'import'
        self.user_prompt = ""
        self.output_type = "file"
        self.generated_script: Optional[dict] = None
        
        # Import State
        self.import_state = ImportState()

        # UI States
        self.is_generating = False
        self.is_executing = False
        
        # Testing Phase
        self.test_input_file: Optional[str] = None
        self.execution_result: Optional[dict] = None
        self.execution_status: Optional[str] = None
        self.execution_error: Optional[str] = None
        
        # Refinement
        self.iteration_count = 0
        self.feedback_text = ""
        
        # Clarification
        self.clarification_responses: List[ClarificationResponse] = []
        self.clarification_skipped = False
        self.clarification_result = None
        self.clarification_callbacks = None

    def can_generate(self) -> bool:
        return len(self.user_prompt.strip()) >= 20

    def to_dict(self) -> dict:
        """Serializes current state to dict for persistence."""
        return {
            "phase": self.phase,
            "mode": self.mode,
            "user_prompt": self.user_prompt,
            "output_type": self.output_type,
            "iteration_count": self.iteration_count,
            "feedback_text": self.feedback_text,
            "test_input_file": self.test_input_file,
            "generated_script": self.generated_script
        }

    def from_dict(self, data: dict):
        """Restores state from dict."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

class ImportState:
    def __init__(self):
        self.file_content = None
        self.filename = ""
        self.description = ""
        self.audit_result = None
        self.auto_adapt = False
        self.target_type = "etl_transform"
        self.working = False


# --- COMPONENT ---

class ScriptCreationWizard(ui.column):
    def __init__(self):
        super().__init__()
        self.classes('w-full')
        self.state = WizardState()
        self.t = state.i18n.t
        
        # Load draft on init
        ui.timer(0.1, self.load_draft, once=True)
        self.render()

    async def save_draft(self):
        """Persists current wizard state to DB."""
        if not self.state.user_prompt and not self.state.generated_script:
            return  # Nothing to save
            
        draft_data = self.state.to_dict()
        state.editing_draft = draft_data
        
        try:
            async with AsyncSession(client_engine) as session:
                # Upsert draft
                query = select(WizardDraft).where(WizardDraft.wizard_type == "custom_script")
                result = await session.execute(query)
                draft = result.scalar_one_or_none()
                
                if not draft:
                    draft = WizardDraft(wizard_type="custom_script")
                
                draft.current_phase = self.state.phase
                draft.data = draft_data
                draft.updated_at = datetime.utcnow()
                
                session.add(draft)
                await session.commit()
                # print(f"[Wizard] Draft saved: {self.state.phase}")
        except Exception as e:
            print(f"[Wizard] Error saving draft: {e}")

    async def load_draft(self):
        """Tries to recovery draft from DB."""
        try:
            async with AsyncSession(client_engine) as session:
                query = select(WizardDraft).where(WizardDraft.wizard_type == "custom_script")
                result = await session.execute(query)
                draft = result.scalar_one_or_none()
                
                if draft:
                    self.state.from_dict(draft.data)
                    ui.notify("Borrador restaurado", icon='restore', type='info')
                    self.render.refresh()
        except Exception as e:
            print(f"[Wizard] Error loading draft: {e}")

    async def clear_draft(self):
        """Deletes draft from DB after successful save."""
        try:
            async with AsyncSession(client_engine) as session:
                await session.execute(delete(WizardDraft).where(WizardDraft.wizard_type == "custom_script"))
                await session.commit()
                state.editing_draft = None
        except Exception as e:
            print(f"[Wizard] Error clearing draft: {e}")

    @ui.refreshable
    def render(self):
        self.clear()
        wizard = self.state
        t = self.t

        with self:
            # Mode Toggle
            with ui.row().classes('w-full mb-6 gap-4 items-center justify-center bg-blue-50 p-2 rounded'):
                ui.label("Modo de Creación:").classes('font-bold text-slate-500')
                ui.toggle(
                    options={'ai': '✨ Generador IA', 'import': '📂 Importar Script'},
                    value=wizard.mode,
                    on_change=lambda e: (setattr(wizard, 'mode', e.value), asyncio.create_task(self.save_draft()), self.render.refresh())
                ).props('spread')

            if wizard.mode == 'ai':
                self.render_ai_wizard(wizard)
            else:
                self.render_import_wizard(wizard)

            # Clarification Dialog Trigger
            if wizard.phase == 'clarification' and wizard.clarification_result:
                 ui.timer(0.1, lambda: show_clarification_dialog(
                     wizard.clarification_result,
                     wizard.clarification_callbacks[0],
                     wizard.clarification_callbacks[1]
                 ), once=True)

    def render_ai_wizard(self, wizard):
        # Stepper
        self.render_stepper(wizard)
        
        if wizard.phase == 'description':
            self.render_description_phase(wizard)
        elif wizard.phase == 'generation':
            self.render_generation_phase(wizard)
        elif wizard.phase == 'testing':
            self.render_testing_phase(wizard)

    def render_stepper(self, wizard):
        with ui.row().classes('w-full items-center gap-4 mb-4'):
            steps = ['description', 'clarification', 'generation', 'testing', 'done']
            for i, step in enumerate(steps):
                active = step == wizard.phase
                passed = steps.index(wizard.phase) > i
                color = 'primary' if active or passed else 'grey'
                icon = 'check_circle' if passed else 'radio_button_checked'
                
                with ui.row().classes('items-center gap-2'):
                    ui.icon(icon, color=color)
                    ui.label(step.capitalize()).classes(f'text-{color} font-bold' if active else 'text-grey')
                
                if i < len(steps) - 1:
                    ui.separator().props('vertical').classes('h-4')
            
            if wizard.phase == 'testing':
                ui.chip(f'Iteración: {wizard.iteration_count}/5', icon='loop').props('outline')

    def render_description_phase(self, wizard):
        t = self.t
        with ui.card().classes('w-full p-4'):
            ui.label(t('custom.phase1', '1. Descripción')).classes('text-xl font-bold mb-4')
            
            ui.textarea(
                placeholder=t('custom.prompt_placeholder', 'Describe en detalle...'),
                on_change=lambda e: (setattr(wizard, 'user_prompt', e.value), asyncio.create_task(self.save_draft()))
            ).bind_value(wizard, 'user_prompt').classes('w-full').props('outlined rows=4')

            ui.label(t('custom.output_type', 'Resultado Esperado')).classes('font-bold mt-4')
            ui.radio(['file', 'text', 'dataframe'], 
                     on_change=lambda e: (setattr(wizard, 'output_type', e.value), asyncio.create_task(self.save_draft()))
            ).bind_value(wizard, 'output_type').props('inline')

            async def start_analysis():
                if not wizard.can_generate():
                    ui.notify('Descripción muy corta', type='warning'); return
                
                ui.spinner(size='lg'); ui.label('Analizando...')
                
                try:
                    result = await clarification_service.analyze_for_clarification(
                        module_type="custom_script",
                        user_input={"prompt": wizard.user_prompt},
                        context={} 
                    )
                    
                    if result.needs_clarification:
                        wizard.phase = 'clarification'
                        
                        def on_submit(responses):
                            wizard.clarification_responses = responses
                            wizard.phase = 'generation'
                            self.render.refresh()

                        def on_skip():
                            wizard.clarification_skipped = True
                            wizard.phase = 'generation'
                            self.render.refresh()
                            
                        wizard.clarification_result = result
                        wizard.clarification_callbacks = (on_submit, on_skip)
                        
                    else:
                        wizard.phase = 'generation'
                    
                    self.render.refresh()
                    
                except Exception as e:
                    ui.notify(f'Error en análisis: {str(e)}', type='negative')
                    wizard.phase = 'generation'
                    self.render.refresh()

            ui.button(t('custom.generate_btn', 'Generar Script'), on_click=start_analysis).classes('mt-4 bg-primary text-white')

    def render_generation_phase(self, wizard):
        with ui.card().classes('w-full p-4'):
            if not wizard.generated_script:
                ui.spinner(size='xl'); ui.label('Generando...')
                ui.timer(0.1, lambda: self.generate_logic(wizard), once=True)
                return
            
            res = wizard.generated_script
            with ui.row().classes('w-full gap-4'):
                ui.code(res['code'], language='python').classes('w-2/3 h-96 border rounded')
                with ui.column().classes('w-1/3'):
                    ui.markdown(res['description'])
                    for lib in res['required_libraries']: ui.chip(lib)
            
            if not wizard.is_executing:
                with ui.row().classes('w-full gap-2 items-center'):
                    ui.button('✨ Generar Script (IA)', on_click=lambda: asyncio.create_task(self.generate_logic(wizard))).props('color=primary').classes('flex-grow')
                    
                    # 🆘 Escalation Button
                    ui.button(icon='support_agent', on_click=lambda: asyncio.create_task(show_escalation_dialog(
                        asset_id=None,
                        asset_type="custom_script_wizard",
                        details={
                            "user_prompt": wizard.user_prompt,
                            "output_type": wizard.output_type,
                            "clarification_responses": wizard.clarification_responses,
                            "feedback_text": wizard.feedback_text
                        }
                    ))).props('flat color=orange').classes('ml-auto')
                ui.button('Probar Script', on_click=lambda: self.go_to_testing(wizard)).classes('bg-green-500 text-white ml-auto')

    def render_testing_phase(self, wizard):
        with ui.card().classes('w-full p-4'):
            ui.label('3. Prueba y Refinamiento').classes('text-xl font-bold mb-4')
            
            # Input Selection
            ui.label('Archivo de entrada (Opcional)').classes('font-bold')
            # For testing, we keep using the file input.
            # Persistence will happen on Save.
            
            async def handle_save():
                 if not wizard.generated_script: return
                 
                 try:
                     # Infer default contract if not present
                     contract = wizard.generated_script.get('ui_contract', {})
                     
                     # Call Service (Prompt 7)
                     script = await custom_script_service.create_script(
                         name=f"Script {wizard.user_prompt[:20]}...", # Auto-name
                         user_prompt=wizard.user_prompt,
                         code=wizard.generated_script['code'],
                         description=wizard.generated_script['description'],
                         required_libraries=wizard.generated_script['required_libraries'],
                         output_type=wizard.output_type,
                         ui_contract=contract
                     )
                     
                     ui.notify(f"Script guardado: {script.id}", type='positive')
                     await self.clear_draft()
                     
                     # Force refresh of selector in parent by navigating
                     ui.navigate.to(f'/custom-scripts?id={script.id}')
                     
                 except Exception as e:
                     ui.notify(f"Error guardando: {e}", type='negative')

            ui.input('Ruta del archivo', on_change=lambda e: (setattr(wizard, 'test_input_file', e.value), asyncio.create_task(self.save_draft()))).bind_value(wizard, 'test_input_file')
            
            if not wizard.is_executing:
                with ui.row().classes('w-full gap-2 items-center'):
                    ui.button('▶ Ejecutar Prueba', on_click=lambda: execute_test_logic(wizard, wizard.test_input_file, self.render.refresh)).classes('my-4 flex-grow')
                    
                    # 🆘 Escalation Button
                    ui.button(icon='support_agent', on_click=lambda: asyncio.create_task(show_escalation_dialog(
                        asset_id=None,
                        asset_type="custom_script_wizard_testing",
                        details={
                            "user_prompt": wizard.user_prompt,
                            "generated_script": wizard.generated_script,
                            "test_input": wizard.test_input_file
                        }
                    ))).props('flat color=orange').classes('ml-auto')
            else:
                ui.spinner(); ui.label('Ejecutando...')

            if wizard.execution_status:
                color = 'green' if wizard.execution_status == 'success' else 'red'
                with ui.card().classes(f'w-full bg-{color}-50 border-{color}-200 border p-4 mt-4'):
                    ui.label(f'Estado: {wizard.execution_status.upper()}').classes(f'text-{color}-700 font-bold')
                    if wizard.execution_error:
                        ui.label(f'Error: {wizard.execution_error}').classes('text-red-600')
                    if wizard.execution_result and wizard.execution_result.get('data'):
                        ui.json_editor({'content': {'json': wizard.execution_result['data']}}).classes('h-40')

                ui.separator().classes('my-4')
                ui.label('¿Es correcto el resultado?').classes('font-bold')
                with ui.row().classes('gap-4'):
                    # Save (Real Implementation Prompt 7)
                    ui.button('✅ Sí, Guardar', on_click=handle_save).classes('bg-green-600 text-white')
                    
                    with ui.expansion('❌ No, Refinar', icon='edit').classes('w-full bg-orange-50'):
                        ui.textarea('Describe el problema...', on_change=lambda e: setattr(wizard, 'feedback_text', e.value)).bind_value(wizard, 'feedback_text').classes('w-full')
                        with ui.row().classes('mt-2 gap-2'):
                            if not wizard.is_generating:
                                ui.button('🔄 Refinar Script', on_click=lambda: refine_logic(wizard, wizard.feedback_text, self.render.refresh)).classes('bg-orange-500 text-white')
                            else:
                                ui.spinner()
                            ui.button('🆘 Escalar al Partner', on_click=lambda: escalate_logic(wizard, self.render.refresh)).classes('bg-red-100 text-red-700')

    def render_import_wizard(self, wizard):
        istate = wizard.import_state
        with ui.card().classes('w-full p-6 shadow-sm border'):
            ui.label('Importar Script Python (.py)').classes('text-xl font-bold mb-4')
            
            if not istate.file_content:
                ui.upload(
                    on_upload=lambda e: self.handle_upload(e, wizard), 
                    label="Arrastra un archivo .py aquí", 
                    auto_upload=True
                ).props('accept=.py').classes('w-full')
            else:
                self.render_import_details(wizard)

    def render_import_details(self, wizard):
        istate = wizard.import_state
        with ui.row().classes('w-full gap-6'):
            with ui.column().classes('w-1/2'):
                ui.input('Nombre del Script').bind_value(istate, 'filename').classes('w-full')
                ui.textarea('Descripción').bind_value(istate, 'description').classes('w-full')
                
                ui.separator().classes('my-4')
                ui.checkbox('✨ Adaptar código con IA').bind_value(istate, 'auto_adapt')
                ui.select(
                    ['etl_transform', 'extraction', 'validation', 'automation'], 
                    label='Tipo of Tarea', 
                    value=istate.target_type
                ).bind_value(istate, 'target_type').classes('w-full')

                with ui.row().classes('mt-6 gap-2'):
                    ui.button('Cancelar', on_click=lambda: setattr(istate, 'file_content', None) or self.render.refresh()).props('flat')
                    
                    async def do_import():
                        from client_app.app.services.script_ingestion_service import script_ingestion_service
                        if not istate.file_content: return
                        istate.working = True; self.render.refresh()
                        try:
                            res = await script_ingestion_service.ingest_external_script(
                                filename=istate.filename, code=istate.file_content,
                                description=istate.description, auto_adapt=istate.auto_adapt,
                                target_type=istate.target_type
                            )
                            if res.success:
                                ui.notify('Script importado correctamente', type='positive')
                                ui.navigate.to('/custom-scripts') # Reload to list
                            else:
                                ui.notify(f"Error: {res.message}", type='negative')
                        except Exception as e:
                            ui.notify(f"Error crítico: {e}", type='negative')
                        finally:
                            istate.working = False; self.render.refresh()

                    btn = ui.button('Importar', on_click=do_import).classes('bg-green-600 text-white')
                    if istate.audit_result and not istate.audit_result.can_proceed_with_review:
                        btn.disable()
                    if istate.working: btn.props('loading')

            # Right: Audit & Preview
            with ui.column().classes('w-1/2'):
                ui.label('Auditoría de Seguridad').classes('font-bold')
                if istate.audit_result:
                    res = istate.audit_result
                    color = 'green' if res.is_safe else ('red' if not res.can_proceed_with_review else 'orange')
                    ui.card().classes(f'bg-{color}-50 p-2').style(f'border: 1px solid {color}').add(ui.label(res.summary))
                
                ui.code(istate.file_content, language='python').classes('w-full h-64 border rounded overflow-auto')


    async def handle_upload(self, e, wizard):
        try:
            # Normalization to avoid issues
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            
            content_raw = await e.file.read()
            if not isinstance(content_raw, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content_raw).__name__}).", type='negative')
                 return
                 
            content = content_raw.decode('utf-8')
            wizard.import_state.file_content = content
            wizard.import_state.filename = safe_name
            wizard.import_state.description = f"Importado: {e.name}"
            
            from client_app.app.services.external_script_audit_service import external_script_audit_service
            wizard.import_state.audit_result = external_script_audit_service.audit_script(content)
            self.render.refresh()
            ui.notify(f"Script cargado: {safe_name}", type='positive')
        except Exception as err:
            ui.notify(f"Error upload: {err}", type='negative')

    async def generate_logic(self, wizard):
        wizard.is_generating = True; self.render.refresh()
        
        anonymizer = AnonymizationContext(locale="es_ES")
        user_prompt_anon = anonymizer.anonymize(wizard.user_prompt)
        
        clarifications = {r.question_id: r.answer for r in wizard.clarification_responses} if wizard.clarification_responses else None

        try:
            wizard.generated_script = await script_generator_service.generate_script(
                user_prompt_anon, 
                output_type=wizard.output_type,
                clarifications=clarifications
            )
        except Exception as e:
            ui.notify(f"Error generación: {e}", type='negative')
        
        wizard.is_generating = False; self.render.refresh()

    def retry_generation(self, wizard):
        wizard.generated_script = None; self.render.refresh()

    def go_to_testing(self, wizard):
        wizard.phase = 'testing'; self.render.refresh()
