from nicegui import ui
from typing import List, Literal, Optional
from client_app.app.core.state import state

class WorkflowStepper(ui.column):
    def __init__(self):
        super().__init__()
        self.classes('w-full gap-0') # Vertical stacking with no gap

        # Internal State
        self.mode: Literal['GENERIC', 'FACTORY'] = 'GENERIC'
        self.current_step_index: int = 0

        # Initial Render
        self.update_state('GENERIC', 0)

    def _get_steps_generic(self):
        t = state.i18n.t
        return [
            t('stepper.file_upload', 'Carga de archivos'),
            t('stepper.analysis', 'Análisis y validación'),
            t('stepper.batch_processing', 'Procesamiento lote'),
            t('stepper.results', 'Resultados')
        ]

    def _get_steps_factory(self):
        t = state.i18n.t
        return [
            t('stepper.file_upload', 'Carga de archivos'),
            t('stepper.analysis', 'Análisis y validación'),
            t('stepper.ai_engineering', 'Ingeniería IA'),
            t('stepper.sandbox_test', 'Prueba sandbox'),
            t('stepper.deploy', 'Despliegue')
        ]

    def update_state(self, mode: str = 'GENERIC', current_step: int = 0):
        """
        Updates the stepper state and redraws.
        Ensures visual continuity by keeping completed steps green.
        """
        self.mode = mode
        self.current_step_index = current_step
        self._render()

    def expand_for_factory(self):
        """Helper to switch to Factory mode, usually called from step 2."""
        # If we are at step 1 (index 1 "Análisis") and switch, we stay at index 1 but list changes
        self.update_state('FACTORY', self.current_step_index)

    def expand_for_batch(self):
        """Helper to switch to Batch mode."""
        self.update_state('GENERIC', self.current_step_index)

    def _render(self):
        self.clear()

        # Select Step List
        step_names = self._get_steps_factory() if self.mode == 'FACTORY' else self._get_steps_generic()
        
        with self:
            for i, name in enumerate(step_names):
                # 1. Determine Status
                if i < self.current_step_index:
                    status = 'completed'
                elif i == self.current_step_index:
                    status = 'active'
                else:
                    status = 'pending'
                
                # 2. Styles
                # Base row
                row_classes = 'w-full items-center py-2 px-2 transition-colors duration-300'
                
                # Icon & Text Styles
                if status == 'completed':
                    icon_name = 'check_circle'
                    icon_color = 'text-green-500'
                    text_color = 'text-slate-700 font-medium'
                    bg_color = '' # Optional: 'bg-green-50'
                elif status == 'active':
                    icon_name = 'radio_button_checked'
                    icon_color = 'text-blue-600'
                    text_color = 'text-blue-700 font-bold'
                    bg_color = 'bg-blue-50 rounded-md' # Highlight active step
                else: # pending
                    icon_name = 'radio_button_unchecked'
                    icon_color = 'text-gray-300'
                    text_color = 'text-gray-400'
                    bg_color = ''

                # 3. Draw Row
                with ui.row().classes(f"{row_classes} {bg_color}"):
                    # Icon
                    ui.icon(icon_name).classes(f"{icon_color} text-xl mr-3")
                    
                    # Label
                    ui.label(f"{i+1}. {name}").classes(f"{text_color} text-sm")
                    
                # Optional: Connector Line (visual fluff)
                if i < len(step_names) - 1:
                    # Draw a small vertical line explicitly? 
                    # NiceGUI columns stack elements. A line would need a separate div.
                    # For simplicity, we skip the line for now as requested "lista vertical de ui.row",
                    # but if we wanted it, we'd add a div with border-left here.
                    pass
