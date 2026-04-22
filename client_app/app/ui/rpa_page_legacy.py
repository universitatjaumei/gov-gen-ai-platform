from nicegui import ui, app, events
import asyncio
import os
import shutil
import json
from datetime import datetime
from client_app.app.core.state import state
from client_app.app.ui.components.privacy_indicator import render_privacy_indicator
from client_app.app.modules.privacy.anonymizer import AnonymizationContext

async def rpa_page_content():
    """
    Controlador principal de la página de automatización de procesos web (RPA).
    Gestiona un asistente para la grabación de acciones en el navegador, 
    análisis inteligente mediante IA para generar Playbooks, y gestión de 
    intervenciones humanas durante la ejecución (HITL).
    """
    t = state.i18n.t
    
    # --- WIZARD STATE ---
    class RPAWizardState:
        """
        Mantiene el estado reactivo del asistente de RPA.
        Controla la fase actual (SETUP, RECORDING, REVIEW), los datos de entrada, 
        el contexto de ejecución y el Playbook resultante del análisis.
        """
        def __init__(self):
            # Phase Control
            self.phase = 'SETUP' # SETUP, RECORDING, REVIEW
            
            # Data Inputs
            self.target_url = ""
            self.data_mode = 'MANUAL' # MANUAL, EXCEL
            self.manual_data = [
                {'key': 'Nombre', 'value': 'Juan'},
                {'key': 'Apellido', 'value': 'Pérez'}
            ]
            self.uploaded_excel_path = None
            self.uploaded_attachments = []
            
            # Execution Context
            # Lazy Init: Created only on action
            self.execution_id = None
            
            # Results
            self.playbook = []
            self.logs = []
            self.feedback_history = []
            
        def ensure_context(self):
            """
            Asegura que exista un contexto de ejecución activo para la sesión de RPA.
            Inicializa las rutas necesarias para almacenar grabaciones y logs.
            """
            if not self.execution_id:
                self.execution_id = state.rpa.paths.create_execution_context(task_type='RPA_REC')
                state.rpa.set_execution_context(self.execution_id)
                print(f"[RPAWizard] Initialized Context (Lazy): {self.execution_id}")
            return self.execution_id
            
    # Initialize State
    wizard = RPAWizardState()
    
    # --- HITL DIALOG ---
    repair_future = None # To store asyncio future for user interaction
    
    with ui.dialog() as repair_dialog, ui.card().classes('w-[800px] h-auto p-0'):
        # Header
        with ui.row().classes('w-full bg-red-600 text-white p-4 items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('emergency_share', size='2em')
                ui.label('Sala de Emergencias RPA').classes('text-xl font-bold')
            ui.label('Intervención Humana Requerida').classes('text-xs opacity-80')
            
        # Content
        with ui.row().classes('w-full p-6 gap-6'):
            # Left: Screenshot
            with ui.column().classes('w-1/2'):
                ui.label("Captura del Fallo").classes('font-bold text-slate-500 mb-2')
                d_screenshot = ui.image('https://placehold.co/600x400?text=No+Screenshot').classes('w-full rounded border border-gray-300 shadow-sm').props('no-spinner')
                
                ui.separator().classes('my-2')
                ui.label("Flujo de Ejecución").classes('font-bold text-slate-500 text-xs')
                d_mermaid_container = ui.column().classes('w-full') # Placeholder
                
            # Right: Controls
            with ui.column().classes('w-1/2 gap-4'):
                # Error Msg
                with ui.card().classes('w-full bg-red-50 border border-red-200 p-3'):
                    ui.label("Error Detectado:").classes('text-xs text-red-800 font-bold')
                    d_error_msg = ui.label("Element not found: #submit-btn").classes('text-sm text-red-600 font-mono break-all')

                # Feedback Input
                ui.label("¿Qué ha pasado? (Feedback)").classes('font-bold text-slate-700')
                d_feedback = ui.textarea(placeholder="Ej: El botón ha cambiado de color o ID...").classes('w-full bg-slate-50').props('outlined')
                
                # AI Repair Button
                async def trigger_ai_repair():
                    if not d_feedback.value:
                        ui.notify("Escribe ayuda para la IA", type='warning')
                        return
                    
                    ui.notify("🤖 IA analizando y reparando...", type='info')
                    # Call Brain Logic
                    try:
                        # Context fallback
                        ctx = {}
                        if wizard.data_mode == 'MANUAL':
                             ctx = {item['key']: item['value'] for item in wizard.manual_data}
                        
                        new_pb = await state.rpa.refine_playbook(
                            current_playbook=wizard.playbook, # Need active playbook from Executor?
                            # NOTE: Wizard.playbook might be stale if we are in batch run modifiying it? 
                            # Ideally handle_user_intervention provides access or we trust state.
                            recording_logs=[], # No rec logs available in execution usually
                            error_logs=d_error_msg.text,
                            user_feedback_history=[d_feedback.value],
                            context_data=ctx
                        )
                        # Return this new playbook via Future
                        if repair_future and not repair_future.done():
                            repair_future.set_result(("RETRY", new_pb))
                            repair_dialog.close()
                            
                    except Exception as e:
                        ui.notify(f"Fallo IA: {e}", type='negative')

                ui.button("✨ Reparar con IA y Reintentar", on_click=trigger_ai_repair) \
                    .classes('w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold shadow-lg')

                # Manual Actions
                with ui.row().classes('w-full gap-2 mt-4'):
                     # We can also just RETRY without AI (if transient)
                     ui.button("Reintentar", on_click=lambda: resolve_intervention("RETRY", None)).props('flat')
                     ui.button("Saltar Paso", on_click=lambda: resolve_intervention("SKIP", None)).props('flat color=orange')
                     ui.button("Detener Robot", on_click=lambda: resolve_intervention("STOP", None)).props('flat color=red')

    # --- MERMAID HELPER ---
    def render_playbook_flow(playbook: list, current_step_index: int = -1, error_index: int = -1) -> str:
        """
        Genera el código Mermaid para visualizar el flujo del Playbook.

        Args:
            playbook: Lista de pasos del proceso.
            current_step_index: Índice del paso actual en ejecución.
            error_index: Índice del paso donde se detectó un fallo.

        Returns:
            Cadena con el gráfico Mermaid.
        """
        mm = ["graph TD"]
        
        # Definir estilos
        mm.append("classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px;")
        mm.append("classDef active fill:#d1fae5,stroke:#059669,stroke-width:3px;") # Verde
        mm.append("classDef error fill:#fee2e2,stroke:#dc2626,stroke-width:3px;") # Rojo
        
        for i, step in enumerate(playbook):
            action = step.get('action', 'unknown')
            selectors = step.get('selector', '')
            # Cortar selector largo
            label = f"{action.upper()}: {selectors[:20]}..." if len(selectors) > 20 else f"{action.upper()}: {selectors}"
            
            # Agent special label
            if action == 'ai_agent':
                label = f"🤖 AGENT: {step.get('value', '')[:15]}..."
            
            # Formas según acción
            if action == 'navigate': shape_l, shape_r = '[', ']'
            elif action == 'click': shape_l, shape_r = '(', ')'
            elif action == 'fill': shape_l, shape_r = '[/', '/]'
            elif action == 'ai_agent': shape_l, shape_r = '{{', '}}'
            else: shape_l, shape_r = '[', ']'
            
            # Escape quotes in label
            label = label.replace('"', "'")
            
            node_id = f"step{i}"
            mm.append(f"{node_id}{shape_l}\"{label}\"{shape_r}")
            
            # Conexión
            if i > 0: mm.append(f"step{i-1} --> {node_id}")
            
            # Aplicar clases
            if i == error_index: mm.append(f"class {node_id} error")
            elif i == current_step_index: mm.append(f"class {node_id} active")

        return "\n".join(mm)

    def resolve_intervention(action, playbook_update):
        if repair_future and not repair_future.done():
            repair_future.set_result((action, playbook_update)) # playbook_update is None if no change
        repair_dialog.close()

    # --- AGENT DELEGATION DIALOG ---
    agent_future = None
    with ui.dialog() as agent_dialog, ui.card().classes('w-[600px] p-6'):
        with ui.row().classes('w-full items-center gap-2 mb-4'):
            ui.icon('travel_explore', size='2em', color='purple')
            ui.label('Delegar al Agente Autónomo').classes('text-xl font-bold text-purple-700')
        
        ui.label('Describe qué debe hacer el agente. (Ej: "Extrae todos los precios de la tabla y guárdalos en Excel")').classes('text-gray-500 mb-2')
        d_agent_instruction = ui.textarea(placeholder="Instrucción...").classes('w-full mb-6 bg-purple-50').props('outlined autofocus')
        
        async def confirm_agent():
            if not d_agent_instruction.value: return
            if agent_future and not agent_future.done():
                agent_future.set_result(d_agent_instruction.value)
            agent_dialog.close()
            
        ui.button('🚀 Ejecutar Agente', on_click=confirm_agent).classes('w-full bg-purple-600 text-white font-bold shadow-md')

    # Loading Spinner for Agent
    with ui.dialog() as agent_spinner_dialog, ui.card().classes('items-center justify-center p-8'):
        ui.spinner(size='3em', color='purple')
        ui.label("Agente Trabajando...").classes('text-purple-600 font-bold mt-4 animate-pulse')
        ui.label("Por favor, no toques el navegador.").classes('text-xs text-gray-400')

    # Callback to be passed to Executor
    async def handle_intervention(error_msg: str, screenshot_path: str, step_index: int = -1):
        """
        Gestiona la intervención humana necesaria durante la ejecución de un robot.
        Muestra un diálogo de emergencia con la captura de pantalla del error y permite 
        al usuario dar feedback para reparar el proceso con la IA.

        Args:
            error_msg: Mensaje de error técnico capturado.
            screenshot_path: Ruta a la imagen del estado del navegador durante el fallo.
            step_index: Índice del paso en el Playbook donde ocurrió el error.
        """
        print(f"[UI] Intervención solicitada: {error_msg} en paso {step_index}")
        
        # Reset UI State
        d_error_msg.text = error_msg
        d_feedback.value = ""
        
        # Render Mermaid Flow with Error
        # Assuming wizard.playbook is the one running. If batch, it might differ slightly but usually consistent structure.
        # Ideally Executor should pass the current playbook too? 
        # For now, we use wizard.playbook or we can't show it.
        # If we are in Batch Mode, wizard.playbook might be the Master one.
        # step_index logic assumes wizard.playbook aligns with execution.
        if wizard.playbook:
            flow_chart = render_playbook_flow(wizard.playbook, current_step_index=step_index, error_index=step_index)
            d_mermaid_container.clear()
            with d_mermaid_container:
                ui.mermaid(flow_chart).classes('w-full h-48 bg-gray-50 rounded border p-2')
        
        if screenshot_path and os.path.exists(screenshot_path):
            import base64
            with open(screenshot_path, "rb") as img_f:
                b64 = base64.b64encode(img_f.read()).decode('utf-8')
                d_screenshot.set_source(f"data:image/png;base64,{b64}")
        else:
            d_screenshot.set_source('https://placehold.co/600x400?text=No+Image')
            
        repair_dialog.open()
        
        # Wait for user
        nonlocal repair_future
        repair_future = asyncio.Future()
        
        try:
            action, new_pb = await repair_future
            # If new_pb is returned, we should probably update wizard.playbook too to reflect UI
            if new_pb:
                wizard.playbook = new_pb
            return action, (new_pb if new_pb else wizard.playbook)
        except Exception as e:
            print(f"Intervention error: {e}")
            return "STOP", wizard.playbook
    
    # --- HANDLERS ---
    
    async def handle_excel_upload(e: events.UploadEventArguments):
        try:
            eid = wizard.ensure_context()
            input_dir = state.rpa.paths.get_input_dir(eid)
            file_path = input_dir / e.name
            
            with open(file_path, 'wb') as f:
                content = e.content.read()
                f.write(content)
                
            wizard.uploaded_excel_path = str(file_path)
            ui.notify(f"Excel cargado: {e.name}", type='positive')
        except Exception as ex:
            ui.notify(f"Error cargando Excel: {ex}", type='negative')

    async def handle_attachment_upload(e: events.UploadEventArguments):
        try:
            eid = wizard.ensure_context()
            input_dir = state.rpa.paths.get_input_dir(eid)
            file_path = input_dir / e.name
            
            with open(file_path, 'wb') as f:
                content = e.content.read()
                f.write(content)
                
            wizard.uploaded_attachments.append(str(file_path))
            ui.notify(f"Adjunto subido: {e.name}", type='positive')
        except Exception as ex:
            ui.notify(f"Error subiendo adjunto: {ex}", type='negative')

    async def start_recording():
        """
        Inicia una sesión de grabación de RPA.
        Abre el navegador en la URL objetivo y comienza a capturar eventos de usuario 
        para el aprendizaje del robot.
        """
        if not wizard.target_url:
            ui.notify("Por favor, introduce una URL inicial", type='warning')
            return

        # Prepare Context Data
        context_data = {}
        if wizard.data_mode == 'MANUAL':
            # Convert list of dicts to flat dict
            context_data = {item['key']: item['value'] for item in wizard.manual_data if item['key']}
        elif wizard.data_mode == 'EXCEL' and wizard.uploaded_excel_path:
            # We don't read it here, we pass the path or let the RPA executor read it if needed.
            # But the executor start_recording takes 'excel_file' as path to persist?
            # RPAExecutor.start_recording_session(url, excel_file=..., attachments_path=...)
            # Actually executor assumes logic logic. We might need to pass the dict for the current session context?
            # Looking at rpa_executor signature: start_recording_session(url, excel_file=None, attachments_path=None...)
            pass

        # Call Executor
        wizard.phase = 'RECORDING'
        render_wizard.refresh()
        
        try:
            log_comp.push(f"🚀 Iniciando navegador en {wizard.target_url}...")
            
            # We pass the input dir as attachments path so the recorder knows where to look for files
            eid = wizard.ensure_context()
            input_dir = state.rpa.paths.get_input_dir(eid)
            
            await state.rpa.start_recording_session(
                url=wizard.target_url,
                _excel_file=wizard.uploaded_excel_path, # Executor expects path or file? Signature says excel_file.
                _attachments_path=str(input_dir),
                log_callback=lambda msg: log_comp.push(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")
            )
            
        except Exception as e:
            ui.notify(f"Error al iniciar: {e}", type='negative')
            wizard.phase = 'SETUP'
            render_wizard.refresh()



    async def stop_and_analyze():
        """
        Finaliza la grabación actual y procesa los eventos capturados.
        Aplica anonimización a los datos sensibles antes de enviar los logs a la IA 
        para generar un Playbook estructurado y optimizado.
        """
        log_comp.push("🛑 Deteniendo grabación...")
        
        try:
            # 1. Stop & Get Logs
            logs = await state.rpa.stop_recording_and_get_logs(
                log_callback=lambda msg: log_comp.push(f"STOP: {msg}")
            )
            
            if not logs:
                ui.notify("No se capturaron eventos.", type='warning')
                wizard.phase = 'SETUP'
                render_wizard.refresh()
                return

            # 2. Analyze
            log_comp.push("🧠 Analizando acciones con IA...")
            
            # Prepare context for Brain
            ctx = {}
            if wizard.data_mode == 'MANUAL':
                 ctx = {item['key']: item['value'] for item in wizard.manual_data if item['key']}
            elif wizard.data_mode == 'EXCEL' and wizard.uploaded_excel_path:
                # Try to read first row for context
                try:
                    import pandas as pd
                    df = pd.read_excel(wizard.uploaded_excel_path)
                    if not df.empty:
                        ctx = json.loads(df.iloc[0].to_json())
                except: pass

            # PROMPT 3.7: ANONYMIZATION Logic
            log_comp.push("🔒 Anonimizando datos sensibles antes de enviar a IA...")
            anonymizer = AnonymizationContext(locale="es_ES")
            
            anon_logs = []
            for log in logs:
                anon_log = log.copy()
                # Anonymize typical sensitive fields in logs
                for field in ['value', 'text', 'input_value', 'semantic_info']: 
                     if field in anon_log and anon_log[field]:
                         if isinstance(anon_log[field], str):
                             anon_log[field] = anonymizer.anonymize(anon_log[field])
                         elif isinstance(anon_log[field], dict):
                             # Recursive anonymization for dicts (e.g. semantic info)
                             anon_log[field] = {k: anonymizer.anonymize(str(v)) for k, v in anon_log[field].items()}
                             
                anon_logs.append(anon_log)

            playbook = await state.rpa.analyze_recording(anon_logs, context_dict=ctx)
            
            # PROMPT 3.7: REHYDRATION Logic
            log_comp.push("🔓 Restaurando datos originales en playbook...")
            for step in playbook:
                if 'value' in step and step['value'] and isinstance(step['value'], str):
                    step['value'] = anonymizer.deanonymize(step['value'])
                if 'selector' in step and step['selector'] and isinstance(step['selector'], str):
                    # Selectors usually shouldn't be anonymized but if they contain PII (e.g. text content selector):
                     step['selector'] = anonymizer.deanonymize(step['selector'])

            wizard.playbook = playbook
            
            wizard.phase = 'REVIEW'
            render_wizard.refresh()
            
        except Exception as e:
            ui.notify(f"Fallo en análisis: {e}", type='negative')
            log_comp.push(f"ERROR: {e}")

    def reset_wizard():
        # Start fresh
        wizard.phase = 'SETUP'
        wizard.data_mode = 'MANUAL'
        wizard.playbook = []
        wizard.logs = []
        # Reset ID
        wizard.execution_id = None
        # No need to set context, next action will create
        render_wizard.refresh()

    # --- UI RENDERER ---

    @ui.refreshable
    def render_wizard():
        """
        Renderiza la interfaz del asistente de creación de robots.
        Cambia dinámicamente según la fase (configuración inicial, grabación en curso o revisión final).
        """
        
        # --- PHASE 1: SETUP ---
        if wizard.phase == 'SETUP':
            with ui.column().classes('w-full max-w-5xl mx-auto p-4 gap-6'):
                with ui.row().classes('items-center gap-4'):
                    ui.label(t('rpa_title')).classes('text-3xl font-bold text-slate-800')
                    
                    # PROMPT 3.7: PRIVACY INDICATOR
                    render_privacy_indicator()
                
                # Card 1: Target
                with ui.card().classes('w-full p-6 bg-white border border-gray-200 shadow-sm'):
                    ui.label("1. Objetivo").classes('text-lg font-bold text-slate-700 mb-2')
                    ui.input(
                        label="URL Inicial", 
                        placeholder="https://ejemplo.com/login",
                        on_change=lambda e: setattr(wizard, 'target_url', e.value)
                    ).bind_value(wizard, 'target_url').classes('w-full text-lg').props('outlined autofocus')

                # Card 2: Context
                with ui.card().classes('w-full p-6 bg-white border border-gray-200 shadow-sm'):
                    ui.label("2. Contexto de Datos (Variables)").classes('text-lg font-bold text-slate-700 mb-4')
                    
                    with ui.tabs().classes('w-full text-slate-600') as tabs:
                        tab_manual = ui.tab('Variables Manuales')
                        tab_excel = ui.tab('Cargar Excel (Lotes)')
                        
                    with ui.tab_panels(tabs, value=tab_manual if wizard.data_mode == 'MANUAL' else tab_excel).classes('w-full bg-slate-50 p-4 border rounded-b-lg').bind_value(wizard, 'data_mode'): # Bind fails with tab obj?
                        # Manual Binding for Tab Panels Value is tricky with Objects. Use string names or manual handler.
                        # Let's use on_change to update mode.
                        
                        with ui.tab_panel(tab_manual):
                            ui.label("Define variables clave para que la IA aprenda (Ej: Usuario, Contraseña, Busqueda)").classes('text-sm text-gray-500 mb-2')
                            
                            # AgGrid for Manual Data
                            grid = ui.aggrid({
                                'columnDefs': [
                                    {'headerName': 'Variable (Clave)', 'field': 'key', 'editable': True},
                                    {'headerName': 'Valor Ejemplo', 'field': 'value', 'editable': True}
                                ],
                                'rowData': wizard.manual_data,
                                'singleClickEdit': True,
                                'stopEditingWhenCellsLoseFocus': True
                            }).classes('h-48 w-full')
                            
                            # Sync back
                            async def update_data(e):
                                wizard.manual_data = await grid.get_rows()
                            grid.on('cellValueChanged', update_data)
                            
                            ui.button('Añadir Fila', on_click=lambda: grid.run_row_method(None, 'add', [{'key': '', 'value': ''}])).props('flat dense size=sm icon=add')

                        with ui.tab_panel(tab_excel):
                            ui.label("Sube un Excel con múltiples filas. Usaremos la primera fila como ejemplo para el aprendizaje.").classes('text-sm text-gray-500 mb-2')
                            ui.upload(
                                label="Arrastra tu Excel aquí (.xlsx)", 
                                auto_upload=True, 
                                on_upload=handle_excel_upload
                            ).props('accept=.xlsx,.xls flat bordered color=green-600').classes('w-full bg-green-50')
                            
                            if wizard.uploaded_excel_path:
                                ui.label(f"Archivo cargado: {os.path.basename(wizard.uploaded_excel_path)}").classes('text-green-700 font-bold mt-2')

                # Card 3: Attachments
                with ui.card().classes('w-full p-6 bg-white border border-gray-200 shadow-sm'):
                    with ui.expansion("3. Adjuntos (Opcional)", icon="attach_file").classes('w-full font-bold text-slate-700'):
                        ui.label("Si el proceso requiere subir archivos, cárgalos aquí para que el robot los tenga disponibles.").classes('text-sm text-gray-500 mb-2 font-normal')
                        ui.upload(
                            label="Adjuntos para el Robot",
                            multiple=True,
                            auto_upload=True,
                            on_upload=handle_attachment_upload
                        ).props('flat bordered color=indigo-500').classes('w-full bg-indigo-50')

                # Action
                ui.button("Iniciar Grabación", icon='videocam', on_click=start_recording) \
                    .classes('w-full h-16 text-xl font-bold bg-gradient-to-r from-red-500 to-pink-600 text-white rounded-lg shadow-lg hover:scale-[1.01] transition-transform')

        # --- PHASE 2: RECORDING ---
        elif wizard.phase == 'RECORDING':
            with ui.column().classes('w-full h-[85vh] items-center justify-center max-w-4xl mx-auto p-4'):
                
                # Status Indicator
                with ui.row().classes('items-center mb-6 gap-4 animate-pulse'):
                    ui.icon('radio_button_checked', size='3em', color='red')
                    ui.label("Grabando... Interactúa con el navegador").classes('text-3xl font-bold text-red-600')

                ui.label("El robot está aprendiendo de tus acciones. Realiza el proceso completo una vez.").classes('text-slate-500 text-lg mb-8')

                # Logs
                with ui.card().classes('w-full bg-slate-900 border-slate-700 p-0 mb-8 shadow-inner'):
                    ui.label("Event Stream").classes('text-xs font-bold text-slate-500 p-2 border-b border-slate-700 bg-slate-800 w-full')
                    global log_comp # Hack for async handlers access
                    log_comp = ui.log().classes('w-full h-48 font-mono text-green-400 text-xs p-4 bg-slate-900').style('overflow-y: auto')

                # Controls
                with ui.row().classes('gap-4'):
                    
                    async def delegate_task():
                        d_agent_instruction.value = ""
                        agent_dialog.open()
                        
                        nonlocal agent_future
                        agent_future = asyncio.Future()
                        
                        try:
                            instruction = await agent_future
                            agent_spinner_dialog.open()
                            
                            try:
                                # Run Backend
                                res = await state.rpa.run_agent_interactive(instruction)
                                
                                agent_spinner_dialog.close()
                                
                                if res.get('success'):
                                    ui.notify("Agente finalizó tarea exitosamente", type='positive')
                                    output_text = res.get('output', '')
                                    
                                    # Inject artificial event into browser recording
                                    # This ensures it appears in the logs and analysis later
                                    # We simulate a special event type 'ai_agent'
                                    js_inject = f"""
                                    window.recorded_actions.push({{
                                        type: 'ai_agent',
                                        selector: '',
                                        semantic: {{ instruction: "{instruction}", output: `{output_text.replace('`', '')}` }},
                                        timestamp: Date.now(),
                                        value: "{instruction}"
                                    }});
                                    """
                                    if state.rpa.page:
                                        await state.rpa.page.evaluate(js_inject)
                                        log_comp.push(f"🤖 AGENT: {instruction}")
                                else:
                                    ui.notify(f"Agente reportó error: {res.get('error')}", type='negative')
                                    
                            except Exception as e:
                                agent_spinner_dialog.close()
                                ui.notify(f"Error invocando agente: {e}", type='negative')
                        except:
                            pass # Dialog Cancelled

                    ui.button("🤖 Delegar a Agente", on_click=delegate_task) \
                        .classes('w-64 h-20 text-xl font-bold bg-purple-700 text-white border-2 border-purple-500 hover:bg-purple-600 rounded-full shadow-xl transition-all hover:scale-105')

                    ui.button("⏹️ Finalizar y Analizar", on_click=stop_and_analyze) \
                        .classes('w-64 h-20 text-xl font-bold bg-slate-800 text-white border-2 border-slate-600 hover:bg-slate-700 rounded-full shadow-xl transition-all hover:scale-105')

        # --- PHASE 3: REVIEW ---
        elif wizard.phase == 'REVIEW':
            with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
                
                # Header
                with ui.row().classes('w-full items-center justify-between mb-6'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('check_circle', size='3em').classes('text-green-500')
                        with ui.column().classes('gap-0'):
                            ui.label(f"Playbook Generado: {len(wizard.playbook)} pasos").classes('text-2xl font-bold text-slate-800')
                            ui.label("Revisa la lógica extraída antes de guardar.").classes('text-slate-500')
                    
                    ui.button("Descartar", on_click=reset_wizard, icon='delete').props('flat color=red')

                # Content layout
                with ui.row().classes('w-full gap-6 items-start'):
                    
                    # Left: Viewer
                    with ui.card().classes('w-2/3 p-0 border border-gray-200 shadow-sm h-[600px] flex flex-col'):
                        ui.label("Secuencia de Acciones").classes('p-4 font-bold border-b border-gray-100 bg-slate-50')
                        
                        with ui.scroll_area().classes('w-full h-1/3 border-b border-gray-100 p-2 bg-slate-50'):
                            if wizard.playbook:
                                ui.mermaid(render_playbook_flow(wizard.playbook)).classes('w-full')
                            else:
                                ui.label("No hay pasos grabados").classes('text-gray-400')

                        ui.json_editor({'content': {'json': wizard.playbook}}, ).classes('w-full flex-grow')

                    # Right: Actions
                    with ui.column().classes('w-1/3 gap-4'):
                        
                        # 1. Save
                        with ui.card().classes('w-full p-6 border-l-4 border-l-green-500'):
                            ui.label("Guardar en Librería").classes('text-lg font-bold mb-4')
                            name_input = ui.input("Nombre del Proceso", placeholder="Ej: Solicitar Beca").classes('w-full mb-4')
                            
                            async def save_lib():
                                if not name_input.value:
                                    ui.notify("Escribe un nombre", type='warning')
                                    return
                                await state.rpa.save_master_playbook(name_input.value, wizard.target_url)
                                ui.notify(f"Guardado: {name_input.value}", type='positive')
                                reset_wizard()

                            ui.button("Guardar Proceso", icon='save', on_click=save_lib).classes('w-full bg-green-600 text-white')

                        # 2. Refine
                        with ui.card().classes('w-full p-6 border-l-4 border-l-blue-500'):
                            ui.label("Refinar con IA").classes('text-lg font-bold mb-2')
                            ui.label("¿El robot se ha equivocado? Da feedback.").classes('text-xs text-slate-500 mb-2')
                            
                            feedback_input = ui.textarea(placeholder="Ej: El paso 3 sobra. Usa la fecha de ayer.").classes('w-full mb-2 bg-slate-50')
                            
                            async def refine_act():
                                if not feedback_input.value: return
                                ui.notify("Refinando lógica...", type='info')
                                wizard.feedback_history.append(feedback_input.value)
                                
                                try:
                                    # Prepare Context same as Analyze
                                    ctx = {}
                                    if wizard.data_mode == 'MANUAL':
                                        ctx = {item['key']: item['value'] for item in wizard.manual_data}
                                    
                                    # Mock error log or empty
                                    errors = "User Refinement Request"
                                    
                                    new_pb = await state.rpa.refine_playbook(
                                        current_playbook=wizard.playbook,
                                        recording_logs=await state.rpa.stop_recording_and_get_logs(), # Might be empty now
                                        error_logs=errors,
                                        user_feedback_history=wizard.feedback_history,
                                        context_data=ctx
                                    )
                                    wizard.playbook = new_pb
                                    ui.notify("Playbook actualizado", type='positive')
                                    render_wizard.refresh()
                                except Exception as e:
                                    ui.notify(f"Error: {e}", type='negative')

                            ui.button("Regenerar", icon='auto_fix_high', on_click=refine_act).classes('w-full bg-blue-100 text-blue-800')

                        # 3. Test
                        with ui.card().classes('w-full p-6 border-l-4 border-l-orange-500'):
                            ui.label("Prueba Rápida").classes('text-lg font-bold mb-2')
                            
                            async def quick_test():
                                ui.notify("Lanzando prueba...", type='warning')
                                # Use manual data as row
                                row = {}
                                if wizard.data_mode == 'MANUAL':
                                     row = {item['key']: item['value'] for item in wizard.manual_data}
                                
                                try:
                                    # PASAR CALLBACK DE INTERVENCION!
                                    await state.rpa.run_playbook_batch(
                                        wizard.playbook, 
                                        explicit_rows=[row],
                                        on_ask_user=handle_intervention
                                    )
                                    ui.notify("Prueba finalizada", type='positive')
                                except Exception as e:
                                    ui.notify(f"Fallo prueba: {e}", type='negative')

                            ui.button("Ejecutar Test", icon='play_arrow', on_click=quick_test).classes('w-full bg-orange-100 text-orange-800')

    # --- MAIN RENDERER ---
    
    # State for Selector
    # We use a simple list to hold the selected ID to avoid scope issues in refreshable
    selection_state = {'id': None}

    def on_selection_change(new_id):
        selection_state['id'] = new_id
        render_main_content.refresh()

    @ui.refreshable
    async def render_main_content():
        # 1. Selector
        from client_app.app.ui.components.automation_selector import render_automation_selector
        await render_automation_selector(
            automation_type='RPA_WEB', 
            on_change=on_selection_change,
            label="Automatización Web (RPA)"
        )

        # 2. Dynamic Content
        if selection_state['id']:
            # EXECUTION MODE
            with ui.card().classes('w-full max-w-5xl mx-auto p-6 bg-slate-50 border border-slate-200 mt-4'):
                ui.label(f"Ejecutar Automatismo: {selection_state['id']}").classes('text-xl font-bold text-slate-700')
                ui.label("Funcionalidad de ejecución directa en desarrollo...").classes('text-gray-500 italic')
                
                # Placeholder for Launcher
                ui.button("Lanzar (Simulado)", on_click=lambda: ui.notify("Ejecución iniciada", type='positive')).classes('mt-4 bg-blue-600 text-white')
                
                # Option to edit?
                ui.button("Editar / Ver Detalles", on_click=lambda: ui.notify("Editor no implementado", type='warning')).props('flat').classes('mt-2')

        else:
            # CREATION MODE (Existing Wizard)
            render_wizard()

    # Initial Render
    await render_main_content()
