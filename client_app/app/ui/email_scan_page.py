"""
EmailScanPage - Configuración del Átomo de Recolección de Emails

Página para configurar el átomo EMAIL_SCAN que busca correos por criterio
y descarga adjuntos (escaneo puntual, no monitoreo continuo).

Incluye:
- Biblioteca: Lista de configuraciones guardadas
- Diseño: Editor de configuración con filtros avanzados
- Bandeja: Vista de correos descargados con acciones masivas

Parte de la Fase 2 del Plan de Refactorización de Taxonomía.
"""
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from nicegui import ui

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.email_scan_service import (
    email_scan_service,
    EmailSearchCriteria,
    EmailScanResult,
)
from client_app.app.services.mail_watcher_service import mail_watcher_service
from client_app.app.services.received_emails_service import received_emails_service
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme


# --- STATE CLASSES ---

class EmailScanPageState:
    def __init__(self):
        self.current_mode: str = 'library'  # library, design, inbox
        self.credentials: List[Dict[str, Any]] = []
        self.saved_configs: List[Dict[str, Any]] = []
        self.is_loading: bool = False


class DesignState:
    def __init__(self):
        self.config_id: Optional[int] = None
        self.name: str = ""
        self.credential_id: Optional[int] = None
        self.folder: str = "INBOX"
        # Filtros de búsqueda
        self.subject_contains: str = ""
        self.from_address: str = ""
        self.to_address: str = ""  # NUEVO: filtro por destinatario
        # Fechas
        self.since_days: int = 7
        self.date_from: str = datetime.now().strftime('%Y-%m-%d')
        self.date_to: str = datetime.now().strftime('%Y-%m-%d')
        self.use_date_range: bool = False
        # Opciones de filtro
        self.has_attachments: bool = False  # Cambiado a False por defecto
        self.max_emails: int = 50
        # Opciones de contenido a descargar (NUEVO)
        self.save_body_plain: bool = True
        self.save_body_html: bool = False
        self.download_attachments: bool = True
        self.persist_to_db: bool = True  # Guardar en BD para informes/LLM
        # Acciones post-procesamiento
        self.mark_as_read: bool = False
        # Estado interno
        self.is_saving: bool = False


class TestState:
    def __init__(self):
        self.is_running: bool = False
        self.result: Optional[EmailScanResult] = None
        self.error: Optional[str] = None


class InboxState:
    """Estado para la vista de Bandeja de correos."""
    def __init__(self):
        self.emails: List[Any] = []
        self.selected_ids: set = set()
        self.selected_email: Optional[Any] = None  # Email seleccionado para detalle
        self.is_loading: bool = False
        self.stats: Dict[str, int] = {}
        self.credential_id: Optional[int] = None  # Cuenta IMAP seleccionada
        # Filtros
        self.use_last_days: bool = True  # True = últimos X días, False = rango de fechas
        self.filter_last_days: int = 30  # Últimos X días
        self.filter_date_from: str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        self.filter_date_to: str = datetime.now().strftime('%Y-%m-%d')
        self.filter_source: str = "all"  # all, scan, watcher
        self.filter_status: str = "all"  # all, processed, pending
        self.filter_search: str = ""
        self.filter_sender: str = ""  # Filtro por remitente


# --- PAGE IMPLEMENTATION ---

async def email_scan_page():
    """Página principal del átomo EmailScan."""
    page_state = EmailScanPageState()
    design_state = DesignState()
    test_state = TestState()
    inbox_state = InboxState()
    colors = AtomColorScheme.get_colors(StepType.EMAIL_SCAN)
    t = state.i18n.t

    # --- HELPER FUNCTIONS ---

    def format_date(dt: datetime) -> str:
        """Formatea fecha para mostrar."""
        if not dt:
            return ""
        return dt.strftime('%d/%m/%Y %H:%M')

    def truncate(text: str, max_len: int = 50) -> str:
        """Trunca texto con elipsis."""
        if not text:
            return ""
        return text[:max_len] + "..." if len(text) > max_len else text

    # --- LOAD FUNCTIONS ---

    async def load_configs():
        """Carga las configuraciones guardadas de EmailScan."""
        from client_app.app.services.atom_service import atom_service
        page_state.is_loading = True
        render_page.refresh()
        atoms = await atom_service.list_atoms(atom_type=StepType.EMAIL_SCAN)
        page_state.saved_configs = [
            {
                'id': a.id, 'name': a.name, 'atom_type': a.atom_type,
                'config': json.loads(a.default_config) if a.default_config else {},
                'updated_at': a.updated_at, 'status': a.status,
            }
            for a in atoms
        ]
        page_state.is_loading = False
        render_page.refresh()

    async def load_credentials():
        """Carga las credenciales de email disponibles."""
        page_state.credentials = await mail_watcher_service.list_credentials(service_type='IMAP')

    async def load_inbox_emails():
        """Carga los emails de la bandeja según filtros."""
        inbox_state.is_loading = True
        inbox_state.selected_email = None
        render_inbox.refresh()

        try:
            # Determinar fechas según modo
            if inbox_state.use_last_days:
                date_from = (datetime.now() - timedelta(days=inbox_state.filter_last_days)).date()
                date_to = datetime.now().date()
            else:
                date_from = datetime.strptime(inbox_state.filter_date_from, '%Y-%m-%d').date() if inbox_state.filter_date_from else None
                date_to = datetime.strptime(inbox_state.filter_date_to, '%Y-%m-%d').date() if inbox_state.filter_date_to else None

            # Determinar filtro de origen
            source = None
            if inbox_state.filter_source == 'scan':
                source = 'scan'
            elif inbox_state.filter_source == 'watcher':
                source = 'watcher'

            # Determinar filtro de procesados
            include_processed = True
            if inbox_state.filter_status == 'pending':
                include_processed = False

            emails = await received_emails_service.get_emails_by_date_range(
                date_from=date_from,
                date_to=date_to,
                source=source,
                include_processed=include_processed,
                limit=200
            )

            # Filtro adicional por estado "procesado" (si solo queremos procesados)
            if inbox_state.filter_status == 'processed':
                emails = [e for e in emails if e.is_processed]

            # Filtro por remitente
            if inbox_state.filter_sender:
                sender_lower = inbox_state.filter_sender.lower()
                emails = [e for e in emails if sender_lower in (e.sender or '').lower()]

            # Filtro de búsqueda por texto (asunto)
            if inbox_state.filter_search:
                search_lower = inbox_state.filter_search.lower()
                emails = [e for e in emails if search_lower in (e.subject or '').lower()]

            inbox_state.emails = emails
            inbox_state.selected_ids = set()

            # Cargar estadísticas
            inbox_state.stats = await received_emails_service.get_stats()

        except Exception as ex:
            ui.notify(f"Error cargando emails: {ex}", type='negative')
            inbox_state.emails = []
        finally:
            inbox_state.is_loading = False
            render_inbox.refresh()

    # --- NAVIGATION ---

    def go_to_library():
        """Vuelve a la biblioteca o al flujo si viene de uno."""
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

    def go_to_inbox():
        """Navega a la bandeja de correos."""
        page_state.current_mode = 'inbox'
        import asyncio
        asyncio.create_task(load_inbox_emails())
        render_page.refresh()

    async def start_new_design():
        """Inicia nuevo diseño de configuración."""
        design_state.__init__()
        await load_credentials()
        layout_manager.enter_design_mode(StepType.EMAIL_SCAN)
        page_state.current_mode = 'design'
        render_page.refresh()

    # --- DESIGN MODE HANDLERS ---

    async def handle_test_scan():
        """Ejecuta un escaneo de prueba con los parámetros actuales."""
        if not design_state.credential_id:
            ui.notify("Selecciona una cuenta de correo", type='warning')
            return

        test_state.is_running = True
        test_state.result = None
        test_state.error = None
        render_page.refresh()

        try:
            # Construir criterios de búsqueda
            since_date = None
            before_date = None

            if design_state.use_date_range:
                if design_state.date_from:
                    since_date = datetime.strptime(design_state.date_from, '%Y-%m-%d')
                if design_state.date_to:
                    before_date = datetime.strptime(design_state.date_to, '%Y-%m-%d') + timedelta(days=1)
            else:
                if design_state.since_days > 0:
                    since_date = datetime.now() - timedelta(days=design_state.since_days)

            criteria = EmailSearchCriteria(
                subject_contains=design_state.subject_contains or None,
                from_address=design_state.from_address or None,
                to_address=design_state.to_address or None,
                since_date=since_date,
                before_date=before_date,
                has_attachments=design_state.has_attachments if design_state.has_attachments else None,
                folder=design_state.folder,
                max_emails=min(design_state.max_emails, 10),  # Limitar en prueba
                mark_as_read=False,  # Nunca marcar en prueba
            )

            result = await email_scan_service.scan_emails(
                connection_id=design_state.credential_id,
                criteria=criteria,
                download_attachments=design_state.download_attachments,
                persist_to_db=False,  # No persistir en prueba
            )

            test_state.result = result

            if result.success:
                ui.notify(
                    f"Encontrados {result.total_emails} emails, {result.total_attachments} adjuntos",
                    type='positive'
                )
            else:
                test_state.error = result.error
                ui.notify(f"Error: {result.error}", type='negative')

        except Exception as e:
            test_state.error = str(e)
            ui.notify(f"Error: {e}", type='negative')
        finally:
            test_state.is_running = False
            render_page.refresh()

    async def handle_test_connection():
        """Prueba la conexión IMAP."""
        if not design_state.credential_id:
            ui.notify("Selecciona una cuenta de correo", type='warning')
            return

        success, msg = await mail_watcher_service.test_connection(design_state.credential_id)
        if success:
            ui.notify("Conexión exitosa", type='positive')
        else:
            ui.notify(f"Error de conexión: {msg}", type='negative')

    async def edit_atom(atom):
        """Edita una configuración existente."""
        await load_credentials()
        design_state.__init__()
        design_state.config_id = atom.get('id') if isinstance(atom, dict) else atom.id
        design_state.name = atom.get('name') if isinstance(atom, dict) else atom.name
        config = atom.get('config') if isinstance(atom, dict) else {}
        if config:
            design_state.credential_id = config.get('credential_id')
            design_state.folder = config.get('folder', 'INBOX')
            design_state.subject_contains = config.get('subject_contains', '')
            design_state.from_address = config.get('from_address', '')
            design_state.to_address = config.get('to_address', '')
            design_state.since_days = config.get('since_days', 7)
            design_state.has_attachments = config.get('has_attachments', False)
            design_state.max_emails = config.get('max_emails', 50)
            design_state.download_attachments = config.get('download_attachments', True)
            design_state.mark_as_read = config.get('mark_as_read', False)
            design_state.use_date_range = config.get('use_date_range', False)
            design_state.date_from = config.get('date_from', design_state.date_from)
            design_state.date_to = config.get('date_to', design_state.date_to)
            # Nuevos campos
            design_state.save_body_plain = config.get('save_body_plain', True)
            design_state.save_body_html = config.get('save_body_html', False)
            design_state.persist_to_db = config.get('persist_to_db', True)
        layout_manager.enter_design_mode(StepType.EMAIL_SCAN, atom_id=design_state.config_id)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def delete_atom(atom):
        """Elimina una configuración."""
        from client_app.app.services.atom_service import atom_service
        atom_id = atom.get('id') if isinstance(atom, dict) else atom.id
        await atom_service.delete_atom(atom_id)
        ui.notify(t('atoms.deleted', 'Acción eliminada'), type='positive')
        await load_configs()

    async def handle_save():
        """Valida y guarda la configuración del átomo."""
        if not design_state.credential_id:
            ui.notify("Selecciona una cuenta de correo", type='warning')
            return

        if design_state.is_saving:
            return

        design_state.is_saving = True
        render_page.refresh()

        try:
            from client_app.app.services.atom_service import atom_service

            config = {
                'credential_id': design_state.credential_id,
                'folder': design_state.folder,
                'subject_contains': design_state.subject_contains,
                'from_address': design_state.from_address,
                'to_address': design_state.to_address,
                'since_days': design_state.since_days,
                'has_attachments': design_state.has_attachments,
                'max_emails': design_state.max_emails,
                'download_attachments': design_state.download_attachments,
                'mark_as_read': design_state.mark_as_read,
                'use_date_range': design_state.use_date_range,
                'date_from': design_state.date_from,
                'date_to': design_state.date_to,
                # Nuevos campos
                'save_body_plain': design_state.save_body_plain,
                'save_body_html': design_state.save_body_html,
                'persist_to_db': design_state.persist_to_db,
            }

            # Schema para Flow Editor
            schema = {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "title": "Carpeta", "description": "Carpeta IMAP (ej: INBOX)"},
                    "subject_contains": {"type": "string", "title": "Asunto contiene", "description": "Filtrar por texto en el asunto"},
                    "from_address": {"type": "string", "title": "Remitente", "description": "Filtrar por dirección del remitente"},
                    "to_address": {"type": "string", "title": "Destinatario", "description": "Filtrar por dirección del destinatario"},
                    "since_days": {"type": "integer", "title": "Histórico (días)", "description": "Buscar en los últimos X días", "minimum": 1},
                    "max_emails": {"type": "integer", "title": "Límite de correos", "minimum": 1, "maximum": 500},
                    "has_attachments": {"type": "boolean", "title": "Solo con adjuntos", "description": "Filtrar correos con archivos"},
                    "download_attachments": {"type": "boolean", "title": "Descargar archivos", "description": "Bajar adjuntos a local"},
                    "save_body_plain": {"type": "boolean", "title": "Guardar cuerpo texto", "description": "Guardar cuerpo en texto plano"},
                    "save_body_html": {"type": "boolean", "title": "Guardar cuerpo HTML", "description": "Guardar cuerpo en HTML"},
                    "persist_to_db": {"type": "boolean", "title": "Persistir en BD", "description": "Guardar emails en base de datos"},
                    "mark_as_read": {"type": "boolean", "title": "Marcar como leído", "description": "Tras el procesamiento"}
                }
            }

            atom_name = design_state.name or f'Email Scan - {design_state.folder}'

            if design_state.config_id:
                await atom_service.update_atom(
                    atom_id=design_state.config_id,
                    name=atom_name,
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config),
                    status='PUBLISHED'
                )
                ui.notify('Configuración actualizada', type='positive')
            else:
                new_atom = await atom_service.create_atom(
                    name=atom_name,
                    atom_type=StepType.EMAIL_SCAN,
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config),
                    status='PUBLISHED'
                )
                design_state.config_id = new_atom.id if new_atom else None
                if state.flow_context and state.flow_context.get('mode') == 'contextual':
                    step = state.flow_context.get('step')
                    if step and design_state.config_id:
                        step.config['config_id'] = design_state.config_id
                ui.notify('Configuración guardada', type='positive')

            go_to_library()
            await load_configs()

        except Exception as e:
            ui.notify(f'Error: {e}', type='negative')
        finally:
            design_state.is_saving = False
            render_page.refresh()

    # --- INBOX MODE HANDLERS ---

    def toggle_email_selection(email_id: int):
        """Alterna la selección de un email."""
        if email_id in inbox_state.selected_ids:
            inbox_state.selected_ids.remove(email_id)
        else:
            inbox_state.selected_ids.add(email_id)
        render_inbox.refresh()

    def toggle_select_all():
        """Selecciona o deselecciona todos los emails visibles."""
        if len(inbox_state.selected_ids) == len(inbox_state.emails):
            inbox_state.selected_ids = set()
        else:
            inbox_state.selected_ids = {e.id for e in inbox_state.emails}
        render_inbox.refresh()

    def select_email_for_detail(email):
        """Selecciona un email para ver en detalle."""
        inbox_state.selected_email = email
        render_inbox.refresh()

    def close_detail():
        """Cierra la vista de detalle."""
        inbox_state.selected_email = None
        render_inbox.refresh()

    async def handle_mark_processed():
        """Marca los emails seleccionados como procesados."""
        if not inbox_state.selected_ids:
            ui.notify("Selecciona al menos un email", type='warning')
            return

        try:
            count = await received_emails_service.mark_as_processed(list(inbox_state.selected_ids))
            ui.notify(f"{count} email(s) marcados como procesados", type='positive')
            await load_inbox_emails()
        except Exception as ex:
            ui.notify(f"Error: {ex}", type='negative')

    async def handle_delete_selected():
        """Elimina los emails seleccionados."""
        if not inbox_state.selected_ids:
            ui.notify("Selecciona al menos un email", type='warning')
            return

        try:
            count = 0
            for email_id in list(inbox_state.selected_ids):
                if await received_emails_service.delete_email(email_id):
                    count += 1
            ui.notify(f"{count} email(s) eliminados", type='positive')
            await load_inbox_emails()
        except Exception as ex:
            ui.notify(f"Error: {ex}", type='negative')

    async def handle_save_as_atom():
        """Guarda los filtros actuales de la bandeja como un átomo reutilizable."""
        if not (inbox_state.filter_sender or inbox_state.filter_search):
            ui.notify("Selecciona un filtro de remitente o asunto para guardar", type='warning')
            return

        # Mostrar diálogo para configurar el átomo
        atom_name = {'value': ''}

        async def save_atom():
            if not atom_name['value']:
                ui.notify("Ingresa un nombre para la acción", type='warning')
                return

            try:
                from client_app.app.services.atom_service import atom_service

                # Construir configuración desde los filtros de la bandeja
                config = {
                    'credential_id': inbox_state.credential_id,
                    'use_date_range': not inbox_state.use_last_days,
                    'since_days': inbox_state.filter_last_days if inbox_state.use_last_days else 30,
                    'date_from': inbox_state.filter_date_from,
                    'date_to': inbox_state.filter_date_to,
                    'from_address': inbox_state.filter_sender,
                    'subject_contains': inbox_state.filter_search,
                    'has_attachments': False,
                    'max_emails': 50,
                    'download_attachments': True,
                    'save_body_plain': True,
                    'save_body_html': False,
                    'persist_to_db': True,
                    'mark_as_read': False,
                }

                # Schema para Flow Editor
                schema = {
                    "type": "object",
                    "properties": {
                        "since_days": {"type": "integer", "title": "Últimos días", "minimum": 1},
                        "from_address": {"type": "string", "title": "Remitente"},
                        "subject_contains": {"type": "string", "title": "Asunto contiene"},
                        "max_emails": {"type": "integer", "title": "Máx. emails", "minimum": 1},
                        "has_attachments": {"type": "boolean", "title": "Solo con adjuntos"},
                        "download_attachments": {"type": "boolean", "title": "Descargar adjuntos"},
                        "persist_to_db": {"type": "boolean", "title": "Persistir en BD"},
                    }
                }

                await atom_service.create_atom(
                    name=atom_name['value'],
                    atom_type=StepType.EMAIL_SCAN,
                    config_schema=json.dumps(schema),
                    default_config=json.dumps(config),
                    status='PUBLISHED'
                )

                ui.notify(f"Acción '{atom_name['value']}' creada correctamente", type='positive')
                dialog.close()

                # Recargar configuraciones y cambiar a biblioteca
                await load_configs()
                page_state.current_mode = 'library'
                render_page.refresh()

            except Exception as ex:
                ui.notify(f"Error: {ex}", type='negative')

        with ui.dialog() as dialog, ui.card().classes('w-full max-w-md'):
            with ui.column().classes('w-full gap-4 p-4'):
                ui.label('Guardar filtros como acción').classes('text-lg font-bold text-primary')
                ui.label('Crea una acción reutilizable con los filtros actuales para usar en flujos.').classes('text-sm text-slate-500')

                ui.input('Nombre de la acción', placeholder='Ej: Correos de facturas últimos 7 días') \
                    .classes('w-full').props('outlined') \
                    .on('update:model-value', lambda e: atom_name.update({'value': e.args}))

                # Resumen de filtros
                with ui.card().classes('w-full p-3 bg-slate-50 border'):
                    ui.label('Filtros a guardar:').classes('text-xs font-bold text-slate-500 uppercase mb-2')
                    with ui.column().classes('gap-1'):
                        if inbox_state.use_last_days:
                            ui.label(f"• Últimos {inbox_state.filter_last_days} días").classes('text-xs')
                        else:
                            ui.label(f"• Desde: {inbox_state.filter_date_from} hasta: {inbox_state.filter_date_to}").classes('text-xs')
                        if inbox_state.filter_sender:
                            ui.label(f"• Remitente: {inbox_state.filter_sender}").classes('text-xs')
                        if inbox_state.filter_search:
                            ui.label(f"• Asunto contiene: {inbox_state.filter_search}").classes('text-xs')

                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Cancelar', on_click=dialog.close).props('flat')
                    ui.button('Guardar acción', icon='save', on_click=save_atom).props('unelevated color=primary')

        dialog.open()

    async def handle_inbox_test_connection():
        """Prueba la conexión IMAP en la bandeja de correos."""
        if not inbox_state.credential_id:
            ui.notify("Selecciona una conexión IMAP", type='warning')
            return

        success, msg = await mail_watcher_service.test_connection(inbox_state.credential_id)
        if success:
            ui.notify("Conexión exitosa", type='positive')
        else:
            ui.notify(f"Error de conexión: {msg}", type='negative')

    # --- RENDERERS ---

    def render_mode_tabs():
        """Renderiza los botones de navegación entre modos."""
        with ui.row().classes('gap-1 bg-slate-100 rounded-lg p-1'):
            btn_library = ui.button('Biblioteca', icon='folder',
                                    on_click=lambda: (setattr(page_state, 'current_mode', 'library'), render_page.refresh()))
            btn_library.props('flat dense' if page_state.current_mode != 'library' else 'unelevated dense color=primary')

            btn_inbox = ui.button('Bandeja', icon='inbox', on_click=go_to_inbox)
            btn_inbox.props('flat dense' if page_state.current_mode != 'inbox' else 'unelevated dense color=primary')

    @ui.refreshable
    def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library':
                render_library()
            elif page_state.current_mode == 'design':
                render_design()
            elif page_state.current_mode == 'inbox':
                render_inbox()

    def render_library():
        """Renderiza la biblioteca de configuraciones."""
        from client_app.app.ui.components.unified_resource_card import unified_resource_card, get_resource_styles

        resources = page_state.saved_configs
        styles = get_resource_styles('email')
        color = styles['color']

        with ui.column().classes('w-full max-w-7xl mx-auto gap-6'):
            # Header con tabs integrados
            with ui.row().classes('w-full items-start justify-between'):
                with ui.column().classes('gap-0'):
                    ui.label(t('email_scan.title')).classes('text-3xl font-bold text-primary mb-1')
                    ui.label(t('email_scan.subtitle')).classes('text-slate-500 text-base')
                render_mode_tabs()

            # Filtros y acciones
            with ui.row().classes('w-full items-center justify-between gap-4'):
                with ui.row().classes('flex-grow items-center gap-4'):
                    ui.input(placeholder=t('index_page.search_placeholder', 'Buscar por nombre...')) \
                        .props('dense outlined icon=search').classes('w-64 bg-white')
                    ui.select(
                        {'all': t('index_page.filter_all', 'Todos los estados'),
                         'published': t('index_page.filter_published', 'Publicados'),
                         'draft': t('index_page.filter_draft', 'Borradores')},
                        value='all'
                    ).props('dense outlined options-dense').classes('w-48 bg-white')

                ui.button(t('index_page.create_button', 'Crear Nuevo'), icon='add', on_click=start_new_design) \
                    .style(f'background-color: {color}; color: white;').props('unelevated')

            # Grid de recursos
            if not resources:
                with ui.card().classes('w-full p-12 text-center bg-slate-50'):
                    ui.icon('email', size='xl', color='amber')
                    ui.label(f"No hay elementos en {t('email_scan.title')}").classes('text-lg font-medium text-slate-600 mt-4')
                    ui.label('Crea el primero para comenzar a trabajar').classes('text-slate-400')
            else:
                with ui.grid(columns=3).classes('w-full gap-6'):
                    for res in resources:
                        unified_resource_card(
                            resource=res,
                            on_click=lambda r=res: edit_atom(r),
                            on_edit=lambda r=res: edit_atom(r),
                            on_delete=lambda r=res: delete_atom(r)
                        )

    def render_design():
        """Renderiza el formulario de diseño/configuración."""
        with ui.column().classes('w-full max-w-5xl mx-auto gap-4'):
            # Header
            with ui.row().classes('w-full items-center gap-4'):
                ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
                with ui.column().classes('gap-0'):
                    ui.label(t('email_scan.designer_title', 'Configurar Escaneo')).classes('text-3xl font-bold text-primary mb-1')
                    ui.label(t('email_scan.designer_subtitle', 'Define los criterios de búsqueda y opciones de descarga')).classes('text-slate-500 text-base')

            with ui.grid(columns=2).classes('w-full gap-4'):
                # --- COLUMNA 1: Conexión y Diagnóstico ---
                with ui.column().classes('gap-4'):
                    # Card Configuración
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('common.configuration', 'Configuración')).classes('text-base font-bold mb-2')

                        ui.input(t('common.atom_name', 'Nombre'), placeholder='Ej: Escaneo de facturas') \
                            .classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'name')

                        creds_options = {c['id']: c['name'] for c in page_state.credentials}
                        ui.select(creds_options, label=t('email_scan.imap_account', 'Cuenta IMAP')) \
                            .classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'credential_id')

                        if not creds_options:
                            with ui.row().classes('w-full items-center justify-between p-2 bg-amber-50 rounded border border-amber-100 text-amber-700 mt-2'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('warning', size='xs')
                                    ui.label(t('common.no_connections', 'No hay conexiones configuradas')).classes('text-[10px] font-medium')
                                ui.button(t('common.configure', 'Configurar'),
                                          on_click=lambda: ui.navigate.to('/config?tab=Conexiones')).props('flat dense color=amber text-[10px]')

                        ui.input(t('email_scan.folder_label', 'Carpeta IMAP'), placeholder='INBOX') \
                            .classes('w-full text-sm font-mono').props('dense outlined').bind_value(design_state, 'folder')

                    # Card Diagnóstico
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('common.diagnostics', 'Diagnóstico')).classes('text-base font-bold mb-2')

                        with ui.row().classes('w-full gap-2'):
                            ui.button(t('email_scan.test_scan', 'Probar escaneo'), icon='science',
                                      on_click=handle_test_scan).props('unelevated color=amber-600 text-sm') \
                                .bind_enabled_from(test_state, 'is_running', backward=lambda x: not x).classes('flex-grow')
                            ui.button(t('email_scan.test_connection', 'Probar conexión'),
                                      on_click=handle_test_connection).props('outline color=amber-600 text-sm').classes('flex-grow')

                        # Resultados de prueba
                        if test_state.result and test_state.result.success:
                            with ui.card().classes('w-full p-3 mt-3 shadow-none border bg-amber-50 border-amber-100 text-amber-900'):
                                with ui.row().classes('w-full justify-around'):
                                    with ui.column().classes('items-center'):
                                        ui.label(str(test_state.result.total_emails)).classes('text-xl font-bold')
                                        ui.label(t('email_scan.emails_count', 'Emails')).classes('text-[10px] uppercase')
                                    with ui.column().classes('items-center'):
                                        ui.label(str(test_state.result.total_attachments)).classes('text-xl font-bold')
                                        ui.label(t('email_scan.attachments_count', 'Adjuntos')).classes('text-[10px] uppercase')

                                if test_state.result.emails:
                                    ui.separator().classes('my-2')
                                    with ui.scroll_area().classes('w-full h-40'):
                                        for email in test_state.result.emails[:10]:
                                            with ui.column().classes('gap-0 mb-2 opacity-80'):
                                                ui.label(truncate(email.subject, 40)).classes('text-[10px] font-bold truncate')
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.label(truncate(email.from_address, 25)).classes('text-[9px] opacity-60')
                                                    if email.attachments:
                                                        ui.chip(f'{len(email.attachments)}', icon='attach_file').props('dense size=xs color=amber')

                # --- COLUMNA 2: Filtros y Opciones ---
                with ui.column().classes('gap-4'):
                    # Card Filtros de búsqueda
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('email_scan.filters', 'Filtros de búsqueda')).classes('text-base font-bold mb-2')

                        ui.input(t('email_scan.filter_subject', 'Asunto contiene'), placeholder='Ej: [FACTURA], Reporte...') \
                            .classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'subject_contains')

                        ui.input(t('email_scan.from_contains', 'Remitente'), placeholder='Ej: admin@empresa.com') \
                            .classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'from_address')

                        ui.input(t('email_scan.to_contains', 'Destinatario'), placeholder='Ej: facturas@miempresa.com') \
                            .classes('w-full text-sm').props('dense outlined').bind_value(design_state, 'to_address')

                        # Selector de modo de fecha
                        ui.checkbox(t('email_scan.use_date_range', 'Usar rango de fechas')).classes('text-xs mt-2') \
                            .bind_value(design_state, 'use_date_range') \
                            .tooltip('Activar para usar rango de fechas específico en lugar de días hacia atrás')

                        # Modo días hacia atrás
                        with ui.row().classes('w-full gap-2').bind_visibility_from(design_state, 'use_date_range', backward=lambda x: not x):
                            ui.number(t('email_scan.since_days', 'Últimos días'), min=1).classes('flex-grow text-sm') \
                                .props('dense outlined').bind_value(design_state, 'since_days')
                            ui.number(t('email_scan.max_emails', 'Máx. emails'), min=1).classes('flex-grow text-sm') \
                                .props('dense outlined').bind_value(design_state, 'max_emails')

                        # Modo rango de fechas
                        with ui.column().classes('w-full gap-2').bind_visibility_from(design_state, 'use_date_range'):
                            with ui.row().classes('w-full gap-2'):
                                with ui.input(t('email_scan.date_from', 'Desde')).classes('flex-grow text-sm').props('dense outlined') as date_from_input:
                                    with ui.menu().props('no-parent-event') as date_from_menu:
                                        with ui.date().bind_value(design_state, 'date_from'):
                                            with ui.row().classes('justify-end'):
                                                ui.button('Cerrar', on_click=date_from_menu.close).props('flat')
                                    with date_from_input.add_slot('append'):
                                        ui.icon('event').on('click', date_from_menu.open).classes('cursor-pointer')
                                    date_from_input.bind_value(design_state, 'date_from')

                                with ui.input(t('email_scan.date_to', 'Hasta')).classes('flex-grow text-sm').props('dense outlined') as date_to_input:
                                    with ui.menu().props('no-parent-event') as date_to_menu:
                                        with ui.date().bind_value(design_state, 'date_to'):
                                            with ui.row().classes('justify-end'):
                                                ui.button('Cerrar', on_click=date_to_menu.close).props('flat')
                                    with date_to_input.add_slot('append'):
                                        ui.icon('event').on('click', date_to_menu.open).classes('cursor-pointer')
                                    date_to_input.bind_value(design_state, 'date_to')

                            ui.number(t('email_scan.max_emails', 'Máx. emails'), min=1).classes('w-full text-sm') \
                                .props('dense outlined').bind_value(design_state, 'max_emails')

                        ui.checkbox(t('email_scan.only_attachments', 'Solo con adjuntos')).classes('text-xs mt-2') \
                            .bind_value(design_state, 'has_attachments')

                    # Card Contenido a descargar (NUEVO)
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('email_scan.content_options', 'Contenido a descargar')).classes('text-base font-bold mb-2')

                        with ui.column().classes('gap-2'):
                            ui.checkbox(t('email_scan.save_body_plain', 'Guardar cuerpo del email (texto plano)')) \
                                .classes('text-xs').bind_value(design_state, 'save_body_plain')

                            ui.checkbox(t('email_scan.save_body_html', 'Guardar cuerpo HTML')) \
                                .classes('text-xs').bind_value(design_state, 'save_body_html')

                            ui.checkbox(t('email_scan.download_attachments', 'Descargar adjuntos')) \
                                .classes('text-xs').bind_value(design_state, 'download_attachments')

                            ui.separator().classes('my-1')

                            ui.checkbox(t('email_scan.persist_to_db', 'Persistir en base de datos')) \
                                .classes('text-xs').bind_value(design_state, 'persist_to_db') \
                                .tooltip('Guardar emails en BD para informes, resúmenes con LLM, etc.')

                            ui.checkbox(t('email_scan.mark_as_read', 'Marcar como leído tras procesar')) \
                                .classes('text-xs').bind_value(design_state, 'mark_as_read')

                    # Botones de acción
                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                        ui.button(t('common.cancel', 'Cancelar'), on_click=go_to_library).props('flat color=slate text-sm')
                        ui.button(t('common.validate', 'Guardar'), icon='check', on_click=handle_save) \
                            .props('unelevated color=primary shadow text-sm') \
                            .bind_enabled_from(design_state, 'is_saving', backward=lambda x: not x)

    @ui.refreshable
    def render_inbox():
        """Renderiza la bandeja de correos recibidos."""
        with ui.column().classes('w-full max-w-6xl mx-auto gap-4'):
            # Header con tabs integrados
            with ui.row().classes('w-full items-start justify-between mb-4'):
                with ui.column().classes('gap-0'):
                    ui.label(t('email_scan.inbox_title', 'Bandeja de Correos')).classes('text-3xl font-bold text-primary mb-1')
                    ui.label(t('email_scan.inbox_subtitle', 'Correos descargados por Email Scan y Email Watcher')).classes('text-slate-500 text-base')
                render_mode_tabs()

            # Filtros
            with ui.card().classes('w-full p-4 shadow-sm border border-slate-100'):
                with ui.column().classes('w-full gap-3'):
                    # Fila 1: Remitente y Asunto
                    with ui.row().classes('w-full gap-4'):
                        ui.input('Remitente contiene', placeholder='ej: facturas@proveedor.com',
                                 value=inbox_state.filter_sender).props('dense outlined').classes('flex-1') \
                            .on('update:model-value', lambda e: (setattr(inbox_state, 'filter_sender', e.args), save_action_btn.set_enabled(bool(e.args or inbox_state.filter_search))))

                        ui.input('Asunto contiene', placeholder='ej: Factura, Reporte...',
                                 value=inbox_state.filter_search).props('dense outlined').classes('flex-1') \
                            .on('update:model-value', lambda e: (setattr(inbox_state, 'filter_search', e.args), save_action_btn.set_enabled(bool(e.args or inbox_state.filter_sender))))


                    # Fila 2: Fechas con selector de modo
                    with ui.row().classes('w-full items-end gap-4'):
                        # Toggle: últimos X días vs rango de fechas
                        ui.checkbox('Últimos X días', value=inbox_state.use_last_days) \
                            .classes('text-xs').bind_value(inbox_state, 'use_last_days')

                        # Modo: últimos X días
                        with ui.row().classes('gap-2').bind_visibility_from(inbox_state, 'use_last_days'):
                            ui.number('Días', value=inbox_state.filter_last_days, min=1, max=365) \
                                .props('dense outlined').classes('w-24') \
                                .bind_value(inbox_state, 'filter_last_days')

                        # Modo: rango de fechas
                        with ui.row().classes('gap-2').bind_visibility_from(inbox_state, 'use_last_days', backward=lambda x: not x):
                            with ui.input('Desde', value=inbox_state.filter_date_from).props('dense outlined').classes('w-36') as df:
                                with ui.menu().props('no-parent-event') as m1:
                                    with ui.date().bind_value(inbox_state, 'filter_date_from'):
                                        ui.button('OK', on_click=m1.close).props('flat')
                                with df.add_slot('append'):
                                    ui.icon('event').on('click', m1.open).classes('cursor-pointer')
                                df.bind_value(inbox_state, 'filter_date_from')

                            with ui.input('Hasta', value=inbox_state.filter_date_to).props('dense outlined').classes('w-36') as dt:
                                with ui.menu().props('no-parent-event') as m2:
                                    with ui.date().bind_value(inbox_state, 'filter_date_to'):
                                        ui.button('OK', on_click=m2.close).props('flat')
                                with dt.add_slot('append'):
                                    ui.icon('event').on('click', m2.open).classes('cursor-pointer')
                                dt.bind_value(inbox_state, 'filter_date_to')

                        # Origen y Estado
                        ui.select({'all': 'Todos', 'scan': 'Escaneo', 'watcher': 'Monitor'},
                                  value=inbox_state.filter_source, label='Origen') \
                            .props('dense outlined').classes('w-28') \
                            .on('update:model-value', lambda e: setattr(inbox_state, 'filter_source', e.args))

                        ui.select({'all': 'Todos', 'pending': 'Pendientes', 'processed': 'Procesados'},
                                  value=inbox_state.filter_status, label='Estado') \
                            .props('dense outlined').classes('w-32') \
                            .on('update:model-value', lambda e: setattr(inbox_state, 'filter_status', e.args))

                        ui.button('Filtrar', icon='filter_list', on_click=load_inbox_emails).props('unelevated color=primary')

                    # Fila 3: Conexión IMAP y Prueba
                    with ui.row().classes('w-full items-center gap-4'):
                        creds_options = {c['id']: c['name'] for c in page_state.credentials}
                        ui.select(creds_options, label='Conexión IMAP') \
                            .classes('w-64').props('dense outlined').bind_value(inbox_state, 'credential_id')
                        ui.button('Probar conexión', icon='science', on_click=handle_inbox_test_connection) \
                            .props('unelevated color=emerald-600 dense').classes('shadow-sm')

            # Estadísticas y acciones
            with ui.row().classes('w-full items-center justify-between'):
                # Stats
                with ui.row().classes('gap-4'):
                    with ui.card().classes('p-3 shadow-none border bg-slate-50'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('email', color='slate')
                            ui.label(f"Total: {inbox_state.stats.get('total', 0)}").classes('text-sm font-medium')

                    with ui.card().classes('p-3 shadow-none border bg-green-50'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('check_circle', color='green')
                            ui.label(f"Procesados: {inbox_state.stats.get('processed', 0)}").classes('text-sm font-medium')

                    with ui.card().classes('p-3 shadow-none border bg-amber-50'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('pending', color='amber')
                            ui.label(f"Pendientes: {inbox_state.stats.get('pending', 0)}").classes('text-sm font-medium')

                # Acciones masivas
                with ui.row().classes('gap-2'):
                    ui.checkbox('Seleccionar todos',
                                value=len(inbox_state.selected_ids) == len(inbox_state.emails) and len(inbox_state.emails) > 0,
                                on_change=lambda: toggle_select_all()).classes('text-xs')

                    save_action_btn = ui.button('Guardar como acción', icon='save', on_click=handle_save_as_atom) \
                        .props('flat dense color=primary') \
                        .tooltip('Guarda los filtros actuales como una acción reutilizable en flujos')
                    save_action_btn.set_enabled(bool(inbox_state.filter_sender or inbox_state.filter_search))


                    ui.button('Marcar procesados', icon='check', on_click=handle_mark_processed) \
                        .props('flat dense color=green').set_enabled(len(inbox_state.selected_ids) > 0)

                    ui.button('Eliminar', icon='delete', on_click=handle_delete_selected) \
                        .props('flat dense color=red').set_enabled(len(inbox_state.selected_ids) > 0)

            # Lista de emails
            if inbox_state.is_loading:
                with ui.row().classes('w-full justify-center p-8'):
                    ui.spinner('dots', size='lg')
                    ui.label('Cargando correos...').classes('text-slate-500')

            elif not inbox_state.emails:
                with ui.card().classes('w-full p-8 text-center bg-slate-50'):
                    ui.icon('inbox', size='xl', color='slate')
                    ui.label('No hay correos que coincidan con los filtros').classes('text-slate-500 mt-2')

            else:
                with ui.row().classes('w-full gap-4'):
                    # Lista de emails (lado izquierdo)
                    with ui.column().classes('flex-1 gap-2'):
                        with ui.scroll_area().classes('w-full h-[500px] border rounded'):
                            with ui.column().classes('w-full gap-1 p-2'):
                                for email in inbox_state.emails:
                                    is_selected = email.id in inbox_state.selected_ids
                                    is_detail = inbox_state.selected_email and inbox_state.selected_email.id == email.id

                                    bg_class = 'bg-blue-50 border-blue-200' if is_detail else ('bg-slate-50' if is_selected else 'bg-white')

                                    with ui.card().classes(f'w-full p-3 shadow-none border cursor-pointer hover:bg-slate-50 {bg_class}'):
                                        with ui.row().classes('w-full items-start gap-3'):
                                            # Checkbox
                                            ui.checkbox(value=is_selected,
                                                        on_change=lambda _, eid=email.id: toggle_email_selection(eid)).props('dense')

                                            # Contenido
                                            with ui.column().classes('flex-1 gap-0').on('click', lambda _, e=email: select_email_for_detail(e)):
                                                with ui.row().classes('w-full items-center gap-2'):
                                                    ui.label(truncate(email.subject or '(Sin asunto)', 50)).classes('text-sm font-medium')
                                                    if email.is_processed:
                                                        ui.chip('Procesado', icon='check').props('dense size=xs color=green')
                                                    else:
                                                        ui.chip('Pendiente', icon='pending').props('dense size=xs color=amber')

                                                with ui.row().classes('w-full items-center gap-2 mt-1'):
                                                    ui.label(truncate(email.sender or '', 30)).classes('text-xs text-slate-500')
                                                    ui.label('|').classes('text-xs text-slate-300')
                                                    ui.label(format_date(email.date)).classes('text-xs text-slate-400')

                                                    # Info adjuntos
                                                    attachments = json.loads(email.attachments_info) if email.attachments_info else []
                                                    if attachments:
                                                        ui.chip(f'{len(attachments)}', icon='attach_file').props('dense size=xs outline color=slate')

                    # Vista detalle (lado derecho)
                    if inbox_state.selected_email:
                        email = inbox_state.selected_email
                        attachments = json.loads(email.attachments_info) if email.attachments_info else []

                        with ui.card().classes('w-[400px] p-4 shadow-sm border'):
                            # Header
                            with ui.row().classes('w-full items-center justify-between mb-3'):
                                ui.label('Detalle del correo').classes('text-base font-bold text-primary')
                                ui.button(icon='close', on_click=close_detail).props('flat round dense')

                            # Metadatos
                            with ui.column().classes('gap-2 mb-3'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('subject', size='xs', color='slate')
                                    ui.label(email.subject or '(Sin asunto)').classes('text-sm font-medium')

                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('person', size='xs', color='slate')
                                    ui.label(email.sender).classes('text-xs text-slate-600')

                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('schedule', size='xs', color='slate')
                                    ui.label(format_date(email.date)).classes('text-xs text-slate-600')

                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('label', size='xs', color='slate')
                                    ui.label(f"Origen: {email.source}").classes('text-xs text-slate-600')
                                    if email.is_processed:
                                        ui.chip('Procesado', icon='check').props('dense size=xs color=green')

                            ui.separator()

                            # Cuerpo
                            ui.label('Contenido').classes('text-xs font-bold text-slate-500 uppercase mt-2')
                            with ui.scroll_area().classes('w-full h-48 border rounded p-2 bg-slate-50 mt-1'):
                                body_text = email.body_plain or email.body_html or '(Sin contenido)'
                                ui.label(body_text).classes('text-xs whitespace-pre-wrap')

                            # Adjuntos
                            if attachments:
                                ui.label(f'Adjuntos ({len(attachments)})').classes('text-xs font-bold text-slate-500 uppercase mt-3')
                                with ui.column().classes('gap-1 mt-1'):
                                    for att in attachments:
                                        with ui.row().classes('items-center gap-2 p-2 bg-slate-50 rounded'):
                                            ui.icon('attach_file', size='xs', color='slate')
                                            ui.label(att.get('filename', 'archivo')).classes('text-xs flex-1 truncate')
                                            if att.get('size'):
                                                size_kb = att['size'] / 1024
                                                ui.label(f'{size_kb:.1f} KB').classes('text-[10px] text-slate-400')

    # --- INITIALIZATION ---
    await load_configs()
    await load_credentials()

    # Verificar si viene desde un flujo (modo contextual)
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
            if flow_config_id:
                matching = next((c for c in page_state.saved_configs if c['id'] == flow_config_id), None)
                if matching:
                    await edit_atom(matching)
        layout_manager.enter_design_mode(StepType.EMAIL_SCAN, from_flow=True)

    render_page()

    return render_page
