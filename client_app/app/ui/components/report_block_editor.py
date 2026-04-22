"""
Editor de bloques para Report Designer.
"""
from nicegui import ui
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from client_app.app.ui.components.markdown_editor import MarkdownEditor


@dataclass
class ChartBlockConfig:
    """Configuración de bloque de gráfico."""
    chart_type: str
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    available_columns: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validar configuración."""
        if self.x_field and self.x_field not in self.available_columns:
            return False
        if self.y_field and self.y_field not in self.available_columns:
            return False
        return True


class ReportBlockEditor:
    """
    Editor visual de bloques para informes.
    Permite añadir, eliminar, reordenar y configurar bloques.
    """

    def __init__(
        self,
        blocks: List[Dict[str, Any]] = None,
        available_columns: List[str] = None,
        on_change: Optional[Callable] = None
    ):
        self.blocks = blocks or []
        self.available_columns = available_columns or []
        self.on_change = on_change
        self._container = None

    def render(self) -> ui.element:
        """Renderizar el editor de bloques."""
        with ui.column().classes('w-full gap-2') as self._container:
            self._render_blocks()
            self._render_add_button()
        return self._container

    def _render_blocks(self):
        """Renderizar lista de bloques."""
        for i, block in enumerate(self.blocks):
            with ui.card().classes('w-full p-3'):
                with ui.row().classes('w-full justify-between items-center'):
                    # Icono y tipo
                    icon = self._get_block_icon(block["type"])
                    ui.icon(icon, size='sm')
                    ui.label(block.get("id", f"Bloque {i+1}")).classes('font-medium')

                    # Acciones
                    with ui.row().classes('gap-1'):
                        if i > 0:
                            ui.button(icon='arrow_upward', on_click=lambda idx=i: self.move_block_up(idx)).props('flat dense')
                        if i < len(self.blocks) - 1:
                            ui.button(icon='arrow_downward', on_click=lambda idx=i: self.move_block_down(idx)).props('flat dense')
                        ui.button(icon='settings', on_click=lambda b=block: self._open_config(b)).props('flat dense')
                        ui.button(icon='delete', on_click=lambda idx=i: self.remove_block(idx)).props('flat dense color=negative')

                # Descripción
                ui.label(self._get_block_description(block)).classes('text-sm text-gray-500')

    def _render_add_button(self):
        """Renderizar botón de añadir bloque."""
        with ui.row().classes('w-full justify-center mt-4'):
            with ui.button_group():
                ui.button('Texto', icon='text_fields', on_click=lambda: self.add_block('text')).props('flat')
                ui.button('Tabla', icon='table_chart', on_click=lambda: self.add_block('table')).props('flat')
                ui.button('Gráfico', icon='bar_chart', on_click=lambda: self.add_block('chart')).props('flat')

    def _get_block_icon(self, block_type: str) -> str:
        """Obtener icono para tipo de bloque."""
        icons = {
            'text': 'text_fields',
            'table': 'table_chart',
            'chart': 'bar_chart',
            'separator': 'horizontal_rule',
            'page_break': 'insert_page_break'
        }
        return icons.get(block_type, 'widgets')

    def _get_block_description(self, block: Dict[str, Any]) -> str:
        """Obtener descripción del bloque."""
        block_type = block.get("type")

        if block_type == "text":
            content = block.get("content", "")
            return content[:50] + "..." if len(content) > 50 else content

        elif block_type == "chart":
            chart_type = block.get("chart_type", "bar")
            x = block.get("x_field", "?")
            y = block.get("y_field", "?")
            return f"Gráfico {chart_type}: {x} vs {y}"

        elif block_type == "table":
            columns = block.get("columns", [])
            return f"Tabla con {len(columns)} columnas"

        return ""

    def add_block(self, block_type: str, config: Dict[str, Any] = None, open_config: bool = True):
        """Añadir nuevo bloque."""
        import uuid

        new_block = {
            "id": f"{block_type}_{uuid.uuid4().hex[:8]}",
            "type": block_type,
            "title": "",  # Título vacío por defecto
            **(config or {})
        }

        # Valores por defecto según tipo
        if block_type == "text":
            new_block.setdefault("content", "")
        elif block_type == "chart":
            new_block.setdefault("chart_type", "bar")
            new_block.setdefault("data_field", "")
            new_block.setdefault("x_field", "")
            new_block.setdefault("y_field", "")
        elif block_type == "table":
            new_block.setdefault("data_field", "")
            new_block.setdefault("columns", [])

        self.blocks.append(new_block)
        self._notify_change()
        self._refresh()

        # Abrir configuración automáticamente
        if open_config:
            self._open_config(new_block)

    def remove_block(self, index: int):
        """Eliminar bloque por índice."""
        if 0 <= index < len(self.blocks):
            self.blocks.pop(index)
            self._notify_change()
            self._refresh()

    def move_block(self, block_id: str, new_index: int):
        """Mover bloque a nueva posición."""
        # Encontrar bloque
        block = None
        old_index = None
        for i, b in enumerate(self.blocks):
            if b["id"] == block_id:
                block = b
                old_index = i
                break

        if block is None:
            return

        # Remover y reinsertar
        self.blocks.pop(old_index)
        self.blocks.insert(new_index, block)
        self._notify_change()

    def move_block_up(self, index: int):
        """Mover bloque una posición arriba."""
        if index > 0:
            self.blocks[index], self.blocks[index-1] = self.blocks[index-1], self.blocks[index]
            self._notify_change()
            self._refresh()

    def move_block_down(self, index: int):
        """Mover bloque una posición abajo."""
        if index < len(self.blocks) - 1:
            self.blocks[index], self.blocks[index+1] = self.blocks[index+1], self.blocks[index]
            self._notify_change()
            self._refresh()

    def _open_config(self, block: Dict[str, Any]):
        """Abrir configuración del bloque."""
        block_type = block.get("type")

        if block_type == "text":
            self._open_text_config(block)
        elif block_type == "chart":
            self._open_chart_config(block)
        elif block_type == "table":
            self._open_table_config(block)
        else:
            ui.notify(f"Configuración para {block_type} no disponible", type='warning')

    def _open_text_config(self, block: Dict[str, Any]):
        """Abrir editor de bloque de texto con Markdown."""
        editor_instance = None

        def save_and_close():
            if editor_instance:
                block['content'] = editor_instance.get_content()
                self._notify_change()
                self._refresh()
            dialog.close()

        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl p-6'):
            # Header
            with ui.row().classes('w-full justify-between items-center mb-4'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('text_fields', size='md', color='primary')
                    ui.label('Editar bloque de texto').classes('text-xl font-bold')
                ui.button(icon='close', on_click=dialog.close).props('flat round')

            # Título del bloque (opcional)
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.label('Título del bloque:').classes('text-sm font-medium w-32')
                ui.input(
                    value=block.get('title', ''),
                    placeholder='Título opcional para esta sección',
                    on_change=lambda e: block.update({'title': e.value})
                ).classes('flex-grow')

            # Editor Markdown
            ui.label('Contenido:').classes('text-sm font-medium mb-2')
            editor_instance = MarkdownEditor(
                initial_content=block.get('content', ''),
                show_preview=True,
                height='h-80'
            )
            editor_instance.render()

            # Ayuda contextual
            with ui.expansion('Ayuda: Variables disponibles', icon='help').classes('w-full mt-4'):
                ui.markdown("""
Puedes usar variables del informe con la sintaxis `{{nombre_variable}}`.

**Ejemplos:**
- `{{titulo}}` - Título del informe
- `{{fecha}}` - Fecha de generación
- `{{resumen}}` - Resumen ejecutivo

Las variables se reemplazarán con los datos reales al generar el informe.
                """)

            # Acciones
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Guardar', on_click=save_and_close).props('color=primary')

        dialog.open()

    def _open_chart_config(self, block: Dict[str, Any]):
        """Abrir configuración de bloque de gráfico."""
        def save_and_close():
            self._notify_change()
            self._refresh()
            dialog.close()

        with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl p-6'):
            # Header
            with ui.row().classes('w-full justify-between items-center mb-4'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('bar_chart', size='md', color='primary')
                    ui.label('Configurar gráfico').classes('text-xl font-bold')
                ui.button(icon='close', on_click=dialog.close).props('flat round')

            # Título del gráfico
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.label('Título:').classes('text-sm font-medium w-32')
                ui.input(
                    value=block.get('title', ''),
                    placeholder='Título del gráfico',
                    on_change=lambda e: block.update({'title': e.value})
                ).classes('flex-grow')

            # Tipo de gráfico
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.label('Tipo:').classes('text-sm font-medium w-32')
                ui.select(
                    options={
                        'bar': 'Barras',
                        'line': 'Líneas',
                        'pie': 'Circular',
                        'scatter': 'Dispersión',
                        'area': 'Área'
                    },
                    value=block.get('chart_type', 'bar'),
                    on_change=lambda e: block.update({'chart_type': e.value})
                ).classes('flex-grow')

            # Campo de datos
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.label('Campo de datos:').classes('text-sm font-medium w-32')
                ui.input(
                    value=block.get('data_field', ''),
                    placeholder='Nombre del campo con los datos',
                    on_change=lambda e: block.update({'data_field': e.value})
                ).classes('flex-grow')

            # Ejes
            with ui.row().classes('w-full gap-4 mb-4'):
                with ui.column().classes('flex-1'):
                    ui.label('Eje X:').classes('text-sm font-medium')
                    ui.input(
                        value=block.get('x_field', ''),
                        placeholder='Campo para eje X',
                        on_change=lambda e: block.update({'x_field': e.value})
                    ).classes('w-full')
                with ui.column().classes('flex-1'):
                    ui.label('Eje Y:').classes('text-sm font-medium')
                    ui.input(
                        value=block.get('y_field', ''),
                        placeholder='Campo para eje Y',
                        on_change=lambda e: block.update({'y_field': e.value})
                    ).classes('w-full')

            # Acciones
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Guardar', on_click=save_and_close).props('color=primary')

        dialog.open()

    def _open_table_config(self, block: Dict[str, Any]):
        """Abrir configuración de bloque de tabla."""
        columns = block.get('columns', [])

        def add_column():
            columns.append({'field': '', 'header': ''})
            refresh_columns()

        def remove_column(idx):
            if idx < len(columns):
                columns.pop(idx)
                refresh_columns()

        def refresh_columns():
            columns_container.clear()
            with columns_container:
                for i, col in enumerate(columns):
                    with ui.row().classes('w-full items-center gap-2 mb-2'):
                        ui.input(
                            value=col.get('field', ''),
                            placeholder='Campo',
                            on_change=lambda e, c=col: c.update({'field': e.value})
                        ).classes('flex-1')
                        ui.input(
                            value=col.get('header', ''),
                            placeholder='Encabezado',
                            on_change=lambda e, c=col: c.update({'header': e.value})
                        ).classes('flex-1')
                        ui.button(
                            icon='delete',
                            on_click=lambda idx=i: remove_column(idx)
                        ).props('flat dense color=negative')

        def save_and_close():
            block['columns'] = columns
            self._notify_change()
            self._refresh()
            dialog.close()

        with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl p-6'):
            # Header
            with ui.row().classes('w-full justify-between items-center mb-4'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('table_chart', size='md', color='primary')
                    ui.label('Configurar tabla').classes('text-xl font-bold')
                ui.button(icon='close', on_click=dialog.close).props('flat round')

            # Título de la tabla
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.label('Título:').classes('text-sm font-medium w-32')
                ui.input(
                    value=block.get('title', ''),
                    placeholder='Título de la tabla',
                    on_change=lambda e: block.update({'title': e.value})
                ).classes('flex-grow')

            # Campo de datos
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.label('Campo de datos:').classes('text-sm font-medium w-32')
                ui.input(
                    value=block.get('data_field', ''),
                    placeholder='Nombre del campo con los datos',
                    on_change=lambda e: block.update({'data_field': e.value})
                ).classes('flex-grow')

            # Columnas
            ui.label('Columnas:').classes('text-sm font-medium mb-2')
            columns_container = ui.column().classes('w-full')
            refresh_columns()

            ui.button('Añadir columna', icon='add', on_click=add_column).props('flat dense')

            # Acciones
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Guardar', on_click=save_and_close).props('color=primary')

        dialog.open()

    def _notify_change(self):
        """Notificar cambios."""
        if self.on_change:
            self.on_change(self.blocks)

    def _refresh(self):
        """Refrescar la vista."""
        if self._container:
            self._container.clear()
            with self._container:
                self._render_blocks()
                self._render_add_button()
