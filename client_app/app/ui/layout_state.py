from typing import Literal

ViewMode = Literal['STANDARD', 'FOCUS']

class LayoutState:
    """
    Gestiona el estado global de la interfaz de usuario (UI).
    Controla modos como 'FOCUS' (concentrado) o 'STANDARD', la visibilidad del Copilot,
    y el contador de sugerencias de salud del flujo.
    Implementa el patrón Singleton para asegurar una única fuente de verdad en la UI.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LayoutState, cls).__new__(cls)
            cls._instance.view_mode: ViewMode = 'STANDARD'
            cls._instance.expert_mode: bool = False
            # cls._instance.is_copilot_visible: bool = False # Removed, now property
            cls._instance.suggestion_count: int = 0
            cls._instance.suggestions: list = []  # List of suggestion dicts for Copilot
            cls._instance.auto_opened: bool = False
        return cls._instance

    @property
    def is_copilot_visible(self) -> bool:
        from client_app.app.services.layout_manager import layout_manager
        return layout_manager.drawer_visible

    @is_copilot_visible.setter
    def is_copilot_visible(self, value: bool):
        from client_app.app.services.layout_manager import layout_manager
        if value:
            layout_manager.drawer_visible = True
            layout_manager.active_tab = 'copilot'
        else:
            layout_manager.exit_focus_mode()


    def toggle_expert_mode(self):
        """Alterna el modo experto que desbloquea opciones avanzadas en la UI."""
        self.expert_mode = not self.expert_mode

    def enter_focus_mode(self):
        """Activa el modo de enfoque (Focus), optimizado para asistentes y wizards."""
        self.view_mode = 'FOCUS'

    def exit_focus_mode(self):
        """Regresa al modo de visualización estándar de la aplicación."""
        self.view_mode = 'STANDARD'
    
    def toggle_copilot(self):
        """Muestra u oculta el panel lateral del asistente (Copilot)."""
        from client_app.app.services.layout_manager import layout_manager

        # Toggle basado en el estado del layout_manager
        if layout_manager.drawer_visible:
            layout_manager.exit_focus_mode()
        else:
            layout_manager.drawer_visible = True
            layout_manager.active_tab = 'copilot'

    def update_suggestion_count(self, count: int):
        """
        Actualiza el contador de sugerencias de salud (Health Check).
        Si se detectan problemas nuevos, abre automáticamente el Copilot 
        para notificar al usuario.

        Args:
            count (int): Número total de sugerencias activas.
        """
        self.suggestion_count = count
        if count > 0 and not self.is_copilot_visible:
            self.is_copilot_visible = True
            self.auto_opened = True
        elif count == 0 and self.auto_opened:
            # Auto-close if it was auto-opened and no more suggestions
            self.is_copilot_visible = False
            self.auto_opened = False

    @property
    def main_container_classes(self) -> str:
        """
        Calcula las clases de CSS dinámicas para el contenedor principal.
        Aplica restricciones de altura y scroll en modo FOCUS para evitar
        el desplazamiento de la página completa fuera de los wizards.

        Returns:
            str: Cadena de clases Tailwind CSS.
        """
        if self.view_mode == 'FOCUS':
            return "overflow-hidden h-screen"
        return "max-w-7xl mx-auto p-4"
