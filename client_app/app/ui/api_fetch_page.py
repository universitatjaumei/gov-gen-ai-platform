import json
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from nicegui import ui
from sqlmodel import select

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.api_connection_service import api_connection_service
from client_app.app.services.mail_watcher_service import mail_watcher_service
from client_app.app.database.models import APIEndpointConfig
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.page_header import page_header

# --- MODELS & STATE ---

class APIFetchPageState:
    def __init__(self):
        self.current_mode: str = 'library' # library, design, execution
        self.saved_configs: List[Dict[str, Any]] = []
        self.is_loading: bool = False

class DesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.url: str = ""
        self.method: str = "GET"
        self.auth_type: str = "none"
        self.auth_credential_id: Optional[int] = None
        self.headers_json: str = "{}"
        self.body_json: str = "{}"
        self.test_response: Optional[Any] = None
        self.test_error: Optional[str] = None
        self.is_testing: bool = False
        self.is_saving: bool = False
        self.is_readonly: bool = False

class ExecutionState:
    def __init__(self):
        self.config_entry: Optional[APIEndpointConfig] = None
        self.execution_result: Optional[Any] = None
        self.execution_error: Optional[str] = None
        self.is_running: bool = False
        self.logs: List[str] = []

# --- PAGE IMPLEMENTATION ---

async def api_fetch_page(api_id: Optional[int] = None, initial_mode: Optional[str] = None):
    page_state = APIFetchPageState()
    design_state = DesignState()
    exec_state = ExecutionState()
    colors = AtomColorScheme.get_colors(StepType.API_FETCH)
    t = state.i18n.t

    # --- INITIAL LAYOUT SETUP ---
    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.API_FETCH, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif api_id:
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.API_FETCH, atom_id=api_id)
    elif initial_mode == 'design':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.API_FETCH)
    elif initial_mode == 'execution':
        page_state.current_mode = 'execution'
        # enter_execution_mode will be called later
    else:
        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()

    # --- LOGIC ---

    async def load_saved_configs():
        page_state.is_loading = True
        render_page.refresh()
        page_state.saved_configs = await api_connection_service.list_configs()
        page_state.is_loading = False
        render_page.refresh()

    def go_to_library():
        # Si viene desde un flujo, volver al flujo
        flow_id = None
        if state.flow_context and state.flow_context.get('mode') == 'contextual':
            flow_id = state.flow_context.get('flow_id')
            
            # --- AUTO-GUARDAR FLUJO EN BBDD ---
            # Para evitar que los cambios del paso se pierdan al recargar flows_page.py
            if getattr(state, 'editing_flow', None) and flow_id:
                import asyncio
                # CAPTURAR DATOS ANTES DE LIMPIAR CONTEXTO
                current_flow_data = state.editing_flow 
                
                async def save_flow_bg():
                    try:
                        async with state.db_session() as session:
                            from client_app.app.services.flow_registry_service import FlowRegistryService
                            from automatia_shared.dtos import FlowSpec
                            reg = FlowRegistryService(session)
                            
                            # Reconstruir DTO para update_flow
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
                        print(f"Error auto-saving flow from API Fetch: {e}")
                
                asyncio.create_task(save_flow_bg())
            # ----------------------------------
            
        elif state.editing_flow and state.flow_id:
            flow_id = state.flow_id

        if flow_id:
            layout_manager.exit_design_mode_to_flow()
            state.clear_flow_context()
            state.clear_atom_editing_context()
            ui.navigate.to(f'/flows/{flow_id}')
            return

        layout_manager.exit_focus_mode()
        page_state.current_mode = 'library'
        render_page.refresh()

    async def start_new_design():
        design_state.__init__()
        layout_manager.enter_design_mode(StepType.API_FETCH)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def edit_config(config_id: int):
        config = await api_connection_service.get_config(config_id)
        if config:
            design_state.config_id = config.id
            design_state.name = config.name
            design_state.url = config.url
            design_state.method = config.method
            design_state.auth_type = config.auth_type
            design_state.auth_credential_id = config.auth_credential_id
            design_state.headers_json = config.headers
            design_state.body_json = config.body if hasattr(config, 'body') else "{}"
            design_state.test_response = None
            design_state.test_error = None
            
            # Si se abre desde un flujo (tiene config_id previo asignado), es de sólo lectura
            if state.flow_context and state.flow_context.get('mode') == 'contextual':
                design_state.is_readonly = True
            
            layout_manager.enter_design_mode(StepType.API_FETCH, atom_id=config_id)
            page_state.current_mode = 'design'
            render_page.refresh()

    async def run_execution(config_id: int):
        config = await api_connection_service.get_config(config_id)
        if config:
            exec_state.config_entry = config
            exec_state.execution_result = None
            exec_state.execution_error = None
            exec_state.logs = [f"Iniciando ejecución de {config.name}..."]
            
            layout_manager.enter_execution_mode(atom_id=config_id)
            page_state.current_mode = 'execution'
            render_page.refresh()
            await handle_execute()

    async def handle_test():
        design_state.is_testing = True
        design_state.test_error = None
        design_state.test_response = None
        # render_page.refresh()  <-- ELIMINADO para evitar RuntimeError
        
        try:
            temp_id = await api_connection_service.save_config({
                "id": design_state.config_id,
                "name": f"[TEST] {design_state.name}",
                "url": design_state.url,
                "method": design_state.method,
                "auth_type": design_state.auth_type,
                "auth_credential_id": design_state.auth_credential_id,
                "headers": design_state.headers_json,
                "body": design_state.body_json,
                "is_active": False
            })
            
            success, msg, data = await api_connection_service.test_connection(temp_id)
            if success:
                design_state.test_response = data
                try:
                    ui.notify("Prueba de conexión exitosa", type='positive')
                except RuntimeError:
                    pass
            else:
                design_state.test_error = msg
                try:
                    ui.notify(f"Error en la prueba: {msg}", type='negative')
                except RuntimeError:
                    pass
            
            if not design_state.config_id:
                await api_connection_service.delete_config(temp_id)
                
        except Exception as e:
            design_state.test_error = str(e)
            try:
                ui.notify(f"Error: {e}", type='negative')
            except RuntimeError:
                pass
        finally:
            design_state.is_testing = False

    async def handle_save():
        design_state.is_saving = True
        try:
            config_id = await api_connection_service.save_config({
                "id": design_state.config_id,
                "name": design_state.name,
                "url": design_state.url,
                "method": design_state.method,
                "auth_type": design_state.auth_type,
                "auth_credential_id": design_state.auth_credential_id,
                "headers": design_state.headers_json,
                "body": design_state.body_json,
                "is_active": True
            })
            
            # Aplicar Sello Atómico
            async with state.db_session() as session:
                from client_app.app.services.asset_finishing_service import AssetFinishingService
                finisher = AssetFinishingService(session)
                await finisher.seal_resource(config_id, StepType.API_FETCH)
                await session.commit()
            
            # --- UPDATE CONTEXTUAL FLOW STEP ---
            if state.flow_context and state.flow_context.get('mode') == 'contextual':
                step = state.flow_context.get('step')
                if step:
                    headers_dict = {}
                    try: headers_dict = json.loads(design_state.headers_json)
                    except: pass
                    
                    body_dict = None
                    try: body_dict = json.loads(design_state.body_json)
                    except: pass
                    
                    step.config = {
                        'config_id': config_id,
                        'url': design_state.url,
                        'method': design_state.method,
                        'headers': headers_dict,
                        'json_body': body_dict,
                        'auth_type': design_state.auth_type,
                        'credential_id': design_state.auth_credential_id
                    }
                    # Actualizar all_steps_config para que el preview refleje los cambios
                    from client_app.app.core.state import app_state
                    if app_state.editing_flow and hasattr(app_state.editing_flow, 'steps'):
                        app_state.refresh_flow_context_steps(app_state.editing_flow.steps)
                    if hasattr(state, 'on_step_change') and callable(state.on_step_change):
                        state.on_step_change()
                        
                # Marcar como de sólo lectura tras guardar como átomo en un flujo
                design_state.is_readonly = True
            # -----------------------------------

            try:
                ui.notify("Configuración guardada y Sellada", type='positive')
            except RuntimeError:
                pass
            go_to_library()
            await load_saved_configs()
        except Exception as e:
            try:
                ui.notify(f"Error al guardar: {e}", type='negative')
            except RuntimeError:
                pass
        finally:
            design_state.is_saving = False
            render_page.refresh()

    async def handle_execute():
        if not exec_state.config_entry: return
        exec_state.is_running = True
        
        try:
            exec_state.logs.append(f"Llamando a {exec_state.config_entry.method} {exec_state.config_entry.url}...")
            success, msg, data = await api_connection_service.test_connection(exec_state.config_entry.id)
            if success:
                exec_state.execution_result = data
                exec_state.logs.append("Respuesta recibida correctamente.")
            else:
                exec_state.execution_error = msg
                exec_state.logs.append(f"ERROR: {msg}")
        except Exception as e:
            exec_state.execution_error = str(e)
            exec_state.logs.append(f"EXCEPTION: {e}")
        finally:
            exec_state.is_running = False
            render_page.refresh()

    # --- RENDERERS ---

    @ui.refreshable
    def render_page():
        if page_state.current_mode == 'library': 
            with ui.column().classes('w-full p-6'):
                render_library()
        else:
            # Focus Mode (Design/Execution) uses standard full-page container
            with ui.column().classes('w-full h-full p-6 gap-0 overflow-hidden'):
                if page_state.current_mode == 'design': render_design()
                elif page_state.current_mode == 'execution': render_execution()

    def render_library():
        if page_state.is_loading:
            with ui.column().classes('w-full items-center py-20'):
                ui.spinner(size='lg')
            return
            
        # Mapping configs to resource dicts
        resources = []
        for c in page_state.saved_configs:
            resources.append({
                'id': c['id'],
                'name': c['name'],
                'description': f"{c['method']} {c['url']}",
                'status': 'published' if c.get('is_active', True) else 'draft',
                'source_module': 'api',
                'doc_path': None,
                'created_at': c.get('created_at'),
                'is_favorite': False,  # API configs don't have favorites (use ScriptLibrary for that)
            })

        layout = StandardPageLayout(
            title=t('api.title'),
            source_module='api',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_config(r['id']),
            on_delete=lambda r: delete_config_confirm(r), # Pass resource dict or id? confirm expects config dict
            on_execute=lambda r: run_execution(r['id']),
            help_description=t('api.help'),
            input_contract=['url', 'method', 'headers', 'auth_token', 'body'],
            output_contract=['status_code', 'response_body', 'headers']
        )
        layout.render()

    def delete_config_confirm(config):
        with ui.dialog() as d, ui.card():
            ui.label(f'¿Eliminar conexión "{config["name"]}"?').classes('text-lg font-bold')
            ui.label('Esta acción no se puede deshacer y puede afectar a flujos que la utilicen.')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel'), on_click=d.close).props('flat')
                async def do_delete():
                    await api_connection_service.delete_config(config['id'])
                    ui.notify("Conexión eliminada")
                    d.close()
                    await load_saved_configs()
                ui.button('Eliminar', on_click=do_delete).props('unelevated color=red')
        d.open()

    def render_design():
        if getattr(design_state, 'is_readonly', False):
             with ui.column().classes('w-full flex-grow mx-auto max-w-4xl p-4 gap-4'):
                 # Header con flecha de navegación para volver al flujo
                 with ui.column().classes('gap-1'):
                     with ui.row().classes('items-center gap-2'):
                         ui.button(icon='arrow_back', on_click=go_to_library).props('flat round color=primary')
                         ui.label('Acción Sellada').classes('text-2xl font-bold text-primary')
                     ui.label('Esta conexión se ha guardado en la biblioteca y su configuración es de sólo lectura dentro de este flujo.').classes('text-sm text-slate-500 ml-12')
                 with ui.card().classes('w-full bg-slate-50 border p-6 shadow-none'):
                     ui.label(t('api.conn_name')).classes('text-xs text-slate-500 font-bold uppercase')
                     ui.label(design_state.name).classes('text-lg text-slate-800 mb-4')
                     ui.label('Endpoint URL').classes('text-xs text-slate-500 font-bold uppercase')
                     with ui.row().classes('items-center gap-2 mb-4 w-full'):
                         ui.chip(design_state.method, color='blue', text_color='white').props('dense square')
                         ui.label(design_state.url).classes('font-mono text-slate-700 bg-white px-2 py-1 rounded border truncate flex-1')
                     ui.label('Autenticación').classes('text-xs text-slate-500 font-bold uppercase')
                     ui.label(design_state.auth_type).classes('text-sm text-slate-700 uppercase mb-4')
             return

        with ui.column().classes('w-full flex-grow overflow-y-auto gap-4 mb-4'):
            with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
                page_header(
                    t('api.designer_title') if not design_state.config_id else t('api.edit_title', name=design_state.name),
                    t('api.designer_subtitle'),
                    classes='w-full gap-0 mb-2'
                )
                
                # URL Full Width at the top
                with ui.card().classes('w-full p-4 shadow-sm border border-slate-50'):
                    ui.input(t('api.endpoint_url'), placeholder='https://api.empresa.com/v1/resource').classes('w-full text-sm font-mono').props('dense outlined').bind_value(design_state, 'url')

                with ui.grid(columns=2).classes('w-full gap-4'):
                    # Columna 1: Configuración, Auth y Test
                    with ui.column().classes('gap-3'):
                        with ui.card().classes('w-full p-4 shadow-sm border border-slate-50'):
                            ui.label(t('common.configuration')).classes('text-sm font-bold mb-1')
                            ui.input(t('api.conn_name'), placeholder='Ej: API de Clientes PROD').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'name')
                            ui.select(['GET', 'POST', 'PUT', 'DELETE', 'PATCH'], label=t('api.method')).classes('w-full text-sm mt-2').props('dense outlined').bind_value(design_state, 'method')

                        with ui.card().classes('w-full p-4 shadow-sm border border-slate-50'):
                            ui.label(t('api.auth')).classes('text-sm font-bold mb-1')
                            ui.select({
                                'none': t('api.auth_none'),
                                'bearer': 'Bearer Token',
                                'api_key': 'API Key (Header)',
                                'basic': 'Basic Auth'
                            }, label=t('api.auth_type')).classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'auth_type')
                            
                            ui.select([{'label': 'Credencial Default', 'value': 1}], label=t('api.auth_cred'))\
                                .classes('w-full text-sm mt-2').props('dense outlined').bind_value(design_state, 'auth_credential_id')\
                                .bind_visibility_from(design_state, 'auth_type', backward=lambda x: x != 'none')

                    # Columna 2: Petición, Resultados y Guardado
                    with ui.column().classes('gap-3'):
                        with ui.card().classes('w-full p-4 shadow-sm border border-slate-50'):
                            ui.label(t('api.request_config')).classes('text-sm font-bold mb-1')
                            with ui.tabs().classes('w-full dense') as p_tabs:
                                ui.tab('HEADERS', icon='list')
                                ui.tab('BODY (JSON)', icon='code')
                            
                            with ui.tab_panels(p_tabs, value='HEADERS').classes('w-full bg-transparent'):
                                with ui.tab_panel('HEADERS').classes('p-0 pt-2'):
                                    ui.label(t('api.headers')).classes('text-[10px] text-slate-400 mb-1')
                                    ui.textarea(placeholder='Ej: {"Content-Type": "application/json", "Authorization": "Bearer ..."}').classes('w-full font-mono text-xs').bind_value(design_state, 'headers_json').props('outlined rows=6')
                                with ui.tab_panel('BODY (JSON)').classes('p-0 pt-2'):
                                    ui.label(t('api.body')).classes('text-[10px] text-slate-400 mb-1')
                                    ui.textarea(placeholder='Ej: {"title": "post", "body": "contenido", "userId": 1}').classes('w-full font-mono text-xs').bind_value(design_state, 'body_json').props('outlined rows=6')

                        with ui.column().classes('w-full mt-1').bind_visibility_from(design_state, 'test_response'):
                            with ui.card().classes('w-full p-3 shadow-none border bg-green-50 border-green-100 text-green-700'):
                                ui.label('Respuesta exitosa').classes('text-[10px] font-bold uppercase mb-1')
                                result_json = ui.label().classes('text-[10px] font-mono break-all bg-white p-2 rounded border w-full h-40 overflow-auto')
                                result_json.bind_text_from(design_state, 'test_response', backward=lambda x: json.dumps(x, indent=2) if x else "{}")

                with ui.column().classes('w-full mt-2').bind_visibility_from(design_state, 'test_error'):
                    with ui.card().classes('w-full p-2 shadow-none border bg-red-50 border-red-100 text-red-700'):
                        ui.label().classes('text-[10px] break-all opacity-80 font-mono').bind_text_from(design_state, 'test_error')

        # Unified Footer
        with ui.column().classes('w-full max-w-4xl mx-auto mt-auto'):
            with ui.row().classes('w-full justify-between items-center pt-6 border-t border-slate-100 mb-8'):
                with ui.row().classes('items-center gap-4'):
                    ui.label(t('common.diagnostics')).classes('text-sm font-bold text-slate-700')
                    ui.button(t('common.test_connection'), icon='science', on_click=handle_test).props('unelevated color=emerald-600 dense shadow-sm')\
                        .bind_enabled_from(design_state, 'is_testing', backward=lambda x: not x)
                    
                    with ui.row().classes('items-center gap-2').bind_visibility_from(design_state, 'is_testing'):
                        ui.spinner(size='sm', color='emerald-600')
                        ui.label(t('common.loading')).classes('text-[10px] text-slate-400 italic')
                
                with ui.row().classes('items-center gap-2'):
                    ui.button(t('common.cancel'), on_click=go_to_library).props('flat color=slate text-sm')
                    ui.button(t('common.save'), icon='save', on_click=handle_save).props('unelevated color=primary shadow text-sm square')\
                        .bind_enabled_from(design_state, 'url', backward=lambda x: bool(x and design_state.name and not design_state.is_saving))

    def render_execution():
        with ui.column().classes('w-full max-w-5xl mx-auto gap-6'):
            # Header Ejecución
            with ui.row().classes('w-full items-center justify-between bg-slate-900 p-6 rounded-2xl text-white'):
                with ui.row().classes('items-center gap-4'):
                    ui.label('🔗').classes('text-3xl')
                    with ui.column():
                        ui.label(t('api.exec_adhoc', name=exec_state.config_entry.name)).classes('text-xl font-bold')
                        ui.label(f'{exec_state.config_entry.method} {exec_state.config_entry.url}').classes('text-xs opacity-60 font-mono')
                
                ui.button(t('api.close_console'), icon='close', on_click=go_to_library).props('flat color=white')

            with ui.row().classes('w-full gap-6'):
                # Logs
                with ui.card().classes('w-1/3 bg-black text-green-500 font-mono text-xs p-4 h-96 overflow-auto'):
                    ui.label(t('api.logs')).classes('text-blue-400 mb-2')
                    for log in exec_state.logs:
                        ui.label(f"> {log}")
                    if exec_state.is_running:
                        ui.spinner(size='sm').classes('mt-2')

                # Resultado
                with ui.column().classes('flex-grow gap-4'):
                    with ui.card().classes('w-full h-96 p-0 overflow-hidden border border-slate-200'):
                        with ui.tabs().classes('w-full bg-slate-50 border-b') as tabs:
                            t1 = ui.tab(t('api.json_tab'))
                            t2 = ui.tab(t('api.table_tab'))
                            with ui.tab_panel(t1):
                                if exec_state.execution_result:
                                    ui.json_editor({'content': {'json': exec_state.execution_result}}).classes('h-72')
                                elif exec_state.execution_error:
                                    ui.label(f"ERROR: {exec_state.execution_error}").classes('text-red-500 italic')
                                else:
                                    ui.label("Esperando ejecución...").classes('text-slate-400 italic')
                            
                            with ui.tab_panel(t2):
                                if isinstance(exec_state.execution_result, list):
                                    ui.table(columns=[{'name': k, 'label': k, 'field': k} for k in exec_state.execution_result[0].keys()], rows=exec_state.execution_result)
                                else:
                                    ui.label("El resultado no tiene formato de tabla compatible.").classes('text-slate-400 italic')

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button(t('api.re_execute'), icon='refresh', on_click=handle_execute).bind_enabled_from(exec_state, 'is_running', backward=lambda x: not x).props('outline color=cyan')

    # --- INITIALIZATION ---
    await load_saved_configs()

    if flow_config_id:
        # Cargar configuración existente desde contexto de flujo
        await edit_config(flow_config_id)
    elif api_id:
        await edit_config(api_id)
    elif initial_mode == 'execution' and api_id:
        await run_execution(api_id)
    elif initial_mode == 'design' and not api_id:
         await start_new_design()

    render_page()
    return render_page



@ui.page('/connections/api')
async def api_fetch_legacy_route(initial_mode: Optional[str] = None):
    # Pass initial_mode from query param to content function
    await api_fetch_page(initial_mode=initial_mode)
