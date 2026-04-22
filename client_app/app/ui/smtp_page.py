import asyncio
from typing import Optional, List, Dict, Any
from nicegui import ui
from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.mail_watcher_service import mail_watcher_service
from client_app.app.ui.components.data_source_selector import render_data_source_selector, DataSourceSelection, DataSourceSelectorState
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.unified_resource_card import unified_resource_card
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme
from client_app.app.ui.components.page_header import page_header

# --- STATE ---

# --- STATE ---

class SMTPPageState:
    def __init__(self):
        self.current_mode: str = 'library' # library, design, execution
        self.saved_actions: List[Dict[str, Any]] = []
        self.smtp_accounts: List[Dict[str, Any]] = []
        self.is_loading: bool = False

class DesignState:
    def __init__(self):
        self.action_id: Optional[int] = None
        self.name: str = ""
        self.credential_id: Optional[int] = None
        self.to: str = ""
        self.subject: str = ""
        self.body: str = ""
        self.attachments: str = ""
        self.is_html: bool = False
        self.is_testing: bool = False
        self.test_result: Optional[tuple] = None # (success, message)

class ExecutionState:
    def __init__(self):
        self.action_id: Optional[int] = None
        self.name: str = ""
        self.credential_id: Optional[int] = None
        self.to: str = ""
        self.subject: str = ""
        self.body: str = ""
        self.is_running: bool = False
        self.execution_result: Optional[tuple] = None
        # Adjuntos desde el selector de fuentes
        self.attachment_source: Optional[DataSourceSelection] = None
        self.attachments: List[str] = []  # Lista de paths de archivos adjuntos
        self.data_source_selector_state = DataSourceSelectorState()

# --- PAGE IMPLEMENTATION ---

async def smtp_page(atom_id: Optional[int] = None):
    page_state = SMTPPageState()
    design_state = DesignState()
    exec_state = ExecutionState()
    colors = AtomColorScheme.get_colors(StepType.EMAIL_SEND)
    t = state.i18n.t

    async def load_data():
        page_state.is_loading = True
        render_page.refresh()
        # Load SMTP Actions (these are the 'sending templates')
        page_state.saved_actions = await mail_watcher_service.list_credentials(service_type="SMTP_SEND")
        # Load Centralized SMTP Accounts
        page_state.smtp_accounts = await mail_watcher_service.list_credentials(service_type="SMTP")
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
        layout_manager.enter_design_mode(StepType.EMAIL_SEND)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def edit_action(atom_id: int):
        action_data = await mail_watcher_service.get_credential(atom_id)
        # Find name in list
        name = ""
        for a in page_state.saved_actions:
            if a['id'] == atom_id:
                name = a['name']
                break

        if action_data:
            design_state.action_id = atom_id
            design_state.name = name
            design_state.credential_id = action_data.get('credential_id')
            design_state.to = action_data.get('to', '')
            design_state.subject = action_data.get('subject', '')
            design_state.body = action_data.get('body', '')
            design_state.attachments = action_data.get('attachments', '')
            design_state.is_html = action_data.get('is_html', False)
            
            layout_manager.enter_design_mode(StepType.EMAIL_SEND, atom_id=atom_id)
            page_state.current_mode = 'design'
            render_page.refresh()

    async def start_execution(atom_id: int):
        exec_state.__init__()
        exec_state.atom_id = atom_id
        action_data = await mail_watcher_service.get_credential(atom_id)
        
        for a in page_state.saved_actions:
            if a['id'] == atom_id:
                exec_state.name = a['name']
                break
        
        if action_data:
            exec_state.credential_id = action_data.get('credential_id')
            exec_state.to = action_data.get('to', '')
            exec_state.subject = action_data.get('subject', '')
            exec_state.body = action_data.get('body', '')

        layout_manager.enter_execution_mode(atom_id=atom_id)
        page_state.current_mode = 'execution'
        render_page.refresh()

    async def handle_test_connection():
        if not design_state.credential_id:
            ui.notify("Selecciona una cuenta SMTP primero", type='warning')
            return

        design_state.is_testing = True
        design_state.test_result = None
        render_page.refresh()
        
        try:
            success, msg = await mail_watcher_service.test_smtp_connection(design_state.credential_id)
            design_state.test_result = (success, msg)
            if success:
                ui.notify(t('smtp.test_success', "Conexión SMTP exitosa"), type='positive')
            else:
                ui.notify(t('smtp.test_error', f"Error de conexión: {msg}"), type='negative')
        except Exception as e:
            design_state.test_result = (False, str(e))
            ui.notify(f"Error: {e}", type='negative')
        finally:
            design_state.is_testing = False
            render_page.refresh()

    async def handle_save():
        if not design_state.name:
            ui.notify(t('atoms.name_required'), type='warning')
            return
        if not design_state.credential_id:
            ui.notify(t('smtp.account_required', "Debes seleccionar una cuenta de correo"), type='warning')
            return

        try:
            # Auto-format attachments string to ensure it has {{}} if user forgot
            attachments = (design_state.attachments or "").strip()
            if attachments and not (attachments.startswith('{{') and attachments.endswith('}}')):
                # Remove any stray braces they might have typed like {var}
                clean_name = attachments.replace('{', '').replace('}', '').strip()
                if clean_name:
                    design_state.attachments = f"{{{{{clean_name}}}}}"

            # We store the atom config in LocalCredentials with service_type="SMTP_SEND"
            # The 'encrypted_data' field will contain a JSON with all personalization.
            atom_config = {
                "credential_id": design_state.credential_id,
                "to": design_state.to,
                "subject": design_state.subject,
                "body": design_state.body,
                "attachments": design_state.attachments,
                "is_html": design_state.is_html
            }
            
            # Using mail_watcher_service.save_credential but overloading it a bit 
            # or we can use update_credential if action_id exists.
            
            if design_state.action_id:
                # Update existing
                from client_app.app.modules.security.encryption_service import EncryptionService
                encryption = EncryptionService()
                encrypted_data = encryption.encrypt(atom_config)
                
                async with mail_watcher_service.AsyncSession(mail_watcher_service.client_engine) as session:
                    from client_app.app.database.models import LocalCredentials
                    cred = await session.get(LocalCredentials, design_state.action_id)
                    if cred:
                        cred.service_name = f"smtp_send_{design_state.name}"
                        cred.encrypted_data = encrypted_data
                        cred.updated_at = mail_watcher_service.datetime.utcnow()
                        await session.commit()
            else:
                # New atom
                await mail_watcher_service.save_credential(
                    name=design_state.name,
                    server="", # Dummy, not used for SMTP_SEND
                    port=0,    # Dummy
                    username="", # Dummy
                    password="", # Dummy
                    use_ssl=False, # Dummy
                    service_type="SMTP_SEND"
                )
                # Need to update the data as save_credential creates a standard structure
                # This is a bit hacky but works with existing service without modifying it too much.
                async with mail_watcher_service.AsyncSession(mail_watcher_service.client_engine) as session:
                    from client_app.app.database.models import LocalCredentials
                    from sqlalchemy import select
                    stmt = select(LocalCredentials).where(LocalCredentials.service_name == f"smtp_send_{design_state.name}").order_by(LocalCredentials.id.desc())
                    result = await session.exec(stmt)
                    new_cred = result.first()
                    if new_cred:
                        from client_app.app.modules.security.encryption_service import EncryptionService
                        encryption = EncryptionService()
                        new_cred.encrypted_data = encryption.encrypt(atom_config)
                        await session.commit()

            ui.notify(t('smtp.config_saved', "Configuración de envío guardada"), type='positive')
            go_to_library()
            await load_data()
        except Exception as e:
            ui.notify(t('smtp.save_error', f"Error al guardar: {e}"), type='negative')

    async def handle_send_test():
        exec_state.is_running = True
        exec_state.execution_result = None
        render_page.refresh()
        
        try:
            from client_app.app.modules.output.email_sender import EmailSender
            from client_app.app.modules.security.encryption_service import EncryptionService
            
            # Procesar adjuntos antes de enviar
            attachments = []
            if exec_state.attachment_source:
                sel = exec_state.attachment_source
                if sel.source_type == 'manual':
                    if sel.file_content:
                        attachments.append({
                            "data": sel.file_content,
                            "name": sel.file_name or "attachment.bin"
                        })
                    elif getattr(sel, 'file_path', None):
                        import pathlib
                        p = pathlib.Path(sel.file_path)
                        if p.exists() and p.is_file():
                            attachments.append({
                                "data": p.read_bytes(),
                                "name": p.name
                            })
                elif sel.source_type in ['flow_step', 'catalog']:
                    selector_state = exec_state.data_source_selector_state
                    if selector_state and hasattr(selector_state, 'preview_data') and selector_state.preview_data:
                        # Extract files from preview_data
                        preview = selector_state.preview_data
                        if 'path' in getattr(preview, 'columns', []):
                            for row in getattr(preview, 'rows', []):
                                file_path = row.get('path', '')
                                if file_path:
                                    import pathlib
                                    p = pathlib.Path(file_path)
                                    if p.exists() and p.is_file():
                                        attachments.append({
                                            "data": p.read_bytes(),
                                            "name": p.name
                                        })

            # Get account credentials
            creds = await mail_watcher_service.get_credential(exec_state.credential_id)
            if not creds:
                raise Exception("Cuenta SMTP no encontrada")
                
            encryption = EncryptionService()
            
            smtp_config = {
                "server": creds['server'],
                "port": creds['port'],
                "username": creds['user'],
                "password": creds['password']
            }
            
            sender = EmailSender(smtp_config, encryption)
            message_id = await asyncio.to_thread(
                sender.send,
                from_addr=creds['user'],
                to_addrs=[exec_state.to],
                subject=exec_state.subject,
                body=exec_state.body,
                html=False,
                attachments=attachments
            )
            
            exec_state.execution_result = (True, f"Email enviado. Message-ID: {message_id}")
            ui.notify(t('smtp.test_email_sent', "Email de prueba enviado"), type='positive')
        except Exception as e:
            exec_state.execution_result = (False, str(e))
            ui.notify(f"Falla en envío: {e}", type='negative')
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
        
        resources = []
        for action in page_state.saved_actions:
            resources.append({
                'id': action['id'],
                'name': action['name'],
                'description': f"Configuración de envío para: {action['name']}",
                'status': 'published',
                'source_module': 'smtp',
                'doc_path': None,
                'created_at': action.get('created_at'),
                'is_favorite': False,
                '_original': action
            })

        layout = StandardPageLayout(
            title=t('smtp.title'),
            source_module='smtp',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_action(r['id']),
            on_delete=lambda r: delete_action_confirm(r['_original']),
            on_execute=lambda r: start_execution(r['id']),
            help_description=t('smtp.help'),
            input_contract=['to', 'subject', 'body', 'attachments'],
            output_contract=['sent_status', 'message_id']
        )
        layout.render()

    def delete_action_confirm(action):
        with ui.dialog() as d, ui.card():
            ui.label(t('smtp.delete_confirm_title', f'¿Eliminar configuración de envío "{action["name"]}"?')).classes('text-lg font-bold')
            ui.label(t('smtp.delete_confirm_hint', 'Solo se eliminará esta plantilla de envío. La cuenta de correo seguirá configurada en el sistema.'))
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel'), on_click=d.close).props('flat')
                async def do_delete():
                    await mail_watcher_service.delete_credential(action['id'])
                    ui.notify(t('smtp.deleted', "Configuración eliminada"))
                    d.close()
                    await load_data()
                ui.button(t('common.delete'), on_click=do_delete).props('unelevated color=red')
        d.open()

    def render_design():
        with ui.column().classes('w-full flex-grow overflow-y-auto gap-4 mb-4'):
            with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
                page_header(
                    t('smtp.title') if not design_state.action_id else t('api.edit_title', name=design_state.name),
                    t('smtp.subtitle')
                )
                
                with ui.grid(columns=2).classes('w-full gap-4'):
                    # Columna 1: Selección de Cuenta y Nombre
                    with ui.column().classes('gap-4'):
                        with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                            ui.label(t('smtp.origin_name')).classes('text-base font-bold mb-2')
                            ui.input(t('atoms.field_name'), placeholder='Ej: Notificación Reporte Diario').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'name')
                            
                            options = {acc['id']: f"{acc['name']} ({acc.get('user', 'SMTP')})" for acc in page_state.smtp_accounts}
                            ui.select(options, label=t('smtp.email_account')).classes('w-full').props('dense outlined').bind_value(design_state, 'credential_id')
                            
                            if not options:
                                with ui.row().classes('w-full p-2 bg-amber-50 rounded border border-amber-100 items-center justify-between mt-2'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('warning', color='warning', size='xs')
                                        ui.label(t('common.no_connections')).classes('text-[10px] text-amber-700')
                                    ui.button(t('common.configure'), on_change=lambda: ui.navigate.to('/config?tab=Conexiones')).props('flat dense color=amber text-[10px]')

                        if design_state.test_result:
                            success, msg = design_state.test_result
                            status_bg = 'bg-green-50 border-green-100 text-green-700' if success else 'bg-red-50 border-red-100 text-red-700'
                            with ui.card().classes(f'w-full p-3 shadow-none border {status_bg}'):
                                ui.label('Resultado' if success else 'Error').classes('text-[10px] font-bold uppercase mb-1')
                                ui.label(msg).classes('text-[10px] font-mono leading-tight')

                    # Columna 2: Personalización del mensaje
                    with ui.column().classes('gap-4'):
                        with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                            ui.label(t('smtp.template')).classes('text-base font-bold mb-2')
                            ui.input(t('smtp.recipients'), placeholder='ejemplo@correo.com (opcional)').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'to')
                            ui.input(t('smtp.subject'), placeholder='Gov Gen AI: Nuevo reporte disponible').classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'subject')
                            ui.textarea(t('smtp.body'), placeholder='Estimado cliente, adjuntamos...').classes('w-full text-sm').props('dense outlined rows=6').bind_value(design_state, 'body')
                            
                            with ui.row().classes('w-full gap-4 items-center mt-2'):
                                ui.input('Adjuntos (variable generada)', placeholder='archivos_generados').classes('flex-grow text-sm').props('dense outlined').bind_value(design_state, 'attachments')\
                                    .tooltip('El sistema añadirá las llaves {{}} automáticamente si no las pones. Ej: reporte_final')
                                ui.checkbox('Enviar como HTML').bind_value(design_state, 'is_html').classes('text-sm shrink-0 whitespace-nowrap')
        # Unified Footer
        with ui.column().classes('w-full max-w-4xl mx-auto mt-auto'):
            with ui.row().classes('w-full justify-between items-center pt-6 border-t border-slate-100 mb-8'):
                # Left: Diagnostics
                with ui.row().classes('items-center gap-4'):
                    ui.label(t('common.diagnostics')).classes('text-sm font-bold text-slate-700')
                    ui.button(t('common.test_connection'), icon='science', on_click=handle_test_connection).props('unelevated color=emerald-600 dense shadow-sm')\
                        .bind_enabled_from(design_state, 'is_testing', backward=lambda x: not x)
                    
                    if design_state.is_testing:
                        ui.spinner(size='sm', color='emerald-600')

                # Right: Actions
                with ui.row().classes('items-center gap-2'):
                    ui.button(t('common.cancel'), on_click=go_to_library).props('flat color=slate text-sm')
                    ui.button(t('smtp.save_action', "GUARDAR ACCIÓN"), icon='save', on_click=handle_save).props('unelevated color=primary shadow text-sm square')

    def render_execution():
        with ui.column().classes('w-full max-w-2xl mx-auto gap-6'):
            with ui.row().classes('w-full items-center justify-between bg-teal-900 p-6 rounded-2xl text-white'):
                ui.label(t('smtp.send_test', name=exec_state.name)).classes('text-xl font-bold')
                ui.button(icon='close', on_click=go_to_library).props('flat color=white')

            with ui.card().classes('w-full p-6'):
                ui.label(t('smtp.send_test_desc')).classes('text-slate-500 mb-4')
                ui.input(t('smtp.recipients'), placeholder='usuario@ejemplo.com').classes('w-full').bind_value(exec_state, 'to')
                ui.input(t('smtp.subject')).classes('w-full').bind_value(exec_state, 'subject')
                ui.textarea(t('smtp.body')).classes('w-full').bind_value(exec_state, 'body').props('outlined')

                # Sección de adjuntos
                with ui.expansion(t('smtp.attachments'), icon='attach_file').classes('w-full mt-4'):
                    def handle_attachment_selection(selection: DataSourceSelection):
                        exec_state.attachment_source = selection
                        if selection.source_type == 'manual' and selection.file_path:
                            exec_state.attachments = [selection.file_path]
                            ui.notify(f'Adjunto: {selection.file_name}', type='info')
                        elif selection.source_type == 'catalog':
                            ui.notify(t('smtp.attachment_from_action', f'Adjunto desde acción: {selection.atom_name}'), type='info')
                        elif selection.source_type == 'flow_step':
                            ui.notify(f'Adjunto del paso: {selection.step_name}', type='info')

                    render_data_source_selector(
                        consumer_type=StepType.EMAIL_SEND,
                        on_source_selected=handle_attachment_selection,
                        flow_context=state.flow_context,
                        initial_selection=exec_state.attachment_source,
                        selector_state_override=exec_state.data_source_selector_state,
                        compact=True
                    )

                ui.button(f"🚀 {t('smtp.send_now')}", on_click=handle_send_test).props('unelevated color=teal fullwidth').classes('mt-4').bind_enabled_from(exec_state, 'is_running', backward=lambda x: not x)

                if exec_state.is_running:
                    ui.spinner().classes('mx-auto mt-4')

                if exec_state.execution_result:
                    success, msg = exec_state.execution_result
                    with ui.row().classes(f'w-full p-4 mt-4 rounded {"bg-green-50 text-green-700" if success else "bg-red-50 text-red-700"} items-center gap-2'):
                        ui.icon('check_circle' if success else 'error')
                        ui.label(msg).classes('text-sm font-medium')

    # --- INITIAL LAYOUT SETUP ---
    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.EMAIL_SEND, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif atom_id:
        # Se cargará después en edit_action
        pass
    else:
        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()

    # --- INITIALIZATION ---
    await load_data()
    render_page()

    if flow_config_id:
        await edit_action(flow_config_id)
    elif atom_id and not (state.flow_context and state.flow_context.get('mode') == 'contextual'):
        await edit_action(atom_id)

    return render_page
