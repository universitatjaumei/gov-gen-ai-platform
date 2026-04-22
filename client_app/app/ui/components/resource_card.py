
from nicegui import ui
from client_app.app.database.models import ScriptLibrary

def get_module_icon(module: str) -> str:
    """Returns icon name for a given source module"""
    icons = {
        'custom': 'code',
        'extraction': 'description',
        'graphics': 'bar_chart',
        'etl': 'transform',
        'rpa': 'travel_explore',
        'workflow': 'account_tree'
    }
    return icons.get(module, 'extension')

def get_status_color(status: str) -> str:
    """Returns color for status badge"""
    colors = {
        'draft': 'grey',
        'validated': 'orange',
        'published': 'green'
    }
    return colors.get(status, 'grey')

def resource_card(resource: ScriptLibrary, on_view_details=None, on_execute=None, on_refine=None, on_support=None):
    """
    Renders a compact card for a ScriptLibrary resource.
    
    Args:
        resource: ScriptLibrary instance
        on_view_details: Callback when clicking the card body/icon
        on_execute: Callback for 'Play' (Published/Validated)
        on_refine: Callback for 'Refine' (Draft)
        on_support: Callback for 'Support' (Draft)
    """
    with ui.card().classes('w-full p-3 hover:shadow-md transition-shadow cursor-pointer').on('click', lambda: on_view_details(resource) if on_view_details else None):
        with ui.row().classes('w-full items-center justify-between no-wrap gap-3'):
            # Icon
            ui.icon(get_module_icon(resource.source_module)).classes('text-2xl text-primary')
            
            # Title & Metadata (Compact)
            with ui.column().classes('gap-0 flex-grow'):
                ui.label(resource.name).classes('text-base font-bold text-gray-800 leading-tight')
                ui.label(resource.source_module.upper()).classes('text-xs text-gray-400 font-mono')
            
            # Status Badge (Small)
            color = get_status_color(resource.status)
            ui.icon('circle', color=color).classes('text-xs').tooltip(resource.status.upper())

        # Footer Actions (Stop Propagation to avoid opening details)
        with ui.row().classes('w-full justify-end gap-2 mt-3').on('click', lambda: None, js_handler='event.stopPropagation()'):
            if resource.status != 'draft':
                 if on_execute:
                    ui.button(icon='play_arrow', on_click=lambda: on_execute(resource)).props('unelevated round size=sm color=green').tooltip('Ejecutar')
            else:
                if on_refine:
                    ui.button(icon='auto_fix_high', on_click=lambda: on_refine(resource)).props('flat round size=sm color=blue').tooltip('Refinar')
                if on_support:
                    ui.button(icon='support_agent', on_click=lambda: on_support(resource)).props('flat round size=sm color=orange').tooltip('Solicitar Soporte')
