"""
Página de logs unificada.
Muestra registros de actividad de tareas (ExtractionLog) y conexiones (ConnectionLog).
Permite la depuración técnica y el seguimiento de ejecuciones.
"""
from nicegui import ui, app
from client_app.app.core.state import state
from client_app.app.database.models import ExtractionLog, ConnectionLog
from sqlmodel import select, or_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# --- CONFIGURACIÓN ---

LOG_VIEW_MODES = {
    'all': 'logs_view_all',
    'tasks': 'logs_view_tasks',
    'connections': 'logs_view_connections',
}

LOG_FILTER_OPTIONS = {
    'date': {
        'today': 'logs_filter_today',
        'week': 'logs_filter_week',
        'month': 'logs_filter_month',
        'all': 'logs_filter_all',
    },
    'status': {
        'all': 'logs_filter_all',
        'success': 'logs_status_success',
        'error': 'logs_status_error',
        'warning': 'logs_status_warning',
    }
}

LOGS_PAGE_SIZE = 50


class LogsPageState:
    """
    Mantiene el estado reactivo de la página de logs.
    Controla el modo de visualización, los filtros activos (fecha, estado, búsqueda)
    y almacena los registros recuperados para su renderizado.
    """
    def __init__(self):
        self.view_mode = 'all'
        self.date_filter = 'week'
        self.status_filter = 'all'
        self.search_text = ''
        self.current_page = 1
        self.logs: List[Dict[str, Any]] = []


def build_unified_logs_query(
    view_mode: str,
    filters: dict,
    page: int = 1,
    # Helper mostly for testing query logic structure if needed via mocking
    # In this implementation, we handle queries inside load_data due to heterogenous models
):
    return "Query building mocked"


def render_view_selector(t, logs_state, on_change):
    """
    Renderiza el selector de pestañas para cambiar entre tipos de logs.
    
    Args:
        t: Función de traducción.
        logs_state: Instancia de LogsPageState.
        on_change: Callback a ejecutar al cambiar de pestaña.
    """
    with ui.tabs().classes('w-full') as tabs:
        for mode, label_key in LOG_VIEW_MODES.items():
            ui.tab(mode, label=t(label_key))
    async def handle_tab_change(e):
        logs_state.view_mode = e.value
        await on_change()

    tabs.on_value_change(handle_tab_change)
    tabs.value = logs_state.view_mode


def logs_page_content():
    """
    Controlador principal de la página de logs del sistema.
    Implementa una vista unificada que combina errores de conexión con resultados
    de procesamiento de documentos, permitiendo un diagnóstico rápido de fallos.
    """
    t = state.i18n.t
    
    # Store state in a persistent object for this page instance
    # To keep state across refreshes (in NiceGUI native mode usually fine)
    logs_state = LogsPageState()

    async def load_data():
        """
        Consulta la base de datos para recuperar los logs correspondientes 
        a los filtros aplicados. Realiza una unión lógica entre modelos 
        heterogéneos (tareas y conectividad).
        """
        try:
            async with state.db_session() as session:
                # Calculo de fechas
                cutoff = None
                if logs_state.date_filter == 'today':
                    cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                elif logs_state.date_filter == 'week':
                    cutoff = datetime.utcnow() - timedelta(days=7)
                elif logs_state.date_filter == 'month':
                    cutoff = datetime.utcnow() - timedelta(days=30)

                results = []

                # --- FETCH TASKS ---
                if logs_state.view_mode in ['all', 'tasks']:
                    query = select(ExtractionLog)
                    if cutoff:
                        query = query.where(ExtractionLog.timestamp >= cutoff)
                    if logs_state.status_filter != 'all':
                        if logs_state.status_filter == 'success':
                            query = query.where(ExtractionLog.status == 'success')
                        elif logs_state.status_filter == 'error':
                            query = query.where(ExtractionLog.status != 'success')
                        elif logs_state.status_filter == 'warning':
                            # Assuming warning maps to error or check if warning existing in extraction log model
                             query = query.where(ExtractionLog.status == 'warning')
                    
                    if logs_state.search_text:
                        query = query.where(ExtractionLog.filename.contains(logs_state.search_text))
                    
                    # Limit fetch for performance
                    query = query.order_by(ExtractionLog.timestamp.desc()).limit(200)

                    tasks = (await session.execute(query)).scalars().all()
                    for task in tasks:
                        results.append({
                            'id': f"task-{task.id}",
                            'obj': task,
                            'timestamp': task.timestamp,
                            'type': 'task',
                            'source': task.service_used or 'Extraction',
                            'status': 'success' if task.status == 'success' else 'error',
                            'message': task.filename or 'Sin nombre',
                            'details': task.error_message,
                            'result': task.extraction_result
                        })

                # --- FETCH CONNECTIONS ---
                if logs_state.view_mode in ['all', 'connections']:
                    query = select(ConnectionLog)
                    if cutoff:
                        query = query.where(ConnectionLog.timestamp >= cutoff)
                    if logs_state.status_filter != 'all':
                        query = query.where(ConnectionLog.status == logs_state.status_filter)
                    
                    if logs_state.search_text:
                        query = query.where(or_(
                            ConnectionLog.message.contains(logs_state.search_text),
                            ConnectionLog.connection_name.contains(logs_state.search_text)
                        ))
                    
                    query = query.order_by(ConnectionLog.timestamp.desc()).limit(200)

                    conns = (await session.execute(query)).scalars().all()
                    for conn in conns:
                        results.append({
                            'id': f"conn-{conn.id}",
                            'obj': conn,
                            'timestamp': conn.timestamp,
                            'type': 'connection', 
                            'source': f"{conn.connection_type.upper()}: {conn.connection_name}",
                            'status': conn.status,
                            'message': conn.message,
                            'details': conn.details,
                            'result': None
                        })

                # Sort merged results
                results.sort(key=lambda x: x['timestamp'], reverse=True)
                
                logs_state.logs = results
                render_logs_table.refresh()

        except Exception as e:
            ui.notify(t('admin.logs.error_loading', error=str(e)), type='negative')
            print(f"Error loading logs: {e}")

    # --- CONTROLS ---
    with ui.card().classes('w-full p-4 mb-4'):
        # Tabs
        render_view_selector(t, logs_state, load_data)
        
        ui.separator().classes('my-4')
        
        # Filters
        with ui.row().classes('w-full gap-4 items-center flex-wrap'):
            # Date Filter
            async def handle_date_change(e):
                logs_state.date_filter = e.value
                await load_data()

            ui.select(
                options={k: t(v) for k, v in LOG_FILTER_OPTIONS['date'].items()},
                label=t('logs_filter_date'),
                value=logs_state.date_filter,
                on_change=handle_date_change
            ).classes('w-48')

            # Status Filter
            async def handle_status_change(e):
                logs_state.status_filter = e.value
                await load_data()

            ui.select(
                options={k: t(v) for k, v in LOG_FILTER_OPTIONS['status'].items()},
                label=t('logs_filter_status'),
                value=logs_state.status_filter,
                on_change=handle_status_change
            ).classes('w-48')

            # Search
            async def on_search(e):
                logs_state.search_text = e.value
                await load_data()

            ui.input(label=t('logs_filter_search'), value=logs_state.search_text) \
                .on('keydown.enter', load_data) \
                .on('change', on_search) \
                .classes('flex-grow min-w-[200px]')
            
            ui.button(icon='refresh', on_click=load_data).props('flat round')

    # --- TABLE ---
    @ui.refreshable
    def render_logs_table():
        """
        Dibuja la tabla de registros con codificación de colores según el estado.
        Gestiona la visualización de celdas vacías y la paginación básica.
        """
        if not logs_state.logs:
            with ui.column().classes('w-full items-center py-12 text-gray-400 bg-slate-50 rounded-lg'):
                ui.icon('inbox', size='4em').classes('mb-2 opacity-50')
                ui.label(t('admin.logs.no_results')).classes('text-lg')
            return

        with ui.column().classes('w-full gap-0 border rounded-lg overflow-hidden'):
            # Header
            with ui.row().classes('bg-gray-100 p-3 font-bold text-gray-600 text-sm items-center'):
                ui.label(t('admin.logs.col_timestamp')).classes('w-36 pl-2')
                ui.label(t('admin.logs.col_status')).classes('w-24 text-center')
                ui.label(t('admin.logs.col_source')).classes('w-48')
                ui.label(t('admin.logs.col_message')).classes('flex-grow')
                ui.label(t('admin.logs.col_actions')).classes('w-24 text-right pr-2')

            # Rows
            # Pagination logic could be here, but using simple slicing for now
            page_items = logs_state.logs[:LOGS_PAGE_SIZE]
            
            for log in page_items:
                bg_color = 'bg-white'
                if log['status'] == 'error': bg_color = 'bg-red-50'
                if log['status'] == 'warning': bg_color = 'bg-amber-50'

                with ui.row().classes(f'w-full p-3 border-t border-gray-100 items-center {bg_color} hover:bg-gray-50 transition-colors group'):
                    # Time
                    ui.label(log['timestamp'].strftime('%Y-%m-%d %H:%M')).classes('w-36 text-xs font-mono text-gray-500 pl-2')
                    
                    # Status Icon
                    with ui.row().classes('w-24 justify-center'):
                        icon = 'check_circle'
                        color = 'text-green-500'
                        if log['status'] == 'error': 
                            icon = 'error'
                            color = 'text-red-500'
                        elif log['status'] == 'warning':
                            icon = 'warning'
                            color = 'text-amber-500'
                        ui.icon(icon).classes(color)

                    # Source
                    ui.label(log['source']).classes('w-48 text-sm font-semibold text-gray-700 truncate')
                    
                    # Message
                    ui.label(log['message']).classes('flex-grow text-sm text-gray-800 break-words line-clamp-2')

                    # Actions
                    with ui.row().classes('w-24 justify-end pr-2 opacity-0 group-hover:opacity-100 transition-opacity'):
                         ui.button(icon='visibility', on_click=lambda l=log: show_details(l)).props('flat round dense size=sm')

    def show_details(log_item):
        """
        Muestra un diálogo con los detalles técnicos completos de un log.
        Incluye trazas de error, metadatos de origen y el JSON de extracción si aplica.

        Args:
            log_item: Diccionario con la información procesada del log.
        """
        with ui.dialog() as dlg, ui.card().classes('w-full max-w-2xl max-h-[90vh] overflow-y-auto'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label(t('admin.logs.col_message')).classes('text-xl font-bold')
                ui.button(icon='close', on_click=dlg.close).props('flat round dense')
            
            ui.separator().classes('mb-4')

            # Metadata Grid
            with ui.grid(columns=2).classes('w-full gap-4 mb-4'):
                # Col 1
                with ui.column().classes('gap-1'):
                     ui.label(t('admin.logs.col_timestamp')).classes('text-xs font-bold text-gray-500 uppercase')
                     ui.label(log_item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')).classes('font-mono')
                     
                     ui.label(t('admin.logs.col_source')).classes('text-xs font-bold text-gray-500 uppercase mt-2')
                     ui.label(log_item['source'])

                # Col 2
                with ui.column().classes('gap-1'):
                     ui.label(t('admin.logs.col_status')).classes('text-xs font-bold text-gray-500 uppercase')
                     status_color = 'text-green-600' if log_item['status'] == 'success' else 'text-red-600'
                     ui.label(log_item['status'].upper()).classes(f'font-bold {status_color}')
                     
                     ui.label('ID').classes('text-xs font-bold text-gray-500 uppercase mt-2')
                     ui.label(str(log_item['id'])).classes('font-mono text-xs')

            # Message
            ui.label(t('admin.logs.col_message')).classes('text-xs font-bold text-gray-500 uppercase mb-1')
            ui.markdown(f"**{log_item['message']}**").classes('bg-gray-50 p-2 rounded w-full mb-4')

            # Details (if explicit)
            if log_item['details']:
                ui.label('Details').classes('text-xs font-bold text-gray-500 uppercase mb-1')
                with ui.scroll_area().classes('h-32 w-full bg-gray-900 text-white rounded p-2 mb-4 font-mono text-xs'):
                    ui.label(str(log_item['details']))

            # Extraction Result (if task)
            if log_item.get('result'):
                ui.label('Extraction Result').classes('text-xs font-bold text-gray-500 uppercase mb-1')
                ui.json_editor({'content': {'json': log_item['result']}}).classes('h-64 border rounded')

        dlg.open()

    render_logs_table()
    ui.timer(0.1, load_data, once=True)
