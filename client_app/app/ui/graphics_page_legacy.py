from nicegui import ui
from client_app.app.ui.components.graphics_wizard import GraphicsWizard
from client_app.app.ui.components.privacy_indicator import render_privacy_indicator

async def graphics_page():
    """
    Controlador de la página de automatización gráfica (G-Module).
    Permite la visualización de datos mediante la generación dinámica de gráficos
    e informes visuales a partir de fuentes de datos estructuradas.
    """
    
    # State for Selector
    selection_state = {'id': None}

    def on_selection_change(new_id):
        selection_state['id'] = new_id
        render_main_content.refresh()

    @ui.refreshable
    async def render_main_content():
        """
        Dibuja el contenido dinámico de la página.
        Maneja la alternancia entre el modo creación (asistente) y el modo 
        ejecución (selector de automatismos existentes).
        """
        # Title & Privacy
        with ui.row().classes('items-center gap-4 mb-4'):
            ui.label('Automatización de Gráficos (G-Module)').classes('text-2xl font-bold')
            render_privacy_indicator()

        # 1. Selector
        from client_app.app.ui.components.automation_selector import render_automation_selector
        await render_automation_selector(
            automation_type='CHART_GENERATOR', 
            on_change=on_selection_change,
            label="Visualización de Datos"
        )

        # 2. Dynamic Content
        if selection_state['id']:
            # EXECUTION MODE
            with ui.card().classes('w-full max-w-5xl mx-auto p-6 bg-slate-50 border border-slate-200 mt-4'):
                ui.label(f"Generar Gráfico: {selection_state['id']}").classes('text-xl font-bold text-slate-700')
                ui.label("Funcionalidad de ejecución directa en desarrollo...").classes('text-gray-500 italic')
                ui.button("Lanzar (Simulado)", on_click=lambda: ui.notify("Ejecución iniciada", type='positive')).classes('mt-4 bg-purple-600 text-white')

        else:
            # CREATION MODE (Existing Wizard)
            wizard = GraphicsWizard()
            wizard.render()

    pass # Wait for async render? nicegui pages are usually synchronous setup but allow async content
    # But render_automation_selector IS async.
    # So we must await it.
    await render_main_content()
