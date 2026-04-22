"""
Componente Drawer lateral reutilizable.
Prompt 5.1 del plan de refactorización.
Prompt #8: Añade TabbedSideDrawer con pestañas verticales para Settings, Variables y Copiloto.

Proporciona un drawer que se desliza desde la derecha para abrir
wizards y formularios sin salir del contexto actual.
"""
from typing import Any, Callable, Optional, List, Dict
from dataclasses import dataclass, field
from nicegui import ui


class SideDrawer:
    """
    Drawer lateral reutilizable para abrir wizards y formularios.

    Ejemplo de uso:
        drawer = SideDrawer("Crear Nuevo Script")
        drawer.on_close(lambda script_id: step.config.update({'script_id': script_id}))
        drawer.open(lambda: render_script_wizard(on_save=drawer.close))
    """

    def __init__(self, title: str, width: str = 'w-1/2', min_width: str = '400px'):
        """
        Inicializa el drawer.

        Args:
            title: Título que se muestra en la parte superior
            width: Ancho del drawer (clase Tailwind, ej: 'w-1/2', 'w-2/3')
            min_width: Ancho mínimo en CSS
        """
        self.title = title
        self.width = width
        self.min_width = min_width
        self._close_callbacks: list = []
        self._dialog: Optional[ui.dialog] = None
        self._content_container: Optional[ui.column] = None
        self._is_open = False
        self._return_value: Any = None

    def on_close(self, callback: Callable[[Any], None]) -> 'SideDrawer':
        """
        Registra un callback que se ejecutará cuando el drawer se cierre.

        Args:
            callback: Función que recibe el valor de retorno (puede ser None)

        Returns:
            self para encadenamiento
        """
        self._close_callbacks.append(callback)
        return self

    def open(self, content_callback: Callable[[], None]) -> None:
        """
        Abre el drawer y renderiza el contenido usando el callback.

        Args:
            content_callback: Función que renderiza el contenido del drawer
        """
        if self._is_open:
            return

        self._is_open = True
        self._return_value = None

        # Crear el diálogo que actúa como drawer
        with ui.dialog() as self._dialog:
            self._dialog.props('position=right persistent maximized')

            # Contenedor principal del drawer
            with ui.card().classes(f'{self.width} h-full m-0 rounded-none shadow-2xl').style(f'min-width: {self.min_width}'):
                # Header
                with ui.row().classes('w-full items-center justify-between p-4 border-b bg-gray-50'):
                    ui.label(self.title).classes('text-xl font-bold text-gray-800')
                    ui.button(
                        icon='close',
                        on_click=lambda: self.close(None)
                    ).props('flat round dense color=grey')

                # Contenido con scroll
                with ui.scroll_area().classes('flex-1 w-full'):
                    with ui.column().classes('w-full p-4 gap-4') as container:
                        self._content_container = container
                        # Renderizar contenido
                        content_callback()

        # Agregar estilos para la animación
        ui.add_head_html('''
        <style>
            .q-dialog__inner--minimized > div {
                max-width: none !important;
                max-height: none !important;
            }
            .q-dialog--right .q-dialog__inner {
                justify-content: flex-end;
            }
        </style>
        ''')

        self._dialog.open()

    def close(self, return_value: Any = None) -> None:
        """
        Cierra el drawer y ejecuta los callbacks con el valor de retorno.

        Args:
            return_value: Valor opcional a pasar a los callbacks de cierre
        """
        if not self._is_open:
            return

        self._return_value = return_value
        self._is_open = False

        if self._dialog:
            self._dialog.close()

        # Ejecutar callbacks
        for callback in self._close_callbacks:
            try:
                callback(return_value)
            except Exception as e:
                print(f"Error in drawer close callback: {e}")

    @property
    def is_open(self) -> bool:
        """Indica si el drawer está abierto."""
        return self._is_open

    @property
    def return_value(self) -> Any:
        """Retorna el último valor de retorno."""
        return self._return_value


def open_side_drawer(
    title: str,
    content_callback: Callable[[], None],
    on_close: Optional[Callable[[Any], None]] = None,
    width: str = 'w-1/2'
) -> SideDrawer:
    """
    Función de conveniencia para abrir un drawer rápidamente.
    Crea la instancia, registra el callback de cierre y lo abre en un solo paso.

    Args:
        title: Título del drawer.
        content_callback: Función que renderiza el contenido inicial.
        on_close: Callback opcional que recibe el valor de retorno al cerrar.
        width: Ancho Tailwind del contenedor (ej: 'w-1/2').

    Returns:
        La instancia del SideDrawer creada.
    """
    drawer = SideDrawer(title, width)
    if on_close:
        drawer.on_close(on_close)
    drawer.open(content_callback)
    return drawer


class DrawerWizard:
    """
    Wizard multi-paso dentro de un drawer.

    Ejemplo:
        wizard = DrawerWizard("Crear Script", steps=[
            {"title": "Información", "render": render_step1},
            {"title": "Configuración", "render": render_step2},
            {"title": "Revisar", "render": render_step3},
        ])
        wizard.on_complete(lambda data: save_script(data))
        wizard.open()
    """

    def __init__(self, title: str, steps: list, width: str = 'w-1/2'):
        """
        Inicializa el wizard.

        Args:
            title: Título del wizard
            steps: Lista de pasos, cada uno con 'title' y 'render' callback
            width: Ancho del drawer
        """
        self.title = title
        self.steps = steps
        self.width = width
        self.current_step = 0
        self.data: dict = {}
        self._complete_callbacks: list = []
        self._drawer: Optional[SideDrawer] = None

    def on_complete(self, callback: Callable[[dict], None]) -> 'DrawerWizard':
        """
        Registra un callback que se invocará cuando el usuario finalice el último paso.
        
        Args:
            callback: Función que recibe el diccionario 'data' acumulado.

        Returns:
            self: Permite el encadenamiento de métodos.
        """
        self._complete_callbacks.append(callback)
        return self

    def open(self) -> None:
        """
        Inicializa el SideDrawer y comienza el flujo del asistente desde el primer paso.
        """
        self._drawer = SideDrawer(self.title, self.width)
        self._drawer.open(self._render_wizard)

    def _render_wizard(self) -> None:
        """Renderiza el contenido del wizard."""
        # Indicador de pasos
        with ui.row().classes('w-full justify-center gap-2 mb-4'):
            for i, step in enumerate(self.steps):
                is_current = i == self.current_step
                is_completed = i < self.current_step

                if is_completed:
                    color = 'green'
                    icon = 'check_circle'
                elif is_current:
                    color = 'primary'
                    icon = 'radio_button_checked'
                else:
                    color = 'grey'
                    icon = 'radio_button_unchecked'

                with ui.column().classes('items-center'):
                    ui.icon(icon, color=color)
                    ui.label(step.get('title', f'Paso {i+1}')).classes(
                        f'text-xs {"font-bold" if is_current else ""}'
                    )

        ui.separator().classes('mb-4')

        # Contenido del paso actual
        step_container = ui.column().classes('w-full flex-1')
        with step_container:
            current = self.steps[self.current_step]
            render_fn = current.get('render')
            if render_fn:
                render_fn(self.data, self._update_data)

        ui.separator().classes('mt-4')

        # Botones de navegación
        with ui.row().classes('w-full justify-between mt-4'):
            if self.current_step > 0:
                ui.button(
                    'Anterior',
                    icon='arrow_back',
                    on_click=self._prev_step
                ).props('flat')
            else:
                ui.label('')  # Spacer

            if self.current_step < len(self.steps) - 1:
                ui.button(
                    'Siguiente',
                    icon='arrow_forward',
                    on_click=self._next_step
                ).props('color=primary')
            else:
                ui.button(
                    'Completar',
                    icon='check',
                    on_click=self._complete
                ).props('color=green')

    def _update_data(self, key: str, value: Any) -> None:
        """Actualiza los datos del wizard."""
        self.data[key] = value

    def _next_step(self) -> None:
        """Avanza al siguiente paso."""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._refresh()

    def _prev_step(self) -> None:
        """Retrocede al paso anterior."""
        if self.current_step > 0:
            self.current_step -= 1
            self._refresh()

    def _complete(self) -> None:
        """Completa el wizard."""
        for callback in self._complete_callbacks:
            try:
                callback(self.data)
            except Exception as e:
                print(f"Error in wizard complete callback: {e}")

        if self._drawer:
            self._drawer.close(self.data)

    def _refresh(self) -> None:
        """Refresca el contenido del wizard."""
        if self._drawer and self._drawer._content_container:
            self._drawer._content_container.clear()
            with self._drawer._content_container:
                self._render_wizard()


# === PROMPT #8: TabbedSideDrawer ===

@dataclass
class TabConfig:
    """Configuration for a drawer tab."""
    name: str
    label: str
    icon: str
    tooltip: Optional[str] = None


@dataclass
class CopilotSuggestion:
    """A suggestion from the copilot."""
    message: str
    severity: str = "info"  # info, warning, error
    action: Optional[str] = None


class TabbedSideDrawer(SideDrawer):
    """
    Drawer con pestañas verticales para Settings, Variables y Copiloto.

    Prompt #8: Extiende SideDrawer con un sistema de tabs que separa:
    1. Ajustes (Settings): Configuración técnica del átomo
    2. Variables (Data Pills): Diccionario de entradas/salidas
    3. Copiloto (AI Assistant): Asistencia inteligente

    Ejemplo de uso:
        drawer = TabbedSideDrawer("Configuración de la Acción")
        drawer.set_contract(script.ui_contract)
        drawer.on_tab_change(lambda tab: print(f"Tab changed to {tab}"))
        drawer.open(render_content_fn)
    """

    # Default tab configurations
    DEFAULT_TABS = {
        "settings": TabConfig(
            name="settings",
            label="Ajustes",
            icon="settings",
            tooltip="Configuración técnica"
        ),
        "variables": TabConfig(
            name="variables",
            label="Variables",
            icon="account_tree",
            tooltip="Entradas y salidas (Data Pills)"
        ),
        "copilot": TabConfig(
            name="copilot",
            label="Copiloto",
            icon="auto_awesome",
            tooltip="Asistente de contratos y conexiones"
        ),
    }

    # Copilot placeholder text
    COPILOT_PLACEHOLDER = "Pregunta sobre esta acción o cómo conectar variables..."

    def __init__(self, title: str, width: str = 'w-1/2', min_width: str = '450px'):
        """
        Inicializa el drawer con pestañas.

        Args:
            title: Título del drawer
            width: Ancho del drawer (clase Tailwind)
            min_width: Ancho mínimo en CSS
        """
        super().__init__(title, width, min_width)

        # Tab state
        self.tabs: Dict[str, TabConfig] = dict(self.DEFAULT_TABS)
        self.current_tab: str = "settings"

        # Copilot state
        self.copilot_has_notification: bool = False
        self.copilot_suggestions: List[Dict[str, Any]] = []
        self.copilot_placeholder: str = self.COPILOT_PLACEHOLDER

        # Contract data for variables tab
        self.contract: Optional[Dict[str, Any]] = None

        # Callbacks
        self._tab_change_callbacks: List[Callable[[str], None]] = []

        # UI elements (set during render)
        self._tabs_element = None
        self._tab_panels_element = None

    def on_tab_change(self, callback: Callable[[str], None]) -> 'TabbedSideDrawer':
        """
        Registra un callback para detectar cambios entre las pestañas (Ajustes, Variables, Copiloto).

        Args:
            callback: Función que recibe el nombre técnico de la pestaña activa.

        Returns:
            self para encadenamiento.
        """
        self._tab_change_callbacks.append(callback)
        return self

    def switch_to(self, tab_name: str) -> None:
        """
        Cambia programáticamente a la pestaña especificada.
        Limpia las notificaciones visuales si se accede al Copiloto.

        Args:
            tab_name: Identificador de la pestaña ('settings', 'variables', 'copilot').
        """
        if tab_name not in self.tabs:
            return

        old_tab = self.current_tab
        self.current_tab = tab_name

        # Clear notification when switching to copilot
        if tab_name == "copilot":
            self.copilot_has_notification = False

        # Notify callbacks
        if old_tab != tab_name:
            for callback in self._tab_change_callbacks:
                try:
                    callback(tab_name)
                except Exception as e:
                    print(f"Error in tab change callback: {e}")

    def notify_suggestion_available(self) -> None:
        """
        Activate visual pulse on the Copilot tab.
        Called when the system has suggestions for the user.
        """
        self.copilot_has_notification = True

    def clear_copilot_notification(self) -> None:
        """Clear the copilot notification state."""
        self.copilot_has_notification = False

    def add_copilot_suggestion(
        self,
        message: str,
        severity: str = "info",
        action: Optional[str] = None
    ) -> None:
        """
        Add a suggestion to the copilot.

        Args:
            message: The suggestion text
            severity: info, warning, or error
            action: Optional action identifier
        """
        self.copilot_suggestions.append({
            "message": message,
            "severity": severity,
            "action": action
        })
        # Trigger notification
        self.notify_suggestion_available()

    def set_contract(self, contract: Dict[str, Any]) -> None:
        """
        Set the contract data for the variables tab.

        Args:
            contract: UIContract dict with inputs and outputs
        """
        self.contract = contract

    def get_file_inputs(self) -> List[Dict[str, Any]]:
        """
        Get all FILE or FILES type inputs from the contract.

        Returns:
            List of input definitions that are file types
        """
        if not self.contract:
            return []

        file_inputs = []
        for inp in self.contract.get("inputs", []):
            input_type = inp.get("type", "")
            if input_type in ("FILE", "FILES", "file", "files"):
                file_inputs.append(inp)

        return file_inputs

    def get_state(self) -> Dict[str, Any]:
        """
        Get current drawer state for persistence.

        Returns:
            State dict that can be restored later
        """
        return {
            "current_tab": self.current_tab,
            "copilot_has_notification": self.copilot_has_notification,
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        Restore drawer state from saved state.

        Args:
            state: State dict from get_state()
        """
        if "current_tab" in state:
            self.switch_to(state["current_tab"])

        if "copilot_has_notification" in state:
            self.copilot_has_notification = state["copilot_has_notification"]

    def get_copilot_pulse_css(self) -> str:
        """
        Get CSS for the copilot pulse animation.

        Returns:
            CSS string for amber breathing effect
        """
        return '''
        @keyframes copilot-pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(255, 179, 0, 0.7);
            }
            50% {
                box-shadow: 0 0 0 8px rgba(255, 179, 0, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(255, 179, 0, 0);
            }
        }

        .copilot-pulse {
            animation: copilot-pulse 2s infinite;
            border-radius: 50%;
        }

        .copilot-pulse-icon {
            color: #FFB300 !important;
        }

        .copilot-tab-notification::after {
            content: '';
            position: absolute;
            top: 4px;
            right: 4px;
            width: 8px;
            height: 8px;
            background-color: #FFB300;
            border-radius: 50%;
            animation: copilot-pulse 2s infinite;
        }
        '''

    def get_tab_styles_css(self) -> str:
        """
        Get CSS for vertical tabs styling.

        Returns:
            CSS string for tab styling
        """
        return '''
        .tabbed-drawer-tabs {
            min-width: 60px;
            border-right: 1px solid #e5e7eb;
        }

        .tabbed-drawer-tabs .q-tab {
            padding: 12px 8px;
            min-height: 60px;
        }

        .tabbed-drawer-tabs .q-tab__icon {
            font-size: 24px;
        }

        .tabbed-drawer-tabs .q-tab__label {
            font-size: 10px;
            text-transform: none;
        }

        .tabbed-drawer-content {
            flex: 1;
            overflow: auto;
        }

        .tab-panel-content {
            padding: 16px;
        }
        '''

    def render_tabs(
        self,
        settings_content: Optional[Callable[[], None]] = None,
        variables_content: Optional[Callable[[], None]] = None,
        copilot_content: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Renderiza la interfaz completa de pestañas verticales dentro del drawer.
        Permite inyectar funciones de renderizado personalizadas para cada sección.

        Args:
            settings_content: Callback opcional para dibujar la pestaña de Ajustes.
            variables_content: Callback opcional para dibujar la pestaña de Variables.
            copilot_content: Callback opcional para dibujar la pestaña de Copiloto.
        """
        # Add CSS styles
        ui.add_head_html(f'<style>{self.get_copilot_pulse_css()}{self.get_tab_styles_css()}</style>')

        with ui.row().classes('w-full h-full gap-0'):
            # Vertical tabs
            with ui.tabs().props('vertical').classes('tabbed-drawer-tabs bg-gray-50') as tabs:
                self._tabs_element = tabs

                # Settings tab
                ui.tab(
                    name='settings',
                    icon=self.tabs["settings"].icon,
                    label=self.tabs["settings"].label
                ).tooltip(self.tabs["settings"].tooltip)

                # Variables tab
                ui.tab(
                    name='variables',
                    icon=self.tabs["variables"].icon,
                    label=self.tabs["variables"].label
                ).tooltip(self.tabs["variables"].tooltip)

                # Copilot tab with notification indicator
                copilot_tab = ui.tab(
                    name='copilot',
                    icon=self.tabs["copilot"].icon,
                    label=self.tabs["copilot"].label
                ).tooltip(self.tabs["copilot"].tooltip)

                if self.copilot_has_notification:
                    copilot_tab.classes('copilot-tab-notification')

            # Tab panels
            with ui.tab_panels(tabs, value=self.current_tab).classes('tabbed-drawer-content') as panels:
                self._tab_panels_element = panels

                # Settings panel
                with ui.tab_panel('settings').classes('tab-panel-content'):
                    if settings_content:
                        settings_content()
                    else:
                        self._render_default_settings()

                # Variables panel
                with ui.tab_panel('variables').classes('tab-panel-content'):
                    if variables_content:
                        variables_content()
                    else:
                        self._render_default_variables()

                # Copilot panel
                with ui.tab_panel('copilot').classes('tab-panel-content'):
                    if copilot_content:
                        copilot_content()
                    else:
                        self._render_default_copilot()

            # Handle tab changes
            tabs.on('update:model-value', lambda e: self.switch_to(e.args))

    def _render_default_settings(self) -> None:
        """Render default settings tab content."""
        ui.label("Configuración").classes('text-lg font-bold mb-4')
        ui.label("Selecciona una acción para ver sus ajustes.").classes('text-gray-500')

    def _render_default_variables(self) -> None:
        """Render default variables tab content (Data Pills)."""
        ui.label("Variables (Data Pills)").classes('text-lg font-bold mb-4')

        if not self.contract:
            ui.label("No hay contrato cargado.").classes('text-gray-500 italic')
            return

        # Inputs section
        inputs = self.contract.get("inputs", [])
        if inputs:
            ui.label("Entradas").classes('font-bold text-sm text-gray-600 mb-2')
            with ui.column().classes('gap-2 mb-4'):
                for inp in inputs:
                    self._render_data_pill(inp, "input")

        # Outputs section
        outputs = self.contract.get("outputs", [])
        if outputs:
            ui.label("Salidas").classes('font-bold text-sm text-gray-600 mb-2')
            with ui.column().classes('gap-2'):
                for out in outputs:
                    self._render_data_pill(out, "output")

        # File upload hint
        file_inputs = self.get_file_inputs()
        if file_inputs:
            with ui.card().classes('w-full p-3 bg-blue-50 border border-blue-200 mt-4'):
                ui.label("Esta configuración requiere archivos.").classes('text-sm text-blue-700')
                ui.label("Usa el panel central para cargar archivos de prueba.").classes('text-xs text-blue-600')

    def _render_data_pill(self, field: Dict[str, Any], direction: str) -> None:
        """Render a single data pill (variable)."""
        name = field.get("name", "unknown")
        label = field.get("label", name)
        field_type = field.get("type", "STR")

        # Type icons
        type_icons = {
            "STR": "text_fields",
            "INT": "pin",
            "FLOAT": "decimal_increase",
            "BOOL": "toggle_on",
            "DATE": "calendar_today",
            "DATETIME": "schedule",
            "FILE": "attach_file",
            "FILES": "folder",
            "JSON": "data_object",
        }

        icon = type_icons.get(str(field_type).upper(), "help")
        color = "blue" if direction == "input" else "green"

        with ui.row().classes(f'items-center gap-2 p-2 bg-{color}-50 rounded border border-{color}-200'):
            ui.icon(icon, size='sm', color=color)
            with ui.column().classes('gap-0'):
                ui.label(label).classes(f'text-sm font-medium text-{color}-800')
                ui.label(f"{name} : {field_type}").classes('text-xs text-gray-500')

    def _render_default_copilot(self) -> None:
        """Render default copilot tab content."""
        # Header
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('auto_awesome', color='amber', size='md')
            ui.label("Asistente de Contratos").classes('text-lg font-bold')

        # Suggestions area
        if self.copilot_suggestions:
            ui.label("Sugerencias").classes('font-bold text-sm text-gray-600 mb-2')
            with ui.column().classes('gap-2 mb-4'):
                for suggestion in self.copilot_suggestions[-5:]:  # Last 5
                    severity = suggestion.get("severity", "info")
                    colors = {
                        "info": "blue",
                        "warning": "amber",
                        "error": "red"
                    }
                    color = colors.get(severity, "blue")
                    icons = {
                        "info": "info",
                        "warning": "warning",
                        "error": "error"
                    }
                    icon = icons.get(severity, "info")

                    with ui.card().classes(f'w-full p-3 bg-{color}-50 border border-{color}-200'):
                        with ui.row().classes('items-start gap-2'):
                            ui.icon(icon, color=color)
                            ui.label(suggestion["message"]).classes(f'text-sm text-{color}-800')
        else:
            ui.label("No hay sugerencias pendientes.").classes('text-gray-500 italic mb-4')

        # Chat input
        ui.separator().classes('my-4')
        ui.label("Pregunta al Copiloto").classes('font-bold text-sm text-gray-600 mb-2')

        with ui.row().classes('w-full gap-2'):
            ui.input(placeholder=self.copilot_placeholder).classes('flex-1').props('outlined dense')
            ui.button(icon='send').props('flat color=amber')


# === END PROMPT #8 ===
