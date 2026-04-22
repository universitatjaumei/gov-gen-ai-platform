"""
Formulario de configuración para pasos EXTRACTION.
Prompt 3.3 del plan de refactorización del editor de flujos.

Proporciona un formulario visual para configurar extracción de datos con IA.

Actualizado en Prompt 5.3 para usar SideDrawer con wizard de creación de configuraciones.
"""
from typing import Callable, Optional, List
from nicegui import ui
from automatia_shared.dtos import TaskSpec, FlowSpec

from client_app.app.ui.components.side_drawer import SideDrawer
from client_app.app.ui.components.extraction_wizard import render_extraction_wizard


async def render_extraction_form(
    step: TaskSpec,
    flow: FlowSpec = None,
    on_change: Optional[Callable] = None
):
    """
    Renderiza el formulario de configuración para un paso EXTRACTION.

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
        # === Configuración de Extracción (obligatorio) ===
        config_id = config.get('config_id')
        is_config_empty = not config_id

        with ui.row().classes('items-center gap-1'):
            ui.label('Configuración de Extracción').classes('font-bold')
            if is_config_empty:
                ui.label('*').classes('text-red-500 font-bold')

        # Cargar configuraciones disponibles
        extraction_configs = await resource_listing_service.list_extraction_configs()

        # Variable para almacenar la configuración seleccionada (para mostrar preview)
        selected_config_data = None

        # Funciones para el drawer de creación de configuraciones
        drawer_ref = {'drawer': None}

        async def open_extraction_wizard():
            """Abre el drawer con el wizard de creación de configuraciones de extracción."""
            drawer = SideDrawer('Crear Configuración de Extracción', width='w-1/2')

            def on_config_created(config_id: str):
                """Callback cuando se crea una nueva configuración."""
                drawer.close(config_id)
                # Actualizar la configuración con el nuevo config_id
                update_config('config_id', config_id)
                ui.notify('Configuración creada y seleccionada', type='positive')
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
                    await render_extraction_wizard(
                        on_save=on_config_created,
                        on_cancel=on_cancel
                    )

        if not extraction_configs:
            with ui.card().classes('w-full p-4 bg-orange-50 border border-orange-200'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('warning', color='orange').classes('text-2xl')
                    with ui.column().classes('gap-1'):
                        ui.label('No hay configuraciones de extracción').classes('font-bold text-orange-800')
                        ui.label('Debes crear una configuración antes de usar este paso.').classes('text-sm text-orange-700')

                ui.separator().classes('my-2')

                ui.button(
                    'Crear configuración de extracción',
                    icon='add',
                    on_click=open_extraction_wizard
                ).props('color=orange')
        else:
            # Crear opciones para el select
            config_opts = {c['id']: c['name'] for c in extraction_configs}

            # Buscar la configuración seleccionada actualmente
            if config_id:
                selected_config_data = next(
                    (c for c in extraction_configs if c['id'] == config_id),
                    None
                )

            @ui.refreshable
            def config_selector():
                nonlocal selected_config_data

                def on_config_change(e):
                    nonlocal selected_config_data
                    update_config('config_id', e.value)
                    selected_config_data = next(
                        (c for c in extraction_configs if c['id'] == e.value),
                        None
                    )
                    config_preview.refresh()

                with ui.row().classes('w-full items-end gap-2'):
                    ui.select(
                        options=config_opts,
                        value=config_id,
                        label='Seleccionar configuración',
                        on_change=on_config_change
                    ).classes('flex-1').props('outlined dense')

                    ui.button(
                        icon='add',
                        on_click=open_extraction_wizard
                    ).props('flat color=primary').tooltip('Crear nueva configuración')

            config_selector()

            if is_config_empty:
                ui.label('Debe seleccionar una configuración de extracción').classes('text-red-500 text-xs -mt-2')

            # Preview de la configuración seleccionada
            @ui.refreshable
            def config_preview():
                if selected_config_data:
                    with ui.card().classes('w-full p-3 bg-blue-50 border border-blue-200 mt-2'):
                        ui.label('Vista previa de la configuración').classes('font-bold text-blue-800 text-sm')

                        # Mostrar descripción si existe
                        if selected_config_data.get('description'):
                            ui.label(selected_config_data['description']).classes('text-sm text-gray-600 mt-1')

                        # Mostrar campos que extrae si están disponibles
                        fields = selected_config_data.get('fields') or selected_config_data.get('extraction_fields')
                        if fields:
                            ui.separator().classes('my-2')
                            ui.label('Campos a extraer:').classes('text-xs font-bold text-blue-700')
                            with ui.row().classes('flex-wrap gap-1 mt-1'):
                                if isinstance(fields, list):
                                    for field in fields[:10]:  # Limitar a 10 campos
                                        field_name = field.get('name', field) if isinstance(field, dict) else str(field)
                                        ui.chip(field_name, icon='check_circle').props('dense color=primary size=sm')
                                    if len(fields) > 10:
                                        ui.chip(f'+{len(fields) - 10} más', icon='more_horiz').props('dense color=grey size=sm')
                                elif isinstance(fields, dict):
                                    for field_name in list(fields.keys())[:10]:
                                        ui.chip(field_name, icon='check_circle').props('dense color=primary size=sm')

                        # Mostrar tipo de documento si está disponible
                        doc_type = selected_config_data.get('document_type') or selected_config_data.get('type')
                        if doc_type:
                            ui.label(f'Tipo de documento: {doc_type}').classes('text-xs text-gray-500 mt-2')

            config_preview()

        ui.separator().classes('my-2')

        # === Archivo de entrada ===
        ui.label('Archivo de entrada').classes('font-bold text-lg')

        input_source = config.get('input_source', 'trigger')

        with ui.column().classes('w-full gap-2'):
            ui.label('Origen del archivo a procesar').classes('text-sm text-gray-600')

            # Opciones básicas de origen
            input_mode_options = {
                'trigger': 'Archivo del trigger',
                'variable': 'Variable de paso anterior',
                'manual': 'Ruta manual',
            }

            # Determinar modo actual
            current_mode = 'trigger'
            if input_source.startswith('var:'):
                current_mode = 'variable'
            elif input_source == 'manual':
                current_mode = 'manual'

            ui.select(
                options=input_mode_options,
                value=current_mode,
                label='Tipo de origen',
                on_change=lambda e: update_config('input_source', e.value if e.value != 'variable' else 'var:')
            ).classes('w-full').props('outlined dense')

            # Si es variable, mostrar selector visual
            if current_mode == 'variable' or input_source.startswith('var:'):
                from client_app.app.ui.components.variable_selector import render_variable_selector

                current_var = input_source.replace('var:', '') if input_source.startswith('var:') else ''

                ui.label('Seleccionar variable de archivo:').classes('text-xs text-gray-500 mt-2')

                def on_var_select(ref):
                    # ref viene como {{variable}}, lo guardamos como var:variable
                    clean = ref.strip('{}').strip()
                    update_config('input_source', f'var:{clean}')

                render_variable_selector(
                    flow=flow,
                    current_step_index=flow.steps.index(step) if step in flow.steps else 0,
                    on_select=on_var_select,
                    selected_value=f'{{{{{current_var}}}}}' if current_var else None,
                    filter_types=['file', 'file[]'],
                    compact=True
                )

            # Si es manual, mostrar input para la ruta
            elif input_source == 'manual':
                manual_path = config.get('input_path', '')
                ui.input(
                    value=manual_path,
                    placeholder='/ruta/al/archivo.pdf',
                    on_change=lambda e: update_config('input_path', e.value)
                ).classes('w-full').props('outlined dense label="Ruta del archivo"')

        ui.separator().classes('my-2')

        # === Variable de salida ===
        ui.label('Resultado').classes('font-bold text-lg')

        with ui.column().classes('w-full gap-2'):
            ui.label('Nombre de la variable donde guardar el resultado').classes('text-sm text-gray-600')

            # Sugerir nombre basado en el índice del paso
            suggested_name = 'datos_extraidos'
            if flow and step in flow.steps:
                step_index = flow.steps.index(step)
                suggested_name = f'extraccion_paso_{step_index + 1}'

            output_var = config.get('output_var', '')
            ui.input(
                value=output_var,
                placeholder=suggested_name,
                on_change=lambda e: update_config('output_var', e.value)
            ).classes('w-full').props('outlined dense label="Nombre de variable"')

            ui.label(
                f'Los datos extraídos estarán disponibles como {{{{{output_var or suggested_name}}}}}'
            ).classes('text-xs text-blue-600')

        ui.separator().classes('my-2')

        # === Opciones avanzadas ===
        with ui.expansion('Opciones avanzadas', icon='settings').classes('w-full'):
            with ui.column().classes('w-full gap-3 p-2'):
                # Procesar múltiples páginas
                process_all_pages = config.get('process_all_pages', True)
                ui.checkbox(
                    'Procesar todas las páginas del documento',
                    value=process_all_pages,
                    on_change=lambda e: update_config('process_all_pages', e.value)
                )

                # Páginas específicas
                if not process_all_pages:
                    pages = config.get('pages', '')
                    ui.input(
                        value=pages,
                        placeholder='1,2,5-10',
                        on_change=lambda e: update_config('pages', e.value)
                    ).classes('w-full').props('outlined dense label="Páginas a procesar"')
                    ui.label('Ejemplo: 1,2,5-10 para páginas específicas').classes('text-xs text-gray-500')

                ui.separator().classes('my-2')

                # Idioma preferido
                ui.label('Idioma del documento').classes('font-bold text-sm')
                language = config.get('language', 'auto')
                ui.select(
                    options={
                        'auto': 'Detectar automáticamente',
                        'es': 'Español',
                        'en': 'Inglés',
                        'fr': 'Francés',
                        'de': 'Alemán',
                        'pt': 'Portugués',
                    },
                    value=language,
                    on_change=lambda e: update_config('language', e.value)
                ).classes('w-48').props('outlined dense')

                ui.separator().classes('my-2')

                # Guardar archivo procesado
                save_processed = config.get('save_processed_file', False)
                ui.checkbox(
                    'Guardar copia del archivo procesado',
                    value=save_processed,
                    on_change=lambda e: update_config('save_processed_file', e.value)
                )

                # Timeout de procesamiento
                ui.label('Timeout de procesamiento (segundos)').classes('font-bold text-sm mt-2')
                timeout = config.get('timeout', 120)
                ui.number(
                    value=timeout,
                    min=30,
                    max=600,
                    step=30,
                    format='%.0f',
                    on_change=lambda e: update_config('timeout', int(e.value) if e.value else 120)
                ).classes('w-32').props('outlined dense')

        # === Resumen de configuración ===
        ui.separator().classes('my-2')
        with ui.row().classes('items-center gap-2 bg-blue-50 p-2 rounded'):
            ui.icon('description', color='blue')
            config_name = '(sin configuración)'
            if config_id and extraction_configs:
                config_data = next((c for c in extraction_configs if c['id'] == config_id), None)
                if config_data:
                    config_name = config_data.get('name', config_name)

            output_display = config.get('output_var') or suggested_name
            ui.label(f'Configuración: {config_name} → {{{{{output_display}}}}}').classes('text-sm text-blue-800')
