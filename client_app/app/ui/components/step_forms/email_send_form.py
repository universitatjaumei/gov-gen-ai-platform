"""
Formulario de configuración para pasos EMAIL_SEND.
Prompt 3.2 del plan de refactorización del editor de flujos.

Proporciona un formulario visual completo para configurar envío de emails.
"""
from typing import Callable, Optional, List
from nicegui import ui
from automatia_shared.dtos import TaskSpec, FlowSpec


async def render_email_send_form(
    step: TaskSpec,
    flow: FlowSpec = None,
    on_change: Optional[Callable] = None
):
    """
    Renderiza el formulario de configuración para un paso EMAIL_SEND.

    Args:
        step: El TaskSpec del paso a configurar
        flow: El FlowSpec completo (para obtener variables de pasos anteriores)
        on_change: Callback opcional que se llama cuando cambia cualquier campo
    """
    from client_app.app.services.resource_listing_service import resource_listing_service

    config = step.config or {}

    def update_config(key: str, value):
        """Actualiza un campo de la configuración y notifica el cambio."""
        step.config[key] = value
        if on_change:
            on_change()

    # Obtener variables disponibles de pasos anteriores
    available_vars: List[str] = []
    if flow:
        try:
            from client_app.app.services.data_flow_analyzer import data_flow_analyzer
            step_index = flow.steps.index(step) if step in flow.steps else -1
            if step_index > 0:
                available_vars = data_flow_analyzer.get_available_variables(flow, step_index)
        except Exception:
            pass

    with ui.column().classes('w-full gap-4'):
        # === Credencial SMTP (obligatorio) ===
        credential_id = config.get('credential_id')
        is_credential_empty = not credential_id

        with ui.row().classes('items-center gap-1'):
            ui.label('Cuenta SMTP').classes('font-bold')
            if is_credential_empty:
                ui.label('*').classes('text-red-500 font-bold')

        # Cargar credenciales SMTP disponibles
        smtp_creds = await resource_listing_service.list_credentials(service_type="SMTP")

        if not smtp_creds:
            with ui.row().classes('items-center gap-2 p-3 bg-orange-50 rounded border border-orange-200'):
                ui.icon('warning', color='orange')
                ui.label('No hay credenciales SMTP configuradas.').classes('text-orange-700')
                ui.button(
                    'Configurar credenciales',
                    icon='settings',
                    on_click=lambda: ui.notify('Ve a Conexiones > Credenciales para añadir una cuenta SMTP', type='info')
                ).props('flat dense color=orange')
        else:
            cred_opts = {c['id']: c['name'] for c in smtp_creds}
            ui.select(
                options=cred_opts,
                value=credential_id,
                label='Seleccionar cuenta SMTP',
                on_change=lambda e: update_config('credential_id', e.value)
            ).classes('w-full').props('outlined dense')

        if is_credential_empty and smtp_creds:
            ui.label('Debe seleccionar una cuenta SMTP').classes('text-red-500 text-xs -mt-2')

        ui.separator().classes('my-2')

        # === Destinatarios ===
        ui.label('Destinatarios').classes('font-bold text-lg')

        # Para (obligatorio)
        to_value = config.get('to', '')
        is_to_empty = not to_value

        with ui.row().classes('items-center gap-1'):
            ui.label('Para').classes('font-bold')
            if is_to_empty:
                ui.label('*').classes('text-red-500 font-bold')

        ui.input(
            value=to_value,
            placeholder='usuario@ejemplo.com, otro@ejemplo.com',
            on_change=lambda e: update_config('to', e.value)
        ).classes('w-full').props('outlined dense')

        if is_to_empty:
            ui.label('El destinatario es obligatorio').classes('text-red-500 text-xs -mt-2')

        ui.label('Separa múltiples destinatarios con coma').classes('text-xs text-gray-500 -mt-2')

        # CC (opcional)
        with ui.row().classes('items-center gap-1'):
            ui.label('CC').classes('font-bold')
            ui.label('(opcional)').classes('text-gray-400 text-sm')

        cc_value = config.get('cc', '')
        ui.input(
            value=cc_value,
            placeholder='copia@ejemplo.com',
            on_change=lambda e: update_config('cc', e.value)
        ).classes('w-full').props('outlined dense')

        # CCO (opcional)
        with ui.row().classes('items-center gap-1'):
            ui.label('CCO').classes('font-bold')
            ui.label('(opcional)').classes('text-gray-400 text-sm')

        bcc_value = config.get('bcc', '')
        ui.input(
            value=bcc_value,
            placeholder='oculto@ejemplo.com',
            on_change=lambda e: update_config('bcc', e.value)
        ).classes('w-full').props('outlined dense')

        ui.separator().classes('my-2')

        # === Contenido del correo ===
        ui.label('Contenido').classes('font-bold text-lg')

        # Asunto (obligatorio)
        subject_value = config.get('subject', '')
        is_subject_empty = not subject_value

        with ui.row().classes('items-center gap-1'):
            ui.label('Asunto').classes('font-bold')
            if is_subject_empty:
                ui.label('*').classes('text-red-500 font-bold')

        ui.input(
            value=subject_value,
            placeholder='Asunto del correo',
            on_change=lambda e: update_config('subject', e.value)
        ).classes('w-full').props('outlined dense')

        if is_subject_empty:
            ui.label('El asunto es obligatorio').classes('text-red-500 text-xs -mt-2')

        # Cuerpo del mensaje
        with ui.row().classes('items-center gap-1'):
            ui.label('Cuerpo del mensaje').classes('font-bold')

        body_value = config.get('body', '')
        ui.textarea(
            value=body_value,
            placeholder='Escriba el contenido del correo aquí...\n\nPuede usar {{variable}} para insertar datos de pasos anteriores.',
            on_change=lambda e: update_config('body', e.value)
        ).classes('w-full').props('outlined rows=8')

        # Ayuda para variables
        if available_vars:
            with ui.expansion('Variables disponibles', icon='data_object').classes('w-full bg-blue-50'):
                with ui.column().classes('p-2 gap-2'):
                    ui.label('Haz clic en una variable para insertarla:').classes('text-xs text-gray-600')
                    with ui.row().classes('flex-wrap gap-1'):
                        for var in available_vars:
                            def insert_var(v=var):
                                current_body = step.config.get('body', '')
                                step.config['body'] = current_body + '{{' + v + '}}'
                                if on_change:
                                    on_change()
                                ui.notify(f'Variable {{{{{v}}}}} añadida al cuerpo', type='positive')

                            ui.button(
                                f'{{{{{var}}}}}',
                                on_click=insert_var
                            ).props('flat dense size=sm color=primary')

        ui.separator().classes('my-2')

        # === Adjuntos ===
        ui.label('Adjuntos').classes('font-bold text-lg')

        attachments_value = config.get('attachments', '')

        with ui.column().classes('w-full gap-2'):
            # Usar el selector visual de variables para archivos
            from client_app.app.ui.components.variable_selector import render_file_variable_selector

            render_file_variable_selector(
                flow=flow,
                current_step_index=flow.steps.index(step) if step in flow.steps else 0,
                current_value=attachments_value,
                on_change=lambda v: update_config('attachments', v),
                label='Variable con archivo(s) a adjuntar'
            )

        ui.separator().classes('my-2')

        # === Opciones avanzadas ===
        with ui.expansion('Opciones avanzadas', icon='settings').classes('w-full'):
            with ui.column().classes('w-full gap-3 p-2'):
                # Formato HTML
                is_html = config.get('is_html', False)
                ui.checkbox(
                    'Enviar como HTML',
                    value=is_html,
                    on_change=lambda e: update_config('is_html', e.value)
                )

                # Prioridad
                ui.label('Prioridad').classes('font-bold text-sm mt-2')
                priority = config.get('priority', 'normal')
                ui.select(
                    options={
                        'high': 'Alta',
                        'normal': 'Normal',
                        'low': 'Baja'
                    },
                    value=priority,
                    on_change=lambda e: update_config('priority', e.value)
                ).classes('w-48').props('outlined dense')

                # Reply-To
                ui.label('Responder a (Reply-To)').classes('font-bold text-sm mt-2')
                reply_to = config.get('reply_to', '')
                ui.input(
                    value=reply_to,
                    placeholder='respuestas@ejemplo.com',
                    on_change=lambda e: update_config('reply_to', e.value)
                ).classes('w-full').props('outlined dense')

        ui.separator().classes('my-2')

        # === Botón de prueba ===
        with ui.card().classes('w-full p-3 bg-green-50 border border-green-200'):
            ui.label('Probar envío').classes('font-bold text-green-800')
            ui.label('Envía un correo de prueba para verificar la configuración').classes('text-sm text-green-700 mb-2')

            test_email_input = ui.input(
                placeholder='tu-email@ejemplo.com',
                value=''
            ).classes('w-full mb-2').props('outlined dense label="Email de prueba"')

            async def send_test_email():
                test_dest = test_email_input.value
                if not test_dest:
                    ui.notify('Introduce un email de destino para la prueba', type='warning')
                    return

                if not config.get('credential_id'):
                    ui.notify('Selecciona una cuenta SMTP primero', type='warning')
                    return

                ui.notify(f'Enviando correo de prueba a {test_dest}...', type='info')

                try:
                    # Importar el servicio de email
                    from client_app.app.services.mail_watcher_service import mail_watcher_service

                    # Intentar enviar
                    result = await mail_watcher_service.send_test_email(
                        credential_id=config.get('credential_id'),
                        to_email=test_dest,
                        subject=config.get('subject', 'Correo de prueba'),
                        body=config.get('body', 'Este es un correo de prueba desde el editor de flujos.')
                    )

                    if result.get('success'):
                        ui.notify('Correo de prueba enviado correctamente', type='positive')
                    else:
                        ui.notify(f'Error al enviar: {result.get("error", "Error desconocido")}', type='negative')

                except AttributeError:
                    # Si el método no existe, mostrar mensaje informativo
                    ui.notify('Función de prueba no disponible. Verifica la configuración al ejecutar el flujo.', type='warning')
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', type='negative')

            ui.button(
                'Enviar correo de prueba',
                icon='send',
                on_click=send_test_email
            ).props('color=green')

        # === Resumen de configuración ===
        ui.separator().classes('my-2')
        with ui.row().classes('items-center gap-2 bg-blue-50 p-2 rounded'):
            ui.icon('email', color='blue')
            to_display = config.get('to', '(sin destinatario)')
            subject_display = config.get('subject', '(sin asunto)')
            ui.label(f'Para: {to_display} | Asunto: {subject_display}').classes('text-sm text-blue-800')
