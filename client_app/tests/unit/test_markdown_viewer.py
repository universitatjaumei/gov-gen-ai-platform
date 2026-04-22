"""
Tests para el componente MarkdownViewer.
TDD: Prompt 13 - Visor de Documentación Adaptativo

Requisitos:
- Renderizado de Markdown con syntax highlighting
- Scroll independiente sin deformar contenedor
- Modo Drawer (estrecho) vs Modo Full (ancho)
- Carga desde archivo o contenido directo
- Botón "Ver Código Fuente" en modo lectura
- Botón "Generar Documentación" si archivo no existe
- Sin uso de ui.dialog
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from client_app.app.ui.components.markdown_viewer import MarkdownViewer


class TestMarkdownViewerBasic:
    """Tests básicos de renderizado."""

    def test_viewer_accepts_content_string(self):
        """Debe aceptar contenido Markdown como string."""
        content = "# Título\n\nContenido de prueba"
        viewer = MarkdownViewer(content=content)

        assert viewer.content == content
        assert viewer.mode == 'full'  # Default mode

    def test_viewer_accepts_file_path(self):
        """Debe aceptar ruta a archivo .md."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("# Desde Archivo\n\nContenido")
            temp_path = Path(f.name)

        try:
            viewer = MarkdownViewer(file_path=temp_path)
            assert viewer.content == "# Desde Archivo\n\nContenido"
        finally:
            temp_path.unlink()

    def test_viewer_handles_missing_file(self):
        """Si el archivo no existe, debe mostrar estado vacío."""
        viewer = MarkdownViewer(file_path=Path("/nonexistent/file.md"))

        assert viewer.content is None
        assert viewer.file_missing is True

    def test_viewer_prioritizes_content_over_file(self):
        """Si se pasa content y file_path, prioriza content."""
        viewer = MarkdownViewer(
            content="# Directo",
            file_path=Path("/some/file.md")
        )

        assert viewer.content == "# Directo"


class TestMarkdownViewerModes:
    """Tests para modos de visualización."""

    def test_drawer_mode_sets_narrow_width(self):
        """Modo drawer debe configurar ancho estrecho."""
        viewer = MarkdownViewer(content="# Test", mode='drawer')

        assert viewer.mode == 'drawer'
        assert 'max-w-md' in viewer.container_classes or viewer.max_width == 400

    def test_full_mode_sets_wide_width(self):
        """Modo full debe configurar ancho amplio."""
        viewer = MarkdownViewer(content="# Test", mode='full')

        assert viewer.mode == 'full'
        assert 'max-w-4xl' in viewer.container_classes or viewer.max_width is None

    def test_drawer_mode_smaller_font(self):
        """Modo drawer debe usar fuente más pequeña."""
        viewer = MarkdownViewer(content="# Test", mode='drawer')

        # Debe incluir clase de texto pequeño
        assert 'text-sm' in viewer.content_classes or viewer.font_size == 'small'


class TestMarkdownViewerScrolling:
    """Tests para comportamiento de scroll."""

    def test_has_scroll_container(self):
        """Debe tener contenedor con scroll independiente."""
        viewer = MarkdownViewer(content="# Test\n" * 100)

        assert viewer.has_scroll_container is True

    def test_code_blocks_have_horizontal_scroll(self):
        """Bloques de código deben tener scroll horizontal propio."""
        content = """
# Código

```python
very_long_variable_name_that_exceeds_normal_width = "some extremely long string value that goes beyond the container"
```
"""
        viewer = MarkdownViewer(content=content)

        # Debe tener estilos para scroll horizontal en código
        assert 'overflow-x-auto' in viewer.code_block_classes


class TestMarkdownViewerActions:
    """Tests para botones de acción."""

    def test_show_source_button_when_script_provided(self):
        """Debe mostrar botón "Ver Código" si se proporciona script_id."""
        viewer = MarkdownViewer(
            content="# Doc",
            script_id=123,
            show_source_button=True
        )

        assert viewer.show_source_button is True
        assert viewer.script_id == 123

    def test_generate_doc_button_when_file_missing(self):
        """Debe mostrar botón "Generar Documentación" si archivo no existe."""
        viewer = MarkdownViewer(
            file_path=Path("/nonexistent/file.md"),
            script_id=456,
            allow_generation=True
        )

        assert viewer.file_missing is True
        assert viewer.show_generate_button is True

    def test_no_generate_button_without_script_id(self):
        """No debe mostrar botón generar si no hay script_id."""
        viewer = MarkdownViewer(
            file_path=Path("/nonexistent/file.md"),
            allow_generation=True
            # No script_id
        )

        assert viewer.show_generate_button is False


class TestMarkdownViewerIntegration:
    """Tests de integración con otros servicios."""

    def test_on_generate_calls_doc_generator(self):
        """Callback on_generate debe estar disponible."""
        callback_called = False

        def on_generate():
            nonlocal callback_called
            callback_called = True

        viewer = MarkdownViewer(
            file_path=Path("/nonexistent/file.md"),
            script_id=789,
            allow_generation=True,
            on_generate=on_generate
        )

        # Simular click en generar
        if viewer.on_generate:
            viewer.on_generate()

        assert callback_called is True

    def test_on_view_source_callback(self):
        """Callback on_view_source debe estar disponible."""
        source_viewed = None

        def on_view_source(script_id):
            nonlocal source_viewed
            source_viewed = script_id

        viewer = MarkdownViewer(
            content="# Doc",
            script_id=101,
            show_source_button=True,
            on_view_source=on_view_source
        )

        # Simular click en ver código
        if viewer.on_view_source:
            viewer.on_view_source(viewer.script_id)

        assert source_viewed == 101


class TestMarkdownViewerNoDialog:
    """Tests para verificar que no se usan diálogos."""

    def test_no_dialog_usage(self):
        """El componente no debe usar ui.dialog."""
        # Este test verifica que el código fuente no contiene ui.dialog
        import inspect
        source = inspect.getsource(MarkdownViewer)

        assert 'ui.dialog' not in source, "MarkdownViewer no debe usar ui.dialog"


class TestMarkdownViewerEmptyState:
    """Tests para estados vacíos."""

    def test_empty_content_shows_placeholder(self):
        """Contenido vacío debe mostrar placeholder."""
        viewer = MarkdownViewer(content="")

        assert viewer.is_empty is True

    def test_none_content_shows_placeholder(self):
        """Contenido None debe mostrar placeholder."""
        viewer = MarkdownViewer(content=None)

        assert viewer.is_empty is True

    def test_whitespace_only_shows_placeholder(self):
        """Solo espacios debe mostrar placeholder."""
        viewer = MarkdownViewer(content="   \n\t  ")

        assert viewer.is_empty is True


class TestMarkdownViewerRefresh:
    """Tests para actualización de contenido."""

    def test_can_update_content(self):
        """Debe poder actualizar contenido dinámicamente."""
        viewer = MarkdownViewer(content="# Original")

        viewer.update_content("# Actualizado")

        assert viewer.content == "# Actualizado"

    def test_can_reload_from_file(self):
        """Debe poder recargar desde archivo."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("# Version 1")
            temp_path = Path(f.name)

        try:
            viewer = MarkdownViewer(file_path=temp_path)
            assert "Version 1" in viewer.content

            # Modificar archivo
            temp_path.write_text("# Version 2", encoding='utf-8')

            # Recargar
            viewer.reload()

            assert "Version 2" in viewer.content
        finally:
            temp_path.unlink()
