from typing import List, Dict, Callable, Optional, Any
from nicegui import ui
from nicegui import ui
from automatia_shared.contracts.ui_contract import OutputField, InputType

class SchemaMapper:
    """
    Component to map structured data (from test results) to Output Variables.
    Used for API_FETCH, SQL_QUERY, etc.
    """
    def __init__(self, step, on_change: Optional[Callable] = None):
        self.step = step
        self.on_change = on_change
        self.variables: List[OutputField] = self._load_variables()
        self.last_test_result: Optional[Any] = self._load_last_test_result()
        self.flat_schema: Dict[str, str] = {} # "path.to.field": "type"
        self._flatten_schema(self.last_test_result)
        self.selected_paths: List[str] = [v.name for v in self.variables]

    def _load_variables(self) -> List[OutputField]:
        """Loads variables from step configuration."""
        stored_vars = self.step.config.get('output_variables', [])
        return [OutputField(**v) if isinstance(v, dict) else v for v in stored_vars]

    def _load_last_test_result(self) -> Optional[Any]:
        """
        Tries to load the last test result for this step.
        In a real scenario, this might come from a central store or the step config itself
        if we saved the last execution result there.
        """
        # Placeholder: Check if 'last_test_output' is in config or look up in app state
        return self.step.config.get('last_test_output', None)

    def _save_variables(self):
        """Saves selected variables to step config."""
        new_vars = []
        for path in self.selected_paths:
            var_type = self.flat_schema.get(path, InputType.STR)
            new_vars.append(OutputField(
                name=path, 
                label=path.replace('_', ' ').capitalize(),
                type=var_type, 
                description=f"Mapped from {path}"
            ))
        
        self.step.config['output_variables'] = [v.model_dump() for v in new_vars]
        if self.on_change:
            self.on_change()

    def _flatten_schema(self, data: Any, prefix: str = ""):
        """Flattens a JSON-like structure into dot-notation paths."""
        if not data:
            return

        if isinstance(data, dict):
            for k, v in data.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    self._flatten_schema(v, key)
                else:
                    self.flat_schema[key] = self._infer_type(v)
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                # Assume list of objects, take first one as schema template
                self._flatten_schema(data[0], f"{prefix}[]")
            else:
                self.flat_schema[prefix] = self._infer_type(data)

    def _infer_type(self, value: Any) -> InputType:
        if isinstance(value, bool): return InputType.BOOL
        if isinstance(value, int): return InputType.INT
        if isinstance(value, float): return InputType.FLOAT
        if isinstance(value, list): return InputType.FILES # simplified
        return InputType.STR

    @ui.refreshable
    def render(self):
        with ui.column().classes('w-full gap-4'):
            # Header
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('Mapeo de Datos (Schema Mapper)').classes('text-sm font-bold text-gray-700 uppercase')
                ui.button(icon='refresh', on_click=self.refresh_schema).props('flat round dense color=primary').tooltip('Recargar desde última prueba')

            if not self.last_test_result:
                with ui.column().classes('w-full items-center justify-center p-8 bg-gray-50 border border-dashed rounded'):
                    ui.icon('science', size='md', color='grey')
                    ui.label('No hay resultados de prueba disponibles').classes('text-sm text-gray-500 italic mt-2')
                    ui.label('Ejecuta una prueba del paso para detectar la estructura de datos.').classes('text-xs text-gray-400')
            else:
                self._render_tree()

    def _render_tree(self):
        with ui.column().classes('w-full gap-2'):
            with ui.row().classes('items-center gap-2 mb-2'):
                ui.button('Seleccionar Todo', on_click=self.select_all).props('flat dense size=sm color=primary')
                ui.button('Deseleccionar Todo', on_click=self.deselect_all).props('flat dense size=sm color=grey')

            with ui.scroll_area().classes('w-full h-80 border rounded p-2'):
                for path, vtype in self.flat_schema.items():
                    with ui.row().classes('items-center gap-2 w-full hover:bg-gray-50 p-1'):
                        cb = ui.checkbox(
                            value=path in self.selected_paths,
                            on_change=lambda e, p=path: self.toggle_path(p, e.value)
                        ).props('dense')
                        ui.label(path).classes('font-mono text-sm flex-1')
                        with ui.chip(vtype, icon='code').props('dense size=xs outline color=grey'):
                            pass

            ui.button('Generar Contrato de Datos', icon='save', on_click=self._save_variables).classes('w-full mt-2')

    def toggle_path(self, path, value):
        if value:
            if path not in self.selected_paths: self.selected_paths.append(path)
        else:
            if path in self.selected_paths: self.selected_paths.remove(path)

    def select_all(self):
        self.selected_paths = list(self.flat_schema.keys())
        self.render.refresh()

    def deselect_all(self):
        self.selected_paths = []
        self.render.refresh()

    def refresh_schema(self):
        self.last_test_result = self._load_last_test_result()
        self.flat_schema = {}
        self._flatten_schema(self.last_test_result)
        self.render.refresh()
