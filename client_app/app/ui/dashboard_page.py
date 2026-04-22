from nicegui import ui, app
from client_app.app.core.state import state
from client_app.app.ui.components.unified_resource_card import unified_resource_card
from client_app.app.ui.components.page_header import page_header
from client_app.app.services.script_library_service import script_library_service
from client_app.app.services.layout_manager import layout_manager
from client_app.app.database.models import (
    ExtractionLog, FavoriteFlow, FlowRegistry, ETLJobHistory,
    LocalAutomation, TaskLog, RunManifestLog, ScriptLibrary,
    TriggerConfig, TriggerSubscription
)
from automatia_shared.core.audit_models import EnterpriseAuditLog
from sqlmodel import select, func
from datetime import datetime
import asyncio
import json

# --- DATA: TASK CATALOG ---
# Note: Strings are keys for i18n or updated dynamically inside component
# --- DATA: AUTOMATIONS CATALOG ---
AUTOMATIONS_CATALOG = {
    'extraction': {
        'name_key': 'task_extract_name',
        'desc_key': 'task_extract_desc',
        'icon': 'description',
        'color': 'blue',
        'route': '/documents',
        'templates': []
    },
    'rpa': {
        'name_key': 'task_rpa_name',
        'desc_key': 'task_rpa_desc',
        'icon': 'public',
        'color': 'orange',
        'route': '/rpa',
        'templates': []
    },
    'etl': {
        'name_key': 'task_etl_name',
        'desc_key': 'task_etl_desc',
        'icon': 'transform',
        'color': 'pink',
        'route': '/etl',
        'templates': []
    },
    'graphics': {
        'name_key': 'task_graphics_name',
        'desc_key': 'task_graphics_desc',
        'icon': 'bar_chart',
        'color': 'indigo',
        'route': '/graphics',
        'templates': []
    },
    'custom_script': {
        'name_key': 'task_custom_name',
        'desc_key': 'task_custom_desc',
        'icon': 'auto_fix_high',
        'color': 'emerald',
        'route': '/custom-scripts',
        'templates': []
    },
    'anonymizer': {
        'name_key': 'task_anon_name',
        'desc_key': 'task_anon_desc',
        'icon': 'lock',
        'color': 'purple',
        'route': '/anonymizer',
        'templates': []
    }
}

# --- DATA: CONNECTIONS CATALOG (Nueva Taxonomía) ---
CONNECTIONS_CATALOG = {
    # Disparadores
    'folder_watcher': {
        'name_key': 'triggers.folder_title',
        'icon': 'folder',
        'color': 'orange',
        'route': '/triggers/folder-watcher'
    },
    'email_watcher': {
        'name_key': 'triggers.email_title',
        'icon': 'email',
        'color': 'blue',
        'route': '/triggers/email-watcher'
    },
    'scheduler': {
        'name_key': 'triggers.scheduler_title',
        'icon': 'schedule',
        'color': 'amber',
        'route': '/triggers/scheduler'
    },
    # Entradas
    'api': {
        'name': 'API Fetch', # Internal name
        'icon': 'api',
        'color': 'cyan',
        'route': '/inputs/api'
    },
    'database': {
        'name_key': 'common.sql_query', # Need to check if added
        'name': 'Consulta SQL',
        'icon': 'storage',
        'color': 'blue-grey',
        'route': '/inputs/sql'
    },
    'folder_scan': {
        'name': 'Escaneo Carpeta',
        'icon': 'folder_open',
        'color': 'orange',
        'route': '/inputs/folder-scan'
    },
    'email_scan': {
        'name': 'Recolector Email',
        'icon': 'attach_email',
        'color': 'indigo',
        'route': '/inputs/email-scan'
    },
    # Procesadores (selección rápida)
    'graphics': {
        'name_key': 'dash.graph_name',
        'icon': 'bar_chart',
        'color': 'pink',
        'route': '/graphics'
    },
    # Salidas
    'smtp': {
        'name': 'Email (SMTP)',
        'icon': 'send',
        'color': 'teal',
        'route': '/outputs/smtp'
    },
    'archive': {
        'name': 'Archivar Resultado',
        'icon': 'save_alt',
        'color': 'teal',
        'route': '/outputs/archive'
    }
}


# --- FILTERS CONFIGURATION (Prompt 1.2) ---
DASHBOARD_FILTER_OPTIONS = {
    'date': {
        'today': 'dash_filter_today',
        'week': 'dash_filter_week',
        'month': 'dash_filter_month',
        'all': 'dash_filter_all',
    },
    'type': {
        'all': 'dash_filter_all',
        'extraction': 'dash_filter_extraction',
        'etl': 'dash_filter_etl',
        'custom_script': 'dash_filter_custom_script',
        'anonymization': 'dash_filter_anonymization',
    },
    'status': {
        'all': 'dash_filter_all',
        'success': 'dash_filter_success',
        'error': 'dash_filter_error',
    }
}

class DashboardFilterState:
    """
    Gestiona el estado reactivo de los filtros del Dashboard en la sesión.
    Permite segmentar la actividad por rango temporal, tipo de automatización
    y estado de ejecución (éxito/error).
    """
    def __init__(self):
        self.date_filter = 'week'
        self.type_filter = 'all'
        self.status_filter = 'all'

def build_activity_query(date_filter: str, type_filter: str, status_filter: str):
    """
    Construye una consulta dinâmica para recuperar el feed de actividad reciente.
    Aplica filtros de fecha, categoría y estado sobre el registro de extracciones.

    Args:
        date_filter: Período solicitado (today, week, month, all).
        type_filter: Filtrado por servicio (extraction, etl, etc.).
        status_filter: Filtrado por resultado (success, error, all).

    Returns:
        Objeto select de SQLModel con los criterios aplicados.
    """
    from client_app.app.database.models import ExtractionLog
    from sqlmodel import select
    from datetime import datetime, timedelta

    # Base query para ExtractionLog
    query = select(ExtractionLog)

    # Filtro de fecha
    if date_filter == 'today':
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.where(ExtractionLog.timestamp >= cutoff)
    elif date_filter == 'week':
        cutoff = datetime.utcnow() - timedelta(days=7)
        query = query.where(ExtractionLog.timestamp >= cutoff)
    elif date_filter == 'month':
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = query.where(ExtractionLog.timestamp >= cutoff)
    # 'all' no aplica filtro de fecha

    # Filtro de estado
    if status_filter != 'all':
        if status_filter == 'success':
             query = query.where(ExtractionLog.status == 'success')
        elif status_filter == 'error':
             query = query.where(ExtractionLog.status.in_(['failed', 'error']))

    # Filtro de tipo
    if type_filter != 'all':
        if type_filter == 'extraction':
             query = query.where(ExtractionLog.service_used == 'extraction')
        elif type_filter == 'etl':
             query = query.where(ExtractionLog.service_used == 'etl')
        elif type_filter == 'custom_script':
             query = query.where(ExtractionLog.service_used == 'custom_script')

    # Ordenar y limitar
    query = query.order_by(ExtractionLog.timestamp.desc()).limit(20)

    return query

def render_activity_filters(t, filter_state, on_change_callback):
    """
    Dibuja los controles de filtrado compactos para la sección de actividad reciente.
    """
    # Filtro de fecha
    date_options = {k: t(v) for k, v in DASHBOARD_FILTER_OPTIONS['date'].items()}
    ui.select(
        options=date_options,
        value=filter_state.date_filter,
        on_change=lambda e: (setattr(filter_state, 'date_filter', e.value), on_change_callback())
    ).props('outlined dense borderless').classes('w-32 text-xs')

    # Filtro de tipo
    type_options = {k: t(v) for k, v in DASHBOARD_FILTER_OPTIONS['type'].items()}
    ui.select(
        options=type_options,
        value=filter_state.type_filter,
        on_change=lambda e: (setattr(filter_state, 'type_filter', e.value), on_change_callback())
    ).props('outlined dense borderless').classes('w-28 text-xs')

    # Filtro de estado
    status_options = {k: t(v) for k, v in DASHBOARD_FILTER_OPTIONS['status'].items()}
    ui.select(
        options=status_options,
        value=filter_state.status_filter,
        on_change=lambda e: (setattr(filter_state, 'status_filter', e.value), on_change_callback())
    ).props('outlined dense borderless').classes('w-24 text-xs')

    # Helper to reset filters
    def reset_filters():
        filter_state.date_filter = 'all'
        filter_state.type_filter = 'all'
        filter_state.status_filter = 'all'
        on_change_callback()

    ui.button(icon='filter_alt_off', on_click=reset_filters).props('flat dense round size=sm color=grey').tooltip(t('dash.filter_reset'))



def dashboard_page_content():
    """
    Controlador principal del Dashboard (Centro de Mando).
    Orquestra la visualización de KPIs globales, el catálogo de automatismos,
    los flujos favoritos del usuario y el estado de monitorización de red.
    """
    t = state.i18n.t
    
    # Import delete for favorites management
    from sqlmodel import delete


    class DashboardState:
        def __init__(self):
            # Sort catalog based on keys order
            self.auto_keys = ['extraction', 'rpa', 'etl', 'graphics', 'custom_script', 'anonymizer']
            self.conn_keys = ['folder_watcher', 'email_watcher', 'scheduler', 'api', 'database', 'smtp']
            self.recent_activity = []
            self.favorite_flows = []
            self.stats = {
                'total_executions': 0,
                'global_success_rate': 0,
                'flows_count': 0,
                'atoms_count': 0,
                'activity_30d': 0,
                'pii_protected': 0
            }
            self.watcher_configs = []
            self.local_automations = [] # Prompt 7
            self.loading = True

            # Pagination for recent activity
            self.activity_page = 0
            self.activity_per_page = 10

            # Initialize or retrieve filter state
            self.filter_state = DashboardFilterState() 
            if 'dashboard_filters' not in app.storage.user:
                 app.storage.user['dashboard_filters'] = {
                     'date': 'week', 'type': 'all', 'status': 'all'
                 }
            
            stored = app.storage.user['dashboard_filters']
            self.filter_state.date_filter = stored.get('date', 'week')
            self.filter_state.type_filter = stored.get('type', 'all')
            self.filter_state.status_filter = stored.get('status', 'all')

    dash = DashboardState()
    
    async def load_data():
        """
        Punto de entrada para la carga y agregación de métricas de negocio.
        Consulta múltiples tablas (Logs, ETL, Reportes, Favoritos) para componer
        una vista holística del estado de la automatización en el cliente.
        """
        try:
            from datetime import timedelta
            async with state.db_session() as session:
                # 1. Recent Activity WITH FILTERS
                stmt = build_activity_query(
                    dash.filter_state.date_filter,
                    dash.filter_state.type_filter,
                    dash.filter_state.status_filter
                )
                result = await session.execute(stmt)
                dash.recent_activity = result.scalars().all()

                # 2. Potencia Operativa (Flujos / Átomos)
                flows_count = (await session.execute(select(func.count(FlowRegistry.id)))).scalar_one() or 0
                atoms_count = (await session.execute(select(func.count(ScriptLibrary.id)))).scalar_one() or 0
                dash.stats['flows_count'] = flows_count
                dash.stats['atoms_count'] = atoms_count

                # 3. Fiabilidad (Tasa de Éxito Global)
                # TaskLog (Workflows)
                task_total = (await session.execute(select(func.count(TaskLog.id)))).scalar_one() or 0
                task_success = (await session.execute(select(func.count(TaskLog.id)).where(TaskLog.status == 'success'))).scalar_one() or 0
                
                # ExtractionLog (Atoms direct exec)
                extr_total = (await session.execute(select(func.count(ExtractionLog.id)))).scalar_one() or 0
                extr_success = (await session.execute(select(func.count(ExtractionLog.id)).where(ExtractionLog.status == 'success'))).scalar_one() or 0
                
                total_execs = task_total + extr_total
                total_ok = task_success + extr_success
                
                if total_execs > 0:
                    dash.stats['global_success_rate'] = int((total_ok / total_execs) * 100)
                else:
                    dash.stats['global_success_rate'] = 0

                # 4. Volumen de Actividad (Últimos 30 días)
                cutoff_30d = datetime.utcnow() - timedelta(days=30)
                activity_stmt = select(func.count(RunManifestLog.id)).where(RunManifestLog.created_at >= cutoff_30d)
                dash.stats['activity_30d'] = (await session.execute(activity_stmt)).scalar_one() or 0

                # 5. Soberanía y Privacidad (PII Protegidas)
                pii_stmt = select(func.sum(EnterpriseAuditLog.pii_protected_count))
                dash.stats['pii_protected'] = (await session.execute(pii_stmt)).scalar_one() or 0

                # 6. Favorite Flows
                fav_stmt = select(FlowRegistry).join(FavoriteFlow, FlowRegistry.id == FavoriteFlow.flow_id)
                dash.favorite_flows = (await session.execute(fav_stmt)).scalars().all()
                
                # 7. Aggregated Triggers (Vigilance)
                all_triggers = []
                
                # 8.1. Legacy Folder Watchers (linked to flows)
                from client_app.app.services.folder_watcher_service import folder_watcher_service
                fw_configs = await folder_watcher_service.list_configs()
                for fw in fw_configs:
                    if fw.get('flow_id'): # Only if linked to a flow (subscribed)
                        all_triggers.append({
                            'id': fw['id'],
                            'type': 'folder',
                            'name': fw['name'],
                            'info': fw['watch_path'],
                            'is_active': fw['is_active'],
                            'is_paused': fw['is_paused'],
                            'last_error': fw['last_error'],
                            'icon': 'folder',
                            'color': 'amber'
                        })

                # 8.2. Web Watchers
                from client_app.app.services.web_watcher_service import web_watcher_service
                ww_configs = await web_watcher_service.list_configs()
                for ww in ww_configs:
                    if ww.get('workflow_id'):
                        all_triggers.append({
                            'id': ww['id'],
                            'type': 'web',
                            'name': ww['name'] or ww['url'],
                            'info': ww['url'],
                            'is_active': ww['is_active'],
                            'is_paused': not ww['is_active'],
                            'last_error': None,
                            'icon': 'public',
                            'color': 'cyan'
                        })

                # 8.3. Scheduler Jobs
                from client_app.app.services.scheduler_service import scheduler_service
                sched_jobs = await scheduler_service.get_scheduled_jobs()
                for job in sched_jobs:
                    all_triggers.append({
                        'id': job.job_id,
                        'type': 'schedule',
                        'name': job.description or job.flow_name,
                        'info': f"Cron: {job.schedule_type.value}",
                        'is_active': not job.is_paused,
                        'is_paused': job.is_paused,
                        'last_error': None,
                        'icon': 'schedule',
                        'color': 'purple'
                    })

                # 8.4. Trigger V2 (with subscriptions OR web_watcher with email notification)
                # First get triggers with active subscriptions
                v2_stmt = select(TriggerConfig).join(TriggerSubscription).where(TriggerSubscription.is_active == True)
                v2_result = await session.execute(v2_stmt)
                v2_triggers_with_subs = v2_result.scalars().unique().all()
                v2_trigger_ids = {t.id for t in v2_triggers_with_subs}

                # Also get active web_watchers with email notification (even without subscriptions)
                all_web_watchers_stmt = select(TriggerConfig).where(
                    TriggerConfig.type == 'web_watcher',
                    TriggerConfig.is_active == True
                )
                all_web_watchers_result = await session.execute(all_web_watchers_stmt)
                all_web_watchers = all_web_watchers_result.scalars().all()

                # Merge: triggers with subs + active web_watchers with email notification
                v2_triggers = list(v2_triggers_with_subs)
                for ww in all_web_watchers:
                    if ww.id not in v2_trigger_ids:
                        config = ww.configuration or {}
                        if config.get('send_email_on_change', False):
                            v2_triggers.append(ww)
                            v2_trigger_ids.add(ww.id)

                for trigger in v2_triggers:
                    icon = 'flash_on'
                    color = 'teal'
                    if trigger.type == 'folder_watcher': icon, color = 'folder', 'amber'
                    elif trigger.type == 'mail_watcher': icon, color = 'email', 'indigo'
                    elif trigger.type == 'web_watcher': icon, color = 'public', 'cyan'
                    elif trigger.type == 'scheduler': icon, color = 'schedule', 'purple'

                    all_triggers.append({
                        'id': trigger.id,
                        'type': trigger.type,
                        'name': trigger.name,
                        'info': trigger.description or f"Trigger {trigger.type}",
                        'is_active': trigger.is_active,
                        'is_paused': not trigger.is_active,
                        'last_error': trigger.last_error,
                        'icon': icon,
                        'color': color
                    })

                dash.watcher_configs = all_triggers

                # 9. Local Library
                library_stmt = select(ScriptLibrary).order_by(
                    ScriptLibrary.is_favorite.desc(), 
                    ScriptLibrary.updated_at.desc()
                ).limit(100)
                dash.local_automations = (await session.execute(library_stmt)).scalars().all()

        except Exception as e:
            # Error loading dashboard - show notification
            print(f"ERROR LOADING DASHBOARD DATA: {e}")
            ui.notify(f"{t('common.loading_error', 'Error cargando datos')}: {e}", type='negative', close_button=True)
        finally:
            dash.loading = False
            # --- SAFE REFRESH PATTERN ---
            try:
                render_activity.refresh()
                render_stats_widgets.refresh()
                render_favorites.refresh()
                render_network_status_widget.refresh()
                render_local_library.refresh()
            except Exception:
                pass

    # Real callback for filter changes
    async def handle_filter_change():
        # Update persistence
        app.storage.user['dashboard_filters'] = {
            'date': dash.filter_state.date_filter,
            'type': dash.filter_state.type_filter,
            'status': dash.filter_state.status_filter
        }
        await load_data()



    # --- DIALOGS ---
    



    # --- UI COMPONENTS ---
    
    def render_task_card(task_key):
        """Card for Automation Catalog"""
        task_data = AUTOMATIONS_CATALOG[task_key]
        color = task_data['color']
        name = t(task_data['name_key'])
        desc = t(task_data['desc_key'])
        
        with ui.card().classes(f'w-full h-full p-0 hover:shadow-lg transition-all border-t-4 border-{color}-500 flex flex-col'):
            # Header
            with ui.row().classes(f'w-full p-4 items-center gap-3 bg-{color}-50'):
                ui.icon(task_data['icon'], size='2em').classes(f'text-{color}-600')
                ui.label(name).classes('font-bold text-lg leading-tight text-slate-800')
            
            # Body
            with ui.column().classes('p-4 flex-grow gap-2 min-h-0'):
                ui.label(desc).classes('text-sm text-gray-600 mb-2 leading-relaxed line-clamp-2 overflow-hidden')
                
                # Templates (Optional for future usage, hidden if empty to clean up card)
                if task_data['templates']:
                    ui.label(t('dash.quick_actions_access')).classes('text-xs font-bold text-gray-400 uppercase mt-1')
                    with ui.column().classes('w-full gap-1'):
                        for tmpl in task_data['templates']:
                            route = tmpl.get('route', task_data['route'])
                            with ui.row().classes('w-full justify-between items-center py-1 px-2 hover:bg-slate-50 rounded cursor-pointer group').on('click', lambda r=route: ui.navigate.to(r)):
                                ui.label(tmpl['name']).classes('text-xs text-gray-700 group-hover:text-primary')
                                ui.icon('play_arrow', size='xs').classes('text-gray-300 group-hover:text-primary')
                else:
                    ui.space()

            # Footer Action
            with ui.row().classes('w-full p-3 border-t border-gray-100 justify-end bg-slate-50'):
                route = task_data['route']
                ui.button(t('dash.open'), icon='arrow_forward', on_click=lambda r=route: ui.navigate.to(r)) \
                    .props(f'flat dense color={color}').classes('text-sm')

    def render_connection_card(conn_key):
        """Card for Connections - Refined Mini Style (Identical to Atoms)"""
        conn = CONNECTIONS_CATALOG[conn_key]
        color = conn['color']
        name = conn['name'] # Using hardcoded menu name
        
        # Optimized Compact Chip Design (matching Fast Access)
        border_color = f"{color}-500" if color != 'blue' else "blue-600"
        
        with ui.card().classes(
            f'w-full h-12 px-4 flex-row items-center gap-3 '
            f'hover:shadow-md hover:bg-{color}-50 transition-all cursor-pointer '
            f'border-l-4 border-{border_color} bg-white'
        ).props('flat bordered').on('click', lambda: ui.navigate.to(conn['route'])):
            ui.icon(conn['icon'], size='1.2em').classes(f'text-{color}-600')
            name = t(conn['name_key']) if 'name_key' in conn else conn['name']
            ui.label(name).classes('font-bold text-slate-700 text-sm whitespace-nowrap tracking-tight')





    # --- NETWORK STATUS WIDGET ---
    
    @ui.refreshable
    def render_network_status_widget():
        """
        Renderiza el monitor de conectividad en tiempo real.
        Muestra el estado de salud de todas las carpetas monitorizadas configuradas,
        indicando si son accesibles (Online), están pausadas o tienen errores.
        """
        from datetime import datetime
        
        configs = dash.watcher_configs
        if dash.loading and not configs:
            with ui.row().classes('w-full justify-center p-4'):
                ui.spinner('dots', size='md').classes('text-primary')
            return

        if not configs:
            with ui.card().classes('w-full p-8 items-center bg-gray-50 border-2 border-dashed border-gray-200 shadow-sm'):
                ui.icon('notifications_off', size='3em').classes('text-gray-300 mb-2')
                ui.label(t('triggers.no_triggers')).classes('text-gray-500 font-medium')
                ui.label(t('dash.vigilance_desc')).classes('text-xs text-gray-400')
            return

        # Botón para re-escanear (solo folder watchers se benefician del re-escaneo directo)
        async def rescan_now():
            from client_app.app.services.folder_watcher_service import folder_watcher_service
            await folder_watcher_service.verify_connectivity()
            await load_data()
            ui.notify(t('triggers.sync_started'), type='info')

        with ui.card().classes('w-full p-0 overflow-hidden shadow-sm'):
            # Header combined with stats
            total_count = len(configs)
            active_count = sum(1 for c in configs if c['is_active'])
            
            with ui.row().classes('w-full p-4 bg-slate-50 items-center justify-between border-b'):
                ui.label(t('dash.vigilance_title')).classes('text-sm font-bold text-slate-700')
                
                with ui.row().classes('gap-3'):
                    # Total Chip
                    with ui.row().classes('px-3 py-1 bg-slate-100 rounded-lg items-center gap-2 border border-slate-200'):
                        ui.icon('sensors', size='xs').classes('text-slate-400')
                        ui.label(t('triggers.total')).classes('text-[10px] font-black text-slate-400')
                        ui.label(str(total_count)).classes('text-xs font-bold text-slate-700')
                    
                    # Active Chip
                    with ui.row().classes('px-3 py-1 bg-green-50 rounded-lg items-center gap-2 border border-green-100'):
                        ui.icon('check_circle', size='xs').classes('text-green-500')
                        ui.label(t('triggers.active')).classes('text-[10px] font-black text-green-600')
                        ui.label(str(active_count)).classes('text-xs font-bold text-green-700')

            # Grid para mostrar cada disparador
            with ui.grid().classes('w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-0'):
                for config in configs:
                    # Determinar estado visual
                    is_active = config['is_active']
                    has_error = config.get('last_error') is not None
                    
                    # Asignar color según estado
                    if has_error:
                        color = 'red'
                        status_text = t('triggers.status_error_label')
                        status_icon = 'error'
                    elif is_active:
                        color = 'green'
                        status_text = t('triggers.status_active')
                        status_icon = 'check_circle'
                    else:
                        color = 'grey'
                        status_text = t('triggers.status_paused')
                        status_icon = 'pause_circle'

                    with ui.column().classes(f'p-4 border-r border-b last:border-r-0 hover:bg-slate-50 transition-colors gap-1'):
                        # Icon and Status Dot
                        with ui.row().classes('w-full justify-between items-start mb-1'):
                            ui.icon(config.get('icon', 'flash_on'), size='1.5em').classes(f'text-{config.get("color", "primary")}-600')
                            ui.icon(status_icon, size='14px').classes(f'text-{color}-500')

                        # Nombre
                        ui.label(config['name']).classes('text-xs font-bold text-slate-700 line-clamp-1')
                        
                        # Info/Ruta
                        ui.label(config.get('info', '')).classes('text-[10px] text-slate-400 truncate w-full')
                        
                        # Estado
                        ui.label(status_text).classes(f'text-xs font-semibold text-{color}-600')


    # Main layout con el widget de estado de red
    with ui.column().classes('w-full gap-2'):
        # Header
        page_header(
            t('menu_dashboard'),
            t('dash.subtitle')
        )

        # 1. KEY PERFORMANCE INDICATORS (KPIs)
        with ui.row().classes('w-full justify-center mb-6'):
             @ui.refreshable
             def render_stats_widgets():
                with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3'):
                    # 1. Potencia Operativa (Inventario Activo)
                    with ui.card().classes('p-4 flex-row gap-3 items-center bg-white shadow-sm border border-gray-100 hover:shadow-md transition-shadow'):
                        with ui.column().classes('p-2 bg-blue-50 rounded-full'):
                            ui.icon('o_library_books', size='1.5em').classes('text-blue-600')
                        with ui.column().classes('gap-0'):
                            ui.label(f"{dash.stats['flows_count']} / {dash.stats['atoms_count']}").classes('text-base font-bold leading-none text-slate-700')
                            ui.label(t('dash.stats_flows_actions')).classes('text-[10px] text-gray-400 uppercase font-bold tracking-wider')
                            ui.tooltip(t('dash.stats_flows_actions_tooltip'))

                    # 2. Tasa de Éxito Global (Fiabilidad)
                    with ui.card().classes('p-4 flex-row gap-3 items-center bg-white shadow-sm border border-gray-100 hover:shadow-md transition-shadow'):
                        with ui.column().classes('p-2 bg-emerald-50 rounded-full'):
                            ui.icon('o_check_circle', size='1.5em').classes('text-emerald-500')
                        with ui.column().classes('gap-0'):
                            ui.label(f"{dash.stats['global_success_rate']}%").classes('text-base font-bold leading-none text-slate-700')
                            ui.label(t('dash.stats_success_rate')).classes('text-[10px] text-gray-400 uppercase font-bold tracking-wider')
                            ui.tooltip(t('dash.stats_success_rate_tooltip'))

                    # 3. Volumen de Actividad (Tráfico de Datos)
                    with ui.card().classes('p-4 flex-row gap-3 items-center bg-white shadow-sm border border-gray-100 hover:shadow-md transition-shadow'):
                        with ui.column().classes('p-2 bg-indigo-50 rounded-full'):
                            ui.icon('o_timeline', size='1.5em').classes('text-indigo-600')
                        with ui.column().classes('gap-0'):
                            ui.label(str(dash.stats['activity_30d'])).classes('text-base font-bold leading-none text-slate-700')
                            ui.label(t('dash.stats_activity')).classes('text-[10px] text-gray-400 uppercase font-bold tracking-wider')
                            ui.tooltip(t('dash.stats_activity_tooltip'))

                    # 4. Soberanía y Privacidad (PII Protegidas)
                    with ui.card().classes('p-4 flex-row gap-3 items-center bg-white shadow-sm border border-gray-100 hover:shadow-md transition-shadow'):
                        with ui.column().classes('p-2 bg-purple-50 rounded-full'):
                            ui.icon('o_security', size='1.5em').classes('text-purple-600')
                        with ui.column().classes('gap-0'):
                            ui.label(str(dash.stats['pii_protected'])).classes('text-base font-bold leading-none text-slate-700')
                            ui.label(t('dash.stats_pii')).classes('text-[10px] text-gray-400 uppercase font-bold tracking-wider')
                            ui.tooltip(t('dash.stats_pii_tooltip'))
             
             render_stats_widgets()

        # 2. FAVORITE FLOWS
        with ui.row().classes('w-full justify-between items-center mb-2'):
            ui.label(t('dash.favorites')).classes('text-xl font-bold text-slate-800')
            ui.button(t('dash.view_all'), icon='arrow_forward', on_click=lambda: ui.navigate.to('/flows')).props('flat dense size=sm color=primary')

        @ui.refreshable
        def render_favorites():
            if dash.loading:
                with ui.row().classes('w-full justify-center'):
                    ui.spinner('dots', size='lg').classes('text-primary')
                return

            if not dash.favorite_flows:
                with ui.card().classes('w-full p-6 items-center bg-gray-50 border-2 border-dashed border-gray-200 shadow-sm'):
                    ui.icon('o_star_outline', size='2em').classes('text-gray-400 mb-2')
                    ui.label(t('dash.no_favorites')).classes('text-gray-500 text-sm')
                return
            
            with ui.list().classes('w-full p-0 bg-white rounded-lg border border-gray-100 shadow-sm'):
                for flow in dash.favorite_flows:
                    step_count = len(json.loads(flow.steps)) if isinstance(flow.steps, str) else len(flow.steps)
                    
                    with ui.item().classes('w-full px-4 py-3 border-b border-gray-100 last:border-0 hover:bg-slate-50 transition-colors cursor-pointer').on('click', lambda f=flow: ui.navigate.to(f'/flows?run={f.id}')):
                        with ui.item_section().props('avatar'):
                             ui.icon('o_account_tree', size='md').classes('text-purple-600 bg-purple-50 p-2 rounded-full')
                        
                        with ui.item_section():
                            ui.item_label(flow.name).classes('font-bold text-slate-700')
                            ui.item_label(f"{step_count} passos").classes('text-caption text-gray-500') # Fixed typo in steps name if needed, or translate
                            # Actually, should use t('flows.step_prefix') + f": {step_count}" or similar
                            # For now just kept it simple or translate:
                            # ui.item_label(t('flows.steps_label', count=step_count)).classes('text-caption text-gray-500')
                        
                        with ui.item_section().props('side'):
                            ui.button(icon='play_arrow', on_click=lambda f=flow: ui.navigate.to(f'/flows?run={f.id}')).props('flat round dense size=sm color=green')

        render_favorites()


        # 3.5. LOCAL LIBRARY (PROMPT 7 + PROMPT 5 Update)
        with ui.column().classes('w-full mb-6'):
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label(t('dash.fav_actions')).classes('text-xl font-bold text-slate-800')
                ui.button(t('dash.go_library'), icon='arrow_forward', on_click=lambda: ui.navigate.to('/atoms')).props('flat dense size=sm color=primary')
            
            # Helper handlers for resource cards
            def open_refine_dash(resource):
                # Usar lógica de editor centralizada
                status = getattr(resource, 'status', 'published')
                
                if status == 'draft':
                    if resource.source_module == 'custom':
                        if resource.source_automation_id:
                            ui.navigate.to(f'/custom-scripts/{resource.source_automation_id}/edit')
                        else:
                            ui.notify("No source script found.", type='negative')
                    elif resource.source_module == 'extraction':
                        ui.navigate.to('/documents')
                    elif resource.source_module == 'rpa':
                        ui.navigate.to('/rpa')
                    elif resource.source_module == 'graphics':
                        ui.navigate.to('/graphics')
                    elif resource.source_module == 'etl':
                        ui.navigate.to('/etl')
                    else:
                        # Si es borrador pero no tiene editor dedicado, abrir documentación
                        layout_manager.enter_documentation_mode(
                            atom_name=resource.name,
                            doc_path=getattr(resource, 'doc_path', f"data/storage/scripts/docs/{resource.id}.md"),
                            resource_id=resource.id,
                            record_type='library',
                            status=status,
                            description=getattr(resource, 'description', '')
                        )
                else:
                    # MODO SELLADO: Metadatos en el Drawer
                    layout_manager.enter_documentation_mode(
                        atom_name=resource.name,
                        doc_path=getattr(resource, 'doc_path', f"data/storage/scripts/docs/{resource.id}.md"),
                        resource_id=resource.id,
                        record_type='library',
                        status=status,
                        description=getattr(resource, 'description', '')
                    )

            def open_execute_dash(resource):
                if resource.source_module == 'custom':
                     if resource.source_automation_id: ui.navigate.to(f'/custom-scripts/{resource.source_automation_id}')
                     else: ui.notify(t('common.error_script_not_found', 'No se encontró el script de origen'), type='negative')
                elif resource.source_module == 'extraction': ui.navigate.to(f'/documents?initial_mode=execution&atom_id={resource.id}')
                elif resource.source_module == 'etl': ui.navigate.to(f'/etl?initial_mode=execution&atom_id={resource.id}')
                elif resource.source_module == 'rpa': ui.navigate.to(f'/rpa?initial_mode=execution&atom_id={resource.id}')
                elif resource.source_module == 'graphics': ui.navigate.to(f'/graphics?initial_mode=execution&atom_id={resource.id}')
                elif resource.source_module == 'smtp': ui.navigate.to(f'/outputs/smtp?initial_mode=execution&atom_id={resource.id}')
                elif resource.source_module in ['anonymization', 'anonymizer']: ui.navigate.to(f'/processors/anonymizer?initial_mode=execution&atom_id={resource.id}')
                elif resource.source_module == 'pdf_tools': ui.navigate.to(f'/atoms/pdf-tools/{resource.id}?initial_mode=execution')
                else: ui.notify(f'{t("common.not_available", "Ejecución no disponible")} para {resource.source_module}', type='warning')

            @ui.refreshable
            def render_local_library():
                if dash.loading:
                    return
                
                try:
                    # Filter Only Favorites + Published
                    favorites = [
                        s for s in dash.local_automations 
                        if getattr(s, 'is_favorite', False) and s.status in ('published', 'validated')
                    ]
                    
                    if not favorites:
                         with ui.card().classes('w-full p-6 bg-slate-50 border-dashed border-2 border-slate-200 items-center justify-center shadow-sm'):
                            ui.icon('star_border', size='3em').classes('text-gray-300 mb-2')
                            ui.label(t('dash.no_fav_actions')).classes('text-gray-500 italic mb-2')
                            ui.button(t('dash.go_library'), on_click=lambda: ui.navigate.to('/library')).props('flat color=primary')
                         return


                    # 3-Column Grid
                    async def delete_from_dash(resource):
                        """Delete a resource from dashboard."""
                        try:
                            await script_library_service.delete_script(resource.id, force=True)
                            ui.notify(t('common.deleted_success', name=resource.name), type='positive')
                            await load_data()
                        except Exception as e:
                            ui.notify(f"{t('common.delete_error')}: {e}", type='negative')

                    with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-6 p-2'):
                        for item in favorites:
                            try:
                                unified_resource_card(
                                    resource=item,
                                    on_execute=open_execute_dash,
                                    on_edit=open_refine_dash,
                                    on_click=open_execute_dash,
                                    on_delete=delete_from_dash
                                )
                            except Exception as e:
                                 with ui.card().classes('w-full bg-red-100 p-2'):
                                    ui.label(f"Error card: {e}").classes('text-red-500 text-xs')
                
                except Exception as e:
                     with ui.card().classes('w-full bg-red-100 p-4'):
                        ui.label(f"Error rendering library: {e}").classes('text-red-500 font-bold')
                        import traceback
                        ui.label(traceback.format_exc()).classes('text-xs font-mono whitespace-pre-wrap')

            render_local_library()

        # 3.6. QUICK ACTIONS SECTION
        with ui.column().classes('w-full mb-6'):
            ui.label(t('dash.quick_actions')).classes('text-xl font-bold text-slate-800 mb-4')

            with ui.grid().classes('w-full grid-cols-2 md:grid-cols-4 gap-4'):
                # Card 1: Anonimizador
                with ui.card().classes(
                    'w-full h-24 p-4 flex-row items-center gap-4 '
                    'hover:shadow-lg transition-all cursor-pointer '
                    'border border-slate-200 border-l-4 border-l-purple-500 bg-white shadow-sm'
                ).on('click', lambda: ui.navigate.to('/anonymizer')):
                    with ui.column().classes('p-2 bg-purple-100 rounded-full'):
                        ui.icon('lock', size='1.5em').classes('text-purple-600')
                    with ui.column().classes('gap-0'):
                        ui.label(t('dash.anon_name')).classes('font-bold text-slate-700 text-sm')
                        ui.label(t('dash.anon_desc')).classes('text-xs text-slate-500')

                # Card 2: Herramientas PDF
                with ui.card().classes(
                    'w-full h-24 p-4 flex-row items-center gap-4 '
                    'hover:shadow-lg transition-all cursor-pointer '
                    'border border-slate-200 border-l-4 border-l-red-500 bg-white shadow-sm'
                ).on('click', lambda: ui.navigate.to('/utilities/pdf-tools')):
                    with ui.column().classes('p-2 bg-red-100 rounded-full'):
                        ui.icon('picture_as_pdf', size='1.5em').classes('text-red-600')
                    with ui.column().classes('gap-0'):
                        ui.label(t('dash.pdf_name')).classes('font-bold text-slate-700 text-sm')
                        ui.label(t('dash.pdf_desc')).classes('text-xs text-slate-500')

                # Card 3: Crear gráfico (va directo al configurador)
                with ui.card().classes(
                    'w-full h-24 p-4 flex-row items-center gap-4 '
                    'hover:shadow-lg transition-all cursor-pointer '
                    'border border-slate-200 border-l-4 border-l-indigo-500 bg-white shadow-sm'
                ).on('click', lambda: ui.navigate.to('/graphics?initial_mode=design')):
                    with ui.column().classes('p-2 bg-indigo-100 rounded-full'):
                        ui.icon('bar_chart', size='1.5em').classes('text-indigo-600')
                    with ui.column().classes('gap-0'):
                        ui.label(t('dash.graph_name')).classes('font-bold text-slate-700 text-sm')
                        ui.label(t('dash.graph_desc')).classes('text-xs text-slate-500')

                # Card 4: Transformar datos (va directo al configurador)
                with ui.card().classes(
                    'w-full h-24 p-4 flex-row items-center gap-4 '
                    'hover:shadow-lg transition-all cursor-pointer '
                    'border border-slate-200 border-l-4 border-l-pink-500 bg-white shadow-sm'
                ).on('click', lambda: ui.navigate.to('/etl?initial_mode=design')):
                    with ui.column().classes('p-2 bg-pink-100 rounded-full'):
                        ui.icon('transform', size='1.5em').classes('text-pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label(t('dash.etl_name')).classes('font-bold text-slate-700 text-sm')
                        ui.label(t('dash.etl_desc')).classes('text-xs text-slate-500')

        # 4. CREATE NEW ATOM SECTION - REMOVED

        # 4. CONNECTIONS - REMOVED

        # 5. NETWORK STATUS SECTION (Relocated)
        with ui.column().classes('w-full mb-6'):
            with ui.row().classes('w-full justify-between items-center mb-0'):
                ui.label(t('dash.vigilance_title')).classes('text-xl font-bold text-slate-800')
                ui.button(t('dash.vigilance_btn'), icon='arrow_forward', on_click=lambda: ui.navigate.to('/triggers')).props('flat dense size=sm color=primary')

            render_network_status_widget()

        # 6. RECENT ACTIVITY
        with ui.column().classes('w-full gap-0'):
            # Header row with title, filters, and navigation
            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label(t('dash.recent')).classes('text-xl font-bold text-slate-800')
                with ui.row().classes('items-center gap-2'):
                    render_activity_filters(t, dash.filter_state, handle_filter_change)
                    ui.button(t('dash.view_history'), icon='arrow_forward', on_click=lambda: ui.navigate.to('/logs')).props('flat dense size=sm color=primary')

            @ui.refreshable
            def render_activity():
                if not dash.recent_activity:
                    with ui.card().classes('w-full p-6 items-center bg-slate-50 border-dashed border-2 border-slate-200'):
                        ui.icon('history', size='2em').classes('text-gray-300 mb-1')
                        ui.label(t('dash.no_recent')).classes('text-gray-400 italic text-sm')
                    return

                # Pagination calculations
                total_items = len(dash.recent_activity)
                total_pages = (total_items + dash.activity_per_page - 1) // dash.activity_per_page
                start_idx = dash.activity_page * dash.activity_per_page
                end_idx = min(start_idx + dash.activity_per_page, total_items)
                page_items = dash.recent_activity[start_idx:end_idx]

                with ui.card().classes('w-full p-2 gap-0 shadow-sm overflow-hidden'):
                    # Two-column grid layout for compact display
                    with ui.grid(columns=2).classes('w-full gap-x-4 gap-y-0'):
                        for log in page_items:
                            icon = 'check_circle' if log.status == 'success' else 'error' if log.status == 'failed' else 'hourglass_empty'
                            color = 'text-green-500' if log.status == 'success' else 'text-red-500' if log.status == 'failed' else 'text-gray-400'
                            ago = log.timestamp.strftime('%H:%M') if log.timestamp else '-'

                            with ui.row().classes('w-full py-1 items-center gap-2 border-b border-gray-50 hover:bg-slate-50 transition-colors'):
                                ui.icon(icon, size='xs').classes(color)
                                ui.label(log.filename or '-').classes('text-sm text-slate-700 truncate max-w-[120px]')
                                ui.label(f"• {log.service_used}").classes('flex-1 text-[11px] text-gray-400 truncate min-w-0')
                                ui.label(ago).classes('text-[11px] text-gray-400 font-mono shrink-0')

                    # Pagination footer
                    if total_pages > 1:
                        with ui.row().classes('w-full pt-2 mt-1 border-t items-center justify-between'):
                            ui.label(f"{start_idx + 1}-{end_idx} de {total_items}").classes('text-xs text-slate-500')

                            with ui.row().classes('items-center gap-1'):
                                def go_prev():
                                    if dash.activity_page > 0:
                                        dash.activity_page -= 1
                                        render_activity.refresh()

                                def go_next():
                                    if dash.activity_page < total_pages - 1:
                                        dash.activity_page += 1
                                        render_activity.refresh()

                                ui.button(icon='chevron_left', on_click=go_prev).props(
                                    f'flat dense round size=sm {"disable" if dash.activity_page == 0 else ""}'
                                )
                                ui.label(f"{dash.activity_page + 1} / {total_pages}").classes('text-xs text-slate-600 mx-2')
                                ui.button(icon='chevron_right', on_click=go_next).props(
                                    f'flat dense round size=sm {"disable" if dash.activity_page >= total_pages - 1 else ""}'
                                )

            render_activity()

    # --- LAUNCHER INTEGRATION (PROMPT 6) ---
    def open_launcher():
        from client_app.app.ui.components.universal_selector import UniversalSelector
        
        def on_launch(item):
            # This is called when user clicks "Launch" inside selector
            # Launcher service is called inside selector, here we just show feedback or refresh
            ui.notify(t('common.starting', name=item.name), type='positive')
            # Refresh logs to show new execution if immediate
            ui.timer(1.0, load_data, once=True)

        selector = UniversalSelector(on_result=on_launch)
        selector.open()


    # Initial Load
    # Run async load_data automatically
    # Use a small delay to avoid "Client has been deleted" errors on fast startup
    ui.timer(0.1, load_data, once=True)

