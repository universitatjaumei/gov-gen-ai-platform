from nicegui import ui, app
from client_app.app.ui.layout_state import LayoutState
from client_app.app.core.state import state as app_state
from client_app.app.menu_config import get_menu_structure
from client_app.app.ui.components.atom_gallery import render_atom_gallery
from automatia_shared.enums import StepType

def main_layout(mini_sidebar=False):
    """
    Define el diseño (layout) principal de la aplicación utilizando una arquitectura de 3 capas.
    
    Capas de Z-Index:
    1. Base Integration: Navegación lateral (Left Drawer) y contenido principal.
    2. Focus Overlay (z-50): Capa para asistentes (wizards) que requieren atención completa.
    3. Copilot Sidebar (z-50): Panel lateral derecho (Right Drawer) para asistencia contextual de IA.

    Args:
        mini_sidebar (bool, optional): Si es True, fuerza el sidebar en modo mini inicialmente.
    """
    layout_state = LayoutState()

    # Reset focus mode state by default when a new layout is rendered.
    # Exclude design/automation pages that handle their own focus mode.
    path = ui.context.client.page.path
    design_prefixes = [
        '/connections', '/triggers', '/etl', '/rpa', '/documents',
        '/anonymizer', '/reports/designer', '/custom-scripts',
        '/graphics', '/atoms', '/inputs', '/outputs', '/docs'
    ]
    is_design_route = any(path.startswith(p) for p in design_prefixes)
    if path.startswith('/flows/') and path != '/flows/':
        is_design_route = True

    if not is_design_route:
        # Solo resetear si estamos en una página "estándar" (Dashboard, Listas, etc)
        app_state.toggle_focus_mode(False)

    # Track current path for reload logic (legacy support)
    app.storage.user['referrer_path'] = ui.context.client.page.path

    # Copilot Pulse CSS (Prompt 8)
    ui.add_head_html('''
    <style>
        @keyframes copilot-pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 179, 0, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(255, 179, 0, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 179, 0, 0); }
        }
        .copilot-pulse {
            animation: copilot-pulse 2s infinite;
            border-radius: 50%;
        }
    </style>
    ''')

    # --- HEADER ---
    with ui.header().classes('bg-slate-900 text-white shadow-md items-center h-16 z-40'):
        # Menu Toggle
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
        
        # Branding
        with ui.row().classes('items-center gap-2'):
            ui.label('Gov Gen AI').classes('text-xl font-bold tracking-tight')

        ui.space()

        # Admin / Partner Links (Dev Mode)
        with ui.row().classes('gap-1 mr-2'):
             ui.button('Admin', icon='admin_panel_settings', on_click=lambda: ui.navigate.to('/admin')).props('flat dense color=white').classes('text-xs')
             ui.button('Partner', icon='business', on_click=lambda: ui.navigate.to('/partner/dashboard')).props('flat dense color=white').classes('text-xs')
        
        
        # Copilot Toggle with Badge
        with ui.button(on_click=layout_state.toggle_copilot, icon='support_agent').props('flat color=white').classes('mr-2 relative').tooltip('Abrir/Cerrar Copiloto'):
             with ui.element('div').bind_visibility_from(layout_state, 'suggestion_count').classes('absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold px-1 rounded-full'):
                  ui.label().bind_text_from(layout_state, 'suggestion_count', backward=lambda n: str(n) if n > 0 else '')
        def change_lang(e):
            """Cambia el idioma de la aplicación y recarga la página actual."""
            app_state.i18n.set_locale(e.value)
            ui.notify(f"Idioma cambiado a {e.value.upper()}.", type='info')
            ui.timer(0.5, lambda: ui.navigate.to(app.storage.user.get('referrer_path', '/')), once=True)

        with ui.element('div').classes('mr-4'):
             ui.select(
                options=['es', 'ca'], 
                value=app_state.i18n.locale,
                on_change=change_lang
            ).props('dense borderless options-dense').classes('bg-white text-black w-24 rounded px-2')

    # --- LEFT DRAWER (Navigation) ---
    from client_app.app.services.layout_manager import layout_manager

    # Mini mode se controla vía binding
    left_drawer = ui.left_drawer(value=True).classes('bg-slate-50 flex flex-col z-30')
    if mini_sidebar:
        left_drawer.props('mini')

    # Binding para mini mode - usamos timer para verificar cambios
    def check_mini_mode():
        if layout_manager.menu_mini_mode:
            left_drawer.props('mini')
        elif not mini_sidebar:
            left_drawer.props(remove='mini')

    # Timer que verifica el estado cada 100ms (más eficiente que watchers globales)
    ui.timer(0.1, check_mini_mode)

    with left_drawer:

        t = app_state.i18n.t
        ui.label(t('menu_main')).classes('text-gray-500 text-xs font-bold px-4 py-2 uppercase tracking-wider')
        
        # Menu Items
        with ui.column().classes('w-full gap-0'):
            def nav_button(text, icon, target, small=False):
                """Crea un botón de navegación estandarizado para el menú lateral."""
                cls = 'w-full text-slate-700 hover:bg-slate-200 rounded-none ' + ('h-9 text-xs' if small else 'h-12')
                ui.button(text, icon=icon, on_click=lambda: ui.navigate.to(target)).props('flat align=left no-caps').classes(cls)

            def render_menu_items(structure):
                """
                Renderiza el árbol de navegación basado en la configuración del menú.
                Implementa soporte para elementos simples y grupos de expansión.

                Args:
                    structure (dict): Diccionario con la jerarquía del menú.
                """
                for key, item in structure.items():
                    if item.get('type') == 'expansion':
                        with ui.expansion(item['label'], icon=item['icon']).props('dense header-class="text-primary" group="main_nav"').classes('w-full'):
                            with ui.column().classes('w-full gap-0 pl-4'):
                                for subitem in item.get('items', []):
                                    nav_button(subitem['label'], subitem['icon'], subitem['route'], small=True)
                    else:
                        nav_button(item['label'], item['icon'], item['route'])

            render_menu_items(get_menu_structure())
        
        ui.space()

    # --- RIGHT DRAWER (Copilot / Assistant) ---
    # Unificado mediante DrawerHub y LayoutManager (Prompt 1)
    from client_app.app.ui.components.drawer_hub import DrawerHub

    right_drawer = ui.right_drawer(value=False, fixed=True).classes('bg-white border-l border-gray-200 z-50').props('behavior=desktop width=400')

    # Estado local para detectar cambios
    drawer_state = {'last_visible': False}

    def sync_drawer():
        """Sincroniza el drawer con layout_manager."""
        if layout_manager.drawer_visible != drawer_state['last_visible']:
            drawer_state['last_visible'] = layout_manager.drawer_visible
            right_drawer.value = layout_manager.drawer_visible

    # Timer que verifica cambios cada 100ms
    ui.timer(0.1, sync_drawer)

    with right_drawer:
        drawer_hub = DrawerHub()
        drawer_hub.render()

    return None

