"""
Selector visual de variables para el editor de flujos.
Prompt 4.2 del plan de refactorización.

Proporciona chips clicables agrupados por paso de origen
para seleccionar variables de pasos anteriores.
"""
from typing import Any, Callable, Optional, Dict
from nicegui import ui
from automatia_shared.dtos import FlowSpec

from client_app.app.services.data_flow_analyzer import (
    data_flow_analyzer,
    VariableInfo,
)


# Iconos por tipo de variable
TYPE_ICONS: Dict[str, str] = {
    'file': 'folder',
    'file[]': 'folder_copy',
    'string': 'text_fields',
    'string[]': 'list',
    'json': 'data_object',
    'json[]': 'data_array',
    'number': 'tag',
    'boolean': 'toggle_on',
    'any': 'help_outline',
}

# Colores por tipo de variable
TYPE_COLORS: Dict[str, str] = {
    'file': 'amber',
    'file[]': 'amber',
    'string': 'blue',
    'string[]': 'blue',
    'json': 'purple',
    'json[]': 'purple',
    'number': 'green',
    'boolean': 'cyan',
    'any': 'grey',
}


def get_icon_for_type(var_type: str) -> str:
    """Obtiene el icono apropiado para un tipo de variable."""
    return TYPE_ICONS.get(var_type, 'help_outline')


def get_color_for_type(var_type: str) -> str:
    """Obtiene el color apropiado para un tipo de variable."""
    return TYPE_COLORS.get(var_type, 'grey')


def format_variable_reference(var: VariableInfo) -> str:
    """
    Formatea la referencia a una variable para usar en templates.

    Args:
        var: La VariableInfo

    Returns:
        String con formato {{variable}} o {{paso_N.variable}}
    """
    if var.source_step is None:
        # Variable del trigger/contexto
        return f'{{{{{var.name}}}}}'
    else:
        # Variable de un paso anterior
        return f'{{{{{var.name}}}}}'


def render_variable_selector(
    flow: FlowSpec,
    current_step_index: int,
    on_select: Callable[[str], None],
    selected_value: Optional[str] = None,
    filter_types: Optional[list] = None,
    show_descriptions: bool = True,
    compact: bool = False
):
    """
    Renderiza un selector visual de variables con chips clicables.

    Args:
        flow: El FlowSpec completo
        current_step_index: Índice del paso actual (para determinar variables disponibles)
        on_select: Callback que recibe la referencia a la variable seleccionada
        selected_value: Valor actualmente seleccionado (para resaltar)
        filter_types: Lista opcional de tipos a mostrar (ej: ['file', 'file[]'])
        show_descriptions: Mostrar descripciones en tooltips
        compact: Modo compacto sin agrupación
    """
    # Obtener variables disponibles
    variables = data_flow_analyzer.get_available_variables(flow, current_step_index)

    # Filtrar por tipo si se especifica
    if filter_types:
        variables = [v for v in variables if v.var_type in filter_types]

    if not variables:
        with ui.row().classes('items-center gap-2 p-2 bg-gray-50 rounded'):
            ui.icon('info', color='grey').classes('text-sm')
            ui.label('No hay variables disponibles').classes('text-sm text-gray-500 italic')
        return

    # Agrupar variables por origen
    groups: Dict[str, list] = {}

    for var in variables:
        if var.source_step is None:
            group_key = 'trigger'
            group_name = 'Trigger'
        elif var.source_step < 0:
            group_key = 'global'
            group_name = 'Variables Globales'
        else:
            group_key = f'step_{var.source_step}'
            group_name = f'Paso {var.source_step + 1}: {var.source_step_name or "Sin nombre"}'

        if group_key not in groups:
            groups[group_key] = {'name': group_name, 'vars': []}
        groups[group_key]['vars'].append(var)

    # Renderizar
    if compact:
        _render_compact(variables, on_select, selected_value, show_descriptions)
    else:
        _render_grouped(groups, on_select, selected_value, show_descriptions)


def _render_grouped(
    groups: Dict[str, dict],
    on_select: Callable[[str], None],
    selected_value: Optional[str],
    show_descriptions: bool
):
    """Renderiza variables agrupadas por origen."""
    with ui.column().classes('w-full gap-2'):
        for group_key, group_data in groups.items():
            group_name = group_data['name']
            group_vars = group_data['vars']

            # Header del grupo
            with ui.row().classes('items-center gap-2'):
                if group_key == 'trigger':
                    ui.icon('bolt', color='orange').classes('text-sm')
                elif group_key == 'global':
                    ui.icon('public', color='green').classes('text-sm')
                else:
                    ui.icon('arrow_forward', color='blue').classes('text-sm')
                ui.label(group_name).classes('text-xs font-bold text-gray-600')

            # Chips de variables
            with ui.row().classes('flex-wrap gap-1 ml-6'):
                for var in group_vars:
                    _render_variable_chip(var, on_select, selected_value, show_descriptions)


def _render_compact(
    variables: list,
    on_select: Callable[[str], None],
    selected_value: Optional[str],
    show_descriptions: bool
):
    """Renderiza variables en modo compacto sin agrupación."""
    with ui.row().classes('flex-wrap gap-1'):
        for var in variables:
            _render_variable_chip(var, on_select, selected_value, show_descriptions)


def _render_variable_chip(
    var: VariableInfo,
    on_select: Callable[[str], None],
    selected_value: Optional[str],
    show_descriptions: bool
):
    """Renderiza un chip individual para una variable."""
    var_ref = format_variable_reference(var)
    is_selected = selected_value == var_ref or selected_value == var.name

    icon = get_icon_for_type(var.var_type)
    color = get_color_for_type(var.var_type)

    # Determinar estilo según selección
    if is_selected:
        chip_props = f'color={color} icon={icon}'
        chip_classes = 'cursor-pointer'
    else:
        chip_props = f'outline color={color} icon={icon}'
        chip_classes = 'cursor-pointer hover:bg-gray-100'

    def handle_click(v=var):
        ref = format_variable_reference(v)
        on_select(ref)

    chip = ui.chip(
        var.name,
        on_click=handle_click
    ).props(f'{chip_props} dense clickable size=sm').classes(chip_classes)

    # Tooltip con descripción y tipo
    if show_descriptions:
        tooltip_text = f'{var.var_type}'
        if var.description:
            tooltip_text = f'{var.description}\nTipo: {var.var_type}'
        chip.tooltip(tooltip_text)


def render_variable_input(
    flow: FlowSpec,
    current_step_index: int,
    current_value: str,
    on_change: Callable[[str], None],
    label: str = 'Variable',
    placeholder: str = 'Seleccionar o escribir variable...',
    filter_types: Optional[list] = None,
    allow_manual: bool = True
):
    """
    Renderiza un input con selector de variables integrado.

    Args:
        flow: El FlowSpec completo
        current_step_index: Índice del paso actual
        current_value: Valor actual del campo
        on_change: Callback cuando cambia el valor
        label: Etiqueta del campo
        placeholder: Placeholder del input
        filter_types: Tipos de variables a mostrar
        allow_manual: Permitir entrada manual además de selección
    """
    with ui.column().classes('w-full gap-2'):
        ui.label(label).classes('font-bold text-sm')

        if allow_manual:
            # Input manual con selector expandible
            with ui.row().classes('w-full items-start gap-2'):
                inp = ui.input(
                    value=current_value,
                    placeholder=placeholder,
                    on_change=lambda e: on_change(e.value)
                ).classes('flex-1').props('outlined dense')

            # Selector de variables en expansión
            with ui.expansion('Seleccionar variable', icon='data_object').classes('w-full'):
                def handle_select(ref):
                    on_change(ref)
                    inp.value = ref

                render_variable_selector(
                    flow=flow,
                    current_step_index=current_step_index,
                    on_select=handle_select,
                    selected_value=current_value,
                    filter_types=filter_types,
                    compact=True
                )
        else:
            # Solo selector de variables (sin input manual)
            render_variable_selector(
                flow=flow,
                current_step_index=current_step_index,
                on_select=on_change,
                selected_value=current_value,
                filter_types=filter_types
            )


def render_file_variable_selector(
    flow: FlowSpec,
    current_step_index: int,
    current_value: str,
    on_change: Callable[[str], None],
    label: str = 'Archivo de entrada'
):
    """
    Renderiza un selector específico para variables de tipo archivo.

    Args:
        flow: El FlowSpec completo
        current_step_index: Índice del paso actual
        current_value: Valor actual
        on_change: Callback cuando cambia
        label: Etiqueta del campo
    """
    render_variable_input(
        flow=flow,
        current_step_index=current_step_index,
        current_value=current_value,
        on_change=on_change,
        label=label,
        placeholder='Seleccionar archivo...',
        filter_types=['file', 'file[]'],
        allow_manual=True
    )


def render_test_data_section(
    test_outputs: Dict[int, dict],
    test_timestamps: Dict[int, Any],
    flow: FlowSpec,
    current_step_index: int,
    on_use_test_data: Callable[[Any], None]
):
    """
    Renderiza una sección con los datos de prueba guardados.
    Prompt 4.3 del plan de refactorización.

    Args:
        test_outputs: Diccionario step_index -> {output, step_name, step_type}
        test_timestamps: Diccionario step_index -> datetime
        flow: El FlowSpec completo
        current_step_index: Índice del paso actual
        on_use_test_data: Callback cuando se selecciona usar datos de prueba
    """
    # Filtrar solo datos de pasos anteriores
    available_data = {
        idx: data for idx, data in test_outputs.items()
        if idx < current_step_index
    }

    if not available_data:
        return

    with ui.card().classes('w-full p-3 bg-purple-50 border border-purple-200'):
        with ui.row().classes('items-center gap-2 mb-2'):
            ui.icon('science', color='purple').classes('text-lg')
            ui.label('Datos de Prueba Guardados').classes('font-bold text-purple-800')

        with ui.column().classes('w-full gap-2'):
            for idx, data in available_data.items():
                step_name = data.get('step_name', f'Paso {idx + 1}')
                step_type = data.get('step_type', '')
                timestamp = test_timestamps.get(idx)

                # Calcular tiempo relativo
                time_str = ''
                if timestamp:
                    from datetime import datetime
                    diff = datetime.now() - timestamp
                    minutes = int(diff.total_seconds() / 60)
                    if minutes < 1:
                        time_str = 'ahora'
                    elif minutes < 60:
                        time_str = f'hace {minutes} min'
                    else:
                        time_str = timestamp.strftime('%H:%M')

                with ui.row().classes('items-center gap-2 w-full p-2 bg-white rounded border'):
                    ui.icon('science', color='purple').classes('text-sm')
                    with ui.column().classes('flex-1 gap-0'):
                        ui.label(f'Paso {idx + 1}: {step_name}').classes('text-sm font-medium')
                        if time_str:
                            ui.label(time_str).classes('text-xs text-gray-400')

                    def use_data(d=data):
                        on_use_test_data(d.get('output'))

                    ui.button(
                        'Usar',
                        icon='play_arrow',
                        on_click=use_data
                    ).props('flat dense size=sm color=purple')

                    # Preview button
                    def show_preview(d=data):
                        import json
                        output = d.get('output')
                        with ui.dialog() as preview_dialog, ui.card().classes('w-[400px]'):
                            ui.label('Preview de datos').classes('font-bold mb-2')
                            if isinstance(output, (dict, list)):
                                ui.json_editor({'content': {'json': output}}).classes('w-full h-60')
                            else:
                                ui.label(str(output)).classes('font-mono text-sm')
                            ui.button('Cerrar', on_click=preview_dialog.close).classes('mt-2')
                            preview_dialog.open()

                    ui.button(
                        icon='visibility',
                        on_click=show_preview
                    ).props('flat dense size=sm color=grey')


class VariableSelector:
    """Selector de variables adaptador para formularios antiguos o nuevos."""
    def __init__(self, available_variables: Dict[str, Any], current_value: str, on_select: Callable[[str], None]):
        self.available_variables = available_variables
        self.current_value = current_value
        self.on_select_callback = on_select

    def render(self):
        with ui.row().classes('items-center gap-2 w-full'):
            input_el = ui.input(
                value=self.current_value,
                on_change=lambda e: self.on_select_callback(e.value),
                placeholder='Valor o {{variable}}'
            ).classes('flex-1').props('dense outlined')

            with ui.button(icon='data_object', color='grey').props('flat round dense'):
                with ui.menu().classes('max-h-60 overflow-y-auto'):
                    with ui.column().classes('p-2 gap-1'):
                        ui.label('Variables Disponibles').classes('text-xs font-bold text-gray-500 mb-1')
                        
                        if not self.available_variables:
                            ui.label('No hay variables disponibles').classes('text-xs italic text-gray-400')
                        else:
                            for name, info in self.available_variables.items():
                                var_type = "any"
                                description = ""
                                if isinstance(info, dict):
                                    var_type = info.get("type", "any")
                                    description = info.get("description", "")
                                elif hasattr(info, "var_type"):
                                    var_type = info.var_type
                                    description = getattr(info, "description", "")
                                
                                def select_var(e, n=name):
                                    val = f"{{{{{n}}}}}"
                                    input_el.set_value(val)
                                    self.on_select_callback(val)
                                    
                                ui.chip(
                                    name,
                                    icon=get_icon_for_type(var_type),
                                    color=get_color_for_type(var_type),
                                    on_click=select_var
                                ).props('dense clickable size=sm').tooltip(f"{var_type}: {description}")
