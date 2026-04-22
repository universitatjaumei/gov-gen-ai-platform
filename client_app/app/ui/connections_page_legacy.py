"""
Página consolidada de gestión de conexiones.
Unifica Monitor de Carpetas, Email y Web en una interfaz con tabs.
"""
import asyncio
import re
import os
from pathlib import Path
from nicegui import ui
from client_app.app.core.state import state


def is_valid_windows_path(path: str) -> bool:
    """Valida que la ruta tenga un formato válido de Windows."""
    if not path or not path.strip():
        return False
    path = path.strip()
    # Ruta con letra de unidad: C:\, D:\Users\..., etc.
    drive_pattern = r'^[A-Za-z]:\\.*$'
    # Ruta UNC: \\servidor\carpeta
    unc_pattern = r'^\\\\[^\\]+\\.*$'
    return bool(re.match(drive_pattern, path) or re.match(unc_pattern, path))
from client_app.app.services.mail_watcher_service import mail_watcher_service
from client_app.app.services.web_watcher_service import web_watcher_service
from client_app.app.services.api_connection_service import api_connection_service
from client_app.app.services.folder_watcher_service import folder_watcher_service
from client_app.app.services.sql_connector_service import sql_connector_service
from client_app.app.database.models import DatabaseCredentialConfig
from sqlmodel import select
from datetime import datetime

# --- CONFIGURACIÓN DE TABS ---

CONNECTION_TABS = [
    {'id': 'folders', 'label_key': 'connections_tab_folders', 'icon': 'folder'},
    {'id': 'api', 'label_key': 'connections_tab_api', 'icon': 'api'},
    {'id': 'email', 'label_key': 'connections_tab_email', 'icon': 'email'},
    {'id': 'web', 'label_key': 'connections_tab_web', 'icon': 'language'},
    {'id': 'database', 'label_key': 'connections_tab_database', 'icon': 'storage'},
]

FOLDERS_TAB_IS_PLACEHOLDER = False


# --- EMAIL TAB FUNCTIONS (migradas de mail_watcher_page.py) ---

async def email_load_config():
    """Carga configuración del monitor de email."""
    return await mail_watcher_service.load_config()

async def email_save_config(config: dict):
    """Guarda configuración del monitor de email."""
    await mail_watcher_service.save_config(config)

async def email_test_connection(credential_id: int) -> tuple:
    """Prueba conexión (IMAP o SMTP)."""
    return await mail_watcher_service.test_connection(credential_id)

async def email_toggle_watcher(config: dict, auto_start: bool) -> tuple:
    """Inicia o detiene el monitor de email."""
    status = await mail_watcher_service.get_status()
    if status['is_running']:
        return await mail_watcher_service.stop_watcher()
    else:
        return await mail_watcher_service.start_watcher(config, auto_start=auto_start)


# --- WEB TAB FUNCTIONS (migradas de web_watcher_page.py) ---

async def web_load_watchers():
    """Carga lista de monitores web."""
    return await web_watcher_service.list_configs()

async def web_create_watcher(config: dict) -> int:
    """Crea nuevo monitor web."""
    return await web_watcher_service.create_config(config)

async def web_delete_watcher(watcher_id: int) -> bool:
    """Elimina monitor web."""
    return await web_watcher_service.delete_config(watcher_id)

async def web_toggle_watcher(watcher_id: int, active: bool) -> bool:
    """Activa o desactiva monitor web."""
    if active:
        success, msg = await web_watcher_service.start_watcher(watcher_id)
        return success
    else:
        return await web_watcher_service.stop_watcher(watcher_id)


# --- API TAB FUNCTIONS ---

async def api_load_configs():
    return await api_connection_service.list_configs()

async def api_save_config(config: dict) -> int:
    return await api_connection_service.save_config(config)

async def api_delete_config(config_id: int) -> bool:
    return await api_connection_service.delete_config(config_id)

async def api_test_connection(config_id: int):
    return await api_connection_service.test_connection(config_id)


# --- TAB RENDERERS ---

def render_folders_tab():
    """
    Renderiza la pestaña de gestión de monitores de carpetas locales.
    Permite configurar observadores que disparan flujos al detectar nuevos archivos.
    """
    t = state.i18n.t

    class FoldersTabState:
        def __init__(self):
            self.configs = []
            self.flows = []
            self.status = {}

    folders_state = FoldersTabState()

    async def load_all():
        """Cargar configuraciones y flujos."""
        folders_state.configs = await folder_watcher_service.list_configs()
        folders_state.status = await folder_watcher_service.get_status()

        # Cargar flujos disponibles
        from client_app.app.database.models import FlowRegistry
        async with state.db_session() as session:
            stmt = select(FlowRegistry).where(FlowRegistry.is_active == True)
            result = await session.execute(stmt)
            folders_state.flows = result.scalars().all()

        render_folders_content.refresh()

    @ui.refreshable
    def render_folders_content():
        # === HEADER CON BOTÓN NUEVO ===
        with ui.row().classes('w-full items-center mb-4'):
            ui.label(t('folder_watcher_title')).classes('text-xl font-bold')
            ui.space()
            ui.button(
                t('folder_watcher_new'),
                icon='add',
                on_click=lambda: open_config_dialog()
            ).props('color=primary')

        # === ESTADO GLOBAL ===
        with ui.card().classes('w-full p-3 mb-4 bg-slate-50'):
            with ui.row().classes('items-center gap-4'):
                active_count = folders_state.status.get('active_watchers', 0)
                if active_count > 0:
                    ui.badge(f'{active_count} {t("folder_watcher_status_active")}', color='green')
                else:
                    ui.badge(t('folder_watcher_status_stopped'), color='grey')

        # === LISTA DE CONFIGURACIONES ===
        if not folders_state.configs:
            with ui.card().classes('w-full p-8 text-center bg-gray-50'):
                ui.icon('folder_off', size='3em').classes('text-gray-300 mb-2')
                ui.label(t('folder_watcher_no_configs')).classes('text-gray-500')
            return

        # Tabla de configuraciones
        for config in folders_state.configs:
            with ui.card().classes('w-full p-4 mb-2'):
                with ui.row().classes('w-full items-center'):
                    # Info
                    with ui.column().classes('flex-grow'):
                        with ui.row().classes('items-center gap-2'):
                            ui.label(config['name']).classes('font-bold')
                            if config['is_active']:
                                ui.badge('●', color='green').props('dense')
                            else:
                                ui.badge('●', color='grey').props('dense')
                            
                            # Validar existencia de la ruta
                            path_exists = os.path.isdir(config['watch_path'])
                            if not path_exists:
                                ui.badge('Ruta no encontrada', color='red').props('dense')

                        path_label_classes = 'text-sm font-mono ' + ('text-red-600' if not path_exists else 'text-gray-500')
                        ui.label(config['watch_path']).classes(path_label_classes)

                        with ui.row().classes('gap-4 text-xs text-gray-400'):
                            ui.label(f"Patterns: {config['file_patterns']}")
                            ui.label(f"Triggers: {config['trigger_count']}")
                            if config['last_triggered_at']:
                                ui.label(f"Last: {config['last_triggered_at'].strftime('%Y-%m-%d %H:%M')}")

                    # Acciones - Capturar valores explícitamente para evitar problemas de closure
                    config_id = config['id']
                    config_name = config['name']
                    config_copy = dict(config)  # Copia del diccionario para el diálogo de edición

                    with ui.row().classes('gap-2'):
                        if config['is_active']:
                            ui.button(
                                icon='stop',
                                on_click=lambda cid=config_id: stop_config(cid)
                            ).props('flat color=negative').tooltip(t('folder_watcher_stop'))
                        else:
                            ui.button(
                                icon='play_arrow',
                                on_click=lambda cid=config_id: start_config(cid)
                            ).props(f'flat color=positive {"disable" if not path_exists else ""}').tooltip(t('folder_watcher_start'))

                        ui.button(
                            icon='edit',
                            on_click=lambda cfg=config_copy: open_config_dialog(cfg)
                        ).props('flat').tooltip(t('common.edit'))

                        ui.button(
                            icon='delete',
                            on_click=lambda cid=config_id, cname=config_name: confirm_delete(cid, cname)
                        ).props('flat color=negative').tooltip(t('common.delete'))

    async def start_config(config_id: int):
        """Iniciar watcher."""
        # Pre-check path in UI for immediate feedback
        config_data = next((c for c in folders_state.configs if c['id'] == config_id), None)
        if config_data and not config_data.get('watch_path'):
            ui.notify("Error: La ruta de monitoreo esta vacia", type='negative')
            return

        ui.notify(t('folder_watcher_starting'), type='info')
        success, msg = await folder_watcher_service.start_watcher(config_id)
        ui.notify(msg, type='positive' if success else 'negative')
        await load_all()

    async def stop_config(config_id: int):
        """Detener watcher."""
        success, msg = await folder_watcher_service.stop_watcher(config_id)
        ui.notify(msg, type='positive' if success else 'negative')
        await load_all()

    def confirm_delete(config_id: int, name: str):
        """Mostrar confirmación de eliminación."""
        with ui.dialog() as dlg, ui.card():
            ui.label(t('folder_watcher_delete_confirm')).classes('text-lg')
            ui.label(f'"{name}"').classes('font-bold')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=dlg.close).props('flat')

                async def do_delete():
                    success = await folder_watcher_service.delete_config(config_id)
                    dlg.close()
                    if success:
                        ui.notify(t('connections_api_deleted'), type='positive')
                    else:
                        ui.notify(t('logs_status_error'), type='negative')
                    await load_all()

                ui.button(t('common.delete'), on_click=do_delete).props('color=negative')

        dlg.open()

    def open_config_dialog(config: dict = None):
        """Abrir diálogo de crear/editar configuración."""
        is_edit = config is not None
        # Capturar el ID del config para edición (evita problemas de closure)
        config_id = config['id'] if config else None

        with ui.dialog() as dlg, ui.card().classes('w-full max-w-lg'):
            ui.label(
                t('folder_watcher_edit') if is_edit else t('folder_watcher_new')
            ).classes('text-xl font-bold mb-4')

            # Función para validar nombre (obligatorio)
            def validate_name(value: str) -> str | None:
                if not value or not value.strip():
                    return t('validation_required') if hasattr(t, '__call__') else 'Este campo es obligatorio'
                return None

            # Función para validar ruta de Windows
            def validate_path(value: str) -> str | None:
                if not value or not value.strip():
                    return t('validation_required') if hasattr(t, '__call__') else 'Este campo es obligatorio'
                if not is_valid_windows_path(value):
                    return 'Formato de ruta inválido. Usa: C:\\carpeta o \\\\servidor\\carpeta'
                return None

            # Campos del formulario con validación
            name_in = ui.input(
                label=t('folder_watcher_name'),
                value=config['name'] if config else '',
                validation=validate_name
            ).classes('w-full')

            with ui.row().classes('w-full items-center gap-2'):
                path_in = ui.input(
                    label=t('folder_watcher_path'),
                    value=config['watch_path'] if config else '',
                    placeholder='C:\\ruta\\a\\monitorear',
                    validation=validate_path
                ).classes('flex-grow font-mono')

                def select_folder():
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    selected_path = filedialog.askdirectory()
                    root.destroy()
                    if selected_path:
                        path_in.value = selected_path
                        update_save_button()

                ui.button(icon='folder', on_click=select_folder).props('flat color=primary').tooltip('Seleccionar carpeta')

            patterns_in = ui.input(
                label=t('folder_watcher_patterns'),
                value=config['file_patterns'] if config else '*.pdf,*.xml',
                placeholder='*.pdf, *.xlsx'
            ).classes('w-full font-mono')

            with ui.row().classes('w-full gap-4'):
                stabilization_in = ui.number(
                    label=t('folder_watcher_stabilization'),
                    value=config['stabilization_seconds'] if config else 2.0,
                    min=0.5, max=30.0, step=0.5
                ).classes('flex-1')

                recursive_cb = ui.checkbox(
                    t('folder_watcher_recursive'),
                    value=config['recursive'] if config else False
                )

            # Selector de flujo
            flow_options = {f.id: f.name for f in folders_state.flows}
            flow_select = ui.select(
                label=t('folder_watcher_flow'),
                options=flow_options,
                value=config['flow_id'] if config else None
            ).classes('w-full')

            autostart_cb = ui.checkbox(
                t('folder_watcher_autostart'),
                value=config['auto_start'] if config else False
            )

            # Función para verificar si el formulario es válido
            def is_form_valid() -> bool:
                name_valid = name_in.value and name_in.value.strip()
                path_valid = is_valid_windows_path(path_in.value)
                return name_valid and path_valid

            # Función para actualizar estado del botón guardar
            def update_save_button():
                if is_form_valid():
                    save_btn.enable()
                    save_btn.props(remove='disable')
                else:
                    save_btn.disable()
                    save_btn.props(add='disable')

            # Botones
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=dlg.close).props('flat')

                async def save():
                    # Validación final antes de guardar
                    if not is_form_valid():
                        ui.notify('Por favor completa todos los campos obligatorios correctamente', type='warning')
                        return

                    data = {
                        "name": name_in.value.strip(),
                        "watch_path": path_in.value.strip(),
                        "file_patterns": patterns_in.value,
                        "flow_id": flow_select.value,
                        "recursive": recursive_cb.value,
                        "stabilization_seconds": float(stabilization_in.value),
                        "auto_start": autostart_cb.value
                    }

                    # Validación adicional de existencia en disco
                    if not os.path.isdir(data["watch_path"]):
                        ui.notify(f"La ruta no existe en el disco: {data['watch_path']}", type='negative')
                        return

                    try:
                        if is_edit and config_id:
                            await folder_watcher_service.update_config(config_id, data)
                            ui.notify(t('config.saved_successfully'), type='positive')
                        else:
                            await folder_watcher_service.create_config(data)
                            ui.notify(t('folder_watcher_created'), type='positive')

                        dlg.close()
                        await load_all()
                    except Exception as e:
                        ui.notify(f'Error: {e}', type='negative')

                save_btn = ui.button(t('common.save'), icon='save', on_click=save).props('color=primary')

            # Conectar eventos de cambio para actualizar el botón
            name_in.on_value_change(lambda _: update_save_button())
            path_in.on_value_change(lambda _: update_save_button())

            # Estado inicial del botón
            update_save_button()

        dlg.open()

    # Renderizar contenido
    render_folders_content()
    ui.timer(0.1, load_all, once=True)


def render_api_tab():
    """
    Renderiza la pestaña de gestión de conexiones a servicios externos vía API/HTTP.
    """
    t = state.i18n.t
    
    class ApiTabState:
        def __init__(self):
            self.apis = []
            
    api_state = ApiTabState()
    
    async def load_all():
        api_state.apis = await api_load_configs()
        render_api_content.refresh()
        
    @ui.refreshable
    def render_api_content():
        with ui.card().classes('w-full p-4'):
            with ui.row().classes('w-full items-center mb-4'):
                ui.label(t('connections_api_title')).classes('text-lg font-bold')
                ui.space()
                ui.button(t('connections_api_new'), icon='add', 
                          on_click=lambda: open_api_dialog()).props('color=primary')
            
            if not api_state.apis:
                with ui.card().classes('w-full p-8 text-center bg-gray-50'):
                    ui.icon('link_off', size='3em').classes('text-gray-300 mb-2')
                    ui.label(t('connections_api_no_apis')).classes('text-gray-500')
                return

            # Tabla
            rows = []
            for a in api_state.apis:
                rows.append({
                    'id': a['id'],
                    'name': a['name'],
                    'method': a['method'],
                    'url': a['url'],
                    'auth': a.get('auth_type', 'none')
                })
                
            columns = [
                {'name': 'name', 'label': 'Nombre', 'field': 'name', 'align': 'left'},
                {'name': 'method', 'label': 'Método', 'field': 'method', 'align': 'center'},
                {'name': 'url', 'label': 'URL', 'field': 'url', 'align': 'left'},
                {'name': 'auth', 'label': 'Auth', 'field': 'auth', 'align': 'left'},
                {'name': 'actions', 'label': t('common_actions'), 'field': 'actions', 'align': 'right'}
            ]
            
            def render_actions(row):
                # Using lambda to capture specific row
                with ui.row().classes('justify-end gap-2'):
                    async def run_test(rid=row['id']):
                        ui.notify('Probando conexión...', type='info')
                        success, msg, data = await api_test_connection(rid)
                        if success:
                            ui.notify(msg, type='positive')
                            # Show data dialog
                            with ui.dialog() as d, ui.card():
                                ui.label(t('connections_api_response')).classes('text-lg font-bold')
                                ui.json_editor({'content': {'json': data}}).classes('h-64 border rounded')
                                ui.button('Cerrar', on_click=d.close)
                            d.open()
                        else:
                            ui.notify(msg, type='negative')

                    ui.button(icon='play_arrow', on_click=lambda: run_test()).props('flat round dense tooltips="Probar" color=green')
                    
                    ui.button(icon='edit', on_click=lambda r=row: open_api_dialog(r)).props('flat round dense color=blue')

                    async def delete_api(rid=row['id']):
                        if await api_delete_config(rid):
                            ui.notify(t('connections_api_deleted'), type='info')
                            await load_all()
                            
                    ui.button(icon='delete', on_click=lambda: delete_api()).props('flat round dense color=red')

            # Listado de Conexiones (Estilo Acordeón)
            with ui.column().classes('w-full gap-2'):
                for row in rows:
                    # Determinar color según método
                    method_color = 'text-blue-800' if row['method'] == 'GET' else 'text-green-800'
                    bg_color = 'bg-blue-50' if row['method'] == 'GET' else 'bg-green-50'
                    
                    with ui.card().classes('w-full p-0 border no-shadow'):
                        # Header: Método - Nombre
                        header_text = f"[{row['method']}] {row['name']}"
                        
                        with ui.expansion(header_text, icon='api').classes(f'w-full hover:bg-gray-50 transition-colors').props(f'header-class="{method_color}"'):
                            with ui.column().classes('w-full p-4 bg-gray-50 border-t gap-3'):
                                # Detalles
                                with ui.grid(columns=1).classes('w-full gap-2'):
                                    ui.label(t('connections_api_url')).classes('text-xs font-bold text-gray-500')
                                    ui.label(row['url']).classes('font-mono text-sm break-all bg-white p-2 rounded border w-full text-gray-700')
                                    
                                    with ui.row().classes('items-center gap-4 mt-2'):
                                        with ui.column().classes('gap-0'):
                                            ui.label(t('connections_api_auth')).classes('text-xs font-bold text-gray-500')
                                            ui.label(row['auth']).classes('text-sm')
                                            
                                        ui.space()
                                        
                                        # Acciones
                                        render_actions(row)

    def open_api_dialog(config=None):
        with ui.dialog() as dlg, ui.card().classes('w-full max-w-lg'):
            title = t('connections_api_new') if not config else t('connections_api_edit')
            ui.label(title).classes('text-xl font-bold mb-4')
            
            with ui.column().classes('w-full gap-4'):
                name_val = config['name'] if config else ''
                url_val = config['url'] if config else ''
                method_val = config['method'] if config else 'GET'
                auth_val = config.get('auth', 'none') if config else 'none' # Row uses 'auth', check DB model if matches
                # If row object comes from table it has 'auth', but load_all uses 'auth_type'. 
                # Let's check rows construction -> 'auth': a.get('auth_type', 'none')
                # But actual DB model likely has 'auth_type'.
                # Checking rows construction: 'auth': a.get('auth_type', 'none'). So row has 'auth'.
                # But when saving we need to pass what api_save_config expects. 
                # If we pass `row` to dialog, it has `auth`. 
                # Ideally we should fetch full object or mapped properly.
                # Let's map back or use safer 'auth' key from row.
                
                # Careful: The `row` passed to open_api_dialog comes from `rows` list constructed above.
                # keys: id, name, method, url, auth.
                # Headers are missing in `rows` construction! We need headers to edit.
                # To fix this, we should fetch the FULL config or include headers in `rows`.
                # Let's look at `load_all` -> `api_state.apis`. This likely contains full objects dicts.
                # We can find full object by ID from `api_state.apis`.
                
                full_config = None
                if config:
                    # Find full config in state by ID to get headers
                    for api in api_state.apis:
                        if api['id'] == config['id']:
                            full_config = api
                            break
                
                headers_val = full_config.get('headers', '{}') if full_config else '{}'
                if isinstance(headers_val, dict):
                    import json
                    headers_val = json.dumps(headers_val)
                    
                name = ui.input(label='Nombre (Ej: API Clientes)', value=name_val).classes('w-full')
                
                with ui.row().classes('w-full gap-4'):
                    method = ui.select(['GET', 'POST', 'PUT', 'DELETE'], value=method_val, label=t('connections_api_method')).classes('w-32')
                    url = ui.input(label=t('connections_api_url'), value=url_val).classes('flex-grow')
                
                # We need to map 'auth' from row back to 'auth_type' expected by select if using row, 
                # but we are using full_config now.
                auth_val_real = full_config.get('auth_type', 'none') if full_config else 'none'
                auth_type = ui.select(['none', 'bearer', 'basic', 'api_key'], value=auth_val_real, label=t('connections_api_auth')).classes('w-full')
                
                headers = ui.textarea(label=t('connections_api_headers'), value=headers_val, placeholder='{"Content-Type": "application/json"}').classes('w-full font-mono text-xs')

                async def save():
                    new_config = {
                        'name': name.value,
                        'url': url.value,
                        'method': method.value,
                        'auth_type': auth_type.value,
                        'headers': headers.value if headers.value else '{}',
                        'is_active': True
                    }
                    if full_config:
                        new_config['id'] = full_config['id']
                        
                    # Basic JSON validation
                    try:
                        import json
                        if new_config['headers']: json.loads(new_config['headers'])
                    except:
                        ui.notify('Headers inválidos (JSON incorrecto)', type='warning')
                        return

                    try:
                        await api_save_config(new_config)
                        ui.notify(t('connections_api_created'), type='positive')
                        dlg.close()
                        await load_all()
                    except Exception as e:
                        ui.notify(f'Error: {e}', type='negative')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=dlg.close).props('flat')
                ui.button(t('common.save'), icon='save', on_click=save).props('color=primary')
        dlg.open()

    render_api_content()
    ui.timer(0.1, load_all, once=True)


def render_email_tab():
    """Renderiza tab de Monitor de Email (migrado de mail_watcher_page)."""
    t = state.i18n.t

    # Estado local del tab
    class EmailTabState:
        def __init__(self):
            self.config = None
            self.credentials = []
            self.flows = []
            self.status = {"is_running": False}
            self.logs = []

    email_state = EmailTabState()

    # --- FUNCIONES DE CARGA (copiar lógica de mail_watcher_page.py) ---
    async def load_all():
        email_state.config = await email_load_config()
        # Fetch ALL credentials for the table
        email_state.credentials = await mail_watcher_service.list_credentials(service_type=None)
        email_state.status = await mail_watcher_service.get_status()
        email_state.logs = await mail_watcher_service.get_execution_logs(limit=20)

        from client_app.app.database.models import FlowRegistry
        async with state.db_session() as session:
            stmt = select(FlowRegistry).where(FlowRegistry.is_active == True)
            result = await session.execute(stmt)
            email_state.flows = result.scalars().all()

        render_email_content.refresh()

    @ui.refreshable
    def render_email_content():
        # --- SECCIÓN: CONFIGURACIÓN IMAP ---
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label(t('connections_email_accounts_title')).classes('text-lg font-bold mb-4')
            
            # Tabla de credenciales con botones de editar y eliminar
            if email_state.credentials:
                rows = [
                    {
                        'id': c['id'],
                        'name': c['name'], 
                        'service_type': c.get('service_type', 'IMAP'), 
                        'created_at': c['created_at'].strftime('%Y-%m-%d') if c.get('created_at') else '-'
                    } for c in email_state.credentials
                ]
                
                columns = [
                    {'name': 'name', 'label': 'Nombre', 'field': 'name', 'align': 'left'},
                    {'name': 'type', 'label': 'Tipo', 'field': 'service_type', 'align': 'left'},
                    {'name': 'created', 'label': 'Creada', 'field': 'created_at', 'align': 'left'},
                    {'name': 'actions', 'label': 'Acciones', 'field': 'actions', 'align': 'right'}
                ]
                
                # Crear la tabla manualmente con controles personalizados para acciones
                with ui.column().classes('w-full mb-4'):
                    # Cabecera de la tabla
                    with ui.row().classes('w-full flex-nowrap bg-slate-100 p-2 font-bold text-sm text-gray-600 rounded'):
                        ui.label('Nombre').classes('w-1/4 shrink-0')
                        ui.label('Tipo').classes('w-1/6 shrink-0')
                        ui.label('Creada').classes('flex-1')
                        ui.label('Acciones').classes('w-28 text-right shrink-0')

                    # Filas de la tabla
                    for row in rows:
                        with ui.row().classes('w-full flex-nowrap p-2 border-b items-center hover:bg-slate-50 transition-colors'):
                            ui.label(row['name']).classes('w-1/4 shrink-0 truncate font-medium')
                            ui.label(row['service_type']).classes('w-1/6 shrink-0')
                            ui.label(row['created_at']).classes('flex-1 text-xs text-gray-500')

                            with ui.row().classes('w-28 shrink-0 justify-end gap-1'):
                                async def test_c(rid=row['id']):
                                    ui.notify(t('connections_testing'), type='info')
                                    success, msg = await email_test_connection(rid)
                                    ui.notify(msg, type='positive' if success else 'negative')
                                
                                ui.button('', icon='network_check', on_click=lambda rid=row['id']: test_c(rid)).props('flat dense color=green').tooltip(t('connections_test_connection'))

                                ui.button('', icon='edit', on_click=lambda r=row: open_credential_dialog(r)).props('flat dense color=blue').tooltip(t('common.edit'))
                                
                                def confirm_delete(rid=row['id'], rname=row['name']):
                                    async def do_delete():
                                        success = await mail_watcher_service.delete_credential(rid)
                                        dialog.close()
                                        if success:
                                            ui.notify('Credencial eliminada', type='positive')
                                            await load_all()
                                        else:
                                            ui.notify('Error al eliminar la credencial', type='negative')

                                    with ui.dialog() as dialog, ui.card().classes('p-4'):
                                        ui.label(f'¿Estás seguro de que quieres eliminar la credencial: {rname}?').classes('mb-4')
                                        with ui.row().classes('w-full justify-end gap-2'):
                                            ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
                                            ui.button(t('common.delete'), on_click=do_delete).props('color=red')
                                    dialog.open()

                                ui.button('', icon='delete', on_click=lambda rid=row['id'], rname=row['name']: confirm_delete(rid, rname)).props('flat dense color=red').tooltip(t('common.delete'))
            else:
                 ui.label(t('connections_email_no_credentials')).classes('text-gray-500 italic mb-4')

            ui.button(t('connections_new_connection'), icon='add',
                      on_click=lambda: open_credential_dialog()).props('outline')

        # --- SECCIÓN: CONFIGURACIÓN DE MONITOREO ---
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label(t('connections_email_monitor_config')).classes('text-lg font-bold mb-4')

            # Selector de credencial IMAP para monitoreo
            imap_creds = [c for c in email_state.credentials if c.get('service_type', 'IMAP') == 'IMAP']
            cred_options = {c['id']: f"{c['name']}" for c in imap_creds}

            credential_select = ui.select(
                label=t('connections_email_credential'),
                options=cred_options,
                value=email_state.config.get('credential_id') if email_state.config else None
            ).classes('w-full mb-4')

            with ui.grid(columns=2).classes('w-full gap-4'):
                folder_input = ui.input(label=t('connections_email_folder'),
                                        value=email_state.config.get('folder', 'INBOX') if email_state.config else 'INBOX')
                # Intervalo en minutos (internamente se guarda en segundos)
                interval_seconds = email_state.config.get('check_interval', 60) if email_state.config else 60
                interval_input = ui.number(label=t('connections_email_interval_minutes'),
                                           value=max(1, interval_seconds // 60),
                                           min=1, max=60)

            ui.label(t('connections_email_subject_filter')).classes('font-bold mt-4 mb-2')
            subject_filter_value = email_state.config.get('subject_filter', '') if email_state.config else ''
            subject_filter_input = ui.input(
                label=t('connections_email_subject_filter_hint'),
                value=subject_filter_value
            ).classes('w-full')

            ui.label(t('connections_email_whitelist')).classes('font-bold mt-4 mb-2')
            whitelist_value = '\n'.join(email_state.config.get('whitelist_senders', [])) if email_state.config else ''
            whitelist_input = ui.textarea(value=whitelist_value).classes('w-full font-mono').props('rows=3')

        # --- SECCIÓN: ACCIONES ---
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label(t('connections_email_actions')).classes('text-lg font-bold mb-4')

            flow_options = {f.id: f.name for f in email_state.flows}
            flow_select = ui.select(
                label=t('connections_email_workflow'),
                options=flow_options,
                value=email_state.config.get('flow_id') if email_state.config else None
            ).classes('w-full')

        # --- SECCIÓN: PANEL DE CONTROL ---
        with ui.card().classes('w-full p-4 mb-4 bg-slate-50'):
            ui.label(t('connections_email_control')).classes('text-lg font-bold mb-4')

            with ui.row().classes('w-full gap-4 items-center'):
                if email_state.status.get('is_running'):
                    ui.badge(t('connections_status_active'), color='green').classes('text-lg px-4 py-2')
                else:
                    ui.badge(t('connections_status_stopped'), color='red').classes('text-lg px-4 py-2')

                ui.space()

                auto_start_cb = ui.checkbox(t('connections_email_autostart'),
                                            value=email_state.status.get('auto_start', False))

                async def toggle():
                    config = {
                        'credential_id': credential_select.value,
                        'folder': folder_input.value,
                        'check_interval': int(interval_input.value) * 60,  # Convertir minutos a segundos
                        'subject_filter': subject_filter_input.value.strip(),
                        'whitelist_senders': [l.strip() for l in whitelist_input.value.split('\n') if l.strip()],
                        'flow_id': flow_select.value,
                    }
                    success, msg = await email_toggle_watcher(config, auto_start_cb.value)
                    ui.notify(msg, type='positive' if success else 'negative')
                    await load_all()

                if email_state.status.get('is_running'):
                    ui.button(t('connections_stop_monitor'), icon='stop', on_click=toggle).props('color=negative')
                else:
                    ui.button(t('connections_start_monitor'), icon='play_arrow', on_click=toggle).props('color=positive')

    async def open_credential_dialog(edit_credential=None):
        # Obtener datos del objeto edit_credential antes de crear el diálogo
        type_val = edit_credential.get('service_type', 'IMAP') if edit_credential else 'IMAP'
        name_val = edit_credential.get('name', '') if edit_credential else ''
        service_info = None
        if edit_credential:
            service_info = await mail_watcher_service.get_credential(edit_credential['id'])

        # Diálogo de nueva o edición de credencial
        with ui.dialog() as dlg, ui.card().classes('w-full max-w-md'):
            if edit_credential:
                ui.label(t('connections_edit_credential')).classes('text-xl font-bold mb-4')
            else:
                ui.label(t('connections_new_imap_credential')).classes('text-xl font-bold mb-4')
            
            type_select = ui.select(['IMAP', 'SMTP'], value=type_val, label='Tipo').classes('w-full mb-2')
            
            name_in = ui.input(label=t('connections_cred_name'), value=name_val).classes('w-full')
            
            if service_info:
                server_val = service_info.get('server', '')
                port_val = service_info.get('port', 993)
                user_val = service_info.get('user', '')
                use_ssl_val = service_info.get('use_ssl', True)
            else:
                server_val = ''
                port_val = 993 if type_val == 'IMAP' else 587
                user_val = ''
                use_ssl_val = True
            
            server_in = ui.input(label=t('connections_cred_server'), value=server_val, placeholder='imap.gmail.com').classes('w-full')
            port_in = ui.number(label=t('connections_cred_port'), value=port_val).classes('w-full')
            
            def on_type_change(e):
                if e.value == 'SMTP':
                    port_in.value = 587
                    server_in.placeholder = 'smtp.gmail.com'
                else:
                    port_in.value = 993
                    server_in.placeholder = 'imap.gmail.com'
            
            type_select.on_value_change(on_type_change)
            
            user_in = ui.input(label=t('connections_cred_user'), value=user_val).classes('w-full')
            pass_in = ui.input(label=t('connections_cred_password'), password=True, password_toggle_button=True).classes('w-full')
            
            # Si estamos en modo edición, indicamos cómo manejar la contraseña
            if edit_credential:
                ui.label('(Dejar en blanco para mantener la contraseña actual)').classes('text-xs text-gray-500')
            
            ssl_cb = ui.checkbox(t('connections_cred_ssl'), value=use_ssl_val)

            async def save_cred():
                try:
                    if edit_credential:
                        # Modo edición
                        success = await mail_watcher_service.update_credential(
                            credential_id=edit_credential['id'],
                            name=name_in.value,
                            server=server_in.value,
                            port=int(port_in.value),
                            username=user_in.value,
                            password=pass_in.value if pass_in.value != '' else None, # Si está vacío, no actualizamos la contraseña
                            use_ssl=ssl_cb.value,
                            service_type=type_select.value
                        )
                        if success:
                            ui.notify(f'Credencial actualizada', type='positive')
                        else:
                            ui.notify(f'Error al actualizar credencial', type='negative')
                    else:
                        # Modo creación
                        cred_id = await mail_watcher_service.save_credential(
                            name=name_in.value, server=server_in.value, port=int(port_in.value),
                            username=user_in.value, password=pass_in.value, use_ssl=ssl_cb.value,
                            service_type=type_select.value
                        )
                        ui.notify(f'Credencial guardada (ID: {cred_id})', type='positive')
                    
                    dlg.close()
                    await load_all()
                except Exception as e:
                    ui.notify(f'Error: {e}', type='negative')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=dlg.close).props('flat')
                ui.button(t('common.save'), icon='save', on_click=save_cred).props('color=primary')

        dlg.open()

    render_email_content()
    ui.timer(0.1, load_all, once=True)


def render_web_tab():
    """Renderiza tab de Monitor Web (migrado de web_watcher_page)."""
    t = state.i18n.t

    class WebTabState:
        def __init__(self):
            self.watchers = []
            self.flows = []
            self.smtp_credentials = []

    web_state = WebTabState()

    async def load_all():
        web_state.watchers = await web_load_watchers()
        # Cargar credenciales SMTP para notificación directa
        web_state.smtp_credentials = await mail_watcher_service.list_credentials(service_type="SMTP")
        from client_app.app.database.models import FlowRegistry
        async with state.db_session() as session:
            stmt = select(FlowRegistry).where(FlowRegistry.is_active == True)
            result = await session.execute(stmt)
            web_state.flows = result.scalars().all()
        render_web_content.refresh()

    @ui.refreshable
    def render_web_content():
        with ui.card().classes('w-full p-4'):
            with ui.row().classes('w-full items-center mb-4'):
                ui.label(t('connections_web_monitors')).classes('text-lg font-bold')
                ui.space()
                ui.button(t('connections_new_web_monitor'), icon='add',
                          on_click=lambda: open_web_dialog()).props('color=primary')

            if not web_state.watchers:
                with ui.card().classes('w-full p-8 text-center bg-gray-50'):
                    ui.icon('public_off', size='3em').classes('text-gray-300 mb-2')
                    ui.label(t('connections_no_web_monitors')).classes('text-gray-500')
                return

            # Tabla de monitores con acciones
            with ui.column().classes('w-full gap-2'):
                # Header
                with ui.row().classes('w-full bg-slate-100 p-2 font-bold text-sm text-gray-600 rounded'):
                    ui.label('URL').classes('w-1/3')
                    ui.label('Selector').classes('w-1/6')
                    ui.label(t('connections_interval')).classes('w-24 text-center')
                    ui.label(t('connections_status')).classes('w-24 text-center')
                    ui.label(t('connections_last_check')).classes('flex-grow')
                    ui.label(t('common_actions')).classes('w-40 text-right')

                # Rows
                for w in web_state.watchers:
                    with ui.row().classes('w-full p-2 border-b items-center hover:bg-slate-50 transition-colors'):
                        url_display = w['url'][:40] + '...' if len(w['url']) > 40 else w['url']
                        ui.label(url_display).classes('w-1/3 truncate font-mono text-xs').tooltip(w['url'])
                        ui.label(w['selector'][:20]).classes('w-1/6 truncate font-mono text-xs')
                        ui.label(f"{w['check_interval']} min").classes('w-24 text-center text-sm')

                        if w['is_active']:
                            ui.badge(t('connections_status_active'), color='green').classes('w-24')
                        else:
                            ui.badge(t('connections_status_stopped'), color='grey').classes('w-24')

                        last_check = w['last_checked_at'].strftime('%Y-%m-%d %H:%M') if w.get('last_checked_at') else '-'
                        ui.label(last_check).classes('flex-grow text-xs text-gray-500')

                        # Acciones
                        with ui.row().classes('w-40 justify-end gap-1'):
                            if w['is_active']:
                                ui.button(icon='stop', on_click=lambda wid=w['id']: toggle_watcher(wid, False)).props('flat dense color=negative').tooltip(t('connections_stop_monitor'))
                            else:
                                ui.button(icon='play_arrow', on_click=lambda wid=w['id']: toggle_watcher(wid, True)).props('flat dense color=positive').tooltip(t('connections_start_monitor'))

                            ui.button(icon='edit', on_click=lambda watcher=w: open_web_dialog(watcher)).props('flat dense color=blue').tooltip(t('common.edit'))

                            ui.button(icon='account_tree', on_click=lambda watcher=w: create_flow_for_watcher(watcher)).props('flat dense color=purple').tooltip('Crear flujo')

                            ui.button(icon='delete', on_click=lambda wid=w['id']: confirm_delete(wid)).props('flat dense color=red').tooltip(t('common.delete'))

    async def toggle_watcher(watcher_id: int, active: bool):
        """Activar o desactivar un watcher."""
        success = await web_toggle_watcher(watcher_id, active)
        if success:
            ui.notify(t('connections_status_active') if active else t('connections_status_stopped'), type='positive')
        else:
            ui.notify('Error', type='negative')
        await load_all()

    def confirm_delete(watcher_id: int):
        """Confirmar eliminación de watcher."""
        with ui.dialog() as dlg, ui.card().classes('p-4'):
            ui.label(t('folder_watcher_delete_confirm')).classes('mb-4')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel'), on_click=dlg.close).props('flat')

                async def do_delete():
                    success = await web_delete_watcher(watcher_id)
                    dlg.close()
                    if success:
                        ui.notify(t('connections_api_deleted'), type='positive')
                        await load_all()
                    else:
                        ui.notify('Error', type='negative')

                ui.button(t('common.delete'), on_click=do_delete).props('color=negative')
        dlg.open()

    def create_flow_for_watcher(watcher: dict):
        """Redirige a /flows con parámetros del monitor para pre-configurar un FlowSpec."""
        import urllib.parse
        params = {
            'trigger_type': 'web_watcher',
            'web_url': watcher.get('url', ''),
            'web_selector': watcher.get('selector', ''),
            'web_watcher_id': watcher.get('id', '')
        }
        query_string = urllib.parse.urlencode(params)
        ui.navigate.to(f'/flows?{query_string}')

    def open_web_dialog(edit_watcher: dict = None):
        """Abre diálogo de crear/editar monitor web."""
        is_edit = edit_watcher is not None

        with ui.dialog() as dlg, ui.card().classes('w-full max-w-lg'):
            title = t('common.edit') + ' Monitor Web' if is_edit else t('connections_new_web_monitor')
            ui.label(title).classes('text-xl font-bold mb-4')

            # --- URL ---
            url_in = ui.input(
                label='URL',
                value=edit_watcher.get('url', '') if edit_watcher else '',
                placeholder='https://example.com/page'
            ).classes('w-full')

            # --- Selector con tipo ---
            with ui.row().classes('w-full gap-4'):
                selector_type_options = {'css': 'CSS', 'xpath': 'XPath'}
                selector_type_in = ui.select(
                    label='Tipo de selector',
                    options=selector_type_options,
                    value=edit_watcher.get('selector_type', 'css') if edit_watcher else 'css'
                ).classes('w-32')

                selector_in = ui.input(
                    label=t('connections_web_selector'),
                    value=edit_watcher.get('selector', '') if edit_watcher else '',
                    placeholder='#content o //div[@class="content"]'
                ).classes('flex-grow')

            # --- Intervalo con unidad (minutos/horas) ---
            with ui.row().classes('w-full gap-4 items-end'):
                # Calcular valor inicial
                current_interval = edit_watcher.get('check_interval', 60) if edit_watcher else 60
                # Si el intervalo es divisible por 60, mostrar en horas
                if current_interval >= 60 and current_interval % 60 == 0:
                    initial_value = current_interval // 60
                    initial_unit = 'hours'
                else:
                    initial_value = current_interval
                    initial_unit = 'minutes'

                interval_in = ui.number(
                    label=t('connections_interval'),
                    value=initial_value,
                    min=1
                ).classes('flex-grow')

                interval_unit_options = {'minutes': 'Minutos', 'hours': 'Horas'}
                interval_unit_in = ui.select(
                    label='Unidad',
                    options=interval_unit_options,
                    value=initial_unit
                ).classes('w-32')

            # --- Flujo asociado ---
            flow_options = {0: '-- Sin flujo --'}
            flow_options.update({f.id: f.name for f in web_state.flows})
            flow_select = ui.select(
                label=t('connections_web_workflow'),
                options=flow_options,
                value=edit_watcher.get('workflow_id', 0) if edit_watcher else 0
            ).classes('w-full')

            # --- Notificación directa por email ---
            ui.separator().classes('my-4')
            ui.label('Notificación por Email').classes('font-bold')

            send_email_cb = ui.checkbox(
                'Enviar aviso por email al detectar cambios',
                value=edit_watcher.get('send_email_on_change', False) if edit_watcher else False
            )

            # Container para campos SMTP (visible solo si checkbox activo)
            smtp_container = ui.column().classes('w-full gap-2')

            def update_smtp_visibility():
                smtp_container.set_visibility(send_email_cb.value)

            send_email_cb.on_value_change(lambda _: update_smtp_visibility())

            with smtp_container:
                # Dropdown de credenciales SMTP
                smtp_options = {0: '-- Seleccionar credencial SMTP --'}
                smtp_options.update({c['id']: c['name'] for c in web_state.smtp_credentials})

                smtp_select = ui.select(
                    label='Credencial SMTP',
                    options=smtp_options,
                    value=edit_watcher.get('smtp_credential_id', 0) if edit_watcher else 0
                ).classes('w-full')

                notification_email_in = ui.input(
                    label='Email de notificación',
                    value=edit_watcher.get('notification_email', '') if edit_watcher else '',
                    placeholder='admin@miempresa.com'
                ).classes('w-full')

            # Inicializar visibilidad
            update_smtp_visibility()

            # --- Guardar ---
            async def save_web():
                try:
                    # Convertir intervalo a minutos
                    interval_value = int(interval_in.value)
                    if interval_unit_in.value == 'hours':
                        interval_minutes = interval_value * 60
                    else:
                        interval_minutes = interval_value

                    config = {
                        'url': url_in.value,
                        'selector': selector_in.value,
                        'selector_type': selector_type_in.value,
                        'check_interval': interval_minutes,
                        'workflow_id': flow_select.value if flow_select.value != 0 else None,
                        'trigger_workflow': flow_select.value != 0,
                        'send_email_on_change': send_email_cb.value,
                        'smtp_credential_id': smtp_select.value if smtp_select.value != 0 else None,
                        'notification_email': notification_email_in.value if send_email_cb.value else None,
                        'is_active': edit_watcher.get('is_active', False) if edit_watcher else False
                    }

                    if is_edit:
                        await web_watcher_service.update_config(edit_watcher['id'], config)
                        ui.notify('Monitor actualizado', type='positive')
                    else:
                        await web_create_watcher(config)
                        ui.notify(t('connections_web_created'), type='positive')

                    dlg.close()
                    await load_all()
                except Exception as e:
                    ui.notify(f'Error: {e}', type='negative')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=dlg.close).props('flat')
                ui.button(t('common.save'), icon='save', on_click=save_web).props('color=primary')

        dlg.open()

    render_web_content()
    ui.timer(0.1, load_all, once=True)


def render_database_tab():
    """Renderiza tab de Conexiones a Bases de Datos."""
    t = state.i18n.t
    
    class DbTabState:
        def __init__(self):
            self.credentials = []
            
    db_state = DbTabState()
    
    async def load_all():
        async with state.db_session() as session:
            stmt = select(DatabaseCredentialConfig)
            result = await session.execute(stmt)
            db_state.credentials = result.scalars().all()
        render_db_content.refresh()

    def open_db_dialog(cred=None):
        is_edit = cred is not None
        
        with ui.dialog() as dlg, ui.card().classes('w-full max-w-lg'):
            title = t('database_edit') if is_edit else t('database_new')
            ui.label(title).classes('text-xl font-bold mb-4')
            
            # Step header as requested
            if not is_edit:
                ui.label('Paso 1 de 5').classes('text-sm text-primary mb-2 font-bold')
            
            with ui.column().classes('w-full gap-4'):
                name_in = ui.input(label=t('connections_cred_name'), value=cred.name if cred else '').classes('w-full')
                
                db_type_in = ui.select(
                    label='Tipo de Base de Datos',
                    options={'mysql': 'MySQL / MariaDB', 'postgresql': 'PostgreSQL', 'sqlserver': 'SQL Server', 'sqlite': 'SQLite'},
                    value=cred.db_type if cred else 'mysql'
                ).classes('w-full')
                
                # Container for network fields (host, port, user, pass) - hidden for sqlite
                network_fields = ui.column().classes('w-full gap-4 pb-0')
                sqlite_fields = ui.column().classes('w-full gap-4 pb-0')
                
                with network_fields:
                    host_in = ui.input(label='Host / URL del Servidor', value=cred.host if cred else '', placeholder='ej: db.midominio.com o 10.0.0.50').classes('w-full')
                    port_in = ui.number(label='Puerto', value=cred.port if cred else 3306).classes('w-full')
                    user_in = ui.input(label='Usuario', value=cred.username if cred else '').classes('w-full')
                    pass_in = ui.input(label='Contraseña', password=True, password_toggle_button=True).classes('w-full')
                    ssl_cb = ui.checkbox('Usar SSL', value=cred.ssl_enabled if cred else False)
                
                with sqlite_fields:
                    db_path_in = ui.input(label='Ruta archivo SQLite', value=cred.database if cred else '').classes('w-full')
                
                # Standard database name for other types
                db_name_in = ui.input(label='Base de Datos', value=cred.database if cred else '').classes('w-full')

                def update_fields_visibility():
                    is_sqlite = db_type_in.value == 'sqlite'
                    network_fields.set_visibility(not is_sqlite)
                    sqlite_fields.set_visibility(is_sqlite)
                    db_name_in.set_visibility(not is_sqlite)
                    
                    # Puertos por defecto
                    if not is_edit:
                        if db_type_in.value == 'mysql': port_in.value = 3306
                        elif db_type_in.value == 'postgresql': port_in.value = 5432
                        elif db_type_in.value == 'sqlserver': port_in.value = 1433
                
                db_type_in.on_value_change(update_fields_visibility)
                update_fields_visibility()
                
                async def save():
                    try:
                        # Validation
                        if not name_in.value:
                            ui.notify('El nombre es obligatorio', type='warning')
                            return
                        
                        password = pass_in.value
                        encrypted_pw = cred.encrypted_password if cred else ""
                        
                        if password:
                            encrypted_pw = sql_connector_service.encryption.encrypt(password)
                        
                        data = {
                            "name": name_in.value,
                            "db_type": db_type_in.value,
                            "database": db_path_in.value if db_type_in.value == 'sqlite' else db_name_in.value,
                            "host": host_in.value if db_type_in.value != 'sqlite' else "localhost",
                            "port": int(port_in.value) if db_type_in.value != 'sqlite' else 0,
                            "username": user_in.value if db_type_in.value != 'sqlite' else "",
                            "encrypted_password": encrypted_pw,
                            "ssl_enabled": ssl_cb.value if db_type_in.value != 'sqlite' else False,
                            "updated_at": datetime.utcnow()
                        }
                        
                        async with state.db_session() as session:
                            if is_edit:
                                db_cred = await session.get(DatabaseCredentialConfig, cred.id)
                                if db_cred:
                                    for k, v in data.items():
                                        setattr(db_cred, k, v)
                            else:
                                data["created_at"] = datetime.utcnow()
                                db_cred = DatabaseCredentialConfig(**data)
                                session.add(db_cred)
                            
                            await session.commit()
                            ui.notify('Configuración guardada', type='positive')
                            dlg.close()
                            await load_all()
                    except Exception as e:
                        ui.notify(f'Error al guardar: {e}', type='negative')

                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button(t('common.cancel'), on_click=dlg.close).props('flat')
                    ui.button(t('common.save'), icon='save', on_click=save).props('color=primary')
        
        dlg.open()
        
    @ui.refreshable
    def render_db_content():
        with ui.card().classes('w-full p-4'):
            with ui.row().classes('w-full items-center mb-4'):
                ui.label(t('database_title')).classes('text-lg font-bold')
                ui.space()
                ui.button(t('database_new'), icon='add', 
                          on_click=lambda: open_db_dialog()).props('color=primary')
            
            if not db_state.credentials:
                with ui.card().classes('w-full p-8 text-center bg-gray-50'):
                    ui.icon('storage', size='3em').classes('text-gray-300 mb-2')
                    ui.label(t('database_no_configs')).classes('text-gray-500')
                return

            with ui.column().classes('w-full gap-2'):
                # Header
                with ui.row().classes('w-full bg-slate-100 p-2 font-bold text-sm text-gray-600 rounded'):
                    ui.label('Nombre').classes('w-1/4')
                    ui.label('Tipo').classes('w-24 text-center')
                    ui.label('Host / DB').classes('flex-grow')
                    ui.label('Acciones').classes('w-32 text-right')
                
                # Rows
                for cred in db_state.credentials:
                    with ui.row().classes('w-full p-2 border-b items-center hover:bg-slate-50 transition-colors'):
                        ui.label(cred.name).classes('w-1/4 truncate font-medium')
                        
                        db_type_color = 'bg-blue-100 text-blue-800'
                        ui.label(cred.db_type.upper()).classes(f'w-24 text-center text-xs font-bold rounded px-1 py-0.5 {db_type_color}')
                        
                        host_info = f"{cred.host}:{cred.port} ({cred.database})" if cred.db_type != "sqlite" else cred.database
                        ui.label(host_info).classes('flex-grow truncate text-xs text-gray-500 font-mono')
                        
                        with ui.row().classes('w-32 justify-end gap-1'):
                            ui.button(icon='edit', on_click=lambda c=cred: open_db_dialog(c)).props('flat dense color=blue').tooltip(t('common.edit'))
                            async def test_db(cid=cred.id):
                                ui.notify(t('database_testing'), type='info')
                                success, msg = await sql_connector_service.test_connection(cid)
                                ui.notify(msg, type='positive' if success else 'negative')

                            ui.button(icon='network_check', on_click=lambda cid=cred.id: test_db(cid)).props('flat dense color=green').tooltip(t('database_test_connection'))
                            
                            async def delete_db(cid=cred.id):
                                with ui.dialog() as dlg, ui.card().classes('p-4'):
                                    ui.label(t('database_delete_confirm')).classes('mb-4')
                                    with ui.row().classes('w-full justify-end gap-2'):
                                        ui.button(t('common.cancel'), on_click=dlg.close).props('flat')
                                        async def do_delete():
                                            async with state.db_session() as session:
                                                to_del = await session.get(DatabaseCredentialConfig, cid)
                                                if to_del:
                                                    await session.delete(to_del)
                                                    await session.commit()
                                                    ui.notify('Conexión eliminada', type='positive')
                                                    await load_all()
                                            dlg.close()
                                        ui.button(t('common.delete'), on_click=do_delete).props('color=red')
                                dlg.open()

                            ui.button(icon='delete', on_click=lambda cid=cred.id: delete_db(cid)).props('flat dense color=red').tooltip(t('common.delete'))

    render_db_content()
    ui.timer(0.1, load_all, once=True)


# --- PÁGINA PRINCIPAL ---

def connections_page_content():
    """Página unificada de gestión de conexiones."""
    t = state.i18n.t

    ui.label(t('connections_title')).classes('text-2xl font-bold text-slate-800 mb-6')

    with ui.tabs().classes('w-full') as tabs:
        for tab_config in CONNECTION_TABS:
            ui.tab(tab_config['id'], label=t(tab_config['label_key']), icon=tab_config['icon'])

    with ui.tab_panels(tabs, value='email').classes('w-full'):
        with ui.tab_panel('folders'):
            render_folders_tab()
        with ui.tab_panel('api'):
            render_api_tab()
        with ui.tab_panel('email'):
            render_email_tab()
        with ui.tab_panel('web'):
            render_web_tab()
        with ui.tab_panel('database'):
            render_database_tab()
