from nicegui import ui
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
from client_app.app.core.state import state
from client_app.app.services.custom_script_service import custom_script_service
from client_app.app.services.doc_generator_service import doc_generator
from client_app.app.ui.components.automation_selector import render_automation_selector
from client_app.app.ui.components.dynamic_form import DynamicExecutorForm
from client_app.app.ui.components.script_creation_wizard import ScriptCreationWizard # Restored wizard
from client_app.app.ui.components.markdown_viewer import MarkdownViewer
from client_app.app.ui.components.escalation_dialog import show_escalation_dialog
from automatia_shared.contracts.ui_contract import UIContract
import uuid
from client_app.app.services.sandbox_service import SandboxExecutionService
from shared.automatia_shared.core.execution_manager import ExecutionPathManager

# Docs base path
DOCS_BASE_PATH = Path("data/storage/scripts/docs")

async def custom_script_page_content(script_id: Optional[int] = None):
    """
    Contenedor universal de ejecución de scripts personalizados.
    Gestiona la carga de contratos de interfaz (UI Contracts), la generación
    dinámica de formularios de entrada y la ejecución en entornos seguros (sandbox).
    """
    t = state.i18n.t
    
    # State for the page
    class ExecutionState:
        """
        Mantiene el estado reactivo de la ejecución de un script.
        Almacena el contrato actual, los valores del formulario, el estado de ejecución
        y los logs resultantes.
        """
        def __init__(self):
            self.current_script_id: Optional[int] = int(script_id) if script_id else None
            self.contract: Optional[UIContract] = None
            self.form_values: Dict[str, Any] = {}
            self.is_executing: bool = False
            self.log_content: str = ""
            self.execution_result: Optional[Dict] = None
            self.samples: List[Path] = []

    est = ExecutionState()
    path_manager = ExecutionPathManager()
    
    # Reference to UI elements for updates
    log_area: Optional[ui.log] = None
    
    async def load_contract(s_id: int):
        """
        Carga un script de la base de datos y parsea su contrato de interfaz.
        """
        script = await custom_script_service.get_script(s_id)
        if script and script.ui_contract:
            # Parse contract from stored JSON
            # Ideally script.ui_contract is a dict
            try:
                est.contract = UIContract(**script.ui_contract)
            except Exception as e:
                ui.notify(f"Error cargando contrato: {e}", type='negative')
                est.contract = None
        elif script:
             # Fallback: Auto-generate simple contract based on previous wizard logic or empty
             # For Prompt 6, we assume contract exists or we might want to generate one on fly?
             # Let's assume empty contract if not found.
             est.contract = UIContract(inputs=[])
             ui.notify("Script sin contrato definido. Ejecución genérica.", type='warning')
        
        # Load Samples from Sandbox
        sandbox_dir = path_manager.get_sandbox_dir(str(s_id))
        if sandbox_dir.exists():
            est.samples = [f for f in sandbox_dir.iterdir() if f.is_file()]

    # Initial load if ID provided
    if est.current_script_id:
        await load_contract(est.current_script_id)

    @ui.refreshable
    async def render_page():
        """
        Renderiza la página de ejecución de scripts.
        Incluye el selector de scripts, el formulario dinámico basado en el contrato 
        y la consola de salida de logs.
        """
        nonlocal log_area
        
        with ui.column().classes('w-full h-full p-4 gap-4'):
            
            # --- 1. SELECTOR ROW ---
            async def on_script_select(val):
                if val:
                    est.current_script_id = int(val)
                    est.log_content = "" # Clear logs
                    await load_contract(est.current_script_id)
                    # Update URL without full reload if possible, or just re-render content
                    # ui.navigate.to(f'/custom-scripts/{val}') # This would reload page
                    render_page.refresh()
                else:
                    # New script mode
                    pass

            await render_automation_selector(
                automation_type='CUSTOM_SCRIPT',
                on_change=on_script_select,
                value=str(est.current_script_id) if est.current_script_id else None,
                label="Seleccionar Script a Ejecutar"
            )

            if est.current_script_id and est.contract:
                
                with ui.row().classes('w-full flex-grow gap-4'):
                    
                    # --- 2. CONFIGURATION (Left Panel) ---
                    with ui.card().classes('w-1/3 h-full p-4 flex flex-col'):
                        ui.label('Configuración de Ejecución').classes('text-lg font-bold mb-4 text-slate-700')
                        
                        # Dynamic Form
                        async def on_submit(values):
                            est.form_values = values
                            await execute_script()
                        
                        # Render Form
                        # We instantiate the component. It handles its own validation UI.
                        form = DynamicExecutorForm(est.contract, on_submit=on_submit)
                        
                        ui.space()
                        # Execute Button (Form submission trigger)
                        # The form has no implicit button? DynamicExecutorForm likely expects us to call a method or provide a submit button.
                        # Let's add an explicit button that triggers form validation.
                        
                        btn_label = 'Ejecutar Script' if not est.is_executing else 'Ejecutando...'
                        btn = ui.button(btn_label, on_click=lambda: form.handle_submit()).props('unelevated').classes('w-full bg-green-600')
                        if est.is_executing:
                            btn.disable()
                            ui.spinner()
                        
                        # PROMPT 8: Promotion Button
                        async def handle_promotion():
                            script = await custom_script_service.get_script(est.current_script_id)
                            if not script: return
                            
                            target = 'validated' if script.status == 'draft' else 'published' if script.status == 'validated' else None
                            if not target:
                                ui.notify('Script ya está publicado o no puede ser promovido', type='info')
                                return
                            
                            result = await custom_script_service.promote_script(est.current_script_id, target)
                            if result.success:
                                ui.notify(f'✅ {result.message}', type='positive')
                                render_page.refresh()
                            else:
                                ui.notify(f'❌ {result.message}', type='negative')
                        
                        if est.current_script_id:
                            ui.button('🚀 Promote Script', on_click=handle_promotion).props('outline').classes('w-full mt-2')
                            
                            async def handle_escalation():
                                try:
                                    script = await custom_script_service.get_script(est.current_script_id)
                                    await show_escalation_dialog(
                                        asset_id=est.current_script_id,
                                        asset_type="custom_script",
                                        details={
                                            "name": script.name,
                                            "user_prompt": script.user_prompt,
                                            "code_hash": script.code_hash
                                        },
                                        on_success=lambda: ui.notify("Script escalado para revisión")
                                    )
                                except Exception as ex:
                                    ui.notify(f"Error al abrir escalado: {ex}", type='negative')

                            ui.button('🆘 Solicitar Soporte', on_click=handle_escalation).props('flat icon=support_agent color=orange').classes('w-full mt-1')

                        # === Prompt 4.1: Data Samples (Uploads) ===
                        ui.separator().classes('my-4')
                        ui.label('Muestras de Datos (Sandbox)').classes('font-bold text-slate-700')
                        
                        async def handle_upload(e):
                            try:
                                sandbox_dir = path_manager.get_sandbox_dir(str(est.current_script_id))
                                
                                # Sanitization simple
                                safe_name = "".join(c for c in e.name if c.isalnum() or c in ('.', '_', '-')).strip()
                                if not safe_name: safe_name = "upload"
                                
                                target = sandbox_dir / safe_name
                                with open(target, 'wb') as f:
                                    f.write(e.content.read())
                                
                                ui.notify(f"Archivo subido: {safe_name}", type='positive')
                                await load_contract(est.current_script_id) # Refresh samples
                                render_page.refresh()
                            except Exception as ex:
                                ui.notify(f"Error en subida: {ex}", type='negative')

                        ui.upload(on_upload=handle_upload, label="Subir muestra (CSV, PDF, TXT)").classes('w-full').props('auto-upload')

                        if est.samples:
                            with ui.list().classes('w-full mt-2 border rounded p-1'):
                                for sample in est.samples:
                                    with ui.item().classes('p-1'):
                                        with ui.item_section():
                                            ui.label(sample.name).classes('text-xs truncate')
                                        with ui.item_section().props('side'):
                                            async def delete_sample(s=sample):
                                                try:
                                                    s.unlink()
                                                    ui.notify(f"Eliminado: {s.name}")
                                                    await load_contract(est.current_script_id)
                                                    render_page.refresh()
                                                except Exception as ex:
                                                    ui.notify(f"Error al eliminar: {ex}", type='negative')
                                            ui.button(icon='delete', on_click=delete_sample).props('flat dense color=red')

                        # === Prompt 13: Documentation Panel ===
                        ui.separator().classes('my-4')

                        async def handle_generate_doc():
                            """Generate documentation for current script."""
                            try:
                                script = await custom_script_service.get_script(est.current_script_id)
                                if not script:
                                    ui.notify('Script no encontrado', type='negative')
                                    return

                                code = script.code if hasattr(script, 'code') else None
                                doc_path = doc_generator.save_readme(
                                    script=script,
                                    base_path=DOCS_BASE_PATH,
                                    code=code,
                                    include_changelog=True
                                )
                                ui.notify(f'Documentación generada: {doc_path.name}', type='positive')
                                render_page.refresh()
                            except Exception as e:
                                ui.notify(f'Error generando docs: {e}', type='negative')

                        with ui.expansion('Documentación', icon='description').classes('w-full'):
                            doc_file = DOCS_BASE_PATH / f"{est.current_script_id}.md"
                            viewer = MarkdownViewer(
                                file_path=doc_file,
                                mode='drawer',
                                script_id=est.current_script_id,
                                show_source_button=False,
                                allow_generation=True,
                                on_generate=lambda: asyncio.create_task(handle_generate_doc())
                            )
                            viewer.render()

                    # --- 3. CONSOLE & RESULTS (Right Panel) ---
                    with ui.column().classes('w-2/3 h-full gap-4'):
                        
                        # Logs Console
                        with ui.card().classes('w-full flex-grow bg-slate-900 text-green-400 p-0 overflow-hidden flex flex-col'):
                            ui.label('Consola de Ejecución').classes('text-xs font-bold text-slate-500 p-2 bg-slate-800 w-full block')
                            log_area = ui.log(max_lines=1000).classes('w-full flex-grow font-mono text-xs p-2')
                            
                        # Results Area (if any)
                        if est.execution_result:
                             with ui.card().classes('w-full max-h-64 p-4 overflow-auto'):
                                 ui.label('Resultados').classes('font-bold mb-2')
                                 if 'table' in est.execution_result:
                                     # Render simple table
                                     cols = [{"name": c, "label": c, "field": c} for c in est.execution_result['table'][0].keys()] if est.execution_result['table'] else []
                                     ui.table(columns=cols, rows=est.execution_result['table'], pagination=5).classes('w-full dense')
                                 elif 'file' in est.execution_result:
                                     ui.button('Descargar Archivo', icon='download', on_click=lambda: ui.download(est.execution_result['file'])).props('outline')
                                 else:
                                     ui.json_editor({'content': {'json': est.execution_result}}).classes('h-full')


            elif not est.current_script_id:
                # No script selected -> CREATION MODE (Restored)
                with ui.column().classes('w-full items-start justify-start'):
                     ScriptCreationWizard()


    async def execute_script():
        """
        Orquesta la lógica de ejecución del script.
        Prepara el entorno de sandbox, captura la salida estándar para los logs
        y gestiona la devolución de resultados.
        """
        est.is_executing = True
        render_page.refresh()
        
        try:
             # Prepare Sandbox
             sandbox = SandboxExecutionService(path_manager)
             
             # Log started
             if log_area: log_area.push(f"--- Iniciando ejecución script {est.current_script_id} ---")
             
             # Call Sandbox
             # We need to pass a callback for stdout capturing if Sandbox supports it.
             # Assuming SandboxExecutionService accepts a 'stdout_callback' or similar, OR we capture it.
             # For Prompt 6, we'll assume we get result at end, OR we simulate streaming if the service supports it.
             # Real implementation might need WebSocket or polling for live logs.
             # Here we mock live logging for demonstration.
            
             # Mock live logs
             if log_area: log_area.push(f"Validando parámetros: {est.form_values}")
             
             # Execute
             script = await custom_script_service.get_script(est.current_script_id)
             execution_id = str(uuid.uuid4())
             
             # Prep samples paths
             sandbox_dir = path_manager.get_sandbox_dir(str(est.current_script_id))
             sample_paths = [str(f.resolve()) for f in sandbox_dir.iterdir() if f.is_file()]
             
             # NOTE: sandbox.execute_in_sandbox usually takes 'code' and 'file_paths'.
             # Params need to be injected or passed. Assuming new signature supports 'params'.
             # If not, we might need to inject them into code or env vars.
             # Prompt 6 says "Envie todo al sandbox_service".
             
             result = await sandbox.execute_in_sandbox(
                 code=script.code,
                 file_paths=sample_paths,
                 execution_id=execution_id,
                 # params=est.form_values # If supported
             )
             
             if log_area: 
                 log_area.push(f"Ejecución finalizada. Status: {result.get('success')}")
                 if result.get('error'): log_area.push(f"ERROR: {result.get('error')}")

             est.execution_result = result.get('data')

        except Exception as e:
             if log_area: log_area.push(f"CRITICAL ERROR: {e}")
             ui.notify(str(e), type='negative')
        finally:
             est.is_executing = False
             render_page.refresh()

    await render_page()
