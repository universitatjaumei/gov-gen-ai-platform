"""
Editor de Markdown con toolbar y preview en tiempo real.
Diseñado para editar bloques de texto en el diseñador de informes.
"""
from nicegui import ui
from typing import Callable, Optional


class MarkdownEditor:
    """
    Editor Markdown con:
    - Toolbar de formato (títulos, negrita, cursiva, listas)
    - Área de edición de texto
    - Preview en tiempo real del Markdown renderizado
    - Soporte para variables {{variable}}
    """

    def __init__(
        self,
        initial_content: str = '',
        on_change: Optional[Callable[[str], None]] = None,
        placeholder: str = 'Escribe aquí usando Markdown...',
        show_preview: bool = True,
        height: str = 'h-64'
    ):
        """
        Inicializar editor.

        Args:
            initial_content: Contenido inicial del editor
            on_change: Callback cuando el contenido cambia
            placeholder: Texto placeholder del textarea
            show_preview: Mostrar panel de preview
            height: Altura del textarea (clase CSS)
        """
        self.content = initial_content
        self.on_change = on_change
        self.placeholder = placeholder
        self.show_preview = show_preview
        self.height = height
        self._textarea = None
        self._preview = None

    def render(self) -> ui.element:
        """Renderizar el editor completo."""
        with ui.column().classes('w-full gap-2') as container:
            # Toolbar
            self._render_toolbar()

            # Editor y Preview
            if self.show_preview:
                with ui.splitter(value=50).classes('w-full') as splitter:
                    with splitter.before:
                        self._render_editor()
                    with splitter.after:
                        self._render_preview()
            else:
                self._render_editor()

        return container

    def _render_toolbar(self):
        """Renderizar barra de herramientas."""
        with ui.row().classes('w-full gap-1 p-2 bg-slate-100 rounded-t-lg border border-slate-200'):
            # Títulos
            with ui.button_group().props('flat dense'):
                ui.button(
                    'H1',
                    on_click=lambda: self._insert_prefix('# ')
                ).props('flat dense size=sm').classes('text-xs font-bold')
                ui.button(
                    'H2',
                    on_click=lambda: self._insert_prefix('## ')
                ).props('flat dense size=sm').classes('text-xs font-bold')
                ui.button(
                    'H3',
                    on_click=lambda: self._insert_prefix('### ')
                ).props('flat dense size=sm').classes('text-xs font-bold')

            ui.separator().props('vertical')

            # Formato de texto
            with ui.button_group().props('flat dense'):
                ui.button(
                    icon='format_bold',
                    on_click=lambda: self._wrap_selection('**')
                ).props('flat dense size=sm').tooltip('Negrita')
                ui.button(
                    icon='format_italic',
                    on_click=lambda: self._wrap_selection('*')
                ).props('flat dense size=sm').tooltip('Cursiva')
                ui.button(
                    icon='strikethrough_s',
                    on_click=lambda: self._wrap_selection('~~')
                ).props('flat dense size=sm').tooltip('Tachado')

            ui.separator().props('vertical')

            # Listas
            with ui.button_group().props('flat dense'):
                ui.button(
                    icon='format_list_bulleted',
                    on_click=lambda: self._insert_prefix('- ')
                ).props('flat dense size=sm').tooltip('Lista con viñetas')
                ui.button(
                    icon='format_list_numbered',
                    on_click=lambda: self._insert_prefix('1. ')
                ).props('flat dense size=sm').tooltip('Lista numerada')

            ui.separator().props('vertical')

            # Otros elementos
            with ui.button_group().props('flat dense'):
                ui.button(
                    icon='link',
                    on_click=lambda: self._insert_link()
                ).props('flat dense size=sm').tooltip('Enlace')
                ui.button(
                    icon='horizontal_rule',
                    on_click=lambda: self._insert_text('\n---\n')
                ).props('flat dense size=sm').tooltip('Separador')
                ui.button(
                    icon='code',
                    on_click=lambda: self._wrap_selection('`')
                ).props('flat dense size=sm').tooltip('Código')

            ui.separator().props('vertical')

            # Variables
            ui.button(
                icon='data_object',
                on_click=lambda: self._insert_variable()
            ).props('flat dense size=sm').tooltip('Insertar variable {{...}}')

            # Spacer
            ui.space()

            # Ayuda
            ui.button(
                icon='help_outline',
                on_click=lambda: self._show_help()
            ).props('flat dense size=sm').tooltip('Ayuda de Markdown')

    def _render_editor(self):
        """Renderizar área de edición."""
        with ui.column().classes('w-full'):
            ui.label('Editor').classes('text-xs text-slate-500 font-medium')
            self._textarea = ui.textarea(
                value=self.content,
                placeholder=self.placeholder
            ).classes(f'w-full {self.height} font-mono text-sm')
            self._textarea.on('input', self._on_input)

    def _render_preview(self):
        """Renderizar panel de preview."""
        with ui.column().classes('w-full'):
            ui.label('Vista previa').classes('text-xs text-slate-500 font-medium')
            with ui.card().classes(f'w-full {self.height} overflow-auto bg-white'):
                self._preview = ui.markdown(self.content or '*Vista previa vacía*')

    def _on_input(self, e):
        """Manejar cambio de texto."""
        self.content = e.value
        if self._preview:
            self._preview.set_content(self.content or '*Vista previa vacía*')
        if self.on_change:
            self.on_change(self.content)

    def _insert_prefix(self, prefix: str):
        """Insertar prefijo al inicio de la línea actual."""
        if self._textarea:
            # Añadir prefijo al contenido actual
            current = self.content or ''
            # Si hay contenido, añadir en nueva línea
            if current and not current.endswith('\n'):
                new_content = current + '\n' + prefix
            else:
                new_content = current + prefix
            self._update_content(new_content)

    def _wrap_selection(self, wrapper: str):
        """Envolver texto seleccionado con wrapper."""
        if self._textarea:
            current = self.content or ''
            # Por simplicidad, añadimos al final
            # En una implementación más avanzada se capturaría la selección
            new_content = current + wrapper + 'texto' + wrapper
            self._update_content(new_content)

    def _insert_text(self, text: str):
        """Insertar texto en la posición actual."""
        if self._textarea:
            current = self.content or ''
            new_content = current + text
            self._update_content(new_content)

    def _insert_link(self):
        """Insertar un enlace."""
        self._insert_text('[texto del enlace](https://url)')

    def _insert_variable(self):
        """Insertar una variable."""
        async def do_insert():
            with ui.dialog() as dialog, ui.card().classes('p-4'):
                ui.label('Insertar variable').classes('text-lg font-bold mb-2')
                ui.label('Escribe el nombre de la variable (sin llaves):').classes('text-sm text-slate-500')
                var_input = ui.input(placeholder='nombre_variable').classes('w-full')
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancelar', on_click=dialog.close).props('flat')

                    async def insert():
                        if var_input.value:
                            self._insert_text('{{' + var_input.value + '}}')
                        dialog.close()

                    ui.button('Insertar', on_click=insert).props('color=primary')
            dialog.open()

        ui.timer(0, do_insert, once=True)

    def _show_help(self):
        """Mostrar ayuda de Markdown."""
        with ui.dialog() as dialog, ui.card().classes('p-6 max-w-lg'):
            ui.label('Guía rápida de Markdown').classes('text-xl font-bold mb-4')

            help_content = """
| Sintaxis | Resultado |
|----------|-----------|
| `# Título` | Título principal |
| `## Subtítulo` | Subtítulo |
| `**negrita**` | **negrita** |
| `*cursiva*` | *cursiva* |
| `- elemento` | Lista con viñetas |
| `1. elemento` | Lista numerada |
| `[texto](url)` | Enlace |
| `---` | Línea separadora |
| `` `código` `` | Código inline |
| `{{variable}}` | Variable del informe |
"""
            ui.markdown(help_content)

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Cerrar', on_click=dialog.close).props('flat')

        dialog.open()

    def _update_content(self, new_content: str):
        """Actualizar contenido del editor."""
        self.content = new_content
        if self._textarea:
            self._textarea.value = new_content
        if self._preview:
            self._preview.set_content(new_content or '*Vista previa vacía*')
        if self.on_change:
            self.on_change(new_content)

    def get_content(self) -> str:
        """Obtener contenido actual."""
        return self.content

    def set_content(self, content: str):
        """Establecer contenido."""
        self._update_content(content)


def markdown_editor(
    initial_content: str = '',
    on_change: Optional[Callable[[str], None]] = None,
    placeholder: str = 'Escribe aquí usando Markdown...',
    show_preview: bool = True,
    height: str = 'h-64'
) -> MarkdownEditor:
    """
    Función helper para crear y renderizar un editor Markdown.

    Args:
        initial_content: Contenido inicial
        on_change: Callback cuando el contenido cambia
        placeholder: Texto placeholder
        show_preview: Mostrar panel de preview
        height: Altura del textarea

    Returns:
        Instancia de MarkdownEditor ya renderizada
    """
    editor = MarkdownEditor(
        initial_content=initial_content,
        on_change=on_change,
        placeholder=placeholder,
        show_preview=show_preview,
        height=height
    )
    editor.render()
    return editor
