import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
from nicegui import ui
from sqlmodel import select

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.sql_connector_service import sql_connector_service
from client_app.app.database.models import DatabaseCredentialConfig
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.page_header import page_header
from client_app.app.ui.components.drawer_hub import DrawerHub
from client_app.app.core.state import state as app_state # Fix import alias to match usage

# --- MODELS & STATE ---

class SQLQueryPageState:
    def __init__(self):
        self.current_mode: str = 'library' # library, design, execution
        self.configs: List[DatabaseCredentialConfig] = []
        self.is_loading: bool = False

class DesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.db_type: str = "mysql"
        self.host: str = ""
        self.port: int = 3306
        self.database: str = ""
        self.username: str = ""
        self.password: str = ""
        self.ssl_enabled: bool = False
        self.test_success: bool = False
        self.test_message: str = ""
        self.is_testing: bool = False
        self.is_saving: bool = False

class ExecutionState:
    def __init__(self):
        self.config_entry: Optional[DatabaseCredentialConfig] = None
        self.query: str = "SELECT * FROM my_table LIMIT 10"
        self.execution_result: Optional[pd.DataFrame] = None
        self.execution_error: Optional[str] = None
        self.is_running: bool = False
        self.tables: List[str] = []
        self.query_name: str = ""

# --- PAGE IMPLEMENTATION ---

async def sql_query_page(config_id: Optional[int] = None, initial_mode: Optional[str] = None):
    page_state = SQLQueryPageState()
    design_state = DesignState()
    exec_state = ExecutionState()
    colors = AtomColorScheme.get_colors(StepType.SQL_QUERY)
    t = state.i18n.t

    # --- INITIAL LAYOUT SETUP ---
    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.SQL_QUERY, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif config_id:
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.SQL_QUERY, atom_id=config_id)
    elif initial_mode == 'design':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.SQL_QUERY)
    elif initial_mode == 'execution':
        page_state.current_mode = 'execution'
        # enter_execution_mode will be called later when config is loaded
    else:
        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()

    # --- LOGIC ---

    async def load_configs():
        page_state.is_loading = True
        render_page.refresh()
        async with state.db_session() as session:
            stmt = select(DatabaseCredentialConfig).order_by(DatabaseCredentialConfig.name)
            result = await session.execute(stmt)
            page_state.configs = result.scalars().all()
        page_state.is_loading = False
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

        layout_manager.exit_focus_mode()
        page_state.current_mode = 'library'
        render_page.refresh()

    async def start_new_design():
        design_state.__init__()
        layout_manager.enter_design_mode(StepType.SQL_QUERY)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def edit_config(config_id: int):
        async with state.db_session() as session:
            config = await session.get(DatabaseCredentialConfig, config_id)
            if config:
                design_state.config_id = config.id
                design_state.name = config.name
                design_state.db_type = config.db_type
                design_state.host = config.host
                design_state.port = config.port
                design_state.database = config.database
                design_state.username = config.username
                design_state.password = "" # No recuperamos contraseña por seguridad
                design_state.ssl_enabled = config.ssl_enabled
                
                layout_manager.enter_design_mode(StepType.SQL_QUERY, atom_id=config_id)
                page_state.current_mode = 'design'
                render_page.refresh()

    async def run_execution(config_id: Optional[int] = None):
        if config_id is None:
            exec_state.config_entry = None
            exec_state.tables = []
            exec_state.execution_result = None
            exec_state.execution_error = None
            page_state.current_mode = 'execution'
            render_page.refresh()
            return

        async with state.db_session() as session:
            config = await session.get(DatabaseCredentialConfig, config_id)
            if config:
                exec_state.config_entry = config
                exec_state.execution_result = None
                exec_state.execution_error = None
                
                # Cargar tablas para asistencia
                try:
                    exec_state.tables = await sql_connector_service.get_tables(config_id)
                except:
                    exec_state.tables = []
                
                layout_manager.enter_execution_mode(atom_id=config_id)
                page_state.current_mode = 'execution'
                
                # Sync with global state for DrawerHub
                mock_step = type('MockStep', (), {
                    'name': 'Consulta SQL',
                    'type': StepType.SQL_QUERY,
                    'config': {'connection_id': config_id, 'output_variables': exec_state.mock_step_config.get('output_variables', [])}
                })
                app_state.editing_step = mock_step
                
                render_page.refresh()

    async def handle_test():
        design_state.is_testing = True
        design_state.test_message = "Probando conexión..."
        render_page.refresh()
        
        try:
            # Para probar, guardamos temporalmente cifrado
            from client_app.app.modules.security.encryption_service import EncryptionService
            encryption = EncryptionService()
            enc_pass = encryption.encrypt(design_state.password)
            
            async with state.db_session() as session:
                # Si es nuevo creamos uno efímero
                if design_state.config_id:
                    cred = await session.get(DatabaseCredentialConfig, design_state.config_id)
                else:
                    cred = DatabaseCredentialConfig(name="TEMP_TEST")
                
                cred.db_type = design_state.db_type
                cred.host = design_state.host
                cred.port = design_state.port
                cred.database = design_state.database
                cred.username = design_state.username
                if design_state.password: # Solo si se escribió una nueva
                    cred.encrypted_password = enc_pass
                cred.ssl_enabled = design_state.ssl_enabled
                
                session.add(cred)
                await session.commit()
                await session.refresh(cred)
                temp_id = cred.id
            
            success, msg = await sql_connector_service.test_connection(temp_id)
            design_state.test_success = success
            design_state.test_message = msg
            
            # Limpiar si era temporal total
            if not design_state.config_id:
                async with state.db_session() as session:
                    cred = await session.get(DatabaseCredentialConfig, temp_id)
                    await session.delete(cred)
                    await session.commit()
                    
        except Exception as e:
            design_state.test_success = False
            design_state.test_message = f"Error: {e}"
        finally:
            design_state.is_testing = False
            render_page.refresh()

    async def handle_save_query():
        # En esta versión, "guardar" en la página standalone 
        # podría guardar la última consulta en la config de la conexión 
        # o simplemente notificar. Como no hay modelo de "SavedQuery",
        # guardamos la query en un metadato de la credencial por comodidad.
        if not exec_state.config_entry: return
        
        design_state.is_saving = True
        render_page.refresh()
        try:
            async with state.db_session() as session:
                cred = await session.get(DatabaseCredentialConfig, exec_state.config_entry.id)
                if cred:
                    # Guardamos la última query como extra_params o similar
                    import json
                    params = json.loads(cred.extra_params or "{}")
                    params['last_query'] = exec_state.query
                    cred.extra_params = json.dumps(params)
                    await session.commit()
            ui.notify(t('sql.saved_success', "Consulta guardada en la conexión"), type='positive')
        except Exception as e:
            ui.notify(f"Error al guardar: {e}", type='negative')
        finally:
            design_state.is_saving = False
            render_page.refresh()

    async def handle_execute_query():
        exec_state.is_running = True
        exec_state.execution_error = None
        render_page.refresh()
        
        try:
            df = await sql_connector_service.execute_query(
                exec_state.config_entry.id,
                exec_state.query
            )
            exec_state.execution_result = df
        except Exception as e:
            exec_state.execution_error = str(e)
            ui.notify(f"Error SQL: {e}", type='negative')
        finally:
            exec_state.is_running = False
            render_page.refresh()

    async def handle_delete(config_id: int):
        async with state.db_session() as session:
            config = await session.get(DatabaseCredentialConfig, config_id)
            if config:
                await session.delete(config)
                await session.commit()
                ui.notify(t('common.deleted_success', name=config.name), type='positive')
                await load_configs()

    # --- RENDERERS ---

    @ui.refreshable
    def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library': render_library()
            elif page_state.current_mode in ['design', 'execution']: render_designer()

    def render_library():
        if page_state.is_loading:
            with ui.column().classes('w-full items-center py-20'):
                ui.spinner(size='lg')
            return
            
        # Mapping configs to resource dicts
        resources = []
        for c in page_state.configs:
            resources.append({
                'id': c.id,
                'name': c.name,
                'description': f"{c.db_type}://{c.host}:{c.port}/{c.database}",
                'status': 'published',
                'source_module': 'sql',
                'doc_path': None,
                'created_at': c.created_at,
                'is_favorite': False,
            })

        layout = StandardPageLayout(
            title=t('sql.title'),
            source_module='sql',
            resources=resources,
            on_create=lambda: run_execution(None), # Enter designer without preset config
            on_edit=lambda r: run_execution(r['id']),
            on_delete=lambda r: confirm_delete(r['id']),
            on_execute=lambda r: run_execution(r['id']),
            help_description=t('sql.help'),
            input_contract=['host', 'port', 'user', 'password', 'database', 'ssl', 'query'],
            output_contract=['result_dataframe', 'affected_rows', 'error_message']
        )
        layout.render()

    def confirm_delete(config_id):
        with ui.dialog() as d, ui.card():
            ui.label(t('sql.delete_confirm', '¿Eliminar esta conexión?')).classes('font-bold')
            with ui.row().classes('justify-end mt-4'):
                ui.button(t('common.cancel'), on_click=d.close).props('flat')
                ui.button(t('common.delete'), on_click=lambda: (d.close(), handle_delete(config_id))).props('unelevated color=red')
        d.open()

    def render_designer():
        """Unified SQL Designer and Tester matching Standard Layout."""
        # Ensure layout states are correct for SQL Query Designer
        layout_manager.menu_mini_mode = True
        layout_manager.drawer_visible = True
        layout_manager.designing_atom_type = StepType.SQL_QUERY

        # Update mock step config for DrawerHub if needed
        if not hasattr(exec_state, 'mock_step_config'):
             exec_state.mock_step_config = {'output_variables': [], 'last_test_output': []}

        # Keep app_state synced for DrawerHub interactions
        if not app_state.editing_step or app_state.editing_step.type != StepType.SQL_QUERY:
            mock_step = type('MockStep', (), {
                'name': 'Consulta SQL',
                'type': StepType.SQL_QUERY,
                'config': {
                    'connection_id': exec_state.config_entry.id if exec_state.config_entry else None, 
                    'output_variables': exec_state.mock_step_config.get('output_variables', []),
                    'last_test_output': []
                }
            })
            app_state.editing_step = mock_step

        if app_state.editing_step and hasattr(app_state.editing_step, 'config'):
            app_state.editing_step.config['output_variables'] = exec_state.mock_step_config['output_variables']
            if exec_state.execution_result is not None:
                app_state.editing_step.config['last_test_output'] = exec_state.execution_result.head(10).to_dict(orient='records')

        # Main Content Area
        with ui.column().classes('w-full h-full p-0 gap-0 overflow-hidden'):
            # 1. Scrollable Content (Header + Config Grid)
            with ui.column().classes('w-full flex-grow overflow-y-auto gap-4 mb-4'):
                with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
                    # Header (Blue H2)
                    page_header(
                        t('sql.designer_title'),
                        t('sql.designer_subtitle')
                    )

                    # Row 1: Configurations (2 Columns - Balanced)
                    with ui.grid(columns=2).classes('w-full gap-4'):
                        # Col 1: Connection
                        with ui.column().classes('gap-4'):
                            with ui.card().classes('w-full p-5 shadow-sm border border-slate-100'):
                                ui.label(t('common.configuration')).classes('text-base font-bold text-slate-900 mb-2')
                                
                                # Query Name
                                ui.input(label=t('sql.query_name'), placeholder='Ej: Listado de Clientes')\
                                    .classes('w-full mb-2').props('outlined dense').bind_value(exec_state, 'query_name')

                                configs_dict = {c.id: f"{c.name} ({c.db_type.upper()})" for c in page_state.configs}
                                current_id = exec_state.config_entry.id if exec_state.config_entry else None
                                
                                ui.select(configs_dict, value=current_id, label=t('sql.connection_label'))\
                                    .classes('w-full').props('outlined dense')\
                                    .on_value_change(lambda e: run_execution(e.value))

                                if not page_state.configs:
                                    with ui.row().classes('w-full items-center justify-between p-2 bg-amber-50 rounded border border-amber-100 text-amber-700 mt-2'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('warning', size='14px')
                                            ui.label(t('common.no_connections')).classes('text-[11px] font-medium')
                                        ui.button(t('common.configure'), on_click=lambda: ui.navigate.to('/config?tab=Bases%20de%20Datos')).props('flat dense color=amber text-[11px] no-caps')

                        # Col 2: Paste Query Tool
                        with ui.card().classes('w-full p-5 shadow-sm border border-slate-100 h-full'):
                             ui.label(t('sql.paste_query')).classes('text-base font-bold text-slate-900 mb-2')
                             ui.textarea(placeholder=t('sql.query_placeholder')).classes('w-full font-mono text-sm h-full flex-grow').bind_value(exec_state, 'query').props('outlined flat')

                    # Row 2: Full Width Editor (Expander - initially contracted)
                    with ui.expansion(t('sql.query_editor'), icon='terminal', value=False).classes('w-full border border-slate-200 rounded shadow-sm bg-white'):
                        with ui.column().classes('p-4 w-full gap-4'):
                            if not exec_state.config_entry:
                                with ui.column().classes('w-full items-center justify-center p-10 bg-slate-50 border-dashed border-2 rounded'):
                                    ui.icon('lock', size='lg', color='slate-200')
                                    ui.label(t('sql.select_connection_first')).classes('text-slate-400 italic')
                            else:
                                ui.textarea(placeholder=t('sql.query_placeholder')).classes('w-full font-mono text-sm h-64').bind_value(exec_state, 'query').props('outlined flat')
                                
                                with ui.row().classes('w-full justify-between items-center'):
                                    ui.label(t('sql.read_only_warning')).classes('text-xs text-gray-400 italic')
                                    ui.button(t('sql.test_query'), icon='play_arrow', on_click=handle_execute_query)\
                                        .props('unelevated color=emerald-600').bind_enabled_from(exec_state, 'is_running', backward=lambda x: not x)

                                # Results Area
                                if exec_state.execution_result is not None:
                                    ui.separator()
                                    ui.label(t('sql.results_preview')).classes('text-xs font-bold text-slate-500 uppercase')
                                    if exec_state.execution_result.empty:
                                        ui.label(t('sql.no_rows_returned')).classes('italic text-gray-400')
                                    else:
                                        df = exec_state.execution_result
                                        columns = [{'name': c, 'label': c, 'field': c} for c in df.columns]
                                        rows = df.head(10).to_dict('records')
                                        ui.table(columns=columns, rows=rows).classes('w-full max-h-60')

                                elif exec_state.execution_error:
                                    ui.separator()
                                    ui.label(f"Error: {exec_state.execution_error}").classes('text-red-500 font-mono text-xs')

                # Row 3: Consolidated Footer (Diagnostics + Actions) - Aligned Horizontally
                with ui.column().classes('w-full max-w-4xl mx-auto mt-auto'):
                    with ui.row().classes('w-full justify-between items-center pt-6 border-t border-slate-100 mb-8'):
                        # Left: Diagnostics
                        with ui.row().classes('items-center gap-4'):
                            ui.label(t('common.diagnostics')).classes('text-sm font-bold text-slate-700')
                            ui.button(t('common.test_connection'), icon='link', on_click=lambda: ui.notify(t('common.success'), type='positive') if exec_state.config_entry else ui.notify(t('sql.select_connection_first'), type='warning'))\
                                .props('unelevated color=emerald-600 dense').classes('shadow-sm')
                        
                        # Right: Actions (Horizontal row)
                        with ui.row().classes('items-center gap-3'):
                            ui.button(t('common.cancel'), on_click=go_to_library).props('flat color=slate')
                            ui.button(t('common.save'), icon='save', on_click=handle_save_query).props('unelevated color=primary shadow')

    # --- INITIALIZATION ---
    await load_configs()

    if flow_config_id:
        await edit_config(flow_config_id)
    elif config_id:
        await edit_config(config_id)
    elif initial_mode == 'execution' and config_id:
        await run_execution(config_id)

    render_page()

    # El retorno es opcional si solo se va a llamar desde el router de FastAPI, 
    # pero mantenemos compatibilidad por si acaso
    return render_page



@ui.page('/connections/sql')
async def sql_query_legacy_route(initial_mode: Optional[str] = None):
    # Pass initial_mode from query param to content function
    await sql_query_page(initial_mode=initial_mode)
