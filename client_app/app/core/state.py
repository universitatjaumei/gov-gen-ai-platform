from typing import TYPE_CHECKING, Optional, Any, Union, List, Callable, Dict
from datetime import datetime

from client_app.app.core.rpa_executor import RPAExecutor
# from client_app.app.services.extraction_service import ExtractionService
from automatia_shared.core.i18n import i18n
from automatia_shared.dtos import AdminProfileDTO, PartnerProfileDTO, ClientProfileDTO

if TYPE_CHECKING:
    from client_app.app.services.extraction_service import ExtractionService

class AppState:
    def __init__(self):
        # Brain client: puede ser BrainAPIClient (HTTP) o LocalBrainClient (monolito local)
        self.brain: Any = None
        self.rpa: RPAExecutor = None
        self.extractor: "ExtractionService" = None
        self.i18n = i18n
        self.sidebar_refresher = None  # Callable for refreshing sidebar UI
        
        # User and Role State
        self.current_role: Optional[str] = None
        self.current_user: Optional[Union[AdminProfileDTO, PartnerProfileDTO, ClientProfileDTO]] = None

        # Focus Mode State (Prompt 4)
        self.focus_mode: bool = False
        self.active_drawer_content: Optional[str] = None
        self.focus_mode_watchers = []  # List of callbacks for UI updates
        
        # Callbacks for specific drawer functions (Prompt 10)
        self.on_apply_flow_proposal: Optional[Callable[[List[Dict]], Any]] = None  # Callback para aplicar propuesta de pasos
        self.on_apply_etl_proposal: Optional[Callable[[List[Dict]], Any]] = None
        self.on_apply_etl_ai_prompt: Optional[Callable[[str], Any]] = None  # Callback para aplicar prompt de ETL Modo IA
        self.on_apply_graphics_proposal: Optional[Callable[[Dict], Any]] = None
        self.on_apply_report_proposal: Optional[Callable[[List[Dict]], Any]] = None
        self.on_atom_select_callback = None
        self.wizard_initial_step_type = None  # To pass data to wizard

        # === Wizard de Átomos con Contratos (Data Contracts Fase 2) ===
        self.wizard_initial_subtype: Optional[str] = None  # Subtipo de conexión (EMAIL, API, DATABASE)
        self.wizard_show_connection_subtypes: bool = False  # Mostrar vista de subtipos
        self.wizard_flow_context = None  # Contexto del flujo para añadir paso tras crear átomo

        # === Contexto de Flujo para Diseño Contextual (naming.md Tarea 1) ===
        self.flow_context: Optional[dict] = None  # Contexto cuando se edita paso desde flujo
        # Estructura: {
        #   'mode': 'contextual',
        #   'flow_id': int,
        #   'flow_name': str,
        #   'step_index': int,
        #   'step': TaskSpec,
        #   'previous_steps': List[TaskSpec],
        #   'available_variables': List[dict]
        # }

        # === Active Service/Atom ID para navegación ===
        self.active_service_id: Optional[int] = None  # ID del servicio/átomo activo para diseño

        # === Copiloto Activo (Propuestas de Flujos) ===
        self.on_apply_flow_proposal: Optional[Callable[[List[Dict]], Any]] = None  # Callback para aplicar propuesta de pasos

        # Step Configuration State
        self.editing_step = None 
        self.editing_flow = None 
        self.on_step_change = None # Callback to refresh UI when step config changes (from inside form)
        
        self.step_edit_watchers = [] # Watchers for when a DIFFERENT step is selected for editing
        
        # Wizard persistence (Prompt 4.2)
        self.editing_draft: Optional[Dict[str, Any]] = None

        # Flow Context Helper Attributes
        self.flow_step_index: int = -1
        self.flow_name: Optional[str] = None
        self.flow_id: Optional[int] = None

        # === Contexto de Datos para Copiloto (Fase 2) ===
        # Las páginas de diseño (ETL, Graphics, Reports) actualizan este campo
        # cuando cargan datos, para que el Copiloto conozca las columnas disponibles.
        self.current_data_context: Optional[Dict[str, Any]] = None
        # Estructura esperada: {
        #   'columns': ['col1', 'col2', ...],
        #   'dtypes': {'col1': 'int64', 'col2': 'object', ...},
        #   'row_count': int,
        #   'sample_values': {'col1': ['val1', 'val2'], ...}  # 2-3 valores de ejemplo por columna
        # }

    def clear_atom_editing_context(self):
        """Limpia el contexto de edición de un átomo dentro de un flujo."""
        self.editing_step = None
        self.editing_flow = None
        self.flow_step_index = -1
        self.flow_name = None
        self.flow_id = None
        # Notificar watchers de limpieza
        for watcher in self.step_edit_watchers:
            try:
                watcher(None, None)
            except Exception:
                pass

    def add_step_edit_watcher(self, callback):
        """Registers a callback to be called when the editing step changes"""
        if callback not in self.step_edit_watchers:
            self.step_edit_watchers.append(callback)

    def remove_step_edit_watcher(self, callback):
        """Removes a registered step edit watcher"""
        if callback in self.step_edit_watchers:
            self.step_edit_watchers.remove(callback)

    def set_role(self, role: Optional[str]):
        """
        Cambia el rol del usuario y carga un perfil mock/real.
        """
        if not role:
            self.current_role = None
            self.current_user = None
            return

        if role == "admin":
            self.current_role = "admin"
            self.current_user = AdminProfileDTO(
                admin_id=1,
                name="Super Admin",
                email="admin@automatia.com",
                created_at=datetime.utcnow()
            )
        elif role == "partner":
            self.current_role = "partner"
            self.current_user = PartnerProfileDTO(
                partner_id="part_001",
                name="Global Partner",
                email="partner@global.com",
                credits_balance=1000,
                created_at=datetime.utcnow()
            )
        elif role == "client":
            self.current_role = "client"
            self.current_user = ClientProfileDTO(
                client_id="cli_001",
                name="End Client",
                partner_id="part_001",
                created_at=datetime.utcnow()
            )
        else:
            raise ValueError(f"Unknown role: {role}")

    def set_editing_step(self, step, flow):
        """Sets the current step being edited and notifies watchers"""
        self.editing_step = step
        self.editing_flow = flow
        for watcher in self.step_edit_watchers:
            try:
                watcher(step, flow)
            except Exception as e:
                print(f"Error in step edit watcher: {e}")

    def set_flow_context(self, flow_id: int, flow_name: str, step, step_index: int, all_steps: list):
        """Establece el contexto del flujo para diseño contextual de átomos."""
        available_vars = []
        all_steps_config = []

        for i, prev_step in enumerate(all_steps):
            if isinstance(prev_step, dict):
                step_type_val = prev_step.get('type', '')
                if hasattr(step_type_val, 'value'): step_type_val = step_type_val.value
                step_name = prev_step.get('name', '')
                step_config = prev_step.get('config', {})
                step_outputs = prev_step.get('outputs', [])
            else:
                step_type_val = getattr(prev_step, 'type', '')
                if hasattr(step_type_val, 'value'): step_type_val = step_type_val.value
                step_name = getattr(prev_step, 'name', '')
                step_config = getattr(prev_step, 'config', {})
                step_outputs = getattr(prev_step, 'outputs', []) or []

            # Configuración serializada para el PreviewDataService
            all_steps_config.append({
                'type': str(step_type_val),
                'name': step_name,
                'config': step_config,
            })
            if i < step_index:
                available_vars.append({
                    'step_index': i,
                    'step_name': step_name,
                    'step_type': str(step_type_val),
                    'output_ref': f'{{{{steps.{step_name}.output}}}}',
                    'outputs': step_outputs
                })

        self.flow_context = {
            'mode': 'contextual',
            'flow_id': flow_id,
            'flow_name': flow_name,
            'step_index': step_index,
            'step': step,
            'previous_steps': all_steps[:step_index],
            'available_variables': available_vars,
            'all_steps_config': all_steps_config,  # Para PreviewDataService
        }

        # También establecer los atributos individuales para acceso directo
        self.flow_id = flow_id
        self.flow_name = flow_name
        self.flow_step_index = step_index

    def clear_flow_context(self):
        """Limpia el contexto del flujo."""
        self.flow_context = None
        self.flow_id = None
        self.flow_name = None
        self.flow_step_index = -1

    def refresh_flow_context_steps(self, all_steps: list):
        """
        Actualiza all_steps_config en el flow_context con la configuración actual de los pasos.

        Debe llamarse después de modificar step.config para que el preview de datos
        refleje los cambios (ej: después de guardar un átomo ETL).
        """
        if not self.flow_context:
            return

        all_steps_config = []
        for i, prev_step in enumerate(all_steps):
            if isinstance(prev_step, dict):
                step_type_val = prev_step.get('type', '')
                if hasattr(step_type_val, 'value'): step_type_val = step_type_val.value
                step_name = prev_step.get('name', '')
                step_config = prev_step.get('config', {})
            else:
                step_type_val = getattr(prev_step, 'type', '')
                if hasattr(step_type_val, 'value'): step_type_val = step_type_val.value
                step_name = getattr(prev_step, 'name', '')
                step_config = getattr(prev_step, 'config', {})

            all_steps_config.append({
                'type': str(step_type_val),
                'name': step_name,
                'config': step_config,
            })

        self.flow_context['all_steps_config'] = all_steps_config

    def toggle_focus_mode(self, active: bool, content: Optional[str] = None):
        """
        Activates or deactivates Focus Mode (Mini Sidebar + Expanded Right Drawer).

        NOTA: Este método sincroniza con layout_manager. El binding reactivo de
        NiceGUI se encarga de actualizar la UI automáticamente.
        """
        # Importación tardía para evitar ciclos
        from client_app.app.services.layout_manager import layout_manager

        if active:
            self.focus_mode = True
            if content:
                self.active_drawer_content = content

            # Sincronizar con layout_manager
            if content == 'atom_selector' or content == 'gallery':
                layout_manager.enter_gallery_mode()
            elif content == 'copilot':
                # Para copilot, abrir drawer y contraer menú
                layout_manager.drawer_visible = True
                layout_manager.active_tab = 'copilot'
                layout_manager.menu_mini_mode = True
            else:
                # Default: modo diseño con menú contraído
                layout_manager.drawer_visible = True
                layout_manager.active_tab = 'stepper'
                layout_manager.menu_mini_mode = True
        else:
            self.focus_mode = False
            self.active_drawer_content = None
            # Limpiar contexto de edición al salir de modo foco
            self.editing_step = None
            self.editing_flow = None
            # Sincronizar cierre con layout_manager
            layout_manager.exit_focus_mode()

    def add_focus_watcher(self, callback):
        """Registers a callback to be called when focus mode changes"""
        if callback not in self.focus_mode_watchers:
            self.focus_mode_watchers.append(callback)

    def remove_focus_watcher(self, callback):
        """Removes a registered focus watcher"""
        if callback in self.focus_mode_watchers:
            self.focus_mode_watchers.remove(callback)


    def db_session(self):
        """Helper to get a client DB session context manager"""
        from client_app.app.database.db import client_engine
        from sqlmodel.ext.asyncio.session import AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        # Create a sessionmaker that binds to the client engine
        async_session = sessionmaker(
            client_engine, class_=AsyncSession, expire_on_commit=False
        )
        return async_session()


# Global State Instance
app_state = AppState()
state = app_state # Alias for backward compatibility
