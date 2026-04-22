"""
ContractViewer - Visualizador de Contratos de Datos

Muestra contratos JSON Schema como tablas legibles con secciones
colapsables para inputs y outputs.

Features:
- Parsea JSON Schema y muestra campos como tabla
- Secciones separadas para Input y Output
- Indicadores de requerido/opcional
- Descripción de cada campo
"""

from typing import Optional, Dict, Any, List
from nicegui import ui
import json


class ContractViewer:
    """
    Componente para visualizar contratos de datos (JSON Schema) como tablas.

    Args:
        input_contract: JSON string o dict del contrato de entrada
        output_contract: JSON string o dict del contrato de salida
        atom_name: Nombre del átomo (para el header)
    """

    def __init__(
        self,
        input_contract: Optional[str | Dict] = None,
        output_contract: Optional[str | Dict] = None,
        atom_name: str = "Acción"
    ):
        self.atom_name = atom_name
        self.input_schema = self._parse_contract(input_contract)
        self.output_schema = self._parse_contract(output_contract)

    def _parse_contract(self, contract: Optional[str | Dict]) -> Optional[Dict]:
        """Parsea el contrato a dict si es string JSON."""
        if contract is None:
            return None
        if isinstance(contract, str):
            try:
                return json.loads(contract)
            except json.JSONDecodeError:
                return None
        return contract

    def _extract_fields(self, schema: Dict) -> List[Dict[str, Any]]:
        """Extrae campos de un JSON Schema para mostrar en tabla."""
        fields = []

        if not schema:
            return fields

        properties = schema.get('properties', {})
        required = schema.get('required', [])

        for name, prop in properties.items():
            field = {
                'name': name,
                'type': self._get_type_label(prop),
                'required': name in required,
                'description': prop.get('description', '-'),
                'default': prop.get('default'),
                'enum': prop.get('enum'),
            }
            fields.append(field)

        return fields

    def _get_type_label(self, prop: Dict) -> str:
        """Obtiene etiqueta legible del tipo."""
        prop_type = prop.get('type', 'any')

        if prop_type == 'array':
            items = prop.get('items', {})
            items_type = items.get('type', 'any')
            return f"array[{items_type}]"
        elif prop_type == 'object':
            return 'object'
        elif isinstance(prop_type, list):
            return ' | '.join(prop_type)

        # Agregar formato si existe
        fmt = prop.get('format')
        if fmt:
            return f"{prop_type} ({fmt})"

        return prop_type

    def render(self) -> ui.element:
        """Renderiza el visor de contratos."""
        with ui.column().classes('w-full h-full gap-4') as container:
            # Header
            with ui.row().classes('w-full items-center gap-2 mb-2'):
                ui.icon('article', color='primary')
                ui.label(f'Contrato de Datos').classes('font-bold text-slate-700')

            # Verificar si hay contratos
            if not self.input_schema and not self.output_schema:
                self._render_empty_state()
            else:
                with ui.scroll_area().classes('w-full flex-grow'):
                    with ui.column().classes('w-full gap-4 p-2'):
                        # Sección Input
                        if self.input_schema:
                            self._render_contract_section(
                                title="Entradas (Input)",
                                icon="input",
                                color="blue",
                                schema=self.input_schema
                            )

                        # Sección Output
                        if self.output_schema:
                            self._render_contract_section(
                                title="Salidas (Output)",
                                icon="output",
                                color="green",
                                schema=self.output_schema
                            )

        return container

    def _render_empty_state(self):
        """Muestra estado vacío cuando no hay contratos."""
        with ui.column().classes('w-full items-center justify-center p-8 text-gray-400'):
            ui.icon('info', size='lg').classes('mb-2')
            ui.label('Esta acción no tiene contrato de datos definido').classes('text-sm italic text-center')

    def _render_contract_section(
        self,
        title: str,
        icon: str,
        color: str,
        schema: Dict
    ):
        """Renderiza una sección del contrato (input u output)."""
        fields = self._extract_fields(schema)

        with ui.expansion(
            text=title,
            icon=icon,
            value=True  # Expandido por defecto
        ).classes(f'w-full border-l-4 border-{color}-500 bg-{color}-50/30'):

            if not fields:
                ui.label('Sin campos definidos').classes('text-gray-400 italic text-sm p-2')
                return

            # Tabla de campos
            with ui.column().classes('w-full gap-0'):
                # Header de tabla
                with ui.row().classes('w-full bg-slate-100 p-2 gap-2 text-xs font-bold text-slate-600 uppercase'):
                    ui.label('Campo').classes('w-1/4')
                    ui.label('Tipo').classes('w-1/4')
                    ui.label('Req.').classes('w-12 text-center')
                    ui.label('Descripción').classes('flex-grow')

                # Filas de datos
                for i, field in enumerate(fields):
                    bg_class = 'bg-white' if i % 2 == 0 else 'bg-slate-50'

                    with ui.row().classes(f'w-full {bg_class} p-2 gap-2 text-sm items-start border-b border-slate-100'):
                        # Nombre del campo
                        ui.label(field['name']).classes('w-1/4 font-mono text-slate-800 font-medium')

                        # Tipo
                        type_label = field['type']
                        ui.label(type_label).classes('w-1/4 font-mono text-xs text-purple-600 bg-purple-50 px-1 py-0.5 rounded')

                        # Requerido
                        if field['required']:
                            ui.icon('check_circle', size='xs', color='positive').classes('w-12 text-center')
                        else:
                            ui.icon('remove_circle_outline', size='xs', color='grey').classes('w-12 text-center')

                        # Descripción (con enum si existe)
                        with ui.column().classes('flex-grow gap-0'):
                            ui.label(field['description']).classes('text-slate-600 text-xs')

                            # Mostrar valores permitidos si es enum
                            if field['enum']:
                                enum_str = ', '.join([f'"{v}"' for v in field['enum'][:5]])
                                if len(field['enum']) > 5:
                                    enum_str += f' (+{len(field["enum"]) - 5} más)'
                                ui.label(f'Valores: {enum_str}').classes('text-xs text-blue-500 mt-1')

                            # Mostrar default si existe
                            if field['default'] is not None:
                                default_str = json.dumps(field['default']) if not isinstance(field['default'], str) else field['default']
                                ui.label(f'Default: {default_str}').classes('text-xs text-gray-400 mt-0.5')


def contract_viewer(**kwargs) -> ui.element:
    """Factory function para ContractViewer."""
    viewer = ContractViewer(**kwargs)
    return viewer.render()
