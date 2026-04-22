from automatia_shared.dtos import TaskSpec, FlowSpec
from client_app.app.ui.layout_state import LayoutState
from typing import Literal, Optional, List

SidebarState = Literal['summary', 'active_assistant']

class FocusManager:
    """
    Orquestador del modo de enfoque (Focus Mode).
    Controla la visualización de asistentes (wizards) a pantalla completa y
    sincroniza el estado del Copilot con el paso actual del flujo de trabajo.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FocusManager, cls).__new__(cls)
            cls._instance.is_active: bool = False
            cls._instance.current_step: Optional[TaskSpec] = None
            cls._instance.current_flow: Optional[FlowSpec] = None # Added for Data Pills
            cls._instance.sidebar_state: SidebarState = 'summary'
            cls._instance.layout_state = LayoutState() # Link to global layout state
            cls._instance.layout_classes: dict[str, bool] = {
                'max-w-7xl': True, 'mx-auto': True, 'p-4': True, 
                'overflow-hidden': False, 'h-screen': False
            }
        return cls._instance

    def enable_focus(self, step: TaskSpec, flow: Optional[FlowSpec] = None):
        """
        Activa el modo de enfoque para un paso específico del flujo.
        Configura el diseño de la página para maximizar el área de trabajo del asistente.

        Args:
            step: Especificación del paso (Step/Task) sobre el que se va a trabajar.
            flow: Especificación del flujo completo para contexto de variables.
        """
        self.is_active = True
        self.current_step = step
        self.current_flow = flow
        self.sidebar_state = 'active_assistant'
        self.layout_state.enter_focus_mode() # Sync with global layout
        
        # Auto-open Copilot when entering Focus Mode
        self.layout_state.is_copilot_visible = True
        self.layout_state.enter_focus_mode()
        
        # Update suggestion count
        suggestions = self.get_suggestions()
        self.layout_state.update_suggestion_count(len(suggestions))
        
        # Update layout classes
        self.layout_classes.update({
            'max-w-7xl': False, 'mx-auto': False, 'p-4': False, 
            'overflow-hidden': True, 'h-screen': True
        })

    def disable_focus(self):
        """Desactiva el modo de enfoque y restaura la visualización estándar de la aplicación."""
        self.is_active = False
        self.current_step = None
        self.current_flow = None
        self.sidebar_state = 'summary'
        self.layout_state.exit_focus_mode() # Sync with global layout
        
        # Update layout classes
        self.layout_classes.update({
            'max-w-7xl': True, 'mx-auto': True, 'p-4': True, 
            'overflow-hidden': False, 'h-screen': False
        })

    # --- Health Service Integration ---
    from client_app.app.services.health_service import WorkflowHealthService
    from client_app.app.services.coherence_service import CoherenceService
    
    def check_health(self) -> List[dict]:
        """
        Ejecuta un análisis de salud del paso actual mediante WorkflowHealthService.
        Identifica problemas de tipos, conexiones faltantes o riesgos de privacidad.

        Returns:
            Lista de incidencias detectadas.
        """
        if not self.current_flow or not self.current_step:
            return []
            
        service = WorkflowHealthService()
        
        # Find index
        step_idx = -1
        for idx, s in enumerate(self.current_flow.steps):
            if s.name == self.current_step.name:
                step_idx = idx
                break
                
        if step_idx != -1:
            return service.check_step(self.current_flow, step_idx)
        return []

    
    def get_suggestions(self) -> List[dict]:
        """
        Obtiene sugerencias accionables basadas en los problemas de salud detectados.
        Utiliza CoherenceService para transformar errores técnicos en propuestas de solución.
        """
        issues = self.check_health()
        if not issues:
            return []
            
        coherence = CoherenceService()
        return coherence.analyze_issues(issues)

    def apply_fix(self, action: dict):
        """
        Ejecuta la acción correctiva propuesta por el asistente de coherencia.
        Puede inyectar pasos puente, solicitar consentimientos o anonymizar variables.

        Args:
            action: Diccionario que describe el tipo de acción y su carga útil (payload).
        """
        if action['action_type'] == 'CREATE_STEP':
            # Logic for Prompt 7 Bridge Creator
            from client_app.app.services.bridge_creator import BridgeService
            
            if not self.current_flow or not self.current_step:
                return
            
            # Simple heuristic: insert before current step
            # In a real app, we would find the best place or ask the user,
            # but for Prompt 7 we assume "Just fix it before this step".
            step_idx = -1
            for idx, s in enumerate(self.current_flow.steps):
                if s.name == self.current_step.name:
                    step_idx = idx
                    break
            
            if step_idx > 0:
                bridge = BridgeService(self.current_flow)
                missing_var = action['action_payload']['output_var']
                
                # Mock context: assume previous step has specific output or just use generic
                # Ideally we ask PillProvider what is available.
                # For demo purposes, we connect to first available output of previous step
                prev_step = self.current_flow.steps[step_idx - 1]
                source_var = prev_step.outputs[0] if prev_step.outputs else "unknown_source"
                
                code = bridge.generate_bridge_code_mock(missing_var, source_var)
                
                bridge.inject_bridge_task(
                    at_index=step_idx,
                    code=code,
                    inputs=[source_var],
                    outputs=[missing_var]
                )
                return True
        
        elif action['action_type'] == 'GRANT_CONSENT':
            # Logic for Prompt 8
            if not self.current_flow:
                return False
                
            step_idx = action['action_payload'].get('step_index')
            if step_idx is not None and 0 <= step_idx < len(self.current_flow.steps):
                self.current_flow.steps[step_idx].metadata['privacy_consent'] = True
                return True
                
        elif action['action_type'] == 'ANONYMIZE_VAR':
            # Calls BridgeService similar to CREATE_STEP but with specific Anonymizer logic
            # For now, we reuse the mock Bridge logic or imply it wraps CREATE_STEP
            # To be fully rigorous we would use BridgeService with an anonymization script template
            pass
            
        return False

    def refresh_suggestions(self):
        """
        Recalcula las sugerencias actuales y actualiza el contador global de la interfaz.
        Se activa cuando ocurre un cambio estructural en el flujo de trabajo.
        """
        suggestions = self.get_suggestions()
        self.layout_state.update_suggestion_count(len(suggestions))
        if hasattr(self, 'refresh_copilot'):
            self.refresh_copilot()
