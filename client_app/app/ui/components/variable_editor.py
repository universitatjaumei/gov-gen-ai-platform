from typing import List, Dict, Callable, Optional
from nicegui import ui
from automatia_shared.contracts.ui_contract import OutputField, InputType

class OutputVariableEditor:
    """
    Editor to define the Output Contract (variables generated) of an atom.
    Used for 'Input' type atoms where the user needs to manually specify what data is produced.
    """
    def __init__(self, step, on_change: Optional[Callable] = None):
        self.step = step
        self.on_change = on_change
        self.variables: List[OutputField] = self._load_variables()

    def _load_variables(self) -> List[OutputField]:
        """Loads variables from step configuration or existing contract."""
        # TODO: Load from step.output_contract if available
        # For now, we'll store them in step.config['output_variables'] as a simple list of dicts
        # and eventually they should be serialized to the formal output_contract
        stored_vars = self.step.config.get('output_variables', [])
        return [OutputField(**v) if isinstance(v, dict) else v for v in stored_vars]

    def _save_variables(self):
        """Saves variables back to step config."""
        # Serialize to dicts for JSON storage
        self.step.config['output_variables'] = [v.model_dump() for v in self.variables]
        # Also update the formal output_contract string if needed (future)
        if self.on_change:
            self.on_change()

    def render(self):
        with ui.column().classes('w-full gap-4'):
            # Header
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('Variables de Salida').classes('text-sm font-bold text-gray-700 uppercase')
                ui.button(icon='add', on_click=self.add_variable).props('flat round dense color=primary').tooltip('Añadir variable')

            if not self.variables:
                with ui.column().classes('w-full items-center justify-center p-8 bg-gray-50 border border-dashed rounded'):
                    ui.icon('output', size='md', color='grey')
                    ui.label('No hay variables definidas').classes('text-sm text-gray-500 italic mt-2')
                    ui.button('Añadir Variable', on_click=self.add_variable).props('flat dense color=primary')
            else:
                layout = ui.column().classes('w-full gap-2')
                self._render_list(layout)

    def _render_list(self, container):
        with container:
            for idx, var in enumerate(self.variables):
                with ui.card().classes('w-full p-2 bg-white border shadow-sm'):
                    with ui.row().classes('w-full items-start gap-2'):
                        # Icon based on type
                        icon = 'text_fields'
                        if var.type == InputType.INT or var.type == InputType.FLOAT: icon = 'tag'
                        elif var.type == InputType.BOOL: icon = 'toggle_on'
                        elif var.type == InputType.FILE or var.type == InputType.FILES: icon = 'description'
                        elif '[]' in str(var.type): icon = 'data_array'
                        
                        ui.icon(icon, color='gray').classes('mt-2')

                        with ui.column().classes('flex-1 gap-1'):
                            # Name Input
                            ui.input(
                                value=var.name, 
                                placeholder='Nombre de variable',
                                on_change=lambda e, v=var: self._update_var_name(v, e.value)
                            ).props('dense borderless').classes('text-sm font-bold w-full p-0')
                            
                            # Description Input
                            ui.input(
                                value=var.description,
                                placeholder='Descripción (opcional)', 
                                on_change=lambda e, v=var: self._update_var_desc(v, e.value)
                            ).props('dense borderless text-xs').classes('w-full text-gray-500 p-0')

                        # Type Selector
                        ui.select(
                            options=[t.value for t in InputType],
                            value=var.type,
                            on_change=lambda e, v=var: self._update_var_type(v, e.value)
                        ).props('dense options-dense borderless').classes('w-32 text-xs')

                        # Delete Button
                        ui.button(
                            icon='delete', 
                            on_click=lambda i=idx: self.remove_variable(i, container)
                        ).props('flat round dense size=sm color=gray').classes('opacity-50 hover:opacity-100')

    def add_variable(self):
        new_var = OutputField(name=f"var_{len(self.variables)+1}", label=f"Variable {len(self.variables)+1}", type=InputType.STR, description="")
        self.variables.append(new_var)
        self._save_variables()
        self.render.refresh()

    def remove_variable(self, index, container):
        if 0 <= index < len(self.variables):
            self.variables.pop(index)
            self._save_variables()
            self.render.refresh()

    def _update_var_name(self, var, value):
        var.name = value
        self._save_variables()

    def _update_var_desc(self, var, value):
        var.description = value
        self._save_variables()

    def _update_var_type(self, var, value):
        var.type = value
        self._save_variables()
