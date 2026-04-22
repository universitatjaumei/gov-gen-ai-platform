"""
Formulario de configuración para pasos API_FETCH.
Prompt 3.1 del plan de refactorización del editor de flujos.

Proporciona un formulario visual completo sin necesidad de editar JSON.
"""
from typing import Callable, Optional
from nicegui import ui
from automatia_shared.dtos import TaskSpec


def render_api_fetch_form(step: TaskSpec, on_change: Optional[Callable] = None):
    """
    Renderiza el formulario de configuración para un paso API_FETCH.

    Args:
        step: El TaskSpec del paso a configurar
        on_change: Callback opcional que se llama cuando cambia cualquier campo
    """
    config = step.config or {}

    def update_config(key: str, value):
        """Actualiza un campo de la configuración y notifica el cambio."""
        step.config[key] = value
        if on_change:
            on_change()

    def update_header(idx: int, key: str = None, value: str = None, delete: bool = False):
        """Actualiza los headers en la configuración."""
        headers = step.config.get('headers', {})
        if isinstance(headers, list):
            # Convertir de lista a diccionario si es necesario
            headers = {h.get('key', ''): h.get('value', '') for h in headers if h.get('key')}

        if delete:
            # Eliminar header por índice
            keys = list(headers.keys())
            if idx < len(keys):
                del headers[keys[idx]]
        elif key is not None:
            # Actualizar o añadir header
            old_keys = list(headers.keys())
            if idx < len(old_keys):
                old_key = old_keys[idx]
                old_value = headers.pop(old_key)
                if key:  # Solo si la nueva key no está vacía
                    headers[key] = value if value is not None else old_value
            else:
                if key:
                    headers[key] = value or ''

        step.config['headers'] = headers
        if on_change:
            on_change()
        headers_section.refresh()

    with ui.column().classes('w-full gap-4'):
        # === URL (obligatorio) ===
        url_value = config.get('url', '')
        is_url_empty = not url_value

        with ui.row().classes('items-center gap-1'):
            ui.label('URL').classes('font-bold')
            if is_url_empty:
                ui.label('*').classes('text-red-500 font-bold')

        ui.input(
            value=url_value,
            placeholder='https://api.ejemplo.com/datos',
            on_change=lambda e: update_config('url', e.value)
        ).classes('w-full').props('outlined dense')

        if is_url_empty:
            ui.label('La URL es obligatoria').classes('text-red-500 text-xs -mt-2')

        # === Método HTTP ===
        with ui.row().classes('items-center gap-1'):
            ui.label('Método HTTP').classes('font-bold')

        current_method = config.get('method', 'GET')
        method_select = ui.select(
            options=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
            value=current_method,
            on_change=lambda e: (update_config('method', e.value), body_section.refresh())
        ).classes('w-full').props('outlined dense')

        # === Headers (colapsable) ===
        @ui.refreshable
        def headers_section():
            headers = config.get('headers', {})
            if isinstance(headers, list):
                headers = {h.get('key', ''): h.get('value', '') for h in headers if h.get('key')}

            with ui.expansion('Headers', icon='code').classes('w-full'):
                with ui.column().classes('w-full gap-2 p-2'):
                    ui.label('Añade headers personalizados para la petición').classes('text-xs text-gray-500')

                    # Lista de headers existentes
                    header_items = list(headers.items())
                    for idx, (key, value) in enumerate(header_items):
                        with ui.row().classes('w-full items-center gap-2'):
                            ui.input(
                                value=key,
                                placeholder='Header-Name',
                                on_change=lambda e, i=idx, v=value: update_header(i, key=e.value, value=v)
                            ).classes('flex-1').props('outlined dense')
                            ui.input(
                                value=value,
                                placeholder='valor',
                                on_change=lambda e, i=idx, k=key: update_header(i, key=k, value=e.value)
                            ).classes('flex-1').props('outlined dense')
                            ui.button(
                                icon='delete',
                                on_click=lambda i=idx: update_header(i, delete=True)
                            ).props('flat dense round color=red')

                    # Botón para añadir nuevo header
                    def add_new_header():
                        headers = step.config.get('headers', {})
                        if isinstance(headers, list):
                            headers = {h.get('key', ''): h.get('value', '') for h in headers if h.get('key')}
                        # Buscar un nombre único
                        new_key = 'New-Header'
                        counter = 1
                        while new_key in headers:
                            new_key = f'New-Header-{counter}'
                            counter += 1
                        headers[new_key] = ''
                        step.config['headers'] = headers
                        headers_section.refresh()

                    ui.button('Añadir Header', icon='add', on_click=add_new_header).props('flat dense color=primary')

                    # Headers comunes como sugerencia
                    ui.separator().classes('my-2')
                    ui.label('Headers comunes:').classes('text-xs text-gray-400')
                    with ui.row().classes('gap-1 flex-wrap'):
                        common_headers = [
                            ('Content-Type', 'application/json'),
                            ('Authorization', 'Bearer '),
                            ('Accept', 'application/json'),
                        ]
                        for h_key, h_value in common_headers:
                            def add_common(k=h_key, v=h_value):
                                headers = step.config.get('headers', {})
                                if isinstance(headers, list):
                                    headers = {h.get('key', ''): h.get('value', '') for h in headers if h.get('key')}
                                if k not in headers:
                                    headers[k] = v
                                    step.config['headers'] = headers
                                    headers_section.refresh()
                                    if on_change:
                                        on_change()

                            ui.button(h_key, on_click=add_common).props('flat dense size=sm outline')

        headers_section()

        # === Body (solo para POST/PUT/PATCH) ===
        @ui.refreshable
        def body_section():
            current_method = step.config.get('method', 'GET')
            if current_method in ['POST', 'PUT', 'PATCH']:
                with ui.column().classes('w-full gap-1'):
                    ui.label('Cuerpo de la petición (Body)').classes('font-bold')
                    ui.label('JSON o texto plano a enviar').classes('text-xs text-gray-500')

                    body_value = config.get('body', '')
                    ui.textarea(
                        value=body_value,
                        placeholder='{"key": "value"}',
                        on_change=lambda e: update_config('body', e.value)
                    ).classes('w-full font-mono text-sm').props('outlined rows=5')

                    # Ayuda para usar variables
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('info', color='blue').classes('text-sm')
                        ui.label('Usa {{variable}} para insertar datos de pasos anteriores').classes('text-xs text-blue-600')

        body_section()

        # === Timeout ===
        with ui.row().classes('items-center gap-1'):
            ui.label('Timeout (segundos)').classes('font-bold')

        timeout_value = config.get('timeout', 30)
        ui.number(
            value=timeout_value,
            min=1,
            max=300,
            step=1,
            format='%.0f',
            on_change=lambda e: update_config('timeout', int(e.value) if e.value else 30)
        ).classes('w-32').props('outlined dense')
        ui.label('Tiempo máximo de espera para la respuesta').classes('text-xs text-gray-500')

        # === Opciones avanzadas ===
        with ui.expansion('Opciones avanzadas', icon='settings').classes('w-full'):
            with ui.column().classes('w-full gap-3 p-2'):
                # Seguir redirecciones
                follow_redirects = config.get('follow_redirects', True)
                ui.checkbox(
                    'Seguir redirecciones automáticamente',
                    value=follow_redirects,
                    on_change=lambda e: update_config('follow_redirects', e.value)
                )

                # Verificar SSL
                verify_ssl = config.get('verify_ssl', True)
                ui.checkbox(
                    'Verificar certificado SSL',
                    value=verify_ssl,
                    on_change=lambda e: update_config('verify_ssl', e.value)
                )

                # Reintentos
                ui.label('Reintentos en caso de error').classes('font-bold text-sm mt-2')
                retries = config.get('retries', 0)
                ui.number(
                    value=retries,
                    min=0,
                    max=5,
                    step=1,
                    format='%.0f',
                    on_change=lambda e: update_config('retries', int(e.value) if e.value else 0)
                ).classes('w-32').props('outlined dense')

        # === Resumen de configuración ===
        ui.separator().classes('my-2')
        with ui.row().classes('items-center gap-2 bg-blue-50 p-2 rounded'):
            ui.icon('info', color='blue')
            method = config.get('method', 'GET')
            url = config.get('url', '(sin URL)')
            ui.label(f'{method} {url}').classes('text-sm font-mono text-blue-800')
