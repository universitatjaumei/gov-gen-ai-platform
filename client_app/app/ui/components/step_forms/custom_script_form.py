"""
Formulario de configuración para pasos CUSTOM_SCRIPT.
Prompt 3.4 del plan de refactorización del editor de flujos.

Proporciona un formulario visual para configurar ejecución de scripts personalizados.
IMPORTANTE: Nunca muestra el código del script en el editor de flujos.

Actualizado en Prompt 5.2 para usar SideDrawer con wizard de creación de scripts.
"""
from typing import Callable, Optional, List
from nicegui import ui
from automatia_shared.dtos import TaskSpec, FlowSpec

from client_app.app.ui.components.side_drawer import SideDrawer
from client_app.app.ui.components.script_wizard import render_script_wizard


async def render_custom_script_form(
    step: TaskSpec,
    flow: FlowSpec = None,
    on_change: Optional[Callable] = None
):
    """
    Renderiza el formulario de configuración para un paso CUSTOM_SCRIPT.

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
            if step_index >= 0:
                available_vars = data_flow_analyzer.get_available_variables(flow, step_index)
        except Exception:
            pass

    with ui.column().classes('w-full gap-4'):
        # === Script (obligatorio) ===
        script_id = config.get('script_id')
        is_script_empty = not script_id

        with ui.row().classes('items-center gap-1'):
            ui.label('Script a ejecutar').classes('font-bold')
            if is_script_empty:
                ui.label('*').classes('text-red-500 font-bold')

        # Cargar scripts disponibles (solo validados o publicados)
        all_scripts = await resource_listing_service.list_custom_scripts()

        # Filtrar solo scripts validados o publicados
        scripts = [
            s for s in all_scripts
            if s.get('status') in ('validated', 'published', 'active')
        ] if all_scripts else []

        # Variable para almacenar info del script seleccionado
        selected_script_data = None

        # Funciones para el drawer de creación de scripts
        drawer_ref = {'drawer': None}

        async def open_script_wizard():
            """Abre el drawer con el wizard de creación de scripts."""
            drawer = SideDrawer('Crear Nuevo Script', width='w-1/2')

            def on_script_created(script_id: int):
                """Callback cuando se crea un nuevo script."""
                drawer.close(script_id)
                # Actualizar la configuración con el nuevo script
                update_config('script_id', script_id)
                ui.notify(f'Script creado y seleccionado', type='positive')
                # Refrescar el formulario completo (esto se maneja desde el padre)
                if on_change:
                    on_change()

            def on_cancel():
                """Callback cuando se cancela el wizard."""
                drawer.close(None)

            drawer_ref['drawer'] = drawer
            drawer.open(lambda: None)  # Placeholder, se renderiza async abajo

            # Renderizar el wizard dentro del drawer
            if drawer._content_container:
                drawer._content_container.clear()
                with drawer._content_container:
                    await render_script_wizard(
                        on_save=on_script_created,
                        on_cancel=on_cancel
                    )

        if not scripts:
            with ui.card().classes('w-full p-4 bg-orange-50 border border-orange-200'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('warning', color='orange').classes('text-2xl')
                    with ui.column().classes('gap-1'):
                        ui.label('No hay scripts validados disponibles').classes('font-bold text-orange-800')
                        ui.label('Los scripts deben estar validados antes de usarse en flujos.').classes('text-sm text-orange-700')

                ui.separator().classes('my-2')

                ui.button(
                    'Crear nuevo script',
                    icon='add',
                    on_click=open_script_wizard
                ).props('color=orange')
        else:
            # Crear opciones para el select
            script_opts = {s['script_id']: s['name'] for s in scripts}

            # Buscar el script seleccionado actualmente
            if script_id:
                selected_script_data = next(
                    (s for s in scripts if s['script_id'] == script_id),
                    None
                )

            @ui.refreshable
            def script_selector():
                nonlocal selected_script_data

                def on_script_change(e):
                    nonlocal selected_script_data
                    new_id = int(e.value) if e.value else None
                    update_config('script_id', new_id)
                    selected_script_data = next(
                        (s for s in scripts if s['script_id'] == new_id),
                        None
                    )
                    script_info.refresh()

                with ui.row().classes('w-full items-end gap-2'):
                    ui.select(
                        options=script_opts,
                        value=script_id,
                        label='Seleccionar script',
                        on_change=on_script_change
                    ).classes('flex-1').props('outlined dense')

                    ui.button(
                        icon='add',
                        on_click=open_script_wizard
                    ).props('flat color=primary').tooltip('Crear nuevo script')

            script_selector()

            if is_script_empty:
                ui.label('Debe seleccionar un script').classes('text-red-500 text-xs -mt-2')

            # Información del script seleccionado
            @ui.refreshable
            def script_info():
                if selected_script_data:
                    with ui.card().classes('w-full p-3 bg-blue-50 border border-blue-200 mt-2'):
                        with ui.row().classes('items-start gap-3'):
                            ui.icon('code', color='blue').classes('text-2xl mt-1')
                            with ui.column().classes('flex-1 gap-1'):
                                ui.label(selected_script_data.get('name', 'Script')).classes('font-bold text-blue-800')

                                # Descripción
                                description = selected_script_data.get('description')
                                if description:
                                    ui.label(description).classes('text-sm text-gray-600')

                        ui.separator().classes('my-2')

                        # Tipo de entrada
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('input', color='green').classes('text-sm')
                            input_type = selected_script_data.get('input_type', 'file')
                            input_desc = selected_script_data.get('input_description', '')
                            input_extensions = selected_script_data.get('input_extensions', [])

                            input_text = f"Entrada: {input_type}"
                            if input_extensions:
                                input_text += f" ({', '.join(input_extensions)})"
                            if input_desc:
                                input_text += f" - {input_desc}"

                            ui.label(input_text).classes('text-sm text-gray-700')

                        # Tipo de salida
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('output', color='purple').classes('text-sm')
                            output_type = selected_script_data.get('output_type', 'file')
                            output_desc = selected_script_data.get('output_description', '')

                            output_text = f"Salida: {output_type}"
                            if output_desc:
                                output_text += f" - {output_desc}"

                            ui.label(output_text).classes('text-sm text-gray-700')

                        # Tags si existen
                        tags = selected_script_data.get('tags', [])
                        if tags:
                            ui.separator().classes('my-2')
                            with ui.row().classes('flex-wrap gap-1'):
                                for tag in tags[:5]:
                                    ui.chip(tag, icon='label').props('dense size=sm color=grey')

                        # Estadísticas si existen
                        exec_count = selected_script_data.get('execution_count', 0)
                        success_count = selected_script_data.get('success_count', 0)
                        if exec_count > 0:
                            ui.separator().classes('my-2')
                            success_rate = (success_count / exec_count * 100) if exec_count > 0 else 0
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('analytics', color='grey').classes('text-sm')
                                ui.label(f'{exec_count} ejecuciones • {success_rate:.0f}% éxito').classes('text-xs text-gray-500')

            script_info()

        ui.separator().classes('my-2')

        # === Entrada del script ===
        ui.label('Datos de entrada').classes('font-bold text-lg')

        with ui.column().classes('w-full gap-2'):
            ui.label('Variable con los datos a procesar por el script').classes('text-sm text-gray-600')

            current_input = config.get('input_mapping', {}).get('file', '')

            # Usar el selector visual de variables
            from client_app.app.ui.components.variable_selector import render_variable_input

            def on_input_change(value):
                # Limpiar el valor de {{ }} si existe
                clean_value = value.strip('{}').strip() if value else ''
                update_config('input_mapping', {'file': clean_value})

            render_variable_input(
                flow=flow,
                current_step_index=flow.steps.index(step) if step in flow.steps else 0,
                current_value=f'{{{{{current_input}}}}}' if current_input and not current_input.startswith('{{') else current_input,
                on_change=on_input_change,
                label='Origen de datos',
                placeholder='Seleccionar variable de entrada...',
                allow_manual=True
            )

            # Hint sobre la entrada
            with ui.row().classes('items-center gap-2'):
                ui.icon('info', color='blue').classes('text-sm')
                ui.label('El script recibirá estos datos como entrada').classes('text-xs text-blue-600')

        ui.separator().classes('my-2')

        # === Variable de salida ===
        ui.label('Resultado').classes('font-bold text-lg')

        with ui.column().classes('w-full gap-2'):
            ui.label('Nombre de la variable donde guardar el resultado del script').classes('text-sm text-gray-600')

            # Sugerir nombre basado en el índice del paso
            suggested_name = 'resultado_script'
            if flow and step in flow.steps:
                step_index = flow.steps.index(step)
                suggested_name = f'script_paso_{step_index + 1}'

            output_var = config.get('output_var', '')
            ui.input(
                value=output_var,
                placeholder=suggested_name,
                on_change=lambda e: update_config('output_var', e.value)
            ).classes('w-full').props('outlined dense label="Nombre de variable"')

            ui.label(
                f'El resultado estará disponible como {{{{{output_var or suggested_name}}}}}'
            ).classes('text-xs text-blue-600')

        ui.separator().classes('my-2')

        # === Opciones avanzadas ===
        with ui.expansion('Opciones avanzadas', icon='settings').classes('w-full'):
            with ui.column().classes('w-full gap-3 p-2'):
                # Timeout
                ui.label('Timeout de ejecución (segundos)').classes('font-bold text-sm')
                timeout = config.get('timeout', 300)
                ui.number(
                    value=timeout,
                    min=10,
                    max=3600,
                    step=30,
                    format='%.0f',
                    on_change=lambda e: update_config('timeout', int(e.value) if e.value else 300)
                ).classes('w-32').props('outlined dense')
                ui.label('Tiempo máximo de ejecución del script').classes('text-xs text-gray-500')

                ui.separator().classes('my-2')

                # Reintentos en caso de error
                ui.label('Reintentos en caso de error').classes('font-bold text-sm')
                retries = config.get('retries', 0)
                ui.number(
                    value=retries,
                    min=0,
                    max=3,
                    step=1,
                    format='%.0f',
                    on_change=lambda e: update_config('retries', int(e.value) if e.value else 0)
                ).classes('w-32').props('outlined dense')

                ui.separator().classes('my-2')

                # Continuar en error
                continue_on_error = config.get('continue_on_error', False)
                ui.checkbox(
                    'Continuar el flujo si el script falla',
                    value=continue_on_error,
                    on_change=lambda e: update_config('continue_on_error', e.value)
                )

                # Guardar logs
                save_logs = config.get('save_logs', True)
                ui.checkbox(
                    'Guardar logs de ejecución',
                    value=save_logs,
                    on_change=lambda e: update_config('save_logs', e.value)
                )

        # === Resumen de configuración ===
        ui.separator().classes('my-2')
        with ui.row().classes('items-center gap-2 bg-blue-50 p-2 rounded'):
            ui.icon('code', color='blue')
            script_name = '(sin script)'
            if script_id and scripts:
                script_data = next((s for s in scripts if s['script_id'] == script_id), None)
                if script_data:
                    script_name = script_data.get('name', script_name)

            input_display = config.get('input_mapping', {}).get('file', 'previous_output')
            output_display = config.get('output_var') or suggested_name
            ui.label(f'{script_name}: {input_display} → {{{{{output_display}}}}}').classes('text-sm text-blue-800')
