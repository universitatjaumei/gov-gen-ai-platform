from nicegui import ui
from client_app.app.core.state import state

def render_privacy_indicator():
    """Muestra indicador de privacidad compacto (Chip + Tooltip)."""
    t = state.i18n.t
    with ui.chip(icon='security', color='green-100').classes('text-green-800 font-bold border border-green-200'):
        ui.label(t('privacy_active')).classes('text-xs ml-1')
        ui.tooltip(t('privacy_tooltip')).classes('bg-slate-800 text-white shadow-lg')
