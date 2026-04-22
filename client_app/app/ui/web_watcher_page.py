"""
Página de configuración del Monitor Web (Web Watcher).
Dispara flujos cuando detecta cambios en páginas web.
"""
from typing import Optional, Any
from nicegui import ui
from sqlmodel import select
from client_app.app.core.state import state
from client_app.app.services.web_watcher_service import web_watcher_service
from client_app.app.services.mail_watcher_service import mail_watcher_service
from client_app.app.database.models import FlowRegistry


from automatia_shared.enums import StepType
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.page_header import page_header

class WebWatcherPageState:
    def __init__(self):
        self.watchers = []
        self.flows = []
        self.smtp_credentials = []
        self.current_mode: str = 'library' # 'library' or 'design'

class WebWatcherDesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.url: str = ""
        self.selector: str = "body"
        self.selector_type: str = "css"  # css, xpath
        self.watch_mode: str = "selector"  # 'full_page' o 'selector'
        self.check_interval_min: int = 60
        self.is_saving: bool = False
        # Detailed content capture for diff
        self.capture_detailed_content: bool = False
        # Action fields
        self.trigger_workflow: bool = False # Deprecated in UI, kept for compatibility if needed internally
        self.flow_id: Optional[int] = None
        self.send_email_on_change: bool = False
        self.smtp_credential_id: Optional[int] = None
        self.notification_email: str = ""
        self.smtp_credentials: list = []

async def web_watcher_page(mode: str = 'library', watcher_id: Optional[int] = None):
    """Página principal del Monitor Web (Refactoreada a Drawer)."""
    t = state.i18n.t

    page_state = WebWatcherPageState()
    design_state = WebWatcherDesignState()
    save_btn = None
    
    # --- LOGIC ---

    async def load_design_data(watcher_id: int = None):
        # Cargar credenciales SMTP
        design_state.smtp_credentials = await mail_watcher_service.list_credentials(service_type="SMTP")

        if watcher_id:
            config = await web_watcher_service.load_config(watcher_id)
            if config:
                design_state.config_id = config['id']
                design_state.name = config.get('name', '')
                design_state.url = config['url']
                design_state.selector = config['selector']
                design_state.selector_type = config.get('selector_type', 'css')
                design_state.watch_mode = config.get('watch_mode', 'selector')
                design_state.check_interval_min = config.get('check_interval', 60)
                design_state.capture_detailed_content = config.get('capture_detailed_content', False)
                design_state.flow_id = config.get('workflow_id')
                design_state.trigger_workflow = config.get('trigger_workflow', False)
                design_state.send_email_on_change = config.get('send_email_on_change', False)
                design_state.smtp_credential_id = config.get('smtp_credential_id')
                design_state.notification_email = config.get('notification_email', '')

        else:
            # Reset
            design_state.config_id = None
            design_state.name = ""
            design_state.url = ""
            design_state.selector = "body"
            design_state.selector_type = "css"
            design_state.watch_mode = "selector"
            design_state.check_interval_min = 60
            design_state.capture_detailed_content = False
            design_state.flow_id = None
            design_state.trigger_workflow = False
            design_state.send_email_on_change = False
            design_state.smtp_credential_id = None
            design_state.notification_email = ""


    async def handle_save_config():
        if not design_state.url:
            ui.notify(t('web_watcher.url_required'), type='warning')
            return

        # Validar selector solo si está en modo selector
        if design_state.watch_mode == "selector" and not design_state.selector:
            ui.notify(t('web_watcher.selector_required'), type='warning')
            return

        # Validar según el tipo de acción seleccionada
        if design_state.send_email_on_change:
            if not design_state.smtp_credential_id:
                ui.notify(t('web_watcher.select_smtp'), type='warning')
                return
            if not design_state.notification_email:
                ui.notify(t('web_watcher.enter_email'), type='warning')
                return

        design_state.is_saving = True
        try:
            # Si es modo full_page, usar body como selector
            selector = "body" if design_state.watch_mode == "full_page" else design_state.selector
            selector_type = "css" if design_state.watch_mode == "full_page" else design_state.selector_type

            # Configurar acciones mutuamente excluyentes
            # Flow selection removed from UI - logic handled by subscription model
            trigger_workflow = False 
            send_email_on_change = design_state.send_email_on_change

            data = {
                "name": design_state.name,
                "url": design_state.url,
                "selector": selector,
                "selector_type": selector_type,
                "watch_mode": design_state.watch_mode,
                "check_interval": design_state.check_interval_min,
                "capture_detailed_content": design_state.capture_detailed_content,
                "trigger_workflow": False, # Always false from this UI
                "workflow_id": None,
                "send_email_on_change": send_email_on_change,
                "smtp_credential_id": design_state.smtp_credential_id if send_email_on_change else None,
                "notification_email": design_state.notification_email if send_email_on_change else None,
                "notify_on_change": True,
                "capture_screenshot": True,
                "is_active": True
            }

            if design_state.config_id:
                await web_watcher_service.update_config(design_state.config_id, data)
                config_id = design_state.config_id
            else:
                config_id = await web_watcher_service.create_config(data)
            
            # Sellado de Acción
            async with state.db_session() as session:
                from client_app.app.services.asset_finishing_service import AssetFinishingService
                finisher = AssetFinishingService(session)
                await finisher.seal_resource(config_id, StepType.WEB_WATCHER)
                await session.commit()

            ui.notify(t('web_watcher.saved'), type='positive')
            go_to_index()
        except Exception as e:
            ui.notify(f"Error: {e}", type='negative')
        finally:
            design_state.is_saving = False

    def go_to_index():
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
        ui.navigate.to('/triggers')

    async def enter_design(watcher_id: int = None):
        await load_design_data(watcher_id)
        layout_manager.enter_design_mode(StepType.WEB_WATCHER, atom_id=watcher_id)
        page_state.current_mode = 'design' # Usamos page_state local aunque deberíamos usar clase
        render_page.refresh()

    async def load_all():
        page_state.watchers = await web_watcher_service.list_configs()
        page_state.smtp_credentials = await mail_watcher_service.list_credentials(service_type="SMTP")
        async with state.db_session() as session:
            stmt = select(FlowRegistry).where(FlowRegistry.is_active == True)
            result = await session.execute(stmt)
            page_state.flows = result.scalars().all()
        render_page.refresh()

    async def toggle_watcher(watcher_id: int, active: bool):
        if active:
            success, msg = await web_watcher_service.start_watcher(watcher_id)
        else:
            success = await web_watcher_service.stop_watcher(watcher_id)
            
        if success:
            ui.notify(t('web_watcher.status_active') if active else t('web_watcher.status_stopped'), type='positive')
        else:
            ui.notify(t('web_watcher.error'), type='negative')
        await load_all()

    async def delete_watcher(watcher_id: int):
        success = await web_watcher_service.delete_config(watcher_id)
        if success:
            ui.notify(t('web_watcher.delete_success'), type='positive')
            await load_all()
        else:
            ui.notify(t('web_watcher.delete_error'), type='negative')

    def confirm_delete(watcher_id: int):
        with ui.dialog() as dlg, ui.card().classes('p-4'):
            ui.label(t('web_watcher.delete_confirm', default='¿Eliminar este monitor?')).classes('mb-4')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel'), on_click=dlg.close).props('flat')
                ui.button(t('common.delete', default='Eliminar'), on_click=lambda: (dlg.close(), delete_watcher(watcher_id))).props('color=negative')
        dlg.open()

    async def show_last_change(watcher_id: int, watcher_name: str):
        """Muestra un diálogo con el último cambio detectado (diff)."""
        history = await web_watcher_service.get_change_history(watcher_id, limit=1)

        with ui.dialog() as dlg, ui.card().classes('w-full max-w-2xl'):
            with ui.row().classes('w-full items-center justify-between p-4 border-b'):
                ui.label(t('web_watcher.last_change', name=watcher_name)).classes('text-lg font-bold')
                ui.button(icon='close', on_click=dlg.close).props('flat round dense')

            with ui.column().classes('w-full p-4 gap-3'):
                if not history:
                    with ui.row().classes('w-full justify-center py-8'):
                        ui.icon('history', size='3rem').classes('text-slate-300')
                    ui.label(t('web_watcher.no_history')).classes('text-center text-slate-500 w-full')
                else:
                    change = history[0]
                    detected_at = change['change_detected_at']
                    if hasattr(detected_at, 'strftime'):
                        detected_at = detected_at.strftime('%d/%m/%Y %H:%M:%S')

                    detected_at_str = t('web_watcher.detected_at', detected_at=detected_at)
                    ui.label(detected_at_str).classes('text-xs text-slate-500')

                    if change.get('diff_html'):
                        ui.label(t('web_watcher.changes_detected')).classes('text-sm font-medium text-slate-700 mt-2')
                        with ui.scroll_area().classes('w-full h-80 border rounded bg-slate-50 p-3'):
                            ui.html(change['diff_html'])
                    elif change.get('diff_text'):
                        ui.label(t('web_watcher.changes_detected')).classes('text-sm font-medium text-slate-700 mt-2')
                        with ui.scroll_area().classes('w-full h-80 border rounded bg-slate-50'):
                            ui.code(change['diff_text']).classes('text-xs')
                    else:
                        with ui.row().classes('w-full items-center gap-2 p-4 bg-amber-50 rounded'):
                            ui.icon('info', color='orange')
                            ui.label(t('web_watcher.no_diff_hint')).classes('text-sm text-amber-800')

                    if change.get('screenshot_path'):
                        with ui.expansion(t('web_watcher.view_screenshot'), icon='image').classes('w-full mt-2'):
                            ui.image(change['screenshot_path']).classes('w-full rounded')

        dlg.open()



    @ui.refreshable
    def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library': render_library()
            elif page_state.current_mode == 'design': render_design()
    
    def render_library():
        # Header
        with ui.row().classes('w-full items-center justify-between mb-6'):
            with ui.column():
                with ui.row().classes('items-center gap-2'):
                    ui.label(t('web_watcher.mon_web')).classes('text-3xl font-bold text-slate-800')
                    ui.badge('LEGACY', color='orange').props('outline').tooltip('Esta vista será eliminada. Usa el panel de Disparadores principal.')
                ui.label(t('web_watcher.mon_web_desc')).classes('text-slate-500')
            ui.button(t('web_watcher.new'), icon='add', on_click=lambda: enter_design()).props('unelevated color=primary')

        if not page_state.watchers:
             with ui.card().classes('w-full p-12 text-center bg-slate-50'):
                ui.icon('public_off', size='4rem').classes('text-slate-300 mb-4')
                ui.label(t('web_watcher.empty')).classes('text-xl text-slate-500 mb-2')
                ui.label(t('web_watcher.empty_hint')).classes('text-slate-400')
             return

        # Tabla de monitores
        with ui.card().classes('w-full'):
            columns = [
                {'name': 'url', 'label': t('web_watcher.col_url'), 'field': 'url', 'align': 'left'},
                {'name': 'selector', 'label': t('web_watcher.col_selector'), 'field': 'selector', 'align': 'left'},
                {'name': 'interval', 'label': t('web_watcher.col_interval'), 'field': 'interval', 'align': 'center'},
                {'name': 'status', 'label': t('web_watcher.col_status'), 'field': 'status', 'align': 'center'},
                {'name': 'last_check', 'label': t('web_watcher.col_last_check'), 'field': 'last_check', 'align': 'left'},
                {'name': 'actions', 'label': t('web_watcher.col_actions'), 'field': 'actions', 'align': 'right'},
            ]

            rows = []
            for w in page_state.watchers:
                url_short = w['url'][:50] + '...' if len(w['url']) > 50 else w['url']
                last_check = w['last_checked_at'].strftime('%d/%m/%Y %H:%M') if w.get('last_checked_at') else '-'
                rows.append({
                    'id': w['id'],
                    'url': url_short,
                    'url_full': w['url'],
                    'selector': w['selector'][:30],
                    'interval': f"{w['check_interval']} min",
                    'status': t('web_watcher.status_active') if w['is_active'] else t('web_watcher.status_stopped'),
                    'is_active': w['is_active'],
                    'last_check': last_check,
                    'raw': w
                })

            table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')

            table.add_slot('body-cell-status', '''
                <q-td :props="props">
                    <q-badge :color="props.row.is_active ? 'green' : 'grey'">
                        {{ props.row.status }}
                    </q-badge>
                </q-td>
            ''')

            table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn flat dense icon="difference" color="info"
                           @click="$parent.$emit('view_diff', props.row)"
                           :title="t('web_watcher.view_last_change')" />
                    <q-btn v-if="props.row.is_active" flat dense icon="stop" color="negative"
                           @click="$parent.$emit('stop', props.row)" />
                    <q-btn v-else flat dense icon="play_arrow" color="positive"
                           @click="$parent.$emit('start', props.row)" />
                    <q-btn flat dense icon="edit" color="primary"
                           @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat dense icon="delete" color="negative"
                           @click="$parent.$emit('delete', props.row)" />
                </q-td>
            ''')

            table.on('stop', lambda e: toggle_watcher(e.args['id'], False))
            table.on('start', lambda e: toggle_watcher(e.args['id'], True))
            table.on('edit', lambda e: enter_design(e.args['raw']['id']))
            table.on('delete', lambda e: confirm_delete(e.args['id']))
            table.on('view_diff', lambda e: show_last_change(e.args['id'], e.args['raw'].get('name', 'Monitor')))

    def update_save_button():
        """Actualiza el estado del botón de guardar."""
        nonlocal save_btn
        if save_btn:
            # Validación base: URL requerida
            is_valid = bool(design_state.url)

            # Validar selector si está en modo selector
            if design_state.watch_mode == "selector":
                is_valid = is_valid and bool(design_state.selector)

            # Validar e-mail si está activado
            if design_state.send_email_on_change:
                is_valid = is_valid and bool(design_state.smtp_credential_id) and bool(design_state.notification_email)

            save_btn.set_visibility(True)
            save_btn.enable() if is_valid else save_btn.disable()

    def open_mode_help():
        """Abre el drawer con ayuda sobre los modos de vigilancia."""
        url = design_state.url or '[URL no especificada]'
        layout_manager.open_drawer_with_message(
            f"Explícame las diferencias entre vigilancia de página completa y selector para esta URL: {url}"
        )

    def open_selector_help():
        """Abre el drawer con ayuda para obtener selectores."""
        layout_manager.open_drawer_with_message(
            "Ayúdame a encontrar el selector CSS/XPath para el elemento que quiero vigilar. ¿Cómo puedo usar el inspector del navegador (F12)?"
        )

    def on_watch_mode_change(e):
        """Maneja el cambio de modo de vigilancia."""
        design_state.watch_mode = 'full_page' if e.value else 'selector'
        update_save_button()
        try:
            render_page.refresh()
        except:
            pass

    def render_design():
        nonlocal save_btn

        with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
            page_header(
                t('web_watcher.title'),
                t('web_watcher.subtitle')
            )

            # CAMPO URL - Compacto y a ancho completo
            ui.input(label=t('web_watcher.url_label'), placeholder='https://example.com', on_change=update_save_button)\
                .classes('w-full font-mono text-sm')\
                .props('outlined clearable dense')\
                .bind_value(design_state, 'url')

            with ui.grid(columns=2).classes('w-full gap-4'):
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('web_watcher.config')).classes('text-base font-bold mb-2')

                        # Nombre del monitor
                        ui.input(label=t('web_watcher.name'), placeholder=t('web_watcher.name_placeholder'))\
                            .classes('w-full text-sm mb-1')\
                            .props('outlined dense')\
                            .bind_value(design_state, 'name')

                        # Switch de modo principal
                        with ui.row().classes('w-full items-center gap-3 my-1'):
                            ui.switch(t('web_watcher.watch_full_page'),
                                      value=design_state.watch_mode == 'full_page',
                                      on_change=on_watch_mode_change).classes('text-sm')

                            help_text = t('web_watcher.full_page_help') if design_state.watch_mode == 'full_page' else t('web_watcher.selector_help')
                            ui.button(icon='help_outline', on_click=open_mode_help)\
                                .props('flat round dense size=sm').tooltip(help_text)

                        # Campos de selector (solo visibles en modo selector)
                        if design_state.watch_mode == "selector":
                            with ui.row().classes('w-full items-center justify-between mt-1 mb-1'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.label(t('web_watcher.col_selector')).classes('text-[10px] font-bold text-slate-400 uppercase')
                                    ui.toggle(['css', 'xpath'], on_change=update_save_button).classes('text-[10px]').bind_value(design_state, 'selector_type').props('no-caps flat dense outline')
                                
                                ui.button(icon='help_outline', on_click=open_selector_help)\
                                    .props('flat round dense size=sm').tooltip(t('web_watcher.selector_help_tooltip', default='No sé cómo obtener el selector'))

                            ui.input(t('web_watcher.col_selector'), placeholder='#price o //div[@class="content"]', on_change=update_save_button)\
                                .classes('w-full font-mono text-sm').props('dense outlined')\
                                .bind_value(design_state, 'selector')

                        # Intervalo siempre visible
                        ui.number(t('web_watcher.col_interval'), value=60, min=5).classes('w-full text-sm mt-1').props('dense outlined')\
                            .bind_value(design_state, 'check_interval_min')

                        # Toggle para captura detallada
                        with ui.row().classes('w-full items-center gap-2 mt-2 pt-1 border-t border-slate-100'):
                            ui.switch(t('web_watcher.capture_detailed')).classes('text-sm')\
                                .bind_value(design_state, 'capture_detailed_content')
                            ui.icon('info_outline', size='xs').classes('text-slate-400')\
                                .tooltip(t('web_watcher.capture_detailed_hint'))

                with ui.column().classes('gap-4'):
                    # --- ACCIONES ---
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        # OPCIÓN: DISPONIBILIDAD (INFORMACIÓN)
                        with ui.row().classes('w-full gap-2 mb-2 pb-2 border-b border-slate-100 items-start'):
                            ui.icon('hub').classes('text-slate-400 text-xl mt-0.5')
                            with ui.column().classes('gap-0'):
                                ui.label(t('web_watcher.watcher_availability_title', 'Disponibilidad para flujos')).classes('text-sm font-bold text-slate-700')
                                ui.label(t('web_watcher.watcher_availability_desc', 'Este monitor estará disponible como disparador en tus flujos. Configura la suscripción desde el editor de flujos.')).classes('text-xs text-slate-500 leading-tight')

                        ui.label(t('web_watcher.action_on_change')).classes('text-base font-bold mb-3')

                        # OPCIÓN: ENVIAR EMAIL (FAST TRACK)
                        with ui.column().classes('w-full gap-2'):
                            ui.checkbox(t('web_watcher.send_email_on_change')).bind_value(design_state, 'send_email_on_change').on_value_change(update_save_button).classes('text-sm font-bold')

                            # Campos de Email (visibles solo si activado)
                            with ui.column().classes('w-full pl-7 gap-3 mt-1').bind_visibility_from(design_state, 'send_email_on_change'):
                                    ui.label(t('web_watcher.email_settings')).classes('text-xs font-medium text-slate-500')

                                    # Selector de cuenta SMTP
                                    smtp_options = {c['id']: c.get('name', c.get('service_name', f"SMTP #{c['id']}")) for c in design_state.smtp_credentials}
                                    ui.select(smtp_options, label=t('web_watcher.smtp_account'), on_change=update_save_button)\
                                        .classes('w-full text-sm').props('dense outlined')\
                                        .bind_value(design_state, 'smtp_credential_id')

                                    # Email destinatario
                                    ui.input(label=t('web_watcher.notification_email'), placeholder='usuario@ejemplo.com', on_change=update_save_button)\
                                        .classes('w-full text-sm').props('dense outlined type=email')\
                                        .bind_value(design_state, 'notification_email')


                    with ui.row().classes('w-full justify-end gap-2 mt-4 items-center'):
                        ui.button(t('common.cancel'), on_click=go_to_index).props('flat color=slate text-sm')
                        save_btn = ui.button(t('common.save'), icon='save', on_click=handle_save_config)\
                            .props('unelevated color=primary shadow text-sm')
                        update_save_button()


    # --- INITIALIZATION ---
    await load_all()

    # Manejar modo inicial antes del primer renderizado
    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
        # Cargar config del flujo o del URL
        effective_watcher_id = flow_config_id or watcher_id
        if effective_watcher_id:
            await load_design_data(effective_watcher_id)
        layout_manager.enter_design_mode(StepType.WEB_WATCHER, from_flow=True)
    elif mode == 'design':
        page_state.current_mode = 'design'
        await load_design_data(watcher_id)
        layout_manager.enter_design_mode(StepType.WEB_WATCHER, atom_id=watcher_id)
    else:
        layout_manager.exit_focus_mode()

    render_page()

