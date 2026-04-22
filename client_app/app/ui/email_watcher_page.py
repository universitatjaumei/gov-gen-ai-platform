"""
Página de configuración del Monitor de Email (Mail Watcher).
Dispara flujos cuando se reciben correos de una cuenta IMAP.
"""
import re
from typing import Optional, Any, List, Dict
from nicegui import ui

# Regex simple para validar formato de email
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
from client_app.app.core.state import state
from client_app.app.services.mail_watcher_service import mail_watcher_service
from automatia_shared.enums import StepType
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.page_header import page_header

class EmailWatcherPageState:
    def __init__(self):
        self.watchers = []
        self.credentials = []
        self.current_mode: str = 'library' # 'library' or 'design'

class EmailWatcherDesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.credential_id: Optional[int] = None
        self.folder: str = "INBOX"
        self.check_interval_min: int = 5
        self.subject_filter: str = ""
        self.whitelist_senders: str = ""
        self.process_attachments: bool = False
        self.allowed_extensions: str = ""
        self.is_saving: bool = False
        self.credentials: List[Dict] = []

async def email_watcher_page(mode: str = 'library', watcher_id: Optional[int] = None):
    """Página principal del Monitor de Email."""
    t = state.i18n.t

    page_state = EmailWatcherPageState()
    design_state = EmailWatcherDesignState()
    save_btn = None
    
    # --- LOGIC ---

    async def load_design_data(watcher_id: int = None):
        # Cargar credenciales
        design_state.credentials = await mail_watcher_service.list_credentials(service_type="IMAP")

        if watcher_id:
            config = await mail_watcher_service.get_config(watcher_id)
            if config:
                design_state.config_id = config['id']
                design_state.name = config.get('name', '')
                design_state.credential_id = config.get('credential_id')
                design_state.folder = config.get('folder', 'INBOX')
                design_state.check_interval_min = config.get('check_interval', 5)
                design_state.subject_filter = config.get('subject_filter', '')
                design_state.whitelist_senders = '\n'.join(config.get('whitelist_senders', []) or [])
                design_state.process_attachments = config.get('process_attachments', False)
                design_state.allowed_extensions = ','.join(config.get('allowed_extensions', []) or [])
        else:
            # Reset
            design_state.config_id = None
            design_state.name = ""
            design_state.credential_id = None
            design_state.folder = "INBOX"
            design_state.check_interval_min = 5
            design_state.subject_filter = ""
            design_state.whitelist_senders = ""
            design_state.process_attachments = False
            design_state.allowed_extensions = ""

    async def handle_save_config():
        if not design_state.credential_id:
            ui.notify(t('email_watcher.select_account'), type='warning')
            return

        # Validar formato de emails en whitelist
        whitelist_emails = [s.strip() for s in design_state.whitelist_senders.split('\n') if s.strip()]
        invalid_emails = [email for email in whitelist_emails if not EMAIL_REGEX.match(email)]
        if invalid_emails:
            ui.notify(
                t('email_watcher.invalid_email_format', default='Formato de email inválido: {emails}').format(emails=', '.join(invalid_emails)),
                type='warning'
            )
            return

        design_state.is_saving = True
        try:
            data = {
                "name": design_state.name,
                "credential_id": design_state.credential_id,
                "folder": design_state.folder,
                "check_interval": design_state.check_interval_min,
                "subject_filter": design_state.subject_filter,
                "whitelist_senders": whitelist_emails,
                "process_attachments": design_state.process_attachments,
                "allowed_extensions": [e.strip() for e in design_state.allowed_extensions.split(',') if e.strip()]
            }

            if design_state.config_id:
                await mail_watcher_service.update_config(design_state.config_id, data)
                config_id = design_state.config_id
            else:
                config_id = await mail_watcher_service.create_config(data)

            # Sello Atómico
            async with state.db_session() as session:
                from client_app.app.services.asset_finishing_service import AssetFinishingService
                finisher = AssetFinishingService(session)
                await finisher.seal_resource(config_id, StepType.EMAIL_WATCHER)
                await session.commit()

            ui.notify(t('email_watcher.saved'), type='positive')
            go_to_index()
        except Exception as e:
            design_state.is_saving = False
            ui.notify(t('common.error_msg', default='Error: {error}').format(error=str(e)), type='negative')

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

        ui.navigate.to('/triggers')

    async def enter_design(watcher_id: int = None):
        await load_design_data(watcher_id)
        layout_manager.enter_design_mode(StepType.EMAIL_WATCHER, atom_id=watcher_id)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def handle_test_connection():
        """Prueba la conexión IMAP."""
        if not design_state.credential_id:
            ui.notify(t('email_watcher.select_account'), type='warning')
            return

        success, msg = await mail_watcher_service.test_connection(design_state.credential_id)
        if success:
            ui.notify(t('common.test_connection_success', default="Conexión exitosa"), type='positive')
        else:
            ui.notify(t('common.test_connection_error', default="Error de conexión: {error}").format(error=msg), type='negative')

    async def load_all():
        page_state.watchers = await mail_watcher_service.list_configs()
        page_state.credentials = await mail_watcher_service.list_credentials(service_type="IMAP")
        render_page.refresh()

    async def delete_watcher(watcher_id: int):
        success = await mail_watcher_service.delete_config(watcher_id)
        if success:
            ui.notify(t('email_watcher.delete_success'), type='positive')
            await load_all()
        else:
            ui.notify(t('email_watcher.delete_error'), type='negative')

    def confirm_delete(watcher_id: int):
        with ui.dialog() as dlg, ui.card().classes('p-4'):
            ui.label(t('email_watcher.delete_confirm')).classes('mb-4')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel'), on_click=dlg.close).props('flat')
                ui.button(t('common.delete', default='Eliminar'), on_click=lambda: (dlg.close(), delete_watcher(watcher_id))).props('color=negative')
        dlg.open()

    def update_save_button():
        nonlocal save_btn
        if save_btn:
            is_valid = bool(design_state.credential_id)
            save_btn.set_visibility(True)
            save_btn.enable() if is_valid else save_btn.disable()

    @ui.refreshable
    def render_preview():
        """Muestra una vista previa compacta."""
        with ui.expansion(t('email_watcher.summary'), icon='preview').classes('w-full border rounded-lg text-sm').props('header-class=text-slate-500'):
            with ui.card().classes('w-full p-4 bg-slate-50 border-none shadow-none'):
                if design_state.credential_id:
                    cred_name = next((c['name'] for c in design_state.credentials if c['id'] == design_state.credential_id), "N/A")
                    ui.label(t('email_watcher.account')).classes('text-[10px] font-bold text-slate-400 uppercase')
                    ui.label(f"{cred_name} -> {design_state.folder}").classes('text-xs mb-2')
                    
                    if design_state.subject_filter:
                        ui.label(t('email_watcher.subject_filter_label')).classes('text-[10px] font-bold text-slate-400 uppercase')
                        ui.label(design_state.subject_filter).classes('text-xs mb-2 font-mono')
                else:
                    ui.label(t('email_watcher.config_hint')).classes('text-slate-400 italic text-xs text-center w-full')

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
                    ui.label(t('email_watcher.mon_email')).classes('text-3xl font-bold text-slate-800')
                    ui.badge('LEGACY', color='orange').props('outline').tooltip('Esta vista será eliminada. Usa el panel de Disparadores principal.')
                ui.label(t('email_watcher.mon_email_desc')).classes('text-slate-500')
            ui.button(t('email_watcher.new_mon'), icon='add', on_click=lambda: enter_design()).props('unelevated color=primary')

        if not page_state.watchers:
             with ui.card().classes('w-full p-12 text-center bg-slate-50'):
                ui.icon('mail', size='4rem').classes('text-slate-300 mb-4')
                ui.label(t('email_watcher.no_mon')).classes('text-xl text-slate-500 mb-2')
                ui.label(t('email_watcher.no_mon_hint')).classes('text-slate-400')
             return

        # Tabla de monitores
        with ui.card().classes('w-full'):
            columns = [
                {'name': 'name', 'label': t('common.name'), 'field': 'name', 'align': 'left'},
                {'name': 'folder', 'label': t('email_watcher.col_folder'), 'field': 'folder', 'align': 'left'},
                {'name': 'interval', 'label': t('email_watcher.col_interval'), 'field': 'check_interval', 'align': 'center'},
                {'name': 'status', 'label': t('email_watcher.col_status'), 'field': 'is_active', 'align': 'center'},
                {'name': 'actions', 'label': t('email_watcher.col_actions'), 'field': 'actions', 'align': 'right'},
            ]

            rows = []
            for w in page_state.watchers:
                rows.append({
                    'id': w['id'],
                    'name': w['name'],
                    'folder': w.get('folder', 'INBOX'),
                    'check_interval': f"{w.get('check_interval', '?')} min",
                    'is_active': w['is_active'],
                    'raw': w
                })

            table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')

            table.add_slot('body-cell-status', '''
                <q-td :props="props">
                    <q-badge :color="props.row.is_active ? 'green' : 'grey'">
                        {{ props.row.is_active ? t('email_watcher.status_active') : t('email_watcher.status_stopped') }}
                    </q-badge>
                </q-td>
            ''')

            table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn flat dense icon="edit" color="primary"
                           @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat dense icon="delete" color="negative"
                           @click="$parent.$emit('delete', props.row)" />
                </q-td>
            ''')

            table.on('edit', lambda e: enter_design(e.args['raw']['id']))
            table.on('delete', lambda e: confirm_delete(e.args['id']))

    def render_design():
        nonlocal save_btn
        
        with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
            page_header(
                t('email_watcher.title'),
                t('email_watcher.subtitle')
            )

            with ui.grid(columns=2).classes('w-full gap-4'):
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('email_watcher.main_config')).classes('text-base font-bold mb-2')

                        ui.input(label=t('common.name'), placeholder='Ej: Facturas proveedores')\
                            .classes('w-full text-sm mb-3')\
                            .props('outlined dense')\
                            .bind_value(design_state, 'name')

                        creds_options = {c['id']: c['name'] for c in design_state.credentials}
                        with ui.row().classes('w-full items-center gap-2'):
                            ui.select(creds_options, label=t('email_watcher.account'), on_change=update_save_button).classes('flex-grow w-0').props('dense outlined').bind_value(design_state, 'credential_id')
                            ui.button(icon='science', on_click=handle_test_connection) \
                                .props('unelevated color=emerald-600 dense').classes('shadow-sm') \
                                .tooltip(t('common.test_connection', default='Probar conexión')) \
                                .bind_enabled_from(design_state, 'credential_id', backward=bool)
                            ui.button(icon='add', on_click=lambda: ui.navigate.to('/config?tab=Conexiones')).props('flat round dense color=primary').tooltip(t('email_watcher.new_conn'))

                        ui.input(t('email_watcher.folder_name'), value='INBOX').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'folder')
                        ui.number(t('email_watcher.check_interval'), value=5, min=1).classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'check_interval_min')

                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                         ui.label(t('email_watcher.attachments_proc')).classes('text-base font-bold mb-2')
                         ui.checkbox(t('email_watcher.proc_attachments')).bind_value(design_state, 'process_attachments')
                         
                         with ui.column().bind_visibility_from(design_state, 'process_attachments'):
                             ui.input(t('email_watcher.allowed_ext'), placeholder='pdf, xlsx, docx').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'allowed_extensions')
                             ui.label(t('email_watcher.allowed_ext_hint')).classes('text-xs text-slate-400 italic')


                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('email_watcher.filters')).classes('text-base font-bold mb-2')
                        ui.input(t('email_watcher.subject_filter'), placeholder='Ej: [FACTURA]').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'subject_filter')
                        ui.textarea(t('email_watcher.whitelist_senders'), placeholder='admin@empresa.com').classes('w-full font-mono text-xs').bind_value(design_state, 'whitelist_senders').props('outlined dense')

                    # Vista Previa
                    render_preview()

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
        layout_manager.enter_design_mode(StepType.EMAIL_WATCHER, from_flow=True)
    elif mode == 'design':
        page_state.current_mode = 'design'
        await load_design_data(watcher_id)
        layout_manager.enter_design_mode(StepType.EMAIL_WATCHER, atom_id=watcher_id)
    else:
        layout_manager.exit_focus_mode()

    render_page()
