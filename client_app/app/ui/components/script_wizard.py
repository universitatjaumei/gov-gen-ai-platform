"""
Wizard simplificado para crear scripts desde el editor de flujos.
Prompt 5.2 del plan de refactorización.
Prompt #3 BIS: Integración con Design Sandbox para carga de archivos de muestra.

Proporciona un formulario para crear scripts que puede renderizarse
dentro de un drawer sin salir del editor de flujos.
"""
from typing import Callable, Optional, List
from nicegui import ui
import uuid
from client_app.app.core.state import state


async def render_script_wizard(
    on_save: Callable[[int], None],
    on_cancel: Optional[Callable[[], None]] = None
):
    """
    Renderiza el wizard de creación de scripts.

    Args:
        on_save: Callback con el script_id del script creado
        on_cancel: Callback opcional cuando se cancela
    """
    t = state.i18n.t

    # Generate temporary script ID for sandbox
    temp_script_id = f"temp-{uuid.uuid4().hex[:8]}"

    # Estado del wizard
    wizard_state = {
        'step': 1,
        'name': '',
        'description': '',
        'user_prompt': '',
        'input_type': 'file',
        'output_type': 'file',
        'generated_code': None,
        'generating': False,
        'saving': False,
        'error': None,
        'sandbox_files': [],  # Prompt #3 BIS: Track uploaded sample files
        'temp_script_id': temp_script_id,  # For sandbox operations
    }

    @ui.refreshable
    def wizard_content():
        step = wizard_state['step']

        # Indicador de pasos
        with ui.row().classes('w-full justify-center gap-4 mb-4'):
            for i, label in enumerate(['Información', 'Generar', 'Revisar'], 1):
                is_current = i == step
                is_completed = i < step

                if is_completed:
                    color = 'green'
                elif is_current:
                    color = 'primary'
                else:
                    color = 'grey'

                with ui.column().classes('items-center'):
                    ui.badge(str(i), color=color).props('rounded')
                    ui.label(label).classes(f'text-xs {"font-bold" if is_current else ""}')

        ui.separator().classes('mb-4')

        if step == 1:
            render_step_info()
        elif step == 2:
            render_step_generate()
        elif step == 3:
            render_step_review()

    def render_step_info():
        """Paso 1: Información básica del script."""
        ui.label('Información del Script').classes('text-lg font-bold mb-2')
        ui.label('Define el nombre y propósito del script').classes('text-sm text-gray-600 mb-4')

        # Nombre
        ui.label('Nombre del script *').classes('font-bold text-sm')
        ui.input(
            value=wizard_state['name'],
            placeholder='Ej: Procesar facturas PDF',
            on_change=lambda e: wizard_state.update({'name': e.value})
        ).classes('w-full mb-3').props('outlined dense')

        # Descripción
        ui.label('Descripción').classes('font-bold text-sm')
        ui.textarea(
            value=wizard_state['description'],
            placeholder='Describe qué hace el script...',
            on_change=lambda e: wizard_state.update({'description': e.value})
        ).classes('w-full mb-3').props('outlined rows=2')

        # Tipo de entrada
        ui.label('Tipo de entrada').classes('font-bold text-sm')
        ui.select(
            options={
                'file': 'Archivo',
                'files': 'Múltiples archivos',
                'text': 'Texto',
                'none': 'Sin entrada'
            },
            value=wizard_state['input_type'],
            on_change=lambda e: wizard_state.update({'input_type': e.value})
        ).classes('w-full mb-3').props('outlined dense')

        # Tipo de salida
        ui.label('Tipo de salida').classes('font-bold text-sm')
        ui.select(
            options={
                'file': 'Archivo',
                'text': 'Texto',
                'json': 'Datos JSON',
                'dataframe': 'Tabla de datos'
            },
            value=wizard_state['output_type'],
            on_change=lambda e: wizard_state.update({'output_type': e.value})
        ).classes('w-full mb-4').props('outlined dense')

        # Botones
        with ui.row().classes('w-full justify-between mt-4'):
            ui.button('Cancelar', on_click=lambda: on_cancel() if on_cancel else None).props('flat color=grey')

            def next_step():
                if not wizard_state['name'].strip():
                    ui.notify('El nombre es obligatorio', type='warning')
                    return
                wizard_state['step'] = 2
                wizard_content.refresh()

            ui.button('Siguiente', icon='arrow_forward', on_click=next_step).props('color=primary')

    def render_step_generate():
        """Paso 2: Generar código con IA."""
        ui.label('Describe qué debe hacer el script').classes('text-lg font-bold mb-2')
        ui.label('La IA generará el código basándose en tu descripción').classes('text-sm text-gray-600 mb-4')

        # Prompt del usuario
        ui.label('¿Qué debe hacer el script? *').classes('font-bold text-sm')
        ui.textarea(
            value=wizard_state['user_prompt'],
            placeholder='Describe en detalle qué debe hacer el script.\n\nEjemplo: "Lee un archivo PDF de factura, extrae el número de factura, fecha, importe total y nombre del proveedor, y guarda los datos en un archivo JSON."',
            on_change=lambda e: wizard_state.update({'user_prompt': e.value})
        ).classes('w-full mb-4').props('outlined rows=6')

        # Botón generar
        if wizard_state['generating']:
            with ui.row().classes('w-full justify-center'):
                ui.spinner('dots', size='lg')
                ui.label('Generando script...').classes('ml-2')
        else:
            if wizard_state['error']:
                with ui.row().classes('items-center gap-2 p-2 bg-red-50 rounded mb-4'):
                    ui.icon('error', color='red')
                    ui.label(wizard_state['error']).classes('text-red-700 text-sm')

            async def generate():
                if not wizard_state['user_prompt'].strip():
                    ui.notify('Describe qué debe hacer el script', type='warning')
                    return

                wizard_state['generating'] = True
                wizard_state['error'] = None
                wizard_content.refresh()

                try:
                    from client_app.app.services.script_generator_service import script_generator_service

                    result = await script_generator_service.generate_script(
                        user_prompt=wizard_state['user_prompt'],
                        output_type=wizard_state['output_type']
                    )

                    if result.get('success'):
                        wizard_state['generated_code'] = {
                            'code': result.get('code', ''),
                            'description': result.get('description', wizard_state['description']),
                            'required_libraries': result.get('required_libraries', []),
                            'input_type': result.get('input_type', wizard_state['input_type']),
                            'output_type': result.get('output_type', wizard_state['output_type']),
                        }
                        wizard_state['step'] = 3
                    else:
                        wizard_state['error'] = result.get('error', 'Error al generar el script')

                except Exception as e:
                    wizard_state['error'] = f'Error: {str(e)}'

                wizard_state['generating'] = False
                wizard_content.refresh()

            with ui.row().classes('w-full justify-center'):
                ui.button(
                    'Generar con IA',
                    icon='auto_awesome',
                    on_click=generate
                ).props('color=purple size=lg')

        # Botones navegación
        with ui.row().classes('w-full justify-between mt-6'):
            def prev_step():
                wizard_state['step'] = 1
                wizard_content.refresh()

            ui.button('Anterior', icon='arrow_back', on_click=prev_step).props('flat')
            ui.label('')  # Spacer

    def render_sample_upload_section(input_type: str):
        """
        Prompt #3 BIS: Render file upload section for sample files.

        Allows users to upload sample files that will be used for testing
        the script during the design phase.
        """
        with ui.card().classes('w-full p-3 bg-purple-50 mb-4'):
            with ui.row().classes('items-center gap-2 mb-2'):
                ui.icon('upload_file', color='purple')
                ui.label('Archivos de Muestra').classes('font-bold text-purple-800')

            if input_type == 'file':
                ui.label('Sube un archivo de ejemplo para probar el script').classes('text-xs text-gray-600 mb-2')
            else:
                ui.label('Sube archivos de ejemplo para probar el script').classes('text-xs text-gray-600 mb-2')

            # File list display
            @ui.refreshable
            def file_list():
                if wizard_state['sandbox_files']:
                    for file_info in wizard_state['sandbox_files']:
                        with ui.row().classes('items-center gap-2 p-1 bg-white rounded mb-1'):
                            ui.icon('description', size='sm', color='grey')
                            ui.label(file_info['name']).classes('text-sm flex-grow')
                            ui.label(f"{file_info['size'] // 1024} KB").classes('text-xs text-gray-500')

                            def remove_file(name=file_info['name']):
                                wizard_state['sandbox_files'] = [
                                    f for f in wizard_state['sandbox_files'] if f['name'] != name
                                ]
                                try:
                                    from client_app.app.services.design_sandbox_service import design_sandbox_service
                                    design_sandbox_service.delete_file(wizard_state['temp_script_id'], name)
                                except Exception:
                                    pass
                                file_list.refresh()

                            ui.button(icon='close', on_click=remove_file).props('flat dense size=sm color=red')
                else:
                    ui.label(t('common.no_files_loaded')).classes('text-xs text-gray-400 italic')

            file_list()

            # Upload component
            async def handle_upload(e):
                """Handle file upload to sandbox."""
                try:
                    from client_app.app.services.design_sandbox_service import design_sandbox_service

                    for upload in e.files if hasattr(e, 'files') else [e]:
                        content = upload.content.read() if hasattr(upload.content, 'read') else upload.content
                        filename = upload.name

                        # Save to sandbox
                        saved_path = design_sandbox_service.save_test_file(
                            script_id=wizard_state['temp_script_id'],
                            filename=filename,
                            content=content,
                            input_name='input_file' if input_type == 'file' else None
                        )

                        # Update state
                        wizard_state['sandbox_files'].append({
                            'name': filename,
                            'path': saved_path,
                            'size': len(content)
                        })

                        ui.notify(f'Archivo "{filename}" cargado', type='positive')

                    file_list.refresh()

                except Exception as ex:
                    ui.notify(f'Error al cargar archivo: {ex}', type='negative')

            with ui.row().classes('w-full mt-2'):
                upload_props = 'accept=".pdf,.xlsx,.xls,.csv,.txt,.json"'
                if input_type == 'files':
                    upload_props += ' multiple'

                ui.upload(
                    on_upload=handle_upload,
                    auto_upload=True,
                    label='Subir archivo de muestra'
                ).props(upload_props).classes('w-full')

            # Info text
            with ui.row().classes('items-center gap-1 mt-2'):
                ui.icon('info', size='xs', color='grey')
                ui.label('Los archivos se usarán para pruebas en tiempo de diseño').classes('text-xs text-gray-500')

    def render_step_review():
        """Paso 3: Revisar y guardar."""
        ui.label('Revisar Script Generado').classes('text-lg font-bold mb-2')
        ui.label('Verifica el código y guarda el script').classes('text-sm text-gray-600 mb-4')

        generated = wizard_state['generated_code']

        if generated:
            # Info del script
            with ui.card().classes('w-full p-3 bg-blue-50 mb-4'):
                ui.label(wizard_state['name']).classes('font-bold text-blue-800')
                if generated.get('description'):
                    ui.label(generated['description']).classes('text-sm text-gray-600')

                with ui.row().classes('gap-4 mt-2'):
                    ui.chip(f"Entrada: {generated.get('input_type', 'file')}", icon='input').props('dense size=sm')
                    ui.chip(f"Salida: {generated.get('output_type', 'file')}", icon='output').props('dense size=sm')

                libs = generated.get('required_libraries', [])
                if libs:
                    with ui.row().classes('gap-1 mt-2 flex-wrap'):
                        ui.label('Librerías:').classes('text-xs text-gray-500')
                        for lib in libs[:5]:
                            ui.chip(lib, icon='code').props('dense size=sm color=grey')

            # Prompt #3 BIS: Sample File Upload Section
            input_type = generated.get('input_type', wizard_state['input_type'])
            if input_type in ('file', 'files'):
                render_sample_upload_section(input_type)

            # Preview del código
            ui.label('Código generado').classes('font-bold text-sm mb-1')
            with ui.card().classes('w-full p-0 bg-gray-900'):
                ui.code(generated.get('code', ''), language='python').classes('w-full max-h-60 overflow-auto')

            # Advertencia
            with ui.row().classes('items-center gap-2 p-2 bg-orange-50 rounded mt-4'):
                ui.icon('warning', color='orange')
                ui.label('El script se guardará como borrador. Deberás validarlo antes de usarlo en flujos.').classes('text-xs text-orange-700')

        # Botones
        with ui.row().classes('w-full justify-between mt-4'):
            def prev_step():
                wizard_state['step'] = 2
                wizard_content.refresh()

            ui.button('Anterior', icon='arrow_back', on_click=prev_step).props('flat')

            if wizard_state['saving']:
                ui.spinner('dots')
            else:
                async def save_script():
                    wizard_state['saving'] = True
                    wizard_content.refresh()

                    try:
                        from client_app.app.services.custom_script_service import custom_script_service

                        generated = wizard_state['generated_code']

                        script = await custom_script_service.create_script(
                            name=wizard_state['name'],
                            user_prompt=wizard_state['user_prompt'],
                            code=generated.get('code', ''),
                            description=generated.get('description', wizard_state['description']),
                            required_libraries=generated.get('required_libraries', []),
                            input_type=generated.get('input_type', wizard_state['input_type']),
                            output_type=generated.get('output_type', wizard_state['output_type']),
                        )

                        ui.notify(f'Script "{wizard_state["name"]}" creado correctamente', type='positive')

                        # Llamar callback con el ID del script
                        on_save(script.script_id)

                    except Exception as e:
                        ui.notify(f'Error al guardar: {str(e)}', type='negative')
                        wizard_state['saving'] = False
                        wizard_content.refresh()

                ui.button(
                    'Guardar Script',
                    icon='save',
                    on_click=save_script
                ).props('color=green')

    # Renderizar contenido inicial
    wizard_content()
