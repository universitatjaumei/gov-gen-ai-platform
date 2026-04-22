import asyncio
from typing import Optional, List, Dict, Any
from nicegui import ui
from sqlmodel import select

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.sql_connector_service import sql_connector_service
from client_app.app.ui.components.page_header import page_header
from client_app.app.ui.components.database_connection_manager import DatabaseConnectionManager
from client_app.app.ui.components.form_factory import AtomColorScheme
from client_app.app.database.models import DatabaseCredentialConfig, FlowRegistry
from automatia_shared.enums import StepType

# --- STATE ---
class SQLInsertPageState:
    def __init__(self):
        self.current_mode: str = 'library' # library, design, execution
        self.is_loading: bool = False

class DesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.credential_id: Optional[int] = None
        self.table_name: Optional[str] = None
        self.column_mapping: Dict[str, str] = {} # {col_name: value_expression}
        
        # UI State
        self.available_tables: List[str] = []
        self.table_schema: Dict[str, str] = {} # {col: type}
        self.is_fetching_tables: bool = False
        self.is_saving: bool = False
        self.test_result: str = ""
        self.test_status: str = "" # success, error

# --- PAGE IMPLEMENTATION ---

async def sql_insert_page(mode: str = 'library', initial_mode: Optional[str] = None):
    page_state = SQLInsertPageState()
    design_state = DesignState()
    t = state.i18n.t
    
    # --- LOGIC ---

    async def load_design_data():
        pass # Por ahora no cargamos configs guardadas (MVP solo diseño visual)

    async def fetch_tables(e=None):
        if not design_state.credential_id:
            return
        
        design_state.is_fetching_tables = True
        render_table_selector.refresh()
        try:
            design_state.available_tables = await sql_connector_service.get_tables(design_state.credential_id)
            if not design_state.available_tables:
                ui.notify("No se encontraron tablas en la base de datos.", type='warning')
        except Exception as e:
            ui.notify(f"Error al obtener tablas: {e}", type='negative')
        finally:
            design_state.is_fetching_tables = False
            render_table_selector.refresh()

    async def on_table_selected(e):
        table = e.value
        design_state.table_name = table
        if not table:
            design_state.table_schema = {}
            render_column_mapper.refresh()
            return

        try:
            design_state.table_schema = await sql_connector_service.get_table_schema(design_state.credential_id, table)
            # Inicializar mapeo vacío para nuevas columnas
            for col in design_state.table_schema:
                if col not in design_state.column_mapping:
                    design_state.column_mapping[col] = "" # Empty by default
            render_column_mapper.refresh()
        except Exception as ex:
            ui.notify(f"Error al leer esquema: {ex}", type='negative')

    async def handle_test():
        if not design_state.credential_id or not design_state.table_name:
            ui.notify("Selecciona conexión y tabla", type='warning')
            return
        
        design_state.test_status = "running"
        design_state.test_result = "Simulando inserción..."
        render_test_result.refresh()
        
        await asyncio.sleep(1) # Simulación
        
        # Aquí iría la lógica real de prueba (dry-run o insert rollback)
        design_state.test_status = "success"
        design_state.test_result = f"ÉXITO: Se generó la sentencia INSERT INTO {design_state.table_name}..."
        render_test_result.refresh()

    async def handle_save():
        if not design_state.name:
            ui.notify("Asigna un nombre a la salida", type='warning')
            return
        if not design_state.credential_id or not design_state.table_name:
            ui.notify("Configuración incompleta", type='warning')
            return
            
        ui.notify("Configuración guardada (Simulado)", type='positive')
        layout_manager.exit_focus_mode()

    def go_to_library():
        layout_manager.exit_focus_mode()
        ui.navigate.to('/outputs') # Asumiendo que existe o volvemos a home

    # --- RENDERERS ---

    @ui.refreshable
    def render_table_selector():
        if design_state.is_fetching_tables:
            ui.spinner(size='sm')
            return
            
        if not design_state.credential_id:
            ui.label(t('sql.select_connection_first')).classes('text-xs text-slate-400 italic')
            return

        if not design_state.available_tables:
            ui.button(t('sql.load_tables'), icon='refresh', on_click=fetch_tables).props('flat dense color=primary')
            return

        ui.select(design_state.available_tables, label=t('sql.select_table'), with_input=True, on_change=on_table_selected)\
            .classes('w-full').props('outlined dense options-dense').bind_value(design_state, 'table_name')

    @ui.refreshable
    def render_column_mapper():
        if not design_state.table_name:
            with ui.column().classes('w-full items-center justify-center p-8 bg-slate-50 border border-slate-100 rounded-lg'):
                ui.icon('table_chart', size='3rem', color='slate-300')
                ui.label(t('sql.select_table_to_map')).classes('text-slate-400 text-sm')
            return

        with ui.column().classes('w-full gap-2'):
            ui.label(t('sql.column_mapping', table=design_state.table_name)).classes('text-sm font-bold mb-2')
            
            # Header Grid
            with ui.grid(columns=12).classes('w-full gap-4 items-center px-2 py-1 bg-slate-100 rounded text-xs font-bold text-slate-600'):
                ui.label(t('sql.col_header')).classes('col-span-4')
                ui.label(t('sql.type_header')).classes('col-span-2')
                ui.label(t('sql.value_header')).classes('col-span-6')

            # Rows
            for col, dtype in design_state.table_schema.items():
                with ui.grid(columns=12).classes('w-full gap-4 items-center border-b border-slate-50 py-2'):
                    # Nombre Columna
                    with ui.row().classes('col-span-4 items-center gap-1'):
                        ui.icon('key' if 'id' in col.lower() else 'minimize', size='xs', color='slate-400')
                        ui.label(col).classes('text-sm font-mono truncate').tooltip(col)
                    
                    # Tipo
                    ui.label(dtype).classes('col-span-2 text-xs text-slate-400 truncate')
                    
                    # Input Valor
                    ui.input(placeholder='Texto o {{variable}}', on_change=lambda e, c=col: design_state.column_mapping.update({c: e.value}))\
                        .classes('col-span-6 text-sm').props('dense outlined').bind_value(design_state.column_mapping, col)

    @ui.refreshable
    def render_test_result():
        if not design_state.test_status: return
        
        color = 'green' if design_state.test_status == 'success' else ('red' if design_state.test_status == 'error' else 'blue')
        bg = f'bg-{color}-50'
        border = f'border-{color}-200'
        text_c = f'text-{color}-700'
        
        with ui.card().classes(f'w-full p-3 {bg} {border} border shadow-none mt-2'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('check_circle' if design_state.test_status == 'success' else 'info', color=color)
                ui.label(design_state.test_result).classes(f'text-xs font-mono {text_c} break-all')

    def render_design():
        # Standard Layout: p-6, max-w-4xl, gap-4
        with ui.column().classes('w-full h-full p-6 gap-0 overflow-hidden'):
            
            # Scrollable Content
            with ui.column().classes('w-full flex-grow overflow-y-auto gap-4 mb-4'):
                with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
                    page_header(
                        t('sql.insert_title'),
                        t('sql.insert_desc'),
                        classes='w-full gap-0 mb-2'
                    )

                    # Main Grid: 2 Columns
                    with ui.grid(columns=2).classes('w-full gap-4'):
                        # Left Column: Configuration
                        with ui.column().classes('gap-4'):
                            with ui.card().classes('w-full p-5 shadow-sm border border-slate-100'):
                                ui.label(t('common.configuration')).classes('text-base font-bold text-slate-900 mb-2')
                                
                                # Name Output
                                ui.input(t('sql.insert_name'), placeholder='Ej: Insertar Clientes Nuevos')\
                                    .classes('w-full mb-2 text-sm font-bold').props('dense outlined').bind_value(design_state, 'name')

                                # Connection Selector
                                ui.select([{'label': 'Conexión Demo', 'value': 1}], label=t('sql.connection_label'), on_change=fetch_tables)\
                                    .classes('w-full').props('outlined dense').bind_value(design_state, 'credential_id')
                                
                                # Horizontal Connection Warning (Single line)
                                # TODO: Detect actual connections
                                has_connections = False # Simulado
                                if not has_connections:
                                    with ui.row().classes('w-full items-center justify-between p-2 bg-amber-50 rounded border border-amber-100 text-amber-700 mt-2'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('warning', size='14px')
                                            ui.label(t('common.no_connections')).classes('text-[11px] font-medium')
                                        ui.button(t('common.configure'), on_click=lambda: ui.navigate.to('/config?tab=Bases%20de%20Datos')).props('flat dense color=amber text-[11px] no-caps')

                                ui.separator().classes('my-4')
                                
                                ui.label(t('sql.table_dest')).classes('text-sm font-bold mb-2')
                                render_table_selector()

                        # Right Column: Mapping
                        with ui.column().classes('gap-4'):
                            with ui.card().classes('w-full p-4 shadow-sm border border-slate-50'):
                                render_column_mapper()

            # Footer
            with ui.column().classes('w-full max-w-4xl mx-auto mt-auto'):
                with ui.row().classes('w-full justify-between items-center pt-6 border-t border-slate-100 mb-8'):
                    # Left: Test Button
                    with ui.row().classes('items-center gap-4'):
                         ui.button(t('sql.test_insert'), icon='play_arrow', on_click=handle_test)\
                            .props('unelevated color=slate dense shadow-sm')
                         render_test_result()
                    
                    # Right: Cancel/Save
                    with ui.row().classes('items-center gap-2'):
                        ui.button(t('common.cancel'), on_click=go_to_library).props('flat color=slate text-sm')
                        ui.button(t('common.save'), icon='save', on_click=handle_save)\
                            .props('unelevated color=primary shadow text-sm')

    # --- INITIALIZATION ---
    
    # Enter design mode to show drawer
    layout_manager.enter_design_mode(StepType.SQL_INSERT)
    
    # Render
    if mode == 'library' and not initial_mode:
        render_design() # Directamente al diseño por ahora
    else:
        render_design()



@ui.page('/outputs/sql')
async def sql_insert_legacy_route(initial_mode: Optional[str] = None):
    # Pass initial_mode from query param to content function
    await sql_insert_page(initial_mode=initial_mode)
