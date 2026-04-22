from nicegui import ui, app
from client_app.app.core.state import app_state
from automatia_shared.enums import StepType
from client_app.app.ui.components.step_forms.extraction_form import render_extraction_form
from client_app.app.ui.components.step_forms.api_fetch_form import render_api_fetch_form
from client_app.app.ui.components.step_forms.email_send_form import render_email_send_form
from client_app.app.ui.components.step_forms.generic_form import render_generic_form
from client_app.app.services.resource_listing_service import resource_listing_service
from client_app.app.services.data_flow_analyzer import data_flow_analyzer

class StepConfigurator(ui.column):
    """
    Gestor reactivo de configuración para pasos de un flujo de trabajo.
    Implementa una interfaz de pestañas (Ajustes, Variables, Copiloto) que se
    adapta dinámicamente al tipo de átomo seleccionado.
    """
    def __init__(self):
        super().__init__()
        self.classes('w-full h-full p-0 gap-0 overflow-hidden')  # Remove padding for tabs
        self.step = None
        self.flow = None
        self.current_tab = "settings"
        
        # Bind visibility to valid state
        self.bind_visibility_from(app_state, 'editing_step', backward=lambda x: x is not None)
        
        # Initial Render (Schedule it once since it's async)
        ui.timer(0, self.render, once=True)
        
        # Cleanup on disconnect
        app.on_disconnect(self._on_disconnect)
        
        # Listen for changes
        app_state.add_step_edit_watcher(self.refresh_content)

    def refresh_content(self, step, flow):
        """
        Actualiza el paso que se está editando y fuerza un re-renderizado.
        
        Args:
            step: El nuevo objeto TaskSpec a configurar.
            flow: El flujo completo (FlowSpec) para el contexto de variables.
        """
        self.step = step
        self.flow = flow
        self.clear()
        self.render()

    async def render(self):
        # Abort if client is deleted or not connected (prevents "Client deleted" errors)
        if not self.client or not self.client.has_socket_connection:
            return

        if not self.step or not self.flow:
            with self:
                ui.label('No step selected').classes('text-gray-500 italic p-4')
            return

        with self:
            # Header
            with ui.row().classes('w-full items-center justify-between p-4 border-b bg-gray-50'):
                 with ui.row().classes('items-center gap-2'):
                    ui.label(f"Configurando:").classes('text-sm text-gray-500')
                    ui.label(f"{self.step.name}").classes('text-lg font-bold text-slate-800')
                 ui.button(icon='close', on_click=self.close_drawer).props('flat round dense color=grey')

            # Tabbed Interface
            from client_app.app.ui.layout_state import LayoutState
            layout_state = LayoutState()

            with ui.row().classes('w-full h-full gap-0 flex-nowrap'):
                # Vertical tabs
                with ui.tabs().props('vertical').classes('bg-gray-100 border-r min-w-[60px]') as tabs:
                    ui.tab('settings', icon='settings', label='Ajustes').tooltip('Configuración técnica')
                    ui.tab('variables', icon='account_tree', label='Variables').tooltip('Entradas y salidas (Data Pills)')
                    copilot_tab = ui.tab('copilot', icon='auto_awesome', label='Copiloto').tooltip('Asistente de IA')
                    
                    # Pulse logic: show breathing effect when there are suggestions
                    copilot_tab.bind_classes({'copilot-pulse': True}, layout_state, 'suggestion_count', backward=lambda n: n > 0)

                # Tab panels
                with ui.tab_panels(tabs, value=self.current_tab).classes('flex-1 h-full overflow-y-auto') as panels:
                    self.current_tab = panels.value # Keep track
                    
                    # Settings panel
                    with ui.tab_panel('settings').classes('p-4'):
                        await self._render_specific_form()
                    
                    # Variables panel
                    with ui.tab_panel('variables').classes('p-4'):
                        self._render_data_flow_analysis()
                    
                    # Copilot panel
                    with ui.tab_panel('copilot').classes('p-4'):
                        self._render_copilot_tab()

            # Bottom Actions (Optional in tabbed mode, maybe just in Settings)
            # with ui.row().classes('w-full justify-end mt-4 pt-4 border-t'):
            #      ui.button('Back to List', on_click=self.close_drawer).props('flat')
    
    def close_drawer(self):
        app_state.toggle_focus_mode(False)
        app_state.active_drawer_content = None
        app_state.editing_step = None

    def _render_data_flow_analysis(self):
        """Renders available variables and output suggestions"""
        try:
             if self.step in self.flow.steps:
                 step_index = self.flow.steps.index(self.step)
                 # Import provider to get pills directly
                 from client_app.app.ui.pill_logic import PillProvider
                 provider = PillProvider(self.flow)
                 pills = provider.get_available_pills(step_index)
                 
                 ui.label('Variables Disponibles (Data Pills)').classes('text-lg font-bold mb-4')
                 
                 # --- FILE DETECTION (Prompt 8) ---
                 from client_app.app.config.atom_catalog import get_atom_metadata
                 from automatia_shared.contracts.ui_contract import InputType
                 
                 meta = get_atom_metadata(self.step.type)
                 schema = meta.config_schema or {}
                 properties = schema.get('properties', {})
                 
                 has_file_input = False
                 # Check schema
                 for prop_name, prop_def in properties.items():
                     if prop_def.get('type') in ('file', 'files', InputType.FILE, InputType.FILES):
                         has_file_input = True
                         break
                 
                 # Hardcoded check for specific steps until contracts are fully implemented
                 if self.step.type in (StepType.EXTRACTION, StepType.ANONYMIZATION):
                     has_file_input = True
                     
                 if has_file_input:
                     with ui.card().classes('w-full bg-amber-50 border border-amber-200 p-3 mb-4 shadow-none'):
                         with ui.row().classes('items-center gap-2 mb-1'):
                             ui.icon('cloud_upload', color='amber-8', size='sm')
                             ui.label('Este paso requiere archivos').classes('text-sm font-bold text-amber-900')
                         ui.markdown('Sugerencia: Usa el **Sandbox Central** para subir archivos temporales y probar este paso.').classes('text-xs text-amber-800')

                 with ui.column().classes('w-full gap-4'):
                     # Available Inputs
                     ui.label('Entradas Disponibles').classes('font-bold text-sm text-gray-400 uppercase tracking-wider')
                     if pills:
                         with ui.row().classes('flex-wrap gap-2'):
                             for pill in pills:
                                 with ui.button(on_click=lambda p=pill: ui.notify(f"Copiado: {p.reference}")).props('rounded outline dense size=sm').classes('px-2 py-1 bg-blue-50 hover:bg-blue-100 border-blue-200'):
                                     with ui.row().classes('items-center gap-1'):
                                         ui.icon('database', size='xs', color='blue')
                                         ui.label(pill.label).classes('text-xs font-medium text-slate-700')
                                 ui.tooltip(f"Clic para copiar {pill.reference}")
                     else:
                         ui.label('No hay datos previos disponibles').classes('text-sm text-gray-500 italic pb-4')
                     
                     ui.separator()
                     
                     # Output Config
                     ui.label('Configuración de Salida').classes('font-bold text-sm text-gray-400 uppercase tracking-wider')
                     from client_app.app.services.data_flow_analyzer import data_flow_analyzer
                     suggested_name = data_flow_analyzer.suggest_output_var_name(self.step.type, step_index)
                     current_output = self.step.config.get('output_var', '')
                     
                     ui.input(
                         'Nombre de la Variable de Salida', 
                         value=current_output,
                         placeholder=suggested_name,
                         on_change=lambda e: self._update_config('output_var', e.value)
                     ).props('dense outlined').classes('w-full text-sm')
                     
                     ui.label('Esta variable estará disponible para los siguientes pasos del flujo.').classes('text-xs text-gray-500 italic')
        except Exception as e:
            ui.label(f"Data Flow Error: {str(e)}").classes('text-red-400 text-xs')

    async def _render_specific_form(self):
        """Renders the appropriate form based on step type"""
        
        # Callback for when form changes data
        def on_change():
            # Notify flow editor to update validation status
            if app_state.on_step_change:
                app_state.on_step_change()

        # Use extracted panel function
        from client_app.app.ui.components.step_panels import render_settings_panel
        await render_settings_panel(self.step, self.flow, on_change)

    def _render_copilot_tab(self):
        """Renders the copilot / assistant tab content"""
        from client_app.app.ui.components.step_panels import render_copilot_panel
        render_copilot_panel(self.step, self.flow)


    def _update_config(self, key, value):
        self.step.config[key] = value
        if app_state.on_step_change:
            app_state.on_step_change()

    def _on_disconnect(self):
        """Cleanup to avoid memory leaks and stale updates"""
        app_state.remove_step_edit_watcher(self.refresh_content)

