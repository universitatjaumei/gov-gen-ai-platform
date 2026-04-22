from nicegui import ui, app
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from client_app.app.core.state import state
from client_app.app.services.enterprise_audit_service import enterprise_audit_service
from client_app.app.database.models import RiskLevel

# --- CONFIGURACIÓN DE FILTROS ---
AUDIT_FILTER_OPTIONS = {
    'date': {
        'today': 'today',
        'week': 'week',
        'month': 'month',
        'all': 'all',
    },
    'risk': {
        'all': 'all',
        'low': RiskLevel.LOW.value,
        'medium': RiskLevel.MEDIUM.value,
        'high': RiskLevel.HIGH.value,
        'critical': RiskLevel.CRITICAL.value,
    }
}

class AuditPageState:
    """
    Mantiene el estado reactivo de la página de auditoría empresarial.
    Controla los filtros de fecha, riesgo y módulo, además de almacenar los logs
    recuperados y las estadísticas resumidas (KPIs).
    """
    def __init__(self):
        self.date_filter = 'week'
        self.risk_filter = 'all'
        self.action_filter = 'all'
        self.module_filter = 'all'
        self.logs = []
        self.stats = {
            'total_count': 0,
            'high_risk_count': 0,
            'pii_processed': 0
        }
        self.loading = True

def audit_page_content():
    """
    Controlador principal de la página de auditoría y cumplimiento (RGPD).
    Proporciona una interfaz para la consulta de registros inmutables de seguridad,
    análisis de exposición de PII y exportación de informes oficiales.
    """
    # Cargar traducciones específicas
    from automatia_shared.core.i18n import i18n
    import json
    import os
    
    # Load audit translations
    trans_path = os.path.join(os.path.dirname(__file__), 'audit_translations.json')
    if os.path.exists(trans_path):
        with open(trans_path, 'r', encoding='utf-8') as f:
            audit_trans = json.load(f)
            # Merge into global i18n (assuming i18n.load_dict or similar exists, 
            # or we just use a local translate helper)
            # For this context, we'll use a local helper that prioritizes audit_trans
            def t_audit(key, **kwargs):
                lang = state.i18n.locale
                val = audit_trans.get(lang, {}).get(key, audit_trans.get('es', {}).get(key, key))
                if kwargs:
                    return val.format(**kwargs)
                return val
    else:
        t_audit = state.i18n.t # Fallback
        
    t = state.i18n.t

    audit_state = AuditPageState()

    async def load_data():
        """
        Carga los datos de auditoría aplicando los filtros actuales.
        Consulta tanto las estadísticas generales como el listado detallado de logs.
        """
        audit_state.loading = True
        render_content.refresh()
        
        try:
            # 1. Calcular fechas
            start_date = None
            end_date = datetime.utcnow()
            
            if audit_state.date_filter == 'today':
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif audit_state.date_filter == 'week':
                start_date = end_date - timedelta(days=7)
            elif audit_state.date_filter == 'month':
                start_date = end_date - timedelta(days=30)
            
            # 2. Consultar Stats
            if start_date:
                audit_state.stats = await enterprise_audit_service.get_summary_stats(start_date, end_date)
            else:
                # Si es 'all', usamos una fecha muy antigua para las stats
                audit_state.stats = await enterprise_audit_service.get_summary_stats(datetime(2000, 1, 1), end_date)
            
            # 3. Consultar Logs con filtros
            risk = None if audit_state.risk_filter == 'all' else audit_state.risk_filter
            action = None if audit_state.action_filter == 'all' else audit_state.action_filter
            module = None if audit_state.module_filter == 'all' else audit_state.module_filter
            
            audit_state.logs = await enterprise_audit_service.query_logs(
                start_date=start_date,
                end_date=end_date,
                risk_level=risk,
                action_type=action,
                module=module,
                limit=100
            )
            
        except Exception as e:
            ui.notify(f"Error cargando auditoría: {e}", type='negative')
        finally:
            audit_state.loading = False
            render_content.refresh()

    def show_log_details(log):
        """
        Muestra un diálogo detallado con toda la información de un registro de auditoría.
        Incluye métricas de protección de PII, contexto de origen/destino y metadatos técnicos.

        Args:
            log: Objeto AuditLog a visualizar.
        """
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-3xl'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label(t_audit('audit_details_title')).classes('text-xl font-bold')
                ui.button(icon='close', on_click=dialog.close).props('flat round dense')
            
            ui.separator().classes('mb-4')
            
            with ui.grid(columns=3).classes('w-full gap-4 mb-6'):
                with ui.column():
                    ui.label(t_audit('audit_col_timestamp')).classes('text-xs font-bold text-gray-400 uppercase')
                    ui.label(log.timestamp.strftime('%Y-%m-%d %H:%M:%S')).classes('font-mono')
                
                with ui.column():
                    ui.label(t_audit('audit_col_action')).classes('text-xs font-bold text-gray-400 uppercase')
                    ui.badge(log.action_type.upper(), color='blue')
                
                with ui.column():
                    ui.label(t_audit('audit_col_risk')).classes('text-xs font-bold text-gray-400 uppercase')
                    risk_colors = {'low': 'green', 'medium': 'orange', 'high': 'red', 'critical': 'purple'}
                    ui.badge(t_audit(f'audit_risk_{log.risk_level}'), color=risk_colors.get(log.risk_level, 'grey'))

            # PII Details
            if log.pii_detected_count > 0:
                with ui.card().classes('w-full p-4 bg-green-50 mb-4 border border-green-100'):
                    ui.label(t_audit('audit_details_metrics')).classes('font-bold text-green-800 mb-2')
                    with ui.row().classes('gap-6'):
                        with ui.column().classes('items-center'):
                            ui.label(str(log.pii_detected_count)).classes('text-2xl font-bold text-green-700')
                            ui.label('Detectadas').classes('text-xs text-green-600')
                        with ui.column().classes('items-center'):
                            ui.label(str(log.pii_protected_count)).classes('text-2xl font-bold text-green-700')
                            ui.label('Protegidas').classes('text-xs text-green-600')
                        with ui.column().classes('flex-1'):
                            ui.label('Tipos de datos:').classes('text-xs font-bold text-green-800')
                            types_str = ", ".join([f"{k} ({v})" for k, v in log.pii_types.items()])
                            ui.label(types_str or "Varios").classes('text-xs text-green-700')
                    
                    if log.anonymization_method:
                        ui.label(f"Método: {log.anonymization_method}").classes('text-xs text-green-600 mt-2 italic')

            # Context
            with ui.column().classes('w-full gap-2 mb-4'):
                ui.label(t_audit('audit_details_context')).classes('font-bold text-slate-700')
                with ui.row().classes('w-full bg-slate-50 p-3 rounded text-sm'):
                    with ui.column().classes('flex-1'):
                        ui.label('Módulo:').classes('font-bold')
                        ui.label(log.module)
                    with ui.column().classes('flex-1'):
                        ui.label('Origen:').classes('font-bold')
                        ui.label(log.source_description or "N/A")
                    with ui.column().classes('flex-1'):
                        ui.label('Destino:').classes('font-bold')
                        ui.label(log.target_description or "N/A")

            # Technical Details (JSON)
            if log.additional_context or log.security_flags:
                with ui.expansion('Datos Técnicos (JSON)', icon='code').classes('w-full border rounded'):
                    technical = {
                        'additional_context': log.additional_context,
                        'security_flags': log.security_flags,
                        'execution_id': log.execution_id,
                        'task_log_id': log.task_log_id
                    }
                    ui.json_editor({'content': {'json': technical}}).classes('h-64')

        dialog.open()

    # --- UI LAYOUT ---
    with ui.column().classes('w-full p-4 gap-6'):
        with ui.row().classes('w-full items-center justify-between'):
            with ui.column().classes('gap-0'):
                pass
            
            ui.button(t_audit('audit_btn_export'), icon='download').props('outline').classes('group').on_click(lambda: export_menu.open())
            with ui.menu() as export_menu:
                ui.menu_item(t_audit('audit_export_excel'), on_click=lambda: handle_export('excel'))
                ui.menu_item(t_audit('audit_export_pdf'), on_click=lambda: handle_export('pdf'))

    async def handle_export(format_type):
        """
        Gestiona la exportación de los logs actuales en formato Excel o PDF.
        Traduce los campos dinámicos para el informe oficial.

        Args:
            format_type: 'excel' o 'pdf'.
        """
        export_loading.set_visibility(True)
        try:
            # 1. Obtener traducciones para el informe (necesarias para el PDF)
            trans_dict = {}
            keys = [
                'audit_export_report_title', 'audit_export_summary', 
                'audit_stats_total', 'audit_stats_high_risk', 'audit_stats_pii', 'audit_filter_date',
                'audit_col_timestamp', 'audit_col_action', 'audit_col_user', 'audit_col_pii', 'audit_col_risk', 'audit_filter_module'
            ]
            for k in keys:
                trans_dict[k] = t_audit(k)
            
            # 2. Generar archivo
            if format_type == 'excel':
                content = await enterprise_audit_service.generate_excel_export(audit_state.logs, audit_state.stats)
                ext = 'xlsx'
            else:
                content = await enterprise_audit_service.generate_pdf_export(audit_state.logs, audit_state.stats, trans_dict)
                ext = 'pdf'
            
            # 3. Descargar
            filename = t_audit('audit_export_filename', date=datetime.now().strftime('%Y%m%d_%H%M%S')) + f".{ext}"
            ui.download(content.read(), filename)
            ui.notify(f"Exportación {format_type.upper()} completada", type='positive')
            
        except Exception as e:
            ui.notify(f"Error en exportación: {e}", type='negative')
        finally:
            export_loading.set_visibility(False)

    export_loading = ui.row().classes('w-full items-center justify-center p-2 bg-blue-50 text-blue-700 hidden')
    with export_loading:
        ui.spinner(size='sm')
        ui.label('Generando archivo de exportación oficial...')

    # KPI Widgets
    @ui.refreshable
    def render_kpis():
        """
        Renderiza los indicadores clave de desempeño (KPIs) en la parte superior.
        Muestra el total de eventos, alertas de alto riesgo y datos PII protegidos.
        """
        with ui.row().classes('w-full gap-4'):
            # Total Events
            with ui.card().classes('flex-1 p-4 flex-row items-center gap-4 bg-white shadow-sm border-l-4 border-blue-500'):
                ui.icon('list_alt', size='2.5em').classes('text-blue-500')
                with ui.column().classes('gap-0'):
                    ui.label(str(audit_state.stats['total_count'])).classes('text-2xl font-bold text-slate-700')
                    ui.label(t_audit('audit_stats_total')).classes('text-xs text-gray-400 font-bold uppercase')

            # High Risk
            with ui.card().classes('flex-1 p-4 flex-row items-center gap-4 bg-white shadow-sm border-l-4 border-red-500'):
                ui.icon('report_problem', size='2.5em').classes('text-red-500')
                with ui.column().classes('gap-0'):
                    ui.label(str(audit_state.stats['high_risk_count'])).classes('text-2xl font-bold text-slate-700')
                    ui.label(t_audit('audit_stats_high_risk')).classes('text-xs text-gray-400 font-bold uppercase')

            # PII Protected
            with ui.card().classes('flex-1 p-4 flex-row items-center gap-4 bg-white shadow-sm border-l-4 border-green-500'):
                ui.icon('security', size='2.5em').classes('text-green-500')
                with ui.column().classes('gap-0'):
                    ui.label(str(audit_state.stats['pii_processed'])).classes('text-2xl font-bold text-slate-700')
                    ui.label(t_audit('audit_stats_pii')).classes('text-xs text-gray-400 font-bold uppercase')

    # Filters
    with ui.card().classes('w-full p-4 bg-slate-50'):
        with ui.row().classes('w-full gap-4 items-end'):
            # Date
            async def on_date_change(e):
                audit_state.date_filter = e.value
                await load_data()

            ui.select(
                label=t_audit('audit_filter_date'),
                options={k: t_audit(f'audit_filter_date') if k=='all' else t(f'logs_filter_{k}') for k in AUDIT_FILTER_OPTIONS['date']},
                value=audit_state.date_filter,
                on_change=on_date_change
            ).classes('w-40')

            # Risk
            async def on_risk_change(e):
                audit_state.risk_filter = e.value
                await load_data()

            ui.select(
                label=t_audit('audit_filter_risk'),
                options={k: t_audit(f'audit_filter_risk') if k=='all' else t_audit(f'audit_risk_{k}') for k in AUDIT_FILTER_OPTIONS['risk']},
                value=audit_state.risk_filter,
                on_change=on_risk_change
            ).classes('w-40')

            # Action (Hardcoded for now based on ActionType)
            actions = {'all': t_audit('audit_filter_action'), 'extraction': 'Extraction', 'anonymization': 'Anonymization', 'deanonymization': 'Deanonymization'}
            
            async def on_action_change(e):
                audit_state.action_filter = e.value
                await load_data()

            ui.select(
                label=t_audit('audit_filter_action'),
                options=actions,
                value=audit_state.action_filter,
                on_change=on_action_change
            ).classes('w-48')

            ui.space()
            ui.button(icon='refresh', on_click=load_data).props('flat round color=primary')

    # Content (Loading or Table)
    @ui.refreshable
    def render_content():
        """
        Renderiza el contenido principal de la página, manejando estados de carga,
        vistas vacías y la tabla interactiva de registros.
        """
        if audit_state.loading:
            with ui.column().classes('w-full items-center py-20'):
                ui.spinner(size='lg').classes('text-primary')
                ui.label(t_audit('audit_fetching', default='Consultando registros inmutables...')).classes('text-slate-400 mt-4')
            return

        if not audit_state.logs:
            with ui.card().classes('w-full p-12 items-center bg-slate-50 border-2 border-dashed border-slate-200'):
                ui.icon('history_toggle_off', size='4em').classes('text-slate-300 mb-2')
                ui.label(t_audit('audit_no_results')).classes('text-slate-400 italic')
            return

        # KPI Refresh inside content refresh to keep sync
        render_kpis()

        # Table
        columns = [
            {'name': 'timestamp', 'label': t_audit('audit_col_timestamp'), 'field': 'timestamp', 'align': 'left', 'sortable': True},
            {'name': 'action', 'label': t_audit('audit_col_action'), 'field': 'action_type', 'align': 'left'},
            {'name': 'module', 'label': t_audit('audit_filter_module'), 'field': 'module', 'align': 'left'},
            {'name': 'pii', 'label': t_audit('audit_col_pii'), 'field': 'pii_detected_count', 'align': 'center'},
            {'name': 'risk', 'label': t_audit('audit_col_risk'), 'field': 'risk_level', 'align': 'center'},
            {'name': 'actions', 'label': '', 'field': 'actions', 'align': 'right'}
        ]

        with ui.table(columns=columns, rows=[], row_key='id').classes('w-full border rounded-lg bg-white shadow-sm').props('flat bordered dense') as table:
            # Custom Row Rendering
            table.add_slot('body-cell-timestamp', r'''
                <q-td :props="props">
                    <span class="text-xs font-mono text-gray-500">{{ new Date(props.value).toLocaleString() }}</span>
                </q-td>
            ''')

            table.add_slot('body-cell-action', r'''
                <q-td :props="props">
                    <q-chip dense outline color="primary" class="text-weight-bold text-uppercase">{{ props.value }}</q-chip>
                </q-td>
            ''')

            table.add_slot('body-cell-risk', r'''
                <q-td :props="props" class="text-center">
                    <q-badge :color="props.value === 'low' ? 'green' : props.value === 'medium' ? 'orange' : 'red'">
                        {{ props.value.toUpperCase() }}
                    </q-badge>
                </q-td>
            ''')

            table.add_slot('body-cell-pii', r'''
                <q-td :props="props" class="text-center">
                    <q-badge v-if="props.value > 0" color="green-2" text-color="green-9" class="text-weight-bold">
                        {{ props.value }}
                    </q-badge>
                    <span v-else class="text-gray-300">-</span>
                </q-td>
            ''')

            table.add_slot('body-cell-actions', r'''
                <q-td :props="props" class="text-right">
                    <q-btn flat round dense icon="visibility" color="gray" @click="() => $parent.$emit('view_details', props.row)" />
                </q-td>
            ''')

            # Pre-process rows for NiceGUI table
            table.rows = [log.model_dump() for log in audit_state.logs]
            table.on('view_details', lambda e: show_log_details(next(l for l in audit_state.logs if l.id == e.args['id'])))

    render_content()

    # Initial Load
    ui.timer(0.1, load_data, once=True)
