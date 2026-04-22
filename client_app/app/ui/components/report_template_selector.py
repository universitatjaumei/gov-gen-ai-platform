"""
Selector de plantillas de reporte para el editor de flujos.

Muestra las plantillas disponibles en cards con preview,
permitiendo seleccionar una para el paso REPORT_GENERATE.
"""
from typing import Callable, Optional, List
from nicegui import ui
import json


async def get_available_templates() -> List[dict]:
    """
    Obtiene las plantillas de reporte disponibles desde la BD.

    Returns:
        Lista de diccionarios con info de cada plantilla
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select
    from client_app.app.database.db import client_engine
    from client_app.app.database.models import ReportTemplate

    async with AsyncSession(client_engine) as session:
        result = await session.exec(
            select(ReportTemplate).where(ReportTemplate.is_active == True)
        )
        templates = result.all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description or "",
            "format": t.format,
            "template_type": t.template_type,
            "available_sections": json.loads(t.available_sections) if t.available_sections else [],
            "is_system": t.is_system,
        }
        for t in templates
    ]


# Iconos por tipo de plantilla
TEMPLATE_TYPE_ICONS = {
    "builtin": "description",
    "html": "code",
    "reportlab": "picture_as_pdf",
}

# Colores por formato
FORMAT_COLORS = {
    "pdf": "red",
    "odt": "blue",
    "both": "purple",
}


def render_template_selector(
    current_template_id: Optional[int],
    on_select: Callable[[int], None],
    show_preview: bool = True,
):
    """
    Renderiza un selector de plantillas de reporte.

    Args:
        current_template_id: ID de la plantilla actualmente seleccionada
        on_select: Callback cuando se selecciona una plantilla
        show_preview: Mostrar preview de la plantilla seleccionada
    """
    # Estado local
    templates: List[dict] = []
    selected_template: Optional[dict] = None

    async def load_templates():
        nonlocal templates, selected_template
        templates = await get_available_templates()
        if current_template_id:
            selected_template = next(
                (t for t in templates if t["id"] == current_template_id),
                None
            )
        content_container.refresh()

    @ui.refreshable
    def content_container():
        if not templates:
            with ui.row().classes('w-full justify-center p-4'):
                ui.spinner('dots', size='lg')
                ui.label('Cargando plantillas...').classes('text-gray-500')
            return

        with ui.column().classes('w-full gap-4'):
            # Grid de plantillas
            with ui.row().classes('flex-wrap gap-3 w-full'):
                for template in templates:
                    is_selected = template["id"] == current_template_id
                    _render_template_card(
                        template=template,
                        is_selected=is_selected,
                        on_click=lambda t=template: handle_select(t)
                    )

            # Preview de la plantilla seleccionada
            if show_preview and selected_template:
                _render_template_preview(selected_template)

    def handle_select(template: dict):
        nonlocal selected_template
        selected_template = template
        on_select(template["id"])
        content_container.refresh()

    # Renderizar contenedor principal
    with ui.column().classes('w-full'):
        content_container()

    # Cargar plantillas async
    ui.timer(0.1, load_templates, once=True)


def _render_template_card(
    template: dict,
    is_selected: bool,
    on_click: Callable
):
    """Renderiza una card individual para una plantilla."""
    icon = TEMPLATE_TYPE_ICONS.get(template["template_type"], "description")
    format_color = FORMAT_COLORS.get(template["format"], "grey")

    # Clases segun seleccion
    card_classes = 'w-36 cursor-pointer transition-all hover:shadow-md'
    if is_selected:
        card_classes += ' ring-2 ring-blue-500 bg-blue-50'
    else:
        card_classes += ' hover:bg-gray-50'

    with ui.card().classes(card_classes).on('click', on_click):
        with ui.column().classes('items-center gap-2 p-2'):
            # Icono grande
            ui.icon(icon, size='xl').classes(f'text-{format_color}-600')

            # Nombre
            ui.label(template["name"]).classes(
                'text-sm font-medium text-center line-clamp-2'
            )

            # Badges
            with ui.row().classes('gap-1'):
                # Formato
                ui.badge(
                    template["format"].upper(),
                    color=format_color
                ).props('dense')

                # Sistema
                if template["is_system"]:
                    ui.badge('Sistema', color='grey').props('dense outline')


def _render_template_preview(template: dict):
    """Renderiza el preview de una plantilla seleccionada."""
    with ui.card().classes('w-full p-4 bg-gray-50 border border-gray-200'):
        with ui.row().classes('items-start gap-4 w-full'):
            # Icono
            icon = TEMPLATE_TYPE_ICONS.get(template["template_type"], "description")
            format_color = FORMAT_COLORS.get(template["format"], "grey")
            ui.icon(icon, size='lg').classes(f'text-{format_color}-600')

            # Info
            with ui.column().classes('flex-1 gap-2'):
                ui.label(template["name"]).classes('font-bold text-lg')

                if template["description"]:
                    ui.label(template["description"]).classes('text-sm text-gray-600')

                # Secciones disponibles
                sections = template.get("available_sections", [])
                if sections:
                    with ui.row().classes('items-center gap-2 mt-2'):
                        ui.label('Secciones:').classes('text-xs text-gray-500')
                        for section in sections:
                            ui.chip(
                                section,
                                color='blue'
                            ).props('dense outline size=sm')


async def render_template_selector_dialog(
    current_template_id: Optional[int],
    on_select: Callable[[int], None],
    on_cancel: Optional[Callable] = None
):
    """
    Muestra un dialogo modal para seleccionar plantilla.

    Args:
        current_template_id: ID de la plantilla actualmente seleccionada
        on_select: Callback cuando se confirma la seleccion
        on_cancel: Callback cuando se cancela
    """
    selected_id = current_template_id

    def handle_select(template_id: int):
        nonlocal selected_id
        selected_id = template_id

    def confirm():
        if selected_id:
            on_select(selected_id)
        dialog.close()

    def cancel():
        if on_cancel:
            on_cancel()
        dialog.close()

    with ui.dialog() as dialog, ui.card().classes('w-[500px] max-h-[80vh]'):
        # Header
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label('Seleccionar Plantilla').classes('text-xl font-bold')
            ui.button(icon='close', on_click=cancel).props('flat round dense')

        # Contenido scrolleable
        with ui.scroll_area().classes('w-full h-96'):
            render_template_selector(
                current_template_id=selected_id,
                on_select=handle_select,
                show_preview=True
            )

        # Footer
        with ui.row().classes('w-full justify-end gap-2 mt-4 pt-4 border-t'):
            ui.button('Cancelar', on_click=cancel).props('flat')
            ui.button('Seleccionar', on_click=confirm).props('color=primary')

    dialog.open()
