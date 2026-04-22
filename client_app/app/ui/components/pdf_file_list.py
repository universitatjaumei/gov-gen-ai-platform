"""
Componente de lista de PDFs reordenable.
Permite reordenar archivos mediante botones de flechas.
Similar al reordenamiento de pasos en flujos.
"""
from nicegui import ui
from typing import List, Dict, Callable, Optional
from client_app.app.core.state import state


class PDFFileList:
    """
    Lista de archivos PDF con capacidad de reordenamiento.

    Uso:
        files = [{"path": "...", "name": "doc.pdf", "pages": 10, "size_mb": 2.5}, ...]
        pdf_list = PDFFileList(
            files=files,
            on_order_change=lambda f: print("Nuevo orden:", f),
            on_remove=lambda i: print("Eliminado índice:", i)
        )
        pdf_list.render()
    """

    def __init__(
        self,
        files: List[Dict],
        on_order_change: Optional[Callable[[List[Dict]], None]] = None,
        on_remove: Optional[Callable[[int], None]] = None,
        show_reorder: bool = True,
        show_remove: bool = True
    ):
        """
        Args:
            files: Lista de dicts con info de archivos (path, name, pages, size_mb)
            on_order_change: Callback cuando cambia el orden
            on_remove: Callback cuando se elimina un archivo
            show_reorder: Mostrar botones de reordenamiento
            show_remove: Mostrar botón de eliminar
        """
        self.files = files
        self.on_order_change = on_order_change
        self.on_remove = on_remove
        self.show_reorder = show_reorder
        self.show_remove = show_remove
        self.container = None

    def move_up(self, index: int):
        """Mueve el archivo una posición hacia arriba."""
        if index > 0:
            self.files[index], self.files[index-1] = self.files[index-1], self.files[index]
            if self.on_order_change:
                self.on_order_change(self.files)
            self.refresh()

    def move_down(self, index: int):
        """Mueve el archivo una posición hacia abajo."""
        if index < len(self.files) - 1:
            self.files[index], self.files[index+1] = self.files[index+1], self.files[index]
            if self.on_order_change:
                self.on_order_change(self.files)
            self.refresh()

    def remove(self, index: int):
        """Elimina un archivo de la lista."""
        if 0 <= index < len(self.files):
            self.files.pop(index)
            if self.on_remove:
                self.on_remove(index)
            self.refresh()

    def refresh(self):
        """Refresca la visualización de la lista."""
        if self.container:
            self.container.clear()
            with self.container:
                self._render_list()

    def _render_list(self):
        """Renderiza la lista de archivos."""
        if not self.files:
            with ui.row().classes('w-full justify-center p-4 text-slate-400'):
                ui.icon('description', size='sm').classes('mr-2')
                ui.label(state.i18n.t('common.no_files_loaded'))
            return

        for i, file_info in enumerate(self.files):
            with ui.row().classes('w-full items-center gap-2 p-0 px-2 bg-slate-50 rounded mb-0.5 hover:bg-slate-100 transition-colors'):
                # Número de orden
                ui.label(f"{i+1}").classes('w-5 h-5 flex items-center justify-center bg-slate-200 rounded text-[10px] font-bold text-slate-600')

                # Icono PDF
                ui.icon('picture_as_pdf', color='red').classes('text-lg')

                # Información del archivo
                with ui.column().classes('flex-grow min-w-0 gap-0'):
                    ui.label(file_info.get('name', 'Sin nombre')).classes('text-[13px] font-medium truncate')
                    with ui.row().classes('gap-1.5 text-[11px] text-slate-400'):
                        if 'pages' in file_info:
                            ui.label(f"{file_info['pages']} págs")
                        if 'size_mb' in file_info:
                            ui.label(f"· {file_info['size_mb']} MB")

                # Botones de reorden
                if self.show_reorder:
                    with ui.row().classes('gap-1'):
                        btn_up = ui.button(icon='keyboard_arrow_up', on_click=lambda _, idx=i: self.move_up(idx))\
                            .props('flat dense size=sm round').classes('text-slate-400 hover:text-slate-600')
                        if i == 0 or len(self.files) <= 1:
                            btn_up.props('disable')

                        btn_down = ui.button(icon='keyboard_arrow_down', on_click=lambda _, idx=i: self.move_down(idx))\
                            .props('flat dense size=sm round').classes('text-slate-400 hover:text-slate-600')
                        if i == len(self.files) - 1 or len(self.files) <= 1:
                            btn_down.props('disable')

                # Botón eliminar
                if self.show_remove:
                    ui.button(icon='close', on_click=lambda _, idx=i: self.remove(idx))\
                        .props('flat dense size=sm round color=negative')

    def render(self) -> ui.column:
        """Renderiza el componente y retorna el contenedor."""
        self.container = ui.column().classes('w-full')
        with self.container:
            self._render_list()
        return self.container

    def get_ordered_paths(self) -> List[str]:
        """Retorna las rutas de archivos en el orden actual."""
        return [f.get('path', '') for f in self.files]

    def clear(self):
        """Limpia la lista de archivos."""
        self.files = []
        self.refresh()

    def add_file(self, file_info: Dict):
        """Añade un archivo a la lista."""
        self.files.append(file_info)
        self.refresh()

    def set_files(self, files: List[Dict]):
        """Establece la lista completa de archivos."""
        self.files = files
        self.refresh()
