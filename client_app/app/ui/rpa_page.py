from nicegui import ui, app, events
import asyncio
import os
import shutil
import json
import re
from datetime import datetime
from uuid import uuid4
from pathlib import Path
from typing import Optional, List, Dict, Any

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.form_factory import FormFactory, FormContext, AtomColorScheme
from client_app.app.ui.components.privacy_indicator import render_privacy_indicator
from client_app.app.ui.components.privacy_report import render_privacy_report
from client_app.app.modules.privacy.anonymizer import AnonymizationContext
from client_app.app.database.models import ScriptLibrary
from client_app.app.ui.components.data_source_selector import render_data_source_selector, DataSourceSelection, DataSourceSelectorState
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.page_header import page_header
from automatia_shared.enums import StepType

# --- CONSTANTS ---
RPA_STORAGE_DIR = Path("data/storage/rpa")
RPA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# --- STATE CLASSES ---

class RPAState:
    """Estado global de la página RPA."""
    def __init__(self):
        self.current_mode = 'library'  # 'library', 'design', 'execution'
        self.selected_robot_id = None
        self.saved_robots: List[ScriptLibrary] = []
        self.search_query = ""

class RPADesignState:
    """Estado del wizard de diseño (Design Mode)."""
    def __init__(self):
        # Phase Control
        self.phase = 'SETUP' # SETUP, RECORDING, REVIEW
        self.user_instructions = ""

        # Data Inputs
        self.target_url = ""
        self.data_mode = 'MANUAL' # MANUAL, EXCEL, CATALOG
        self.manual_data = [
            {'key': 'Nombre', 'value': 'Juan'},
            {'key': 'Apellido', 'value': 'Pérez'}
        ]
        self.uploaded_excel_path = None
        self.uploaded_attachments = []
        # Fuente de datos desde catálogo/flujo
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()
        
        # Execution Context
        self.execution_id = None
        
        # Results
        self.playbook = []
        self.logs = []
        self.feedback_history = []
        
        # UI Helpers
        self.log_comp = None
        self.stepper = None
        
    def reset(self):
        self.__init__()

    def ensure_context(self):
        if not self.execution_id:
            self.execution_id = state.rpa.paths.create_execution_context(task_type='RPA_REC')
            state.rpa.set_execution_context(self.execution_id)
        return self.execution_id

class RPAExecutionState:
    """Estado del modo ejecución."""
    def __init__(self):
        self.script_entry: Optional[ScriptLibrary] = None
        self.playbook = []
        self.is_running = False
        self.current_step_index = -1
        self.execution_logs = []
        self.output_file_path = None
        self.execution_result = None
        self.execution_id = None  # ID de ejecución para acceder a carpeta de resultados

# --- PAGE CONTENT ---

async def rpa_page_content(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    """
    Controlador refactorizado de la página de RPA.
    Arquitectura de tres modos: Library, Design, Execution.
    Identidad Visual: Morado (🤖).
    """
    from client_app.app.services.naming_service import naming_service
    t = state.i18n.t
    
    # Persistent page state
    page_state = RPAState()
    design_state = RPADesignState()
    exec_state = RPAExecutionState()

    # --- LOCAL FUNCTIONS (Ordered by scope) ---

    async def load_saved_robots():
        """Carga robots RPA desde la base de datos."""
        async with state.db_session() as session:
            from sqlalchemy import select
            stmt = select(ScriptLibrary).where(ScriptLibrary.source_module == 'rpa')
            result = await session.execute(stmt)
            page_state.saved_robots = list(result.scalars().all())
            render_page.refresh()

    def get_current_context_data():
        """Obtiene el diccionario de contexto de la fila de prueba según el modo actual."""
        ctx = {}
        if design_state.data_mode == 'MANUAL':
            ctx = {i['key']: i['value'] for i in design_state.manual_data if i.get('key')}
        elif design_state.data_mode == 'EXCEL' and design_state.uploaded_excel_path:
            try:
                import pandas as pd
                df = pd.read_excel(design_state.uploaded_excel_path)
                if not df.empty: ctx = json.loads(df.iloc[0].to_json())
            except: pass
        elif design_state.data_mode == 'CATALOG' and getattr(design_state.data_source_selector_state, 'preview_data', None):
            try:
                df = design_state.data_source_selector_state.preview_data.to_dataframe()
                if not df.empty: ctx = json.loads(df.iloc[0].to_json())
            except: pass
        return ctx

    def go_to_library():
        from client_app.app.core.state import app_state
        # Si viene desde un flujo, volver al flujo
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

        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()

    def start_new_design():
        page_state.current_mode = 'design'
        design_state.reset()
        layout_manager.enter_design_mode(StepType.RPA_EXECUTE)
        render_page.refresh()

    async def edit_robot(script: ScriptLibrary):
        if getattr(script, 'status', 'published') == 'draft':
            page_state.current_mode = 'design'
            design_state.reset()
            if script.source_metadata:
                design_state.target_url = script.source_metadata.get('base_url', '')
            else:
                design_state.target_url = ""
            if script.script_path and os.path.exists(script.script_path):
                 try:
                     with open(script.script_path, 'r') as f:
                         design_state.playbook = json.load(f)
                 except: pass
            design_state.phase = 'REVIEW'
            layout_manager.enter_design_mode(StepType.RPA_EXECUTE, atom_id=str(script.id))
            render_page.refresh()
        else:
            # Abrir panel de metadatos en el lateral
            layout_manager.enter_documentation_mode(
                atom_name=script.name,
                doc_path=script.doc_path,
                status=script.status,
                description=script.description,
                resource_id=script.id,
                record_type='library'
            )
            ui.notify("Abriendo edición de metadatos", type='info')

    async def run_robot(script: ScriptLibrary):
        page_state.current_mode = 'execution'
        exec_state.script_entry = script
        if script.script_path and os.path.exists(script.script_path):
            try:
                with open(script.script_path, 'r') as f:
                    exec_state.playbook = json.load(f)
            except: pass
        layout_manager.enter_execution_mode(str(script.id))
        render_page.refresh()

    async def delete_robot(script_id: int):
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, script_id)
            if script:
                await session.delete(script)
                await session.commit()
                ui.notify("Robot eliminado", type='positive')
                await load_saved_robots()

    def render_playbook_flow(playbook: list, current_step_index: int = -1, error_index: int = -1) -> str:
        mm = ["graph TD"]
        mm.append("classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px;")
        mm.append("classDef active fill:#d1fae5,stroke:#059669,stroke-width:3px;")
        mm.append("classDef error fill:#fee2e2,stroke:#dc2626,stroke-width:3px;")
        
        for i, step in enumerate(playbook):
            action = step.get('action', 'unknown')
            selectors = step.get('selector', '')
            label = f"{action.upper()}: {selectors[:20]}..." if len(selectors) > 20 else f"{action.upper()}: {selectors}"
            if action == 'ai_agent': label = f"🤖 AGENT: {step.get('value', '')[:15]}..."
            
            if action == 'navigate': sh_l, sh_r = '[', ']'
            elif action == 'click': sh_l, sh_r = '(', ')'
            elif action == 'fill': sh_l, sh_r = '[/', '/]'
            elif action == 'ai_agent': sh_l, sh_r = '{{', '}}'
            else: sh_l, sh_r = '[', ']'
            
            label = label.replace('"', "'")
            node_id = f"step{i}"
            mm.append(f"{node_id}{sh_l}\"{label}\"{sh_r}")
            if i > 0: mm.append(f"step{i-1} --> {node_id}")
            if i == error_index: mm.append(f"class {node_id} error")
            elif i == current_step_index: mm.append(f"class {node_id} active")
        return "\n".join(mm)

    def resolve_intervention(action, pb_update):
        if repair_future and not repair_future.done(): repair_future.set_result((action, pb_update))
        repair_dialog.close()

    async def trigger_ai_repair():
        if not d_feedback.value: return ui.notify("Escribe ayuda para la IA", type='warning')
        ui.notify("🤖 IA analizando y reparando...", type='info')
        try:
            ctx = get_current_context_data()
            new_pb = await state.rpa.refine_playbook(
                current_playbook=design_state.playbook if page_state.current_mode == 'design' else exec_state.playbook,
                recording_logs=[], error_logs=d_error_msg.text, user_feedback_history=[d_feedback.value], context_data=ctx
            )
            if repair_future and not repair_future.done():
                repair_future.set_result(("RETRY", new_pb)); repair_dialog.close()
        except Exception as e: ui.notify(f"Fallo IA: {e}", type='negative')

    async def handle_intervention(error_msg: str, screenshot_path: str, step_index: int = -1):
        d_error_msg.text = error_msg; d_feedback.value = ""
        pb = design_state.playbook if page_state.current_mode == 'design' else exec_state.playbook
        if pb:
            d_mermaid_container.clear()
            with d_mermaid_container: ui.mermaid(render_playbook_flow(pb, current_step_index=step_index, error_index=step_index)).classes('w-full h-48 bg-gray-50 rounded border p-2')
        if screenshot_path and os.path.exists(screenshot_path):
            import base64
            with open(screenshot_path, "rb") as f: d_screenshot.set_source(f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}")
        else: d_screenshot.set_source('https://placehold.co/600x400?text=No+Image')
        repair_dialog.open()
        nonlocal repair_future
        repair_future = asyncio.Future()
        try:
            action, new_pb = await repair_future
            return action, (new_pb if new_pb else pb)
        except: return "STOP", pb

    async def confirm_agent():
        if not d_agent_instr.value: return
        if agent_future and not agent_future.done(): agent_future.set_result(d_agent_instr.value)
        agent_dialog.close()

    async def update_manual_data(grid): design_state.manual_data = await grid.get_rows()

    async def handle_start_recording():
        eid = design_state.ensure_context()
        design_state.phase = 'RECORDING'; render_page.refresh()
        try:
            design_state.log_comp.push(f"🚀 Iniciando en {design_state.target_url}...")
            await state.rpa.start_recording_session(
                url=design_state.target_url, _excel_file=design_state.uploaded_excel_path,
                _attachments_path=str(state.rpa.paths.get_input_dir(eid)),
                log_callback=lambda m: design_state.log_comp.push(f"{datetime.now().strftime('%H:%M:%S')} - {m}")
            )
        except Exception as e: ui.notify(f"Error: {e}", type='negative'); design_state.stepper.previous()

    async def handle_stop_recording():
        design_state.log_comp.push("🛑 Analizando trazas con IA...")
        try:
            logs = await state.rpa.stop_recording_and_get_logs()
            if not logs: return ui.notify("No se grabaron eventos", type='warning')
            
            # Privacy Anonymization
            anonymizer = AnonymizationContext(locale="es_ES")
            anon_logs = []
            for l in logs:
                al = l.copy()
                for f in ['value', 'text', 'input_value', 'semantic_info']:
                    if f in al and al[f]: al[f] = anonymizer.anonymize(str(al[f])) if not isinstance(al[f], dict) else {k: anonymizer.anonymize(str(v)) for k, v in al[f].items()}
                anon_logs.append(al)
            
            # Context Extraction (Manual, Excel or Catalog)
            ctx = get_current_context_data()
            
            playbook = await state.rpa.analyze_recording(anon_logs, context_dict=ctx)
            
            # Rehydrate (Restore original values)
            for s in playbook:
                if 'value' in s and isinstance(s['value'], str): s['value'] = anonymizer.deanonymize(s['value'])
                if 'selector' in s and isinstance(s['selector'], str): s['selector'] = anonymizer.deanonymize(s['selector'])
            
            design_state.playbook = playbook; design_state.phase = 'REVIEW'; render_page.refresh()
        except Exception as e: ui.notify(f"Fallo IA: {e}", type='negative')

    async def handle_agent_delegation():
        d_agent_instr.value = ""; agent_dialog.open()
        nonlocal agent_future; agent_future = asyncio.Future()
        try:
            instr = await agent_future
            agent_spin_dialog.open()
            res = await state.rpa.run_agent_interactive(instr)
            agent_spin_dialog.close()
            if res.get('success'):
                ui.notify("Agente completó tarea", type='positive')
                if state.rpa.page:
                    await state.rpa.page.evaluate(f"window.recorded_actions.push({{type:'ai_agent', value:'{instr}', semantic:{{instruction:'{instr}', output:'{res.get('output','')}'}}, timestamp:Date.now()}})")
                    design_state.log_comp.push(f"🤖 AGENT: {instr}")
            else: ui.notify(f"Error Agente: {res.get('error')}", type='negative')
        except: pass

    async def handle_refine(fb: str):
        MAX_RPA_ITERATIONS = 5
        if not fb: return

        # Check iteration limit for auto-escalation
        if len(design_state.feedback_history) >= MAX_RPA_ITERATIONS:
            ui.notify("Límite de iteraciones alcanzado. Escalando al soporte...", type='warning')
            from client_app.app.ui.components.escalation_dialog import show_escalation_dialog
            await show_escalation_dialog(
                asset_id=None,
                asset_type="rpa_wizard",
                details={"target_url": design_state.target_url, "playbook": design_state.playbook}
            )
            return

        ui.notify("Refinando lógica...", type='info')

        # Anonymize feedback before sending to LLM
        anonymizer = AnonymizationContext(locale="es_ES")
        fb_anon = anonymizer.anonymize(fb)
        design_state.feedback_history.append(fb)

        try:
            ctx = get_current_context_data()
            # Anonymize context data for privacy
            ctx_anon = anonymizer.anonymize(ctx) if ctx else {}

            new_pb = await state.rpa.refine_playbook(
                current_playbook=design_state.playbook,
                recording_logs=[],
                error_logs="User Correction",
                user_feedback_history=[anonymizer.anonymize(h) for h in design_state.feedback_history],
                context_data=ctx_anon
            )

            # Rehydrate playbook values
            for s in new_pb:
                if 'value' in s and isinstance(s['value'], str):
                    s['value'] = anonymizer.deanonymize(s['value'])
                if 'selector' in s and isinstance(s['selector'], str):
                    s['selector'] = anonymizer.deanonymize(s['selector'])

            design_state.playbook = new_pb
            ui.notify("Playbook actualizado", type='positive')
            render_page.refresh()
        except Exception as e:
            ui.notify(f"Error: {e}")

    async def handle_quick_test():
        ui.notify("Lanzando test rápido...", type='warning')
        ctx = get_current_context_data()
        try:
            await state.rpa.run_playbook_batch(design_state.playbook, explicit_rows=[ctx], on_ask_user=handle_intervention)
            ui.notify("Test finalizado", type='positive')
        except Exception as e: ui.notify(f"Fallo test: {e}")

    async def handle_seal_robot():
        if not design_state.playbook: return
        try:
            # Sync with ScriptLibrary AND RPAService specific Table
            state.rpa._current_playbook = design_state.playbook # Required by save_master_playbook
            playbook = await state.rpa.save_master_playbook(design_state.user_instructions or "Nuevo Robot", design_state.target_url)

            # Actualizar step.config si estamos en modo contextual de flujo
            from client_app.app.core.state import app_state
            if app_state.flow_context and app_state.flow_context.get('mode') == 'contextual':
                step = app_state.flow_context.get('step')
                if step and playbook:
                    # Buscar el ScriptLibrary correspondiente
                    from client_app.app.database.models import ScriptLibrary
                    from sqlmodel import select
                    async with state.db_session() as session:
                        stmt = select(ScriptLibrary).where(
                            ScriptLibrary.source_module == 'rpa',
                            ScriptLibrary.source_automation_id == playbook.id
                        )
                        result = await session.execute(stmt)
                        script_entry = result.scalars().first()
                        if script_entry:
                            step.config['config_id'] = script_entry.id
                            step.config['script_id'] = script_entry.id
                            if app_state.editing_flow and hasattr(app_state.editing_flow, 'steps'):
                                app_state.refresh_flow_context_steps(app_state.editing_flow.steps)
                            if hasattr(app_state, 'on_step_change') and callable(app_state.on_step_change):
                                app_state.on_step_change()

            ui.notify("Robot sellado y guardado en biblioteca", type='positive')
            go_to_library(); await load_saved_robots()
        except Exception as e: ui.notify(f"Error al sellar: {e}")

    async def handle_excel_upload(e: events.UploadEventArguments):
        try:
            # Normalization to avoid issues
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            
            eid = design_state.ensure_context()
            p = state.rpa.paths.get_input_dir(eid) / safe_name
            
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                 return
                 
            with open(p, 'wb') as f: f.write(content)
            design_state.uploaded_excel_path = str(p); ui.notify(f"Excel listo", type='positive')
        except Exception as ex:
            ui.notify(f"Error en carga: {ex}", type='negative')

    async def handle_attachment_upload(e: events.UploadEventArguments):
        try:
            # Normalization to avoid issues
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            
            eid = design_state.ensure_context()
            input_dir = state.rpa.paths.get_input_dir(eid)
            p = input_dir / safe_name
            
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                 return
                 
            with open(p, 'wb') as f: f.write(content)
            design_state.uploaded_attachments.append(str(p))
            ui.notify(f"Adjunto listo: {safe_name}", type='positive')
        except Exception as ex: ui.notify(f"Error adjunto: {ex}", type='negative')

    async def handle_exec_upload(e: events.UploadEventArguments):
        try:
            # Normalization to avoid issues
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            
            eid = str(uuid4())
            p = RPA_STORAGE_DIR / f"in_exec_{eid}_{safe_name}"
            
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                 return
                 
            with open(p, 'wb') as f: f.write(content)
            exec_state.output_file_path = str(p); ui.notify("Archivo para ejecución cargado", type='positive')
        except Exception as ex:
            ui.notify(f"Error de ejecución: {ex}", type='negative')

    async def handle_execution_start():
        if not exec_state.playbook: return
        exec_state.is_running = True; exec_state.current_step_index = 0
        exec_state.execution_logs = []
        try:
            exec_state.log_comp.push("🚀 Iniciando ejecución de Playbook...")
            await state.rpa.run_playbook_batch(
                exec_state.playbook,
                excel_file=exec_state.output_file_path,
                on_ask_user=handle_intervention,
                log_callback=lambda m: exec_state.log_comp.push(f"{datetime.now().strftime('%H:%M:%S')} - {m}")
            )
            # Capturar execution_id para acceder a carpeta de resultados/descargas
            exec_state.execution_id = state.rpa.current_execution_id
            exec_state.execution_result = "Success"
            ui.notify("Ejecución finalizada con éxito", type='positive')
        except Exception as e:
            ui.notify(f"Error ejecución: {e}", type='negative')
            print(f"DEBUG RPA EXEC FAIL: {e}")
            # Capturar execution_id incluso en caso de error
            exec_state.execution_id = state.rpa.current_execution_id
        finally: exec_state.is_running = False; render_page.refresh()

    @ui.refreshable
    async def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library': await render_library()
            elif page_state.current_mode == 'design': await render_design()
            elif page_state.current_mode == 'execution': await render_execution()

    async def toggle_favorite(resource):
        """Toggle favorito para un robot RPA."""
        robot_id = resource.get('id')
        if robot_id:
            from client_app.app.services.script_library_service import script_library_service
            await script_library_service.toggle_favorite(robot_id)
            await load_saved_robots()
            render_page.refresh()

    async def render_library():
        # Map ScriptLibrary objects to dicts for StandardPageLayout
        resources = []
        for robot in page_state.saved_robots:
            resources.append({
                'id': robot.id,
                'name': robot.name,
                'description': robot.description or 'Sin descripción',
                'status': robot.status or 'draft',
                'source_module': 'rpa',
                'doc_path': robot.doc_path,
                'is_favorite': robot.is_favorite,
                'created_at': robot.created_at,
                '_original': robot
            })

        layout = StandardPageLayout(
            title='Automatización de procesos web (RPA)',
            source_module='rpa',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_robot(r['_original']),
            on_delete=lambda r: delete_robot(r['id']),
            on_execute=lambda r: run_robot(r['_original']),
            on_favorite_toggle=toggle_favorite,
            help_description='Graba, refina y ejecuta robots que interactúan con aplicaciones web de forma autónoma.',
            input_contract=['target_url', 'manual_data', 'excel_file'],
            output_contract=['execution_logs', 'output_file', 'success']
        )
        layout.render()

    async def render_design_setup():
        with ui.column().classes('w-full gap-4 p-0'):
            with ui.card().classes('w-full p-4 border border-gray-100 bg-slate-50 shadow-sm'):
                ui.input(placeholder="URL de Inicio").classes('w-full text-lg').props('outlined autofocus label="URL de Inicio"')\
                    .bind_value(design_state, 'target_url')
            
            with ui.card().classes('w-full p-4 border border-gray-100 shadow-sm'):
                with ui.tabs().classes('w-full') as tabs:
                    t1 = ui.tab('Variables Manuales'); t2 = ui.tab('Excel de Ejemplo'); t3 = ui.tab('Desde Catálogo')
                with ui.tab_panels(tabs, value=t1).classes('w-full'):
                    with ui.tab_panel(t1):
                        grid = ui.aggrid({
                            'columnDefs': [{'headerName': 'Variable', 'field': 'key', 'editable': True}, {'headerName': 'Valor', 'field': 'value', 'editable': True}],
                            'rowData': design_state.manual_data, 'singleClickEdit': True, 'stopEditingWhenCellsLoseFocus': True
                        }).classes('h-32 w-full')
                        ui.button('Añadir Fila', on_click=lambda: grid.run_row_method(None, 'add', [{'key': '', 'value': ''}])).props('flat dense icon=add')
                        grid.on('cellValueChanged', lambda: (asyncio.create_task(update_manual_data(grid))))
                        def set_manual_mode(): design_state.data_mode = 'MANUAL'
                        tabs.on('update:model-value', lambda e: set_manual_mode() if e.args == 'Variables Manuales' else None)
                    with ui.tab_panel(t2):
                        ui.label("Sube Excel con filas reales para que la IA entienda el contexto").classes('text-xs text-slate-500 mb-2')
                        ui.upload(label="Sube Excel (.xlsx)", auto_upload=True, on_upload=handle_excel_upload).classes('w-full')
                        if design_state.uploaded_excel_path: ui.label(f"✓ {os.path.basename(design_state.uploaded_excel_path)}").classes('text-green-600 font-bold mt-2')
                        def set_excel_mode(): design_state.data_mode = 'EXCEL'
                        tabs.on('update:model-value', lambda e: set_excel_mode() if e.args == 'Excel de Ejemplo' else None)
                    with ui.tab_panel(t3):
                        ui.label("Selecciona datos de una acción del catálogo o paso del flujo").classes('text-xs text-slate-500 mb-2')
                        def handle_rpa_source_selection(selection: DataSourceSelection):
                            design_state.data_source = selection
                            design_state.data_mode = 'CATALOG'
                            if selection.source_type == 'catalog':
                                ui.notify(f'Acción seleccionada: {selection.atom_name}', type='info')
                            elif selection.source_type == 'flow_step':
                                ui.notify(f'Datos del paso: {selection.step_name}', type='info')
                        render_data_source_selector(
                            consumer_type=StepType.RPA_EXECUTE,
                            on_source_selected=handle_rpa_source_selection,
                            flow_context=state.flow_context,
                            initial_selection=design_state.data_source,
                            selector_state_override=design_state.data_source_selector_state,
                            upload_formats_override=['xlsx', 'csv']
                        )

            with ui.card().classes('w-full p-4 border border-gray-100 shadow-sm'):
                with ui.expansion("Adjuntos (Opcional)", icon="attach_file").classes('w-full font-bold text-slate-700'):
                    ui.upload(label="Sube archivos necesarios", multiple=True, auto_upload=True, on_upload=handle_attachment_upload)\
                        .props('flat bordered color=indigo-500 dense').classes('w-full bg-indigo-50')
                    if design_state.uploaded_attachments:
                        with ui.column().classes('mt-2'):
                            for att in design_state.uploaded_attachments: ui.label(f"📎 {os.path.basename(att)}").classes('text-xs text-slate-600')

    async def render_design_recording():
        with ui.column().classes('w-full items-center py-8'):
            with ui.row().classes('items-center mb-6 gap-4 animate-pulse'):
                ui.icon('radio_button_checked', size='3em', color='red')
                ui.label("GRABANDO NAVEGADOR").classes('text-3xl font-bold text-red-600')
            ui.label("Interactúa con el navegador. La IA aprenderá tus pasos.").classes('text-slate-500 mb-8')
            with ui.card().classes('w-full bg-slate-900 p-0 shadow-xl max-w-3xl'):
                ui.label("EVENT STREAM").classes('text-xs font-bold text-slate-500 p-3 bg-slate-800 w-full border-b border-slate-700')
                design_state.log_comp = ui.log().classes('w-full h-48 font-mono text-green-400 text-xs p-4 bg-slate-900').style('overflow-y: auto')
            with ui.row().classes('mt-8 gap-4'):
                ui.button("🤖 Delegar al Agente", icon='travel_explore', on_click=handle_agent_delegation).props('unelevated color=purple-700').classes('h-14 px-8 rounded-full shadow-lg')

    async def render_design_review():
        with ui.row().classes('w-full gap-6 items-start p-4'):
            with ui.card().classes('w-2/3 p-0 h-[650px] flex flex-col'):
                ui.label("Secuencia de Acciones (Diagrama)").classes('p-4 font-bold bg-slate-50 border-b')
                with ui.scroll_area().classes('w-full h-2/5 p-4 bg-white border-b'):
                    if design_state.playbook: ui.mermaid(render_playbook_flow(design_state.playbook)).classes('w-full')
                ui.label("Editor de Playbook (JSON)").classes('p-2 text-[10px] font-bold text-slate-400 bg-slate-50')
                ui.json_editor({'content': {'json': design_state.playbook}}).classes('w-full flex-grow')
            with ui.column().classes('w-1/3 gap-4'):
                with ui.card().classes('w-full p-6 border-l-4 border-l-indigo-500'):
                    ui.label("Datos del Robot").classes('text-lg font-bold mb-4')
                    ui.input("Nombre del Proceso", placeholder="Ej: Solicitar Beca").classes('w-full')\
                        .bind_value(design_state, 'user_instructions')
                with ui.card().classes('w-full p-6 border-l-4 border-l-blue-500'):
                    ui.label("Refinar con IA").classes('text-lg font-bold mb-2')
                    fb = ui.textarea(placeholder="Ej: El paso 2 es opcional...").classes('w-full bg-slate-50 mb-2').props('outlined')
                    ui.button("Regenerar", icon='auto_fix_high', on_click=lambda: handle_refine(fb.value)).props('flat color=indigo').classes('w-full')
                ui.button("Lanzar Prueba Rápida", icon='play_circle', on_click=handle_quick_test).props('outline color=orange').classes('w-full h-12 shadow-sm')

    async def render_design():
        with ui.row().classes('w-full max-w-5xl mx-auto items-start gap-4 mb-2'):
            ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
            page_header(
                t('rpa.design_title', 'Diseñador de automatización web'),
                t('rpa.design_subtitle', 'Configura la grabación, entrena la IA y crea un robot reutilizable'),
                classes='gap-0 mb-2'
            )
        
        with ui.column().classes('w-full max-w-5xl mx-auto bg-white rounded-xl shadow-sm p-4'):
            if design_state.phase == 'SETUP':
                await render_design_setup()
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Iniciar Grabación', on_click=handle_start_recording).props('unelevated color=indigo-700')\
                        .bind_enabled_from(design_state, 'target_url', backward=lambda x: len(x) > 5)
            elif design_state.phase == 'RECORDING':
                await render_design_recording()
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Finalizar y Analizar', on_click=handle_stop_recording).props('unelevated color=indigo-700')
            elif design_state.phase == 'REVIEW':
                await render_design_review()
                with ui.row().classes('w-full justify-end mt-4 gap-2'):
                    ui.button('ATRÁS', on_click=lambda: (setattr(design_state, 'phase', 'SETUP'), render_page.refresh())).props('flat color=slate')
                    ui.button('GUARDAR', icon='save', on_click=handle_seal_robot).props('unelevated color=primary shadow')\
                        .bind_enabled_from(design_state, 'playbook', backward=lambda p: len(p) > 0)

    async def render_execution():
        robot = exec_state.script_entry
        if not robot: return
        with ui.row().classes('w-full items-start gap-4 mb-4'):
            ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
            page_header(
                robot.name,
                t('rpa.execution_subtitle', 'Ejecuta el robot con los datos de entrada y monitoriza el proceso'),
                classes='gap-0 mb-6'
            )
        with ui.row().classes('w-full gap-6'):
            with ui.column().classes('w-2/3 gap-4'):
                with ui.card().classes('w-full p-6 border-t-8 border-indigo-600 shadow-md'):
                    ui.label("1. Entrada de Datos para Ejecución").classes('text-lg font-bold mb-4')
                    ui.upload(label="Selecciona archivo Excel (.xlsx)", auto_upload=True, on_upload=handle_exec_upload).classes('w-full')
                if exec_state.playbook:
                    with ui.card().classes('w-full p-0 overflow-hidden shadow-md'):
                         ui.label("Estado de ejecución en Playbook").classes('p-4 font-bold bg-slate-50 border-b')
                         with ui.column().classes('p-4 w-full h-[400px] overflow-auto'):
                             ui.mermaid(render_playbook_flow(exec_state.playbook, current_step_index=exec_state.current_step_index)).classes('w-full')
                with ui.card().classes('w-full bg-slate-900 p-0 text-white overflow-hidden'):
                    ui.label("SISTEMA DE LOGS").classes('text-[10px] p-3 bg-slate-800 text-slate-500 border-b border-slate-700')
                    exec_state.log_comp = ui.log().classes('w-full h-40 font-mono text-xs text-indigo-300 p-4 bg-slate-900')
            with ui.column().classes('w-1/3 gap-4'):
                ui.button('EJECUTAR AHORA', icon='bolt', on_click=handle_execution_start).props('unelevated color=indigo-700 size=lg')\
                    .classes('w-full h-24 text-xl font-bold shadow-xl border-2 border-indigo-400')\
                    .bind_enabled_from(exec_state, 'is_running', backward=lambda r: not r)
                if exec_state.execution_result:
                    with ui.card().classes('w-full p-6 bg-green-50 border border-green-200'):
                        ui.label("✓ Éxito").classes('font-bold text-green-800')
                        ui.label("Transformación web finalizada").classes('text-sm text-green-700')
                        with ui.row().classes('gap-2 mt-2'):
                            ui.button('Descargar Resultados', icon='download', on_click=lambda: ui.download(exec_state.output_file_path)).props('outline color=green')
                            if exec_state.execution_id:
                                ui.button(
                                    'Abrir Carpeta',
                                    icon='folder_open',
                                    on_click=lambda: state.rpa.paths.open_output_folder(exec_state.execution_id)
                                ).props('outline color=blue')

    # --- HELPERS ---


    # --- MERMAID HELPER ---

    # --- HITL SYSTEM ---
    repair_future = None
    with ui.dialog() as repair_dialog, ui.card().classes('w-[800px] h-auto p-0'):
        with ui.row().classes('w-full bg-red-600 text-white p-4 items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('emergency_share', size='2em')
                ui.label('Sala de Emergencias RPA').classes('text-xl font-bold')
            ui.label('Intervención Humana Requerida').classes('text-xs opacity-80')
            
        with ui.row().classes('w-full p-6 gap-6'):
            with ui.column().classes('w-1/2'):
                ui.label("Captura del Fallo").classes('font-bold text-slate-500 mb-2')
                d_screenshot = ui.image('').classes('w-full rounded border border-gray-300 shadow-sm').props('no-spinner')
                ui.separator().classes('my-2')
                ui.label("Flujo de Ejecución").classes('font-bold text-slate-500 text-xs')
                d_mermaid_container = ui.column().classes('w-full')
                
            with ui.column().classes('w-1/2 gap-4'):
                with ui.card().classes('w-full bg-red-50 border border-red-200 p-3'):
                    ui.label("Error Detectado:").classes('text-xs text-red-800 font-bold')
                    d_error_msg = ui.label("").classes('text-sm text-red-600 font-mono break-all')

                ui.label("¿Qué ha pasado? (Feedback)").classes('font-bold text-slate-700')
                d_feedback = ui.textarea(placeholder="Ej: El botón ha cambiado de ID...").classes('w-full bg-slate-50').props('outlined')
                
                ui.button("✨ Reparar con IA y Reintentar", on_click=trigger_ai_repair).classes('w-full bg-blue-600 text-white font-bold h-12')
                with ui.row().classes('w-full gap-2 mt-2'):
                     ui.button("Reintentar", on_click=lambda: resolve_intervention("RETRY", None)).props('flat')
                     ui.button("Saltar", on_click=lambda: resolve_intervention("SKIP", None)).props('flat color=orange')
                     ui.button("Detener", on_click=lambda: resolve_intervention("STOP", None)).props('flat color=red')



    # --- AGENT DELEGATION ---
    agent_future = None
    with ui.dialog() as agent_dialog, ui.card().classes('w-[600px] p-6'):
        ui.label('Delegar al Agente Autónomo').classes('text-xl font-bold text-purple-700 mb-4')
        d_agent_instr = ui.textarea(placeholder="¿Qué debe hacer el agente?").classes('w-full mb-6 bg-purple-50').props('outlined autofocus')
        ui.button('🚀 Ejecutar Agente', on_click=confirm_agent).classes('w-full bg-purple-600 text-white font-bold h-12')

    with ui.dialog() as agent_spin_dialog, ui.card().classes('items-center justify-center p-8'):
        ui.spinner(size='3em', color='purple')
        ui.label("Agente Trabajando...").classes('text-purple-600 font-bold mt-4 animate-pulse')



    # --- INITIALIZATION ---

    # 1. IMMEDIATE LAYOUT SETUP (sync) to avoid flicker/leakage
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.RPA_EXECUTE, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif initial_mode == 'design':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.RPA_EXECUTE, from_flow=False)
        design_state.user_instructions = naming_service.generate_provisional_name(StepType.RPA_EXECUTE)
    elif initial_mode == 'execution' and (page_state.selected_robot_id or atom_id):
        page_state.current_mode = 'execution'
        if atom_id:
            page_state.selected_robot_id = atom_id
        # No drawer in execution
    else:
        # Default to library: EXPLICITLY exit focus mode to clear leakage from other pages
        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()

    # Singleton-like guard for the content within the same client call
    if hasattr(ui.context.client, '_rpa_rendered'):
        return
    ui.context.client._rpa_rendered = True

    # Use a persistent main container for this instance
    main_container = ui.column().classes('w-full p-6')

    @ui.refreshable
    async def render_page():
        main_container.clear()
        with main_container:
            if page_state.current_mode == 'library': await render_library()
            elif page_state.current_mode == 'design': await render_design()
            elif page_state.current_mode == 'execution': await render_execution()

    # 2. ASYNC INITIALIZATION (data loading)
    await load_saved_robots()

    # Si hay config_id del flujo, cargar el robot
    if flow_config_id:
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, int(flow_config_id))
            if script:
                await edit_robot(script)

    # Mode refinement (if ID was provided for execution)
    if page_state.current_mode == 'execution' and page_state.selected_robot_id:
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, int(page_state.selected_robot_id))
            if script:
                exec_state.script_entry = script
                layout_manager.enter_execution_mode(str(script.id))

    await render_page()

@ui.page('/rpa')
async def rpa_page(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    await rpa_page_content(initial_mode=initial_mode, atom_id=atom_id)


