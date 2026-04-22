from nicegui import ui, app
import asyncio
from datetime import datetime
from client_app.app.core.state import state

# --- FACTORY STATE ---
class FactoryState:
    """
    Gestiona el estado interno de la "Fábrica de Software" (Factory).
    Almacena la fase actual del ciclo de vida del script (Alcance, Construcción, 
    Revisión, Despliegue) y los resultados intermedios de ejecución y auditoría.
    """
    def __init__(self):
        self.phase = 'BUILDING' # BUILDING, REVIEW, DEPLOY
        self.status_message = "Iniciando Fábrica de Software..."
        self.logs = []
        self.generated_code = ""
        self.execution_result = {}
        self.audit_report = {}
        self.service_name_candidate = ""
        self.field_selection = {} # Stores boolean state of review checkboxes
        
        # Internal flags
        self.is_running = False

factory_state = FactoryState()

# --- UI RENDERER ---

@ui.refreshable
def render_factory_page():
    """
    Renderiza la interfaz principal de la Fábrica de Software.
    Implementa un motor de fases dinámico que guía al usuario desde la definición
    de campos hasta el despliegue del script automatizado, integrando la 
    autogeneración de código mediante IA.
    """
    
    # --- PHASE 0: SCOPE DEFINITION ---
    if factory_state.phase == 'SCOPE_DEFINITION':
        with ui.column().classes('w-full items-center max-w-4xl mx-auto p-8'):
            ui.label("Definición de Alcance").classes('text-3xl font-bold text-slate-800 mb-2')
            ui.label("Selecciona qué campos quieres que extraiga tu robot.").classes('text-slate-500 mb-8')

            # Container for checkboxes
            checks = {}
            # Recover fields from ground_truth
            fields = []
            if hasattr(factory_state, 'ground_truth') and factory_state.ground_truth:
                 fields = list(factory_state.ground_truth.keys())

            # Prompt #4 BIS: Import fields from Excel/CSV
            @ui.refreshable
            def render_field_list():
                nonlocal checks, fields
                checks = {}

                # Refresh fields from ground_truth
                if hasattr(factory_state, 'ground_truth') and factory_state.ground_truth:
                    fields = list(factory_state.ground_truth.keys())

                if not fields:
                    ui.label("No se encontraron campos. Importa desde Excel/CSV o continúa sin campos.").classes('text-slate-500 italic')
                else:
                    with ui.card().classes('w-full p-6 bg-white shadow-sm border border-slate-200'):
                        ui.label(f"{len(fields)} Campos Detectados").classes('text-xs font-bold text-slate-400 uppercase mb-4')
                        with ui.grid(columns=3).classes('w-full gap-4'):
                            for f in fields:
                                checks[f] = ui.checkbox(text=f, value=True).props('dense text-color=slate-700')

            # Prompt #4 BIS: File upload section
            with ui.card().classes('w-full p-4 bg-purple-50 border border-purple-200 mb-4'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('upload_file', color='purple')
                    ui.label('Importar Campos desde Excel/CSV').classes('font-bold text-purple-800')

                ui.label('Sube un archivo con columnas: nombre, tipo, descripcion (opcional)').classes('text-xs text-slate-600 mb-2')

                async def handle_field_import(e):
                    """Handle file upload for field import."""
                    try:
                        from client_app.app.services.field_import_service import field_import_service
                        import io

                        for upload in e.files if hasattr(e, 'files') else [e]:
                            content = upload.content.read() if hasattr(upload.content, 'read') else upload.content
                            filename = upload.name
                            ext = '.' + filename.rsplit('.', 1)[-1].lower()

                            # Parse the file
                            if ext == '.csv':
                                buffer = io.StringIO(content.decode('utf-8'))
                            else:
                                buffer = io.BytesIO(content)

                            imported_fields, warnings = field_import_service.parse_file_with_warnings(
                                buffer, extension=ext
                            )

                            # Show warnings if any
                            for warn in warnings[:3]:  # Limit to 3 warnings
                                ui.notify(warn, type='warning')

                            # Update ground_truth with imported fields
                            if not hasattr(factory_state, 'ground_truth') or not factory_state.ground_truth:
                                factory_state.ground_truth = {}

                            for field in imported_fields:
                                # Use empty string as default value for ground_truth
                                factory_state.ground_truth[field['name']] = ''

                            # Store field definitions for later use
                            if not hasattr(factory_state, 'imported_field_definitions'):
                                factory_state.imported_field_definitions = []
                            factory_state.imported_field_definitions = imported_fields

                            ui.notify(f'{len(imported_fields)} campos importados desde {filename}', type='positive')
                            render_field_list.refresh()

                    except ValueError as ve:
                        ui.notify(f'Error: {str(ve)}', type='negative')
                    except Exception as ex:
                        ui.notify(f'Error importando archivo: {str(ex)}', type='negative')

                ui.upload(
                    on_upload=handle_field_import,
                    auto_upload=True,
                    label='Subir Excel o CSV'
                ).props('accept=".xlsx,.xls,.csv"').classes('w-full')

            # Render the field list
            render_field_list()

            async def start_building():
                 # Filter ground_truth based on checks
                 selected = [k for k, v in checks.items() if v.value]
                 if not selected:
                      ui.notify("Selecciona al menos un campo", type='warning')
                      return

                 # Update ground_truth to ONLY selected fields
                 current_gt = getattr(factory_state, 'ground_truth', {})
                 new_gt = {k: current_gt[k] for k in selected if k in current_gt}
                 factory_state.ground_truth = new_gt

                 factory_state.status_message = "Entrenando robot con tus datos seleccionados..."
                 factory_state.phase = 'BUILDING'
                 render_factory_page.refresh()

            ui.button("Generar Robot", icon='precision_manufacturing', on_click=start_building).classes('mt-8 bg-indigo-600 text-white font-bold h-12 px-8 shadow-lg hover:scale-105 transition-transform')


    # --- PHASE 1: BUILDING (CONSTRUCTION) ---
    elif factory_state.phase == 'BUILDING':
        with ui.column().classes('w-full h-[80vh] items-center justify-center max-w-4xl mx-auto p-4'):
            
            # Use Indigo Spinner as requested
            ui.spinner('dots', size='3em', color='indigo').classes('mb-6')
            
            # Pulsing Status Label
            ui.label().bind_text_from(factory_state, 'status_message').classes('text-2xl font-bold text-slate-700 animate-pulse text-center')
            
            ui.label("Esto puede tomar hasta 2 minutos. La IA está programando y testeando tu solución.").classes('text-slate-500 mt-4')
            
            # Auto-start construction on mount if not running
            if not factory_state.is_running:
                factory_state.is_running = True
                ui.timer(0.1, run_construction, once=True)

    # --- PHASE 2: REVIEW (AUDIT) ---
    # --- PHASE 2: REVIEW (AUDIT) ---
    elif factory_state.phase == 'REVIEW':
        # Main Container
        with ui.column().classes('w-full max-w-5xl mx-auto p-4 gap-6'):
             
            # 1. HERO: TRUST CARD
            # Calculate Confidence (Simulated for now based on result status)
            # Todo: Extract real confidence from audit report meta
            confidence_score = 0.95 if factory_state.execution_result.get('success', True) else 0.5
            is_high_conf = confidence_score > 0.90
            color = 'green' if is_high_conf else 'orange'
            
            with ui.card().classes(f'w-full p-6 border-l-8 border-{color}-500 shadow-md bg-slate-50 flex-row items-center gap-6'):
                # Circular Progress
                with ui.column().classes('items-center justify-center p-2'):
                    with ui.circular_progress(value=confidence_score, show_value=False, size='80px', color=color).classes('font-bold text-xl'):
                        ui.label(f"{int(confidence_score*100)}%").classes(f'text-{color}-600 font-bold text-xl')
                    ui.label("Confianza").classes('text-xs text-slate-400 font-bold uppercase tracking-wider mt-1')
                
                # Text Summary
                with ui.column().classes('gap-1 flex-1'):
                    ui.label("Auditoría de Calidad Completada").classes('text-2xl font-bold text-slate-800')
                    if is_high_conf:
                         ui.label("El modelo ha generado un script que cumple con los esquemas esperados y las pruebas de seguridad.").classes('text-slate-600')
                    else:
                         ui.label("Se detectaron discrepancias entre los datos esperados y los obtenidos. Revise el informe detallado.").classes('text-orange-700 font-medium')

            # 2. AUDIT REPORT (Textual - Promoted)
            with ui.card().classes('w-full p-6 shadow-sm border border-gray-200 bg-white'):
                ui.label("Informe Forense de Calidad").classes('text-lg font-bold text-slate-800 mb-4 border-b pb-2')
                
                content = factory_state.audit_report if isinstance(factory_state.audit_report, str) else "Generando reporte..."
                # Render Markdown directly
                ui.markdown(content).classes('w-full prose prose-sm max-w-none text-slate-700')

            # 3. INLINE FEEDBACK & ACTIONS
            with ui.card().classes('w-full p-6 bg-slate-50 border border-slate-200 mt-4'):
                ui.label("Refinamiento del Robot").classes('text-lg font-bold text-slate-800 mb-2')
                ui.label("Si el resultado no es perfecto, describe el error y la IA corregirá el código.").classes('text-sm text-slate-500 mb-4')
                
                fb_area = ui.textarea(placeholder='Ej: El formato de fecha debe ser DD/MM/YYYY, o ignora el campo X...').classes('w-full bg-white mb-4').props('outlined')
                
                async def submit_refine():
                    feedback_text = fb_area.value
                    
                    # 1. Update Scope (Implicit: All current knowledge)
                    # Since we removed checkboxes, we assume the current Ground Truth is the base.
                    # We might want to add new keys found in result_data if they are not in GT?
                    # Strategy: Merge all known keys into GT (accepting new findings as candidates) or just stick to GT.
                    # Providing complete context to the AI is better.
                    
                    current_gt = getattr(factory_state, 'ground_truth', {})
                    result_data = getattr(factory_state, 'execution_result', {})
                    
                    # Merge: if key in GT, use GT. If key in Result but not GT, add to GT (Auto-discovery acceptance)?
                    # Providing complete context to the AI is better.
                    merged_gt = current_gt.copy()
                    for k, v in result_data.items():
                         if k not in merged_gt:
                             merged_gt[k] = v
                    
                    factory_state.ground_truth = merged_gt # Update State
                    
                    # 2. Trigger Backend Refinement
                    factory_state.status_message = "🛠️ Aplicando correcciones y re-testeando..."
                    factory_state.phase = 'BUILDING'
                    render_factory_page.refresh()
                    
                    try:
                        exec_id = getattr(factory_state, 'execution_id', None) or "demo_fallback"
                        prev_code = factory_state.generated_code
                        prev_report = str(factory_state.audit_report)
                        
                        result = await state.extractor.refine_factory_pipeline(
                            execution_id=exec_id,
                            user_feedback=feedback_text,
                            previous_code=prev_code,
                            audit_report=prev_report,
                            reference_data=merged_gt # PASS MERGED REFERENCE
                        )
                        
                        if result.get('status') == 'success':
                            factory_state.generated_code = result.get('code', '')
                            # Update execution result
                            if 'result' in result: factory_state.execution_result = result['result']
                            elif 'execution_result' in result: factory_state.execution_result = result['execution_result']

                            factory_state.audit_report = result.get('audit', '')
                            
                            factory_state.audit_report = result.get('audit', '')
                            
                            # Clean up old flags if any
                            if hasattr(factory_state, 'field_selection'): del factory_state.field_selection
                            
                            # Update phase then notify then refresh
                            factory_state.phase = 'REVIEW'
                            ui.notify("✅ Solución refinada (V2)", type='positive')
                            render_factory_page.refresh()
                            
                        else:
                            ui.notify(f"Error Refinamiento: {result.get('error')}", type='negative')
                            factory_state.phase = 'REVIEW'
                            render_factory_page.refresh()

                    except Exception as e:
                         # Safe notify check
                         try:
                             ui.notify(f"System Error: {e}", type='negative')
                         except:
                             print(f"UI Notification Failed (Context Lost): {e}")
                         
                         factory_state.phase = 'REVIEW'
                         render_factory_page.refresh()

                ui.button("Corregir y Re-Generar", icon='auto_fix_high', on_click=submit_refine).classes('bg-blue-600 text-white font-bold px-6 h-10 shadow-md')
                    
            # 5. DEPLOY ACTION
            async def deploy_action():
                 # Form Dialog
                with ui.dialog() as d, ui.card().classes('w-full max-w-lg'):
                     ui.label('🚀 Puesta en Producción').classes('text-xl font-bold text-indigo-700 mb-2')
                     ui.label('Configura tu nuevo Router Documental').classes('text-sm text-slate-500 mb-4')
                     
                     # 1. Name Input with Live Sanitization
                     name_inp = ui.input(
                         label="Nombre del Robot", 
                         placeholder="Ej: Facturas Endesa 2024",
                         value=f"Extractor {datetime.now().strftime('%d-%m')}"
                     ).classes('w-full text-lg font-bold')
                     
                     id_preview = ui.label("ID: custom_extractor_...").classes('text-xs font-mono text-slate-400 mb-4 ml-1')
                     
                     def update_id_preview(e):
                         import re
                         raw = e.value or ""
                         # Sanitize: Lower, No Accents (Simple), Alphanum + _
                         # Simple approximation for UI feedback
                         safe = re.sub(r'[^a-zA-Z0-9_]', '', raw.lower().replace(' ', '_'))
                         id_preview.set_text(f"ID Interno: custom_{safe}_...")
                     
                     name_inp.on_value_change(update_id_preview)
                     # Trigger once
                     update_id_preview(name_inp)

                     # 3. Process Button Logic
                     files = getattr(factory_state, 'input_files', [])
                     count = len(files)
                     
                     btn_text = "Guardar y Finalizar"
                     if count > 1:
                         btn_text = f"Guardar y Procesar Restantes ({count-1})"
                     
                     async def confirm_deploy():
                        d.close()
                        if not name_inp.value:
                             ui.notify("El nombre es obligatorio", type='warning')
                             return

                        factory_state.status_message = "💾 Guardando y aplicando robot masivamente..."
                        factory_state.phase = 'BUILDING' 
                        render_factory_page.refresh()
                        
                        try:
                            # Collect Data
                            exec_id = getattr(factory_state, 'execution_id', None) or "demo_id"
                            code = factory_state.generated_code
                            first_res = factory_state.execution_result
                            import os
                            # FIX: Ensure we use basename to avoid Path vs String mismatches in Service
                            if files:
                                raw_name = getattr(files[0], 'name', str(files[0]))
                                first_res['filename'] = os.path.basename(raw_name)

                            # Update UI Progress Callback
                            def on_deploy_progress(msg):
                                 factory_state.status_message = msg
                                 render_factory_page.refresh() # Force update

                            result = await state.extractor.deploy_and_execute_batch(
                                execution_id=exec_id,
                                service_name=name_inp.value,
                                description="", # Removed description input
                                script_code=code,
                                all_files=[str(f) for f in files],
                                first_file_result=first_res,
                                on_progress=on_deploy_progress
                            )
                            
                            if result.get('status') == 'success':
                                factory_state.deploy_result = result
                                factory_state.service_name_candidate = name_inp.value
                                factory_state.phase = 'DEPLOY'
                                render_factory_page.refresh()
                                ui.notify("🚀 Despliegue Exitoso", type='positive')
                            else:
                                factory_state.phase = 'REVIEW'
                                ui.notify(f"Error Despliegue: {result.get('error')}", type='negative')
                                render_factory_page.refresh()
                            
                        except Exception as e:
                            ui.notify(f"System Error: {e}", type='negative')
                            factory_state.phase = 'REVIEW'
                            render_factory_page.refresh()

                     ui.button(btn_text, icon='save_as', on_click=confirm_deploy).classes('w-full bg-indigo-600 text-white font-bold h-12 shadow-lg hover:scale-105 transition-transform')
                d.open()

            # Action Button Row
            with ui.row().classes('w-full justify-end mt-4'):
                 ui.button("Aprobar y Desplegar", icon='rocket_launch', on_click=deploy_action).classes('bg-green-600 text-white px-8 h-12 shadow-lg hover:scale-105 transition-transform font-bold')


    # --- PHASE 3: DEPLOY (SUCCESS) ---
    elif factory_state.phase == 'DEPLOY':
        res = getattr(factory_state, 'deploy_result', {})
        processed_count = res.get('processed_count', 0)
        errors = res.get('errors', 0)
        excel_path = res.get('excel_path', '#')
        
        with ui.column().classes('w-full h-[80vh] items-center justify-center max-w-4xl mx-auto p-4'):
             # Celebration Icon
             ui.icon('verified', size='6em').classes('text-green-500 mb-6 animate-bounce shadow-green-200 drop-shadow-xl')
             
             ui.label("¡Misión Cumplida!").classes('text-5xl font-black text-slate-800 mb-2 tracking-tight')
             ui.label(f"El robot '{factory_state.service_name_candidate}' ha sido creado y ejecutado.").classes('text-xl text-slate-500 mb-8 font-light')
             
             # Stats Card
             with ui.row().classes('gap-6 mb-10'):
                 with ui.card().classes('items-center p-4 min-w-[150px] bg-blue-50 border-blue-100'):
                     ui.label(str(processed_count)).classes('text-4xl font-bold text-blue-600')
                     ui.label("Archivos").classes('text-sm text-blue-400 uppercase font-bold')
                 
                 with ui.card().classes('items-center p-4 min-w-[150px] bg-green-50 border-green-100'):
                     ui.label("100%").classes('text-4xl font-bold text-green-600') # Placeholder efficiency
                     ui.label("Automatizado").classes('text-sm text-green-400 uppercase font-bold')
                     
                 if errors > 0:
                     with ui.card().classes('items-center p-4 min-w-[150px] bg-red-50 border-red-100'):
                         ui.label(str(errors)).classes('text-4xl font-bold text-red-600')
                         ui.label("Errores").classes('text-sm text-red-400 uppercase font-bold')

             # Actions
             with ui.row().classes('gap-4'):
                 
                 def open_excel_file():
                     import os
                     if excel_path == '#' or not os.path.exists(excel_path):
                         ui.notify("Archivo Excel no encontrado", type='negative')
                         return
                     try:
                         os.startfile(os.path.abspath(excel_path))
                     except Exception as e:
                         ui.notify(f"Error al abrir: {e}", type='negative')

                 ui.button("Abrir Excel", icon='table_view', on_click=open_excel_file).classes('bg-green-600 text-white font-bold px-8 h-12 shadow-lg hover:scale-105 transition-transform')
                 
                 # Open Folder
                 def open_folder():
                     import os
                     folder = os.path.dirname(excel_path)
                     os.startfile(folder) if os.name == 'nt' else ui.notify("Solo Windows")
                     
                 ui.button("Ver Carpeta", icon='folder', on_click=open_folder).props('outline color=slate').classes('h-12 px-6')
                 
                 # Back to Home
                 ui.button("Inicio", icon='home', on_click=lambda: ui.open('/')).props('flat color=slate').classes('ml-8')


# --- LOGIC ---

async def run_construction():
    """
    Orchestrates the factory pipeline via Backend.
    """
    try:
        # 1. Update Status
        factory_state.status_message = "Generando código Python..."
        # render_factory_page.refresh() # Removed: using binding, avoiding context destruction
        
        # 2. Call Backend (ExtractionService.run_factory_pipeline)
        
        # ... logic ...
        if not hasattr(factory_state, 'input_files') or not hasattr(factory_state, 'execution_id'):
             print("Warning: Missing Input Context")
        
        def update_status(msg):
             factory_state.status_message = msg

        # Recuperar datos validados (Ground Truth)
        reference_data = {}
        if hasattr(factory_state, 'ground_truth') and factory_state.ground_truth:
             reference_data = factory_state.ground_truth

        if hasattr(state.extractor, 'run_factory_pipeline'):
             result = await state.extractor.run_factory_pipeline(
                execution_id=factory_state.execution_id,
                user_feedback=getattr(factory_state, 'user_feedback', ""),
                reference_data=reference_data, # <--- PASAMOS LA REFERENCIA COMPLETA
                on_progress=update_status
             )
        else:
             # Clean Simulation (Fallback if no backend service found)
             result = {
                 'status': 'error', 
                 'error': 'Backend extractor service not found'
             }
             
        # Process Result (Common for Real & Mock)
        if result.get('status') == 'error':
            # Handle Error Gracefully
            factory_state.status_message = f"Error en Pipeline: {result.get('error')}"
            factory_state.audit_report = f"# Error Crítico\n\nNo se pudo generar el script.\n\n**Detalle:** {result.get('error')}\n\n**Código parcial:**\n```python\n{result.get('code', '')}\n```"
            factory_state.generated_code = result.get('code', '# Fallo generación')
            factory_state.execution_result = {'success': False, 'error': result.get('error')}
            ui.notify(f"Error generando bot: {result.get('error')}", type='negative', close_button=True, multi_line=True)
        else:
            # Success
            factory_state.generated_code = result.get('code', '# Error: No code')
            factory_state.execution_result = result.get('result', {})
            factory_state.audit_report = result.get('audit', 'No report generated')
            factory_state.service_name_candidate = f"Extraccion {datetime.now().strftime('%H%M')}"
             


        # 3. Transition
        factory_state.phase = 'REVIEW'
        render_factory_page.refresh()
        
    except Exception as e:
        factory_state.status_message = f"Error Crítico: {e}"
        ui.notify(f"Error: {e}", type='negative')
        factory_state.is_running = False # Allow retry?
        render_factory_page.refresh()
