"""
Formulario genérico para pasos sin formulario específico.
Prompt 3.5 del plan de refactorización del editor de flujos.

Proporciona:
- Generación dinámica de campos basada en JSON Schema (si hay átomo asociado)
- Fallback con editor JSON oculto (si no hay schema)
"""
from typing import Callable, Optional, Any, Dict, List
from nicegui import ui
from automatia_shared.dtos import TaskSpec


def render_generic_form(
    step: TaskSpec,
    config_schema: Optional[Dict[str, Any]] = None,
    on_change: Optional[Callable] = None
):
    """
    Renderiza un formulario genérico para un paso.

    Args:
        step: El TaskSpec del paso a configurar
        config_schema: JSON Schema opcional para generar campos dinámicamente
        on_change: Callback opcional que se llama cuando cambia cualquier campo
    """
    config = step.config or {}

    def update_config(key: str, value):
        """Actualiza un campo de la configuración y notifica el cambio."""
        step.config[key] = value
        if on_change:
            on_change()

    with ui.column().classes('w-full gap-4'):
        if config_schema and config_schema.get('properties'):
            # Generar campos dinámicamente basado en el schema
            _render_schema_fields(config_schema, config, update_config)
        else:
            # Fallback: mostrar mensaje y editor JSON oculto
            _render_fallback_editor(step, config, on_change)


def _render_schema_fields(
    schema: Dict[str, Any],
    config: Dict[str, Any],
    update_config: Callable
):
    """
    Genera campos de formulario dinámicamente basados en un JSON Schema.

    Args:
        schema: El JSON Schema con las propiedades
        config: Configuración actual del paso
        update_config: Función para actualizar la configuración
    """
    properties = schema.get('properties', {})
    required_fields = schema.get('required', [])

    # Título del schema si existe
    schema_title = schema.get('title')
    if schema_title:
        ui.label(schema_title).classes('font-bold text-lg')

    # Descripción del schema si existe
    schema_desc = schema.get('description')
    if schema_desc:
        ui.label(schema_desc).classes('text-sm text-gray-600 mb-2')

    ui.separator().classes('my-2')

    for field_name, field_schema in properties.items():
        is_required = field_name in required_fields
        _render_field(field_name, field_schema, config, update_config, is_required)


def _render_field(
    field_name: str,
    field_schema: Dict[str, Any],
    config: Dict[str, Any],
    update_config: Callable,
    is_required: bool = False
):
    """
    Renderiza un campo individual basado en su schema.

    Args:
        field_name: Nombre del campo
        field_schema: Schema del campo
        config: Configuración actual
        update_config: Función para actualizar
        is_required: Si el campo es obligatorio
    """
    field_type = field_schema.get('type', 'string')
    title = field_schema.get('title', field_name.replace('_', ' ').title())
    description = field_schema.get('description', '')
    default = field_schema.get('default')
    enum_values = field_schema.get('enum')

    current_value = config.get(field_name, default)

    with ui.column().classes('w-full gap-1'):
        # Label con indicador de obligatorio
        with ui.row().classes('items-center gap-1'):
            ui.label(title).classes('font-bold text-sm')
            if is_required:
                ui.label('*').classes('text-red-500 font-bold')

        # Campo según el tipo
        if enum_values:
            # Enum -> Select with binding
            options = {v: str(v) for v in enum_values}
            select = ui.select(
                options=options
            ).bind_value(config, field_name).classes('w-full').props('outlined dense')

            if description:
                select.tooltip(description)

        elif field_type == 'string':
            # String -> Input with binding
            inp = ui.input(
                placeholder=description or f'Ingrese {title.lower()}'
            ).bind_value(config, field_name).classes('w-full').props('outlined dense')

            if description:
                inp.tooltip(description)

        elif field_type == 'number' or field_type == 'integer':
            # Number -> Number input with binding
            min_val = field_schema.get('minimum')
            max_val = field_schema.get('maximum')

            num = ui.number(
                min=min_val,
                max=max_val
            ).bind_value(config, field_name).classes('w-48').props('outlined dense')

            if description:
                num.tooltip(description)

        elif field_type == 'boolean':
            # Boolean -> Checkbox with binding
            cb = ui.checkbox(
                title
            ).bind_value(config, field_name)

            if description:
                cb.tooltip(description)

        elif field_type == 'array':
            # Array -> Select múltiple o textarea
            items_schema = field_schema.get('items', {})
            items_enum = items_schema.get('enum')

            if items_enum:
                # Array de enum -> Select múltiple
                options = {v: str(v) for v in items_enum}
                sel = ui.select(
                    options=options,
                    value=current_value or [],
                    multiple=True,
                    on_change=lambda e, fn=field_name: update_config(fn, list(e.value) if e.value else [])
                ).classes('w-full').props('outlined dense use-chips')

                if description:
                    sel.tooltip(description)
            else:
                # Array genérico -> Textarea con valores separados por coma
                array_value = ', '.join(str(v) for v in (current_value or []))
                ta = ui.input(
                    value=array_value,
                    placeholder='Valores separados por coma',
                    on_change=lambda e, fn=field_name: update_config(
                        fn,
                        [v.strip() for v in e.value.split(',') if v.strip()]
                    )
                ).classes('w-full').props('outlined dense')

                if description:
                    ta.tooltip(description)

        elif field_type == 'object':
            # Object -> JSON Editor en expansión
            import json
            with ui.expansion(f'{title} (JSON)', icon='data_object').classes('w-full'):
                obj_value = json.dumps(current_value or {}, indent=2)

                def update_object(e, fn=field_name):
                    try:
                        parsed = json.loads(e.value)
                        update_config(fn, parsed)
                    except json.JSONDecodeError:
                        pass  # Ignorar JSON inválido

                ui.textarea(
                    value=obj_value,
                    on_change=update_object
                ).classes('w-full h-32 font-mono text-xs').props('outlined')

        else:
            # Tipo desconocido -> Input genérico
            ui.input(
                value=str(current_value) if current_value else '',
                on_change=lambda e, fn=field_name: update_config(fn, e.value)
            ).classes('w-full').props('outlined dense')

        # Descripción como texto de ayuda (si no está como tooltip)
        if description and field_type not in ('boolean',):
            ui.label(description).classes('text-xs text-gray-500 -mt-1')


def _render_fallback_editor(
    step: TaskSpec,
    config: Dict[str, Any],
    on_change: Optional[Callable]
):
    """
    Renderiza el editor de fallback cuando no hay schema disponible.

    Args:
        step: El TaskSpec del paso
        config: Configuración actual
        on_change: Callback de cambio
    """
    import json

    with ui.card().classes('w-full p-4 bg-gray-50 border border-gray-200'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('settings', color='gray').classes('text-2xl')
            with ui.column().classes('gap-1'):
                ui.label('Configuración avanzada').classes('font-bold text-gray-700')
                ui.label('Este paso requiere configuración manual.').classes('text-sm text-gray-600')

    # Editor JSON oculto por defecto
    editor_visible = {'value': False}
    editor_container = ui.column().classes('w-full mt-4')

    def toggle_editor():
        editor_visible['value'] = not editor_visible['value']
        render_editor.refresh()

    @ui.refreshable
    def render_editor():
        editor_container.clear()
        with editor_container:
            if editor_visible['value']:
                ui.label('Configuración JSON').classes('font-bold text-sm mb-2')

                def update_json(e):
                    try:
                        parsed = json.loads(e.value)
                        step.config = parsed
                        if on_change:
                            on_change()
                    except json.JSONDecodeError:
                        pass  # Ignorar JSON inválido mientras escribe

                # Usar json_editor si está disponible, o textarea como fallback
                try:
                    initial_json = {'content': {'json': config}}
                    editor = ui.json_editor(initial_json).classes('w-full h-64')

                    def on_editor_change(e):
                        try:
                            if e.args and 'json' in e.args.get('content', {}):
                                step.config = e.args['content']['json']
                                if on_change:
                                    on_change()
                        except Exception:
                            pass

                    editor.on('change', on_editor_change)

                except Exception:
                    # Fallback a textarea si json_editor no está disponible
                    ui.textarea(
                        value=json.dumps(config, indent=2, ensure_ascii=False),
                        on_change=update_json
                    ).classes('w-full h-48 font-mono text-xs').props('outlined')

                ui.button(
                    'Cerrar editor',
                    icon='close',
                    on_click=toggle_editor
                ).props('flat dense color=grey').classes('mt-2')

            else:
                # Mostrar resumen de la configuración
                if config:
                    with ui.row().classes('items-center gap-2 text-sm text-gray-600'):
                        ui.icon('check_circle', color='green').classes('text-sm')
                        keys = list(config.keys())[:3]
                        summary = ', '.join(keys)
                        if len(config) > 3:
                            summary += f' (+{len(config) - 3} más)'
                        ui.label(f'Configurado: {summary}')

                ui.button(
                    'Abrir editor JSON',
                    icon='code',
                    on_click=toggle_editor
                ).props('outline dense color=primary')

    render_editor()

    # Advertencia sobre edición manual
    with ui.row().classes('items-center gap-2 mt-3 p-2 bg-orange-50 rounded border border-orange-200'):
        ui.icon('warning', color='orange').classes('text-sm')
        ui.label('La edición manual requiere conocimiento del formato esperado.').classes('text-xs text-orange-700')
