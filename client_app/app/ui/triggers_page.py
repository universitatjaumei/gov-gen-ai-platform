from typing import List, Dict, Any, Optional
from nicegui import ui
from client_app.app.ui.components.page_header import page_header

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from automatia_shared.enums import StepType

# --- NAVIGATION HANDLERS ---

def open_folder_page(watcher_id: Optional[int] = None):
    url = '/connections/folders?mode=design'
    if watcher_id:
        url += f'&config_id={watcher_id}'
    ui.navigate.to(url)

def open_email_page(watcher_id: Optional[int] = None):
    url = '/connections/email?mode=design'
    if watcher_id:
        url += f'&watcher_id={watcher_id}'
    ui.navigate.to(url)

def open_web_page(watcher_id: Optional[int] = None):
    url = '/triggers/web-watcher?mode=design'
    if watcher_id:
        url += f'&watcher_id={watcher_id}'
    ui.navigate.to(url)
    
def open_scheduler_page(job_id: Optional[str] = None):
    url = '/triggers/scheduler?mode=design'
    if job_id:
        url += f'&job_id={job_id}'
    ui.navigate.to(url)

def handle_edit(item: Dict):
    t_type = item['type']
    item_id = item['id']
    if t_type == 'FOLDER':
        open_folder_page(item_id)
    elif t_type == 'EMAIL':
        open_email_page(item_id)
    elif t_type == 'WEB':
        open_web_page(item_id)
    elif t_type == 'SCHEDULER':
        open_scheduler_page(item_id)
    elif t_type == 'TRIGGER_V2':
        # Handle V2 triggers based on subtype
        subtype = item.get('subtype', '')
        if subtype == 'email_watcher':
            open_email_page(item_id)
        elif subtype == 'folder_watcher':
            open_folder_page(item_id)
        elif subtype == 'web_watcher':
            open_web_page(item_id)
        elif subtype == 'scheduler':
            open_scheduler_page(item_id)

# --- STATE ---
class TriggersPageState:
    def __init__(self):
        self.triggers: List[Dict] = []
        self.is_loading: bool = False
        self.stats = {
            'total': 0, 'active': 0, 'alerts': 0
        }

page_state = TriggersPageState()

# --- LOGIC ---

async def load_all_triggers():
    """Carga todos los disparadores desde TriggerConfig (arquitectura unificada V2)."""
    page_state.is_loading = True
    render_page.refresh()

    all_items = []

    from sqlmodel import select
    from client_app.app.database.db import get_session
    from client_app.app.database.models import TriggerConfig, TriggerSubscription, FlowRegistry

    async with get_session() as session:
        v2_triggers_res = await session.exec(select(TriggerConfig))
        v2_triggers = v2_triggers_res.all()

        for trig in v2_triggers:
            # Map icon/color based on type
            icon = 'flash_on'
            color = 'teal'
            if trig.type == 'folder_watcher': icon, color = 'folder', 'amber'
            elif trig.type == 'email_watcher': icon, color = 'email', 'indigo'
            elif trig.type == 'web_watcher': icon, color = 'public', 'cyan'
            elif trig.type == 'scheduler': icon, color = 'schedule', 'purple'

            # Load subscribed flows with their is_active status
            subs_stmt = select(TriggerSubscription, FlowRegistry).join(
                FlowRegistry, TriggerSubscription.flow_id == FlowRegistry.id
            ).where(
                TriggerSubscription.trigger_id == trig.id,
                TriggerSubscription.is_active == True
            )
            subs_result = await session.exec(subs_stmt)
            subscribed_flows = []
            has_active_flows = False
            for sub, flow in subs_result.all():
                flow_is_active = getattr(flow, 'is_active', True)
                subscribed_flows.append({
                    'id': flow.id,
                    'name': flow.name,
                    'is_active': flow_is_active
                })
                if flow_is_active:
                    has_active_flows = True

            # Extract relevant config info based on type
            config = trig.configuration or {}

            # Check for direct email notification (web_watcher only)
            has_direct_notification = False
            if trig.type == 'web_watcher':
                has_direct_notification = config.get('send_email_on_change', False)

            if trig.type == 'email_watcher':
                cred_id = config.get('credential_id')
                folder = config.get('folder', 'INBOX')
                if cred_id:
                    from client_app.app.database.models import LocalCredentials
                    cred = await session.get(LocalCredentials, cred_id)
                    info = f"{cred.service_name if cred else '?'} / {folder}"
                else:
                    info = folder
            elif trig.type == 'web_watcher':
                url = config.get('url', '')
                interval = config.get('check_interval', 60)
                info = f"{url[:40]}... ({interval} min)" if len(url) > 40 else f"{url} ({interval} min)"
            elif trig.type == 'folder_watcher':
                path = config.get('path', config.get('watch_path', ''))
                info = path.split('\\')[-1] if '\\' in path else path.split('/')[-1] if '/' in path else path
            elif trig.type == 'scheduler':
                interval = config.get('interval', config.get('check_interval'))
                cron = config.get('cron')
                info = cron if cron else f"Cada {interval} min" if interval else "Programado"
            else:
                info = trig.description or trig.type

            # El status siempre se basa en is_active del trigger (control manual)
            trigger_status = trig.is_active

            # Determinar si el toggle debe estar habilitado:
            # - Habilitado si tiene flujos suscritos activos, O
            # - Es un web_watcher con notificación por email configurada
            can_toggle = has_active_flows or has_direct_notification

            all_items.append({
                'id': trig.id,
                'type': 'TRIGGER_V2',
                'subtype': trig.type,
                'name': trig.name,
                'info': info,
                'status': trigger_status,
                'can_toggle': can_toggle,
                'has_active_flows': has_active_flows,
                'last_active': trig.last_triggered.strftime('%d/%m %H:%M') if trig.last_triggered else state.i18n.t('triggers.last_active_na'),
                'raw': trig,
                'icon': icon,
                'color': color,
                'subscribed_flows': subscribed_flows,
                'has_direct_notification': has_direct_notification,
            })

    page_state.triggers = all_items

    # Calc stats
    page_state.stats['total'] = len(all_items)
    page_state.stats['active'] = sum(1 for t in all_items if t['status'])
    
    page_state.is_loading = False
    render_page.refresh()

async def handle_toggle_trigger(item_id: int, current_status: bool):
    """Maneja el toggle de activar/desactivar para cualquier disparador."""
    try:
        from client_app.app.services.trigger_lifecycle_manager import trigger_lifecycle_manager
        await trigger_lifecycle_manager.set_trigger_active(item_id, not current_status)
        ui.notify(state.i18n.t('triggers.status_updated'), type='positive')
        await load_all_triggers()
    except Exception as e:
        ui.notify(state.i18n.t('triggers.error_toggle', error=str(e)), type='negative')


async def handle_delete(trigger_type: str, item_id: Any):
    """Maneja eliminación de un disparador V2."""
    try:
        # Stop the trigger first
        from client_app.app.services.trigger_lifecycle_manager import trigger_lifecycle_manager
        await trigger_lifecycle_manager.set_trigger_active(item_id, False)

        # Delete from DB
        from client_app.app.database.db import get_session
        from client_app.app.database.models import TriggerConfig
        async with get_session() as session:
            trig = await session.get(TriggerConfig, item_id)
            if trig:
                await session.delete(trig)
                await session.commit()

        ui.notify(state.i18n.t('triggers.deleted_success'), type='positive')
        await load_all_triggers()
    except Exception as e:
        ui.notify(state.i18n.t('triggers.error_delete', error=str(e)), type='negative')

# --- PAGE UI ---

@ui.refreshable
def render_page():
    t = state.i18n.t
    # --- HEADER ---
    page_header(
        t('triggers.page_title'),
        t('triggers.page_desc'),
        classes='w-full gap-0 mb-3'
    )

    # --- SUPERVISION TABLE ---
    with ui.card().classes('w-full mb-4 p-0 overflow-hidden shadow-sm hover:shadow-md transition-shadow'):
        with ui.row().classes('w-full px-4 py-2 bg-slate-50 items-center justify-between border-b'):
            ui.label(t('triggers.table_title')).classes('font-semibold text-slate-700 text-sm')
            
            with ui.row().classes('gap-3'):
                # Total Card (Compact)
                with ui.row().classes('px-3 py-1 bg-slate-100 rounded-lg items-center gap-2 border border-slate-200'):
                    ui.icon('sensors', size='xs', color='primary')
                    ui.label(t('triggers.stats_total')).classes('text-xs font-bold text-slate-400 uppercase')
                    ui.label(str(page_state.stats['total'])).classes('text-sm font-bold text-slate-700')
                
                # Active Card (Compact)
                with ui.row().classes('px-3 py-1 bg-green-50 rounded-lg items-center gap-2 border border-green-100'):
                    ui.icon('check_circle', size='xs', color='green')
                    ui.label(t('triggers.stats_active')).classes('text-xs font-bold text-green-700 uppercase')
                    ui.label(str(page_state.stats['active'])).classes('text-sm font-bold text-green-800')
        
        if page_state.is_loading:
            with ui.column().classes('w-full p-4 items-center'):
                ui.spinner('dots', size='md', color='primary')
        elif not page_state.triggers:
            with ui.column().classes('w-full p-6 items-center text-slate-400'):
                ui.icon('notifications_off', size='2rem').classes('mb-1 opacity-50')
                ui.label(t('triggers.no_triggers')).classes('text-sm')
        else:
            # Table Header
            grid_cols = "50px 2fr 2fr 3fr 100px 80px"
            with ui.grid(columns=grid_cols).classes('w-full px-4 py-1 bg-slate-50 text-xs font-bold text-slate-500 border-b'):
                ui.label(t('triggers.col_type'))
                ui.label(t('triggers.col_name'))
                ui.label(t('triggers.col_config'))
                ui.label(t('triggers.col_status'))
                ui.label(t('triggers.col_activity'))
                ui.label(t('triggers.col_actions')).classes('text-right')

            # Table Rows
            for item in page_state.triggers:
                color_cls = f"text-{item['color']}-600"
                bg_cls = f"bg-{item['color']}-50"

                with ui.grid(columns=grid_cols).classes('w-full px-4 py-1 items-center border-b hover:bg-slate-50 transition-colors'):
                    # Type Icon
                    with ui.row().classes(f'w-8 h-8 rounded-full items-center justify-center {bg_cls}'):
                        ui.icon(item['icon']).classes(f'text-lg {color_cls}')

                    # Name
                    ui.label(item['name']).classes('font-medium text-slate-800 truncate')

                    # Config
                    with ui.row().classes('items-center gap-2'):
                        ui.label(item['info']).classes('text-xs font-mono text-slate-500 truncate')
                        # Direct notification indicator for web_watcher
                        if item.get('has_direct_notification'):
                            ui.icon('email', size='xs', color='cyan').tooltip(t('triggers.direct_notification'))

                    # Status column: Toggle + Flows badges para todos los triggers
                    with ui.row().classes('items-center gap-2 flex-wrap'):
                        # Mostrar flujos suscritos como badges
                        flows = item.get('subscribed_flows', [])
                        if flows:
                            for flow in flows[:2]:
                                flow_color = 'green' if flow.get('is_active', True) else 'grey'
                                ui.badge(flow['name'], color=flow_color).props('outline dense').classes('text-[10px]')
                            if len(flows) > 2:
                                ui.label(f"+{len(flows) - 2}").classes('text-[10px] text-slate-400')
                        else:
                            # Sin flujos: mostrar badge indicando
                            if item.get('has_direct_notification'):
                                # Web watcher con notificación directa
                                ui.badge(t('triggers.direct_email'), color='cyan').props('outline dense').classes('text-[10px]')
                            else:
                                ui.badge(t('triggers.no_flows'), color='grey').props('outline dense').classes('text-[10px]')

                    # Activity column: Toggle de activación
                    with ui.row().classes('items-center'):
                        can_toggle = item.get('can_toggle', False)
                        if can_toggle:
                            # Toggle habilitado: tiene flujos o es web_watcher con email
                            switch_color = item.get('color', 'primary')
                            ui.switch(
                                value=item['status'],
                                on_change=lambda e, i=item: handle_toggle_trigger(i['id'], i['status'])
                            ).props(f'dense color={switch_color}')
                        else:
                            # Toggle deshabilitado: necesita flujos suscritos
                            switch = ui.switch(value=False).props('dense disable color=grey')
                            switch.tooltip(t('triggers.toggle_disabled_tooltip'))

                    # Actions
                    with ui.row().classes('justify-end gap-1'):
                        ui.button(icon='edit', on_click=lambda i=item: handle_edit(i))\
                            .props('flat dense round color=grey')\
                            .tooltip(t('triggers.edit'))

                        def confirm_del(i=item):
                            with ui.dialog() as d, ui.card():
                                ui.label(t('triggers.confirm_del_title')).classes('font-bold')
                                with ui.row().classes('justify-end mt-4'):
                                    ui.button(t('common.cancel'), on_click=d.close).props('flat')
                                    async def do_delete():
                                        d.close()
                                        await handle_delete(i['type'], i['id'])
                                    ui.button(t('common.delete'), on_click=do_delete).props('unelevated color=red')
                            d.open()

                        ui.button(icon='delete', on_click=confirm_del)\
                            .props('flat dense round color=red')\
                            .tooltip(t('triggers.delete'))

    # --- ACTION GRID (New Trigger) ---
    ui.label(t('triggers.add_title')).classes('text-lg font-bold text-slate-700 mb-4')
    
    with ui.grid(columns=4).classes('w-full gap-4'):
        # Card Helper
        # Card Helper (Compact Version)
        def trigger_card(title, desc, icon, color, action):
            with ui.card().classes(f'w-full p-0 cursor-pointer hover:shadow-lg transition-all border-l-4 border-{color}-500 group').on('click', action):
                with ui.column().classes('w-full p-3 gap-1'):
                    # Row 1: Icon + Title
                    with ui.row().classes('items-center gap-3'):
                        with ui.column().classes(f'p-2 rounded-lg bg-{color}-50 group-hover:bg-{color}-100 transition-colors'):
                            ui.icon(icon, size='sm').classes(f'text-{color}-600')
                        ui.label(title).classes('font-bold text-slate-800 text-sm')
                    
                    # Row 2: Description (slightly indented or just below)
                    ui.label(desc).classes('text-xs text-slate-500 leading-tight ml-1')

        # 1. Folder
        trigger_card(
            t('triggers.folder_title'), 
            t('triggers.folder_desc'), 
            'folder', 'amber', 
            open_folder_page
        )
        
        # 2. Email
        trigger_card(
            t('triggers.email_title'), 
            t('triggers.email_desc'), 
            'email', 'indigo', 
            open_email_page
        )
        
        # 3. Web
        trigger_card(
            t('triggers.web_title'), 
            t('triggers.web_desc'), 
            'public', 'cyan', 
            open_web_page
        )
        
        # 4. Scheduler
        trigger_card(
            t('triggers.scheduler_title'), 
            t('triggers.scheduler_desc'), 
            'schedule', 'purple', 
            open_scheduler_page
        )

async def triggers_page():
    # Initial Load
    render_page()
    await load_all_triggers()
