from nicegui import ui
from client_app.app.core.state import state
from client_app.app.database.models import ServerConnection, LocalCredentials
from client_app.app.modules.security.encryption_service import EncryptionService
from client_app.app.ui.components.page_header import page_header
from client_app.app.ui.logs_page import logs_page_content
from client_app.app.ui.audit_page import audit_page_content
from client_app.app.ui.import_export_page import packages_page_content
from client_app.app.services.cleanup_service import cleanup_service
from sqlmodel import select
import json
import asyncio
from client_app.app.ui.components.connections_manager import ConnectionsManager
from client_app.app.ui.components.database_connection_manager import DatabaseConnectionManager

async def _load_effective_policy_from_server(license_key: str, brain_url: str = None) -> dict:
    """
    Recupera la política de seguridad efectiva del servidor para el cliente actual.
    Utiliza el motor de cascada del servidor (CLIENTE > PARTNER > SISTEMA) para
    determinar las restricciones de ejecución basadas en la clave de licencia.

    Usa el patrón consistente: LocalBrainClient (monolito) o BrainAPIClient (split).

    Args:
        license_key: Clave de licencia del cliente (sin hashear).
        brain_url: URL del servidor Brain (opcional, para modo split).

    Returns:
        Diccionario con la política resuelta y metadatos del nivel aplicado.
    """
    from client_app.app.core.state import state
    from client_app.app.clients import BrainAPIClient
    from client_app.app.database.models import ServerConnection
    from client_app.app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    default_policy = {
        "allowed_domains": [],
        "allowed_libraries": ["pandas", "json", "re", "math", "datetime"],
        "forbidden_libraries": ["os", "sys", "subprocess"],
        "max_memory_mb": 512,
        "max_execution_time": 300,
        "applied_level": "SYSTEM",
        "scope": "SYSTEM",
        "screenshot_policy": "REVIEW"
    }

    if not license_key:
        return default_policy

    try:
        # Resolve URL from DB if not provided
        url = brain_url
        if not url:
            async with AsyncSession(client_engine) as session:
                stmt = select(ServerConnection).where(ServerConnection.is_active == True)
                res = await session.exec(stmt)
                conn = res.first()
                url = conn.brain_url if (conn and conn.brain_url) else "http://localhost:8080"

        client = BrainAPIClient(base_url=url)
        return await client.get_effective_policy(license_key)

    except Exception as e:
        print(f"[client_admin_page] Error loading effective policy: {e}")
        return default_policy


def client_admin_page_content(tab: str = 'General'):
    """
    Controlador de la página de administración del cliente.
    Permite configurar la conexión con el Brain, gestionar credenciales locales cifradas,
    visualizar políticas de seguridad y configurar el servicio de auto-limpieza.
    """
    t = state.i18n.t

    class ConfigState:
        """
        Mantiene el estado reactivo de la configuración del cliente.
        Sincroniza los valores de la base de datos con los componentes de la UI.
        """
        def __init__(self, initial_tab: str = 'General'):
            # General
            self.brain_url = ""
            self.license_key = ""
            self.connection_id = None

            # Integrations
            self.credentials = []
            self.new_cred_dialog = False
            self.editing_cred = None # None or LocalCredentials object

            # Security
            self.policy = {}

            # Cleanup
            self.cleanup_status = {}

            # UI State - preservar tab activo
            self.active_tab = initial_tab
            self.initial_load_done = False

    config = ConfigState(initial_tab=tab)

    async def load_config():
        """
        Carga la configuración completa del cliente: conexión, credenciales, 
        políticas de seguridad y estado de limpieza.
        """
        async with state.db_session() as session:
            # 1. Load Server Connection
            result = await session.execute(select(ServerConnection))
            conn = result.scalars().first()
            if conn:
                config.connection_id = conn.id # Use Primary Key 'id' not 'connection_id' as per models.py
                config.brain_url = conn.brain_url
                config.license_key = conn.license_key
            else:
                # Defaults - usar localhost para desarrollo local
                config.brain_url = "http://localhost:8080"
                config.license_key = ""

            # 2. Load Credentials
            result = await session.execute(select(LocalCredentials))
            config.credentials = result.scalars().all()

            # 3. Load Security Policy (Effective) from SERVER via cascade
            # The policy is resolved using: CLIENT > PARTNER > SYSTEM cascade
            config.policy = await _load_effective_policy_from_server(config.license_key, config.brain_url)

        config.cleanup_status = await cleanup_service.get_status()

        # Solo refrescar en la carga inicial, no en recargas (evita perder el tab activo)
        if not config.initial_load_done:
            config.initial_load_done = True
            render_content.refresh()

    async def save_general_config():
        """
        Guarda los ajustes generales de conexión (URL del Brain y Licencia) 
        en la base de datos local.
        """
        async with state.db_session() as session:
            if config.connection_id:
                conn = await session.get(ServerConnection, config.connection_id)
                conn.brain_url = config.brain_url
                conn.license_key = config.license_key
                session.add(conn)
            else:
                conn = ServerConnection(
                    brain_url=config.brain_url,
                    license_key=config.license_key,
                    is_active=True
                )
                session.add(conn)
            await session.commit()
            config.connection_id = conn.id
        ui.notify(t('config.saved_successfully'), type='positive')

    async def save_credential(service_name, username, password, cred_id=None):
        """
        Cifra y guarda una credencial local.

        Args:
            service_name: Nombre del servicio (ej. Gmail, Salesforce).
            username: Identificador del usuario.
            password: Contraseña o token.
            cred_id: ID existente para actualización, o None para nueva creación.
        """
        crypto = EncryptionService()
        data = {"username": username, "password": password}
        encrypted = crypto.encrypt(data)

        async with state.db_session() as session:
            if cred_id:
                cred = await session.get(LocalCredentials, cred_id)
                cred.service_name = service_name
                cred.encrypted_data = encrypted
                cred.updated_at = datetime.utcnow()
                session.add(cred)
            else:
                cred = LocalCredentials(
                    service_name=service_name,
                    encrypted_data=encrypted
                )
                session.add(cred)
            await session.commit()
        
        await load_config()
        ui.notify(t('config.cred_saved'), type='positive')

    async def delete_credential(cred_id):
        async with state.db_session() as session:
             cred = await session.get(LocalCredentials, cred_id)
             if cred:
                 await session.delete(cred)
                 await session.commit()
        await load_config()
        ui.notify(t('config.cred_deleted'), type='positive')

    # --- UI RENDERERS ---

    # --- HEADER CONTENT MAPPING ---
    # Keys match the labels of the tabs below
    HEADERS = {
        'General': {
            'title': t('admin.headers.general_title'),
            'subtitle': t('admin.headers.general_subtitle')
        },
        'Seguridad': {
            'title': t('admin.headers.security_title'),
            'subtitle': t('admin.headers.security_subtitle')
        },
        'Logs': {
            'title': t('admin.headers.logs_title'),
            'subtitle': t('admin.headers.logs_subtitle')
        },
        'Auditoría RGPD': {
            'title': t('admin.headers.audit_title'),
            'subtitle': t('admin.headers.audit_subtitle')
        },
        'Limpieza': {
            'title': t('admin.headers.cleanup_title'),
            'subtitle': t('admin.headers.cleanup_subtitle')
        },
        'Paquetes': {
            'title': t('admin.headers.packages_title'),
            'subtitle': t('admin.headers.packages_subtitle')
        },
        'Cuentas': {
            'title': t('admin.headers.accounts_title'),
            'subtitle': t('admin.headers.accounts_subtitle')
        },
    }

    @ui.refreshable
    def render_content():
        # 1. TABS NAVIGATION (Header removed from here and moved inside panels)
        with ui.tabs().classes('w-full border-b border-gray-200 bg-white').props('active-color=blue-900 active-bg-color=transparent indicator-color=primary uppercase=false') as tabs:
            ui.tab('General', icon='settings', label=t('admin.tabs.general')).props('no-caps').classes('text-primary text-sm font-medium h-16')
            ui.tab('Seguridad', icon='security', label=t('admin.tabs.security')).props('no-caps').classes('text-primary text-sm font-medium h-16')
            ui.tab('Logs', icon='list_alt', label=t('admin.tabs.logs')).props('no-caps').classes('text-primary text-sm font-medium h-16')
            ui.tab('Auditoría RGPD', icon='verified_user', label=t('admin.tabs.audit')).props('no-caps').classes('text-primary text-sm font-medium h-16')
            ui.tab('Limpieza', icon='auto_delete', label=t('admin.tabs.cleanup')).props('no-caps').classes('text-primary text-sm font-medium h-16')
            ui.tab('Paquetes', icon='inventory_2', label=t('admin.tabs.packages')).props('no-caps').classes('text-primary text-sm font-medium h-16')
            ui.tab('Cuentas', icon='mail', label=t('admin.tabs.accounts')).props('no-caps').classes('text-primary text-sm font-medium h-16')
            ui.tab('Bases de Datos', icon='storage', label=t('admin.tabs.databases')).props('no-caps').classes('text-primary text-sm font-medium h-16')

        # Sincronizar cambios de tab con el estado
        def on_tab_change(e):
            config.active_tab = e.value

        tabs.on_value_change(on_tab_change)

        with ui.tab_panels(tabs, value=config.active_tab).classes('w-full mt-4 bg-transparent shadow-none') as panels:
            
            # --- GENERAL TAB ---
            with ui.tab_panel('General'):
                page_header(t('admin.headers.general_title'), t('admin.headers.general_subtitle'))
                with ui.card().classes('w-full max-w-2xl p-6'):
                    ui.label(t('admin.brain_connection')).classes('text-lg font-bold mb-4')
                    
                    ui.input(t('config.brain_url'), value=config.brain_url).bind_value(config, 'brain_url').classes('w-full mb-4')
                    ui.input(t('config.license_key'), password=True, value=config.license_key).bind_value(config, 'license_key').classes('w-full mb-4')
                    
                    ui.button(t('config.save_config'), on_click=save_general_config).props('color=primary icon=save')

            # --- SECURITY TAB ---
            with ui.tab_panel('Seguridad'):
                page_header(t('admin.headers.security_title'), t('admin.headers.security_subtitle'))
                with ui.card().classes('w-full p-6'):
                    ui.label(t('admin.security_policies_title')).classes('text-lg font-bold mb-2')
                    ui.label(t('admin.security_policies_desc')).classes('text-sm text-gray-500 mb-4')

                    if not config.policy:
                        ui.spinner()
                    else:
                        # Show cascade level applied
                        applied_level = config.policy.get('applied_level', 'SYSTEM')
                        level_colors = {
                            'CLIENT': 'blue',
                            'PARTNER': 'purple',
                            'SYSTEM': 'gray'
                        }
                        level_color = level_colors.get(applied_level, 'gray')

                        with ui.row().classes('items-center gap-2 mb-6'):
                            ui.label('Nivel de política aplicada:').classes('text-sm text-gray-600')
                            ui.chip(applied_level, color=f'{level_color}-100').classes(f'text-{level_color}-800 font-medium')

                        with ui.grid(columns=2).classes('gap-6'):
                            # Domains
                            with ui.column():
                                ui.label(t('config.allowed_domains')).classes('font-bold mb-2')
                                domains = config.policy.get('allowed_domains', [])
                                # Handle both list and JSON string formats
                                if isinstance(domains, str):
                                    try:
                                        domains = json.loads(domains)
                                    except:
                                        domains = []
                                if domains:
                                    for d in domains:
                                        ui.chip(d, icon='check_circle', color='green-100')
                                else:
                                    ui.label(t('config.no_restrictions')).classes('text-sm text-gray-400 italic')

                            # Libraries (Imports)
                            with ui.column():
                                ui.label(t('config.allowed_imports')).classes('font-bold mb-2')
                                # Server uses 'allowed_libraries', fallback to 'allowed_imports'
                                libraries = config.policy.get('allowed_libraries') or config.policy.get('allowed_imports', [])
                                if isinstance(libraries, str):
                                    try:
                                        libraries = json.loads(libraries)
                                    except:
                                        libraries = []
                                if libraries:
                                    ui.label(', '.join(libraries)).classes('text-sm')
                                else:
                                    ui.label(t('config.none')).classes('text-sm text-gray-400 italic')

                            # Forbidden Libraries
                            with ui.column():
                                ui.label(t('config.forbidden_imports')).classes('font-bold mb-2')
                                forbidden = config.policy.get('forbidden_libraries', [])
                                if isinstance(forbidden, str):
                                    try:
                                        forbidden = json.loads(forbidden)
                                    except:
                                        forbidden = []
                                if forbidden:
                                    for f in forbidden:
                                        ui.chip(f, icon='block', color='red-100').classes('text-red-800')
                                else:
                                    ui.label(t('config.none')).classes('text-sm text-gray-400 italic')

                            # Limits
                            with ui.column():
                                ui.label(t('config.resource_limits')).classes('font-bold mb-2')
                                ui.label(f"{t('config.max_memory')}: {config.policy.get('max_memory_mb', 512)} MB").classes('text-sm')
                                ui.label(f"{t('config.max_time')}: {config.policy.get('max_execution_time', 300)} s").classes('text-sm')

                            # Screenshot Policy
                            with ui.column():
                                ui.label(t('admin.pii_policy_rpa')).classes('font-bold mb-2')
                                policy_val = config.policy.get('screenshot_policy', 'REVIEW')
                                
                                color = 'orange'
                                icon = 'visibility'
                                if policy_val == 'BLOCK': color, icon = 'red', 'visibility_off'
                                elif policy_val == 'TRUSTED': color, icon = 'green', 'verified'
                                
                                ui.chip(policy_val, icon=icon, color=f'{color}-100').classes(f'text-{color}-800 font-bold')
                                
                                trusted = config.policy.get('trusted_screenshot_domains', [])
                                if policy_val == 'TRUSTED' and trusted:
                                    ui.label(t('config.allowed_domains') + ':').classes('text-xs text-gray-500 mt-1')
                                    for d in trusted:
                                        ui.label(f"• {d}").classes('text-xs text-gray-600 ml-2')

            # --- LOGS TAB ---
            with ui.tab_panel('Logs'):
                page_header(t('admin.headers.logs_title'), t('admin.headers.logs_subtitle'))
                logs_page_content()

            # --- AUDIT (RGPD) TAB ---
            with ui.tab_panel('Auditoría RGPD'):
                page_header(t('admin.headers.audit_title'), t('admin.headers.audit_subtitle'))
                audit_page_content()

            # --- CLEANUP TAB ---
            with ui.tab_panel('Limpieza'):
                page_header(t('admin.headers.cleanup_title'), t('admin.headers.cleanup_subtitle'))
                render_cleanup_tab()

            # --- PAQUETES TAB ---
            with ui.tab_panel('Paquetes'):
                page_header(t('admin.headers.packages_title'), t('admin.headers.packages_subtitle'))
                packages_page_content()

            # --- CUENTAS TAB ---
            with ui.tab_panel('Cuentas'):
                page_header(t('admin.headers.accounts_title'), t('admin.headers.accounts_subtitle'))
                
                with ui.grid(columns=2).classes('w-full max-w-6xl mx-auto gap-12'):
                    with ui.column().classes('w-full'):
                        ui.label(t('admin.incoming_mail')).classes('text-lg font-bold mb-4 text-slate-800')
                        imap_manager = ConnectionsManager(service_type="IMAP")
                        imap_manager.render()

                    with ui.column().classes('w-full'):
                        ui.label(t('admin.outgoing_mail')).classes('text-lg font-bold mb-4 text-slate-800')
                        smtp_manager = ConnectionsManager(service_type="SMTP")
                        smtp_manager.render()

            # --- BASES DE DATOS TAB ---
            with ui.tab_panel('Bases de Datos'):
                page_header(t('admin.headers.databases_title'), t('admin.headers.databases_subtitle'))
                with ui.column().classes('w-full max-w-4xl mx-auto'):
                    db_manager = DatabaseConnectionManager()
                    db_manager.render()


    def render_cleanup_tab():
        """
        Renderiza la pestaña de mantenimiento y limpieza automática.
        Incluye visualización de uso de disco, configuración de frecuencias
        y gestión de políticas de retención por tipo de directorio.
        """
        status = config.cleanup_status

        # Status Card
        with ui.card().classes('w-full p-4 mb-6'):
            ui.label(t('admin.cleanup.status_card')).classes('text-lg font-bold mb-4')

            with ui.grid(columns=3).classes('w-full gap-4'):
                # Status indicator
                with ui.row().classes('items-center p-2 bg-slate-50 rounded gap-3'):
                    status_color = 'text-green-600' if status.get('enabled') else 'text-gray-400'
                    status_icon = 'check_circle' if status.get('enabled') else 'cancel'
                    ui.icon(status_icon).classes(f'{status_color} text-2xl')
                    with ui.column().classes('gap-0'):
                        ui.label(t('config.cleanup.status_enabled') if status.get('enabled')
                                 else t('config.cleanup.status_disabled')).classes(f'{status_color} font-bold text-sm')
                        ui.label('Monitoreo activo' if status.get('enabled') else 'Inactivo').classes('text-[10px] text-gray-400')

                # Pending cleanup info
                with ui.row().classes('items-center p-2 bg-slate-50 rounded gap-3'):
                    ui.icon('folder_delete').classes('text-orange-500 text-2xl')
                    pending_files = status.get('pending_files', 0)
                    pending_mb = status.get('pending_bytes', 0) / (1024 * 1024)
                    with ui.column().classes('gap-0'):
                        ui.label(f"{pending_files} {t('config.cleanup.pending_files')}").classes('text-orange-600 font-bold text-sm')
                        ui.label(f"{pending_mb:.1f} MB").classes('text-[10px] text-gray-400')

                # Last run info
                with ui.row().classes('items-center p-2 bg-slate-50 rounded gap-3'):
                    ui.icon('history').classes('text-blue-600 text-2xl')
                    with ui.column().classes('gap-0'):
                        if status.get('last_run'):
                            from datetime import datetime
                            last_run = datetime.fromisoformat(status['last_run'])
                            last_deleted = status.get('last_files_deleted', 0)
                            ui.label(last_run.strftime('%d/%m %H:%M')).classes('text-blue-600 font-bold text-sm')
                            ui.label(f"{last_deleted} elim. ({status.get('last_bytes_freed', 0) / (1024 * 1024):.1f}MB)").classes('text-[10px] text-gray-400')
                        else:
                            ui.label('--').classes('text-gray-400 font-bold')
                            ui.label(t('config.cleanup.never_run')).classes('text-[10px] text-gray-400')

        # Storage Usage Panel (Prompt 15)
        storage = status.get('storage', {})
        total_bytes = storage.get('total_bytes', 0)
        total_mb = total_bytes / (1024 * 1024)

        with ui.card().classes('w-full p-4 mb-6'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label(t('admin.cleanup.storage_usage')).classes('text-lg font-bold')
                
                async def refresh_all():
                    ui.notify("Actualizando estadísticas...", type='info')
                    # This is a bit brute force but effective for current structure
                    ui.navigate.to('/config') 
                
                ui.button(icon='refresh', on_click=refresh_all).props('flat dense')

            with ui.grid(columns='1fr 1fr').classes('w-full gap-8'):
                # Left: Breakdown with bars
                with ui.column().classes('w-full gap-4'):
                    for cat in storage.get('categories', []):
                        size_mb = cat['size_bytes'] / (1024 * 1024)
                        percent = (cat['size_bytes'] / total_bytes) if total_bytes > 0 else 0
                        
                        with ui.column().classes('w-full gap-1'):
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label(cat['label']).classes('text-sm font-medium text-slate-700')
                                ui.label(f"{size_mb:.1f} MB").classes('text-xs text-gray-400')
                            ui.linear_progress(value=percent).classes('w-full h-1.5 rounded bg-slate-100').props('color=blue-600')

                # Right: Summary cards
                with ui.row().classes('w-full gap-2 items-center'):
                    with ui.row().classes('flex-1 items-center p-2 bg-slate-50 border-none shadow-none rounded gap-2'):
                        ui.icon('storage', color='slate-400', size='xs')
                        with ui.column().classes('gap-0'):
                            ui.label(t('admin.cleanup.total_space')).classes('text-[10px] text-gray-500 uppercase font-bold')
                            ui.label(f"{total_mb:.1f} MB").classes('text-sm font-extrabold text-slate-800')

                    with ui.row().classes('flex-1 items-center p-2 bg-slate-50 border-none shadow-none rounded gap-2'):
                        ui.icon('delete_sweep', color='orange-400', size='xs')
                        orphans = storage.get('orphan_count', 0)
                        orphan_color = 'orange-600' if orphans > 0 else 'green-600'
                        with ui.column().classes('gap-0'):
                            ui.label(t('admin.cleanup.orphans')).classes('text-[10px] text-gray-500 uppercase font-bold')
                            ui.label(f"{orphans} {t('admin.cleanup.files')}").classes(f'text-sm font-extrabold text-{orphan_color}')

        # Configuration Card
        with ui.card().classes('w-full p-4 mb-6'):
            ui.label(t('admin.cleanup.config_title')).classes('text-lg font-bold mb-4')

            # Enable switch
            enabled_switch = ui.switch(
                t('config.cleanup.enabled_label'),
                value=status.get('enabled', True)
            ).classes('mb-4')

            # Delay setting
            with ui.row().classes('items-center gap-4 mb-2'):
                ui.label(t('config.cleanup.delay_label')).classes('text-sm')
                delay_input = ui.number(
                    value=status.get('startup_delay_minutes', 2),
                    min=1,
                    max=60
                ).classes('w-24')
                ui.label(t('config.cleanup.minutes')).classes('text-sm text-gray-500')

            # Interval setting
            with ui.row().classes('items-center gap-4 mb-6'):
                ui.label(t('admin.cleanup.frequency')).classes('text-sm')
                interval_input = ui.number(
                    value=status.get('interval_hours', 24),
                    min=1,
                    max=168
                ).classes('w-24')
                ui.label(t('admin.cleanup.hours')).classes('text-sm text-gray-500')

            # Action buttons
            with ui.row().classes('gap-4'):
                async def save_cleanup_config():
                    await cleanup_service.update_config(
                        enabled=enabled_switch.value,
                        delay_minutes=int(delay_input.value),
                        interval_hours=int(interval_input.value)
                    )
                    config.cleanup_status = await cleanup_service.get_status()
                    ui.notify(t('config.cleanup.config_saved'), type='positive')
                    render_content.refresh()

                async def run_cleanup_now():
                    ui.notify(t('config.cleanup.running'), type='info')
                    result = await cleanup_service.run_cleanup(manual=True)
                    if result.get('success'):
                        total = result.get('total_files_deleted', 0)
                        mb = result.get('total_bytes_freed', 0) / (1024 * 1024)
                        ui.notify(
                            f"{t('config.cleanup.completed')}: {total} {t('config.cleanup.files_deleted')} ({mb:.1f} MB)",
                            type='positive'
                        )
                    config.cleanup_status = await cleanup_service.get_status()
                    render_content.refresh()

                ui.button(t('common.save'), icon='save', on_click=save_cleanup_config).props('color=primary')
                ui.button(t('config.cleanup.run_now'), icon='play_arrow', on_click=run_cleanup_now).props('color=secondary outline')

        # Retention Policies Card
        with ui.card().classes('w-full p-4'):
            ui.label(t('admin.cleanup.retention_policies')).classes('text-lg font-bold mb-4')
            ui.label(t('admin.cleanup.retention_desc')).classes('text-sm text-gray-500 mb-4')

            policies = status.get('policies', [])

            # Policy type labels
            policy_labels = {
                'uploads': t('config.cleanup.policy_uploads'),
                'etl': t('config.cleanup.policy_etl'),
                'results': t('config.cleanup.policy_results'),
                'execution': t('config.cleanup.policy_execution'),
                'screenshots': t('config.cleanup.policy_screenshots'),
            }

            policy_refs = {}

            with ui.column().classes('w-full gap-4'):
                for policy in policies:
                    folder_type = policy['folder_type']
                    label = policy_labels.get(folder_type, folder_type)

                    bg_class = 'bg-slate-200' if policy['enabled'] else 'bg-slate-50'
                    with ui.row().classes(f'w-full items-center gap-4 p-3 {bg_class} rounded'):
                        # Enable checkbox
                        enabled_cb = ui.checkbox(value=policy['enabled']).classes('mr-2')

                        # Label and path
                        with ui.column().classes('flex-1'):
                            ui.label(label).classes('font-medium')
                            ui.label(policy['folder_path']).classes('text-xs text-gray-400')

                        # Retention days input
                        ui.label(t('config.cleanup.retention')).classes('text-sm text-gray-600')
                        days_input = ui.number(
                            value=policy['retention_days'],
                            min=1,
                            max=365
                        ).classes('w-20')
                        ui.label(t('config.cleanup.days')).classes('text-sm text-gray-500')

                        # Store references for saving
                        policy_refs[folder_type] = {
                            'enabled': enabled_cb,
                            'days': days_input
                        }

            # Save policies button
            async def save_policies():
                for folder_type, refs in policy_refs.items():
                    await cleanup_service.update_policy(
                        folder_type=folder_type,
                        enabled=refs['enabled'].value,
                        retention_days=int(refs['days'].value)
                    )
                config.cleanup_status = await cleanup_service.get_status()
                ui.notify(t('config.cleanup.policies_saved'), type='positive')
                render_content.refresh()

            ui.button(
                t('config.cleanup.save_policies'),
                icon='save',
                on_click=save_policies
            ).props('color=primary').classes('mt-4')


    # --- DIALOGS ---
    
    def open_cred_dialog(cred=None):
        name_val = cred.service_name if cred else ""
        user_val = ""
        pass_val = ""
        
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label(t('config.edit_credential') if cred else t('config.new_credential')).classes('text-lg font-bold mb-4')
            
            name_input = ui.input(t('config.service_name'), value=name_val).classes('w-full')
            user_input = ui.input(t('config.user_email'), value=user_val).classes('w-full')
            pass_input = ui.input(t('config.password_token'), password=True, value=pass_val).classes('w-full')
            
            async def on_save():
                if not name_input.value or not user_input.value or not pass_input.value:
                    ui.notify(t('config.all_fields_required'), type='warning')
                    return
                await save_credential(name_input.value, user_input.value, pass_input.value, cred.id if cred else None)
                dialog.close()
            
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
                ui.button(t('common.save'), on_click=on_save).props('color=primary')
        
        dialog.open()

    from datetime import datetime

    # Initial Load
    ui.timer(0.1, load_config, once=True)
    render_content()
