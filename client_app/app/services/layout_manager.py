from typing import Literal, List, Optional, Any, Dict
from automatia_shared.enums import StepType


class LayoutManager:
    """
    Gestiona el estado del layout (diseño vs ejecución).
    Actúa como fuente de verdad para la visibilidad del drawer y el modo del menú.

    NOTA: Este es el ÚNICO gestor de estado del drawer. Usa binding reactivo
    de NiceGUI (bind_value) en lugar de watchers manuales para evitar errores
    de elementos eliminados.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.current_mode: Literal['design', 'execution', 'gallery', 'documentation', None] = None
        self.drawer_visible: bool = False
        self.drawer_tabs: List[str] = ['stepper', 'pills', 'copilot']  # 3 pestañas: Ajustes, Variables, Copilot
        self.active_tab: str = 'stepper'  # Pestaña activa del DrawerHub
        self.menu_mini_mode: bool = False
        self.designing_atom_type: Optional[StepType] = None  # Tipo de átomo que se está diseñando
        self.designing_atom_id: Optional[str] = None  # ID del átomo en edición (si existe)
        self.from_flow_context: bool = False  # NUEVO: Indica si se viene desde un flujo
        # Datos para modo documentación
        self.doc_atom_data: Optional[Dict[str, Any]] = None  # {name, doc_path, input_contract, output_contract}
        # Mensaje pendiente para el copiloto (para comunicación entre páginas y drawer)
        self.pending_copilot_message: Optional[str] = None
        # Controla si la galería muestra la sección de biblioteca (Mi biblioteca)
        self.gallery_show_library: bool = True
        # Filtro por tipo de paso para la galería (cuando se vincula a un paso específico)
        self.gallery_filter_step_type: Optional[StepType] = None
        # Configuración de la página de diseño actual (para drawer sin editing_step)
        # Permite sincronizar el stepper lateral con el estado de la página modular
        self.page_design_config: Dict[str, Any] = {
            'current_step_index': 0,
            'completed_step_indexes': []
        }
        # Borrador de prompt propuesto por el copiloto (para comunicación drawer → página LLM)
        self.pending_prompt_draft: Optional[str] = None
        # Bandera para mostrar la documentación a pantalla completa (en la capa main_layout)
        self.fullscreen_doc_visible: bool = False

    def enter_design_mode(
        self,
        atom_type: StepType = None,
        atom_id: Optional[int] = None,
        flow_context: Optional[Any] = None,
        from_flow: bool = False  # NUEVO: Indica si se accede desde un flujo
    ):
        """Activa modo diseño con drawer visible y pestaña de stepper."""
        self.current_mode = 'design'
        self.drawer_visible = True
        self.menu_mini_mode = True
        self.active_tab = 'stepper'
        self.designing_atom_type = atom_type  # Guardar tipo de átomo
        self.designing_atom_id = str(atom_id) if atom_id else None
        self.from_flow_context = from_flow  # NUEVO

        # Limpiar contexto de edición si es standalone (no viene de flujo)
        from client_app.app.core.state import app_state
        if not from_flow:
            app_state.clear_atom_editing_context()

    def enter_gallery_mode(self, show_library: bool = True, filter_step_type: Optional[StepType] = None):
        """
        Activa modo galería con drawer visible. La galería se muestra en la pestaña stepper.

        Args:
            show_library: Si True, muestra la sección "Mi biblioteca" en la galería.
                          Si False, solo muestra "Crear nuevo" (útil cuando ya hay
                          una vista de biblioteca en la página principal).
            filter_step_type: Si se especifica, filtra la galería para mostrar solo
                              acciones de este tipo (útil al vincular a un paso específico).
        """
        self.current_mode = 'gallery'
        self.drawer_visible = True
        self.menu_mini_mode = True
        self.active_tab = 'stepper'  # La galería está integrada en stepper
        self.designing_atom_type = None  # Limpiar tipo de átomo
        self.designing_atom_id = None
        self.doc_atom_data = None
        self.gallery_show_library = show_library
        self.gallery_filter_step_type = filter_step_type

    def enter_documentation_mode(
        self,
        atom_name: str,
        doc_path: Optional[str] = None,
        input_contract: Optional[str] = None,
        output_contract: Optional[str] = None,
        status: str = 'PUBLISHED',
        description: str = "",
        resource_id: Optional[int] = None,
        record_type: str = 'atom'
    ):
        """
        Activa modo documentación con drawer visible.
        - Tab stepper muestra README.md y metadatos editables.
        - Tab pills muestra contratos de datos.
        """
        self.current_mode = 'documentation'
        self.drawer_visible = True
        self.menu_mini_mode = True
        self.active_tab = 'stepper'  # Empezar en documentación
        self.designing_atom_type = None
        self.designing_atom_id = None
        self.doc_atom_data = {
            'name': atom_name,
            'description': description,
            'doc_path': doc_path,
            'input_contract': input_contract,
            'output_contract': output_contract,
            'status': status,
            'resource_id': resource_id,
            'record_type': record_type  # 'library' or 'atom'
        }

    def enter_execution_mode(self, atom_id: int = None):
        """Activa modo ejecución sin drawer."""
        self.current_mode = 'execution'
        self.drawer_visible = False
        self.menu_mini_mode = False

    def enter_flow_edit_mode(self):
        """
        Activa modo edición de flujo con drawer visible solo en pestaña Copiloto.
        El usuario puede describir su automatización y recibir sugerencias de IA.
        """
        self.current_mode = 'flow_edit'
        self.drawer_visible = True
        self.menu_mini_mode = True
        self.active_tab = 'copilot'  # Solo mostrar el copiloto
        self.designing_atom_type = None
        self.designing_atom_id = None
        self.doc_atom_data = None

    def exit_focus_mode(self):
        """Vuelve a estado normal y limpia todo el contexto de diseño/documentación."""
        self.current_mode = None
        self.drawer_visible = False
        self.menu_mini_mode = False
        self.active_tab = 'stepper'  # Reset a pestaña por defecto
        self.designing_atom_type = None  # Limpiar tipo de átomo
        self.designing_atom_id = None
        self.doc_atom_data = None  # Limpiar datos de documentación
        self.from_flow_context = False

        from client_app.app.core.state import app_state
        app_state.clear_atom_editing_context()

        self.page_design_config = {
            'current_step_index': 0,
            'completed_step_indexes': []
        }
        self.pending_copilot_message = None  # Limpiar mensajes pendientes
        self.pending_prompt_draft = None  # Limpiar borradores de prompt

    def exit_design_mode_to_flow(self):
        """
        Sale del modo diseño de átomo y vuelve al modo galería.
        Usado cuando se regresa de una página de diseño de átomo al editor de flujos.
        Resetea el drawer a modo galería para permitir añadir más pasos.
        """
        self.current_mode = 'gallery'
        self.drawer_visible = True
        self.menu_mini_mode = True
        self.active_tab = 'stepper'
        self.designing_atom_type = None
        self.designing_atom_id = None
        self.from_flow_context = False

    def set_active_tab(self, tab: str):
        """Cambia la pestaña activa del drawer sin cambiar el modo."""
        if tab in self.drawer_tabs:
            self.active_tab = tab

    def switch_to_stepper(self):
        """Cambia a la pestaña de stepper (útil tras seleccionar átomo)."""
        self.active_tab = 'stepper'

    def open_drawer_with_message(self, message: str):
        """
        Abre el drawer en la pestaña del copiloto con un mensaje pendiente.

        El mensaje será enviado automáticamente cuando el chat del copiloto
        se renderice. Útil para botones de ayuda contextual en páginas de diseño.

        Args:
            message: Mensaje que se enviará al copiloto como si el usuario lo escribiera
        """
        self.pending_copilot_message = message
        self.drawer_visible = True
        self.active_tab = 'copilot'

    def consume_pending_message(self) -> Optional[str]:
        """
        Consume y retorna el mensaje pendiente del copiloto.

        Returns:
            El mensaje pendiente o None si no hay ninguno
        """
        message = self.pending_copilot_message
        self.pending_copilot_message = None
        return message

    def update_step_index(self, index: int, completed: List[int] = None):
        """
        Actualiza el índice del paso actual para el stepper del drawer.
        
        Args:
            index: Índice del paso actual (0-based)
            completed: Lista opcional de índices de pasos completados
        """
        if self.page_design_config is None:
            self.page_design_config = {'current_step_index': 0, 'completed_step_indexes': []}
            
        self.page_design_config['current_step_index'] = index
        if completed is not None:
            self.page_design_config['completed_step_indexes'] = completed
        else:
            # Por defecto, todos los anteriores al actual están completados
            self.page_design_config['completed_step_indexes'] = list(range(index))
        
        # Opcional: Podríamos disparar un refresh del drawer aquí si fuera necesario
        # pero DrawerHub suele reaccionar al cambio en layout_manager si está bindeado.


# Instancia global para facilitar acceso
layout_manager = LayoutManager()
