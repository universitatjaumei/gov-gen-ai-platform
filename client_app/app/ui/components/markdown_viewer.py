"""
MarkdownViewer - Visor de Documentación Adaptativo
Prompt 13 Implementation

Features:
- Renderizado de Markdown con syntax highlighting (Python, JSON)
- Contenedor con scroll independiente
- Modo Drawer (panel lateral ~400px) vs Modo Full (página completa)
- Carga desde archivo o contenido directo
- Botón "Ver Código Fuente" en modo lectura
- Botón "Generar Documentación" si archivo no existe
- NO usa ui.dialog (integrado en layout)
"""

from typing import Optional, Callable, Literal
from pathlib import Path
from nicegui import ui


class MarkdownViewer:
    """
    Componente reutilizable para visualizar documentación Markdown.

    Soporta dos modos de visualización:
    - 'drawer': Panel lateral estrecho (~400px), fuente pequeña
    - 'full': Página completa con ancho máximo legible

    Args:
        content: Contenido Markdown como string
        file_path: Ruta al archivo .md (alternativa a content)
        mode: 'drawer' o 'full'
        script_id: ID del script asociado (para acciones)
        show_source_button: Mostrar botón "Ver Código Fuente"
        allow_generation: Permitir generar documentación si no existe
        on_generate: Callback al pulsar "Generar Documentación"
        on_view_source: Callback al pulsar "Ver Código Fuente"
    """

    def __init__(
        self,
        content: Optional[str] = None,
        file_path: Optional[Path] = None,
        mode: Literal['drawer', 'full'] = 'full',
        script_id: Optional[int] = None,
        show_source_button: bool = False,
        allow_generation: bool = False,
        on_generate: Optional[Callable[[], None]] = None,
        on_view_source: Optional[Callable[[int], None]] = None
    ):
        self.mode = mode
        self.script_id = script_id
        self.show_source_button = show_source_button and script_id is not None
        self.allow_generation = allow_generation
        self.on_generate = on_generate
        self.on_view_source = on_view_source
        self.file_path = Path(file_path) if file_path else None
        self.file_missing = False

        # Priorizar content sobre file_path
        if content is not None:
            self._content = content
        elif self.file_path:
            self._content = self._load_from_file()
        else:
            self._content = None

        # Container reference for refresh
        self._container = None

        # Computed properties
        self._setup_styles()

    def _load_from_file(self) -> Optional[str]:
        """Load content from file path."""
        if self.file_path and self.file_path.exists():
            try:
                return self.file_path.read_text(encoding='utf-8')
            except Exception:
                self.file_missing = True
                return None
        else:
            self.file_missing = True
            return None

    def _setup_styles(self):
        """Setup CSS classes based on mode."""
        if self.mode == 'drawer':
            self.container_classes = 'w-full h-full max-w-md'
            self.content_classes = 'prose prose-sm max-w-none text-sm'
            self.max_width = 400
            self.font_size = 'small'
        else:
            self.container_classes = 'w-full max-w-5xl mx-auto'
            self.content_classes = 'prose max-w-none text-base'
            self.max_width = None
            self.font_size = 'normal'
            # No redundant outer border here in full mode; handled by host page if desired
            self.container_styles = '' 

        # Code block styles (horizontal scroll)
        self.code_block_classes = 'overflow-x-auto'
        self.has_scroll_container = True

    @property
    def content(self) -> Optional[str]:
        """Get current content."""
        return self._content

    @property
    def is_empty(self) -> bool:
        """Check if content is empty."""
        return not self._content or not self._content.strip()

    @property
    def show_generate_button(self) -> bool:
        """Should show generate documentation button."""
        return (
            self.file_missing and
            self.allow_generation and
            self.script_id is not None
        )

    def update_content(self, new_content: str):
        """Update content and refresh display."""
        self._content = new_content
        self.file_missing = False
        if self._container:
            self._container.refresh()

    def reload(self):
        """Reload content from file."""
        if self.file_path:
            self._content = self._load_from_file()
            if self._container:
                self._container.refresh()

    def render(self) -> ui.element:
        """
        Render the MarkdownViewer component.

        Returns:
            The container element for further customization
        """
        @ui.refreshable
        def viewer_content():
            if self.is_empty:
                self._render_empty_state()
            else:
                self._render_content()

        self._container = viewer_content
        
        # Use computed styles as the base for the main container in full mode
        container_style = getattr(self, 'container_styles', '') if self.mode == 'full' else ''

        with ui.column().classes(self.container_classes).style(container_style) as container:
            # Action bar (if needed)
            if self.show_source_button or self.show_generate_button:
                self._render_action_bar()

            # Content area
            viewer_content()

        return container

    def _render_empty_state(self):
        """Render empty/missing state."""
        with ui.column().classes('w-full items-center justify-center p-8 gap-4'):
            ui.icon('description', size='3rem').classes('text-gray-300')

            if self.file_missing:
                ui.label('Documentación no disponible').classes('text-gray-500 font-medium')

                if self.show_generate_button:
                    ui.label(
                        'Puedes generar la documentación automáticamente'
                    ).classes('text-gray-400 text-sm text-center')

                    ui.button(
                        'Generar Documentación',
                        icon='auto_fix_high',
                        on_click=self._handle_generate
                    ).classes('mt-2').props('color=primary')
            else:
                ui.label('Sin contenido').classes('text-gray-500')

    def _render_content(self):
        """Render markdown content."""
        # Add custom CSS for code blocks
        ui.add_css('''
            .markdown-viewer pre {
                overflow-x: auto;
                max-width: 100%;
            }
            .markdown-viewer code {
                white-space: pre;
            }
            .markdown-viewer img {
                max-width: 100%;
                height: auto;
            }
        ''')

        # Minimal inner container for text padding
        with ui.column().classes('w-full p-6 md:p-10 markdown-viewer'):
            # Render markdown with syntax highlighting
            ui.markdown(
                self._content,
                extras=['fenced-code-blocks', 'tables', 'strike']
            ).classes(self.content_classes)

    def _render_action_bar(self):
        """Render action buttons bar."""
        with ui.row().classes('w-full justify-end gap-2 p-2 border-b border-gray-200'):
            if self.show_source_button:
                ui.button(
                    'Ver Código',
                    icon='code',
                    on_click=self._handle_view_source
                ).props('flat dense color=primary size=sm')

            if self.show_generate_button and not self.is_empty:
                ui.button(
                    'Regenerar',
                    icon='refresh',
                    on_click=self._handle_generate
                ).props('flat dense color=secondary size=sm')

    def _handle_generate(self):
        """Handle generate documentation click."""
        if self.on_generate:
            self.on_generate()

    def _handle_view_source(self):
        """Handle view source code click."""
        if self.on_view_source and self.script_id:
            self.on_view_source(self.script_id)


# Backward compatibility: keep the simple function
def markdown_viewer(content: str, mode: str = 'full'):
    """
    Simple function for rendering markdown content.
    For more features, use MarkdownViewer class.

    Args:
        content: Markdown content string
        mode: 'drawer' or 'full'
    """
    if not content:
        ui.label("No documentation available.").classes("text-gray-500 italic")
        return

    viewer = MarkdownViewer(content=content, mode=mode)
    return viewer.render()


# Factory function for common use cases
def create_doc_viewer(
    script_id: int,
    docs_base_path: Path,
    mode: str = 'full',
    on_generate: Optional[Callable[[], None]] = None,
    on_view_source: Optional[Callable[[int], None]] = None
) -> MarkdownViewer:
    """
    Factory function to create a documentation viewer for a script.

    Args:
        script_id: Script ID
        docs_base_path: Base path for documentation files
        mode: 'drawer' or 'full'
        on_generate: Callback for generation
        on_view_source: Callback for viewing source

    Returns:
        Configured MarkdownViewer instance
    """
    doc_path = docs_base_path / f"{script_id}.md"

    return MarkdownViewer(
        file_path=doc_path,
        mode=mode,
        script_id=script_id,
        show_source_button=True,
        allow_generation=True,
        on_generate=on_generate,
        on_view_source=on_view_source
    )
