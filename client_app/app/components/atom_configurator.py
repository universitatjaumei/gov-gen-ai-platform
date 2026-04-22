from nicegui import ui
from typing import Dict, Any, Optional, Callable
from client_app.app.core.state import state as app_state

def coerce_value(value: Any, target_type: str) -> Any:
    """Helper to convert UI inputs to Schema types."""
    if target_type == 'integer':
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    elif target_type == 'boolean':
        if isinstance(value, bool): return value
        return str(value).lower() in ('true', '1', 'yes', 'on')
    elif target_type == 'number':
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    return value

class AtomConfigurator(ui.column):
    def __init__(self, atom_schema: Dict[str, Any], current_values: Dict[str, Any], on_change: Optional[Callable] = None):
        super().__init__()
        self.schema = atom_schema
        self.values = current_values.copy()
        self.on_change = on_change
        self.classes('w-full gap-4')

        with self:
            self.render_form()
            
            # Footer Actions
            with ui.row().classes('w-full justify-between mt-4 border-t pt-4'):
                 ui.button('Volver', icon='arrow_back', on_click=self.handle_back).props('flat dense color=grey')
                 ui.button('Eliminar Paso', icon='delete', on_click=self.handle_delete).props('flat dense color=red')

    def render_form(self):
        """Generates UI elements based on schema."""
        if not self.schema:
            ui.label('No hay parámetros configurables.').classes('text-gray-500 italic')
            return

        for field_name, field_def in self.schema.items():
            field_type = field_def.get('type', 'string')
            label = field_name.replace('_', ' ').capitalize()
            default_val = field_def.get('default')
            current_val = self.values.get(field_name, default_val)
            
            with ui.column().classes('w-full gap-1'):
                ui.label(label).classes('text-xs font-bold text-gray-500 uppercase')
                
                if field_type == 'string':
                    ui.input().bind_value(self.values, field_name).classes('w-full')
                
                elif field_type == 'integer':
                    ui.number().bind_value(self.values, field_name).classes('w-full')
                
                elif field_type == 'boolean':
                    ui.switch(text='').bind_value(self.values, field_name).props('dense')
                
                elif field_type == 'list' or 'enum' in field_def:
                    opts = field_def.get('enum', [])
                    ui.select(options=opts).bind_value(self.values, field_name).classes('w-full')


    def update_value(self, field: str, value: Any):
        self.values[field] = value
        if self.on_change:
            self.on_change(self.values)

    def handle_back(self):
        app_state.toggle_focus_mode(True, content='explorer')

    def handle_delete(self):
        """Elimina el paso actual del flujo."""
        if not self.app_state or not self.app_state.editing_flow:
            ui.notify("No hay flujo activo", type='warning')
            return

        try:
            # Eliminar nodo del grafo
            self.app_state.editing_flow.network.nodes.pop(self.atom_id, None)
            
            # Limpiar conexiones asociadas
            # Esto debería manejarse en el modelo del grafo, pero para asegurar:
            self.app_state.editing_flow.network.edges = [
                e for e in self.app_state.editing_flow.network.edges 
                if e.source != self.atom_id and e.target != self.atom_id
            ]
            
            ui.notify(f"Paso '{self.atom_id}' eliminado", type='positive')
            
            # Volver al explorador
            self.on_back()
            
        except Exception as e:
            ui.notify(f"Error eliminando paso: {e}", type='negative')
